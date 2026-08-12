# -*- coding: utf-8 -*-
"""Blueprint: usuarios — gestión de cuentas (admin/superusuario)."""

import sqlite3
import logging
from flask import Blueprint, render_template, request, jsonify, session

from core.constants import DATABASE, ROLES_COORD, ROLES_DISPONIBLES
from core.database import get_db
from core.auth import _normalizar_rol, _hash, login_required, get_usuario

logger = logging.getLogger("axula")

usuarios_bp = Blueprint("usuarios_bp", __name__)

# Roles con acceso completo a gestión de usuarios
_ROLES_ADMIN = {"superusuario", "directora"}


def _requiere_admin():
    """Retorna 403 JSON si el usuario actual no es admin. None si ok."""
    u = get_usuario()
    if not u:
        return jsonify({"error": "No autenticado"}), 401
    if _normalizar_rol(u.get("rol", "")) not in _ROLES_ADMIN:
        return jsonify({"error": "Acceso restringido a administradores"}), 403
    return None


# ── PÁGINA PRINCIPAL ─────────────────────────────────────────────────────────

@usuarios_bp.route("/usuarios")
@login_required
def lista_usuarios():
    u = get_usuario()
    if _normalizar_rol(u.get("rol", "")) not in _ROLES_ADMIN:
        return "Sin permisos", 403
    return render_template("usuarios.html", current_user=u,
                           roles=ROLES_DISPONIBLES)


# ── API ──────────────────────────────────────────────────────────────────────

@usuarios_bp.route("/api/usuarios")
@login_required
def api_lista():
    err = _requiere_admin()
    if err:
        return err
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT id, username, nombre, rol, materia, grado, mencion,
                   tipo_docencia, ciclo, activo, email, telefono,
                   titulo_academico, departamento
            FROM usuarios ORDER BY activo DESC, nombre
        """).fetchall()
    return jsonify([dict(r) for r in rows])


@usuarios_bp.route("/api/usuarios/<int:uid>", methods=["PATCH"])
@login_required
def api_editar(uid):
    err = _requiere_admin()
    if err:
        return err

    d = request.get_json(silent=True) or {}
    EDITABLES = {
        "nombre", "rol", "materia", "grado", "mencion",
        "tipo_docencia", "ciclo", "activo", "email",
        "telefono", "titulo_academico", "departamento", "username",
    }
    updates = {k: v for k, v in d.items() if k in EDITABLES}
    if not updates:
        return jsonify({"error": "Nada que actualizar"}), 400

    # Normalizar rol si se envía
    if "rol" in updates:
        updates["rol"] = _normalizar_rol(updates["rol"])

    # Si se actualiza materia, limpiar asignaturas para que no tome precedencia
    if "materia" in updates:
        updates["asignaturas"] = None

    sets   = ", ".join(f"{k}=?" for k in updates)
    valores = list(updates.values()) + [uid]

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.execute(f"UPDATE usuarios SET {sets} WHERE id=?", valores)
        conn.commit()

    return jsonify({"ok": True})


@usuarios_bp.route("/api/usuarios/<int:uid>/password", methods=["POST"])
@login_required
def api_reset_password(uid):
    err = _requiere_admin()
    if err:
        return err
    d = request.get_json(silent=True) or {}
    nueva = (d.get("password") or "").strip()
    if len(nueva) < 4:
        return jsonify({"error": "Mínimo 4 caracteres"}), 400
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.execute("UPDATE usuarios SET password=? WHERE id=?",
                     (_hash(nueva), uid))
        conn.commit()
    return jsonify({"ok": True})


@usuarios_bp.route("/api/usuarios", methods=["POST"])
@login_required
def api_crear():
    err = _requiere_admin()
    if err:
        return err
    d = request.get_json(silent=True) or {}
    username = (d.get("username") or "").strip()
    nombre   = (d.get("nombre") or "").strip()
    password = (d.get("password") or "").strip()
    rol      = _normalizar_rol(d.get("rol") or "profesor")

    if not username or not nombre or len(password) < 4:
        return jsonify({"error": "username, nombre y contraseña (≥4 car.) son requeridos"}), 400

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        existe = conn.execute("SELECT id FROM usuarios WHERE username=?",
                              (username,)).fetchone()
        if existe:
            return jsonify({"error": "Username ya existe"}), 409
        conn.execute("""
            INSERT INTO usuarios (username, nombre, password, rol,
                                  materia, grado, mencion, tipo_docencia, activo)
            VALUES (?,?,?,?,?,?,?,?,1)
        """, (username, nombre, _hash(password), rol,
              d.get("materia",""), d.get("grado",""),
              d.get("mencion",""), d.get("tipo_docencia","ambas")))
        conn.commit()
        new_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    return jsonify({"ok": True, "id": new_id})
