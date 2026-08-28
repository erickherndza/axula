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
from core.importar_listado import leer_listado_workbook, construir_plan, aplicar_carga
import uuid
import openpyxl

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
            WHERE (nombre LIKE ? OR apellido LIKE ?
               OR (nombre || ' ' || apellido) LIKE ?)
              AND (condicion IS NULL OR condicion NOT IN ('RETIRADO','TRANSFERIDO'))
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
                f"WHERE id IN ({placeholders}) "
                f"AND (condicion IS NULL OR condicion NOT IN ('RETIRADO','TRANSFERIDO')) "
                f"ORDER BY apellido,nombre",
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
                 "asistencia,indice_riesgo,nivel_riesgo FROM estudiantes "
                 "WHERE (condicion IS NULL OR condicion NOT IN ('RETIRADO','TRANSFERIDO'))")
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
    CAMPOS_EDITABLES = {"telefono", "bio", "titulo_academico", "departamento", "materia", "grado"}
    updates = {k: v for k, v in d.items() if k in CAMPOS_EDITABLES}
    # Si se actualiza materia, limpiar asignaturas para que no tome precedencia
    if "materia" in updates:
        updates["asignaturas"] = None

    if not updates:
        return jsonify({"error": "Nada que actualizar"}), 400

    sets   = ", ".join(f"{k}=?" for k in updates)
    valores = list(updates.values()) + [u["id"]]

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.execute(f"UPDATE usuarios SET {sets} WHERE id=?", valores)
        conn.commit()

    # Refrescar sesión si cambió materia o grado (afecta filtro de estudiantes)
    if "materia" in updates:
        from flask import session as _sess
        _sess["materia"] = updates["materia"]
    if "grado" in updates:
        from flask import session as _sess
        _sess["grado"] = updates["grado"]

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

      q = ("SELECT id, nombre, apellido, curso, grado, seccion FROM estudiantes "
           "WHERE (condicion IS NULL OR condicion NOT IN ('RETIRADO','TRANSFERIDO'))")
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

      if not estudiantes:
          logger.warning(f"[portal_profesor] 0 estudiantes — uid={prof.get('id')} "
                         f"grado_db={prof.get('grado')!r} mencion_db={prof.get('mencion')!r} "
                         f"alcance={alcance} query={q!r} params={params}")

      # Plan: unión de todos los grados del profesor (multigrado)
      import unicodedata as _ud
      def _norm_asig(s):
          s = (s or "").strip().lower()
          return _ud.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")

      asigs_raw  = (prof.get("asignaturas") or prof.get("materia") or "").strip()
      asigs_prof = [_norm_asig(a) for a in asigs_raw.split("|") if a.strip()]

      def _coincide(nombre_plan):
          n = _norm_asig(nombre_plan)
          return any(ap in n or n in ap for ap in asigs_prof)

      # Plan por grado + modalidad (mención) — SIN aplanar: cada materia
      # conserva a qué grado(s) y modalidad(es) pertenece, para que Pase de
      # Lista pueda filtrar la matrícula exacta y no mezclar estudiantes de
      # grados/modalidades distintas que comparten profesor (ej: un profesor
      # técnico que imparte "Fotografía" en varias menciones, o una materia
      # académica repetida por grado como "Lengua Española" en 4to Y 5to).
      mencion_list = (menciones_prof if (filtro_men and menciones_prof) else ["MULTIMEDIA"])

      def _construir_plan(aplicar_filtro_asigs):
          ppgm = {}    # {grado: {mencion: [[asig,horas],...]}}
          pset = {}    # nombre_asig → horas (deduplicado, para vista "Plan de Estudio")
          for gk in (grados_prof if grados_prof else ["4to"]):
              ppgm[gk] = {}
              for mk in mencion_list:
                  plan_mencion = PLAN_ARTES.get(mk.upper(), PLAN_MULTIMEDIA)
                  materias_gkm = plan_mencion.get(gk.lower(), plan_mencion.get("4to", []))
                  if aplicar_filtro_asigs and asigs_prof and rol_norm == "profesor":
                      # Sin coincidencia en este grado+modalidad: no es materia
                      # de este profesor ahí (ej: técnica que solo existe en
                      # otra mención) — dejar la lista vacía en vez de mostrar
                      # el plan completo.
                      materias_gkm = [(a, h) for a, h in materias_gkm if _coincide(a)]
                  ppgm[gk][mk] = [[a, h] for a, h in materias_gkm]
                  for asig, horas in materias_gkm:
                      if asig not in pset:
                          pset[asig] = horas
          return ppgm, pset

      plan_por_grado_mencion, plan_set = _construir_plan(aplicar_filtro_asigs=True)
      plan = list(plan_set.items())

      if asigs_prof and rol_norm == "profesor" and not plan:
          # Ninguna combinación grado+modalidad tuvo coincidencia — avisar y
          # mostrar el plan completo sin filtrar (mismo fallback que antes)
          # para no dejar al profesor sin nada que seleccionar.
          logger.warning(
              f"[portal_profesor] Profesor id={prof.get('id')} — "
              f"asignaturas '{asigs_raw}' no coinciden con ningún grado/modalidad del plan. "
              "Se muestra el plan completo sin filtrar."
          )
          plan_por_grado_mencion, plan_set = _construir_plan(aplicar_filtro_asigs=False)
          plan = list(plan_set.items())

      from datetime import date as _date
      return render_template(
          "profesor.html",
          profesor=prof,
          estudiantes=estudiantes,
          plan=plan,
          plan_por_grado_mencion=plan_por_grado_mencion,
          grados_prof=grados_prof,
          menciones_prof=menciones_prof,
          filtro_men=filtro_men,
          fecha_hoy=_date.today().isoformat(),
          current_user=get_usuario()
      )
    except Exception as _ep:
        import traceback as _tb
        logger.error(f"[portal_profesor] ERROR: {_ep}\n{_tb.format_exc()}")
        # Página genérica — sin detalles internos al cliente
        return """<html><body style='font-family:sans-serif;background:#111;color:#ef4444;padding:30px'>
            <h2>Error en el Portal Docente</h2>
            <p style='color:#aaa'>Ocurrió un problema inesperado. Por favor contacta al administrador.</p>
            <a href='/' style='color:#60b8f0'>← Volver al dashboard</a>
            </body></html>""", 500


# ══════════════════════════════════════════════════════════════════════════════
#  LISTADO DE ESTUDIANTES (formato oficial "GRADO:"/"ÁREA:" — ver core/importar_listado.py)
#  Flujo preview → confirmar, igual que otras cargas masivas del sistema:
#  el navegador sube el .xlsx, el servidor arma un plan sin escribir en BD,
#  el profesor lo revisa y solo entonces confirma con un segundo POST.
# ══════════════════════════════════════════════════════════════════════════════

_LISTADO_PREVIEW_CACHE = {}
_LISTADO_PREVIEW_TTL = 900  # 15 minutos — tiempo de sobra para revisar el preview


def _limpiar_previews_vencidos():
    ahora = _time.time()
    vencidos = [t for t, e in _LISTADO_PREVIEW_CACHE.items() if ahora - e["ts"] > _LISTADO_PREVIEW_TTL]
    for t in vencidos:
        _LISTADO_PREVIEW_CACHE.pop(t, None)


@profesor_bp.route("/api/profesor/preview-listado-estudiantes", methods=["POST"])
@login_required
@rate_limited(max_calls=10, window=3600)
def preview_listado_estudiantes():
    """Lee el Excel subido y arma el plan de carga SIN escribir en BD."""
    if "file" not in request.files:
        return jsonify({"error": "No se recibió archivo"}), 400
    file = request.files["file"]
    if not file.filename.lower().endswith((".xlsx", ".xls", ".xlsm")):
        return jsonify({"error": "Formato no válido. Sube el archivo .xlsx del listado"}), 400

    try:
        wb = openpyxl.load_workbook(BytesIO(file.read()), data_only=True)
        grado, seccion, mencion, alumnos = leer_listado_workbook(wb)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"[preview_listado_estudiantes] error leyendo archivo: {e}")
        return jsonify({"error": "No se pudo leer el archivo. Verifica que sea el listado oficial."}), 400

    if not alumnos:
        return jsonify({"error": "No se encontraron filas de alumnos en el archivo."}), 400

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        curso, ciclo, plan = construir_plan(conn, grado, seccion, mencion, alumnos)

    _limpiar_previews_vencidos()
    token = uuid.uuid4().hex
    _LISTADO_PREVIEW_CACHE[token] = {
        "grado": grado, "seccion": seccion, "mencion": mencion, "alumnos": alumnos,
        "ts": _time.time(), "user_id": session.get("user_id"),
    }

    return jsonify({
        "ok": True, "token": token,
        "grado": grado, "seccion": seccion, "mencion": mencion, "curso": curso,
        "total": len(alumnos),
        "nuevos": sum(1 for p in plan if p["accion"] == "nuevo"),
        "actualizados": sum(1 for p in plan if p["accion"] == "actualiza"),
        "plan": plan,
    })


@profesor_bp.route("/api/profesor/confirmar-listado-estudiantes", methods=["POST"])
@login_required
@rate_limited(max_calls=10, window=3600)
def confirmar_listado_estudiantes():
    """Aplica un plan previamente generado por /preview-listado-estudiantes."""
    d = request.get_json(silent=True) or {}
    token = d.get("token", "")
    _limpiar_previews_vencidos()
    entry = _LISTADO_PREVIEW_CACHE.pop(token, None)
    if not entry:
        return jsonify({"error": "La vista previa expiró o no existe. Vuelve a subir el archivo."}), 400
    if entry["user_id"] != session.get("user_id"):
        return jsonify({"error": "Esta vista previa pertenece a otra sesión."}), 403

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        nuevos, actualizados = aplicar_carga(
            conn, entry["grado"], entry["seccion"], entry["mencion"], entry["alumnos"]
        )

    cache_bust()  # el roster cambió — invalida cachés de listados/dashboard
    return jsonify({"ok": True, "nuevos": nuevos, "actualizados": actualizados})



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


