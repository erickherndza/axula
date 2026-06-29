# -*- coding: utf-8 -*-
"""Blueprint: profesor"""

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
from core.helpers import _get_profesor, _render_perfil_staff, _resolver_alcance_profesor, _validar_materia_profesor
from core.ia import _get_groq_client, groq_client, construir_prompt, construir_prompt_planificacion, construir_prompt_rubrica, construir_prompt_estrategia
from core.excel import _parsear_boletin_bj, _buscar_o_crear_estudiante, _detectar_mencion_listado, _limpiar_nota
from core.pdf import _generar_pdf_acuerdo

logger = logging.getLogger("axula")

profesor_bp = Blueprint("profesor_bp", __name__)

@profesor_bp.route("/api/buscar-estudiantes")
@login_required
@rate_limited(max_calls=40, window=60)   # anti-enumeración
def buscar_estudiantes():
    q = request.args.get("q", "").strip()
    # Mínimo 2 chars, máximo 80 para evitar payloads largos
    if len(q) < 2 or len(q) > 80:
        return jsonify([])
    like = f"%{q}%"
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT id, nombre, apellido, grado, curso
            FROM estudiantes
            WHERE nombre LIKE ? OR apellido LIKE ?
               OR (nombre || ' ' || apellido) LIKE ?
            ORDER BY apellido, nombre LIMIT 12
        """, (like, like, like)).fetchall()
    return jsonify([dict(r) for r in rows])



# ══════════════════════════════════════════════════════════════════════════════
# HELPER DE BÚSQUEDA DE ESTUDIANTES — nivel módulo
# Usado por cargar_registro y cargar_boletin
# ══════════════════════════════════════════════════════════════════════════════


@profesor_bp.route("/api/profesor/mis-estudiantes")
@login_required
def mis_estudiantes():
    """
    Devuelve solo los estudiantes asignados al profesor logueado.
    Prioridad:
      1. Estudiantes con asistencia registrada por este profesor (calificaciones_periodo)
      2. Fallback: estudiantes en el alcance de grado/mención del profesor
    Nunca devuelve todos los estudiantes sin filtro.
    """
    u = get_usuario()
    prof_id = u.get("id")
    materia = u.get("materia", "")

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row

        # 1️⃣ IDs de estudiantes con notas registradas por este profesor
        ids_notas = [r[0] for r in conn.execute(
            "SELECT DISTINCT estudiante_id FROM calificaciones_periodo WHERE profesor_id=?",
            (prof_id,)
        ).fetchall()]

        # 2️⃣ IDs de estudiantes con asistencia registrada por este profesor
        ids_asist = [r[0] for r in conn.execute(
            "SELECT DISTINCT estudiante_id FROM asistencia WHERE profesor_id=?",
            (prof_id,)
        ).fetchall()]

        all_ids = list(set(ids_notas + ids_asist))

        if all_ids:
            placeholders = ",".join("?" * len(all_ids))
            rows = conn.execute(
                f"SELECT id,nombre,apellido,curso,grado,p_acad,puntualidad,participacion,"
                f"asistencia,indice_riesgo,nivel_riesgo FROM estudiantes "
                f"WHERE id IN ({placeholders}) ORDER BY apellido,nombre",
                all_ids
            ).fetchall()
        else:
            # Fallback: filtrar por alcance de grado/mención del profesor
            # (nunca devolver todos sin filtro)
            alcance = _resolver_alcance_profesor(u)
            grados  = alcance["grados"]
            menciones = alcance["menciones"]
            filtro_men = alcance["filtro_mencion"]

            q = ("SELECT id,nombre,apellido,curso,grado,p_acad,puntualidad,participacion,"
                 "asistencia,indice_riesgo,nivel_riesgo FROM estudiantes WHERE 1=1")
            params = []
            if grados:
                q += " AND (" + " OR ".join(["grado LIKE ?" for _ in grados]) + ")"
                params.extend([f"%{g}%" for g in grados])
            if filtro_men and menciones:
                q += " AND (" + " OR ".join(["curso LIKE ?" for _ in menciones]) + ")"
                params.extend([f"%{m}%" for m in menciones])
            q += " ORDER BY apellido, nombre"
            rows = conn.execute(q, params).fetchall()

        # Mapa de calificaciones del profesor en esta materia
        materias_map = {}
        mat_q = ("SELECT estudiante_id, materia, p1, p2, p3, p4, promedio "
                 "FROM materias_calificaciones WHERE 1=1")
        mat_p = []
        if materia:
            mat_q += " AND LOWER(materia) LIKE LOWER(?)"
            mat_p.append(f"%{materia}%")
        for r in conn.execute(mat_q, mat_p).fetchall():
            materias_map.setdefault(r[0], []).append(dict(r))

    result = []
    for r in rows:
        d = dict(r)
        d["materias"] = materias_map.get(d["id"], [])
        result.append(d)
    return jsonify(result)


# ── EXPORTAR REPORTES (Excel) ─────────────────────────────────────────────────


@profesor_bp.route("/api/plan-estudio")
@login_required
def plan_estudio():
    """Retorna el plan de estudio oficial MINERD para todas las menciones."""
    grado   = request.args.get("grado", "")
    mencion = request.args.get("mencion", "MULTIMEDIA").upper()
    plan    = PLAN_ARTES.get(mencion, PLAN_MULTIMEDIA)
    if grado and grado in plan:
        return jsonify({
            "grado": grado,
            "mencion": mencion,
            "asignaturas": [{"nombre": n, "horas_semana": h} for n, h in plan[grado]]
        })
    return jsonify({
        "mencion": mencion,
        "todos": {g: [{"nombre": n, "horas_semana": h} for n, h in lst]
                  for g, lst in plan.items()}
    })


# ── ASISTENCIA ─────────────────────────────────────────────────────────────


@profesor_bp.route("/api/validar-materia-profesor", methods=["POST"])
@login_required
def validar_materia_profesor():
    """
    Valida si una materia+curso es compatible con el perfil del profesor.
    Llamado ANTES de confirmar la carga.
    """
    prof = _get_profesor()
    d = request.get_json(silent=True) or {}
    nombre_materia = d.get("materia", "")
    nombre_curso   = d.get("curso", "")

    ok, msg = _validar_materia_profesor(nombre_materia, nombre_curso, prof)
    return jsonify({"ok": ok, "mensaje": msg})


# ── PORTAL PROFESOR (página) ─────────────────────────────────────────────────


# ═══════════════════════════════════════════════════════════════════════════════
#  HELPERS CALIFICACIONES
# ═══════════════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════════════
#  SISTEMA DE GESTIÓN DE CASOS — Helpers
# ═══════════════════════════════════════════════════════════════════════════════


@profesor_bp.route("/mi-perfil")
@login_required
def mi_perfil():
    """Perfil personal del usuario logueado — con timeline completo."""
    u = get_usuario()
    return _render_perfil_staff(u["id"], u)


@profesor_bp.route("/mi-perfil/editar", methods=["POST"])
@login_required
def editar_mi_perfil():
    """Permite al usuario editar sus propios datos no-críticos."""
    u  = get_usuario()
    d  = request.get_json(silent=True) or {}

    # Solo campos permitidos para auto-edición
    CAMPOS_EDITABLES = {"telefono", "bio", "titulo_academico", "departamento"}
    updates = {k: v for k, v in d.items() if k in CAMPOS_EDITABLES}

    if not updates:
        return jsonify({"error": "Nada que actualizar"}), 400

    sets   = ", ".join(f"{k}=?" for k in updates)
    valores = list(updates.values()) + [u["id"]]

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.execute(f"UPDATE usuarios SET {sets} WHERE id=?", valores)
        conn.commit()

    return jsonify({"ok": True})


@profesor_bp.route("/staff/<int:uid>")
@login_required
def ver_perfil_staff(uid):
    """Ver el perfil público de cualquier miembro del personal."""
    u = get_usuario()
    rol_n = _normalizar_rol(u["rol"])
    # SEGURIDAD: Solo directora y coordinador_general pueden ver perfiles de CUALQUIER usuario
    # Los coordinadores de ciclo solo pueden ver los de su ciclo
    # Nadie más puede ver el perfil de otro usuario
    puede_ver_ajeno = rol_n in ROLES_SUPER  # directora + coordinador_general
    if not puede_ver_ajeno and u["id"] != uid:
        return redirect("/mi-perfil")

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        staff = conn.execute("SELECT * FROM usuarios WHERE id=?", (uid,)).fetchone()
        if not staff:
            return redirect("/")
        staff = dict(staff)

    return _render_perfil_staff(uid, u)


@profesor_bp.route("/profesor")
@login_required
def portal_profesor():
    try:
      prof = _get_profesor()
      if not prof:
          return redirect("/")
      rol_norm = _normalizar_rol(prof.get("rol", ""))
      # Coordinadores/directora van al dashboard principal
      if rol_norm in ROLES_COORD:
          return redirect("/")

      # ── Resolver alcance real del profesor (multi-grado, nueva lógica) ──
      alcance        = _resolver_alcance_profesor(prof)
      grados_prof    = alcance["grados"]
      menciones_prof = alcance["menciones"]
      filtro_men     = alcance["filtro_mencion"]

      q = "SELECT id, nombre, apellido, curso, grado FROM estudiantes WHERE 1=1"
      params = []
      if grados_prof:
          q += " AND (" + " OR ".join(["grado LIKE ?" for _ in grados_prof]) + ")"
          params.extend([f"%{g}%" for g in grados_prof])
      if filtro_men and menciones_prof:
          q += " AND (" + " OR ".join(["curso LIKE ?" for _ in menciones_prof]) + ")"
          params.extend([f"%{m}%" for m in menciones_prof])
      q += " ORDER BY grado, apellido, nombre"

      with sqlite3.connect(DATABASE, timeout=10) as conn:
          conn.row_factory = sqlite3.Row
          estudiantes = [dict(r) for r in conn.execute(q, params).fetchall()]

      grado_key   = grados_prof[0].lower() if grados_prof else "4to"
      mencion_key = menciones_prof[0].upper() if (filtro_men and menciones_prof) else "MULTIMEDIA"
      plan_mencion = PLAN_ARTES.get(mencion_key, PLAN_MULTIMEDIA)
      plan = plan_mencion.get(grado_key, plan_mencion.get("4to", []))

      # Filtrar plan a solo las asignaturas que imparte el profesor
      asigs_prof = {a.strip() for a in (prof.get("asignaturas") or prof.get("materia") or "").split(",") if a.strip()}
      if asigs_prof and rol_norm == "profesor":
          plan = [(asig, horas) for asig, horas in plan if asig in asigs_prof]

      # Grados normalizados en mayúsculas para el selector del frontend
      grados_display = [g.upper() for g in grados_prof] if grados_prof else ["4TO", "5TO", "6TO"]

      from datetime import date as _date
      return render_template(
          "profesor.html",
          profesor=prof,
          estudiantes=estudiantes,
          plan=plan,
          grados_prof=grados_display,
          fecha_hoy=_date.today().isoformat(),
          current_user=get_usuario()
      )
    except Exception as _ep:
        import traceback as _tb
        err_detail = _tb.format_exc()
        logger.error(f"[portal_profesor] ERROR: {_ep}")
        logger.info(err_detail)
        # Return a minimal error page instead of silent redirect
        return f"""<html><body style='font-family:monospace;background:#111;color:#ef4444;padding:30px'>
            <h2>Error en Portal Profesor</h2>
            <pre style='color:#fca5a5;font-size:12px'>{_ep}</pre>
            <pre style='color:#555;font-size:11px'>{err_detail[:1000]}</pre>
            <a href='/' style='color:#c8f060'>← Volver al dashboard</a>
            </body></html>""", 500





# ══════════════════════════════════════════════════════════════════════════════
#  PARSER DE BOLETINES OFICIALES — C.E. BENITO JUÁREZ
#  Soporta:
#    - Boletín Primer Ciclo (1ro, 2do, 3ro): solo materias académicas, secciones A-E
#    - Boletín Segundo Ciclo (4to, 5to, 6to): académicas + técnicas por mención
#
#  Estructura del Excel (ambos ciclos):
#    - Una hoja por sección (1ro) o por mención-sección (4to)
#    - Cada estudiante ocupa un bloque de ~43 filas que se repite
#    - idx[2]='ALUMNO/A:', idx[6]=nombre completo del estudiante
#    - Académicas: idx[2]=materia, P1=idx[3], P2=idx[5], P3=idx[7], P4=idx[9]
#    - Técnicas:   idx[1]=materia, P1=idx[3], P2=idx[4]
# ══════════════════════════════════════════════════════════════════════════════


