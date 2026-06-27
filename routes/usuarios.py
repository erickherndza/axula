# -*- coding: utf-8 -*-
"""Blueprint: usuarios"""

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
from core.helpers import _audit, _enviar_bienvenida, _validar_email_usuario
from core.ia import _get_groq_client, groq_client, construir_prompt, construir_prompt_planificacion, construir_prompt_rubrica, construir_prompt_estrategia
from core.excel import _parsear_boletin_bj, _buscar_o_crear_estudiante, _detectar_mencion_listado, _limpiar_nota
from core.pdf import _generar_pdf_acuerdo

logger = logging.getLogger("axula")

usuarios_bp = Blueprint("usuarios_bp", __name__)

@usuarios_bp.route("/api/usuarios", methods=["GET"])
@coord_required
def listar_usuarios():
    q   = request.args.get("q", "").strip()
    rol = request.args.get("rol", "").strip()
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        sql = """SELECT id, username, email, nombre, rol, materia, grado, mencion,
                        asignaturas, activo, creado, ciclo, tipo_docencia,
                        telefono, titulo_academico, departamento, fecha_ingreso
                 FROM usuarios WHERE 1=1"""
        params = []
        if rol:
            sql += " AND rol=?"; params.append(rol)
        if q:
            like = f"%{q}%"
            sql += " AND (nombre LIKE ? OR username LIKE ? OR email LIKE ?)"
            params.extend([like, like, like])
        sql += " ORDER BY rol, nombre"
        rows = conn.execute(sql, params).fetchall()
    return jsonify([dict(r) for r in rows])

# Roles disponibles en el sistema


@usuarios_bp.route("/api/usuarios", methods=["POST"])
@login_required
@csrf_protected
def crear_usuario():
    if _normalizar_rol(get_usuario().get("rol","")) not in ROLES_DIRECTORA:
        return jsonify({"error": "Solo la directora puede crear usuarios"}), 403
    d = request.get_json(silent=True) or {}
    username    = d.get("username","").strip()
    password    = d.get("password","").strip()
    nombre      = d.get("nombre","").strip()
    email       = d.get("email","").strip().lower()
    rol         = d.get("rol","profesor").strip()
    materia     = d.get("materia","").strip()
    grado       = d.get("grado","").strip()
    mencion     = d.get("mencion","").strip()
    asignaturas = d.get("asignaturas","").strip()

    if not username or not password or not nombre:
        return jsonify({"error": "username, password y nombre son requeridos"}), 400
    if rol not in ROLES_DISPONIBLES:
        return jsonify({"error": f"Rol inválido. Roles permitidos: {', '.join(ROLES_DISPONIBLES)}"}), 400
    if email:
        # Padres pueden usar cualquier correo (personal, Gmail, etc.)
        # Solo el personal institucional requiere dominio institucional
        if rol == "padre":
            import re as _re
            if not _re.match(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', email):
                return jsonify({"error": "El correo no tiene un formato válido."}), 400
        else:
            ok, msg = _validar_email_usuario(email)
            if not ok:
                return jsonify({"error": msg}), 400

    try:
        with sqlite3.connect(DATABASE, timeout=10) as conn:
            conn.execute(
                """INSERT INTO usuarios (username,email,password,nombre,rol,materia,grado,mencion,asignaturas)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (username, email or None, _hash(password), nombre, rol, materia, grado, mencion, asignaturas)
            )
            conn.commit()

        # ── Enviar email de bienvenida si tiene correo configurado ────────────
        if email:
            _enviar_bienvenida(nombre, username, password, email, rol)

        _audit("crear_usuario", f"Nuevo usuario: {nombre} (@{username}, {rol})",
               "usuarios", None, None, {"nombre": nombre, "rol": rol, "username": username})

        return jsonify({"ok": True})
    except sqlite3.IntegrityError:
        return jsonify({"error": "El username ya existe"}), 400


@usuarios_bp.route("/api/usuarios/<int:uid>", methods=["PATCH"])
@login_required
@csrf_protected
def editar_usuario(uid):
    if _normalizar_rol(get_usuario().get("rol","")) not in ROLES_DIRECTORA:
        return jsonify({"error": "Solo la directora puede editar usuarios"}), 403
    d = request.get_json(silent=True) or {}
    allowed = ["nombre","email","rol","materia","grado","mencion","asignaturas","activo","password","telefono","titulo_academico","departamento","fecha_ingreso","ciclo","tipo_docencia"]
    updates = {k: d[k] for k in allowed if k in d}

    # Validar email si viene
    if "email" in updates and updates["email"]:
        updates["email"] = updates["email"].strip().lower()
        rol_actual = updates.get("rol") or d.get("rol_actual", "")
        # Padres pueden usar cualquier correo personal
        if rol_actual != "padre":
            ok, msg = _validar_email_usuario(updates["email"])
            if not ok:
                return jsonify({"error": msg}), 400

    # Validar rol si viene
    if "rol" in updates and updates["rol"] not in ROLES_DISPONIBLES:
        return jsonify({"error": f"Rol inválido"}), 400

    # Hash password ONCE — only here, never again below
    if "password" in d and d["password"]:
        pwd = d["password"].strip()
        if len(pwd) < 6:
            return jsonify({"error": "La contraseña debe tener al menos 6 caracteres"}), 400
        updates["password"] = _hash(pwd)
    elif "password" in updates:
        del updates["password"]  # empty password → don't change it

    if not updates:
        return jsonify({"ok": True})

    sets = ", ".join(f"{k}=?" for k in updates)
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.execute(f"UPDATE usuarios SET {sets} WHERE id=?", list(updates.values()) + [uid])
        conn.commit()
    return jsonify({"ok": True})


@usuarios_bp.route("/api/usuarios/<int:uid>/reset-password", methods=["POST"])
@coord_required
@csrf_protected
def admin_reset_password(uid):
    """
    Endpoint dedicado para que directora/coordinador cambien la contraseña
    de cualquier usuario. Más simple y menos propenso a errores que el PATCH genérico.
    """
    u = get_usuario()
    rol_n = _normalizar_rol(u.get("rol", ""))
    
    # Solo la directora puede cambiar contraseñas de otros usuarios
    if rol_n not in ROLES_DIRECTORA:
        return jsonify({"error": "Solo la directora puede cambiar contraseñas de otros usuarios"}), 403
    
    d = request.get_json(silent=True) or {}
    nueva_pwd = (d.get("password") or "").strip()
    
    if not nueva_pwd:
        return jsonify({"error": "La contraseña es requerida"}), 400
    if len(nueva_pwd) < 6:
        return jsonify({"error": "Mínimo 6 caracteres"}), 400
    
    # Hash ONCE
    nuevo_hash = _hash(nueva_pwd)
    
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        target = conn.execute("SELECT id, nombre, rol FROM usuarios WHERE id=?", (uid,)).fetchone()
        if not target:
            return jsonify({"error": "Usuario no encontrado"}), 404
        # Proteger: nadie puede cambiar la contraseña de la directora excepto ella misma
        if _normalizar_rol(target["rol"]) == "directora" and rol_n != "directora":
            return jsonify({"error": "Solo la directora puede cambiar su propia contraseña"}), 403
        conn.execute("UPDATE usuarios SET password=? WHERE id=?", (nuevo_hash, uid))
        conn.commit()
    
    return jsonify({"ok": True, "mensaje": f"Contraseña de {target['nombre']} actualizada"})


@usuarios_bp.route("/api/usuarios/<int:uid>", methods=["DELETE"])
@login_required
@csrf_protected
def borrar_usuario(uid):
    if _normalizar_rol(get_usuario().get("rol","")) not in ROLES_DIRECTORA:
        return jsonify({"error": "Solo la directora puede eliminar usuarios"}), 403
    if uid == session.get("user_id"):
        return jsonify({"error": "No puedes eliminarte a ti mismo"}), 400
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        u_old = conn.execute("SELECT nombre, username, rol FROM usuarios WHERE id=?", (uid,)).fetchone()
        conn.execute("DELETE FROM usuarios WHERE id=?", (uid,))
        conn.commit()
    if u_old:
        _audit("eliminar_usuario", f"Usuario eliminado: {u_old['nombre']} (@{u_old['username']}, {u_old['rol']})",
               "usuarios", uid, {"nombre": u_old["nombre"], "rol": u_old["rol"]}, None)
    return jsonify({"ok": True})


# ── UTILIDADES ──────────────────────────────────────────────────────────────


@usuarios_bp.route("/api/usuarios/bulk", methods=["POST"])
@login_required
@csrf_protected
def crear_usuarios_bulk():
    if _normalizar_rol(get_usuario().get("rol","")) not in ROLES_DIRECTORA:
        return jsonify({"error": "Solo la directora puede crear usuarios en lote"}), 403
    """Crea multiples usuarios desde JSON. Retorna resultados."""
    data = request.get_json(silent=True) or []
    if not isinstance(data, list):
        return jsonify({"error": "Se esperaba lista"}), 400
    resultados = []
    for u in data:
        username    = str(u.get("username", "")).strip()
        password    = str(u.get("password", "")).strip()
        nombre      = str(u.get("nombre", "")).strip()
        rol         = str(u.get("rol", "profesor")).strip()
        grado       = str(u.get("grado", "")).strip()
        mencion     = str(u.get("mencion", "")).strip()
        asignaturas = str(u.get("asignaturas", "")).strip()
        materia     = asignaturas.split(",")[0].strip() if asignaturas else ""
        if not username or not password or not nombre:
            resultados.append({"username": username, "ok": False, "error": "Faltan campos"})
            continue
        try:
            with sqlite3.connect(DATABASE, timeout=10) as conn:
                conn.execute(
                    "INSERT INTO usuarios (username,password,nombre,rol,materia,grado,mencion,asignaturas) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    (username, _hash(password), nombre, rol, materia, grado, mencion, asignaturas)
                )
                conn.commit()
            resultados.append({"username": username, "ok": True})
        except sqlite3.IntegrityError:
            resultados.append({"username": username, "ok": False, "error": "Usuario ya existe"})
    ok_count = sum(1 for r in resultados if r["ok"])
    return jsonify({"resultados": resultados, "ok": ok_count, "errores": len(resultados) - ok_count})


