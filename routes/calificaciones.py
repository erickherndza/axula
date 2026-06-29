# -*- coding: utf-8 -*-
"""Blueprint: calificaciones"""

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
from core import rls as _rls
from core.auth import (
    _hash, _check_password, _normalizar_rol, _ciclo_del_rol,
    login_required, coord_required, admin_required, directora_required,
    _csrf_token, _csrf_check, csrf_protected, rate_limited,
    get_usuario,
)
from core.helpers import *
from core.helpers import _anio_escolar_actual, _audit, _calcular_nota_final_con_recuperacion, _color_nota, _get_config_centro, _get_profesor, _nota_estado, _nota_requiere_recuperacion, _notificar, _periodo_actual, _periodo_bloqueado
from core import grades as G
from core.ia import _get_groq_client, groq_client, construir_prompt, construir_prompt_planificacion, construir_prompt_rubrica, construir_prompt_estrategia
from core.excel import _parsear_boletin_bj, _buscar_o_crear_estudiante, _detectar_mencion_listado, _limpiar_nota
from core.pdf import _generar_pdf_acuerdo

logger = logging.getLogger("axula")

calificaciones_bp = Blueprint("calificaciones_bp", __name__)

@calificaciones_bp.route("/api/calificaciones", methods=["GET"])
@login_required
def listar_calificaciones():
    """
    Lista calificaciones con filtros opcionales.
    Profesores ven solo las que ellos registraron.
    Coordinadores de ciclo ven solo su ciclo (RLS).
    ?estudiante_id=  &materia=  &periodo=  &anio=
    """
    prof = _get_profesor()
    est_id  = request.args.get("estudiante_id", "")
    materia = request.args.get("materia", "")
    periodo = request.args.get("periodo", "")
    anio    = request.args.get("anio", "")

    q = """
        SELECT cp.*, e.nombre, e.apellido, e.curso, e.grado,
               u.nombre AS profesor_nombre
        FROM calificaciones_periodo cp
        JOIN estudiantes e ON e.id = cp.estudiante_id
        JOIN usuarios u    ON u.id = cp.profesor_id
        WHERE 1=1
    """
    params = []

    # RLS: filtro por ciclo del coordinador
    rls_sql, rls_params = _rls.sql_filtro_grado(alias="e")
    q += rls_sql; params.extend(rls_params)

    if prof and prof.get("rol") == "profesor":
        q += " AND cp.profesor_id=?"; params.append(prof["id"])

    if est_id:  q += " AND cp.estudiante_id=?"; params.append(int(est_id))
    if materia: q += " AND cp.materia=?";        params.append(materia)
    if periodo: q += " AND cp.periodo=?";        params.append(periodo)
    if anio:    q += " AND cp.anio_escolar=?";   params.append(anio)
    else:       q += " AND cp.anio_escolar=?";   params.append(_anio_escolar_actual())

    q += " ORDER BY e.apellido, cp.materia, cp.periodo"

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(q, params).fetchall()

    return jsonify([dict(r) for r in rows])


@calificaciones_bp.route("/api/calificaciones", methods=["POST"])
@login_required
@rate_limited(max_calls=60, window=60)
def registrar_calificacion():
    """
    Registra o actualiza la nota de un período.
    UPSERT por (estudiante_id + materia + periodo + anio_escolar).
    Body: {estudiante_id, materia, periodo, calificacion, observacion?, anio_escolar?}
    Puede recibir una lista (batch) o un objeto único.
    """
    prof = _get_profesor()
    if not prof:
        return jsonify({"error": "No autenticado"}), 401

    # Profesores no pueden modificar períodos bloqueados
    # Coordinadores y directora sí pueden (ignoran el bloqueo)
    rol_n_prof = _normalizar_rol(prof.get("rol", ""))
    es_privilegiado = (rol_n_prof in ROLES_COORD or prof.get("es_directora") or
                       rol_n_prof in ROLES_SUPER)

    data = request.get_json(silent=True) or {}

    # Soporte batch (lista) o single (objeto)
    registros = data if isinstance(data, list) else [data]

    prof_id = prof["id"]
    anio    = _anio_escolar_actual()
    guardados = 0
    errores   = []

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        for item in registros:
            est_id  = item.get("estudiante_id")
            materia = (item.get("materia") or "").strip()
            periodo = (item.get("periodo") or "").strip().upper()
            nota    = item.get("calificacion")
            obs     = item.get("observacion", "")
            item_anio = item.get("anio_escolar") or anio

            if not est_id or not materia or not periodo or nota is None:
                errores.append(f"Datos incompletos: {item}")
                continue

            # ── Verificar si el período está bloqueado ────────────────────
            if not es_privilegiado and _periodo_bloqueado(periodo, item_anio):
                errores.append(
                    f"Período {periodo} está cerrado. "
                    f"Contacta al coordinador para modificar calificaciones."
                )
                continue

            # Validar rango
            try:
                nota = float(nota)
                if nota < 0 or nota > 100:
                    raise ValueError
            except (ValueError, TypeError):
                errores.append(f"Calificación inválida ({nota}) para est {est_id}")
                continue

            # Validar período
            if periodo not in ("P1", "P2", "P3", "P4"):
                errores.append(f"Período inválido: {periodo}")
                continue

            existing = conn.execute(
                "SELECT id, calificacion FROM calificaciones_periodo "
                "WHERE estudiante_id=? AND materia=? AND periodo=? AND anio_escolar=?",
                (est_id, materia, periodo, item_anio)
            ).fetchone()

            nota_anterior = existing[1] if existing else None

            if existing:
                conn.execute(
                    "UPDATE calificaciones_periodo "
                    "SET calificacion=?, observacion=?, profesor_id=?, actualizado=datetime('now') "
                    "WHERE id=?",
                    (nota, obs, prof_id, existing[0])
                )
            else:
                conn.execute(
                    "INSERT INTO calificaciones_periodo "
                    "(estudiante_id,profesor_id,materia,periodo,calificacion,anio_escolar,observacion) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (est_id, prof_id, materia, periodo, nota, item_anio, obs)
                )
            guardados += 1

            # Audit
            accion_txt = "actualizar_nota" if existing else "registrar_nota"
            desc = f"{materia} {periodo} ({item_anio}): {nota_anterior} → {nota}" if existing else f"{materia} {periodo} ({item_anio}): {nota}"
            _audit(accion_txt, desc, "calificaciones_periodo", est_id,
                   {"nota": nota_anterior} if existing else None,
                   {"nota": nota, "materia": materia, "periodo": periodo})

            # Notificar si la nota está en EP o I (< 70)
            if nota < 70:
                with sqlite3.connect(DATABASE, timeout=5) as _nc:
                    _nc.row_factory = sqlite3.Row
                    _est_n = _nc.execute(
                        "SELECT nombre, apellido FROM estudiantes WHERE id=?", (est_id,)
                    ).fetchone()
                if _est_n:
                    nivel = "En proceso (EP)" if nota >= 60 else "Insuficiente (I)"
                    _notificar(
                        "riesgo_nota",
                        f"⚠ Nota en riesgo — {_est_n['nombre']} {_est_n['apellido']}",
                        f"{materia} {periodo}: {nota} · Nivel {nivel}. Requiere atención.",
                        url=f"/perfil/{est_id}"
                    )

        conn.commit()

    return jsonify({"ok": True, "guardados": guardados, "errores": errores})


@calificaciones_bp.route("/api/calificaciones/resumen/<int:est_id>")
@login_required
def resumen_calificaciones(est_id):
    """
    Devuelve nota por período (P1-P4) y calcula:
    - Nota final anual = promedio de los períodos disponibles
    - Nota semestral 1er = (P1+P2)/2, 2do = (P3+P4)/2
    - Estado: aprobado / completiva / reprobado / sin_nota
    - Incluye también resumen de asistencia MINERD por materia
    RLS: verifica que el usuario puede ver este estudiante.
    """
    anio = request.args.get("anio", _anio_escolar_actual())

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        _rls.verificar_acceso_estudiante(conn, est_id)  # RLS — 403 si no tiene permiso

        # BUG FIX: mat_rows faltaba — cargar desde materias_calificaciones
        mat_rows = conn.execute(
            "SELECT materia, p1, p2, p3, p4, promedio, tipo "
            "FROM materias_calificaciones "
            "WHERE estudiante_id=? "
            "ORDER BY materia",
            (est_id,)
        ).fetchall()

        # Notas manuales (mayor prioridad)
        notas_rows = conn.execute(
            "SELECT materia, periodo, calificacion, observacion, profesor_id, actualizado "
            "FROM calificaciones_periodo "
            "WHERE estudiante_id=? AND anio_escolar=? "
            "ORDER BY materia, periodo",
            (est_id, anio)
        ).fetchall()

        # Asistencia MINERD
        asist_rows = conn.execute("""
            SELECT materia, periodo,
                   SUM(horas_clase) AS horas_total,
                   SUM(CASE WHEN estado IN ('P','presente') THEN horas_clase ELSE 0 END) AS horas_presente,
                   SUM(CASE WHEN estado IN ('J','justificado') THEN horas_clase ELSE 0 END) AS horas_justif,
                   SUM(CASE WHEN estado IN ('A','ausente') THEN horas_clase ELSE 0 END) AS horas_ausente,
                   SUM(CASE WHEN estado IN ('T','tardanza') THEN horas_clase * 0.5 ELSE 0 END) AS horas_tardanza_peso
            FROM asistencia
            WHERE estudiante_id=?
            GROUP BY materia, periodo
        """, (est_id,)).fetchall()

    # Organizar notas por materia — clave normalizada para deduplicar variantes de capitalización
    from collections import defaultdict
    from routes.estudiantes import _normalizar_clave_materia as _mat_clave

    def _nombre_display(existente, nuevo):
        # Prefiere Proper Case sobre TODO MAYÚSCULAS, o el nombre más largo si ambos son uppercase
        if existente == existente.upper() and nuevo != nuevo.upper():
            return nuevo
        if existente == existente.upper() and len(nuevo) > len(existente):
            return nuevo
        return existente

    # clave_a_nombre: mapea clave_norm → nombre de display preferido
    clave_a_nombre = {}
    materias = defaultdict(lambda: {"P1": None, "P2": None, "P3": None, "P4": None, "tipo": "académico"})

    # Primero: datos del boletín Excel (fuente base)
    for r in mat_rows:
        mat_name = r["materia"]
        clave = _mat_clave(mat_name)
        if clave not in clave_a_nombre:
            clave_a_nombre[clave] = mat_name
        else:
            clave_a_nombre[clave] = _nombre_display(clave_a_nombre[clave], mat_name)
        materias[clave]["tipo"] = r["tipo"] or "académico"
        if r["p1"] is not None and r["p1"] > 0: materias[clave]["P1"] = r["p1"]
        if r["p2"] is not None and r["p2"] > 0: materias[clave]["P2"] = r["p2"]
        if r["p3"] is not None and r["p3"] > 0: materias[clave]["P3"] = r["p3"]
        if r["p4"] is not None and r["p4"] > 0: materias[clave]["P4"] = r["p4"]

    # Then: overlay with calificaciones_periodo (manual entry — higher priority)
    for r in notas_rows:
        clave = _mat_clave(r["materia"])
        if clave not in clave_a_nombre:
            clave_a_nombre[clave] = r["materia"]
        materias[clave][r["periodo"]] = r["calificacion"]

    # Organizar asistencia por materia (acumular todos los períodos, clave normalizada)
    asist_por_materia = defaultdict(lambda: {"horas_total": 0, "horas_ausente": 0, "horas_tardanza_peso": 0})
    for r in asist_rows:
        clave = _mat_clave(r["materia"])
        asist_por_materia[clave]["horas_total"]          += (r["horas_total"] or 0)
        asist_por_materia[clave]["horas_ausente"]         += (r["horas_ausente"] or 0)
        asist_por_materia[clave]["horas_tardanza_peso"]   += (r["horas_tardanza_peso"] or 0)

    resultado = []
    for clave, periodos in materias.items():
        materia = clave_a_nombre.get(clave, clave)
        # ── grades.py: única fuente de verdad ──
        nota_final  = G.promedio_periodos(
            periodos.get("P1"), periodos.get("P2"),
            periodos.get("P3"), periodos.get("P4")
        )
        s1 = G.semestre(periodos.get("P1"), periodos.get("P2"))
        s2 = G.semestre(periodos.get("P3"), periodos.get("P4"))

        ai = asist_por_materia.get(clave, {})
        pct_inasist = G.calcular_pct_inasistencia(
            ai.get("horas_ausente", 0),
            ai.get("horas_tardanza_peso", 0),
            ai.get("horas_total", 0),
        )
        em = G.estado_materia(nota_final, pct_inasist)

        resultado.append({
            "materia":           materia,
            "anio_escolar":      anio,
            "periodos":          periodos,
            "nota_final":        nota_final,
            "semestre_1":        s1,
            "semestre_2":        s2,
            "estado":            em["estado"],
            "color":             em["color"],
            "periodos_con_nota": len([v for v in [periodos.get(p) for p in ("P1","P2","P3","P4")] if v is not None]),
            "pct_inasistencia":  pct_inasist,
            "reprueba_asistencia": em["reprueba_asistencia"],
            "alerta_asistencia":   em["alerta_asistencia"],
        })

    resultado.sort(key=lambda x: x["materia"])

    # Profesores solo ven sus propias asignaturas
    prof = _get_profesor()
    if prof and _normalizar_rol(prof.get("rol", "")) == "profesor":
        from routes.estudiantes import _normalizar_clave_materia as _nc
        asigs_raw = (prof.get("asignaturas") or prof.get("materia") or "").strip()
        asigs = {_nc(a) for a in asigs_raw.split(",") if a.strip()}
        if asigs:
            resultado = [r for r in resultado if _nc(r["materia"]) in asigs]

    return jsonify({
        "estudiante_id": est_id,
        "anio_escolar":  anio,
        "materias":      resultado,
        "periodo_actual": _periodo_actual(),
        "total_materias": len(resultado),
        "materias_riesgo": sum(1 for m in resultado if m["reprueba_asistencia"] or m["estado"] in ("en_proceso","insuficiente")),
    })


@calificaciones_bp.route("/api/calificaciones/reporte-grupo")
@login_required
def reporte_grupo_calificaciones():
    """
    Reporte de grupo: todas las notas de un grado/mención por período.
    Solo coordinadores o profesores de ese grado.
    ?grado= &mencion= &periodo= &anio=
    """
    grado   = request.args.get("grado", "").strip()
    mencion = request.args.get("mencion", "").upper().strip()
    periodo = request.args.get("periodo", "").strip().upper()
    anio    = request.args.get("anio", _anio_escolar_actual())

    prof = _get_profesor()
    # Profesores solo ven su grado
    if prof and prof.get("rol") == "profesor":
        if grado and prof.get("grado") and grado.lower() not in prof.get("grado","").lower():
            return jsonify({"error": "Sin permisos para ese grado"}), 403

    q = """
        SELECT e.id, e.nombre, e.apellido, e.curso, e.grado,
               cp.materia, cp.periodo, cp.calificacion
        FROM calificaciones_periodo cp
        JOIN estudiantes e ON e.id = cp.estudiante_id
        WHERE cp.anio_escolar=?
    """
    params = [anio]

    if grado:
        q += " AND (e.grado LIKE ? OR e.curso LIKE ?)"; params += [f"%{grado}%", f"%{grado}%"]
    if mencion:
        q += " AND UPPER(e.curso) LIKE ?"; params.append(f"%{mencion}%")
    if periodo:
        q += " AND cp.periodo=?"; params.append(periodo)

    q += " ORDER BY e.apellido, e.nombre, cp.materia, cp.periodo"

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(q, params).fetchall()

    # Pivot: {estudiante: {materia: {periodo: nota}}}
    from collections import defaultdict
    pivot = defaultdict(lambda: defaultdict(dict))
    info_est = {}

    for r in rows:
        eid = r["id"]
        info_est[eid] = {
            "id": eid, "nombre": r["nombre"], "apellido": r["apellido"],
            "curso": r["curso"], "grado": r["grado"]
        }
        pivot[eid][r["materia"]][r["periodo"]] = r["calificacion"]

    resultado = []
    for eid, materias_dict in pivot.items():
        notas_est = []
        for materia, periodos in materias_dict.items():
            nota_final = G.promedio_periodos(
                periodos.get("P1"), periodos.get("P2"),
                periodos.get("P3"), periodos.get("P4")
            )
            notas_est.append({
                "materia": materia,
                "periodos": periodos,
                "nota_final": nota_final,
                "estado": G.clasificar_nota(nota_final),
                "color":  G.color_nota(nota_final),
            })
        resultado.append({
            "estudiante": info_est[eid],
            "notas": notas_est
        })

    resultado.sort(key=lambda x: x["estudiante"]["apellido"])
    return jsonify({
        "anio_escolar": anio,
        "grado": grado, "mencion": mencion, "periodo_filtro": periodo,
        "total_estudiantes": len(resultado),
        "estudiantes": resultado
    })


# ══════════════════════════════════════════════════════════════════════════════
#  RECUPERACIONES PEDAGÓGICAS — Ordenanza 04-2023 Art.28
#  Gestiona los 3 niveles de recuperación:
#    1. Recuperación Pedagógica (actividades complementarias, nota < 70)
#    2. Evaluación Completiva   (50% nota_final + 50% completiva)
#    3. Evaluación Extraordinaria (antes del nuevo año escolar)
# ══════════════════════════════════════════════════════════════════════════════


@calificaciones_bp.route("/api/recuperaciones/<int:est_id>", methods=["GET"])
@login_required
def get_recuperaciones(est_id):
    """Devuelve todas las recuperaciones del estudiante para el año escolar."""
    anio = request.args.get("anio", _anio_escolar_actual())
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        _rls.verificar_acceso_estudiante(conn, est_id)
        rows = conn.execute(
            """SELECT * FROM recuperaciones_pedagogicas
               WHERE estudiante_id=? AND anio_escolar=?
               ORDER BY materia""",
            (est_id, anio)
        ).fetchall()
    return jsonify({"ok": True, "recuperaciones": [dict(r) for r in rows], "anio_escolar": anio})


@calificaciones_bp.route("/api/recuperaciones", methods=["POST"])
@login_required
def guardar_recuperacion():
    """
    Guarda o actualiza la recuperación pedagógica de un estudiante en una materia.
    Body: {
        estudiante_id, materia, anio_escolar?,
        nota_recuperacion?,    -- 1ra oportunidad (prof ingresa directamente)
        nota_completiva?,      -- evaluación completiva (50/50 con nota_final)
        nota_extraordinaria?,  -- evaluación extraordinaria
        nota_base?,            -- nota_final del período (para calcular ajustada)
        observacion?
    }
    """
    u = get_usuario()
    d = request.get_json(force=True) or {}

    est_id  = d.get("estudiante_id")
    materia = (d.get("materia") or "").strip()
    anio    = (d.get("anio_escolar") or _anio_escolar_actual()).strip()
    nota_r  = d.get("nota_recuperacion")
    nota_c  = d.get("nota_completiva")
    nota_e  = d.get("nota_extraordinaria")
    nota_base = d.get("nota_base")  # nota promedio P1-P4
    obs     = (d.get("observacion") or "").strip() or None

    if not est_id or not materia:
        return jsonify({"ok": False, "error": "estudiante_id y materia requeridos"}), 400

    # Convertir a float si vienen
    def _f(v):
        try:
            return round(float(v), 1) if v is not None and v != "" else None
        except (ValueError, TypeError):
            return None

    nota_r = _f(nota_r)
    nota_c = _f(nota_c)
    nota_e = _f(nota_e)
    nota_base = _f(nota_base)

    # Calcular nota_final_ajustada según el nivel más alto disponible
    # Prioridad: extraordinaria > completiva > recuperacion > base
    nota_final_ajustada = nota_base
    if nota_c is not None and nota_base is not None:
        nota_final_ajustada = _calcular_nota_final_con_recuperacion(nota_base, nota_c)
    elif nota_r is not None and nota_r > (nota_base or 0):
        nota_final_ajustada = nota_r  # recuperación mejora la nota si es mayor
    if nota_e is not None:
        nota_final_ajustada = nota_e  # extraordinaria es la nota definitiva

    if nota_final_ajustada is not None:
        nota_final_ajustada = round(nota_final_ajustada, 1)

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.execute(
            """INSERT INTO recuperaciones_pedagogicas
               (estudiante_id, materia, anio_escolar, nota_recuperacion, nota_completiva,
                nota_extraordinaria, nota_final_ajustada, observacion, registrado_por, actualizado)
               VALUES (?,?,?,?,?,?,?,?,?,datetime('now'))
               ON CONFLICT(estudiante_id, materia, anio_escolar)
               DO UPDATE SET
                 nota_recuperacion   = COALESCE(excluded.nota_recuperacion, nota_recuperacion),
                 nota_completiva     = COALESCE(excluded.nota_completiva, nota_completiva),
                 nota_extraordinaria = COALESCE(excluded.nota_extraordinaria, nota_extraordinaria),
                 nota_final_ajustada = excluded.nota_final_ajustada,
                 observacion         = COALESCE(excluded.observacion, observacion),
                 registrado_por      = excluded.registrado_por,
                 actualizado         = datetime('now')""",
            (est_id, materia, anio, nota_r, nota_c, nota_e,
             nota_final_ajustada, obs, u["id"])
        )

    _audit("recuperacion", f"{materia} ({anio}) → ajustada: {nota_final_ajustada}",
           "recuperaciones_pedagogicas", est_id,
           None, {"materia": materia, "nota_r": nota_r, "nota_c": nota_c,
                  "nota_e": nota_e, "ajustada": nota_final_ajustada})

    return jsonify({"ok": True, "nota_final_ajustada": nota_final_ajustada})


@calificaciones_bp.route("/api/calificaciones/boletin/<int:est_id>")
@login_required
def boletin_estudiante(est_id):
    """
    Boletín completo del estudiante: notas + asistencia + recuperaciones.
    Incluye estado final, alertas MINERD y datos del estudiante.
    RLS: coordi de ciclo solo ven su ciclo; padres solo sus hijos.
    """
    anio = request.args.get("anio", _anio_escolar_actual())

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        _rls.verificar_acceso_estudiante(conn, est_id)
        est = conn.execute(
            "SELECT * FROM estudiantes WHERE id=?", (est_id,)
        ).fetchone()

    if not est:
        return jsonify({"error": "Estudiante no encontrado"}), 404

    # Llamar directamente la lógica
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row

        # Notas manuales (calificaciones_periodo)
        notas_rows = conn.execute(
            "SELECT materia, periodo, calificacion FROM calificaciones_periodo "
            "WHERE estudiante_id=? AND anio_escolar=? ORDER BY materia, periodo",
            (est_id, anio)
        ).fetchall()

        # Notas del boletín Excel (materias_calificaciones)
        mat_rows = conn.execute(
            """SELECT materia, tipo,
                      CASE WHEN p1>0 THEN p1 ELSE NULL END as p1,
                      CASE WHEN p2>0 THEN p2 ELSE NULL END as p2,
                      CASE WHEN p3>0 THEN p3 ELSE NULL END as p3,
                      CASE WHEN p4>0 THEN p4 ELSE NULL END as p4
               FROM materias_calificaciones
               WHERE estudiante_id=? ORDER BY materia""",
            (est_id,)
        ).fetchall()

        # Recuperaciones pedagógicas
        recup_rows = conn.execute(
            """SELECT materia, nota_recuperacion, nota_completiva,
                      nota_extraordinaria, nota_final_ajustada, observacion
               FROM recuperaciones_pedagogicas
               WHERE estudiante_id=? AND anio_escolar=?""",
            (est_id, anio)
        ).fetchall()

        asist_rows = conn.execute("""
            SELECT materia,
                   SUM(horas_clase) AS ht,
                   SUM(CASE WHEN estado IN ('A','ausente') THEN horas_clase ELSE 0 END) AS ha,
                   SUM(CASE WHEN estado IN ('T','tardanza') THEN horas_clase*0.5 ELSE 0 END) AS ht_peso,
                   SUM(CASE WHEN estado IN ('P','presente') THEN 1 ELSE 0 END) AS dias_presentes,
                   COUNT(*) AS total_dias
            FROM asistencia
            WHERE estudiante_id=?
            GROUP BY materia
        """, (est_id,)).fetchall()

    from collections import defaultdict
    # Map de nombres normalizados → nombre canónico (preserva el primero que aparece)
    _canonico = {}
    def _norm(nombre):
        """Normaliza un nombre de materia para comparación case/space-insensitive."""
        return (nombre or "").strip().lower().replace("  ", " ")

    materias = defaultdict(lambda: {"P1": None, "P2": None, "P3": None, "P4": None, "tipo": "académico"})

    # Cargar desde materias_calificaciones (boletín Excel)
    for r in mat_rows:
        key = _norm(r["materia"])
        if key not in _canonico:
            _canonico[key] = r["materia"]
        canon = _canonico[key]
        if r["p1"] is not None: materias[canon]["P1"] = r["p1"]
        if r["p2"] is not None: materias[canon]["P2"] = r["p2"]
        if r["p3"] is not None: materias[canon]["P3"] = r["p3"]
        if r["p4"] is not None: materias[canon]["P4"] = r["p4"]
        materias[canon]["tipo"] = r["tipo"] or "académico"

    # Overlay con calificaciones_periodo (entrada manual — prioridad mayor)
    for r in notas_rows:
        key = _norm(r["materia"])
        if key not in _canonico:
            _canonico[key] = r["materia"]
        canon = _canonico[key]
        materias[canon][r["periodo"]] = r["calificacion"]

    # Indexar recuperaciones por materia
    recup_map = {r["materia"]: dict(r) for r in recup_rows}

    asist_m = {}
    for r in asist_rows:
        ht = r["ht"] or 0
        ha_total = (r["ha"] or 0) + (r["ht_peso"] or 0)
        asist_m[r["materia"]] = {
            "horas_total": ht,
            "pct_inasist": round(ha_total / ht * 100, 1) if ht > 0 else 0,
            "dias_presentes": r["dias_presentes"],
            "total_dias": r["total_dias"],
        }

    boletin_materias = []
    for materia, periodos in materias.items():
        nota_final_base = G.promedio_periodos(
            periodos.get("P1"), periodos.get("P2"),
            periodos.get("P3"), periodos.get("P4")
        )

        # Aplicar recuperación si existe
        recup = recup_map.get(materia, {})
        nota_recuperacion   = recup.get("nota_recuperacion")
        nota_completiva     = recup.get("nota_completiva")
        nota_extraordinaria = recup.get("nota_extraordinaria")
        nota_final_ajustada = recup.get("nota_final_ajustada")

        # La nota final definitiva usa ajustada si existe, si no usa la base
        nota_final = nota_final_ajustada if nota_final_ajustada is not None else nota_final_base

        ai = asist_m.get(materia, {"pct_inasist": 0, "horas_total": 0})
        requiere_recup = _nota_requiere_recuperacion(nota_final_base)

        boletin_materias.append({
            "materia":                   materia,
            "tipo":                      periodos.get("tipo", "académico"),
            "P1": periodos["P1"], "P2": periodos["P2"],
            "P3": periodos["P3"], "P4": periodos["P4"],
            "p1": periodos["P1"], "p2": periodos["P2"],
            "p3": periodos["P3"], "p4": periodos["P4"],
            "nota_final_base":           nota_final_base,
            "nota_recuperacion":         nota_recuperacion,
            "nota_completiva":           nota_completiva,
            "nota_extraordinaria":       nota_extraordinaria,
            "nota_final_ajustada":       nota_final_ajustada,
            "nota_final":                nota_final,
            "promedio":                  nota_final,
            "requiere_recuperacion":     requiere_recup,
            "estado":                    _nota_estado(nota_final),
            "estado_base":               _nota_estado(nota_final_base),
            "recup_observacion":         recup.get("observacion"),
            "pct_inasistencia":          ai["pct_inasist"],
            "pct_inasistencia_injustificada": ai["pct_inasist"],
            "reprueba_asistencia":       ai["pct_inasist"] >= 20,
            "alerta_asistencia":         ai["pct_inasist"] >= 15,
        })

    boletin_materias.sort(key=lambda x: x["materia"])

    # Conteos con escala Ord.04-2023
    aprobadas    = sum(1 for m in boletin_materias if m["estado"] in ("destacado","satisfactorio","basico"))
    en_proceso   = sum(1 for m in boletin_materias if m["estado"] == "en_proceso")
    insuficientes= sum(1 for m in boletin_materias if m["estado"] == "insuficiente")
    con_asist    = sum(1 for m in boletin_materias if m["reprueba_asistencia"])
    # Materias en riesgo (insuficiente O reprueba asistencia)
    en_riesgo    = sum(1 for m in boletin_materias if m["estado"] == "insuficiente" or m["reprueba_asistencia"])

    return jsonify({
        "estudiante":    dict(est),
        "anio_escolar":  anio,
        "periodo_actual": _periodo_actual(),
        "materias":      boletin_materias,
        "resumen": {
            "total_materias":  len(boletin_materias),
            "aprobadas":       aprobadas,
            "en_proceso":      en_proceso,
            "insuficientes":   insuficientes,
            "con_asistencia":  con_asist,
            "en_riesgo":       en_riesgo,
            # Compatibilidad con código anterior
            "completivas":     en_proceso,
            "reprobadas":      en_riesgo,
            "promueve":        en_riesgo < 4,
            "repite":          en_riesgo >= 4,
        }
    })


# ══════════════════════════════════════════════════════════════════════════════
# SISTEMA DE GESTIÓN DE CASOS — Alertas, Notificaciones, Casos, Acuerdos
# ══════════════════════════════════════════════════════════════════════════════


@calificaciones_bp.route("/boletin/<int:est_id>")
@login_required
def boletin_view(est_id):
    """
    Página de boletín imprimible — solo coordinadores y directora.
    Genera la hoja horizontal con todas las calificaciones del estudiante
    según el formato oficial MINERD del C.E. Benito Juárez.
    """
    u = get_usuario()
    rol_n = _normalizar_rol(u.get("rol", ""))
    if rol_n not in ROLES_COORD and not u.get("es_directora"):
        return redirect(f"/perfil/{est_id}")

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        _rls.verificar_acceso_estudiante(conn, est_id)  # RLS ciclo
        est = conn.execute("SELECT * FROM estudiantes WHERE id=?", (est_id,)).fetchone()
        if not est:
            return "Estudiante no encontrado", 404
        e = dict(est)

        # ── Completar notas desde materias_calificaciones ──────────────────
        mats_rows = conn.execute("""
            SELECT materia, p1, p2, p3, p4, promedio, tipo, profesor
            FROM materias_calificaciones
            WHERE estudiante_id = ?
            ORDER BY materia
        """, (est_id,)).fetchall()

        # ── Notas manuales por período (prioridad mayor) ───────────────────
        anio_actual = _anio_escolar_actual()
        notas_periodo_rows = conn.execute("""
            SELECT materia, periodo, calificacion
            FROM calificaciones_periodo
            WHERE estudiante_id = ? AND anio_escolar = ?
            ORDER BY materia, periodo
        """, (est_id, anio_actual)).fetchall()

        # ── Asistencia por materia y período desde tabla asistencia ────────
        asist_rows = conn.execute("""
            SELECT
                materia,
                periodo,
                ROUND(
                    100.0 * SUM(CASE WHEN estado IN ('presente','P') THEN horas_clase ELSE 0 END)
                    / NULLIF(SUM(horas_clase), 0)
                , 1) as pct_asistencia
            FROM asistencia
            WHERE estudiante_id = ?
            GROUP BY materia, periodo
        """, (est_id,)).fetchall()

        # ── Maestro/a asignado ──────────────────────────────────────────────
        maestro = conn.execute("""
            SELECT nombre FROM usuarios
            WHERE grado LIKE ? AND mencion LIKE ? AND rol='profesor' AND activo=1
            LIMIT 1
        """, (f"%{e.get('grado','4to')}%", f"%{(e.get('curso') or '').split()[-1] if e.get('curso') else 'MULTIMEDIA'}%")
        ).fetchone()

    # Alias de nombres reales en BD → nombres en el plan oficial
    # Cubre los casos donde el maestro guardó con un nombre diferente
    ALIAS_MATERIAS = {
        # Académicas
        'ciencias naturales':                       'Ciencias de la Naturaleza',
        'naturales':                                'Ciencias de la Naturaleza',
        # Note: keeping 'Idioma Inglés' as-is — plan uses this exact name
        # 'idioma inglés': 'Idioma Inglés',  # no alias needed
        'fihr':                                     'Formación Integral Humana y Religiosa',
        'f.i.h.r.':                                 'Formación Integral Humana y Religiosa',
        'formacion religiosa':                      'Formación Integral Humana y Religiosa',
        'formación religiosa':                      'Formación Integral Humana y Religiosa',
        # Técnicas Artes Visuales
        'dibujo técnico':                           'Dibujo Técnico y Artístico',
        'dibujo tecnico':                           'Dibujo Técnico y Artístico',
        'historia del arte universal y teoría de las artes visuales': 'Historia del Arte Universal',
        'historia del arte universal y teoria de las artes visuales': 'Historia del Arte Universal',
        'historia del arte':                        'Historia del Arte Universal',
        'principios de dibujo, pintura y creatividad': 'Pintura y Técnicas Mixtas',
        'principios de dibujo pintura y creatividad':  'Pintura y Técnicas Mixtas',
        'pintura':                                  'Pintura y Técnicas Mixtas',
        # Técnicas Artes Visuales — Lenguaje Plástico conserva su nombre de Artes Visuales
        'lenguaje visual y principios del diseño artesanal': 'Lenguaje Plástico y Visual',
        'lenguaje visual y principios del diseno artesanal': 'Lenguaje Plástico y Visual',
        'lenguaje visual artesanal':                'Lenguaje Plástico y Visual',
        'lenguaje plastico y visual':               'Lenguaje Plástico y Visual',
        # Técnicas Multimedia
        'lenguaje visual, dibujo y creación de personajes': 'Lenguaje Visual, Dibujo y Creación de Personajes',
        'introducción a la fotografía digital':     'Introducción a la Fotografía Digital',
        'introduccion a la fotografia digital':     'Introducción a la Fotografía Digital',
        'introducción fotografía digital':          'Introducción a la Fotografía Digital',
        'fotografía artística':                     'Fotografía Artística',
        'fotografia artistica':                     'Fotografía Artística',
        # Primer ciclo aliases
        'educación artística':                      'Educación Artística',
        'educacion artistica':                      'Educación Artística',
        'ed. artística':                            'Educación Artística',
        'ed artistica':                             'Educación Artística',
        'idioma francés':                           'Idioma Francés',
        'idioma frances':                           'Idioma Francés',
        'francés':                                  'Idioma Francés',
        'frances':                                  'Idioma Francés',
        'lengua':                                   'Lengua Española',
        'lengua española':                          'Lengua Española',
        'español':                                  'Lengua Española',
        'espanol':                                  'Lengua Española',
        'matemáticas':                              'Matemática',
        'matematica':                               'Matemática',
        'matematicas':                              'Matemática',
        'ciencias sociales':                        'Ciencias Sociales',
        'sociales':                                 'Ciencias Sociales',
        'educación física':                         'Educación Física',
        'educacion fisica':                         'Educación Física',
        'ed física':                                'Educación Física',
        'ed. física':                               'Educación Física',
        # Inglés variants
        'inglés':                                   'Idioma Inglés',
        'ingles':                                   'Idioma Inglés',
        'idioma inglés':                            'Idioma Inglés',
        'idioma ingles':                            'Idioma Inglés',
    }

    # Organizar notas por materia — aplicando aliases y mergeando duplicados de casing
    notas_por_materia = {}
    _norm_to_canon = {}  # norm_key → canonical name actualmente en notas_por_materia

    def _nm(n):
        return (n or "").strip().lower().rstrip('.')

    for m in mats_rows:
        nombre_real = m["materia"]
        norm = _nm(nombre_real)
        # Aplicar alias si existe (usa original-case como fallback)
        nombre_canon = ALIAS_MATERIAS.get(norm, nombre_real)
        norm_canon = _nm(nombre_canon)

        # Primer registro para este nombre normalizado → crear slot
        if norm_canon not in _norm_to_canon:
            _norm_to_canon[norm_canon] = nombre_canon
            notas_por_materia[nombre_canon] = {
                "p1": None, "p2": None, "p3": None, "p4": None,
                "promedio": None, "tipo": "académico",
            }

        canon = _norm_to_canon[norm_canon]
        ex = notas_por_materia[canon]

        # Merge: solo actualiza períodos con valor real (no sobreescribe con NULL/0)
        if m["p1"] not in (None, 0): ex["p1"] = m["p1"]
        if m["p2"] not in (None, 0): ex["p2"] = m["p2"]
        if m["p3"] not in (None, 0): ex["p3"] = m["p3"]
        if m["p4"] not in (None, 0): ex["p4"] = m["p4"]
        if m["promedio"] is not None: ex["promedio"] = m["promedio"]
        ex["tipo"] = m["tipo"] or "académico"

        # Alias de fallback: también indexar bajo el nombre original para el template
        if nombre_real != canon:
            notas_por_materia[nombre_real] = ex
        # Indexar también lowercase por si el template busca así
        if norm != norm_canon:
            notas_por_materia[nombre_real.strip()] = ex

    # Overlay con calificaciones_periodo (entrada manual — prioridad mayor sobre Excel)
    for r in notas_periodo_rows:
        nombre_real = r["materia"]
        norm = _nm(nombre_real)
        nombre_canon = ALIAS_MATERIAS.get(norm, nombre_real)
        norm_canon = _nm(nombre_canon)

        if norm_canon not in _norm_to_canon:
            _norm_to_canon[norm_canon] = nombre_canon
            notas_por_materia[nombre_canon] = {
                "p1": None, "p2": None, "p3": None, "p4": None,
                "promedio": None, "tipo": "académico",
            }

        canon = _norm_to_canon[norm_canon]
        ex = notas_por_materia[canon]
        periodo_key = r["periodo"] if r["periodo"].startswith("P") else f"P{r['periodo']}"
        cal = r["calificacion"]
        if cal is not None:
            ex[periodo_key.lower()] = cal  # "p1"/"p2"/"p3"/"p4"
        if nombre_real != canon:
            notas_por_materia[nombre_real] = ex

    # Incorporar materias_extras del estudiante (calculadas en perfil_estudiante)
    # Esto cubre menciones no-Multimedia donde las notas técnicas no van a campos directos
    for mat_nombre, mat_vals in (e.get("materias_extras") or {}).items():
        if mat_nombre not in notas_por_materia:
            notas_por_materia[mat_nombre] = {
                "p1": mat_vals.get("p1"), "p2": mat_vals.get("p2"),
                "p3": mat_vals.get("p3"), "p4": mat_vals.get("p4"),
                "promedio": mat_vals.get("promedio"), "tipo": "técnico",
            }

    # Organizar asistencia por materia→período
    asist_por_materia = {}
    for a in asist_rows:
        mat = a["materia"]
        if mat not in asist_por_materia:
            asist_por_materia[mat] = {}
        asist_por_materia[mat][f"P{a['periodo']}"] = a["pct_asistencia"]

    # Determinar mención y grado limpios
    curso = (e.get("curso") or "").strip().upper()
    grado_raw = (e.get("grado") or "4TO").strip().upper()
    # Robust grado_key: handle "1ERO", "1RO", "2DO", "3RO", "4TO", "5TO", "6TO"
    _grado_map = {
        "1ERO": "1ro", "1RO": "1ro", "1ER": "1ro", "1RO.": "1ro",
        "2DO": "2do", "2DO.": "2do",
        "3RO": "3ro", "3ER": "3ro", "3RO.": "3ro",
        "4TO": "4to", "4TO.": "4to",
        "5TO": "5to", "5TO.": "5to",
        "6TO": "6to", "6TO.": "6to",
    }
    grado_key = _grado_map.get(grado_raw)
    if not grado_key:
        # Fallback: extract digit and suffix
        import re as _re_g
        m_g = _re_g.match(r'^([0-9])(ERO|RO|DO|TO|ER)', grado_raw)
        if m_g:
            _num = m_g.group(1)
            _suf = m_g.group(2)
            _suf_map = {"ERO":"ro","RO":"ro","DO":"do","TO":"to","ER":"ro"}
            grado_key = _num + _suf_map.get(_suf, "to")
        else:
            grado_key = "4to"
    if not grado_key[0].isdigit():
        grado_key = "4to"

    # Detectar si es primer ciclo (1ro, 2do, 3ro)
    es_primer_ciclo = grado_key in ('1ro', '2do', '3ro')

    # Detectar mención desde el curso (ej "4TO MULTIMEDIA" → "MULTIMEDIA")
    mencion = "MULTIMEDIA"
    if es_primer_ciclo:
        mencion = "PRIMER_CICLO"
    else:
        for m_key in PLAN_ARTES.keys():
            if m_key in curso:
                mencion = m_key
                break

    # Plan oficial de materias para este grado y mención
    plan_oficial = PLAN_ARTES.get(mencion, PLAN_MULTIMEDIA).get(grado_key, [])

    # Separar materias académicas y técnicas del plan
    # Para primer ciclo: Educación Artística e Idioma Francés son técnicas
    MATS_ACAD_NOMBRES = {
        "Lengua Española", "Inglés", "Idioma Inglés", "Matemática",
        "Ciencias Sociales", "Ciencias de la Naturaleza",
        "Formación Integral Humana y Religiosa", "Educación Física",
    }
    if es_primer_ciclo:
        MATS_TEC_PRIMER_CICLO = {"Educación Artística", "Idioma Francés"}
        plan_acad = [(n, h) for n, h in plan_oficial if n not in MATS_TEC_PRIMER_CICLO]
        plan_tec  = [(n, h) for n, h in plan_oficial if n in MATS_TEC_PRIMER_CICLO]
    else:
        plan_acad = [(n, h) for n, h in plan_oficial if n in MATS_ACAD_NOMBRES]
        plan_tec  = [(n, h) for n, h in plan_oficial if n not in MATS_ACAD_NOMBRES]

    # Usar acad_p1..p4 del estudiante como fallback para académicas
    acad_fallback = {
        "P1": e.get("acad_p1") or 0,
        "P2": e.get("acad_p2") or 0,
        "P3": e.get("acad_p3") or 0,
        "P4": e.get("acad_p4") or 0,
    }

    # ── Mapa de materias técnicas Multimedia → campos directos del estudiante ──
    # Las demás menciones usan materias_extras (ya mergeado en notas_por_materia)
    CAMPOS_DIRECTOS_MAP = {
        # Fotografía — todas las variantes
        'fotografía':                               ('fotografia_p1','fotografia_p2','fotografia_p3','fotografia_p4'),
        'fotografia':                               ('fotografia_p1','fotografia_p2','fotografia_p3','fotografia_p4'),
        'foto':                                     ('fotografia_p1','fotografia_p2','fotografia_p3','fotografia_p4'),
        'fotografía digital':                       ('fotografia_p1','fotografia_p2','fotografia_p3','fotografia_p4'),
        'fotografia digital':                       ('fotografia_p1','fotografia_p2','fotografia_p3','fotografia_p4'),
        'introducción fotografía':                  ('fotografia_p1','fotografia_p2','fotografia_p3','fotografia_p4'),
        'introduccion fotografia':                  ('fotografia_p1','fotografia_p2','fotografia_p3','fotografia_p4'),
        'introducción a la fotografía digital':     ('fotografia_p1','fotografia_p2','fotografia_p3','fotografia_p4'),
        'introduccion a la fotografia digital':     ('fotografia_p1','fotografia_p2','fotografia_p3','fotografia_p4'),
        'fotografía artística':                     ('fotografia_p1','fotografia_p2','fotografia_p3','fotografia_p4'),
        'fotografia artistica':                     ('fotografia_p1','fotografia_p2','fotografia_p3','fotografia_p4'),
        # Lenguaje Visual / Plástico — solo Multimedia usa campos directos lv_p*
        'lenguaje visual':                                      ('lv_p1','lv_p2','lv_p3','lv_p4'),
        'lenguaje visual, dibujo y creación de personajes':     ('lv_p1','lv_p2','lv_p3','lv_p4'),
        'lenguaje visual dibujo y creacion de personajes':      ('lv_p1','lv_p2','lv_p3','lv_p4'),
        'lenguaje visual y principios de diseño':               ('lv_p1','lv_p2','lv_p3','lv_p4'),
        # Artes Visuales guarda en materias_calificaciones — no usar campos directos lv_p*
        # Diseño Básico
        'diseño básico y expresión visual':         ('diseno_p1','diseno_p2','diseno_p3','diseno_p4'),
        'diseño basico y expresion visual':         ('diseno_p1','diseno_p2','diseno_p3','diseno_p4'),
        'diseño básico':                            ('diseno_p1','diseno_p2','diseno_p3','diseno_p4'),
        'diseño basico':                            ('diseno_p1','diseno_p2','diseno_p3','diseno_p4'),
        'diseño':                                   ('diseno_p1','diseno_p2','diseno_p3','diseno_p4'),
        'diseno':                                   ('diseno_p1','diseno_p2','diseno_p3','diseno_p4'),
    }

    def _buscar_campo_directo(nombre, periodo_num):
        """Busca en campos directos del estudiante para materias técnicas de Multimedia."""
        nb = nombre.lower().strip()
        for key_frag, campos in CAMPOS_DIRECTOS_MAP.items():
            if key_frag in nb or nb in key_frag:
                col = campos[periodo_num - 1]
                val = e.get(col)
                return float(val) if val and float(val) > 0 else None
        return None

    # Palabras genéricas que NO deben usarse solas para hacer match
    _PALABRAS_GENERICAS = {
        'y', 'de', 'la', 'el', 'las', 'los', 'del', 'al',
        'ciencias', 'lenguaje', 'lengua', 'historia', 'arte',
        'educacion', 'educación', 'idioma', 'principios',
    }

    import unicodedata as _ud
    def _norm(s):
        """Normaliza acentos/tildes para comparación robusta."""
        return _ud.normalize('NFD', s).encode('ascii', 'ignore').decode('ascii').lower().strip().rstrip('.')

    def nota_mat(nombre, periodo):
        """
        Busca nota de una materia con matching progresivo y preciso.
        1. Exact match (case-insensitive)
        2. Fuzzy: palabras clave únicas (ignora palabras genéricas)
        3. Fallback a campos directos del estudiante
        """
        nb   = nombre.lower().strip().rstrip('.')
        pkey = periodo.lower()
        pnum = int(pkey[1]) if len(pkey) == 2 and pkey[1].isdigit() else 0

        # 1. Exact match — con y sin tildes
        nb_norm = _norm(nb)
        for k, v in notas_por_materia.items():
            if _norm(k) == nb_norm:
                return v.get(pkey) or v.get(pkey.upper()) or None

        # 2. Fuzzy con palabras clave no-genéricas, normalizando tildes
        def palabras_clave(s):
            return [_norm(w) for w in s.split()
                    if len(w) > 3 and w.lower() not in _PALABRAS_GENERICAS
                    and _norm(w) not in _PALABRAS_GENERICAS]

        nb_kw = palabras_clave(nb)
        if not nb_kw:
            nb_kw = [_norm(w) for w in nb.split() if len(w) > 2]

        best_match = None
        best_score = 0
        for k, v in notas_por_materia.items():
            kl    = _norm(k)
            kl_kw = palabras_clave(k)
            if not kl_kw:
                continue

            # Contar palabras clave que coinciden (ya normalizadas, sin tildes)
            matches_nb = sum(1 for w in nb_kw if any(w in wk or wk in w for wk in kl_kw))
            matches_kl = sum(1 for w in kl_kw if any(w in wk or wk in w for wk in nb_kw))

            # Score: proporción de coincidencia en ambas direcciones
            score = (matches_nb / max(len(nb_kw), 1)) + (matches_kl / max(len(kl_kw), 1))

            # Umbral: score >= 0.8 para evitar falsos positivos
            # y > best_score para quedarse con el mejor match
            if score >= 0.8 and score > best_score:
                best_score = score
                best_match = v

        if best_match:
            val = best_match.get(pkey) or best_match.get(pkey.upper())
            if val:
                return val

        # 3. Fallback a campos directos del estudiante
        if pnum > 0:
            return _buscar_campo_directo(nombre, pnum)

        return None

    def asist_mat_p(nombre, periodo):
        for k, v in asist_por_materia.items():
            if nombre.lower() in k.lower() or k.lower() in nombre.lower():
                return v.get(f"P{periodo}")
        return None

    # Construir datos académicos para la plantilla
    acad_data = []
    for nombre, horas in plan_acad:
        p1 = nota_mat(nombre, "p1") or nota_mat(nombre, "P1")
        p2 = nota_mat(nombre, "p2") or nota_mat(nombre, "P2")
        p3 = nota_mat(nombre, "p3") or nota_mat(nombre, "P3")
        p4 = nota_mat(nombre, "p4") or nota_mat(nombre, "P4")
        acad_data.append({
            "nombre": nombre, "horas": horas,
            "p1": round(float(p1), 1) if p1 else None,
            "p2": round(float(p2), 1) if p2 else None,
            "p3": round(float(p3), 1) if p3 else None,
            "p4": round(float(p4), 1) if p4 else None,
            "asist_p1": asist_mat_p(nombre, 1),
            "asist_p2": asist_mat_p(nombre, 2),
        })

    # Construir datos técnicos para la plantilla
    tec_data = []
    for nombre, horas in plan_tec:
        p1 = nota_mat(nombre, "p1") or nota_mat(nombre, "P1")
        p2 = nota_mat(nombre, "p2") or nota_mat(nombre, "P2")
        p3 = nota_mat(nombre, "p3") or nota_mat(nombre, "P3")
        p4 = nota_mat(nombre, "p4") or nota_mat(nombre, "P4")
        vals = [float(x) for x in [p1,p2,p3,p4] if x]
        cf = round(sum(vals)/len(vals), 1) if vals else None
        tec_data.append({
            "nombre": nombre, "horas": horas,
            "p1": round(float(p1), 1) if p1 else None,
            "p2": round(float(p2), 1) if p2 else None,
            "p3": round(float(p3), 1) if p3 else None,
            "p4": round(float(p4), 1) if p4 else None,
            "cf": cf,
            "asist_p1": asist_mat_p(nombre, 1),
            "asist_p2": asist_mat_p(nombre, 2),
        })

    # Condición final
    def _cond(data):
        if not data:
            return {"aprobado": True, "reprobadas": 0}
        notas_cf = []
        # Try 'cf' key first (técnicas), else calculate from p1..p4 (académicas)
        for m in data:
            if m.get("cf") and m["cf"] > 0:
                notas_cf.append(m["cf"])
            else:
                vals = [float(m[k]) for k in ["p1","p2","p3","p4"] if m.get(k) and float(m.get(k,0)) > 0]
                if vals: notas_cf.append(round(sum(vals)/len(vals), 1))
        reprobadas = sum(1 for n in notas_cf if n < 70)
        return {"aprobado": reprobadas == 0, "reprobadas": reprobadas}

    cond_acad = _cond(acad_data)
    # ── Materias EXTRA: en BD pero fuera del plan oficial ─────────────────
    # Ocurre cuando el estudiante lleva materias de otra mención o el
    # docente registró con nombre distinto al del plan.
    MATS_ACAD_SET = {n.lower() for n in MATS_ACAD_NOMBRES}
    # Nombres del plan técnico normalizados para comparar
    nombres_plan_tec = set()
    for nombre_p, _ in plan_tec:
        nombres_plan_tec.add(nombre_p.lower().strip())
    # También agregar alias inversos
    for alias_key, alias_val in ALIAS_MATERIAS.items():
        if alias_val:
            for nombre_p, _ in plan_tec:
                if alias_val.lower() == nombre_p.lower():
                    nombres_plan_tec.add(alias_key.lower())

    extra_data = []
    for nombre_bd, vals_bd in notas_por_materia.items():
        nb_l = nombre_bd.lower().strip()
        # Ignorar académicas estándar
        if any(a in nb_l or nb_l in a for a in MATS_ACAD_SET):
            continue
        # Ignorar si ya está cubierta por el plan técnico
        en_plan = any(np == nb_l or np in nb_l or nb_l in np
                      for np in nombres_plan_tec)
        if en_plan:
            continue
        # Materia extra — incluir si tiene al menos una nota
        p1 = vals_bd.get("p1"); p2 = vals_bd.get("p2")
        p3 = vals_bd.get("p3"); p4 = vals_bd.get("p4")
        vals = [float(x) for x in [p1,p2,p3,p4] if x]
        cf   = round(sum(vals)/len(vals), 1) if vals else None
        if vals:  # solo si tiene notas
            extra_data.append({
                "nombre":   nombre_bd, "horas": 0,
                "p1": round(float(p1),1) if p1 else None,
                "p2": round(float(p2),1) if p2 else None,
                "p3": round(float(p3),1) if p3 else None,
                "p4": round(float(p4),1) if p4 else None,
                "cf": cf,
                "asist_p1": asist_mat_p(nombre_bd, 1),
                "asist_p2": asist_mat_p(nombre_bd, 2),
            })

    # Agregar materias extra directamente a tec_data (misma sección técnica)
    # Para que el boletín muestre TODO en una sola tabla de componente técnico
    tec_data.extend(extra_data)
    cond_tec  = _cond(tec_data)

    nombre_completo = f"{e.get('nombre','')} {e.get('apellido','')}".strip()

    return render_template(
        "boletin.html",
        e          = e,
        nombre_completo = nombre_completo,
        grado      = grado_raw,
        mencion    = mencion.title(),
        curso      = curso,
        maestro    = (maestro["nombre"] if maestro else ""),
        acad_data  = acad_data,
        tec_data   = tec_data,
        extra_data = extra_data,
        cond_acad  = cond_acad,
        cond_tec   = cond_tec,
        periodo_actual = _periodo_actual(),
        anio_escolar   = _anio_escolar_actual(),
        current_user   = u,
    )




# ══════════════════════════════════════════════════════════════════════════════
# BOLETÍN PDF — Ord.04-2023 MINERD
# ══════════════════════════════════════════════════════════════════════════════


@calificaciones_bp.route("/api/calificaciones/boletin/<int:est_id>/pdf")
@login_required
def boletin_pdf(est_id):
    """
    Genera el boletín de calificaciones del estudiante en PDF.
    Formato oficial C.E. Benito Juárez — Ordenanza 04-2023 MINERD.
    Accesible para el propio estudiante, profesores, coordinadores y directora.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                     Paragraph, Spacer, HRFlowable)
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    import io

    anio = request.args.get("anio", _anio_escolar_actual())

    # ── Obtener datos ─────────────────────────────────────────────────────────
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        _rls.verificar_acceso_estudiante(conn, est_id)  # RLS — PDF sensible
        est = conn.execute("SELECT * FROM estudiantes WHERE id=?", (est_id,)).fetchone()
        if not est:
            return jsonify({"error": "Estudiante no encontrado"}), 404
        est = dict(est)

        recup_rows = conn.execute(
            """SELECT materia, nota_recuperacion, nota_completiva,
                      nota_extraordinaria, nota_final_ajustada
               FROM recuperaciones_pedagogicas
               WHERE estudiante_id=? AND anio_escolar=?""",
            (est_id, anio)
        ).fetchall()

    recup_map = {r["materia"]: dict(r) for r in recup_rows}

    # Llamar lógica del boletín reutilizando la función interna
    import urllib.request as _ureq, json as _json
    host = request.host_url.rstrip("/")
    try:
        req = _ureq.Request(
            f"{host}/api/calificaciones/boletin/{est_id}?anio={anio}",
            headers={"Cookie": request.headers.get("Cookie", "")}
        )
        with _ureq.urlopen(req, timeout=10) as resp:
            boletin_data = _json.loads(resp.read())
    except Exception:
        return jsonify({"error": "No se pudo obtener el boletín"}), 500

    materias = boletin_data.get("materias", [])
    resumen  = boletin_data.get("resumen", {})

    # ── Paleta de colores ─────────────────────────────────────────────────────
    C_HEADER   = colors.HexColor("#024959")   # teal oscuro institucional
    C_ACCENT   = colors.HexColor("#037F8C")   # teal claro
    C_D        = colors.HexColor("#15803d")   # Destacado verde
    C_S        = colors.HexColor("#1d4ed8")   # Satisfactorio azul
    C_B        = colors.HexColor("#4d7c0f")   # Básico lima
    C_EP       = colors.HexColor("#b45309")   # En proceso amarillo
    C_I        = colors.HexColor("#b91c1c")   # Insuficiente rojo
    C_GRAY     = colors.HexColor("#6b7280")
    C_LIGHT    = colors.HexColor("#f0f9fa")
    C_ROW_ALT  = colors.HexColor("#f8fafb")
    C_BORDER   = colors.HexColor("#d1e8ec")

    def nivel_color(estado):
        return {
            "destacado": C_D, "satisfactorio": C_S, "basico": C_B,
            "en_proceso": C_EP, "insuficiente": C_I,
        }.get(estado, C_GRAY)

    def nivel_label(estado):
        return {
            "destacado": "D · Destacado", "satisfactorio": "S · Satisfactorio",
            "basico": "B · Básico", "en_proceso": "EP · En proceso",
            "insuficiente": "I · Insuficiente", "sin_nota": "—",
        }.get(estado, estado or "—")

    def fmt_nota(v):
        if v is None: return "—"
        try: return str(round(float(v), 1))
        except: return "—"

    # ── Estilos ───────────────────────────────────────────────────────────────
    def ps(name, **kw):
        defaults = dict(fontName="Helvetica", fontSize=10, leading=13,
                        textColor=colors.HexColor("#1a1a2e"))
        defaults.update(kw)
        return ParagraphStyle(name, **defaults)

    st_title   = ps("title",  fontName="Helvetica-Bold", fontSize=14, textColor=C_HEADER, alignment=TA_CENTER, spaceAfter=2)
    st_sub     = ps("sub",    fontName="Helvetica",      fontSize=9,  textColor=C_GRAY,   alignment=TA_CENTER, spaceAfter=1)
    st_label   = ps("label",  fontName="Helvetica-Bold", fontSize=8,  textColor=C_GRAY)
    st_value   = ps("value",  fontName="Helvetica",      fontSize=9,  textColor=colors.HexColor("#1a1a2e"))
    st_th      = ps("th",     fontName="Helvetica-Bold", fontSize=7.5,textColor=colors.white)
    st_td      = ps("td",     fontName="Helvetica",      fontSize=8,  textColor=colors.HexColor("#1a1a2e"))
    st_td_c    = ps("tdc",    fontName="Helvetica",      fontSize=8,  textColor=colors.HexColor("#1a1a2e"), alignment=TA_CENTER)
    st_note    = ps("note",   fontName="Helvetica-Oblique", fontSize=7, textColor=C_GRAY, alignment=TA_CENTER)

    # ── Construir PDF ─────────────────────────────────────────────────────────
    buf = io.BytesIO()
    PAGE_W, PAGE_H = A4
    MARGIN = 1.8 * cm
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=MARGIN,
        title=f"Boletín {est.get('nombre','')} {est.get('apellido','')}",
        author="C.E. Benito Juárez — Axula",
    )

    story = []
    W = PAGE_W - 2 * MARGIN  # usable width

    # ── Encabezado ────────────────────────────────────────────────────────────
    # ── Encabezado con logo desde BD ─────────────────────────────────────────
    _cfg_b  = _get_config_centro()
    _nom_b  = _cfg_b.get("nombre",    "Centro Educativo en Artes Benito Juárez")
    _mod_b  = _cfg_b.get("modalidad", "Modalidad en Artes · Nivel Secundario")
    _dir_b  = _cfg_b.get("direccion", "")
    _tel_b  = _cfg_b.get("telefono",  "")
    _eml_b  = _cfg_b.get("email",     "")
    _lg_b64 = _cfg_b.get("logo_base64")

    import base64 as _b64b, io as _iob
    _logo_b = None
    if _lg_b64 and _lg_b64.startswith("data:image/"):
        try:
            _, _raw_b = _lg_b64.split(",", 1)
            _logo_b   = RLImage(_iob.BytesIO(_b64b.b64decode(_raw_b)), width=2*cm, height=2*cm)
            _logo_b.hAlign = "CENTER"
        except Exception as _e:
            logger.warning(f"[calificaciones] Excepción silenciada")

    _centro_col = [
        Paragraph("REPÚBLICA DOMINICANA — MINISTERIO DE EDUCACIÓN — MINERD",
                  ps("brd", fontSize=7, textColor=C_GRAY, alignment=TA_CENTER, spaceAfter=1)),
        Paragraph(_nom_b,
                  ps("bnom", fontName="Helvetica-Bold", fontSize=13, textColor=C_HEADER,
                     alignment=TA_CENTER, leading=15, spaceAfter=2)),
        Paragraph(_mod_b,
                  ps("bmod", fontSize=8, textColor=C_GRAY, alignment=TA_CENTER, spaceAfter=2)),
    ]
    _info_b = " · ".join(filter(None, [_dir_b, _tel_b, _eml_b]))
    if _info_b:
        _centro_col.append(Paragraph(_info_b,
            ps("binfo", fontSize=7, textColor=C_GRAY, alignment=TA_CENTER, spaceAfter=3)))

    _tit_col = [
        Paragraph("BOLETÍN DE<br/>CALIFICACIONES",
                  ps("btit2", fontName="Helvetica-Bold", fontSize=10, textColor=C_HEADER,
                     alignment=TA_RIGHT, leading=13, spaceAfter=4)),
        Paragraph(f"Año Escolar {anio}",
                  ps("banio", fontSize=8, textColor=C_ACCENT, alignment=TA_RIGHT)),
    ]

    _LW, _TW = 2.3*cm, 3.8*cm
    if _logo_b:
        _hdr_data = [[_logo_b, _centro_col, _tit_col]]
        _hdr_cols = [_LW, W - _LW - _TW, _TW]
    else:
        _hdr_data = [[_centro_col, _tit_col]]
        _hdr_cols = [W - _TW, _TW]

    _hdr_t = Table(_hdr_data, colWidths=_hdr_cols)
    _hdr_t.setStyle(TableStyle([
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("ALIGN",         (-1,0),(-1,-1), "RIGHT"),
        ("TOPPADDING",    (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
        ("LEFTPADDING",   (0,0), (-1,-1), 3),
        ("RIGHTPADDING",  (0,0), (-1,-1), 3),
    ]))
    story.append(_hdr_t)
    story.append(HRFlowable(width=W, thickness=2, color=C_HEADER, spaceBefore=6, spaceAfter=6))
    story.append(HRFlowable(width=W, thickness=1, color=C_ACCENT, spaceAfter=10))

    # ── Datos del estudiante ──────────────────────────────────────────────────
    nombre_completo = f"{est.get('nombre','').strip()} {est.get('apellido','').strip()}"
    info_data = [
        [Paragraph("<b>Estudiante:</b>", st_label), Paragraph(nombre_completo.upper(), st_value),
         Paragraph("<b>Cédula:</b>", st_label),     Paragraph(est.get("cedula") or "—", st_value)],
        [Paragraph("<b>Grado:</b>", st_label),       Paragraph(est.get("grado") or "—", st_value),
         Paragraph("<b>Mención:</b>", st_label),    Paragraph((est.get("curso") or "—"), st_value)],
        [Paragraph("<b>Condición:</b>", st_label),   Paragraph(est.get("condicion") or "ACTIVO", st_value),
         Paragraph("<b>Período actual:</b>", st_label), Paragraph(boletin_data.get("periodo_actual","—"), st_value)],
    ]
    info_table = Table(info_data, colWidths=[2.2*cm, W/2-2.2*cm, 2.2*cm, W/2-2.2*cm])
    info_table.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,-1), C_LIGHT),
        ("BOX",         (0,0), (-1,-1), 0.5, C_BORDER),
        ("INNERGRID",   (0,0), (-1,-1), 0.3, C_BORDER),
        ("TOPPADDING",  (0,0), (-1,-1), 5),
        ("BOTTOMPADDING",(0,0),(-1,-1), 5),
        ("LEFTPADDING", (0,0), (-1,-1), 7),
        ("RIGHTPADDING",(0,0), (-1,-1), 7),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 12))

    # ── Tabla de calificaciones ───────────────────────────────────────────────
    COL_W = [W*0.32, W*0.09, W*0.09, W*0.09, W*0.09, W*0.10, W*0.10, W*0.12]
    header_row = [
        Paragraph("Materia", st_th),
        Paragraph("P1", st_th), Paragraph("P2", st_th),
        Paragraph("P3", st_th), Paragraph("P4", st_th),
        Paragraph("Final", st_th),
        Paragraph("Inasist.", st_th),
        Paragraph("Nivel", st_th),
    ]
    rows = [header_row]

    for i, m in enumerate(materias):
        estado = m.get("estado", "sin_nota")
        nota_f = m.get("nota_final")
        recup  = recup_map.get(m["materia"], {})
        nota_aj = recup.get("nota_final_ajustada")

        # Nota final: usar ajustada si existe
        nota_display = nota_aj if nota_aj is not None else nota_f
        nivel_txt  = nivel_label(estado)
        nivel_clr  = nivel_color(estado)

        # Extra: si hay recuperación, añadir nota ajustada en la celda final
        final_cell = fmt_nota(nota_display)
        if nota_aj is not None and nota_aj != nota_f:
            final_cell += f" *"

        row_bg = colors.white if i % 2 == 0 else C_ROW_ALT

        nivel_par = Paragraph(f'<font color="#{"%02x%02x%02x" % (int(nivel_clr.red*255), int(nivel_clr.green*255), int(nivel_clr.blue*255))}"><b>{nivel_txt}</b></font>', st_td_c)

        inasist_v = m.get("pct_inasistencia", 0) or 0
        inasist_clr = C_I if inasist_v >= 20 else (C_EP if inasist_v >= 15 else colors.HexColor("#1a1a2e"))
        inasist_par = Paragraph(f'<font color="#{"%02x%02x%02x" % (int(inasist_clr.red*255), int(inasist_clr.green*255), int(inasist_clr.blue*255))}">{inasist_v:.0f}%</font>', st_td_c)

        rows.append([
            Paragraph(m["materia"], st_td),
            Paragraph(fmt_nota(m.get("P1") or m.get("p1")), st_td_c),
            Paragraph(fmt_nota(m.get("P2") or m.get("p2")), st_td_c),
            Paragraph(fmt_nota(m.get("P3") or m.get("p3")), st_td_c),
            Paragraph(fmt_nota(m.get("P4") or m.get("p4")), st_td_c),
            Paragraph(f"<b>{final_cell}</b>", st_td_c),
            inasist_par,
            nivel_par,
        ])

    cal_table = Table(rows, colWidths=COL_W, repeatRows=1)
    # Row styles
    row_styles = [
        ("BACKGROUND",   (0,0), (-1,0),  C_HEADER),
        ("TEXTCOLOR",    (0,0), (-1,0),  colors.white),
        ("FONTNAME",     (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",     (0,0), (-1,0),  8),
        ("ALIGN",        (0,0), (-1,-1), "CENTER"),
        ("ALIGN",        (0,1), (0,-1),  "LEFT"),
        ("BOX",          (0,0), (-1,-1), 0.5, C_BORDER),
        ("INNERGRID",    (0,0), (-1,-1), 0.3, C_BORDER),
        ("TOPPADDING",   (0,0), (-1,-1), 4),
        ("BOTTOMPADDING",(0,0), (-1,-1), 4),
        ("LEFTPADDING",  (0,0), (-1,-1), 5),
        ("RIGHTPADDING", (0,0), (-1,-1), 5),
    ]
    for i in range(1, len(rows)):
        bg = colors.white if i % 2 == 1 else C_ROW_ALT
        row_styles.append(("BACKGROUND", (0,i), (-1,i), bg))

    cal_table.setStyle(TableStyle(row_styles))
    story.append(cal_table)

    # ── Nota al pie si hay recuperaciones ─────────────────────────────────────
    if recup_map:
        story.append(Spacer(1, 4))
        story.append(Paragraph("* Nota ajustada con Recuperación Pedagógica (Ord.04-2023 Art.28)", st_note))

    story.append(Spacer(1, 10))

    # ── Resumen ───────────────────────────────────────────────────────────────
    aprobadas  = resumen.get("aprobadas", 0)
    en_proceso = resumen.get("en_proceso", 0)
    insuf      = resumen.get("insuficientes", 0)
    promueve   = resumen.get("promueve", True)

    resumen_data = [[
        Paragraph(f"<b>Aprobadas:</b> {aprobadas}", st_td_c),
        Paragraph(f"<b>En proceso:</b> {en_proceso}", st_td_c),
        Paragraph(f"<b>Insuficientes:</b> {insuf}", st_td_c),
        Paragraph(
            f'<font color="#{"%02x%02x%02x" % (int(C_D.red*255), int(C_D.green*255), int(C_D.blue*255))}"><b>PROMOVIDO/A</b></font>'
            if promueve else
            f'<font color="#{"%02x%02x%02x" % (int(C_I.red*255), int(C_I.green*255), int(C_I.blue*255))}"><b>REPITE EL GRADO</b></font>',
            st_td_c
        ),
    ]]
    res_table = Table(resumen_data, colWidths=[W/4]*4)
    res_table.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,-1), C_LIGHT),
        ("BOX",          (0,0), (-1,-1), 1,   C_ACCENT),
        ("INNERGRID",    (0,0), (-1,-1), 0.3, C_BORDER),
        ("TOPPADDING",   (0,0), (-1,-1), 7),
        ("BOTTOMPADDING",(0,0), (-1,-1), 7),
    ]))
    story.append(res_table)

    # ── Escala de niveles ─────────────────────────────────────────────────────
    story.append(Spacer(1, 10))
    niveles_data = [[
        Paragraph("<b>D</b> Destacado (89-100)", ps("n", fontSize=7, textColor=C_D)),
        Paragraph("<b>S</b> Satisfactorio (80-88)", ps("n", fontSize=7, textColor=C_S)),
        Paragraph("<b>B</b> Básico (70-79)", ps("n", fontSize=7, textColor=C_B)),
        Paragraph("<b>EP</b> En proceso (60-69)", ps("n", fontSize=7, textColor=C_EP)),
        Paragraph("<b>I</b> Insuficiente (&lt;60)", ps("n", fontSize=7, textColor=C_I)),
    ]]
    niv_table = Table(niveles_data, colWidths=[W/5]*5)
    niv_table.setStyle(TableStyle([
        ("ALIGN",    (0,0),(-1,-1),"CENTER"),
        ("BOX",      (0,0),(-1,-1),0.3, C_BORDER),
        ("INNERGRID",(0,0),(-1,-1),0.3, C_BORDER),
        ("TOPPADDING",   (0,0),(-1,-1),4),
        ("BOTTOMPADDING",(0,0),(-1,-1),4),
    ]))
    story.append(niv_table)

    # ── Firmas ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 24))
    firma_data = [[
        Paragraph("_______________________________\n<font size='7'>Firma Director/a</font>", ps("firma", fontSize=8, alignment=TA_CENTER)),
        Paragraph("_______________________________\n<font size='7'>Firma Coordinador/a</font>", ps("firma", fontSize=8, alignment=TA_CENTER)),
        Paragraph("_______________________________\n<font size='7'>Firma Padre / Madre / Tutor/a</font>", ps("firma", fontSize=8, alignment=TA_CENTER)),
    ]]
    firma_table = Table(firma_data, colWidths=[W/3]*3)
    firma_table.setStyle(TableStyle([
        ("ALIGN",   (0,0),(-1,-1),"CENTER"),
        ("TOPPADDING",(0,0),(-1,-1),2),
    ]))
    story.append(firma_table)

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 12))
    story.append(HRFlowable(width=W, thickness=0.5, color=C_BORDER))
    story.append(Spacer(1, 4))
    from datetime import date as _date
    story.append(Paragraph(
        f"Generado por Axula · C.E. Benito Juárez · {_date.today().strftime('%d/%m/%Y')} · Ordenanza 04-2023 MINERD",
        ps("footer", fontSize=7, textColor=C_GRAY, alignment=TA_CENTER)
    ))

    # ── Build y respuesta ─────────────────────────────────────────────────────
    doc.build(story)
    buf.seek(0)

    nombre_safe = f"{est.get('nombre','').strip()}_{est.get('apellido','').strip()}".replace(" ","_")
    filename    = f"Boletin_{nombre_safe}_{anio}.pdf"

    from flask import Response
    return Response(
        buf.read(),
        mimetype="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


# ══════════════════════════════════════════════════════════════════════════════
# PERFILES DE PERSONAL (directora, coordinadores, psicólogas, profesores, etc.)
# ══════════════════════════════════════════════════════════════════════════════


# ── MÓDULO DE PROMOCIÓN ──────────────────────────────────────────────────────

ORDEN_GRADOS = ["1ERO", "2DO", "3ERO", "4TO", "5TO", "6TO", "EGRESADO"]


def _siguiente_grado(grado: str) -> str:
    g = grado.strip().upper()
    try:
        idx = ORDEN_GRADOS.index(g)
        return ORDEN_GRADOS[idx + 1] if idx + 1 < len(ORDEN_GRADOS) else "EGRESADO"
    except ValueError:
        return "EGRESADO"


def _calcular_estado_promocion(mats_reprobadas: int) -> str:
    if mats_reprobadas == 0:
        return "PROMOVIDO"
    elif mats_reprobadas <= 2:
        return "CONDICIONADO"
    else:
        return "NO_PROMOVIDO"


@calificaciones_bp.route("/api/coordinador/promocion-preview")
@login_required
@coord_required
def promocion_preview():
    """
    Devuelve la lista de estudiantes de un grado con su estado de promocion calculado
    segun reglas MINERD. No modifica la BD.
    Query params: grado (requerido), anio_escolar (opcional, default actual)
    """
    grado = request.args.get("grado", "").strip().upper()
    if not grado:
        return jsonify({"ok": False, "error": "Parametro grado requerido"}), 400

    anio = request.args.get("anio_escolar") or _anio_escolar_actual()

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row

        estudiantes = conn.execute("""
            SELECT id, nombre, apellido, seccion, curso
            FROM estudiantes
            WHERE UPPER(grado) = ? AND condicion = 'ACTIVO'
            ORDER BY apellido, nombre
        """, (grado,)).fetchall()

        resultado = []
        for est in estudiantes:
            materias = conn.execute("""
                SELECT materia, promedio, tipo
                FROM materias_calificaciones
                WHERE estudiante_id = ? AND anio_escolar = ?
            """, (est["id"], anio)).fetchall()

            total = len(materias)
            reprobadas = [m for m in materias if (m["promedio"] or 0) < 70]
            n_repr = len(reprobadas)
            estado = _calcular_estado_promocion(n_repr)

            prom_existente = conn.execute(
                "SELECT estado FROM promociones WHERE estudiante_id=? AND anio_escolar=?",
                (est["id"], anio)
            ).fetchone()

            resultado.append({
                "id":              est["id"],
                "nombre":          est["nombre"],
                "apellido":        est["apellido"],
                "seccion":         est["seccion"] or "",
                "mencion":         est["curso"] or "",
                "mats_total":      total,
                "mats_aprobadas":  total - n_repr,
                "mats_reprobadas": n_repr,
                "reprobadas":      [m["materia"] for m in reprobadas],
                "estado":          estado,
                "ya_procesado":    prom_existente is not None,
                "estado_previo":   prom_existente["estado"] if prom_existente else None,
            })

    return jsonify({
        "ok":             True,
        "grado":          grado,
        "anio":           anio,
        "siguiente_grado": _siguiente_grado(grado),
        "total":          len(resultado),
        "estudiantes":    resultado,
        "resumen": {
            "promovidos":    sum(1 for r in resultado if r["estado"] == "PROMOVIDO"),
            "condicionados": sum(1 for r in resultado if r["estado"] == "CONDICIONADO"),
            "no_promovidos": sum(1 for r in resultado if r["estado"] == "NO_PROMOVIDO"),
        }
    })


@calificaciones_bp.route("/api/coordinador/promocion-ejecutar", methods=["POST"])
@login_required
@coord_required
def promocion_ejecutar():
    """
    Ejecuta la promocion de los estudiantes seleccionados.
    Body JSON: { grado, anio_escolar, estudiante_ids: [int,...], observacion? }
    Solo actualiza estudiantes con estado PROMOVIDO o CONDICIONADO.
    Guarda registro en tabla promociones.
    """
    data        = request.get_json() or {}
    grado       = (data.get("grado") or "").strip().upper()
    anio        = data.get("anio_escolar") or _anio_escolar_actual()
    ids_sel     = data.get("estudiante_ids", [])
    observacion = data.get("observacion", "")
    ejecutor_id = session.get("usuario_id") or session.get("uid")

    if not grado or not ids_sel:
        return jsonify({"ok": False, "error": "grado y estudiante_ids son requeridos"}), 400

    siguiente = _siguiente_grado(grado)
    promovidos = 0
    condicionados = 0
    errores = []

    with sqlite3.connect(DATABASE, timeout=15) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")

        for est_id in ids_sel:
            try:
                materias = conn.execute("""
                    SELECT promedio FROM materias_calificaciones
                    WHERE estudiante_id=? AND anio_escolar=?
                """, (est_id, anio)).fetchall()

                total  = len(materias)
                n_repr = sum(1 for m in materias if (m["promedio"] or 0) < 70)
                estado = _calcular_estado_promocion(n_repr)

                if estado == "NO_PROMOVIDO":
                    errores.append(f"Estudiante {est_id} no cumple requisitos (NO PROMOVIDO)")
                    continue

                conn.execute(
                    "UPDATE estudiantes SET grado=? WHERE id=?",
                    (siguiente, est_id)
                )

                conn.execute("""
                    INSERT INTO promociones
                        (estudiante_id, grado_origen, grado_destino, anio_escolar,
                         estado, mats_reprobadas, mats_total, ejecutado_por, observacion)
                    VALUES (?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(estudiante_id, anio_escolar) DO UPDATE SET
                        grado_destino=excluded.grado_destino,
                        estado=excluded.estado,
                        mats_reprobadas=excluded.mats_reprobadas,
                        mats_total=excluded.mats_total,
                        ejecutado_por=excluded.ejecutado_por,
                        fecha=datetime('now'),
                        observacion=excluded.observacion
                """, (est_id, grado, siguiente, anio, estado,
                      n_repr, total, ejecutor_id, observacion))

                if estado == "PROMOVIDO":
                    promovidos += 1
                else:
                    condicionados += 1

            except Exception as e:
                errores.append(f"Error estudiante {est_id}: {e}")

        conn.commit()

    return jsonify({
        "ok":           True,
        "mensaje":      f"Promocion ejecutada: {promovidos} promovidos, {condicionados} condicionados -> {siguiente}",
        "promovidos":   promovidos,
        "condicionados": condicionados,
        "siguiente_grado": siguiente,
        "errores":      errores,
    })


