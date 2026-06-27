# -*- coding: utf-8 -*-
"""Blueprint: analitica — Motor Conductual (Fase 1)
Rutas:
  GET  /analitica/semaforo          — vista principal semáforo por sección
  GET  /analitica/api/secciones     — lista de grados/secciones disponibles
  POST /analitica/api/recalcular    — recalcular métricas de una sección
  POST /analitica/api/tag-entrada   — añadir polaridad/tags a entrada cuaderno
  GET  /analitica/api/tags-catalogo — catálogo de tags predefinidos
"""

import sqlite3
import logging
import json
from datetime import datetime

from flask import (
    Blueprint, render_template, request, jsonify, session, redirect, url_for
)

from core.constants import DATABASE
from core.auth import _normalizar_rol
from core.helpers import _anio_escolar_actual
from core.analytics import (
    recalcular_metricas_estudiante,
    recalcular_seccion,
    obtener_semaforo_seccion,
)

logger = logging.getLogger(__name__)
bp = Blueprint('analitica', __name__, url_prefix='/analitica')

ROLES_PERMITIDOS = {
    'directora', 'coordinador_general',
    'coordinador_primer_ciclo', 'coordinador_segundo_ciclo',
    'psicologa_primer_ciclo', 'psicologa_segundo_ciclo',
    'profesor',
}


def _verificar_acceso():
    rol = _normalizar_rol(session.get('rol', ''))
    if rol not in ROLES_PERMITIDOS:
        return False
    return True


# ──────────────────────────────────────────────
# Vistas
# ──────────────────────────────────────────────

@bp.route('/semaforo')
def semaforo():
    if not _verificar_acceso():
        return redirect('/login')

    rol = _normalizar_rol(session.get('rol', ''))
    usuario = session.get('nombre', '')
    anio = _anio_escolar_actual()

    # Secciones disponibles
    secciones = _get_secciones()

    # Si viene parámetro, mostrar esa sección
    grado   = request.args.get('grado', '')
    seccion = request.args.get('seccion', '')
    datos_semaforo = None

    if grado and seccion:
        datos_semaforo = obtener_semaforo_seccion(grado, seccion, anio, DATABASE)

    return render_template(
        'analitica/semaforo.html',
        usuario=usuario,
        rol=rol,
        anio=anio,
        secciones=secciones,
        grado_sel=grado,
        seccion_sel=seccion,
        datos=datos_semaforo,
    )


# ──────────────────────────────────────────────
# API
# ──────────────────────────────────────────────

@bp.route('/api/secciones')
def api_secciones():
    if not _verificar_acceso():
        return jsonify({'error': 'no autorizado'}), 403
    return jsonify({'secciones': _get_secciones()})


@bp.route('/api/recalcular', methods=['POST'])
def api_recalcular():
    if not _verificar_acceso():
        return jsonify({'error': 'no autorizado'}), 403

    data    = request.get_json(silent=True) or {}
    grado   = data.get('grado', '').strip()
    seccion = data.get('seccion', '').strip()
    anio    = data.get('anio') or _anio_escolar_actual()

    if not grado or not seccion:
        return jsonify({'error': 'grado y seccion requeridos'}), 400

    try:
        resultados = recalcular_seccion(grado, seccion, anio, DATABASE)
        return jsonify({
            'ok': True,
            'calculados': len(resultados),
            'anio': anio,
        })
    except Exception as e:
        logger.error("Error recalcular seccion %s %s: %s", grado, seccion, e)
        return jsonify({'error': 'Error al recalcular la sección. Intenta de nuevo.'}), 500


@bp.route('/api/recalcular-estudiante', methods=['POST'])
def api_recalcular_estudiante():
    if not _verificar_acceso():
        return jsonify({'error': 'no autorizado'}), 403

    data          = request.get_json(silent=True) or {}
    estudiante_id = data.get('estudiante_id')
    anio          = data.get('anio') or _anio_escolar_actual()

    if not estudiante_id:
        return jsonify({'error': 'estudiante_id requerido'}), 400

    try:
        result = recalcular_metricas_estudiante(int(estudiante_id), anio, DATABASE)
        return jsonify({'ok': True, 'resultado': result})
    except Exception as e:
        logger.error("Error recalcular est=%s: %s", estudiante_id, e)
        return jsonify({'error': 'Error al recalcular métricas. Intenta de nuevo.'}), 500


@bp.route('/api/tag-entrada', methods=['POST'])
def api_tag_entrada():
    """Actualiza polaridad y tags de un registro del cuaderno anecdótico."""
    if not _verificar_acceso():
        return jsonify({'error': 'no autorizado'}), 403

    data         = request.get_json(silent=True) or {}
    cuaderno_id  = data.get('cuaderno_id')
    polaridad    = data.get('polaridad', 'neutro')
    tags         = data.get('tags', [])   # lista de strings

    if polaridad not in ('positivo', 'negativo', 'neutro'):
        return jsonify({'error': 'polaridad inválida'}), 400
    if not cuaderno_id:
        return jsonify({'error': 'cuaderno_id requerido'}), 400

    tags_json = json.dumps(tags, ensure_ascii=False)

    try:
        with sqlite3.connect(DATABASE, timeout=15) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""
                UPDATE cuaderno_anecdotico
                SET polaridad = ?, tags = ?
                WHERE id = ?
            """, (polaridad, tags_json, cuaderno_id))
            conn.commit()
        return jsonify({'ok': True})
    except Exception as e:
        logger.error("Error tag-entrada id=%s: %s", cuaderno_id, e)
        return jsonify({'error': 'Error al actualizar la entrada. Intenta de nuevo.'}), 500


@bp.route('/api/tags-catalogo')
def api_tags_catalogo():
    if not _verificar_acceso():
        return jsonify({'error': 'no autorizado'}), 403
    try:
        with sqlite3.connect(DATABASE, timeout=10) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute("""
                SELECT tag, polaridad, icono FROM conductor_tags_catalogo
                WHERE activo = 1 ORDER BY polaridad, tag
            """)
            tags = [dict(r) for r in cur.fetchall()]
        return jsonify({'tags': tags})
    except Exception as e:
        logger.error("Error tags-catalogo: %s", e)
        return jsonify({'error': 'Error al obtener el catálogo. Intenta de nuevo.'}), 500


# ──────────────────────────────────────────────
# Helper interno
# ──────────────────────────────────────────────

def _get_secciones() -> list[dict]:
    """Retorna lista de {grado, seccion} ordenados."""
    try:
        with sqlite3.connect(DATABASE, timeout=10) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute("""
                SELECT DISTINCT grado, seccion
                FROM estudiantes
                WHERE grado IS NOT NULL AND seccion IS NOT NULL
                ORDER BY grado, seccion
            """)
            return [dict(r) for r in cur.fetchall()]
    except Exception as e:
        logger.error("Error obteniendo secciones: %s", e)
        return []
