# -*- coding: utf-8 -*-
"""Registro central de todos los Blueprints."""

from .auth import auth_bp
from .usuarios import usuarios_bp
from .estudiantes import estudiantes_bp
from .calificaciones import calificaciones_bp
from .asistencia import asistencia_bp
from .casos import casos_bp
from .firmas import firmas_bp
from .reportes import reportes_bp
from .notificaciones import notificaciones_bp
from .calendario import calendario_bp
from .portal_padres import portal_padres_bp
from .profesor import profesor_bp
from .planificacion import planificacion_bp
from .config import config_bp
from .dashboard import dashboard_bp
from .asignaciones import asignaciones_bp
from .secretaria import secretaria_bp
from .digitador import digitador_bp
from .finanzas import finanzas_bp
from .evaluacion import evaluacion_bp
from .ocr import ocr_bp
from .expediente import expediente_bp
from .planificacion_basica import planificacion_basica_bp
from .analitica import bp as analitica_bp
from .archivos import archivos_bp
from .suministros import suministros_bp
from .asistente import asistente_bp
from .normativa import normativa_bp

ALL_BLUEPRINTS = [
    auth_bp,
    usuarios_bp,
    estudiantes_bp,
    calificaciones_bp,
    asistencia_bp,
    casos_bp,
    firmas_bp,
    reportes_bp,
    notificaciones_bp,
    calendario_bp,
    portal_padres_bp,
    profesor_bp,
    planificacion_bp,
    config_bp,
    dashboard_bp,
    asignaciones_bp,
    secretaria_bp,
    digitador_bp,
    finanzas_bp,
    evaluacion_bp,
    ocr_bp,
    expediente_bp,
    planificacion_basica_bp,
    analitica_bp,
    archivos_bp,
    suministros_bp,
    asistente_bp,
    normativa_bp,
]
