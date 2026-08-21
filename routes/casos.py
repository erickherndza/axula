# -*- coding: utf-8 -*-
"""Blueprint: casos"""

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
from core.helpers import _anio_escolar_actual, _anonimizar_estudiante, _audit, _crear_notificacion, _get_config_centro
from core.ia import _get_groq_client, groq_client, construir_prompt, construir_prompt_planificacion, construir_prompt_rubrica, construir_prompt_estrategia, generar_con_fallback
from core.excel import _parsear_boletin_bj, _buscar_o_crear_estudiante, _detectar_mencion_listado, _limpiar_nota
from core.pdf import _generar_pdf_acuerdo
from core import rls as _rls

logger = logging.getLogger("axula")

casos_bp = Blueprint("casos_bp", __name__)

@casos_bp.route("/casos")
@login_required
def casos_page():
    """Panel de gestión de casos — psicólogas, coordinadores y directora."""
    u = get_usuario()
    rol_n = _normalizar_rol(u.get("rol", ""))

    # Sanciones disponibles según el nivel del cargo (MINERD — Normas de Convivencia)
    es_directora  = rol_n in ROLES_SUPER or u.get("es_directora")
    es_coord      = rol_n in ROLES_COORD and not es_directora
    es_psicologa  = rol_n in ROLES_PSICOLOGA

    SANCIONES_PSICOLOGA = [
        ("", "Ninguna — Caso resuelto positivamente"),
        ("amonestacion_verbal", "Amonestación verbal (Falta leve)"),
        ("amonestacion_escrita", "Amonestación escrita (Falta leve reincidente)"),
    ]
    SANCIONES_COORD = SANCIONES_PSICOLOGA + [
        ("suspension_1_3", "Suspensión 1-3 días (Falta grave)"),
        ("plan_mejora", "Plan de mejora académica / conductual"),
        ("traslado", "Traslado de sección (por acuerdo)"),
    ]
    SANCIONES_DIRECTORA = SANCIONES_COORD + [
        ("suspension_4_7", "Suspensión 4-7 días (Falta muy grave)"),
        ("acuerdo_compromiso_formal", "Acuerdo-Compromiso con firma de padres"),
        ("proceso_disciplinario", "Proceso disciplinario formal ante el Distrito Educativo"),
        ("exclusion_temporal", "Exclusión temporal (requiere aprobación MINERD)"),
    ]

    if es_directora:
        sanciones = SANCIONES_DIRECTORA
    elif es_coord:
        sanciones = SANCIONES_COORD
    else:
        sanciones = SANCIONES_PSICOLOGA

    return render_template(
        "casos.html",
        current_user  = u,
        es_directora  = es_directora,
        es_coord      = es_coord,
        es_psicologa  = es_psicologa,
        sanciones     = sanciones,
        nivel_usuario = 3 if es_directora else 2 if es_coord else 1,
    )


@casos_bp.route("/api/casos")
@login_required
def listar_casos():
    u = get_usuario()
    rol_n = _normalizar_rol(u.get("rol", ""))
    est_id = request.args.get("estudiante_id", "")
    estado = request.args.get("estado", "")

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        q = """
            SELECT c.*,
                   e.nombre as est_nombre, e.apellido as est_apellido,
                   e.grado, e.curso,
                   u.nombre as abierto_por_nombre
            FROM casos c
            JOIN estudiantes e ON e.id = c.estudiante_id
            JOIN usuarios u    ON u.id = c.abierto_por
            WHERE 1=1
        """
        params = []
        # Psicóloga: solo ve casos de su ciclo
        if rol_n in ROLES_PSICOLOGA:
            ciclo = _ciclo_del_rol(rol_n)
            if ciclo:
                q += " AND e.ciclo=?"
                params.append(ciclo)
        if est_id:
            q += " AND c.estudiante_id=?"
            params.append(int(est_id))
        if estado:
            q += " AND c.estado=?"
            params.append(estado)
        q += " ORDER BY c.creado_en DESC LIMIT 200"
        rows = conn.execute(q, params).fetchall()
    return jsonify([dict(r) for r in rows])


@casos_bp.route("/api/casos", methods=["POST"])
@login_required
def crear_caso():
    u = get_usuario()
    d = request.get_json(silent=True) or {}
    est_id = d.get("estudiante_id")
    tipo   = d.get("tipo", "conducta")
    titulo = (d.get("titulo") or "").strip()
    desc   = (d.get("descripcion") or "").strip()
    if not est_id or not titulo:
        return jsonify({"error": "estudiante_id y titulo son requeridos"}), 400

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("""
            INSERT INTO casos (estudiante_id, abierto_por, tipo, titulo, descripcion,
                               origen_tipo, origen_id)
            VALUES (?,?,?,?,?,?,?)
        """, (est_id, u["id"], tipo, titulo, desc,
              d.get("origen_tipo"), d.get("origen_id")))
        conn.commit()
        caso_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    return jsonify({"ok": True, "id": caso_id})


@casos_bp.route("/api/casos/<int:cid>")
@login_required
def get_caso(cid):
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        caso = conn.execute("""
            SELECT c.*, e.nombre as est_nombre, e.apellido as est_apellido,
                   e.grado, e.curso, e.ciclo,
                   u.nombre as abierto_por_nombre
            FROM casos c
            JOIN estudiantes e ON e.id = c.estudiante_id
            JOIN usuarios u    ON u.id = c.abierto_por
            WHERE c.id=?
        """, (cid,)).fetchone()
        if not caso:
            return jsonify({"error": "Caso no encontrado"}), 404

        acciones = conn.execute("""
            SELECT a.*, u.nombre as actor_nombre, u.rol as actor_rol
            FROM caso_acciones a
            JOIN usuarios u ON u.id = a.actor_id
            WHERE a.caso_id=?
            ORDER BY a.creado_en ASC
        """, (cid,)).fetchall()

    return jsonify({
        "caso": dict(caso),
        "acciones": [dict(a) for a in acciones]
    })


@casos_bp.route("/api/casos/<int:cid>/accion", methods=["POST"])
@login_required
def agregar_accion_caso(cid):
    u = get_usuario()
    d = request.get_json(silent=True) or {}
    tipo_accion  = d.get("tipo_accion", "nota")
    descripcion  = (d.get("descripcion") or "").strip()
    fecha_prog   = d.get("fecha_programada", "")
    participantes= d.get("participantes", [])
    resultado    = (d.get("resultado") or "").strip()
    nuevo_estado = d.get("nuevo_estado", "")

    if not descripcion:
        return jsonify({"error": "La descripción es requerida"}), 400

    import json as _j
    ESCALA_NIVEL = {
        "nota": 1, "cita": 1,
        "reunion_profesor": 2, "reunion_coordinador": 2,
        "reunion_padres": 3, "escalar": 3,
        "acuerdo": 2, "resolucion": 1
    }

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        caso = conn.execute("SELECT * FROM casos WHERE id=?", (cid,)).fetchone()
        if not caso:
            return jsonify({"error": "Caso no encontrado"}), 404

        conn.execute("""
            INSERT INTO caso_acciones
                (caso_id, actor_id, tipo_accion, descripcion,
                 fecha_programada, participantes, resultado)
            VALUES (?,?,?,?,?,?,?)
        """, (cid, u["id"], tipo_accion, descripcion,
              fecha_prog or None,
              _j.dumps(participantes, ensure_ascii=False) if participantes else None,
              resultado or None))

        # Actualizar estado y nivel del caso si corresponde
        updates = {"actualizado_en": "datetime('now')"}
        if nuevo_estado and nuevo_estado != caso["estado"]:
            conn.execute("UPDATE casos SET estado=? WHERE id=?", (nuevo_estado, cid))

        # Escalar nivel automáticamente
        nivel_accion = ESCALA_NIVEL.get(tipo_accion, 1)
        if nivel_accion > (caso["nivel_escala"] or 1):
            conn.execute("UPDATE casos SET nivel_escala=? WHERE id=?",
                        (nivel_accion, cid))

        conn.commit()
        accion_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        # Notificar al coordinador si se escaló
        if tipo_accion in ("reunion_coordinador", "escalar", "reunion_padres"):
            est = conn.execute(
                "SELECT ciclo FROM estudiantes WHERE id=?",
                (caso["estudiante_id"],)
            ).fetchone()
            ciclo_est = (est["ciclo"] if est else "") or "segundo_ciclo"
            rol_coord = ("coordinador_segundo_ciclo"
                        if ciclo_est == "segundo_ciclo"
                        else "coordinador_primer_ciclo")
            coord = conn.execute(
                "SELECT id FROM usuarios WHERE rol=? AND activo=1 LIMIT 1",
                (rol_coord,)
            ).fetchone()
            if coord:
                est_full = conn.execute(
                    "SELECT nombre, apellido FROM estudiantes WHERE id=?",
                    (caso["estudiante_id"],)
                ).fetchone()
                nombre_est = f"{est_full['nombre']} {est_full['apellido']}".strip() if est_full else ""
                _crear_notificacion(
                    conn, coord["id"], "caso", cid, caso["estudiante_id"],
                    f"📌 Caso escalado — {nombre_est}",
                    f"La psicóloga escaló el caso: {caso['titulo']}. "
                    f"Acción registrada: {tipo_accion}. {descripcion}"
                )
                conn.commit()

    return jsonify({"ok": True, "accion_id": accion_id})


@casos_bp.route("/api/casos/<int:cid>/cerrar", methods=["POST"])
@login_required
def cerrar_caso(cid):
    u     = get_usuario()
    rol_n = _normalizar_rol(u.get("rol", ""))
    d     = request.get_json(silent=True) or {}

    descripcion  = (d.get("descripcion") or "").strip()
    sancion      = (d.get("sancion") or "").strip()
    seguimiento  = (d.get("seguimiento") or "ninguno").strip()

    if not descripcion:
        return jsonify({"error": "La resolución final es requerida"}), 400

    # ── Validar que la sanción corresponde al nivel del rol (Prioridad 1) ──
    SANCIONES_COORD = {
        "", "amonestacion_verbal", "amonestacion_escrita",
        "suspension_1_3", "plan_mejora", "traslado"
    }
    SANCIONES_DIRECTORA = SANCIONES_COORD | {
        "suspension_4_7", "acuerdo_compromiso_formal",
        "proceso_disciplinario", "exclusion_temporal"
    }
    es_directora = rol_n in ROLES_SUPER or u.get("es_directora")
    es_coord     = rol_n in ROLES_COORD and not es_directora
    es_psicologa = rol_n in ROLES_PSICOLOGA

    if sancion:
        sanciones_permitidas = SANCIONES_DIRECTORA if es_directora else \
                               SANCIONES_COORD     if es_coord     else \
                               {"", "amonestacion_verbal", "amonestacion_escrita"}
        if sancion not in sanciones_permitidas:
            return jsonify({
                "error": f"La medida '{sancion}' excede el nivel de tu cargo. Escala el caso al nivel superior."
            }), 403

    # Etiqueta legible para el expediente
    SANCION_LABELS = {
        "": "Ninguna",
        "amonestacion_verbal":        "Amonestación verbal",
        "amonestacion_escrita":       "Amonestación escrita",
        "suspension_1_3":             "Suspensión 1-3 días",
        "suspension_4_7":             "Suspensión 4-7 días",
        "plan_mejora":                "Plan de mejora",
        "traslado":                   "Traslado de sección",
        "acuerdo_compromiso_formal":  "Acuerdo-Compromiso con familia",
        "proceso_disciplinario":      "Proceso disciplinario ante el Distrito",
        "exclusion_temporal":         "Exclusión temporal",
    }
    sancion_label = SANCION_LABELS.get(sancion, sancion)

    # Texto completo para el timeline
    resolucion_txt = descripcion
    if sancion:
        resolucion_txt += f"\n\n📋 Medida aplicada: {sancion_label}"
    if seguimiento and seguimiento != "ninguno":
        seg_labels = {
            "monitoreo_mensual": "Monitoreo mensual de asistencia",
            "cita_seguimiento":  "Cita de seguimiento en 30 días",
            "reunion_padres":    "Reunión periódica con familia",
            "plan_activo":       "Plan de mejora activo",
        }
        resolucion_txt += f"\n🔔 Seguimiento: {seg_labels.get(seguimiento, seguimiento)}"

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row

        # Verificar que el caso existe
        caso = conn.execute("SELECT * FROM casos WHERE id=?", (cid,)).fetchone()
        if not caso:
            return jsonify({"error": "Caso no encontrado"}), 404

        # Actualizar el caso con sanción estructurada
        conn.execute("""
            UPDATE casos
               SET estado       = 'Resuelto',
                   cerrado_en   = date('now')
             WHERE id=?
        """, (cid,))

        # Registrar en timeline como acción de resolución
        conn.execute("""
            INSERT INTO caso_acciones
                (caso_id, actor_id, tipo_accion, descripcion, resultado)
            VALUES (?,?,'resolucion',?,?)
        """, (cid, u["id"], resolucion_txt, sancion_label if sancion else "Sin medida disciplinaria"))

        # Si hay sanción formal, también registrarla como acción separada destacada
        if sancion and sancion not in ("", "amonestacion_verbal", "amonestacion_escrita"):
            conn.execute("""
                INSERT INTO caso_acciones
                    (caso_id, actor_id, tipo_accion, descripcion)
                VALUES (?,?,'sancion_formal',?)
            """, (cid, u["id"],
                  f"⚖️ MEDIDA DISCIPLINARIA FORMAL: {sancion_label} — Aplicada por {u.get('nombre','')}, {u.get('rol','')}"))

        conn.commit()

    return jsonify({"ok": True, "sancion": sancion_label})


# ── ACUERDO-COMPROMISO ────────────────────────────────────────────────────────


@casos_bp.route("/api/acuerdo-compromiso/generar", methods=["POST"])
@login_required
@rate_limited(max_calls=10, window=60)
def generar_acuerdo_compromiso():
    """
    Genera un Acuerdo-Compromiso usando LLaMA 3.3 basado en el expediente
    del estudiante y el historial del caso. Alineado a normativa MINERD RD.
    """
    u = get_usuario()
    rol_n = _normalizar_rol(u.get("rol", ""))
    if rol_n not in ROLES_PSICOLOGA and rol_n not in ROLES_COORD and not u.get("es_directora"):
        return jsonify({"error": "Sin permisos para generar acuerdos"}), 403

    d = request.get_json(silent=True) or {}
    caso_id    = d.get("caso_id")
    est_id     = d.get("estudiante_id")
    adicional  = (d.get("contexto_adicional") or "").strip()

    if not est_id:
        return jsonify({"error": "estudiante_id es requerido"}), 400

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        est = conn.execute("SELECT * FROM estudiantes WHERE id=?", (est_id,)).fetchone()
        if not est:
            return jsonify({"error": "Estudiante no encontrado"}), 404
        e = dict(est)

        # Obtener historial del caso si existe
        acciones_txt = ""
        caso_titulo  = ""
        caso_tipo    = ""
        if caso_id:
            caso = conn.execute("SELECT * FROM casos WHERE id=?", (caso_id,)).fetchone()
            if caso:
                caso_titulo = caso["titulo"]
                caso_tipo   = caso["tipo"]
                acciones = conn.execute("""
                    SELECT a.tipo_accion, a.descripcion, a.fecha_accion, u.nombre as actor
                    FROM caso_acciones a JOIN usuarios u ON u.id=a.actor_id
                    WHERE a.caso_id=? ORDER BY a.creado_en ASC
                """, (caso_id,)).fetchall()
                acciones_txt = "\n".join(
                    f"- [{r['fecha_accion']}] {r['actor']} ({r['tipo_accion']}): {r['descripcion']}"
                    for r in acciones
                )

        # Obtener reportes recientes
        reportes = conn.execute("""
            SELECT tipo, titulo, descripcion, severidad, fecha
            FROM reportes WHERE estudiante_id=?
            ORDER BY fecha DESC LIMIT 5
        """, (est_id,)).fetchall()
        rep_txt = "\n".join(
            f"- [{r['fecha']}] {r['tipo'].upper()} ({r['severidad']}): {r['titulo']}"
            for r in reportes
        ) or "Sin reportes recientes."

        # Número correlativo del acuerdo
        n_acuerdos = conn.execute(
            "SELECT COUNT(*) FROM acuerdos_compromiso"
        ).fetchone()[0] + 1
        numero_acuerdo = f"AC-{_anio_escolar_actual().split('-')[0]}-{n_acuerdos:03d}"

    nombre_est = f"{e.get('nombre','')} {e.get('apellido','')}".strip()
    grado_est  = f"{e.get('grado','')} {e.get('curso','')}"
    _cfg_caso  = _get_config_centro()
    _centro_nombre = _cfg_caso.get("nombre", "Centro Educativo")

    prompt = f"""Eres un orientador escolar del MINERD (Ministerio de Educación de la República Dominicana).
Genera un Acuerdo-Compromiso Escolar formal y completo basado en los siguientes datos.

DATOS DEL ESTUDIANTE:
- Código: {_anonimizar_estudiante(est_id)}
- Grado: {grado_est}
- Centro: {_centro_nombre}

SITUACIÓN (caso tipo: {caso_tipo or 'general'}):
{caso_titulo or 'Situación escolar que requiere compromiso'}

HISTORIAL DE ACCIONES DEL CASO:
{acciones_txt or 'Sin acciones previas registradas.'}

REPORTES PREVIOS:
{rep_txt}

CONTEXTO ADICIONAL:
{adicional or 'Ninguno.'}

Genera el Acuerdo-Compromiso con estas secciones exactas en español formal:
1. ENCABEZADO (con número {numero_acuerdo}, fecha, centro, datos del estudiante)
2. ANTECEDENTES (resumen objetivo de la situación basado en el historial)
3. COMPROMISOS DEL/LA ESTUDIANTE (lista numerada de 4-6 compromisos específicos y medibles)
4. COMPROMISOS DE LA FAMILIA/TUTOR (lista numerada de 3-4 compromisos)
5. COMPROMISOS DEL CENTRO EDUCATIVO (lista numerada de 3 compromisos del centro)
6. BASE LEGAL (citar Ley 66-97, Ley 136-03 Art. 50, Normas de Convivencia Armoniosa MINERD)
7. CONSECUENCIAS DEL INCUMPLIMIENTO (redactado de forma constructiva, no punitiva)
8. FIRMAS (espacios para: Estudiante, Padre/Madre/Tutor, Director/a, Orientador/a Psicológica, Fecha)

Tono: formal, respetuoso, orientado a la solución. Lenguaje dominicano oficial educativo.
Devuelve SOLO el texto del acuerdo, sin comentarios adicionales."""

    try:
        contenido = generar_con_fallback(
            prompt,
            prompt_sistema="Eres un especialista en normativa educativa dominicana (MINERD). Generas documentos formales precisos alineados a la legislación vigente.",
            temperature=0.4,
            max_tokens=2000,
        )
    except Exception as ex:
        logger.error(f"[IA] Error generando acuerdo: {ex}")
        return jsonify({"error": "Error al generar el acuerdo. Intenta de nuevo."}), 500

    # Guardar en BD
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.execute("""
            INSERT INTO acuerdos_compromiso
                (caso_id, estudiante_id, generado_por, numero_acuerdo,
                 base_legal, contenido_completo)
            VALUES (?,?,?,?,?,?)
        """, (
            caso_id or None, est_id, u["id"], numero_acuerdo,
            "Ley 66-97; Ley 136-03 Art.50; Normas de Convivencia Armoniosa MINERD",
            contenido
        ))
        conn.commit()
        ac_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        # Registrar como acción en el caso
        if caso_id:
            conn.execute("""
                INSERT INTO caso_acciones
                    (caso_id, actor_id, tipo_accion, descripcion)
                VALUES (?,?,'acuerdo',?)
            """, (caso_id, u["id"],
                  f"Acuerdo-Compromiso generado: {numero_acuerdo}"))
            conn.commit()

    return jsonify({
        "ok": True,
        "id": ac_id,
        "numero": numero_acuerdo,
        "contenido": contenido
    })


@casos_bp.route("/api/acuerdo-compromiso/<int:acid>")
@login_required
def get_acuerdo(acid):
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("""
            SELECT ac.*, e.nombre as est_nombre, e.apellido as est_apellido,
                   e.grado, e.curso, u.nombre as generado_por_nombre
            FROM acuerdos_compromiso ac
            JOIN estudiantes e ON e.id = ac.estudiante_id
            JOIN usuarios u    ON u.id = ac.generado_por
            WHERE ac.id=?
        """, (acid,)).fetchone()
    if not row:
        return jsonify({"error": "Acuerdo no encontrado"}), 404
    return jsonify(dict(row))


# ══════════════════════════════════════════════════════════════════════════════
#  FIRMAS DIGITALES — Acuerdos-Compromiso
# ══════════════════════════════════════════════════════════════════════════════


@casos_bp.route("/api/acuerdo-compromiso/<int:acid>/solicitar-firma", methods=["POST"])
@login_required
def solicitar_firma(acid):
    """
    Genera un token único para que el padre/tutor firme desde su teléfono.
    Devuelve la URL de firma que se puede enviar por WhatsApp o email.
    """
    u = get_usuario()
    rol_n = _normalizar_rol(u.get("rol", ""))
    if rol_n not in ROLES_PSICOLOGA and rol_n not in ROLES_COORD and not u.get("es_directora"):
        return jsonify({"error": "Sin permisos"}), 403

    import secrets as _sec
    token = _sec.token_urlsafe(32)

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        acuerdo = conn.execute(
            "SELECT id, numero_acuerdo, estudiante_id FROM acuerdos_compromiso WHERE id=?", (acid,)
        ).fetchone()
        if not acuerdo:
            return jsonify({"error": "Acuerdo no encontrado"}), 404
        conn.execute(
            "UPDATE acuerdos_compromiso SET token_firma=? WHERE id=?",
            (token, acid)
        )

    url_firma = f"{request.host_url.rstrip('/')}/firma/{acid}/{token}"
    return jsonify({
        "ok": True,
        "token": token,
        "url_firma": url_firma,
        "mensaje": f"Envía este enlace al padre/tutor para que firme digitalmente el {acuerdo['numero_acuerdo'] or 'acuerdo'}"
    })


@casos_bp.route("/api/acuerdo-compromiso/<int:acid>/guardar-firma", methods=["POST"])
@rate_limited(max_calls=5, window=300)
def guardar_firma(acid):
    """
    Guarda la firma digital (imagen base64 del canvas).
    Puede ser llamado sin login usando el token (por el padre)
    o con login por coordinador/psicóloga/directora.
    Body: { token?, rol_firmante, firma_data (data URL base64) }
    """
    d = request.get_json(force=True) or {}
    token      = d.get("token", "").strip()
    firma_data = d.get("firma_data", "").strip()

    if not firma_data or not firma_data.startswith("data:image/"):
        return jsonify({"ok": False, "error": "Firma inválida"}), 400

    # Limitar tamaño (base64 de ~300KB máx)
    if len(firma_data) > 400_000:
        return jsonify({"ok": False, "error": "Imagen de firma demasiado grande"}), 400

    # Mapa rol → campo de BD (solo estos 4 son válidos)
    CAMPOS = {
        "tutor":        "firma_tutor",
        "coordinador":  "firma_coordinador",
        "psicologa":    "firma_psicologa",
        "director":     "firma_director",
    }
    # Mapa rol de sesión → rol de firmante permitido
    ROL_SESION_A_FIRMANTE = {
        "coordinador":         "coordinador",
        "coordinador_general": "coordinador",
        "directora":           "director",
        "psicologa":           "psicologa",
        "superusuario":        "coordinador",
    }

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row

        # ── Rama token (padre/tutor sin login) ──
        if token:
            ac = conn.execute(
                "SELECT id, token_firma, firma_tutor FROM acuerdos_compromiso WHERE id=?",
                (acid,)
            ).fetchone()
            if not ac or ac["token_firma"] != token:
                return jsonify({"ok": False, "error": "Token inválido"}), 403
            # Forzar rol en servidor — nunca tomar del body
            rol_firmante = "tutor"
            if ac["firma_tutor"]:
                return jsonify({"ok": False, "error": "Ya fue firmado por el tutor"}), 400

        # ── Rama sesión (staff autenticado) ──
        else:
            u = get_usuario()
            if not u:
                return jsonify({"ok": False, "error": "No autenticado"}), 401
            from core.auth import _normalizar_rol
            rol_sesion = _normalizar_rol(u.get("rol", ""))
            rol_firmante = ROL_SESION_A_FIRMANTE.get(rol_sesion)
            if not rol_firmante:
                return jsonify({"ok": False, "error": "Tu rol no puede firmar acuerdos"}), 403

    campo = CAMPOS.get(rol_firmante)
    if not campo:
        return jsonify({"ok": False, "error": "Rol de firmante inválido"}), 400

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row

        # Guardar firma
        conn.execute(
            f"UPDATE acuerdos_compromiso SET {campo}=? WHERE id=?",
            (firma_data, acid)
        )

        # Verificar si todas las firmas requeridas ya están
        ac_updated = conn.execute(
            "SELECT firma_tutor, firma_coordinador, firma_psicologa FROM acuerdos_compromiso WHERE id=?",
            (acid,)
        ).fetchone()
        todas_firmadas = all([
            ac_updated["firma_tutor"],
            ac_updated["firma_coordinador"] or ac_updated["firma_psicologa"],
        ])
        if todas_firmadas:
            from datetime import date as _d
            conn.execute(
                "UPDATE acuerdos_compromiso SET firmado=1, fecha_firma=? WHERE id=?",
                (_d.today().isoformat(), acid)
            )

    _audit("firma_acuerdo", f"Acuerdo {acid} — firma de {rol_firmante}", "acuerdos_compromiso", acid)

    return jsonify({
        "ok": True,
        "campo": campo,
        "completamente_firmado": todas_firmadas if token else None,
    })


@casos_bp.route("/api/acuerdo-compromiso/<int:acid>/pdf-firmado")
def acuerdo_pdf_firmado(acid):
    """
    Genera el PDF del acuerdo-compromiso con las firmas digitales incrustadas.
    Accesible con login o con token de firma.
    """
    token = request.args.get("token", "").strip()

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        if token:
            ac = conn.execute(
                """SELECT ac.*, e.nombre AS est_nombre, e.apellido AS est_apellido,
                          e.grado, e.curso, u.nombre AS generado_por_nombre
                   FROM acuerdos_compromiso ac
                   JOIN estudiantes e ON e.id=ac.estudiante_id
                   JOIN usuarios u    ON u.id=ac.generado_por
                   WHERE ac.id=? AND ac.token_firma=?""",
                (acid, token)
            ).fetchone()
        else:
            if not get_usuario():
                return jsonify({"error": "No autenticado"}), 401
            ac = conn.execute(
                """SELECT ac.*, e.nombre AS est_nombre, e.apellido AS est_apellido,
                          e.grado, e.curso, u.nombre AS generado_por_nombre
                   FROM acuerdos_compromiso ac
                   JOIN estudiantes e ON e.id=ac.estudiante_id
                   JOIN usuarios u    ON u.id=ac.generado_por
                   WHERE ac.id=?""",
                (acid,)
            ).fetchone()

    if not ac:
        return "Acuerdo no encontrado", 404

    ac = dict(ac)
    return _generar_pdf_acuerdo(ac)


@casos_bp.route("/api/casos/estudiante/<int:est_id>")
@login_required
def casos_del_estudiante(est_id):
    """Timeline completo del estudiante: casos + acciones + acuerdos + reportes."""
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        _rls.verificar_acceso_estudiante(conn, est_id)

        casos = conn.execute("""
            SELECT c.*, u.nombre as abierto_por_nombre
            FROM casos c JOIN usuarios u ON u.id=c.abierto_por
            WHERE c.estudiante_id=?
            ORDER BY c.creado_en DESC
        """, (est_id,)).fetchall()

        acuerdos = conn.execute("""
            SELECT ac.*, u.nombre as generado_por_nombre
            FROM acuerdos_compromiso ac JOIN usuarios u ON u.id=ac.generado_por
            WHERE ac.estudiante_id=?
            ORDER BY ac.creado_en DESC
        """, (est_id,)).fetchall()

        # Para cada caso, traer sus acciones
        casos_con_acciones = []
        for caso in casos:
            acciones = conn.execute("""
                SELECT a.*, u.nombre as actor_nombre, u.rol as actor_rol
                FROM caso_acciones a JOIN usuarios u ON u.id=a.actor_id
                WHERE a.caso_id=? ORDER BY a.creado_en ASC
            """, (caso["id"],)).fetchall()
            cd = dict(caso)
            cd["acciones"] = [dict(a) for a in acciones]
            casos_con_acciones.append(cd)

    return jsonify({
        "casos": casos_con_acciones,
        "acuerdos": [dict(a) for a in acuerdos]
    })


# ── HOOK: interceptar creación de reportes para generar alerta ───────────────
# (se llama desde el endpoint existente de POST /api/reportes)


@casos_bp.route("/acuerdo/<int:est_id>")
@login_required
def acuerdo_page(est_id):
    """Página dedicada para generar Acuerdo-Compromiso."""
    u = get_usuario()
    rol_n = _normalizar_rol(u.get("rol", ""))
    if rol_n not in ROLES_PSICOLOGA and rol_n not in ROLES_COORD and not u.get("es_directora"):
        return redirect(f"/perfil/{est_id}")

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        est = conn.execute("SELECT * FROM estudiantes WHERE id=?", (est_id,)).fetchone()
        if not est:
            return "Estudiante no encontrado", 404
        e = dict(est)

        # Casos abiertos del estudiante
        casos = conn.execute("""
            SELECT id, titulo, tipo, estado FROM casos
            WHERE estudiante_id=? AND estado NOT IN ('Resuelto','Cerrado')
            ORDER BY creado_en DESC
        """, (est_id,)).fetchall()

        # Acuerdos anteriores
        anteriores = conn.execute("""
            SELECT id, numero_acuerdo, fecha_acuerdo, firmado
            FROM acuerdos_compromiso
            WHERE estudiante_id=?
            ORDER BY creado_en DESC LIMIT 10
        """, (est_id,)).fetchall()

    cfg_centro = _get_config_centro()
    return render_template("acuerdo.html",
        e=e,
        casos=[dict(c) for c in casos],
        anteriores=[dict(a) for a in anteriores],
        current_user=u,
        cfg_centro=cfg_centro,
    )


