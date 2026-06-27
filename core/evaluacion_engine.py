# core/evaluacion_engine.py
"""
Motor de cálculo del sistema de evaluación.
Ordenanza 04-2023 MINERD — Escala 0-100, mínimo aprobatorio 70.

Nota de implementación: usa 'materia' TEXT como identificador de área
hasta que exista una tabla materias con IDs propios.
"""
from __future__ import annotations
from typing import Optional


NOTA_MINIMA_APROBACION = 70
TOTAL_PUNTOS_PERIODO   = 100
TOTAL_PERIODOS         = 4


# ──────────────────────────────────────────
# VALIDACIONES DE PERÍODO
# ──────────────────────────────────────────

def get_puntos_usados_periodo(db, materia: str, docente_id: int,
                               periodo: int, anio_escolar_id: int,
                               excluir_actividad_id: int = None) -> int:
    query = """
        SELECT COALESCE(SUM(valor_puntos), 0) as total
        FROM actividades_evaluacion
        WHERE materia = ? AND docente_id = ?
          AND periodo = ? AND anio_escolar_id = ?
          AND activa = 1
    """
    params = [materia, docente_id, periodo, anio_escolar_id]

    if excluir_actividad_id:
        query += " AND id != ?"
        params.append(excluir_actividad_id)

    result = db.execute(query, params).fetchone()
    return int(result['total'])


def validar_puntos_actividad(db, materia: str, docente_id: int,
                              periodo: int, anio_escolar_id: int,
                              valor_puntos: int,
                              actividad_id: int = None) -> dict:
    """
    Retorna {'valido': bool, 'puntos_usados': int,
             'puntos_disponibles': int, 'mensaje': str}
    """
    usados = get_puntos_usados_periodo(
        db, materia, docente_id, periodo,
        anio_escolar_id, excluir_actividad_id=actividad_id
    )
    disponibles = TOTAL_PUNTOS_PERIODO - usados

    if valor_puntos <= 0:
        return {
            'valido': False,
            'puntos_usados': usados,
            'puntos_disponibles': disponibles,
            'mensaje': "El valor en puntos debe ser mayor a 0.",
        }

    if valor_puntos > disponibles:
        return {
            'valido': False,
            'puntos_usados': usados,
            'puntos_disponibles': disponibles,
            'mensaje': (f"No se puede asignar {valor_puntos} pts. "
                        f"Solo quedan {disponibles} pts disponibles en el período {periodo}."),
        }

    return {
        'valido': True,
        'puntos_usados': usados + valor_puntos,
        'puntos_disponibles': disponibles - valor_puntos,
        'mensaje': f"OK. Período {periodo}: {usados + valor_puntos}/100 pts asignados.",
    }


# ──────────────────────────────────────────
# CÁLCULO DE NOTAS
# ──────────────────────────────────────────

def calcular_nota_periodo(db, est_id: int, materia: str, docente_id: int,
                           periodo: int, anio_escolar_id: int) -> Optional[float]:
    """
    Fórmula: (suma pts_obtenidos / suma pts_posibles) * 100
    Actividades sin calificar cuentan como 0.
    """
    actividades = db.execute("""
        SELECT ae.id, ae.valor_puntos,
               COALESCE(na.puntuacion_obtenida, 0) as obtenida
        FROM actividades_evaluacion ae
        LEFT JOIN notas_actividad na
            ON na.actividad_id = ae.id AND na.est_id = ?
        WHERE ae.materia = ?
          AND ae.docente_id = ?
          AND ae.periodo = ?
          AND ae.anio_escolar_id = ?
          AND ae.activa = 1
    """, [est_id, materia, docente_id, periodo, anio_escolar_id]).fetchall()

    if not actividades:
        return None

    total_posible  = sum(a['valor_puntos'] for a in actividades)
    total_obtenido = sum(a['obtenida']     for a in actividades)

    if total_posible == 0:
        return 0.0

    return round((total_obtenido / total_posible) * 100, 2)


def calcular_nota_final_area(db, est_id: int, materia: str,
                              docente_id: int, anio_escolar_id: int) -> Optional[float]:
    """Promedio de los períodos cerrados que tengan nota_calculada."""
    registros = db.execute("""
        SELECT COALESCE(nota_manual, nota_calculada) as nota_final
        FROM registro_notas_periodo
        WHERE est_id = ? AND materia = ?
          AND docente_id = ? AND anio_escolar_id = ?
          AND COALESCE(nota_manual, nota_calculada) IS NOT NULL
    """, [est_id, materia, docente_id, anio_escolar_id]).fetchall()

    if not registros:
        return None

    notas = [r['nota_final'] for r in registros]
    return round(sum(notas) / len(notas), 2)


def get_estado_estudiante_periodo(nota: Optional[float]) -> dict:
    if nota is None:
        return {'estado': 'sin_evaluar', 'label': 'Sin evaluar', 'color': 'gray'}
    if nota >= NOTA_MINIMA_APROBACION:
        return {'estado': 'aprobado', 'label': 'Aprobado', 'color': 'green'}
    return {'estado': 'recuperacion', 'label': 'Recuperación', 'color': 'red'}


# ──────────────────────────────────────────
# CIERRE DE PERÍODO
# ──────────────────────────────────────────

def cerrar_periodo(db, materia: str, docente_id: int,
                   periodo: int, anio_escolar_id: int) -> dict:
    """
    Calcula y guarda la nota de todos los estudiantes en registro_notas_periodo.
    """
    pts_usados = get_puntos_usados_periodo(db, materia, docente_id,
                                           periodo, anio_escolar_id)
    if pts_usados == 0:
        return {
            'exitoso': False,
            'mensaje': f"El período {periodo} no tiene actividades asignadas.",
        }

    if pts_usados > TOTAL_PUNTOS_PERIODO:
        return {
            'exitoso': False,
            'mensaje': (f"El período {periodo} tiene {pts_usados} pts asignados. "
                        f"No puede superar {TOTAL_PUNTOS_PERIODO} pts."),
        }

    estudiantes = db.execute("""
        SELECT DISTINCT na.est_id
        FROM notas_actividad na
        JOIN actividades_evaluacion ae ON ae.id = na.actividad_id
        WHERE ae.materia = ? AND ae.docente_id = ?
          AND ae.periodo = ? AND ae.anio_escolar_id = ?
          AND ae.activa = 1
    """, [materia, docente_id, periodo, anio_escolar_id]).fetchall()

    procesados   = 0
    advertencias = []

    # Recuperar anio_escolar TEXT para guardarlo
    ae_row = db.execute(
        "SELECT nombre FROM anios_escolares WHERE id = ?", [anio_escolar_id]
    ).fetchone()
    anio_escolar_txt = ae_row['nombre'] if ae_row else str(anio_escolar_id)

    for est in estudiantes:
        est_id = est['est_id']

        sin_nota = db.execute("""
            SELECT COUNT(*) as cnt
            FROM actividades_evaluacion ae
            LEFT JOIN notas_actividad na
                ON na.actividad_id = ae.id AND na.est_id = ?
            WHERE ae.materia = ? AND ae.docente_id = ?
              AND ae.periodo = ? AND ae.anio_escolar_id = ?
              AND ae.activa = 1
              AND na.id IS NULL
        """, [est_id, materia, docente_id, periodo, anio_escolar_id]).fetchone()

        if sin_nota['cnt'] > 0:
            advertencias.append({
                'est_id': est_id,
                'mensaje': f"Tiene {sin_nota['cnt']} actividad(es) sin calificar → cuentan como 0",
            })

        nota = calcular_nota_periodo(db, est_id, materia, docente_id,
                                     periodo, anio_escolar_id)

        totales = db.execute("""
            SELECT
                SUM(ae.valor_puntos)                          as posible,
                SUM(COALESCE(na.puntuacion_obtenida, 0))      as obtenida
            FROM actividades_evaluacion ae
            LEFT JOIN notas_actividad na
                ON na.actividad_id = ae.id AND na.est_id = ?
            WHERE ae.materia = ? AND ae.docente_id = ?
              AND ae.periodo = ? AND ae.anio_escolar_id = ?
              AND ae.activa = 1
        """, [est_id, materia, docente_id, periodo, anio_escolar_id]).fetchone()

        db.execute("""
            INSERT INTO registro_notas_periodo
                (est_id, materia, docente_id, anio_escolar_id, anio_escolar,
                 periodo, nota_calculada, total_pts_posibles, total_pts_obtenidos,
                 cerrado, fecha_cierre)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
            ON CONFLICT(est_id, materia, docente_id, anio_escolar_id, periodo)
            DO UPDATE SET
                nota_calculada      = excluded.nota_calculada,
                total_pts_posibles  = excluded.total_pts_posibles,
                total_pts_obtenidos = excluded.total_pts_obtenidos,
                cerrado             = 1,
                fecha_cierre        = CURRENT_TIMESTAMP,
                updated_at          = CURRENT_TIMESTAMP
        """, [est_id, materia, docente_id, anio_escolar_id, anio_escolar_txt,
              periodo, nota, totales['posible'], totales['obtenida']])

        procesados += 1

    db.commit()

    return {
        'exitoso':      True,
        'procesados':   procesados,
        'pts_usados':   pts_usados,
        'advertencias': advertencias,
        'errores':      [],
    }
