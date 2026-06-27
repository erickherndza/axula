# -*- coding: utf-8 -*-
"""
core/security/rls.py
Row-Level Security (RLS) a nivel de aplicación para SQLite.

El proyecto usa sqlite3 directo (no SQLAlchemy), por lo que rls_filter
trabaja con strings SQL y devuelve cláusulas WHERE adicionales, o hace
abort(403) si el rol no tiene acceso a la tabla en absoluto.

Uso típico::

    from core.security.rls import rls_filter

    # Verificar acceso antes de ejecutar una query
    extra_where = rls_filter("SELECT * FROM movimientos_financieros", "movimientos_financieros")
    # extra_where es None (sin restricción adicional) o un string SQL

    # Solo verificar acceso (abort automático si denegado)
    rls_filter(None, "movimientos_financieros")
"""

from flask import session, abort
from core.auth import _normalizar_rol

# ── Mapa de restricciones por rol ────────────────────────────────────────────
# Cada entrada define las tablas a las que el rol NO puede acceder.
# Un rol ausente del mapa = acceso completo (ej. directora / superusuario).

_TABLAS_DENEGADAS: dict[str, frozenset[str]] = {
    "secretaria": frozenset({
        "movimientos_financieros",
        "presupuestos",
    }),
    "secretaria_docente": frozenset({
        "movimientos_financieros",
        "presupuestos",
    }),
    "digitador": frozenset({
        "notas_actividad",
        "actividades_evaluacion",
        "movimientos_financieros",
        "presupuestos",
    }),
    "evaluacion": frozenset({
        "movimientos_financieros",
        "presupuestos",
        "documentos_admin",
    }),
    "profesor": frozenset({
        "movimientos_financieros",
        "presupuestos",
        "documentos_admin",
    }),
}

# Roles con acceso EXCLUSIVO a un subconjunto de tablas financieras.
# Cualquier tabla que no esté en este set → abort(403).
_TABLAS_EXCLUSIVAS: dict[str, frozenset[str]] = {
    "auxiliar_contabilidad": frozenset({
        "movimientos_financieros",
        "presupuestos",
        "categorias_financieros",
    }),
}

# Roles con acceso total sin restricción
_ROLES_ADMIN = frozenset({
    "directora",
    "coordinador_general",
    "coordinador_primer_ciclo",
    "coordinador_segundo_ciclo",
    "superusuario",
    "asistente_directora",
})


def rls_filter(query: str | None, tabla: str) -> str | None:
    """
    Verifica si el usuario en sesión tiene acceso a *tabla* y devuelve
    una cláusula WHERE adicional si aplica, o None si no hay restricción.

    Parámetros
    ----------
    query : str | None
        Query SQL que se ejecutará.  Puede ser None si solo se desea
        verificar el acceso sin modificar ningún string.
    tabla : str
        Nombre de la tabla objetivo (case-insensitive).

    Retorna
    -------
    str | None
        ``None`` — sin restricción adicional, usar query como está.
        str     — cláusula WHERE extra para agregar al query.
                  (reservado para futuras restricciones por filas)

    Efectos secundarios
    -------------------
    Llama a ``abort(403)`` si el rol activo no tiene permiso.
    """
    tabla_norm = tabla.strip().lower()

    rol_raw = session.get("rol", "")
    rol = _normalizar_rol(rol_raw)

    # Roles con acceso total — sin filtro
    if rol in _ROLES_ADMIN:
        return None

    # Roles con acceso EXCLUSIVO a tablas financieras
    if rol in _TABLAS_EXCLUSIVAS:
        if tabla_norm not in _TABLAS_EXCLUSIVAS[rol]:
            abort(403)
        return None

    # Roles con tablas denegadas
    denegadas = _TABLAS_DENEGADAS.get(rol, frozenset())
    if tabla_norm in denegadas:
        abort(403)

    # Sin restricción adicional por filas
    return None


def verificar_acceso(tabla: str) -> None:
    """
    Atajo para solo verificar acceso (sin devolver cláusula WHERE).
    Hace abort(403) si el rol no tiene permiso.

    Uso::

        from core.security.rls import verificar_acceso
        verificar_acceso("movimientos_financieros")
    """
    rls_filter(None, tabla)
