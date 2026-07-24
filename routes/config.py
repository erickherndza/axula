# -*- coding: utf-8 -*-
"""Blueprint: config"""

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
from core.database import get_db, cache_get, cache_set, cache_bust, cache_delete, _CACHE
from core.auth import (
    _hash, _check_password, _normalizar_rol, _ciclo_del_rol,
    login_required, coord_required, admin_required, directora_required,
    _csrf_token, _csrf_check, csrf_protected, rate_limited,
    get_usuario,
)
from core.helpers import *
from core.helpers import _anio_escolar_actual, _get_periodos_estado
from core.ia import _get_groq_client, groq_client, construir_prompt, construir_prompt_planificacion, construir_prompt_rubrica, construir_prompt_estrategia
from core.excel import _parsear_boletin_bj, _buscar_o_crear_estudiante, _detectar_mencion_listado, _limpiar_nota
from core.pdf import _generar_pdf_acuerdo

logger = logging.getLogger("axula")

config_bp = Blueprint("config_bp", __name__)

@config_bp.route("/auditoria")
@login_required
def auditoria_page():
    """Panel de auditoría — exclusivo de la directora."""
    u     = get_usuario()
    rol_n = _normalizar_rol(u.get("rol", ""))
    if rol_n not in ROLES_DIRECTORA:
        return redirect("/")

    anio = _anio_escolar_actual()

    # Valores por defecto — se usan si las tablas aún no existen
    casos_por_estado    = {}
    casos_por_tipo      = {}
    sanciones_aplicadas = []
    tiempo_resolucion   = {}
    casos_criticos      = []
    asistencia_centro   = {}
    top_ausentes        = []
    reportes_por_tipo       = {}
    reportes_por_severidad  = {}
    notif_pendientes    = 0
    usuarios_por_rol    = {}

    try:
        with sqlite3.connect(DATABASE, timeout=10) as conn:
            conn.row_factory = sqlite3.Row

            # ── Casos ──────────────────────────────────────────────────────
            try:
                casos_por_estado = {r["estado"]: r["total"] for r in conn.execute(
                    "SELECT estado, COUNT(*) as total FROM casos GROUP BY estado"
                ).fetchall()}
            except Exception: pass

            try:
                casos_por_tipo = {r["tipo"]: r["total"] for r in conn.execute(
                    "SELECT tipo, COUNT(*) as total FROM casos GROUP BY tipo ORDER BY total DESC"
                ).fetchall()}
            except Exception: pass

            try:
                sanciones_aplicadas = [dict(r) for r in conn.execute("""
                    SELECT a.resultado as sancion, COUNT(*) as total
                    FROM caso_acciones a
                    WHERE a.tipo_accion IN ('resolucion','sancion_formal')
                      AND a.resultado IS NOT NULL AND a.resultado != 'Sin medida disciplinaria'
                    GROUP BY a.resultado ORDER BY total DESC LIMIT 10
                """).fetchall()]
            except Exception: pass

            try:
                t = conn.execute("""
                    SELECT ROUND(AVG(
                        JULIANDAY(cerrado_en) - JULIANDAY(creado_en)
                    ), 1) as promedio_dias
                    FROM casos WHERE estado IN ('Resuelto','Cerrado') AND cerrado_en IS NOT NULL
                """).fetchone()
                tiempo_resolucion = dict(t) if t else {}
            except Exception: pass

            try:
                casos_criticos = [dict(r) for r in conn.execute("""
                    SELECT c.id, c.titulo, c.tipo, c.nivel_escala, c.creado_en,
                           e.nombre || ' ' || e.apellido as estudiante,
                           CAST(JULIANDAY('now') - JULIANDAY(c.creado_en) AS INTEGER) as dias_abierto
                    FROM casos c JOIN estudiantes e ON e.id = c.estudiante_id
                    WHERE c.estado NOT IN ('Resuelto','Cerrado')
                    ORDER BY dias_abierto DESC LIMIT 10
                """).fetchall()]
            except Exception: pass

            # ── Asistencia ─────────────────────────────────────────────────
            try:
                row = conn.execute("""
                    SELECT
                        ROUND(AVG(
                            CAST(SUM(CASE WHEN estado='presente' THEN horas_clase ELSE 0 END) AS REAL)
                            / NULLIF(SUM(horas_clase), 0) * 100
                        ), 1) as pct_promedio,
                        COUNT(DISTINCT estudiante_id) as estudiantes_con_datos,
                        SUM(CASE WHEN estado='ausente' THEN 1 ELSE 0 END) as total_ausencias
                    FROM asistencia
                """).fetchone()
                asistencia_centro = dict(row) if row else {}
            except Exception: pass

            try:
                top_ausentes = [dict(r) for r in conn.execute("""
                    SELECT e.nombre || ' ' || e.apellido as estudiante,
                           e.grado, e.curso, COUNT(*) as total_ausencias
                    FROM asistencia a JOIN estudiantes e ON e.id = a.estudiante_id
                    WHERE a.estado IN ('ausente','A')
                    GROUP BY a.estudiante_id ORDER BY total_ausencias DESC LIMIT 10
                """).fetchall()]
            except Exception: pass

            # ── Reportes ───────────────────────────────────────────────────
            try:
                reportes_por_tipo = {r["tipo"]: r["total"] for r in conn.execute(
                    "SELECT tipo, COUNT(*) as total FROM reportes GROUP BY tipo ORDER BY total DESC"
                ).fetchall()}
            except Exception: pass

            try:
                reportes_por_severidad = {r["severidad"]: r["total"] for r in conn.execute(
                    "SELECT severidad, COUNT(*) as total FROM reportes GROUP BY severidad"
                ).fetchall()}
            except Exception: pass

            # ── Notificaciones y usuarios ──────────────────────────────────
            try:
                notif_pendientes = conn.execute(
                    "SELECT COUNT(*) as total FROM notificaciones WHERE leida=0"
                ).fetchone()["total"]
            except Exception: pass

            try:
                usuarios_por_rol = {r["rol"]: r["total"] for r in conn.execute(
                    "SELECT rol, COUNT(*) as total FROM usuarios WHERE activo=1 GROUP BY rol ORDER BY total DESC"
                ).fetchall()}
            except Exception: pass

    except Exception as ex:
        logger.error(f"[auditoria_page] Error general: {ex}")

    return render_template(
        "auditoria.html",
        current_user          = u,
        anio_escolar          = anio,
        casos_por_estado      = casos_por_estado,
        casos_por_tipo        = casos_por_tipo,
        sanciones_aplicadas   = sanciones_aplicadas,
        tiempo_resolucion     = tiempo_resolucion,
        casos_criticos        = casos_criticos,
        asistencia_centro     = asistencia_centro,
        top_ausentes          = top_ausentes,
        reportes_por_tipo     = reportes_por_tipo,
        reportes_por_severidad= reportes_por_severidad,
        notif_pendientes      = notif_pendientes,
        usuarios_por_rol      = usuarios_por_rol,
    )


@config_bp.route("/api/db/estado")
@login_required
def db_estado():
    """Devuelve conteo de registros por tabla. Solo superusuario."""
    u = get_usuario()
    if not u or _normalizar_rol(u.get("rol","")) != "superusuario":
        return jsonify({"error": "Acceso exclusivo del superusuario"}), 403
    resultado = {}
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        for tabla, meta in DB_TABLAS_META.items():
            try:
                n = conn.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
            except Exception:
                n = 0
            resultado[tabla] = {"label": meta["label"], "registros": n, "icon": meta["icon"]}
    return jsonify({"tablas": resultado})


@config_bp.route("/api/db/purgar", methods=["POST"])
@login_required
def db_purgar():
    """Purga selectiva de tablas. Solo superusuario."""
    u = get_usuario()
    if not u or _normalizar_rol(u.get("rol","")) != "superusuario":
        return jsonify({"error": "Acceso exclusivo del superusuario"}), 403
    d = request.get_json(silent=True) or {}
    if d.get("confirmar") != "CONFIRMAR":
        return jsonify({"error": "Confirmación requerida"}), 400
    tablas_solicitadas = d.get("tablas", [])
    # Solo permitir tablas conocidas para evitar inyección
    tablas_permitidas = set(DB_TABLAS_META.keys())
    tablas_validas = [t for t in tablas_solicitadas if t in tablas_permitidas]
    if not tablas_validas:
        return jsonify({"error": "Ninguna tabla válida seleccionada"}), 400
    errores = []
    purgadas = []
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        for tabla in tablas_validas:
            try:
                conn.execute(f"DELETE FROM {tabla}")
                purgadas.append(tabla)
            except Exception as ex:
                errores.append(f"{tabla}: {str(ex)}")
        conn.commit()
    cache_delete("api_datos_all")
    return jsonify({
        "ok": True,
        "purgadas": purgadas,
        "errores": errores,
        "mensaje": f"{len(purgadas)} tabla(s) purgada(s)."
    })


@config_bp.route("/api/db/purgar-todo", methods=["POST"])
@login_required
def db_purgar_todo():
    """Purga total — borra todos los datos excepto usuarios. Solo superusuario."""
    u = get_usuario()
    if not u or _normalizar_rol(u.get("rol","")) != "superusuario":
        return jsonify({"error": "Acceso exclusivo del superusuario"}), 403
    d = request.get_json(silent=True) or {}
    if d.get("confirmar") != "BORRAR TODO" or not d.get("yo_entiendo"):
        return jsonify({"error": "Confirmación incorrecta"}), 400
    tablas_a_borrar = [t for t in DB_TABLAS_META if t != "recovery_tokens"]
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        for tabla in tablas_a_borrar:
            try:
                conn.execute(f"DELETE FROM {tabla}")
            except Exception as _e:
                logger.warning(f"[config] Excepción silenciada")
        conn.commit()
    cache_delete("api_datos_all")
    return jsonify({
        "ok": True,
        "mensaje": "Base de datos reseteada. Usuarios conservados."
    })


# ── GESTIÓN DE USUARIOS (página) ─────────────────────────────────────────────


@config_bp.route("/usuarios")
@login_required
def vista_usuarios():
    u = get_usuario()
    if _normalizar_rol(u["rol"]) not in ROLES_COORD:
        return redirect("/")
    return render_template("usuarios.html", usuario=u)


# ── EXPORTAR REPORTES PDF ────────────────────────────────────────────────────


@config_bp.route("/api/importar-profesores", methods=["POST"])
@coord_required
def importar_profesores():
    """
    Importa un Excel con columnas:
    nombre | usuario | password | rol | grado | mencion | asignaturas
    Crea o actualiza profesores en lote.
    """
    f = request.files.get("archivo")
    if not f:
        return jsonify({"error": "No se envió archivo"}), 400

    try:
        import pandas as pd
        df = pd.read_excel(f, dtype=str).fillna("")
    except Exception as ex:
        return jsonify({"error": f"No se pudo leer el Excel: {ex}"}), 400

    # Normalize column names
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    requeridas = {"nombre", "usuario"}
    if not requeridas.issubset(set(df.columns)):
        return jsonify({"error": f"El Excel debe tener columnas: nombre, usuario (y opcionalmente: password, rol, grado, mencion, asignaturas)"}), 400

    creados = 0
    actualizados = 0
    errores = []

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        for _, row in df.iterrows():
            try:
                nombre   = str(row.get("nombre", "")).strip()
                username = str(row.get("usuario", "")).strip()
                password = str(row.get("password", "")).strip() or username + "123"
                rol      = str(row.get("rol", "profesor")).strip() or "profesor"
                grado    = str(row.get("grado", "")).strip()
                mencion  = str(row.get("mencion", "")).strip()
                asigs    = str(row.get("asignaturas", "")).strip()
                materia  = asigs.split("|")[0].strip() if asigs else ""

                if not nombre or not username:
                    continue

                existing = conn.execute(
                    "SELECT id FROM usuarios WHERE username=?", (username,)
                ).fetchone()

                if existing:
                    conn.execute("""
                        UPDATE usuarios SET nombre=?, rol=?, grado=?, mencion=?, asignaturas=?, materia=?
                        WHERE username=?
                    """, (nombre, rol, grado, mencion, asigs, materia, username))
                    actualizados += 1
                else:
                    conn.execute("""
                        INSERT INTO usuarios (username,password,nombre,rol,materia,grado,mencion,asignaturas)
                        VALUES (?,?,?,?,?,?,?,?)
                    """, (username, _hash(password), nombre, rol, materia, grado, mencion, asigs))
                    creados += 1
            except Exception as ex:
                errores.append(f"Fila {_}: {ex}")

        conn.commit()

    return jsonify({
        "ok": True,
        "creados": creados,
        "actualizados": actualizados,
        "errores": errores
    })


# ── VALIDACIÓN EN CARGA (hook para cargar-materia) ──────────────────────────


@config_bp.route("/api/audit")
@login_required
def get_audit_log():
    """
    Devuelve el historial de cambios.
    Solo coordinadores y directora pueden ver el log completo.
    ?estudiante_id=   filtra por estudiante
    ?usuario_id=      filtra por quién hizo el cambio
    ?accion=          filtra por tipo de acción
    ?limit=50         límite de resultados (default 100, max 500)
    """
    u = get_usuario()
    rol_n = _normalizar_rol(u.get("rol", ""))
    if rol_n not in ROLES_COORD and not u.get("es_directora"):
        return jsonify({"error": "Sin permisos"}), 403

    est_id   = request.args.get("estudiante_id")
    uid_f    = request.args.get("usuario_id")
    accion_f = request.args.get("accion", "").strip()
    limit    = min(int(request.args.get("limit", 100)), 500)

    sql = """SELECT a.*, 
                    e.nombre AS est_nombre, e.apellido AS est_apellido
             FROM audit_log a
             LEFT JOIN estudiantes e ON e.id = a.entidad_id
                   AND a.accion IN ('registrar_nota','actualizar_nota','recuperacion')
             WHERE 1=1"""
    params = []

    if est_id:
        sql += " AND a.entidad_id=? AND a.accion IN ('registrar_nota','actualizar_nota','recuperacion')"
        params.append(int(est_id))
    if uid_f:
        sql += " AND a.usuario_id=?"; params.append(int(uid_f))
    if accion_f:
        sql += " AND a.accion=?"; params.append(accion_f)

    sql += " ORDER BY a.creado DESC LIMIT ?"
    params.append(limit)

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(sql, params).fetchall()

    return jsonify({
        "ok": True,
        "total": len(rows),
        "registros": [dict(r) for r in rows]
    })


@config_bp.route("/api/audit/estudiante/<int:est_id>")
@login_required
def get_audit_estudiante(est_id):
    """Historial de cambios de un estudiante específico — notas y recuperaciones."""
    u = get_usuario()
    # Coordinadores, directora y el propio profesor que registró pueden ver
    rol_n = _normalizar_rol(u.get("rol", ""))
    puede = (rol_n in ROLES_COORD or u.get("es_directora") or rol_n == "profesor")
    if not puede:
        return jsonify({"error": "Sin permisos"}), 403

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """SELECT * FROM audit_log
               WHERE entidad_id=? AND accion IN ('registrar_nota','actualizar_nota','recuperacion')
               ORDER BY creado DESC LIMIT 200""",
            (est_id,)
        ).fetchall()

    return jsonify({"ok": True, "registros": [dict(r) for r in rows]})


@config_bp.route("/api/roles-disponibles", methods=["GET"])
@login_required
def get_roles_disponibles():
    """Retorna los roles que el usuario actual puede asignar."""
    u   = get_usuario()
    rol = _normalizar_rol(u.get("rol",""))
    if rol == "directora":
        roles = [
            "coordinador_general", "coordinador_primer_ciclo",
            "coordinador_segundo_ciclo", "psicologa_primer_ciclo",
            "psicologa_segundo_ciclo", "profesor"
        ]
    elif rol == "coordinador_general":
        roles = [
            "coordinador_primer_ciclo", "coordinador_segundo_ciclo",
            "psicologa_primer_ciclo", "psicologa_segundo_ciclo", "profesor"
        ]
    elif rol in {"coordinador_primer_ciclo", "coordinador_segundo_ciclo"}:
        roles = ["profesor"]
    else:
        roles = []
    return jsonify(roles)


@config_bp.route("/api/recalcular-promedios", methods=["POST"])
@login_required
def recalcular_promedios():
    """
    Recalcula p_acad, acad_p1..p4 y tiene_notas para TODOS los estudiantes.
    Solo superusuario — operación masiva sobre la base de datos.
    """
    u = get_usuario()
    if not u or _normalizar_rol(u.get("rol","")) != "superusuario":
        return jsonify({"error": "Acceso exclusivo del superusuario"}), 403
    actualizados = 0
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        
        # Detectar columnas disponibles
        cols = {r[1] for r in conn.execute("PRAGMA table_info(estudiantes)").fetchall()}
        
        estudiantes = conn.execute("SELECT id FROM estudiantes").fetchall()
        
        for est_row in estudiantes:
            est_id = est_row['id']
            
            # Notas académicas
            acad = conn.execute("""
                SELECT p1, p2, p3, p4, promedio FROM materias_calificaciones
                WHERE estudiante_id=? AND (tipo='académico' OR tipo IS NULL)
                  AND promedio > 0
            """, (est_id,)).fetchall()
            
            if not acad:
                continue
            
            promedios = [r['promedio'] for r in acad if r['promedio'] and r['promedio'] > 0]
            p1s = [r['p1'] for r in acad if r['p1'] and r['p1'] > 0]
            p2s = [r['p2'] for r in acad if r['p2'] and r['p2'] > 0]
            
            p_acad  = round(sum(promedios)/len(promedios), 2) if promedios else 0
            acad_p1 = round(sum(p1s)/len(p1s), 2) if p1s else 0
            acad_p2 = round(sum(p2s)/len(p2s), 2) if p2s else 0
            
            # Módulos técnicos Multimedia
            MODULO_MAP_RECALC = {
                'fotografi': 'p_foto',
                'lenguaje visual': 'p_lv',
                'diseno': 'p_diseno', 'diseño': 'p_diseno',
            }
            mods_vals = {}
            mats_tecn = conn.execute("""
                SELECT materia, promedio FROM materias_calificaciones
                WHERE estudiante_id=? AND tipo='técnico' AND promedio > 0
            """, (est_id,)).fetchall()
            for mt in mats_tecn:
                mn = mt['materia'].lower()
                for key, col in MODULO_MAP_RECALC.items():
                    if key in mn:
                        mods_vals[col] = mt['promedio']
                        break
            
            try:
                set_parts = ["p_acad=?", "acad_p1=?", "acad_p2=?", "tiene_notas=1"]
                vals = [p_acad, acad_p1, acad_p2]
                
                for col, val in mods_vals.items():
                    if col in cols:
                        set_parts.append(f"{col}=?")
                        vals.append(val)
                
                vals.append(est_id)
                conn.execute(
                    f"UPDATE estudiantes SET {', '.join(set_parts)} WHERE id=?",
                    vals
                )
                actualizados += 1
            except Exception as ex:
                logger.warning(f"[config] {type(ex).__name__}: {ex}")
        
        conn.commit()
    cache_delete("api_datos_all")
    return jsonify({"ok": True, "actualizados": actualizados,
                    "mensaje": f"Promedios recalculados para {actualizados} estudiantes."})


@config_bp.route("/api/dedup-estudiantes", methods=["POST"])
@login_required
def dedup_estudiantes():
    """
    Fusiona estudiantes duplicados (mismo nombre+apellido similares).
    Solo superusuario — modifica registros directamente en la BD.
    """
    u = get_usuario()
    if _normalizar_rol(u.get("rol","")) != "superusuario":
        return jsonify({"error": "Acceso exclusivo del superusuario"}), 403

    import difflib
    eliminados = []

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        todos = conn.execute(
            "SELECT id, nombre, apellido, p_acad, ciclo, seccion, grado FROM estudiantes ORDER BY id"
        ).fetchall()

        procesados = set()
        for i, a in enumerate(todos):
            if a["id"] in procesados: continue
            full_a = f"{a['nombre'] or ''} {a['apellido'] or ''}".lower().strip()
            for b in todos[i+1:]:
                if b["id"] in procesados: continue
                full_b = f"{b['nombre'] or ''} {b['apellido'] or ''}".lower().strip()
                sim = difflib.SequenceMatcher(None, full_a, full_b).ratio()
                if sim >= 0.88:
                    keep = a if (a["p_acad"] or 0) >= (b["p_acad"] or 0) else b
                    drop = b if keep["id"] == a["id"] else a
                    try:
                        conn.execute(
                            "UPDATE materias_calificaciones SET estudiante_id=? WHERE estudiante_id=?",
                            (keep["id"], drop["id"])
                        )
                        conn.execute("DELETE FROM estudiantes WHERE id=?", (drop["id"],))
                        eliminados.append(
                            f"{drop['nombre']} {drop['apellido']} (ID {drop['id']}) → mergeado con ID {keep['id']}"
                        )
                        procesados.add(drop["id"])
                    except Exception as _ex:
                        logger.warning(f"[config] {type(_ex).__name__}: {_ex}")
        conn.commit()

    cache_delete("api_datos_all")
    return jsonify({"ok": True, "eliminados": len(eliminados), "detalle": eliminados[:20]})


@config_bp.route("/api/session-check")
@login_required
def session_check():
    """Debug endpoint — verifica estado de la sesión actual. Requiere autenticación."""
    u = get_usuario()
    return jsonify({
        "ok": True,
        "user_id": u["id"],
        "username": u["username"],
        "rol": u["rol"],
        "csrf_token": _csrf_token(),
    })


@config_bp.route("/api/periodos/estado")
@login_required
def get_periodos_estado():
    """Devuelve el estado de bloqueo de todos los períodos."""
    anio = request.args.get("anio") or _anio_escolar_actual()
    estado = _get_periodos_estado(anio)
    return jsonify({"anio_escolar": anio, "periodos": estado})


@config_bp.route("/api/periodos/bloquear", methods=["POST"])
@coord_required
def bloquear_periodo():
    """
    Bloquea un período — solo coordinador y directora.
    Bloquear impide que los profesores modifiquen calificaciones de ese período.
    """
    u = get_usuario()
    rol_n = _normalizar_rol(u.get("rol", ""))
    if rol_n not in ROLES_COORD and not u.get("es_directora"):
        return jsonify({"error": "Solo coordinadores y directora pueden bloquear períodos"}), 403

    d = request.get_json(silent=True) or {}
    periodo = (d.get("periodo") or "").strip().upper()
    anio    = d.get("anio_escolar") or _anio_escolar_actual()
    motivo  = (d.get("motivo") or "Cierre de período").strip()

    if periodo not in ("P1", "P2", "P3", "P4"):
        return jsonify({"error": "Período inválido. Debe ser P1, P2, P3 o P4"}), 400

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        try:
            conn.execute(
                """INSERT OR REPLACE INTO periodos_bloqueados
                   (periodo, anio_escolar, bloqueado_por, motivo)
                   VALUES (?,?,?,?)""",
                (periodo, anio, u["id"], motivo)
            )
            conn.commit()
        except Exception as ex:
            logger.error(f"[CONFIG] Error bloqueando período: {ex}")
            return jsonify({"error": "Error al bloquear el período. Intenta de nuevo."}), 500

    return jsonify({
        "ok": True,
        "mensaje": f"Período {periodo} bloqueado. Los profesores no podrán modificar calificaciones.",
        "periodo": periodo,
        "anio_escolar": anio
    })


@config_bp.route("/api/periodos/desbloquear", methods=["POST"])
@coord_required
def desbloquear_periodo():
    """Desbloquea un período — solo coordinador y directora."""
    u = get_usuario()
    rol_n = _normalizar_rol(u.get("rol", ""))
    if rol_n not in ROLES_COORD and not u.get("es_directora"):
        return jsonify({"error": "Solo coordinadores y directora pueden desbloquear períodos"}), 403

    d = request.get_json(silent=True) or {}
    periodo = (d.get("periodo") or "").strip().upper()
    anio    = d.get("anio_escolar") or _anio_escolar_actual()

    if periodo not in ("P1", "P2", "P3", "P4"):
        return jsonify({"error": "Período inválido"}), 400

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.execute(
            "DELETE FROM periodos_bloqueados WHERE periodo=? AND anio_escolar=?",
            (periodo, anio)
        )
        conn.commit()

    return jsonify({
        "ok": True,
        "mensaje": f"Período {periodo} desbloqueado. Los profesores pueden modificar calificaciones.",
        "periodo": periodo,
        "anio_escolar": anio
    })


# ── CIERRE / INICIO DE AÑO ESCOLAR ──────────────────────────────────────────


@config_bp.route("/api/config/cerrar-anio-escolar", methods=["POST"])
@coord_required
def cerrar_anio_escolar():
    """
    Cierra el año escolar activo:
      1. Auto-promueve todos los estudiantes PROMOVIDO de todos los grados.
      2. Registra el nuevo año escolar en configuracion_centro.anio_escolar_activo.

    Body JSON:
      { "nuevo_anio": "2026-2027", "observacion": "Cierre año escolar ordinario" }

    Solo coordinador y directora pueden ejecutar esto.
    """
    from core.promocion_engine import evaluar_grado, ejecutar_promocion_estudiante

    u     = get_usuario()
    rol_n = _normalizar_rol(u.get("rol", ""))
    if rol_n not in ROLES_COORD and not u.get("es_directora"):
        return jsonify({"error": "Solo coordinadores y directora pueden cerrar el año escolar"}), 403

    d         = request.get_json(silent=True) or {}
    nuevo_anio = (d.get("nuevo_anio") or "").strip()
    observacion = (d.get("observacion") or "Cierre de año escolar").strip()

    if not nuevo_anio:
        return jsonify({"error": "Debes indicar el nuevo año escolar (ej: 2026-2027)"}), 400

    # Validar formato XXXX-XXXX
    import re as _re
    if not _re.match(r"^\d{4}-\d{4}$", nuevo_anio):
        return jsonify({"error": "Formato inválido. Usa XXXX-XXXX (ej: 2026-2027)"}), 400

    anio_actual = _anio_escolar_actual()

    # No permitir cerrar al mismo año ni a un año anterior
    if nuevo_anio == anio_actual:
        return jsonify({
            "error": f"El nuevo año ({nuevo_anio}) no puede ser igual al año actual. "
                     f"Ingresa el año siguiente, ej: {nuevo_anio.split('-')[1]}-{int(nuevo_anio.split('-')[1])+1}"
        }), 400
    try:
        _p_actual = int(anio_actual.split("-")[0])
        _p_nuevo  = int(nuevo_anio.split("-")[0])
        if _p_nuevo < _p_actual:
            return jsonify({
                "error": f"No se puede retroceder el año escolar ({nuevo_anio} < {anio_actual})."
            }), 400
    except Exception:
        pass

    GRADOS = ["1ERO", "2DO", "3RO", "4TO", "5TO", "6TO"]
    resumen = {}   # {grado: {promovidos, skipped, errores}}
    total_promovidos = 0

    try:
        with sqlite3.connect(DATABASE, timeout=30) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")

            # ── FASE 1: evaluar todos los grados SIN escribir ─────────────────
            # CRÍTICO: evaluar primero, ejecutar después.
            # Si evaluamos y ejecutamos grado por grado en orden ascendente,
            # un alumno promovido de 4TO→5TO aparece en el loop de 5TO y se
            # promueve de nuevo a 6TO (efecto dominó).
            # La fase 1 captura el estado real de TODOS los alumnos antes de
            # que cualquier promoción cambie su grado en la BD.
            plan: dict[str, list[dict]] = {}   # {grado: [resultados evaluar_grado]}
            for grado in GRADOS:
                plan[grado] = evaluar_grado(conn, grado, anio_actual)

            # ── FASE 2: ejecutar promociones con el plan ya fijo ──────────────
            for grado in GRADOS:
                g_prom = 0
                g_skip = 0
                g_err  = []

                for est in plan[grado]:
                    if est.get("estado") != "PROMOVIDO":
                        g_skip += 1
                        continue
                    est_id_val = est.get("est_id") or est.get("id")
                    try:
                        res = ejecutar_promocion_estudiante(
                            conn,
                            est_id_val,
                            anio_actual,
                            u["id"],
                            observacion=observacion,
                        )
                        if res.get("ok"):
                            g_prom += 1
                            total_promovidos += 1
                        else:
                            g_err.append({"id": est_id_val, "nombre": est.get("nombre", "?"), "error": res.get("error")})
                    except Exception as ex:
                        g_err.append({"id": est_id_val, "nombre": est.get("nombre", "?"), "error": str(ex)})

                resumen[grado] = {
                    "promovidos": g_prom,
                    "no_promovidos_skipped": g_skip,
                    "errores": g_err,
                    "total": len(plan[grado]),
                }

            # Resetear asistencia de repitientes (ACTIVO) para el nuevo año.
            # NO se borran KPIs de notas — los repitientes mantienen su historial
            # visible hasta que el digitador registre las del nuevo año.
            # Los KPIs de promovidos ya se resetean en ejecutar_promocion_estudiante().
            conn.execute("""
                UPDATE estudiantes
                SET asistencia_p1 = NULL,
                    asistencia_p2 = NULL,
                    asistencia_p3 = NULL,
                    asistencia_p4 = NULL
                WHERE condicion = 'ACTIVO'
            """)

            # Actualizar el año escolar activo
            conn.execute(
                """UPDATE configuracion_centro
                   SET anio_escolar_activo = ?
                   WHERE id = 1""",
                (nuevo_anio,)
            )
            conn.commit()

    except Exception as ex:
        logger.error(f"[cerrar_anio_escolar] Error: {ex}")
        return jsonify({"ok": False, "error": f"Error interno: {ex}"}), 500

    # Registrar en auditoría
    try:
        with sqlite3.connect(DATABASE, timeout=10) as conn:
            conn.execute(
                """INSERT INTO audit_log (usuario_id, accion, entidad, detalle, creado)
                   VALUES (?, 'cerrar_anio_escolar', 'configuracion_centro',
                           ?, datetime('now'))""",
                (u["id"], _json.dumps({
                    "anio_anterior": anio_actual,
                    "nuevo_anio": nuevo_anio,
                    "total_promovidos": total_promovidos,
                    "observacion": observacion,
                }, ensure_ascii=False))
            )
            conn.commit()
    except Exception:
        pass

    return jsonify({
        "ok": True,
        "anio_anterior": anio_actual,
        "nuevo_anio": nuevo_anio,
        "total_promovidos": total_promovidos,
        "resumen_por_grado": resumen,
        "mensaje": (
            f"Año escolar cerrado. {total_promovidos} estudiante(s) promovido(s). "
            f"El sistema ahora opera en {nuevo_anio}."
        ),
    })


@config_bp.route("/api/promocion/pendientes-mencion")
@coord_required
def pendientes_mencion():
    anio = request.args.get("anio_escolar") or _anio_escolar_actual()
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT e.id, e.nombre, e.apellido, e.curso, e.seccion,
                   p.estado
            FROM estudiantes e
            JOIN promociones p ON p.estudiante_id = e.id
              AND p.anio_escolar = ?
              AND p.estado = 'PROMOVIDO'
            WHERE UPPER(e.grado) IN ('3RO','3ERO')
              AND e.condicion = 'ACTIVO'
            ORDER BY e.apellido, e.nombre
        """, (anio,)).fetchall()
    return jsonify({"ok": True, "estudiantes": [dict(r) for r in rows]})


@config_bp.route("/api/estudiantes/<int:est_id>/mencion", methods=["POST"])
@coord_required
def asignar_mencion(est_id):
    u = get_usuario()
    d = request.get_json(silent=True) or {}
    mencion = (d.get("mencion") or "").strip().upper()
    MENCIONES_VALIDAS = {"MULTIMEDIA", "TEATRO", "MÚSICA", "MUSICA", "ARTES VISUALES", "DANZA"}
    if mencion not in MENCIONES_VALIDAS:
        return jsonify({"error": f"Mención inválida: {mencion}"}), 400
    # Normalize: MUSICA → MÚSICA
    if mencion == "MUSICA":
        mencion = "MÚSICA"
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        est = conn.execute("SELECT grado, curso FROM estudiantes WHERE id=?", (est_id,)).fetchone()
        if not est:
            return jsonify({"error": "Estudiante no encontrado"}), 404
        grado = (est["grado"] or "").strip().upper()
        nuevo_curso = f"{grado} {mencion}".strip()
        conn.execute("UPDATE estudiantes SET curso=? WHERE id=?", (nuevo_curso, est_id))
        try:
            conn.execute("""INSERT INTO audit_log (usuario_id, accion, entidad, entidad_id, detalle, creado)
                           VALUES (?, 'asignar_mencion', 'estudiantes', ?, ?, datetime('now'))""",
                        (u["id"], est_id, _json.dumps({"mencion": mencion, "nuevo_curso": nuevo_curso})))
        except Exception:
            pass
        conn.commit()
    return jsonify({"ok": True, "nuevo_curso": nuevo_curso})


@config_bp.route("/api/config/anio-escolar-activo", methods=["GET"])
@login_required
def get_anio_escolar_activo():
    """Retorna el año escolar activo configurado."""
    anio = _anio_escolar_actual()
    return jsonify({"ok": True, "anio_escolar_activo": anio})


@config_bp.route("/api/config/anio-escolar-activo", methods=["POST"])
@coord_required
def set_anio_escolar_activo():
    """
    Cambia el año escolar activo sin promover estudiantes.
    Útil para correcciones o para iniciar el año sin auto-promover.

    Body JSON: { "anio_escolar": "2026-2027" }
    """
    u     = get_usuario()
    rol_n = _normalizar_rol(u.get("rol", ""))
    if rol_n not in ROLES_COORD and not u.get("es_directora"):
        return jsonify({"error": "Sin permisos"}), 403

    d    = request.get_json(silent=True) or {}
    anio = (d.get("anio_escolar") or "").strip()

    import re as _re
    if not _re.match(r"^\d{4}-\d{4}$", anio):
        return jsonify({"error": "Formato inválido. Usa XXXX-XXXX (ej: 2026-2027)"}), 400

    try:
        with sqlite3.connect(DATABASE, timeout=10) as conn:
            conn.execute(
                "UPDATE configuracion_centro SET anio_escolar_activo = ? WHERE id = 1",
                (anio,)
            )
            conn.commit()
    except Exception as ex:
        return jsonify({"ok": False, "error": str(ex)}), 500

    return jsonify({"ok": True, "anio_escolar_activo": anio,
                    "mensaje": f"Año escolar activo actualizado a {anio}."})


