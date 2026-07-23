# -*- coding: utf-8 -*-
"""
Motor de Promoción Estudiantil — Ordenanzas MINERD
Nivel Secundario (Bachillerato en Artes) · 1RO – 6TO

Separación explícita:
  calcular  → funciones puras / de lectura (no escriben en BD)
  ejecutar  → escribe en BD (el caller hace commit)

Reglas implementadas:
  Primer ciclo  (1RO, 2DO, 3RO):  70 mínimo; 1-2 reprobadas → RECUPERACION agosto
  Segundo ciclo (4TO, 5TO):        igual que primer ciclo, sin completiva
  Segundo ciclo (6TO):             nota_final = promedio×0.80 + completiva×0.20
  Asistencia:    >20% ausencias → reprueba automática esa materia
  Promoción:     0 reprobadas → PROMOVIDO
                 1-2           → RECUPERACION
                 3+            → NO_PROMOVIDO
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from core.helpers import obtener_notas_estudiante, _normalizar_clave_materia

log = logging.getLogger(__name__)

# ── Constantes ────────────────────────────────────────────────────────────────

NOTA_MINIMA          = 70.0
PESO_ANUAL_6TO       = 0.80
PESO_COMPLETIVA_6TO  = 0.20
MAX_MATS_RECUP       = 2          # 1-2 materias → RECUPERACION
UMBRAL_INASISTENCIA  = 0.20       # >20% ausencias → reprueba

GRADOS_PRIMER_CICLO   = {"1ERO", "2DO", "3RO", "3ERO"}
GRADOS_SEGUNDO_CICLO  = {"4TO", "5TO", "6TO"}
GRADOS_CON_COMPLETIVA = {"6TO"}

MAPA_SIGUIENTE = {
    "1ERO": "2DO",
    "2DO":  "3RO",
    "3RO":  "4TO",
    "3ERO": "4TO",
    "4TO":  "5TO",
    "5TO":  "6TO",
    "6TO":  "CANDIDATO_PRUEBAS",   # Ord. 1-2016: aprueba materias → candidato a Pruebas Nacionales
}

# Estados de materia
EST_APROBADA            = "APROBADA"
EST_REPROBADA           = "REPROBADA"
EST_PENDIENTE           = "PENDIENTE"
EST_REPROBADA_ASISTENCIA = "REPROBADA_ASISTENCIA"

# Estados de promoción
PROM_PROMOVIDO    = "PROMOVIDO"
PROM_RECUPERACION = "RECUPERACION"
PROM_NO_PROMOVIDO = "NO_PROMOVIDO"
PROM_PENDIENTE    = "PENDIENTE"


# ── Clasificación de grado ────────────────────────────────────────────────────

def _norm_grado(grado: str) -> str:
    """Normaliza el grado a mayúsculas sin espacios extra."""
    return (grado or "").strip().upper()


def clasificar_grado(grado: str) -> dict:
    """
    Retorna {ciclo, tiene_completiva, grado_norm} para cualquier formato de entrada.
    '4to' → {'ciclo': 'segundo_ciclo', 'tiene_completiva': False, 'grado_norm': '4TO'}
    """
    g = _norm_grado(grado)
    if g in GRADOS_PRIMER_CICLO:
        return {"ciclo": "primer_ciclo", "tiene_completiva": False, "grado_norm": g}
    if g in GRADOS_SEGUNDO_CICLO:
        return {
            "ciclo": "segundo_ciclo",
            "tiene_completiva": g in GRADOS_CON_COMPLETIVA,
            "grado_norm": g,
        }
    # Grado desconocido — tratar como primer ciclo sin completiva
    log.warning("clasificar_grado: grado desconocido '%s'", grado)
    return {"ciclo": "desconocido", "tiene_completiva": False, "grado_norm": g}


def siguiente_grado(grado: str) -> str:
    """
    '5TO' → '6TO' · '6TO' → 'CANDIDATO_PRUEBAS' (Ord. 1-2016 MINERD)
    Acepta minúsculas y variantes ('3ero', '3ERO').
    """
    g = _norm_grado(grado)
    if g not in MAPA_SIGUIENTE:
        raise ValueError(f"Grado '{grado}' no tiene mapa de siguiente grado.")
    return MAPA_SIGUIENTE[g]


# ── Asistencia ────────────────────────────────────────────────────────────────

def _anios_de_escolar(anio_escolar: str) -> tuple[int, int]:
    """
    '2025-2026' → (2025, 2026)
    Usado para filtrar tablas que guardan anio como INTEGER, no como 'YYYY-YYYY'.
    """
    try:
        partes = (anio_escolar or "").split("-")
        return int(partes[0]), int(partes[1])
    except (ValueError, IndexError, AttributeError):
        import datetime
        y = datetime.date.today().year
        return y - 1, y


def calcular_pct_inasistencia_materia(
    db,
    est_id: int,
    materia: str,
    anio_escolar: str,
) -> Optional[float]:
    """
    Calcula porcentaje de inasistencia (0.0–1.0) para un estudiante en una materia.
    Fuente primaria: asistencia_mensual (columnas: anio INT + mes INT, SIN anio_escolar).
    Fallback: tabla asistencia (columna fecha TEXT 'YYYY-MM-DD', SIN anio_escolar).
    Retorna None si no hay datos suficientes.
    """
    anio1, anio2 = _anios_de_escolar(anio_escolar)

    # Fuente primaria: asistencia_mensual — filtra por anio IN (2025, 2026)
    row = db.execute(
        """
        SELECT SUM(dias_asistio)          AS asistio,
               SUM(dias_clase_impartidos) AS total
        FROM   asistencia_mensual
        WHERE  estudiante_id = ? AND materia = ?
          AND  anio IN (?, ?)
        """,
        (est_id, materia, anio1, anio2),
    ).fetchone()

    if row and row["total"] and row["total"] > 0:
        pct_asistencia = (row["asistio"] or 0) / row["total"]
        return round(1.0 - pct_asistencia, 4)

    # Fallback: tabla asistencia granular — filtra por año dentro de fecha TEXT
    a1, a2 = str(anio1), str(anio2)
    total = db.execute(
        """
        SELECT COUNT(*) FROM asistencia
        WHERE  estudiante_id = ? AND materia = ?
          AND  (strftime('%Y', fecha) = ? OR strftime('%Y', fecha) = ?)
        """,
        (est_id, materia, a1, a2),
    ).fetchone()[0]

    # Mínimo de registros para que el cálculo sea estadísticamente válido.
    # 1-2 pases sueltos dan porcentajes absurdos (ej: 1 ausencia / 1 total = 100%).
    MIN_REGISTROS = 10
    if not total or total < MIN_REGISTROS:
        return None

    ausencias = db.execute(
        """
        SELECT COUNT(*) FROM asistencia
        WHERE  estudiante_id = ? AND materia = ? AND estado = 'ausente'
          AND  (strftime('%Y', fecha) = ? OR strftime('%Y', fecha) = ?)
        """,
        (est_id, materia, a1, a2),
    ).fetchone()[0]

    return round(ausencias / total, 4)


def reprueba_por_inasistencia(
    db,
    est_id: int,
    materia: str,
    anio_escolar: str,
) -> tuple[bool, Optional[float]]:
    """Retorna (reprueba: bool, pct_inasistencia: float|None)."""
    pct = calcular_pct_inasistencia_materia(db, est_id, materia, anio_escolar)
    if pct is None:
        return False, None
    return pct > UMBRAL_INASISTENCIA, pct


# ── Nota efectiva por materia ─────────────────────────────────────────────────

def nota_efectiva_materia(
    promedio_anual: Optional[float],
    nota_completiva: Optional[float],
    es_6to: bool,
) -> tuple[Optional[float], str]:
    """
    Calcula la nota que decide aprobación en el centro.
    Retorna (nota_efectiva, estado_calculo).

    Ord. 1-2016 MINERD:
      - El centro evalúa si el estudiante aprobó sus materias (≥70) con el promedio anual.
      - La fórmula 70% nota centro + 30% prueba nacional la calcula el MINERD externamente.
      - La completiva (si existe) mejora el promedio interno pero NO bloquea la promoción.

    estado_calculo:
      'completiva_aplicada' → 6to con completiva registrada (promedio ajustado)
      'promedio_directo'    → cualquier grado, incluyendo 6to sin completiva
    """
    if es_6to and nota_completiva is not None:
        # Completiva registrada: ajusta el promedio (dato informativo para el récord)
        nota = (promedio_anual or 0) * PESO_ANUAL_6TO + nota_completiva * PESO_COMPLETIVA_6TO
        return round(nota, 2), "completiva_aplicada"
    # Sin completiva o no es 6to: usar promedio anual directamente
    return promedio_anual, "promedio_directo"


def calcular_estado_materia(
    nota_efectiva: Optional[float],
    reprueba_asist: bool,
    estado_calculo: str,
) -> str:
    """
    Prioridades:
      1. Reprueba por asistencia → REPROBADA_ASISTENCIA
      2. Sin completiva (6to)    → PENDIENTE
      3. nota >= 70              → APROBADA
      4. nota < 70               → REPROBADA
    """
    if reprueba_asist:
        return EST_REPROBADA_ASISTENCIA
    if estado_calculo == "pendiente_completiva":
        return EST_PENDIENTE
    if nota_efectiva is not None and nota_efectiva >= NOTA_MINIMA:
        return EST_APROBADA
    return EST_REPROBADA


# ── Motor central (no escribe en BD) ─────────────────────────────────────────

def evaluar_estudiante(
    db,
    est_id: int,
    anio_escolar: str,
) -> dict:
    """
    Calcula el estado de promoción de un estudiante SIN escribir en BD.

    Retorna dict con:
      est_id, grado, ciclo, tiene_completiva, siguiente_grado,
      estado (PROMOVIDO|RECUPERACION|NO_PROMOVIDO|PENDIENTE),
      mats_total, mats_aprobadas, mats_reprobadas, mats_pendientes,
      mats_recuperacion (lista de nombres), detalle_materias, razon
    """
    # 1. Leer datos del estudiante
    est = db.execute(
        "SELECT grado, nombre, apellido, seccion, mencion FROM estudiantes WHERE id = ?",
        (est_id,),
    ).fetchone()

    if not est:
        return {"ok": False, "error": f"Estudiante {est_id} no encontrado"}

    info_grado = clasificar_grado(est["grado"] or "")
    grado_norm = info_grado["grado_norm"]
    es_6to     = info_grado["tiene_completiva"]

    try:
        sig_grado = siguiente_grado(grado_norm)
    except ValueError:
        sig_grado = "DESCONOCIDO"

    # 2. Leer materias del año — fuente canónica: calificaciones_periodo (notas manuales
    #    de profesores) con fallback a materias_calificaciones (importación PDF).
    #    Esto garantiza que Diseño Básico u otras materias con notas manuales usen
    #    los datos reales, no los ceros del PDF.
    notas_canon = obtener_notas_estudiante(db, est_id, anio_escolar)

    # Deduplicar usando _normalizar_clave_materia (consulta _MATERIA_SINONIMOS):
    # · MAYÚS vs Title Case del mismo nombre → misma clave
    # · Alias cross-mención (ej: "HISTORIA DEL ARTE UNIVERSAL Y ESTÉTICA DIGITAL"
    #   vs "Introducción a la Historia del Arte...") → misma clave canónica
    # Regla de merge: conservar la entrada con promedio más alto; para períodos
    # individuales faltantes, completar con la otra entrada.
    dedup: dict = {}   # {clave_canon: (nombre_display, datos)}
    for mat, d in notas_canon.items():
        key = _normalizar_clave_materia(mat)
        if key not in dedup:
            dedup[key] = (mat, dict(d))
        else:
            prev_mat, prev_d = dedup[key]
            # Completar períodos faltantes con la entrada alternativa
            merged = dict(prev_d)
            for p in ("p1", "p2", "p3", "p4"):
                if not (merged.get(p) and merged[p] > 0) and (d.get(p) and d[p] > 0):
                    merged[p] = d[p]
            # Recalcular promedio con todos los períodos disponibles
            vals = [merged[p] for p in ("p1", "p2", "p3", "p4") if merged.get(p) and merged[p] > 0]
            merged["promedio"] = round(sum(vals) / len(vals), 2) if vals else 0.0
            # Preferir nombre Proper Case sobre TODO MAYÚSCULAS
            nombre_display = prev_mat if prev_mat != prev_mat.upper() else mat
            dedup[key] = (nombre_display, merged)

    # Construir lista ordenada, compatible con el resto del motor
    materias_rows = [
        {"materia": mat, "p1": d["p1"], "p2": d["p2"],
         "p3": d["p3"], "p4": d["p4"], "promedio": d["promedio"]}
        for _, (mat, d) in sorted(dedup.items())
    ]

    if not materias_rows:
        return {
            "est_id": est_id,
            "grado": grado_norm,
            "ciclo": info_grado["ciclo"],
            "tiene_completiva": es_6to,
            "siguiente_grado": sig_grado,
            "estado": PROM_PENDIENTE,
            "mats_total": 0,
            "mats_aprobadas": 0,
            "mats_reprobadas": 0,
            "mats_pendientes": 0,
            "mats_recuperacion": [],
            "detalle_materias": [],
            "razon": "Sin materias registradas para el año escolar",
        }

    # 3. Leer notas completivas (solo relevante para 6to)
    completivas = {}
    if es_6to:
        rows_c = db.execute(
            """
            SELECT materia, nota_completiva
            FROM   recuperaciones_pedagogicas
            WHERE  estudiante_id = ? AND anio_escolar = ? AND nota_completiva IS NOT NULL
            """,
            (est_id, anio_escolar),
        ).fetchall()
        completivas = {r["materia"]: r["nota_completiva"] for r in rows_c}

    # 4. Evaluar cada materia
    detalle = []
    conteo = {EST_APROBADA: 0, EST_REPROBADA: 0, EST_PENDIENTE: 0, EST_REPROBADA_ASISTENCIA: 0}
    mats_reprobadas_nombres = []

    for row in materias_rows:
        materia = row["materia"]
        promedio_anual = row["promedio"]

        # Verificar períodos incompletos (detectamos materia sin datos reales)
        periodos_con_nota = sum(
            1 for p in [row["p1"], row["p2"], row["p3"], row["p4"]] if p and p > 0
        )

        nota_comp = completivas.get(materia) if es_6to else None
        nota_ef, estado_calc = nota_efectiva_materia(promedio_anual, nota_comp, es_6to)

        # Si todos los períodos son 0 y no tiene completiva → PENDIENTE
        if periodos_con_nota == 0 and not (es_6to and nota_comp is not None):
            estado_calc = "pendiente_completiva" if es_6to else "sin_datos"
            nota_ef = None

        reprueba_asist, pct_asist = reprueba_por_inasistencia(db, est_id, materia, anio_escolar)

        # Para "sin_datos" lo tratamos como PENDIENTE
        estado_mat = calcular_estado_materia(nota_ef, reprueba_asist, estado_calc)
        if estado_calc == "sin_datos":
            estado_mat = EST_PENDIENTE

        conteo[estado_mat] = conteo.get(estado_mat, 0) + 1

        if estado_mat in (EST_REPROBADA, EST_REPROBADA_ASISTENCIA):
            mats_reprobadas_nombres.append(materia)

        detalle.append({
            "materia":              materia,
            "promedio_anual":       promedio_anual,
            "nota_completiva":      nota_comp,
            "nota_final_efectiva":  nota_ef,
            "pct_inasistencia":     pct_asist,
            "reprobada_asistencia": reprueba_asist,
            "estado_materia":       estado_mat,
        })

    total        = len(materias_rows)
    n_aprobadas  = conteo[EST_APROBADA]
    n_reprobadas = conteo[EST_REPROBADA] + conteo[EST_REPROBADA_ASISTENCIA]
    n_pendientes = conteo[EST_PENDIENTE]

    # 5. Leer criterios del nivel desde BD (con fallback a constantes)
    #    Permite que el coordinador los ajuste por ordenanza sin tocar código.
    _nota_minima   = NOTA_MINIMA
    _max_recup     = MAX_MATS_RECUP
    _umbral_limite = 65  # por debajo de nota_minima hasta aquí → caso límite
    try:
        _crit = db.execute("""
            SELECT nota_minima, max_areas_aplazado, umbral_caso_limite_inferior
            FROM   criterios_promocion
            WHERE  nivel IN ('secundario_academico','primario')
              AND  activo = 1
            ORDER BY vigente_desde DESC LIMIT 1
        """).fetchone()
        if _crit:
            _nota_minima   = _crit["nota_minima"]
            _max_recup     = _crit["max_areas_aplazado"]
            _umbral_limite = _crit["umbral_caso_limite_inferior"]
    except Exception:
        pass

    # 5b. Verificar perfil inclusivo — criterios diferenciados
    _nota_minima_efec = _nota_minima
    _perfil_inclusivo = None
    try:
        _pi = db.execute("""
            SELECT nota_minima_diferenciada, asistencia_minima_diferenciada,
                   perfil, plan_adaptacion_json
            FROM   estudiante_perfil_inclusivo
            WHERE  estudiante_id = ? AND activo = 1
            LIMIT  1
        """, (est_id,)).fetchone()
        if _pi:
            _perfil_inclusivo = dict(_pi)
            if _pi["nota_minima_diferenciada"] is not None:
                _nota_minima_efec = _pi["nota_minima_diferenciada"]
    except Exception:
        pass

    # 5c. Detectar caso límite: alguna materia reprobada tiene promedio entre
    #     umbral_caso_limite_inferior y nota_minima_efectiva − 1
    mats_caso_limite = [
        d["materia"] for d in detalle
        if d["estado_materia"] in (EST_REPROBADA,)
        and d["nota_final_efectiva"] is not None
        and _umbral_limite <= d["nota_final_efectiva"] < _nota_minima_efec
    ]
    caso_limite = len(mats_caso_limite) > 0

    # 5d. Determinar estado global
    if n_pendientes > 0:
        estado  = PROM_PENDIENTE
        razon   = f"{n_pendientes} materia(s) pendiente(s) (sin completiva o datos incompletos)"
    elif n_reprobadas == 0:
        estado  = PROM_PROMOVIDO
        razon   = "Todas las materias aprobadas"
    elif n_reprobadas <= _max_recup:
        estado  = PROM_RECUPERACION
        razon   = f"{n_reprobadas} materia(s) en recuperación: {', '.join(mats_reprobadas_nombres)}"
    else:
        estado  = PROM_NO_PROMOVIDO
        razon   = f"{n_reprobadas} materias reprobadas (límite: {_max_recup})"

    requiere_revision = caso_limite or (_perfil_inclusivo is not None)

    return {
        "est_id":                 est_id,
        "nombre":                 est["nombre"],
        "apellido":               est["apellido"],
        "seccion":                est["seccion"],
        "mencion":                est["mencion"],
        "grado":                  grado_norm,
        "ciclo":                  info_grado["ciclo"],
        "tiene_completiva":       es_6to,
        "siguiente_grado":        sig_grado,
        "estado":                 estado,
        "mats_total":             total,
        "mats_aprobadas":         n_aprobadas,
        "mats_reprobadas":        n_reprobadas,
        "mats_pendientes":        n_pendientes,
        "mats_recuperacion":      mats_reprobadas_nombres,
        "detalle_materias":       detalle,
        "razon":                  razon,
        # Nuevos campos — sistemanotas.md
        "caso_limite":            caso_limite,
        "mats_caso_limite":       mats_caso_limite,
        "requiere_revision_humana": requiere_revision,
        "perfil_inclusivo":       _perfil_inclusivo,
        "criterios_aplicados": {
            "nota_minima": _nota_minima_efec,
            "max_areas_aplazado": _max_recup,
            "umbral_caso_limite": _umbral_limite,
            "diferenciados": _perfil_inclusivo is not None,
        },
    }


def evaluar_grado(
    db,
    grado: str,
    anio_escolar: str,
    solo_activos: bool = True,
) -> list[dict]:
    """
    Evalúa a todos los estudiantes ACTIVOS de un grado.
    Los estudiantes RETIRADOS se excluyen del listado — sus datos permanecen
    en la BD pero no participan en el proceso de promoción.
    Añade ya_procesado y estado_previo a cada resultado.
    """
    grado_norm = _norm_grado(grado)
    # Solo ACTIVOS — retirados quedan excluidos del listado de promoción
    cond = "condicion = 'ACTIVO' AND " if solo_activos else ""

    estudiantes = db.execute(
        f"""
        SELECT id FROM estudiantes
        WHERE  {cond}UPPER(TRIM(grado)) = ?
        ORDER  BY apellido, nombre
        """,
        (grado_norm,),
    ).fetchall()

    resultados = []
    for est in estudiantes:
        res = evaluar_estudiante(db, est["id"], anio_escolar)

        # Verificar si ya fue procesado este año
        prev = db.execute(
            "SELECT estado FROM promociones WHERE estudiante_id = ? AND anio_escolar = ?",
            (est["id"], anio_escolar),
        ).fetchone()
        res["ya_procesado"]  = prev is not None
        res["estado_previo"] = prev["estado"] if prev else None

        resultados.append(res)

    return resultados


def resumen_grado(resultados: list[dict]) -> dict:
    """Agrega conteos de evaluar_grado() — función pura."""
    conteo = {PROM_PROMOVIDO: 0, PROM_RECUPERACION: 0, PROM_NO_PROMOVIDO: 0, PROM_PENDIENTE: 0}
    for r in resultados:
        estado = r.get("estado", PROM_PENDIENTE)
        conteo[estado] = conteo.get(estado, 0) + 1

    # Determinar etapa del flujo de promoción
    # Etapa 1: hay pendientes → el año aún no completó los 4 períodos
    # Etapa 2: sin pendientes, hay promovidos/recuperacion sin procesar → listo para ejecutar
    # Etapa 3: promovidos ejecutados, quedan recuperacion por extraordinario
    # Etapa 4: todo procesado
    total      = len(resultados)
    pendientes = conteo[PROM_PENDIENTE]
    ya_proc    = sum(1 for r in resultados if r.get("ya_procesado"))
    recuperacion_sin_proc = sum(
        1 for r in resultados
        if r.get("estado") == PROM_RECUPERACION and not r.get("ya_procesado")
    )

    if pendientes > 0:
        etapa = 1  # Año incompleto
    elif ya_proc == 0:
        etapa = 2  # Año completo, listo para ejecutar primera ronda
    elif recuperacion_sin_proc > 0:
        etapa = 3  # Promovidos ejecutados, quedan en recuperación
    else:
        etapa = 4  # Proceso finalizado

    return {
        "promovidos":    conteo[PROM_PROMOVIDO],
        "recuperacion":  conteo[PROM_RECUPERACION],
        "no_promovidos": conteo[PROM_NO_PROMOVIDO],
        "pendientes":    pendientes,
        "total":         total,
        "etapa":         etapa,
    }


# ── Recuperación post-agosto ──────────────────────────────────────────────────

def evaluar_post_recuperacion(
    db,
    est_id: int,
    anio_escolar: str,
) -> dict:
    """
    Re-evalúa el estudiante DESPUÉS de ingresar notas de recuperación de agosto.
    Para materias reprobadas busca nota_recuperacion en recuperaciones_pedagogicas.
    Si nota_recuperacion >= 70 → materia aprobada post-recuperación.
    """
    base = evaluar_estudiante(db, est_id, anio_escolar)
    if "error" in base:
        return base

    # Solo aplica a estudiantes en recuperación
    if base["estado"] != PROM_RECUPERACION:
        base["post_recuperacion"] = False
        return base

    # Leer notas de recuperación
    rec_rows = db.execute(
        """
        SELECT materia, nota_recuperacion
        FROM   recuperaciones_pedagogicas
        WHERE  estudiante_id = ? AND anio_escolar = ? AND nota_recuperacion IS NOT NULL
        """,
        (est_id, anio_escolar),
    ).fetchall()
    rec_map = {r["materia"]: r["nota_recuperacion"] for r in rec_rows}

    mats_aprobadas_rec  = []
    mats_reprobadas_rec = []

    # Recalcular solo las materias reprobadas
    nuevas_mats_reprobadas = []
    for det in base["detalle_materias"]:
        if det["estado_materia"] in (EST_REPROBADA, EST_REPROBADA_ASISTENCIA):
            nota_rec = rec_map.get(det["materia"])
            if nota_rec is not None and nota_rec >= NOTA_MINIMA:
                det["estado_materia"]      = EST_APROBADA
                det["nota_recuperacion"]   = nota_rec
                mats_aprobadas_rec.append(det["materia"])
            else:
                nuevas_mats_reprobadas.append(det["materia"])
                mats_reprobadas_rec.append(det["materia"])
                det["nota_recuperacion"]   = nota_rec

    n_rep_post = len(nuevas_mats_reprobadas)

    if n_rep_post == 0:
        base["estado"] = PROM_PROMOVIDO
        base["razon"]  = "Aprobó todas las materias en recuperación de agosto"
    else:
        base["estado"] = PROM_NO_PROMOVIDO
        base["razon"]  = f"Reprobó recuperación en: {', '.join(mats_reprobadas_rec)}"

    base["post_recuperacion"]          = True
    base["mats_recuperacion_aprobadas"]  = mats_aprobadas_rec
    base["mats_recuperacion_reprobadas"] = mats_reprobadas_rec
    return base


# ── Ejecución de promoción (escribe en BD) ────────────────────────────────────

def ejecutar_promocion_estudiante(
    db,
    est_id: int,
    anio_escolar: str,
    ejecutado_por: int,
    post_recuperacion: bool = False,
    forzar: bool = False,
    forzar_promovido: bool = False,
    observacion: str = "",
) -> dict:
    """
    Escribe el resultado en BD. El caller hace commit.

    post_recuperacion=True → usa evaluar_post_recuperacion()
    forzar=True            → procede aunque haya materias PENDIENTES (con advertencia)
    forzar_promovido=True  → override manual: mueve al estudiante al siguiente grado
                             aunque el motor lo clasifique RECUPERACION/NO_PROMOVIDO.
                             Requiere justificación (observacion) por auditoría.
    """
    if post_recuperacion:
        ev = evaluar_post_recuperacion(db, est_id, anio_escolar)
    else:
        ev = evaluar_estudiante(db, est_id, anio_escolar)

    if "error" in ev:
        return {"ok": False, "est_id": est_id, "error": ev["error"]}

    estado       = ev["estado"]
    grado_origen = ev["grado"]
    sig_grado    = ev["siguiente_grado"]

    # Bloquear si hay pendientes (a menos que se fuerce)
    if estado == PROM_PENDIENTE and not forzar:
        return {
            "ok":      False,
            "est_id":  est_id,
            "estado":  estado,
            "error":   ev["razon"],
            "requiere_confirmacion": True,
        }

    # Determinar grado_destino
    promover_fisicamente = estado == PROM_PROMOVIDO or forzar_promovido
    if promover_fisicamente:
        grado_destino = sig_grado
    else:
        grado_destino = grado_origen  # permanece en el mismo grado

    # Cuando se fuerza la promoción manual: el estado registrado en la tabla
    # promociones es PROMOVIDO (para que boletin_estudiante() lo detecte correctamente).
    # La observación documenta que fue una decisión manual.
    if forzar_promovido and estado != PROM_PROMOVIDO:
        observacion = f"[PROMOCIÓN MANUAL] {observacion}".strip()
        estado = PROM_PROMOVIDO  # override: se registra como PROMOVIDO en BD

    # Actualizar grado/condición del estudiante
    if promover_fisicamente:
        if sig_grado == "CANDIDATO_PRUEBAS":
            # 6TO aprobado → candidato a Pruebas Nacionales (Ord. 1-2016 MINERD)
            # condicion cambia; el grado se mantiene en 6TO hasta que obtenga el título
            db.execute(
                "UPDATE estudiantes SET condicion = 'CANDIDATO_PRUEBAS' WHERE id = ?",
                (est_id,),
            )
        else:
            # Construir nuevo curso: "4TO MULTIMEDIA" → "5TO MULTIMEDIA"
            est_row = db.execute(
                "SELECT curso FROM estudiantes WHERE id = ?", (est_id,)
            ).fetchone()
            curso_actual = (est_row["curso"] if est_row else "") or ""
            partes = curso_actual.split(None, 1)
            mencion = partes[1] if len(partes) > 1 else ""
            nuevo_curso = f"{sig_grado} {mencion}".strip() if mencion else sig_grado

            # Actualiza grado, curso y resetea KPIs y asistencia — nuevo año desde cero
            db.execute(
                """UPDATE estudiantes
                   SET grado          = ?,
                       curso          = ?,
                       p_acad         = NULL,
                       acad_p1        = NULL,
                       acad_p2        = NULL,
                       acad_p3        = NULL,
                       acad_p4        = NULL,
                       asistencia_p1  = NULL,
                       asistencia_p2  = NULL,
                       asistencia_p3  = NULL,
                       asistencia_p4  = NULL
                   WHERE id = ?""",
                (sig_grado, nuevo_curso, est_id),
            )

    # Guardar en tabla promociones (upsert)
    db.execute(
        """
        INSERT INTO promociones
            (estudiante_id, grado_origen, grado_destino, anio_escolar,
             estado, mats_reprobadas, mats_total, ejecutado_por, observacion,
             tiene_completiva, mats_pendientes, mats_recuperacion, ciclo,
             caso_limite, requiere_revision_humana)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(estudiante_id, anio_escolar) DO UPDATE SET
            grado_origen              = excluded.grado_origen,
            grado_destino             = excluded.grado_destino,
            estado                    = excluded.estado,
            mats_reprobadas           = excluded.mats_reprobadas,
            mats_total                = excluded.mats_total,
            ejecutado_por             = excluded.ejecutado_por,
            observacion               = excluded.observacion,
            tiene_completiva          = excluded.tiene_completiva,
            mats_pendientes           = excluded.mats_pendientes,
            mats_recuperacion         = excluded.mats_recuperacion,
            ciclo                     = excluded.ciclo,
            caso_limite               = excluded.caso_limite,
            requiere_revision_humana  = excluded.requiere_revision_humana,
            fecha                     = datetime('now')
        """,
        (
            est_id, grado_origen, grado_destino, anio_escolar,
            estado, ev["mats_reprobadas"], ev["mats_total"],
            ejecutado_por, observacion,
            1 if ev["tiene_completiva"] else 0,
            ev["mats_pendientes"],
            json.dumps(ev["mats_recuperacion"], ensure_ascii=False),
            ev["ciclo"],
            1 if ev.get("caso_limite") else 0,
            1 if ev.get("requiere_revision_humana") else 0,
        ),
    )

    # Obtener id de la fila de promociones recién insertada/actualizada
    prom_id = db.execute(
        "SELECT id FROM promociones WHERE estudiante_id = ? AND anio_escolar = ?",
        (est_id, anio_escolar),
    ).fetchone()["id"]

    # Log inmutable por materia
    db.execute(
        "DELETE FROM promocion_detalle_materias WHERE promocion_id = ?",
        (prom_id,),
    )
    for det in ev["detalle_materias"]:
        db.execute(
            """
            INSERT INTO promocion_detalle_materias
                (promocion_id, estudiante_id, materia, anio_escolar,
                 promedio_anual, nota_completiva, nota_final_efectiva,
                 aprobada, reprobada_asistencia, pct_inasistencia, estado_materia)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                prom_id, est_id, det["materia"], anio_escolar,
                det["promedio_anual"], det.get("nota_completiva"),
                det["nota_final_efectiva"],
                1 if det["estado_materia"] == EST_APROBADA else 0,
                1 if det["reprobada_asistencia"] else 0,
                det["pct_inasistencia"], det["estado_materia"],
            ),
        )

    return {
        "ok":            True,
        "est_id":        est_id,
        "estado":        estado,
        "grado_origen":  grado_origen,
        "grado_destino": grado_destino,
        "siguiente_grado": sig_grado,
        "prom_id":       prom_id,
        "error":         None,
    }


def ejecutar_promocion_lote(
    db,
    grado: str,
    anio_escolar: str,
    estudiante_ids: list[int],
    ejecutado_por: int,
    post_recuperacion: bool = False,
    observacion: str = "",
) -> dict:
    """
    Ejecuta la promoción para una lista de estudiantes en UNA sola transacción.
    Si falla uno, hace rollback completo.
    """
    conteo = {PROM_PROMOVIDO: 0, PROM_RECUPERACION: 0, PROM_NO_PROMOVIDO: 0, PROM_PENDIENTE: 0}
    errores = []

    try:
        db.execute("BEGIN IMMEDIATE")
        for est_id in estudiante_ids:
            res = ejecutar_promocion_estudiante(
                db, est_id, anio_escolar, ejecutado_por,
                post_recuperacion=post_recuperacion,
                observacion=observacion,
            )
            if res["ok"]:
                conteo[res["estado"]] = conteo.get(res["estado"], 0) + 1
            else:
                if res.get("requiere_confirmacion"):
                    conteo[PROM_PENDIENTE] += 1
                    errores.append({"est_id": est_id, "error": res["error"]})
                else:
                    errores.append({"est_id": est_id, "error": res.get("error", "Error desconocido")})
        db.execute("COMMIT")
    except Exception as exc:
        db.execute("ROLLBACK")
        log.exception("ejecutar_promocion_lote: rollback por error en grado %s", grado)
        return {
            "ok":     False,
            "grado":  _norm_grado(grado),
            "error":  str(exc),
            "errores": errores,
        }

    try:
        sig = siguiente_grado(grado)
    except ValueError:
        sig = "DESCONOCIDO"

    return {
        "ok":                   True,
        "grado":                _norm_grado(grado),
        "siguiente_grado":      sig,
        "promovidos":           conteo[PROM_PROMOVIDO],
        "recuperacion":         conteo[PROM_RECUPERACION],
        "no_promovidos":        conteo[PROM_NO_PROMOVIDO],
        "pendientes_bloqueados": conteo[PROM_PENDIENTE],
        "errores":              errores,
    }
