# -*- coding: utf-8 -*-
"""
Blueprint: promocion

Expone el motor de promoción (core/promocion_engine.py) por HTTP.

Estas dos rutas fueron eliminadas junto con el resto del módulo institucional
de "promocion" en la sesión 14 (paradigma personal-assistant), pero el botón
"Promover" de templates/perfil.html y el motor en core/promocion_engine.py
se quedaron sin borrar — quedaron huérfanos, sin ruta que los conecte, así
que el botón daba error silencioso desde entonces. Cualquier cambio de grado
posterior tuvo que hacerse a mano por el editor genérico de campos
(PATCH /api/estudiante/<id>), que no resetea nada — de ahí que estudiantes
promovidos siguieran arrastrando KPIs del grado anterior.

Solo se restauran las 2 rutas que perfil.html realmente usa (evaluar +
ejecutar para un solo estudiante). El resto de la API original de 9 rutas
(preview de grado completo, historial, completiva 6TO, recuperación agosto)
pertenecía al panel de coordinador institucional, que ya no existe en este
repo — no se reconstruye aquí porque nada la usa.
"""

import sqlite3
import logging

from flask import Blueprint, jsonify

from core.constants import DATABASE
from core.auth import login_required, get_usuario, _normalizar_rol
from core.promocion_engine import evaluar_estudiante, ejecutar_promocion_estudiante
from core.helpers import _anio_escolar_actual

logger = logging.getLogger("axula")

promocion_bp = Blueprint("promocion_bp", __name__)


@promocion_bp.route("/api/promocion/estudiante/<int:est_id>")
@login_required
def promocion_evaluar(est_id):
    """Evalúa el estado de promoción de un estudiante SIN escribir en BD."""
    anio = _anio_escolar_actual()
    try:
        with sqlite3.connect(DATABASE, timeout=10) as conn:
            conn.row_factory = sqlite3.Row
            resultado = evaluar_estudiante(conn, est_id, anio)
    except Exception as ex:
        logger.error(f"[promocion] evaluar_estudiante({est_id}) falló: {ex}")
        return jsonify({"ok": False, "error": "Error al evaluar la promoción."}), 500

    if "error" in resultado:
        return jsonify({"ok": False, "error": resultado["error"]}), 404

    resultado["ok"] = True
    return jsonify(resultado)


@promocion_bp.route("/api/promocion/ejecutar/<int:est_id>", methods=["POST"])
@login_required
def promocion_ejecutar_individual(est_id):
    """Ejecuta la promoción de un estudiante — escribe grado, curso, resetea
    los KPIs cacheados y registra en la tabla promociones."""
    u = get_usuario()
    anio = _anio_escolar_actual()
    try:
        with sqlite3.connect(DATABASE, timeout=10) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("BEGIN IMMEDIATE")
            try:
                resultado = ejecutar_promocion_estudiante(
                    conn, est_id, anio, ejecutado_por=u.get("id"),
                )
                if resultado.get("ok"):
                    conn.execute("COMMIT")
                else:
                    conn.execute("ROLLBACK")
            except Exception:
                conn.execute("ROLLBACK")
                raise
    except Exception as ex:
        logger.error(f"[promocion] ejecutar_promocion_estudiante({est_id}) falló: {ex}")
        return jsonify({"ok": False, "error": "Error al ejecutar la promoción."}), 500

    status = 200 if resultado.get("ok") else 400
    return jsonify(resultado), status
