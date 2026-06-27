# -*- coding: utf-8 -*-
"""
Row-Level Security (RLS) — capa de aislamiento de datos por rol.

SQLite no tiene RLS nativo. Este módulo lo implementa a nivel de aplicación:
cada consulta que devuelva datos de estudiantes DEBE pasar por los helpers
de este módulo antes de ejecutarse.

Jerarquía de acceso:
  superusuario / directora          → ve TODO
  coordinador_general               → ve TODO
  coordinador_primer_ciclo          → grados 1ERO, 2DO, 3ERO
  coordinador_segundo_ciclo         → grados 4TO, 5TO, 6TO
  psicologa_primer_ciclo            → grados 1ERO, 2DO, 3ERO
  psicologa_segundo_ciclo           → grados 4TO, 5TO, 6TO
  secretaria / digitador            → ve TODO (administrativo)
  profesor                          → solo sus estudiantes asignados
  padre                             → solo sus hijos vinculados
  suministros / finanzas            → NO acceden a datos de estudiantes
"""

import sqlite3
import logging
from flask import session, abort
from core.auth import _normalizar_rol, _ciclo_del_rol
from core.constants import ROLES_COORD, ROLES_SUPER

logger = logging.getLogger("axula")

# Grados por ciclo
GRADOS_PRIMER_CICLO  = {"1ERO", "2DO", "3ERO"}
GRADOS_SEGUNDO_CICLO = {"4TO", "5TO", "6TO"}

# Roles que tienen acceso administrativo total a estudiantes
ROLES_VER_TODO = ROLES_SUPER | {"coordinador_general", "secretaria", "digitador",
                                  "directora", "aux_contabilidad"}


def _rol_actual():
    """Devuelve el rol normalizado del usuario en sesión."""
    return _normalizar_rol(session.get("rol", ""))


def grados_permitidos(rol: str = None) -> list | None:
    """
    Retorna la lista de grados que puede ver este rol.
    None = sin restricción (ve todos).
    """
    r = _normalizar_rol(rol or _rol_actual())
    ciclo = _ciclo_del_rol(r)
    if ciclo is None:
        return None  # sin restricción
    if ciclo == "primer_ciclo":
        return list(GRADOS_PRIMER_CICLO)
    if ciclo == "segundo_ciclo":
        return list(GRADOS_SEGUNDO_CICLO)
    return None


def sql_filtro_grado(alias: str = "e", col: str = "grado") -> tuple[str, list]:
    """
    Genera el fragmento SQL WHERE para filtrar por grados permitidos.

    Uso:
        filtro_sql, filtro_params = rls.sql_filtro_grado()
        q = f"SELECT * FROM estudiantes {alias} WHERE 1=1 {filtro_sql}"
        conn.execute(q, filtro_params)

    Retorna ("", []) si el rol tiene acceso total.
    Retorna (" AND UPPER(e.grado) IN (?,?,?)", ["1ERO","2DO","3ERO"]) para primer ciclo.
    """
    grados = grados_permitidos()
    if grados is None:
        return "", []
    placeholders = ",".join("?" * len(grados))
    return f" AND UPPER({alias}.{col}) IN ({placeholders})", [g.upper() for g in grados]


def verificar_acceso_estudiante(conn: sqlite3.Connection, est_id: int) -> None:
    """
    Verifica que el usuario en sesión puede acceder a este estudiante.
    Lanza abort(403) si no tiene permiso.
    Registra el intento denegado en el log de auditoría.

    Compatible con roles:
    - padre: verifica vínculo en vinculos_padre_estudiante
    - coordinador de ciclo: verifica que el estudiante es de su ciclo
    - roles con acceso total: pasa sin verificación
    """
    rol = _rol_actual()
    uid = session.get("user_id")

    # Rol padre: solo sus hijos vinculados
    if rol == "padre":
        vinculo = conn.execute(
            "SELECT 1 FROM vinculos_padre_estudiante WHERE padre_id=? AND estudiante_id=?",
            (uid, est_id)
        ).fetchone()
        if not vinculo:
            logger.warning(f"[RLS] DENEGADO padre uid={uid} → estudiante {est_id}")
            abort(403)
        return

    # Roles con acceso total
    if rol in ROLES_VER_TODO or rol in ROLES_COORD:
        grados = grados_permitidos(rol)
        if grados is None:
            return  # acceso total

        # Verificar que el estudiante pertenece al ciclo del coordinador
        est = conn.execute(
            "SELECT grado FROM estudiantes WHERE id=?", (est_id,)
        ).fetchone()
        if not est:
            logger.warning(f"[RLS] DENEGADO {rol} uid={uid} → estudiante {est_id} no existe")
            abort(404)
        if est["grado"].upper() not in [g.upper() for g in grados]:
            logger.warning(
                f"[RLS] DENEGADO {rol} uid={uid} → estudiante {est_id} "
                f"grado={est['grado']} fuera de ciclo {grados}"
            )
            abort(403)
        return

    # Rol profesor: solo sus estudiantes asignados (via asignaciones o calificaciones)
    if rol == "profesor":
        asignado = conn.execute("""
            SELECT 1 FROM asignaciones
            WHERE profesor_id=? AND estudiante_id=?
            UNION
            SELECT 1 FROM calificaciones_periodo
            WHERE profesor_id=? AND estudiante_id=?
            LIMIT 1
        """, (uid, est_id, uid, est_id)).fetchone()
        if not asignado:
            logger.warning(f"[RLS] DENEGADO profesor uid={uid} → estudiante {est_id}")
            abort(403)
        return

    # Rol desconocido / sin permiso explícito
    logger.warning(f"[RLS] DENEGADO rol={rol} uid={uid} → estudiante {est_id} (rol no reconocido)")
    abort(403)


def verificar_acceso_o_none(conn: sqlite3.Connection, est_id: int) -> bool:
    """
    Versión no-abortante de verificar_acceso_estudiante.
    Retorna True si tiene acceso, False si no.
    """
    try:
        verificar_acceso_estudiante(conn, est_id)
        return True
    except Exception:
        return False
