# -*- coding: utf-8 -*-
"""Registro central de todos los Blueprints."""

from .auth import auth_bp
from .estudiantes import estudiantes_bp
from .calificaciones import calificaciones_bp
from .asistencia import asistencia_bp
from .casos import casos_bp
from .reportes import reportes_bp
from .notificaciones import notificaciones_bp
from .calendario import calendario_bp
from .profesor import profesor_bp
from .planificacion import planificacion_bp
from .dashboard import dashboard_bp
from .asignaciones import asignaciones_bp
from .evaluacion import evaluacion_bp
from .ocr import ocr_bp
from .expediente import expediente_bp
from .analitica import bp as analitica_bp
from .archivos import archivos_bp
from .asistente import asistente_bp
from .usuarios import usuarios_bp
from .poa import poa_bp
from .promocion import promocion_bp

ALL_BLUEPRINTS = [
    auth_bp,
    estudiantes_bp,
    calificaciones_bp,
    asistencia_bp,
    casos_bp,
    reportes_bp,
    notificaciones_bp,
    calendario_bp,
    profesor_bp,
    planificacion_bp,
    dashboard_bp,
    asignaciones_bp,
    evaluacion_bp,
    ocr_bp,
    expediente_bp,
    analitica_bp,
    archivos_bp,
    asistente_bp,
    usuarios_bp,
    poa_bp,
    promocion_bp,
]
