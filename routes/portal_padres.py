# -*- coding: utf-8 -*-
"""Blueprint: portal_padres"""

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
from core.helpers import _get_hijos
from core.ia import _get_groq_client, groq_client, construir_prompt, construir_prompt_planificacion, construir_prompt_rubrica, construir_prompt_estrategia
from core.excel import _parsear_boletin_bj, _buscar_o_crear_estudiante, _detectar_mencion_listado, _limpiar_nota
from core.pdf import _generar_pdf_acuerdo

logger = logging.getLogger("axula")

portal_padres_bp = Blueprint("portal_padres_bp", __name__)

@portal_padres_bp.route("/portal-padres")
@login_required
def portal_padres():
    """Portal principal del padre/tutor — muestra todos sus hijos."""
    u = get_usuario()
    if u.get("rol") != "padre":
        return redirect("/")
    hijos = _get_hijos(u["id"])
    return render_template("portal_padres.html", usuario=u, hijos=hijos)


@portal_padres_bp.route("/portal-padres/estudiante/<int:est_id>")
@login_required
def portal_padres_estudiante(est_id):
    """Perfil de solo lectura de un hijo — verifica vínculo."""
    u = get_usuario()
    if u.get("rol") != "padre":
        return redirect("/")
    # Verificar que este padre tiene acceso a este estudiante
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        vinculo = conn.execute(
            "SELECT id FROM vinculos_padre_estudiante WHERE padre_id=? AND estudiante_id=?",
            (u["id"], est_id)
        ).fetchone()
    if not vinculo:
        return "Acceso denegado", 403
    return redirect(f"/perfil/{est_id}")


@portal_padres_bp.route("/api/padres/vinculos", methods=["GET"])
@login_required
def listar_vinculos():
    """Lista los vínculos padre↔estudiante. Coordinadores y directora ven todos."""
    u = get_usuario()
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        if u.get("rol") == "padre":
            rows = conn.execute(
                """SELECT v.*, e.nombre AS est_nombre, e.apellido AS est_apellido,
                          e.grado, e.curso, e.cedula AS est_cedula
                   FROM vinculos_padre_estudiante v
                   JOIN estudiantes e ON e.id = v.estudiante_id
                   WHERE v.padre_id = ?""",
                (u["id"],)
            ).fetchall()
        elif _normalizar_rol(u.get("rol","")) in ROLES_COORD or u.get("es_directora"):
            padre_id = request.args.get("padre_id")
            if padre_id:
                rows = conn.execute(
                    """SELECT v.*, e.nombre AS est_nombre, e.apellido AS est_apellido,
                              e.grado, e.curso, u.nombre AS padre_nombre, u.username
                       FROM vinculos_padre_estudiante v
                       JOIN estudiantes e ON e.id = v.estudiante_id
                       JOIN usuarios u    ON u.id = v.padre_id
                       WHERE v.padre_id = ?""",
                    (int(padre_id),)
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT v.*, e.nombre AS est_nombre, e.apellido AS est_apellido,
                              e.grado, u.nombre AS padre_nombre, u.username, u.email
                       FROM vinculos_padre_estudiante v
                       JOIN estudiantes e ON e.id = v.estudiante_id
                       JOIN usuarios u    ON u.id = v.padre_id
                       ORDER BY u.nombre"""
                ).fetchall()
        else:
            return jsonify({"error": "Sin permisos"}), 403
    return jsonify({"ok": True, "vinculos": [dict(r) for r in rows]})


@portal_padres_bp.route("/api/padres/vinculos", methods=["POST"])
@login_required
def crear_vinculo():
    """
    Crea o actualiza el vínculo padre↔estudiante.
    Solo coordinadores, directora y secretaria pueden crear vínculos.
    Body: { padre_id, estudiante_id, parentesco? }
    """
    u = get_usuario()
    rol_n = _normalizar_rol(u.get("rol",""))
    puede = (rol_n in ROLES_COORD or u.get("es_directora") or
             rol_n in {"secretaria", "secretaria_docente"})
    if not puede:
        return jsonify({"error": "Sin permisos"}), 403

    d = request.get_json(force=True) or {}
    padre_id     = d.get("padre_id")
    est_id       = d.get("estudiante_id")
    parentesco   = (d.get("parentesco") or "padre/madre").strip()

    if not padre_id or not est_id:
        return jsonify({"ok": False, "error": "padre_id y estudiante_id requeridos"}), 400

    # Verificar que el usuario padre existe y tiene rol padre
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        padre = conn.execute(
            "SELECT id, nombre, rol FROM usuarios WHERE id=? AND activo=1", (padre_id,)
        ).fetchone()
        if not padre or padre["rol"] != "padre":
            return jsonify({"ok": False, "error": "El usuario no existe o no tiene rol 'padre'"}), 400

        est = conn.execute("SELECT id, nombre FROM estudiantes WHERE id=?", (est_id,)).fetchone()
        if not est:
            return jsonify({"ok": False, "error": "Estudiante no encontrado"}), 404

        conn.execute(
            """INSERT INTO vinculos_padre_estudiante (padre_id, estudiante_id, parentesco)
               VALUES (?,?,?)
               ON CONFLICT(padre_id, estudiante_id) DO UPDATE SET parentesco=excluded.parentesco""",
            (padre_id, est_id, parentesco)
        )

    return jsonify({"ok": True, "mensaje": f"Vínculo creado: {padre['nombre']} → {est['nombre']}"})


@portal_padres_bp.route("/api/padres/vinculos/<int:vinculo_id>", methods=["DELETE"])
@login_required
def eliminar_vinculo(vinculo_id):
    """Elimina un vínculo padre↔estudiante."""
    u = get_usuario()
    rol_n = _normalizar_rol(u.get("rol",""))
    if rol_n not in ROLES_COORD and not u.get("es_directora"):
        return jsonify({"error": "Sin permisos"}), 403
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.execute("DELETE FROM vinculos_padre_estudiante WHERE id=?", (vinculo_id,))
    return jsonify({"ok": True})


# ══════════════════════════════════════════════════════════════════════════════
#  HISTORIAL DE CAMBIOS — Audit Log
# ══════════════════════════════════════════════════════════════════════════════


