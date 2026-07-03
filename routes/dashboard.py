# -*- coding: utf-8 -*-
"""Blueprint: dashboard"""

import sqlite3
import logging
import json as _json
import os
import re
import time as _time
from datetime import datetime, date, timedelta
from io import BytesIO
from flask import (
    Blueprint, render_template, request, jsonify, session,
    redirect, url_for, g, send_from_directory, Response, send_file,
)

from core.constants import *
from core.database import get_db, cache_get, cache_set, cache_bust, _CACHE
from core.auth import (
    _hash, _check_password, _normalizar_rol, _ciclo_del_rol,
    login_required, coord_required, admin_required, directora_required,
    _csrf_token, _csrf_check, csrf_protected, rate_limited,
    get_usuario,
)
from core.helpers import *
from core.ia import _get_groq_client, groq_client, construir_prompt, construir_prompt_planificacion, construir_prompt_rubrica, construir_prompt_estrategia
from core.excel import _parsear_boletin_bj, _buscar_o_crear_estudiante, _detectar_mencion_listado, _limpiar_nota
from core.pdf import _generar_pdf_acuerdo

logger = logging.getLogger("axula")

dashboard_bp = Blueprint("dashboard_bp", __name__)

@dashboard_bp.route("/")
@login_required
def index():
    return redirect("/home")


@dashboard_bp.route("/dashboard")
@login_required
def dashboard_clasico():
    """Dashboard clásico con tabla de estudiantes."""
    u = get_usuario()
    rol = u.get("rol","")
    return render_template(
        "index.html",
        usuario=u,
        current_user=u,
        es_profesor=(rol == "profesor"),
        es_coord=(rol in ROLES_COORD),
        es_admin=(rol in ROLES_DIRECTORA),
        es_psicologa=(rol in ROLES_PSICOLOGA),
        prof_grado=(u.get("grado") or ""),
        prof_mencion=(u.get("mencion") or ""),
        prof_asignaturas=(u.get("asignaturas") or ""),
    )


@dashboard_bp.route("/coordinador")
@login_required
def coordinador_page():
    """Panel exclusivo del coordinador de ciclo — vista unificada."""
    u = get_usuario()
    rol_n = _normalizar_rol(u.get("rol", ""))
    if rol_n not in ROLES_COORD and not u.get("es_directora"):
        return redirect("/")
    ciclo = _ciclo_del_rol(rol_n) or "segundo_ciclo"
    return render_template("coordinador.html", current_user=u, ciclo=ciclo)


@dashboard_bp.route("/api/coordinador/resumen")
@login_required
def coordinador_resumen():
    """Resumen completo del ciclo para el panel del coordinador."""
    u = get_usuario()
    rol_n = _normalizar_rol(u.get("rol", ""))
    if rol_n not in ROLES_COORD and not u.get("es_directora"):
        return jsonify({"error": "Sin permisos"}), 403

    ciclo = _ciclo_del_rol(rol_n)
    filtro_ciclo = ciclo if ciclo else None

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row

        base_q = "WHERE 1=1"
        base_p = []
        if filtro_ciclo:
            base_q += " AND ciclo=?"
            base_p.append(filtro_ciclo)

        total_est  = conn.execute(f"SELECT COUNT(*) FROM estudiantes {base_q}", base_p).fetchone()[0]
        con_notas  = conn.execute(f"SELECT COUNT(*) FROM estudiantes {base_q} AND (p_acad>0 OR acad_p1>0)", base_p).fetchone()[0]
        criticos   = conn.execute(f"SELECT COUNT(*) FROM estudiantes {base_q} AND p_acad>0 AND p_acad<70", base_p).fetchone()[0]
        observacion= conn.execute(f"SELECT COUNT(*) FROM estudiantes {base_q} AND p_acad>=70 AND p_acad<80", base_p).fetchone()[0]
        excelentes = conn.execute(f"SELECT COUNT(*) FROM estudiantes {base_q} AND p_acad>=85", base_p).fetchone()[0]

        prom_row = conn.execute(f"SELECT ROUND(AVG(p_acad),1) as prom FROM estudiantes {base_q} AND p_acad>0", base_p).fetchone()
        prom_ciclo = (prom_row["prom"] if prom_row else None) or 0

        riesgo_rows = conn.execute(
            f"""SELECT id, nombre, apellido, grado, curso, seccion, p_acad, acad_p1, acad_p2, acad_p3
                FROM estudiantes {base_q} AND p_acad>0 ORDER BY p_acad ASC LIMIT 10""", base_p).fetchall()

        casos_q = """SELECT c.id, c.titulo, c.tipo, c.estado, c.nivel_escala, c.creado_en,
                            e.nombre||' '||e.apellido as estudiante, e.grado, e.ciclo
                     FROM casos c JOIN estudiantes e ON e.id=c.estudiante_id
                     WHERE c.estado NOT IN ('Resuelto','Cerrado')"""
        casos_p = []
        if filtro_ciclo:
            casos_q += " AND e.ciclo=?"; casos_p.append(filtro_ciclo)
        casos_q += " ORDER BY c.creado_en DESC LIMIT 10"
        casos_rows = conn.execute(casos_q, casos_p).fetchall()

        dist_rows = conn.execute(
            f"""SELECT grado, COUNT(*) as total,
                       ROUND(AVG(CASE WHEN p_acad>0 THEN p_acad END),1) as prom,
                       SUM(CASE WHEN p_acad>0 AND p_acad<70 THEN 1 ELSE 0 END) as en_riesgo
                FROM estudiantes {base_q} GROUP BY grado ORDER BY grado""", base_p).fetchall()

        from datetime import date, timedelta
        inicio_sem = date.today() - timedelta(days=date.today().weekday())
        try:
            ausencias_q = "SELECT COUNT(*) FROM asistencia a JOIN estudiantes e ON e.id=a.estudiante_id WHERE a.estado IN ('ausente','A') AND a.fecha>=?"
            ausencias_p = [inicio_sem.isoformat()]
            if filtro_ciclo: ausencias_q += " AND e.ciclo=?"; ausencias_p.append(filtro_ciclo)
            ausencias_sem = conn.execute(ausencias_q, ausencias_p).fetchone()[0]
        except Exception: ausencias_sem = 0

        try:
            rq = "SELECT COUNT(*) FROM reportes r JOIN estudiantes e ON e.id=r.estudiante_id WHERE r.fecha>=?"
            rp = [inicio_sem.isoformat()]
            if filtro_ciclo: rq += " AND e.ciclo=?"; rp.append(filtro_ciclo)
            reportes_sem = conn.execute(rq, rp).fetchone()[0]
        except Exception: reportes_sem = 0

        # Distribución semáforo conductual (Motor Conductual Fase 1)
        try:
            sem_q = f"""SELECT semaforo, COUNT(*) as n
                        FROM estudiantes {base_q}
                        AND semaforo IS NOT NULL
                        GROUP BY semaforo"""
            sem_rows = conn.execute(sem_q, base_p).fetchall()
            semaforo_dist = {r["semaforo"]: r["n"] for r in sem_rows}
        except Exception:
            semaforo_dist = {}

    return jsonify({
        "ciclo": filtro_ciclo or "todos",
        "kpis": {
            "total_estudiantes": total_est, "con_notas": con_notas,
            "prom_ciclo": prom_ciclo, "criticos": criticos,
            "observacion": observacion, "excelentes": excelentes,
            "ausencias_semana": ausencias_sem, "reportes_semana": reportes_sem,
        },
        "en_riesgo":      [dict(r) for r in riesgo_rows],
        "casos_abiertos": [dict(r) for r in casos_rows],
        "por_grado":      [dict(r) for r in dist_rows],
        "semaforo_dist":  semaforo_dist,
    })


@dashboard_bp.route("/api/dashboard/metricas-avanzadas")
@login_required
def metricas_avanzadas():
    """
    Métricas detalladas para coordinadores y directora:
    - Tasa de aprobación y promedio por grado + mención
    - Asistencia promedio real (%) por grado
    - Tendencia P1→P2→P3→P4 del ciclo
    - Distribución por nivel Ord.04-2023
    """
    u = get_usuario()
    rol_n = _normalizar_rol(u.get("rol", ""))
    if rol_n not in ROLES_COORD and not u.get("es_directora"):
        return jsonify({"error": "Sin permisos"}), 403

    ciclo = _ciclo_del_rol(rol_n)
    filtro_ciclo = ciclo if ciclo else None

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row

        base_q = "WHERE condicion='ACTIVO'"
        base_p = []
        if filtro_ciclo:
            base_q += " AND ciclo=?"
            base_p.append(filtro_ciclo)

        # ── Por grado + mención ──────────────────────────────────────────────
        por_mencion = conn.execute(f"""
            SELECT grado, curso AS mencion,
                   COUNT(*) as total,
                   ROUND(AVG(CASE WHEN p_acad > 0 THEN p_acad END), 1) AS promedio,
                   SUM(CASE WHEN p_acad >= 70 THEN 1 ELSE 0 END) AS aprobados,
                   SUM(CASE WHEN p_acad > 0 AND p_acad < 70 THEN 1 ELSE 0 END) AS en_riesgo
            FROM estudiantes {base_q}
            GROUP BY grado, curso
            ORDER BY grado, curso
        """, base_p).fetchall()

        # ── Tendencia P1→P2→P3→P4 ───────────────────────────────────────────
        tendencia = conn.execute(f"""
            SELECT
                ROUND(AVG(CASE WHEN acad_p1 > 0 THEN acad_p1 END), 1) AS p1,
                ROUND(AVG(CASE WHEN acad_p2 > 0 THEN acad_p2 END), 1) AS p2,
                ROUND(AVG(CASE WHEN acad_p3 > 0 THEN acad_p3 END), 1) AS p3,
                ROUND(AVG(CASE WHEN acad_p4 > 0 THEN acad_p4 END), 1) AS p4
            FROM estudiantes {base_q} AND p_acad > 0
        """, base_p).fetchone()

        # ── Distribución niveles Ord.04-2023 ────────────────────────────────
        niveles = conn.execute(f"""
            SELECT
              SUM(CASE WHEN p_acad >= 89 THEN 1 ELSE 0 END) AS destacado,
              SUM(CASE WHEN p_acad >= 80 AND p_acad < 89 THEN 1 ELSE 0 END) AS satisfactorio,
              SUM(CASE WHEN p_acad >= 70 AND p_acad < 80 THEN 1 ELSE 0 END) AS basico,
              SUM(CASE WHEN p_acad >= 60 AND p_acad < 70 THEN 1 ELSE 0 END) AS en_proceso,
              SUM(CASE WHEN p_acad > 0 AND p_acad < 60 THEN 1 ELSE 0 END) AS insuficiente,
              SUM(CASE WHEN p_acad IS NULL OR p_acad = 0 THEN 1 ELSE 0 END) AS sin_nota
            FROM estudiantes {base_q}
        """, base_p).fetchone()

        # ── Asistencia promedio por grado ────────────────────────────────────
        try:
            asist_grado = conn.execute(f"""
                SELECT e.grado,
                       ROUND(
                         100.0 * SUM(CASE WHEN a.estado IN ('P','presente') THEN 1 ELSE 0 END)
                         / NULLIF(COUNT(a.id), 0)
                       , 1) AS pct_asistencia,
                       COUNT(DISTINCT a.estudiante_id) AS con_registro
                FROM asistencia a
                JOIN estudiantes e ON e.id = a.estudiante_id
                {'WHERE e.ciclo=?' if filtro_ciclo else 'WHERE 1=1'}
                GROUP BY e.grado ORDER BY e.grado
            """, ([filtro_ciclo] if filtro_ciclo else [])).fetchall()
        except Exception:
            asist_grado = []

    return jsonify({
        "por_mencion": [dict(r) for r in por_mencion],
        "tendencia": {
            "p1": tendencia["p1"] if tendencia else None,
            "p2": tendencia["p2"] if tendencia else None,
            "p3": tendencia["p3"] if tendencia else None,
            "p4": tendencia["p4"] if tendencia else None,
        },
        "niveles": dict(niveles) if niveles else {},
        "asistencia_por_grado": [dict(r) for r in asist_grado],
    })


@dashboard_bp.route("/home")
@login_required
def home_dashboard():
    """
    Dashboard principal — usa index.html que soporta todos los roles.
    /home y /dashboard son equivalentes; se mantiene /home por compatibilidad
    con los links de navegación existentes en los templates.
    """
    u   = get_usuario()
    rol = _normalizar_rol(u.get("rol", ""))

    # Roles operativos puros → redirigir a su portal propio
    if rol == "suministros":
        return redirect("/suministros")
    return render_template(
        "index.html",
        usuario=u,
        current_user=u,
        es_profesor=(rol == "profesor"),
        es_coord=(rol in ROLES_COORD),
        es_admin=(rol in ROLES_DIRECTORA),
        es_psicologa=(rol in ROLES_PSICOLOGA),
        prof_grado=(u.get("grado") or ""),
        prof_mencion=(u.get("mencion") or ""),
        prof_asignaturas=(u.get("materia") or ""),
    )


# ── PANEL EJECUTIVO DIRECTORA ───────────────────────────────────────────────

@dashboard_bp.route("/ejecutivo")
@login_required
def panel_ejecutivo():
    u = get_usuario()
    rol = _normalizar_rol(u.get("rol", ""))
    if rol not in ROLES_COORD | ROLES_DIRECTORA:
        return redirect("/")
    return render_template("ejecutivo.html", current_user=u)


@dashboard_bp.route("/api/dashboard/kpis-ejecutivos")
@login_required
def kpis_ejecutivos():
    """KPIs consolidados para la directora: aprobación, promedio, riesgo, tendencia."""
    u = get_usuario()
    rol = _normalizar_rol(u.get("rol", ""))
    if rol not in ROLES_SUPER | ROLES_DIRECTORA | ROLES_COORD:
        return jsonify({"error": "Sin permisos"}), 403

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row

        # ── Totales generales ────────────────────────────────────────────────
        total_activos = conn.execute(
            "SELECT COUNT(*) FROM estudiantes WHERE condicion='ACTIVO'"
        ).fetchone()[0]

        total_inactivos = conn.execute(
            "SELECT COUNT(*) FROM estudiantes WHERE condicion != 'ACTIVO'"
        ).fetchone()[0]

        # ── Aprobación y promedio por grado (desde materias_calificaciones) ──
        por_grado = conn.execute("""
            SELECT
                grado,
                COUNT(DISTINCT estudiante_id)                               AS estudiantes,
                ROUND(AVG(CASE WHEN p1 > 0 THEN p1 END), 1)               AS prom_p1,
                ROUND(AVG(CASE WHEN p2 > 0 THEN p2 END), 1)               AS prom_p2,
                ROUND(AVG(CASE WHEN p3 > 0 THEN p3 END), 1)               AS prom_p3,
                COUNT(CASE WHEN p1 >= 70 THEN 1 END)                       AS aprob_p1,
                COUNT(CASE WHEN p1 > 0  THEN 1 END)                        AS con_nota_p1,
                COUNT(CASE WHEN p2 >= 70 THEN 1 END)                       AS aprob_p2,
                COUNT(CASE WHEN p2 > 0  THEN 1 END)                        AS con_nota_p2
            FROM materias_calificaciones
            WHERE grado IS NOT NULL AND grado != ''
            GROUP BY grado ORDER BY grado
        """).fetchall()

        # ── Tendencia institucional P1→P2→P3 (promedio de promedios por est) ─
        tendencia = conn.execute("""
            SELECT
                ROUND(AVG(CASE WHEN acad_p1 > 0 THEN acad_p1 END), 1) AS p1,
                ROUND(AVG(CASE WHEN acad_p2 > 0 THEN acad_p2 END), 1) AS p2,
                ROUND(AVG(CASE WHEN acad_p3 > 0 THEN acad_p3 END), 1) AS p3
            FROM estudiantes WHERE condicion='ACTIVO' AND p_acad > 0
        """).fetchone()

        # ── Distribución niveles Ord.04-2023 (estudiantes con notas) ────────
        niveles = conn.execute("""
            SELECT
                SUM(CASE WHEN p_acad >= 89 THEN 1 ELSE 0 END)              AS destacado,
                SUM(CASE WHEN p_acad >= 80 AND p_acad < 89 THEN 1 ELSE 0 END) AS satisfactorio,
                SUM(CASE WHEN p_acad >= 70 AND p_acad < 80 THEN 1 ELSE 0 END) AS basico,
                SUM(CASE WHEN p_acad >= 60 AND p_acad < 70 THEN 1 ELSE 0 END) AS en_proceso,
                SUM(CASE WHEN p_acad >  0  AND p_acad < 60 THEN 1 ELSE 0 END) AS insuficiente,
                SUM(CASE WHEN p_acad IS NULL OR p_acad = 0 THEN 1 ELSE 0 END) AS sin_nota
            FROM estudiantes WHERE condicion='ACTIVO'
        """).fetchone()

        # ── Aprobación global P1 y P2 ────────────────────────────────────────
        glob = conn.execute("""
            SELECT
                ROUND(AVG(CASE WHEN p1 > 0 THEN p1 END), 1) AS prom_p1_global,
                ROUND(AVG(CASE WHEN p2 > 0 THEN p2 END), 1) AS prom_p2_global,
                COUNT(CASE WHEN p1 >= 70 THEN 1 END) * 100.0
                    / NULLIF(COUNT(CASE WHEN p1 > 0 THEN 1 END), 0) AS pct_aprob_p1,
                COUNT(CASE WHEN p2 >= 70 THEN 1 END) * 100.0
                    / NULLIF(COUNT(CASE WHEN p2 > 0 THEN 1 END), 0) AS pct_aprob_p2
            FROM materias_calificaciones
        """).fetchone()

        # ── Casos y reportes activos ─────────────────────────────────────────
        casos_abiertos = conn.execute(
            "SELECT COUNT(*) FROM casos WHERE estado NOT IN ('Resuelto','Cerrado','cerrado')"
        ).fetchone()[0]

        reportes_activos = conn.execute(
            "SELECT COUNT(*) FROM reportes WHERE estado IN ('abierto','en_seguimiento')"
        ).fetchone()[0]

        # ── Menciones (4TO-6TO) ──────────────────────────────────────────────
        por_mencion = conn.execute("""
            SELECT mencion, COUNT(*) AS total,
                   ROUND(AVG(CASE WHEN p_acad > 0 THEN p_acad END), 1) AS promedio
            FROM estudiantes
            WHERE condicion='ACTIVO' AND mencion IS NOT NULL AND mencion != ''
            GROUP BY mencion ORDER BY mencion
        """).fetchall()

        # ── Personal activo ──────────────────────────────────────────────────
        personal = conn.execute(
            "SELECT COUNT(*) FROM usuarios WHERE activo=1 AND rol != 'padre'"
        ).fetchone()[0]

    # Construir respuesta
    grados_data = []
    for g in por_grado:
        pct_p1 = round(g["aprob_p1"] * 100 / g["con_nota_p1"], 1) if g["con_nota_p1"] else None
        pct_p2 = round(g["aprob_p2"] * 100 / g["con_nota_p2"], 1) if g["con_nota_p2"] else None
        grados_data.append({
            "grado":       g["grado"],
            "estudiantes": g["estudiantes"],
            "prom_p1":     g["prom_p1"],
            "prom_p2":     g["prom_p2"],
            "prom_p3":     g["prom_p3"],
            "pct_aprob_p1": pct_p1,
            "pct_aprob_p2": pct_p2,
        })

    return jsonify({
        "resumen": {
            "total_activos":   total_activos,
            "total_inactivos": total_inactivos,
            "personal":        personal,
            "casos_abiertos":  casos_abiertos,
            "reportes_activos": reportes_activos,
            "prom_p1_global":  round(glob["prom_p1_global"] or 0, 1),
            "prom_p2_global":  round(glob["prom_p2_global"] or 0, 1),
            "pct_aprob_p1":    round(glob["pct_aprob_p1"] or 0, 1),
            "pct_aprob_p2":    round(glob["pct_aprob_p2"] or 0, 1),
        },
        "por_grado":  grados_data,
        "tendencia":  {
            "p1": tendencia["p1"] if tendencia else None,
            "p2": tendencia["p2"] if tendencia else None,
            "p3": tendencia["p3"] if tendencia else None,
        },
        "niveles":    dict(niveles) if niveles else {},
        "por_mencion": [dict(m) for m in por_mencion],
    })


# ── CIERRE DE PERÍODOS ──────────────────────────────────────────────────────


