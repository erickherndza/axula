# -*- coding: utf-8 -*-
"""Blueprint: firmas"""

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

firmas_bp = Blueprint("firmas_bp", __name__)

@firmas_bp.route("/firma/<int:acid>/<token>")
def pagina_firma(acid, token):
    """
    Página pública (sin login) donde el padre/tutor firma con su dedo.
    Se accede mediante el enlace generado por solicitar_firma.
    """
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        ac = conn.execute(
            """SELECT ac.*, e.nombre AS est_nombre, e.apellido AS est_apellido,
                      e.grado, e.curso
               FROM acuerdos_compromiso ac
               JOIN estudiantes e ON e.id = ac.estudiante_id
               WHERE ac.id=? AND ac.token_firma=?""",
            (acid, token)
        ).fetchone()

    if not ac:
        return "<h2 style='font-family:sans-serif;text-align:center;padding:40px;color:#666'>Enlace de firma inválido o expirado.</h2>", 404

    ac = dict(ac)
    if ac.get("firma_tutor"):
        return "<h2 style='font-family:sans-serif;text-align:center;padding:40px;color:#15803d'>✓ Este acuerdo ya fue firmado. Gracias.</h2>"

    return render_template("acuerdo_firma.html", ac=ac, token=token)


