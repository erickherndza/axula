# -*- coding: utf-8 -*-
"""Blueprint: notificaciones"""

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

notificaciones_bp = Blueprint("notificaciones_bp", __name__)

@notificaciones_bp.route("/api/notificaciones")
@login_required
def listar_notificaciones():
    u = get_usuario()
    solo_no_leidas = request.args.get("no_leidas", "0") == "1"
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        q = """
            SELECT n.*, e.nombre as est_nombre, e.apellido as est_apellido,
                   e.grado, e.curso
            FROM notificaciones n
            JOIN estudiantes e ON e.id = n.estudiante_id
            WHERE n.destinatario_id = ?
        """
        params = [u["id"]]
        if solo_no_leidas:
            q += " AND n.leida = 0"
        q += " ORDER BY n.creada_en DESC LIMIT 100"
        rows = conn.execute(q, params).fetchall()
    return jsonify([dict(r) for r in rows])


@notificaciones_bp.route("/api/notificaciones/count")
@login_required
def contar_notificaciones():
    u = get_usuario()
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        n = conn.execute(
            "SELECT COUNT(*) FROM notificaciones WHERE destinatario_id=? AND leida=0",
            (u["id"],)
        ).fetchone()[0]
    return jsonify({"no_leidas": n, "total": n})


@notificaciones_bp.route("/api/notificaciones/<int:nid>/leer", methods=["POST"])
@login_required
def marcar_leida(nid):
    u = get_usuario()
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.execute(
            "UPDATE notificaciones SET leida=1 WHERE id=? AND destinatario_id=?",
            (nid, u["id"])
        )
        conn.commit()
    return jsonify({"ok": True})


@notificaciones_bp.route("/api/notificaciones/leer-todas", methods=["POST"])
@login_required
def marcar_todas_leidas():
    u = get_usuario()
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.execute(
            "UPDATE notificaciones SET leida=1 WHERE destinatario_id=?",
            (u["id"],)
        )
        conn.commit()
    return jsonify({"ok": True})


@notificaciones_bp.route("/api/notificaciones/conteo")
@login_required
def conteo_notificaciones():
    """Endpoint ligero — solo devuelve el conteo de no leídas. Usado por polling."""
    u = get_usuario()
    with sqlite3.connect(DATABASE, timeout=5) as conn:
        n = conn.execute(
            "SELECT COUNT(*) FROM notificaciones WHERE destinatario_id=? AND leida=0",
            (u["id"],)
        ).fetchone()[0]
    return jsonify({"no_leidas": n, "total": n})


@notificaciones_bp.route("/api/notificaciones/sse")
@login_required
def notificaciones_sse():
    """
    Server-Sent Events — empuja el conteo de no leídas cada 20 segundos.
    El cliente se reconecta automáticamente si se corta.
    """
    from flask import Response, stream_with_context
    import time as _time

    u = get_usuario()
    uid = u["id"]

    def generate():
        while True:
            try:
                with sqlite3.connect(DATABASE, timeout=5) as conn:
                    n = conn.execute(
                        "SELECT COUNT(*) FROM notificaciones WHERE destinatario_id=? AND leida=0",
                        (uid,)
                    ).fetchone()[0]
                yield f"data: {n}\n\n"
            except Exception:
                yield "data: 0\n\n"
            _time.sleep(20)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


# ── CASOS ─────────────────────────────────────────────────────────────────────


@notificaciones_bp.route("/api/notificaciones")
@login_required
def get_notificaciones():
    """Devuelve las notificaciones del usuario actual. ?no_leidas=1 para solo no leídas."""
    u = get_usuario()
    solo_no_leidas = request.args.get("no_leidas") == "1"
    limit = min(int(request.args.get("limit", 30)), 100)
    sql = "SELECT * FROM notificaciones WHERE destinatario_id=?"
    params = [u["id"]]
    if solo_no_leidas:
        sql += " AND leida=0"
    sql += " ORDER BY creado DESC LIMIT ?"
    params.append(limit)
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(sql, params).fetchall()
        total_no_leidas = conn.execute(
            "SELECT COUNT(*) FROM notificaciones WHERE destinatario_id=? AND leida=0",
            (u["id"],)
        ).fetchone()[0]
    return jsonify({
        "ok": True,
        "notificaciones": [dict(r) for r in rows],
        "no_leidas": total_no_leidas
    })


