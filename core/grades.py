# -*- coding: utf-8 -*-
"""
core/grades.py — Fuente única de verdad para evaluación académica.

Toda la lógica de cálculo de notas, promedios, clasificación y
recuperación pedagógica se centraliza aquí según Ord. 04-2023 MINERD.

Ningún otro archivo debe implementar estas fórmulas por su cuenta.
"""

__all__ = [
    # Constantes
    "APROBATORIO",
    "ESCALA",
    "INASISTENCIA_ALERTA",
    "INASISTENCIA_REPRUEBA",
    "ETIQUETAS",
    "COLORES",
    # Funciones
    "clasificar_nota",
    "color_nota",
    "etiqueta_nota",
    "promedio_periodos",
    "semestre",
    "nota_con_recuperacion",
    "reprueba_por_asistencia",
    "alerta_asistencia",
    "promedio_competencias",
    "estado_materia",
    "requiere_recuperacion",
]

# ── CONSTANTES MINERD Ord. 04-2023 ───────────────────────────────────────────

APROBATORIO         = 70    # Nota mínima para aprobar
INASISTENCIA_REPRUEBA = 20  # % de ausencias injustificadas que reprueban
INASISTENCIA_ALERTA   = 15  # % que genera alerta sin reprobar todavía

# Escala oficial (umbral_mínimo, código)
ESCALA = [
    (89, "destacado"),
    (80, "satisfactorio"),
    (70, "basico"),
    (60, "en_proceso"),
    (0,  "insuficiente"),
]

ETIQUETAS = {
    "destacado":     "D · Destacado",
    "satisfactorio": "S · Satisfactorio",
    "basico":        "B · Básico",
    "en_proceso":    "EP · En Proceso",
    "insuficiente":  "I · Insuficiente",
    "sin_nota":      "Sin nota",
    "no_entrego":    "✗ No entregó",
    "pendiente":     "Pendiente",
}

COLORES = {
    "destacado":     "#4dffb4",
    "satisfactorio": "#60b8f0",
    "basico":        "#c8f060",
    "en_proceso":    "#f7b731",
    "insuficiente":  "#ff4d4d",
    "sin_nota":      "#555555",
    "no_entrego":    "#ff4d4d",
    "pendiente":     "#888888",
}


# ── CLASIFICACIÓN ─────────────────────────────────────────────────────────────

def clasificar_nota(nota):
    """
    Clasifica una nota según la escala Ord. 04-2023.

    Args:
        nota: número (0-100) o None

    Returns:
        str: código de clasificación ('destacado', 'satisfactorio',
             'basico', 'en_proceso', 'insuficiente', 'sin_nota')
    """
    if nota is None:
        return "sin_nota"
    nota = float(nota)
    for umbral, codigo in ESCALA:
        if nota >= umbral:
            return codigo
    return "insuficiente"


def color_nota(nota):
    """Devuelve el color hex correspondiente a la nota."""
    return COLORES.get(clasificar_nota(nota), COLORES["sin_nota"])


def etiqueta_nota(nota):
    """Devuelve la etiqueta legible correspondiente a la nota."""
    return ETIQUETAS.get(clasificar_nota(nota), "—")


def requiere_recuperacion(nota):
    """
    True si la nota requiere Recuperación Pedagógica (< 70).
    Ord. 04-2023 Art. 28: el docente debe aplicar actividades
    complementarias antes de la evaluación completiva.
    """
    return nota is not None and float(nota) < APROBATORIO


# ── PROMEDIOS ─────────────────────────────────────────────────────────────────

def promedio_periodos(p1=None, p2=None, p3=None, p4=None):
    """
    Calcula el promedio anual de una materia a partir de los 4 períodos.
    Solo promedia los períodos que tienen nota (ignora None y 0).

    Ord. 04-2023: todos los períodos tienen el mismo peso.

    Args:
        p1, p2, p3, p4: notas de cada período (float o None)

    Returns:
        float redondeado a 1 decimal, o None si no hay ningún período.
    """
    valores = [float(p) for p in [p1, p2, p3, p4]
               if p is not None and float(p) > 0]
    if not valores:
        return None
    return round(sum(valores) / len(valores), 1)


def semestre(p1=None, p2=None):
    """
    Promedio semestral de dos períodos.
    Acepta None en uno de los dos (devuelve el que tenga valor).
    """
    valores = [float(p) for p in [p1, p2]
               if p is not None and float(p) > 0]
    if not valores:
        return None
    return round(sum(valores) / len(valores), 1)


# ── RECUPERACIÓN PEDAGÓGICA (Ord. 04-2023 Art. 28) ───────────────────────────

def nota_con_recuperacion(nota_base, nota_completiva=None, nota_extraordinaria=None):
    """
    Calcula la nota final ajustada con recuperación pedagógica.

    Jerarquía (la más alta gana):
      1. Evaluación Extraordinaria  → nota definitiva (reemplaza todo)
      2. Evaluación Completiva      → 50% nota_base + 50% nota_completiva
      3. Recuperación pedagógica    → mejora directa por actividades
         complementarias (el docente la sube si supera la base)
      4. Nota base                  → sin recuperación

    Args:
        nota_base:           promedio P1-P4 original
        nota_completiva:     nota de la evaluación completiva (float o None)
        nota_extraordinaria: nota de la evaluación extraordinaria (float o None)

    Returns:
        float redondeado a 1 decimal
    """
    if nota_base is None:
        return None

    ajustada = float(nota_base)

    # Completiva: 50 / 50
    if nota_completiva is not None:
        ajustada = float(nota_base) * 0.5 + float(nota_completiva) * 0.5

    # Extraordinaria: reemplaza completamente
    if nota_extraordinaria is not None:
        ajustada = float(nota_extraordinaria)

    return round(ajustada, 1)


# ── ASISTENCIA ────────────────────────────────────────────────────────────────

def reprueba_por_asistencia(pct_inasistencia):
    """
    True si el porcentaje de inasistencia injustificada reproba la materia.
    Ord. 04-2023: ≥ 20% de ausencias injustificadas → reprobación automática.

    Args:
        pct_inasistencia: porcentaje (0-100)
    """
    return pct_inasistencia is not None and float(pct_inasistencia) >= INASISTENCIA_REPRUEBA


def alerta_asistencia(pct_inasistencia):
    """
    True si el porcentaje genera alerta MINERD pero aún no reproba.
    ≥ 15% y < 20%
    """
    if pct_inasistencia is None:
        return False
    pct = float(pct_inasistencia)
    return INASISTENCIA_ALERTA <= pct < INASISTENCIA_REPRUEBA


def calcular_pct_inasistencia(horas_ausente, horas_tardanza_peso, horas_total):
    """
    Calcula el % de inasistencia injustificada para una materia.

    Tardanza: cada tardanza equivale a 0.5 horas de ausencia (MINERD).

    Args:
        horas_ausente:        horas de ausencia injustificada
        horas_tardanza_peso:  horas de tardanza ponderadas (ya × 0.5)
        horas_total:          total de horas clase impartidas

    Returns:
        float porcentaje (0-100), 0 si horas_total es 0
    """
    if not horas_total or horas_total == 0:
        return 0.0
    horas_injustif = (horas_ausente or 0) + (horas_tardanza_peso or 0)
    return round(horas_injustif / horas_total * 100, 1)


# ── COMPETENCIAS ──────────────────────────────────────────────────────────────

def promedio_competencias(scores_por_competencia):
    """
    Calcula el promedio general a partir de los promedios por competencia.

    Ord. 04-2023: todas las competencias tienen el mismo peso.

    Args:
        scores_por_competencia: dict {codigo: promedio_float}
            ej: {"COM": 85.0, "PL": 78.0, "EC": 90.0}

    Returns:
        float redondeado a 1 decimal, o None si el dict está vacío
    """
    valores = [v for v in scores_por_competencia.values()
               if v is not None]
    if not valores:
        return None
    return round(sum(valores) / len(valores), 1)


def promediar_notas_por_competencia(actividades_con_notas):
    """
    Calcula el promedio por competencia a partir de una lista de actividades
    con sus notas y competencias asignadas.

    Args:
        actividades_con_notas: list de dict con claves:
            - "competencias": list de códigos (ej. ["COM", "PL"])
            - "nota": float o None
            - "peso": float (default 1.0, reservado para uso futuro)

    Returns:
        dict {codigo_competencia: promedio_float}
    """
    acumulado = {}  # {comp_code: [notas]}

    for act in actividades_con_notas:
        nota = act.get("nota")
        if nota is None:
            continue
        for comp in (act.get("competencias") or []):
            acumulado.setdefault(comp, []).append(float(nota))

    return {
        comp: round(sum(notas) / len(notas), 1)
        for comp, notas in acumulado.items()
        if notas
    }


# ── ESTADO COMPLETO DE UNA MATERIA ───────────────────────────────────────────

def estado_materia(nota_final, pct_inasistencia=0, nota_final_ajustada=None):
    """
    Determina el estado definitivo de un estudiante en una materia,
    considerando nota y asistencia.

    Args:
        nota_final:           promedio de los 4 períodos
        pct_inasistencia:     % de ausencias injustificadas (default 0)
        nota_final_ajustada:  nota tras recuperación (si aplica)

    Returns:
        dict con:
            - "nota":        nota a mostrar (ajustada si existe, sino final)
            - "estado":      código clasificación
            - "etiqueta":    texto legible
            - "color":       hex
            - "aprobado":    bool
            - "reprueba_asistencia": bool
            - "alerta_asistencia":   bool
    """
    nota_efectiva = nota_final_ajustada if nota_final_ajustada is not None else nota_final
    estado_cod    = clasificar_nota(nota_efectiva)

    reprueba_asist = reprueba_por_asistencia(pct_inasistencia)

    # Si repruba por asistencia, el estado siempre es insuficiente
    if reprueba_asist and nota_efectiva is not None:
        estado_cod = "insuficiente"

    return {
        "nota":               nota_efectiva,
        "estado":             estado_cod,
        "etiqueta":           ETIQUETAS.get(estado_cod, "—"),
        "color":              COLORES.get(estado_cod, "#555"),
        "aprobado":           not reprueba_asist and (nota_efectiva or 0) >= APROBATORIO,
        "reprueba_asistencia": reprueba_asist,
        "alerta_asistencia":  alerta_asistencia(pct_inasistencia),
    }
