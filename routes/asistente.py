# -*- coding: utf-8 -*-
"""Blueprint: asistente — Portal Asistente de Dirección + gestión de permisos configurables"""

import logging
from datetime import datetime
from flask import (
    Blueprint, render_template, request, jsonify, session, abort, redirect,
)

from core.constants import ROLES_DIRECTORA
from core.database import get_db
from core.auth import (
    login_required, _normalizar_rol, get_usuario,
    _tiene_permiso, PERMISOS_CATALOGO,
)

logger = logging.getLogger("axula")

asistente_bp = Blueprint("asistente_bp", __name__)


def _asistente_o_directora():
    rol = _normalizar_rol(session.get("rol", ""))
    return rol in {"asistente_directora"} | ROLES_DIRECTORA


# ── PORTAL ASISTENTE ──────────────────────────────────────────────────────────

@asistente_bp.route("/asistente")
@login_required
def portal_asistente():
    rol = _normalizar_rol(session.get("rol", ""))
    if rol not in {"asistente_directora"} | ROLES_DIRECTORA:
        abort(403)

    user_id = session["user_id"]
    u = get_usuario()

    # Obtener permisos activos del usuario
    permisos_activos = _get_permisos_usuario(user_id) if rol == "asistente_directora" else \
                       {k: True for k in PERMISOS_CATALOGO}

    return render_template("asistente.html",
        current_user=u,
        permisos=permisos_activos,
        catalogo=PERMISOS_CATALOGO,
    )


# ── PANEL PERMISOS (solo directora) ──────────────────────────────────────────

@asistente_bp.route("/permisos-asistente")
@login_required
def panel_permisos():
    rol = _normalizar_rol(session.get("rol", ""))
    if rol not in ROLES_DIRECTORA:
        abort(403)

    u = get_usuario()
    db = get_db()

    # Buscar todos los usuarios con rol asistente_directora
    asistentes = db.execute("""
        SELECT id, nombre, username, activo
        FROM usuarios
        WHERE rol = 'asistente_directora' AND activo = 1
        ORDER BY nombre
    """).fetchall()

    return render_template("permisos_asistente.html",
        current_user=u,
        asistentes=[dict(a) for a in asistentes],
        catalogo=PERMISOS_CATALOGO,
    )


# ── API: obtener permisos de un asistente ────────────────────────────────────

@asistente_bp.route("/api/asistente/permisos/<int:usuario_id>")
@login_required
def get_permisos(usuario_id):
    rol = _normalizar_rol(session.get("rol", ""))
    # Directora ve todos; asistente solo los suyos
    if rol not in ROLES_DIRECTORA and session["user_id"] != usuario_id:
        return jsonify({"error": "Sin permisos"}), 403

    permisos = _get_permisos_usuario(usuario_id)
    return jsonify({"permisos": permisos, "catalogo": PERMISOS_CATALOGO})


# ── API: guardar permisos (solo directora) ────────────────────────────────────

@asistente_bp.route("/api/asistente/permisos/<int:usuario_id>", methods=["POST"])
@login_required
def guardar_permisos(usuario_id):
    rol = _normalizar_rol(session.get("rol", ""))
    if rol not in ROLES_DIRECTORA:
        return jsonify({"error": "Solo la directora puede modificar permisos"}), 403

    db = get_db()

    # Verificar que el usuario objetivo es asistente_directora
    target = db.execute(
        "SELECT id, nombre, rol FROM usuarios WHERE id = ? AND activo = 1",
        (usuario_id,)
    ).fetchone()
    if not target:
        return jsonify({"error": "Usuario no encontrado"}), 404
    if _normalizar_rol(target["rol"]) != "asistente_directora":
        return jsonify({"error": "Solo se pueden configurar permisos para asistentes de dirección"}), 400

    d = request.get_json() or {}
    permisos_nuevos = d.get("permisos", {})  # {permiso: bool}
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    modificado_por = session["user_id"]

    for permiso, habilitado in permisos_nuevos.items():
        if permiso not in PERMISOS_CATALOGO:
            continue
        habilitado = bool(habilitado)
        # UPSERT
        existing = db.execute(
            "SELECT id FROM permisos_configurables WHERE usuario_id=? AND permiso=?",
            (usuario_id, permiso)
        ).fetchone()
        if existing:
            db.execute(
                "UPDATE permisos_configurables SET habilitado=?, modificado_por=?, fecha_mod=? WHERE usuario_id=? AND permiso=?",
                (1 if habilitado else 0, modificado_por, ahora, usuario_id, permiso)
            )
        else:
            db.execute(
                "INSERT INTO permisos_configurables (usuario_id, permiso, habilitado, modificado_por, fecha_mod) VALUES (?,?,?,?,?)",
                (usuario_id, permiso, 1 if habilitado else 0, modificado_por, ahora)
            )

    db.commit()
    logger.info(f"[PERMISOS] Directora id={modificado_por} actualizó permisos de asistente id={usuario_id}: {permisos_nuevos}")

    return jsonify({"ok": True, "nombre": target["nombre"]})


# ── Helper interno ────────────────────────────────────────────────────────────

def _get_permisos_usuario(usuario_id: int) -> dict:
    """Retorna dict {permiso: bool} con todos los permisos del catálogo."""
    db = get_db()
    rows = db.execute(
        "SELECT permiso, habilitado FROM permisos_configurables WHERE usuario_id=?",
        (usuario_id,)
    ).fetchall()
    guardados = {r["permiso"]: bool(r["habilitado"]) for r in rows}
    # Permisos no configurados aún → False por defecto
    return {p: guardados.get(p, False) for p in PERMISOS_CATALOGO}
