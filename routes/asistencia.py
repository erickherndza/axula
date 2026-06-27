# -*- coding: utf-8 -*-
"""Blueprint: asistencia"""

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
from core import rls as _rls
from core.helpers import _get_profesor, _resolver_alcance_profesor, _validar_materia_profesor, _verificar_ausencias_semana
from core.ia import _get_groq_client, groq_client, construir_prompt, construir_prompt_planificacion, construir_prompt_rubrica, construir_prompt_estrategia
from core.excel import _parsear_boletin_bj, _buscar_o_crear_estudiante, _detectar_mencion_listado, _limpiar_nota
from core.pdf import _generar_pdf_acuerdo

logger = logging.getLogger("axula")

asistencia_bp = Blueprint("asistencia_bp", __name__)

@asistencia_bp.route("/api/asistencia/lote", methods=["POST"])
@login_required
@rate_limited(max_calls=20, window=60)
def registrar_asistencia_lote():
    """Registra asistencia de multiples estudiantes en un POST.
    Body: { fecha, materia, grado, periodo, horas_clase,
            registros: [{estudiante_id, estado, observacion}] }
    Valida materia/grado contra perfil del profesor.
    """
    d = request.get_json(silent=True) or {}
    fecha     = d.get("fecha", "")
    materia   = d.get("materia", "").strip()
    periodo   = int(d.get("periodo", 1))
    horas     = int(d.get("horas_clase", 1))
    registros = d.get("registros", [])
    grado     = d.get("grado", "").strip()
    if not fecha or not materia or not registros:
        return jsonify({"error": "fecha, materia y registros son requeridos"}), 400
    prof = _get_profesor()
    ok, msg = _validar_materia_profesor(materia, grado + " MULTIMEDIA", prof)
    if not ok:
        return jsonify({"error": msg}), 403
    prof_id = session.get("user_id")
    creados = 0
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        for r in registros:
            est_id = r.get("estudiante_id")
            estado = r.get("estado", "presente")
            obs    = r.get("observacion", "")
            if not est_id:
                continue
            existing = conn.execute(
                "SELECT id FROM asistencia WHERE estudiante_id=? AND materia=? AND fecha=? AND profesor_id=?",
                (est_id, materia, fecha, prof_id)
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE asistencia SET estado=?, horas_clase=?, observacion=? WHERE id=?",
                    (estado, horas, obs, existing[0])
                )
            else:
                conn.execute(
                    "INSERT INTO asistencia "
                    "(estudiante_id,profesor_id,materia,fecha,periodo,estado,horas_clase,observacion) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    (est_id, prof_id, materia, fecha, periodo, estado, horas, obs)
                )
            creados += 1
        conn.commit()
    return jsonify({"ok": True, "registros": creados})


@asistencia_bp.route("/api/asistencia/resumen-mensual/<int:prof_id>")
@login_required
def resumen_mensual_asistencia(prof_id):
    """Resumen mensual de asistencia para un profesor.
    Calculo MINERD: (horas presentes / horas totales impartidas) * 100.
    Alerta si < 75% (riesgo de reprobacion por inasistencia segun Ordenanza 1-96 Art 51).
    """
    mes     = request.args.get("mes", "")
    materia = request.args.get("materia", "")
    rol_actual = _normalizar_rol(session.get("rol", ""))
    if rol_actual not in ROLES_COORD and session.get("user_id") != prof_id:
        return jsonify({"error": "Sin permisos"}), 403
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        q = (
            "SELECT a.estudiante_id, e.nombre AS est_nombre, e.grado, a.materia,"
            " COUNT(*) AS total_sesiones,"
            " SUM(a.horas_clase) AS horas_totales,"
            " SUM(CASE WHEN a.estado='presente' THEN a.horas_clase ELSE 0 END) AS horas_presentes,"
            " SUM(CASE WHEN a.estado='tardanza' THEN 1 ELSE 0 END) AS tardanzas,"
            " SUM(CASE WHEN a.estado='ausente' THEN 1 ELSE 0 END) AS ausencias"
            " FROM asistencia a"
            " JOIN estudiantes e ON e.id=a.estudiante_id"
            " WHERE a.profesor_id=?"
        )
        params = [prof_id]
        if mes:
            q += " AND strftime('%Y-%m',a.fecha)=?"
            params.append(mes)
        if materia:
            q += " AND a.materia=?"
            params.append(materia)
        q += " GROUP BY a.estudiante_id,a.materia ORDER BY e.nombre"
        rows = conn.execute(q, params).fetchall()
    result = []
    for r in rows:
        ht  = r["horas_totales"] or 0
        hp  = r["horas_presentes"] or 0
        pct = round((hp / ht * 100), 1) if ht > 0 else 0
        result.append({
            "estudiante_id":         r["estudiante_id"],
            "nombre":                r["est_nombre"],
            "grado":                 r["grado"],
            "materia":               r["materia"],
            "total_sesiones":        r["total_sesiones"],
            "horas_totales":         ht,
            "horas_presentes":       hp,
            "ausencias":             r["ausencias"],
            "tardanzas":             r["tardanzas"],
            "porcentaje_asistencia": pct,
            "alerta_inasistencia":   pct < 75 if ht > 0 else False,
        })
    return jsonify(result)


@asistencia_bp.route("/api/asistencia", methods=["GET"])
@login_required
def listar_asistencia():
    prof = _get_profesor()
    est_id    = request.args.get("estudiante_id", "")
    materia   = request.args.get("materia", "")
    periodo   = request.args.get("periodo", "")
    prof_id   = request.args.get("profesor_id", "")
    fecha_ini = request.args.get("fecha_ini", "")
    fecha_fin = request.args.get("fecha_fin", "")

    q = """
        SELECT a.*, e.nombre, e.apellido, e.curso
        FROM asistencia a
        JOIN estudiantes e ON e.id = a.estudiante_id
        WHERE 1=1
    """
    params = []

    # Profesores solo ven su propia asistencia — usar _normalizar_rol para compatibilidad
    rol_norm = _normalizar_rol(prof.get("rol", "")) if prof else ""
    if prof and rol_norm == "profesor":
        q += " AND a.profesor_id=?"; params.append(prof["id"])
    elif prof_id:
        q += " AND a.profesor_id=?"; params.append(int(prof_id))

    if est_id:   q += " AND a.estudiante_id=?"; params.append(int(est_id))
    if materia:  q += " AND a.materia=?";        params.append(materia)
    if periodo:  q += " AND a.periodo=?";         params.append(int(periodo))
    if fecha_ini: q += " AND a.fecha>=?";          params.append(fecha_ini)
    if fecha_fin: q += " AND a.fecha<=?";          params.append(fecha_fin)

    q += " ORDER BY a.fecha DESC, e.apellido"

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(q, params).fetchall()
    return jsonify([dict(r) for r in rows])


@asistencia_bp.route("/api/asistencia", methods=["POST"])
@login_required
@rate_limited(max_calls=20, window=60)
def registrar_asistencia():
    """Registra asistencia masiva para una clase (lista de estudiantes)."""
    prof = _get_profesor()
    d = request.get_json(silent=True) or {}

    materia  = d.get("materia", "").strip()
    periodo  = d.get("periodo", 1)
    fecha    = d.get("fecha", "")
    horas    = d.get("horas_clase", 1)
    registros= d.get("registros", [])  # [{estudiante_id, estado, observacion}]

    if not materia or not fecha or not registros:
        return jsonify({"error": "materia, fecha y registros son requeridos"}), 400

    prof_id = prof["id"] if prof else 0

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        for r in registros:
            est_id = r.get("estudiante_id")
            if not est_id:
                continue
            # Upsert: si ya existe esa fecha+estudiante+materia, actualiza
            existing = conn.execute(
                "SELECT id FROM asistencia WHERE estudiante_id=? AND materia=? AND fecha=? AND profesor_id=?",
                (est_id, materia, fecha, prof_id)
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE asistencia SET estado=?, horas_clase=?, observacion=?, periodo=? WHERE id=?",
                    (r.get("estado","presente"), horas, r.get("observacion",""), periodo, existing[0])
                )
            else:
                conn.execute(
                    """INSERT INTO asistencia
                       (estudiante_id, profesor_id, materia, fecha, periodo, estado, horas_clase, observacion)
                       VALUES (?,?,?,?,?,?,?,?)""",
                    (est_id, prof_id, materia, fecha, periodo,
                     r.get("estado","presente"), horas, r.get("observacion",""))
                )
        conn.commit()

    # ── Verificar alertas de ausencias por semana ─────────────────────────
    ausentes_ids = [
        r.get("estudiante_id") for r in registros
        if r.get("estado") in ("ausente", "A", "tardanza", "T")
        and r.get("estudiante_id")
    ]
    if ausentes_ids and fecha:
        with sqlite3.connect(DATABASE, timeout=10) as conn2:
            conn2.row_factory = sqlite3.Row
            for est_id in set(ausentes_ids):
                _verificar_ausencias_semana(conn2, est_id, fecha)
            conn2.commit()

    return jsonify({"ok": True, "registrados": len(registros)})


@asistencia_bp.route("/api/asistencia/resumen/<int:est_id>")
@login_required
def resumen_asistencia(est_id):
    """
    Calcula resumen de asistencia por materia y período.
    Fórmula MINERD: % = (horas_presentes / horas_totales) × 100
    Umbral reprobación: <80% (margen sobre el 20% de inasistencias permitidas)
    """
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        _rls.verificar_acceso_estudiante(conn, est_id)
        rows = conn.execute("""
            SELECT materia, periodo,
                   SUM(horas_clase) as horas_total,
                   SUM(CASE WHEN estado='presente' THEN horas_clase ELSE 0 END) as horas_presente,
                   SUM(CASE WHEN estado='tardanza' THEN horas_clase ELSE 0 END) as horas_tardanza,
                   SUM(CASE WHEN estado='ausente' THEN horas_clase ELSE 0 END)  as horas_ausente,
                   SUM(CASE WHEN estado='justificado' THEN horas_clase ELSE 0 END) as horas_justif,
                   COUNT(*) as total_dias
            FROM asistencia
            WHERE estudiante_id=?
            GROUP BY materia, periodo
            ORDER BY materia, periodo
        """, (est_id,)).fetchall()

    resultado = []
    for r in rows:
        total  = r["horas_total"] or 1
        pres   = (r["horas_presente"] or 0) + (r["horas_tardanza"] or 0) * 0.5
        pct    = round(pres / total * 100, 1)
        inasist_pct = round((r["horas_ausente"] or 0) / total * 100, 1)
        alerta = inasist_pct > 15  # Alerta temprana (MINERD reprueba >20%)
        critico= inasist_pct >= 20  # Ya en zona de reprobación

        resultado.append({
            "materia":         r["materia"],
            "periodo":         r["periodo"],
            "horas_total":     r["horas_total"],
            "horas_presente":  r["horas_presente"],
            "horas_ausente":   r["horas_ausente"],
            "horas_tardanza":  r["horas_tardanza"],
            "horas_justif":    r["horas_justif"],
            "pct_asistencia":  pct,
            "pct_inasistencia":inasist_pct,
            "alerta":          alerta,
            "critico":         critico,
            "total_dias":      r["total_dias"],
        })
    return jsonify(resultado)


@asistencia_bp.route("/api/asistencia/clase")
@login_required
def asistencia_por_clase():
    """Retorna lista de estudiantes para pasar lista, filtrada por profesor."""
    prof = _get_profesor()
    materia = request.args.get("materia", "")
    grado   = request.args.get("grado", "")

    # Build filter
    q = "SELECT id, nombre, apellido, curso, grado FROM estudiantes WHERE 1=1"
    params = []

    if prof and prof.get("rol") == "profesor":
        if prof.get("grado"):
            q += " AND grado LIKE ?"; params.append(f"%{prof['grado']}%")
        if prof.get("mencion"):
            q += " AND curso LIKE ?"; params.append(f"%{prof['mencion']}%")
    elif grado:
        q += " AND grado LIKE ?"; params.append(f"%{grado}%")

    q += " ORDER BY apellido, nombre"

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(q, params).fetchall()
    return jsonify([dict(r) for r in rows])


# ── IMPORTAR LISTA DE PROFESORES (Excel) ────────────────────────────────────


@asistencia_bp.route("/api/asistencia-mensual/calcular", methods=["POST"])
@login_required
def calcular_asistencia_mensual():
    """
    Calcula el resumen de asistencia del mes para todos los estudiantes
    del profesor. El profesor indica cuántos días dio clase ese mes.
    """
    u = get_usuario()
    data = request.get_json() or {}
    mes     = int(data.get("mes", 1))
    anio    = int(data.get("anio", 2025))
    materia = data.get("materia", "").strip()
    dias_clase_impartidos = int(data.get("dias_clase_impartidos", 0))
    anio_esc = data.get("anio_escolar", "2025-2026")

    if not materia or dias_clase_impartidos < 1:
        return jsonify({"error": "Materia y días de clase son requeridos"}), 400

    mes_str = f"{anio:04d}-{mes:02d}"
    import datetime as _dt

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        # Obtener días hábiles del mes desde calendario
        no_lab = {r[0] for r in conn.execute("""
            SELECT fecha FROM calendario_escolar
            WHERE substr(fecha,1,7)=? AND anio_escolar=?
        """, (mes_str, anio_esc)).fetchall()}

        import calendar as _cal
        _, total_dias = _cal.monthrange(anio, mes)
        habiles = sum(
            1 for d in range(1, total_dias+1)
            if _dt.date(anio, mes, d).weekday() < 5
            and f"{anio:04d}-{mes:02d}-{d:02d}" not in no_lab
        )

        # Contar asistencias por estudiante en el mes
        asist_rows = conn.execute("""
            SELECT estudiante_id,
                   SUM(CASE WHEN estado='presente' THEN 1 ELSE 0 END) as presentes,
                   COUNT(*) as total_registros
            FROM asistencia
            WHERE profesor_id=? AND materia=?
              AND substr(fecha,1,7)=?
            GROUP BY estudiante_id
        """, (u["id"], materia, mes_str)).fetchall()

        resumen = []
        for row in asist_rows:
            presentes = row["presentes"] or 0
            pct = round((presentes / dias_clase_impartidos) * 100, 1) if dias_clase_impartidos > 0 else 0

            conn.execute("""
                INSERT INTO asistencia_mensual
                    (estudiante_id, profesor_id, materia, mes, anio,
                     dias_habiles, dias_clase_impartidos, dias_asistio, porcentaje)
                VALUES (?,?,?,?,?,?,?,?,?)
                ON CONFLICT(estudiante_id, profesor_id, materia, mes, anio)
                DO UPDATE SET
                    dias_habiles=excluded.dias_habiles,
                    dias_clase_impartidos=excluded.dias_clase_impartidos,
                    dias_asistio=excluded.dias_asistio,
                    porcentaje=excluded.porcentaje,
                    validado=0
            """, (row["estudiante_id"], u["id"], materia, mes, anio,
                  habiles, dias_clase_impartidos, presentes, pct))

            resumen.append({
                "estudiante_id": row["estudiante_id"],
                "presentes": presentes,
                "porcentaje": pct
            })

        conn.commit()

    return jsonify({
        "ok": True,
        "mes": mes, "anio": anio,
        "dias_habiles": habiles,
        "dias_clase_impartidos": dias_clase_impartidos,
        "estudiantes_calculados": len(resumen),
        "resumen": resumen
    })


@asistencia_bp.route("/api/asistencia-mensual/validar", methods=["POST"])
@login_required
def validar_asistencia_mensual():
    """El profesor valida (cierra) el mes de asistencia."""
    u   = get_usuario()
    data = request.get_json() or {}
    mes     = int(data.get("mes"))
    anio    = int(data.get("anio"))
    materia = data.get("materia","").strip()
    import datetime as _dt
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.execute("""
            UPDATE asistencia_mensual
               SET validado=1, fecha_validacion=?
             WHERE profesor_id=? AND materia=? AND mes=? AND anio=?
        """, (_dt.datetime.now().isoformat(), u["id"], materia, mes, anio))
        conn.commit()
    cache_bust()
    return jsonify({"ok": True, "mensaje": f"Asistencia de {mes}/{anio} validada"})


@asistencia_bp.route("/api/asistencia-mensual/<int:est_id>", methods=["GET"])
@login_required
def get_asistencia_mensual_est(est_id):
    """Historial de asistencia mensual de un estudiante."""
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        _rls.verificar_acceso_estudiante(conn, est_id)
        rows = conn.execute("""
            SELECT am.*, u.nombre as profesor_nombre
            FROM asistencia_mensual am
            JOIN usuarios u ON am.profesor_id = u.id
            WHERE am.estudiante_id=?
            ORDER BY am.anio DESC, am.mes DESC
        """, (est_id,)).fetchall()
    return jsonify([dict(r) for r in rows])


# ══════════════════════════════════════════════════════════════════════════════
#  EVALUACIONES NARRATIVAS DEL PROFESOR
# ══════════════════════════════════════════════════════════════════════════════


@asistencia_bp.route("/api/evaluacion-narrativa", methods=["POST"])
@login_required
def guardar_evaluacion_narrativa():
    u    = get_usuario()
    data = request.get_json() or {}
    est_id   = data.get("estudiante_id")
    periodo  = int(data.get("periodo", 1))
    texto    = (data.get("texto") or "").strip()
    anio_esc = data.get("anio_escolar", "2025-2026")

    if not est_id or not texto:
        return jsonify({"error": "Faltan campos"}), 400

    import datetime as _dt
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.execute("""
            INSERT INTO evaluaciones_narrativas
                (estudiante_id, profesor_id, periodo, anio_escolar, texto, actualizado_en)
            VALUES (?,?,?,?,?,?)
            ON CONFLICT(estudiante_id, profesor_id, periodo, anio_escolar)
            DO UPDATE SET texto=excluded.texto, actualizado_en=excluded.actualizado_en
        """, (est_id, u["id"], periodo, anio_esc, texto,
              _dt.datetime.now().isoformat()))
        conn.commit()
    return jsonify({"ok": True})


@asistencia_bp.route("/api/evaluacion-narrativa/<int:est_id>", methods=["GET"])
@login_required
def get_evaluaciones_narrativas(est_id):
    anio_esc = request.args.get("anio_escolar", "2025-2026")
    u = get_usuario()
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        _rls.verificar_acceso_estudiante(conn, est_id)
        # Profesores solo ven las suyas; coordinadores/directora ven todas
        rol_n = _normalizar_rol(u.get("rol",""))
        if rol_n == "profesor":
            rows = conn.execute("""
                SELECT en.*, u.nombre as profesor_nombre
                FROM evaluaciones_narrativas en
                JOIN usuarios u ON en.profesor_id = u.id
                WHERE en.estudiante_id=? AND en.profesor_id=? AND en.anio_escolar=?
                ORDER BY en.periodo
            """, (est_id, u["id"], anio_esc)).fetchall()
        else:
            rows = conn.execute("""
                SELECT en.*, u.nombre as profesor_nombre
                FROM evaluaciones_narrativas en
                JOIN usuarios u ON en.profesor_id = u.id
                WHERE en.estudiante_id=? AND en.anio_escolar=?
                ORDER BY en.periodo, u.nombre
            """, (est_id, anio_esc)).fetchall()
    return jsonify([dict(r) for r in rows])


# ══════════════════════════════════════════════════════════════════════════════
#  PROGRESO DEL ESTUDIANTE (vista del profesor)
# ══════════════════════════════════════════════════════════════════════════════


@asistencia_bp.route("/api/profesor/mis-grupos")
@login_required
def mis_grupos():
    """
    Devuelve los grupos reales que tiene el profesor:
    combinaciones únicas de (grado, curso/mención, materia) extraídas de
    sus registros de asistencia y calificaciones_periodo.
    Es la fuente de verdad para saber a quién le da clase.
    """
    u   = get_usuario()
    prof_id = u.get("id")
    from core.database import get_db
    with get_db() as conn:
        rows_asist = conn.execute("""
            SELECT DISTINCT e.grado, e.curso, a.materia
            FROM asistencia a
            JOIN estudiantes e ON e.id = a.estudiante_id
            WHERE a.profesor_id = ?
        """, (prof_id,)).fetchall()

        rows_calif = conn.execute("""
            SELECT DISTINCT e.grado, e.curso, cp.materia
            FROM calificaciones_periodo cp
            JOIN estudiantes e ON e.id = cp.estudiante_id
            WHERE cp.profesor_id = ?
        """, (prof_id,)).fetchall()

    vistos = {}
    for r in list(rows_asist) + list(rows_calif):
        grado  = r["grado"]  or ""
        curso  = r["curso"]  or ""
        materia = r["materia"] or ""
        key = f"{grado}|{curso}|{materia}"
        if key not in vistos:
            curso_label = curso.replace(grado, "").strip() if grado in curso else curso
            vistos[key] = {
                "grado":   grado,
                "curso":   curso,
                "materia": materia,
                "label":   f"{grado} {curso_label} — {materia}".strip(" —"),
            }

    grupos = sorted(vistos.values(), key=lambda x: (x["grado"], x["curso"], x["materia"]))
    return jsonify(grupos)


@asistencia_bp.route("/api/profesor/estadisticas-asistencia")
@login_required
def profesor_estadisticas_asistencia():
    """
    Devuelve estadísticas de asistencia de los estudiantes del profesor
    filtradas por período (semana, mes, periodo, anio) y materia.
    Incluye totales por estudiante y resumen general.
    """
    u = get_usuario()
    periodo = request.args.get("periodo", "semana")
    fecha   = request.args.get("fecha", "")
    materia = request.args.get("materia", "").strip()
    grado_filtro = request.args.get("grado", "").strip()
    curso_filtro = request.args.get("curso", "").strip()

    from datetime import date, timedelta, datetime

    # ── Rango de fechas según período ──────────────────────────────────
    hoy = date.today()
    try:
        ref = datetime.strptime(fecha, "%Y-%m-%d").date() if fecha else hoy
    except Exception:
        ref = hoy

    if periodo == "semana":
        # Lunes de la semana de la fecha de referencia
        inicio = ref - timedelta(days=ref.weekday())
        fin    = inicio + timedelta(days=6)
        label  = f"Semana {inicio.strftime('%d/%m')} – {fin.strftime('%d/%m/%Y')}"
    elif periodo == "mes":
        inicio = ref.replace(day=1)
        next_month = (inicio.replace(day=28) + timedelta(days=4)).replace(day=1)
        fin    = next_month - timedelta(days=1)
        label  = inicio.strftime("%B %Y")
    elif periodo == "periodo":
        # Períodos del año escolar dominicano
        m = ref.month
        if m in (8, 9, 10):
            inicio = date(ref.year, 8, 1); fin = date(ref.year, 10, 31); label = "P1 (Ago–Oct)"
        elif m in (11, 12):
            inicio = date(ref.year, 11, 1); fin = date(ref.year, 12, 31); label = "P2 (Nov–Dic)"
        elif m == 1:
            inicio = date(ref.year, 1, 1);  fin = date(ref.year, 1, 31);  label = "P2 (Ene)"
        elif m in (2, 3, 4):
            inicio = date(ref.year, 2, 1);  fin = date(ref.year, 4, 30);  label = "P3 (Feb–Abr)"
        else:
            inicio = date(ref.year, 5, 1);  fin = date(ref.year, 7, 31);  label = "P4 (May–Jul)"
    else:  # anio
        if hoy.month >= 8:
            inicio = date(hoy.year, 8, 1); fin = date(hoy.year + 1, 7, 31)
        else:
            inicio = date(hoy.year - 1, 8, 1); fin = date(hoy.year, 7, 31)
        label = f"Año Escolar {inicio.year}–{fin.year}"

    ini_str = inicio.isoformat()
    fin_str = fin.isoformat()

    # ── Obtener estudiantes del profesor ──────────────────────────────
    prof_id_est = u.get("id")
    rol_norm_est = _normalizar_rol(u.get("rol", ""))
    roles_admin_est = {"directora", "coordinador_general",
                       "coordinador_primer_ciclo", "coordinador_segundo_ciclo"}

    est_query  = "SELECT id, nombre, apellido, grado, curso, ciclo, seccion FROM estudiantes WHERE 1=1"
    est_params = []

    if grado_filtro or curso_filtro:
        # Grupo específico seleccionado por el profesor — filtrar exacto
        if grado_filtro:
            est_query += " AND grado=?"
            est_params.append(grado_filtro)
        if curso_filtro:
            est_query += " AND curso=?"
            est_params.append(curso_filtro)
    elif rol_norm_est not in roles_admin_est:
        # Sin grupo seleccionado: restringir a estudiantes con registro de este profesor
        from core.database import get_db as _gdb
        with _gdb() as _c:
            ids_asist = [r[0] for r in _c.execute(
                "SELECT DISTINCT estudiante_id FROM asistencia WHERE profesor_id=?",
                (prof_id_est,)
            ).fetchall()]
            ids_calif = [r[0] for r in _c.execute(
                "SELECT DISTINCT estudiante_id FROM calificaciones_periodo WHERE profesor_id=?",
                (prof_id_est,)
            ).fetchall()]
        ids_prof = list(set(ids_asist + ids_calif))
        if ids_prof:
            est_query += " AND id IN (%s)" % ",".join("?" * len(ids_prof))
            est_params.extend(ids_prof)
        else:
            # Profesor sin registros aún — usar alcance de grado/mención como fallback
            alcance_est    = _resolver_alcance_profesor(u)
            grados_prof    = alcance_est["grados"]
            menciones_prof = alcance_est["menciones"]
            filtro_men_est = alcance_est["filtro_mencion"]
            if grados_prof:
                est_query += " AND (" + " OR ".join(["grado LIKE ?" for _ in grados_prof]) + ")"
                est_params.extend([f"%{g}%" for g in grados_prof])
            if filtro_men_est and menciones_prof:
                est_query += " AND (" + " OR ".join(["curso LIKE ?" for _ in menciones_prof]) + ")"
                est_params.extend([f"%{m}%" for m in menciones_prof])

    est_query += " ORDER BY grado, apellido, nombre"

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row

        estudiantes = [dict(r) for r in conn.execute(est_query, est_params).fetchall()]
        if not estudiantes:
            return jsonify({"estudiantes": [], "resumen": {}, "label": label})

        est_ids = [e["id"] for e in estudiantes]

        # ── Query de asistencia — solo registros de ESTE profesor ────
        prof_id = u.get("id")
        rol_norm = _normalizar_rol(u.get("rol", ""))
        roles_admin = {"directora", "coordinador_general", "coordinador_primer_ciclo",
                       "coordinador_segundo_ciclo"}

        asist_q = """
            SELECT estudiante_id,
                   SUM(CASE WHEN estado IN ('P','presente') THEN 1 ELSE 0 END) as presentes,
                   SUM(CASE WHEN estado IN ('A','ausente')  THEN 1 ELSE 0 END) as ausentes,
                   SUM(CASE WHEN estado IN ('T','tardanza') THEN 1 ELSE 0 END) as tardanzas,
                   COUNT(*) as total_registros
            FROM asistencia
            WHERE fecha BETWEEN ? AND ?
        """
        asist_params = [ini_str, fin_str]

        # Profesores solo ven lo que ELLOS registraron
        if rol_norm not in roles_admin:
            asist_q += " AND profesor_id=?"
            asist_params.append(prof_id)

        if materia:
            asist_q += " AND materia=?"
            asist_params.append(materia)
        asist_q += " AND estudiante_id IN (%s)" % ",".join("?" * len(est_ids))
        asist_params.extend(est_ids)
        asist_q += " GROUP BY estudiante_id"

        asist_map = {}
        try:
            for r in conn.execute(asist_q, asist_params).fetchall():
                asist_map[r["estudiante_id"]] = dict(r)
        except Exception as ex:
            logger.error(f"[estadisticas_asistencia] Error query: {ex}")

    # ── Calcular porcentajes ──────────────────────────────────────────
    resultado = []
    total_pct_sum = 0
    sobre_80 = 0; con_alerta = 0; en_riesgo = 0
    total_dias_max = 0

    for e in estudiantes:
        a = asist_map.get(e["id"], {})
        presentes  = a.get("presentes", 0) or 0
        ausentes   = a.get("ausentes", 0)  or 0
        tardanzas  = a.get("tardanzas", 0) or 0
        total_reg  = a.get("total_registros", 0) or 0

        # Tardanzas cuentan como 0.5 presencia
        efectivos = presentes + tardanzas * 0.5
        total_posible = presentes + ausentes + tardanzas
        pct = round(efectivos / total_posible * 100, 1) if total_posible > 0 else None

        if pct is not None:
            total_pct_sum += pct
            if pct >= 80: sobre_80 += 1
            elif pct >= 70: con_alerta += 1
            else: en_riesgo += 1

        if total_posible > total_dias_max:
            total_dias_max = total_posible

        resultado.append({
            "id":              e["id"],
            "nombre":          e["nombre"],
            "apellido":        e["apellido"],
            "grado":           e["grado"],
            "curso":           e["curso"],
            "seccion":         e.get("seccion", ""),
            "presentes":       presentes,
            "ausentes":        ausentes,
            "tardanzas":       tardanzas,
            "total_registros": total_reg,
            "pct_asistencia":  pct if pct is not None else "—",
        })

    # Ordenar: peor asistencia primero
    resultado.sort(key=lambda x: float(x["pct_asistencia"]) if isinstance(x["pct_asistencia"], (int, float)) else 999)

    total_con_datos = len([r for r in resultado if r["pct_asistencia"] != "—"])
    pct_promedio = round(total_pct_sum / total_con_datos, 1) if total_con_datos > 0 else 0

    return jsonify({
        "estudiantes": resultado,
        "label": label,
        "rango": {"inicio": ini_str, "fin": fin_str},
        "resumen": {
            "total_est":   len(resultado),
            "total_dias":  total_dias_max,
            "pct_promedio": pct_promedio,
            "sobre_80":    sobre_80,
            "con_alerta":  con_alerta,
            "en_riesgo":   en_riesgo,
            "label":       label,
        }
    })


# ══════════════════════════════════════════════════════════════════════════════
#  MÓDULO DE ASIGNACIONES — tareas, exámenes y proyectos por materia
#  Diferencia el tipo de evaluación según la materia y mención (CURRICULUM_ARTES)
#  y usa IA (Groq) para generar criterios de evaluación contextualizados.
# ══════════════════════════════════════════════════════════════════════════════


