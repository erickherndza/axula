"""
core/analytics.py — Motor Conductual (Fase 1)

Score por estudiante:
  40% promedio de calificaciones  (0-100)
  35% tasa de asistencia          (0-100)
  25% balance de tags             (0-100, centrado en 50)

Semáforo:
  VERDE    > 70
  AMARILLO 50-70
  ROJO     < 50
"""

import sqlite3
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Pesos del score
# ──────────────────────────────────────────────
W_NOTAS      = 0.40
W_ASISTENCIA = 0.35
W_TAGS       = 0.25

NIVEL_VERDE    = 70
NIVEL_AMARILLO = 50   # por debajo → ROJO


def _get_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=20)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


# ──────────────────────────────────────────────
# Componentes del score
# ──────────────────────────────────────────────

def _score_notas(cur, estudiante_id: int, anio_escolar: str) -> float:
    """Promedio de calificaciones del año escolar (escala 0-100)."""
    # Extraer el año del string "2025-2026"
    anio_inicio = anio_escolar.split('-')[0] if '-' in anio_escolar else anio_escolar

    cur.execute("""
        SELECT AVG(promedio) as avg_prom
        FROM materias_calificaciones
        WHERE estudiante_id = ?
          AND (
            fecha_carga LIKE ? OR
            fecha_carga LIKE ?
          )
    """, (estudiante_id, f"{anio_inicio}%", f"{int(anio_inicio)+1}%"))
    row = cur.fetchone()
    if row and row['avg_prom'] is not None:
        return min(float(row['avg_prom']), 100.0)

    # Fallback: columnas p1-p4 en tabla estudiantes
    cur.execute("""
        SELECT acad_p1, acad_p2, acad_p3, acad_p4
        FROM estudiantes WHERE id = ?
    """, (estudiante_id,))
    est = cur.fetchone()
    if est:
        valores = [est[k] for k in ['acad_p1','acad_p2','acad_p3','acad_p4']
                   if est[k] is not None]
        if valores:
            return min(sum(valores) / len(valores), 100.0)
    return 0.0


def _score_asistencia(cur, estudiante_id: int, anio_escolar: str) -> float:
    """Tasa de asistencia (0-100). Presentes / total registros."""
    anio_inicio = anio_escolar.split('-')[0] if '-' in anio_escolar else anio_escolar

    cur.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN estado IN ('presente','tarde') THEN 1 ELSE 0 END) as presentes
        FROM asistencia
        WHERE estudiante_id = ?
          AND (fecha LIKE ? OR fecha LIKE ?)
    """, (estudiante_id, f"{anio_inicio}%", f"{int(anio_inicio)+1}%"))
    row = cur.fetchone()
    if row and row['total'] and row['total'] > 0:
        return round((row['presentes'] / row['total']) * 100, 2)
    return 100.0   # sin registros → no penalizar


def _score_tags(cur, estudiante_id: int, anio_escolar: str) -> tuple[float, int, int, int]:
    """
    Balance de tags en cuaderno_anecdotico.
    Retorna (score 0-100, n_positivos, n_negativos, total_registros).
    Score: 50 = neutro, sube con positivos, baja con negativos.
    """
    anio_inicio = anio_escolar.split('-')[0] if '-' in anio_escolar else anio_escolar

    cur.execute("""
        SELECT polaridad, COUNT(*) as cnt
        FROM cuaderno_anecdotico
        WHERE estudiante_id = ?
          AND (fecha LIKE ? OR fecha LIKE ?)
          AND polaridad IN ('positivo','negativo','neutro')
        GROUP BY polaridad
    """, (estudiante_id, f"{anio_inicio}%", f"{int(anio_inicio)+1}%"))

    conteos = {r['polaridad']: r['cnt'] for r in cur.fetchall()}
    pos = conteos.get('positivo', 0)
    neg = conteos.get('negativo', 0)
    total = pos + neg + conteos.get('neutro', 0)

    if total == 0:
        return 50.0, 0, 0, 0

    # Balance: cada positivo suma, cada negativo resta, ponderado sobre total
    balance = (pos - neg) / max(pos + neg, 1)  # -1 a +1
    score = round(50 + balance * 50, 2)         # 0 a 100
    return max(0.0, min(100.0, score)), pos, neg, total


def _calcular_nivel(score: float) -> str:
    if score > NIVEL_VERDE:
        return 'VERDE'
    if score >= NIVEL_AMARILLO:
        return 'AMARILLO'
    return 'ROJO'


# ──────────────────────────────────────────────
# Función principal
# ──────────────────────────────────────────────

def recalcular_metricas_estudiante(estudiante_id: int, anio_escolar: str, db_path: str) -> dict:
    """
    Calcula y persiste las métricas conductuales de un estudiante.
    Retorna el dict con el resultado.
    """
    conn = _get_db(db_path)
    try:
        cur = conn.cursor()

        s_notas      = _score_notas(cur, estudiante_id, anio_escolar)
        s_asistencia = _score_asistencia(cur, estudiante_id, anio_escolar)
        s_tags, pos, neg, total_reg = _score_tags(cur, estudiante_id, anio_escolar)

        score_total = round(
            s_notas * W_NOTAS +
            s_asistencia * W_ASISTENCIA +
            s_tags * W_TAGS,
            2
        )
        nivel = _calcular_nivel(score_total)

        cur.execute("""
            INSERT INTO metricas_conductuales
                (estudiante_id, anio_escolar, score_total,
                 score_notas, score_asistencia, score_tags,
                 nivel, tags_positivos, tags_negativos, total_registros,
                 calculado_en)
            VALUES (?,?,?,?,?,?,?,?,?,?,datetime('now'))
            ON CONFLICT(estudiante_id, anio_escolar) DO UPDATE SET
                score_total      = excluded.score_total,
                score_notas      = excluded.score_notas,
                score_asistencia = excluded.score_asistencia,
                score_tags       = excluded.score_tags,
                nivel            = excluded.nivel,
                tags_positivos   = excluded.tags_positivos,
                tags_negativos   = excluded.tags_negativos,
                total_registros  = excluded.total_registros,
                calculado_en     = datetime('now')
        """, (estudiante_id, anio_escolar, score_total,
              s_notas, s_asistencia, s_tags,
              nivel, pos, neg, total_reg))
        conn.commit()

        result = {
            'estudiante_id': estudiante_id,
            'anio_escolar':  anio_escolar,
            'score_total':   score_total,
            'score_notas':   s_notas,
            'score_asistencia': s_asistencia,
            'score_tags':    s_tags,
            'nivel':         nivel,
            'tags_positivos': pos,
            'tags_negativos': neg,
            'total_registros': total_reg,
        }
        logger.info("Métricas recalculadas est=%s anio=%s score=%.1f nivel=%s",
                    estudiante_id, anio_escolar, score_total, nivel)
        return result

    except Exception as e:
        logger.error("Error recalculando métricas est=%s: %s", estudiante_id, e)
        conn.rollback()
        raise
    finally:
        conn.close()


def recalcular_seccion(grado: str, seccion: str, anio_escolar: str, db_path: str) -> list[dict]:
    """
    Recalcula métricas para todos los estudiantes de una sección.
    Retorna lista de resultados.
    """
    conn = _get_db(db_path)
    cur = conn.cursor()
    cur.execute("""
        SELECT id FROM estudiantes
        WHERE grado = ? AND seccion = ?
    """, (grado, seccion))
    ids = [r['id'] for r in cur.fetchall()]
    conn.close()

    resultados = []
    for eid in ids:
        try:
            r = recalcular_metricas_estudiante(eid, anio_escolar, db_path)
            resultados.append(r)
        except Exception as e:
            logger.warning("Falló recálculo est=%s: %s", eid, e)
    return resultados


def obtener_semaforo_seccion(grado: str, seccion: str, anio_escolar: str, db_path: str) -> dict:
    """
    Devuelve resumen del semáforo para una sección:
    { verde: N, amarillo: N, rojo: N, estudiantes: [...] }
    """
    conn = _get_db(db_path)
    cur = conn.cursor()

    cur.execute("""
        SELECT e.id, e.nombre, e.apellido, e.grado, e.seccion,
               m.score_total, m.nivel, m.tags_positivos, m.tags_negativos,
               m.score_notas, m.score_asistencia, m.score_tags, m.calculado_en
        FROM estudiantes e
        LEFT JOIN metricas_conductuales m
               ON m.estudiante_id = e.id AND m.anio_escolar = ?
        WHERE e.grado = ? AND e.seccion = ?
        ORDER BY m.score_total ASC NULLS LAST
    """, (anio_escolar, grado, seccion))

    estudiantes = [dict(r) for r in cur.fetchall()]
    conn.close()

    resumen = {'VERDE': 0, 'AMARILLO': 0, 'ROJO': 0, 'SIN_DATOS': 0}
    for est in estudiantes:
        nivel = est.get('nivel') or 'SIN_DATOS'
        resumen[nivel] = resumen.get(nivel, 0) + 1

    return {
        'grado':     grado,
        'seccion':   seccion,
        'anio':      anio_escolar,
        'resumen':   resumen,
        'estudiantes': estudiantes,
    }
