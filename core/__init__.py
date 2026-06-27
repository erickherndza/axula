# -*- coding: utf-8 -*-
"""Paquete core — re-exporta los componentes principales."""

from .constants import *
from .database import get_db, cache_get, cache_set, cache_bust, migrar_bd, _seed_admin
from .auth import (
    _hash, _check_password, _normalizar_rol, _ciclo_del_rol,
    login_required, coord_required, admin_required, directora_required,
    _csrf_token, _csrf_check, csrf_protected, rate_limited,
    get_usuario, _rate_check,
)
from .ia import (
    _get_groq_client, groq_client,
    construir_prompt, construir_prompt_planificacion,
    construir_prompt_rubrica, construir_prompt_estrategia,
)
