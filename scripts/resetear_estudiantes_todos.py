#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
resetear_estudiantes_todos.py
===============================
Borra TODOS los estudiantes y todo lo que depende de ellos, para volver a
cargar los listados oficiales desde cero — después de que cargas repetidas
(algunas con el cargador viejo, corruptas) dejaran el roster con datos
mezclados/duplicados entre grados y menciones.

Mantiene intactas las cuentas de `usuarios` (login de profesores/admin).

Tablas que se vacían (verificado contra el esquema real ejecutando
migrar_bd() en una BD temporal — no una lista escrita a mano):
    estudiantes, registro_liceo, acuerdos_compromiso, asistencia,
    asistencia_mensual, ausencias_semanales, calificaciones_periodo, casos,
    cuaderno_anecdotico, documentos_admin, entregas_asignacion,
    estudiante_perfil_inclusivo, evaluaciones_narrativas,
    historial_planificaciones, inscripciones, logros,
    materias_calificaciones, notas_actividad, notas_competencias_ce,
    notas_componentes, promocion_detalle_materias, promociones,
    recuperaciones_pedagogicas, reportes, retiros_traslados,
    vinculos_padre_estudiante

EXCLUIDA a propósito: expedientes_historicos — es el archivo digitalizado
de 25+ años del centro, vinculado a estudiantes.id de forma OPCIONAL
("vinculado a estudiantes activos si aplica"), no datos del año actual.
Correr scripts/resetear_expedientes_historicos.py aparte si también hace
falta borrarlo (no existe todavía — pedir si se necesita).

NO TOCA: usuarios (cuentas de login), configuracion_centro,
calendario_escolar, competencias_materia.

Uso:
    # Dry-run (no escribe en BD) — SIEMPRE correr esto primero
    python3 scripts/resetear_estudiantes_todos.py

    # Borrado real
    python3 scripts/resetear_estudiantes_todos.py --commit
"""
import os
import sys
import sqlite3

_en_render = os.path.exists("/data")
DB_PATH = os.environ.get(
    "DATABASE_PATH",
    "/data/database.db" if _en_render
    else os.path.join(os.path.dirname(__file__), "..", "database.db"),
)

COMMIT = "--commit" in sys.argv

TABLAS_ESTUDIANTE_ID = [
    "acuerdos_compromiso", "asistencia", "asistencia_mensual",
    "ausencias_semanales", "calificaciones_periodo", "casos",
    "cuaderno_anecdotico", "documentos_admin", "entregas_asignacion",
    "estudiante_perfil_inclusivo", "evaluaciones_narrativas",
    "historial_planificaciones", "inscripciones", "logros",
    "materias_calificaciones", "notas_competencias_ce", "notas_componentes",
    "promocion_detalle_materias", "promociones",
    "recuperaciones_pedagogicas", "reportes", "retiros_traslados",
    "vinculos_padre_estudiante",
]
TABLAS_EST_ID = ["notas_actividad"]  # usa 'est_id' en vez de 'estudiante_id'
TABLA_REGISTRO_LICEO = "registro_liceo"  # keyed por cedula, no estudiante_id


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    print(f"BD: {DB_PATH}")
    print(f"Modo: {'COMMIT (borra en serio)' if COMMIT else 'DRY-RUN (solo muestra qué haría)'}\n")

    tablas_existentes = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}

    plan = []
    for t in TABLAS_ESTUDIANTE_ID:
        if t in tablas_existentes:
            n = conn.execute(f"SELECT COUNT(*) FROM {t} WHERE estudiante_id IS NOT NULL").fetchone()[0]
            plan.append((t, "estudiante_id", n))
    for t in TABLAS_EST_ID:
        if t in tablas_existentes:
            n = conn.execute(f"SELECT COUNT(*) FROM {t} WHERE est_id IS NOT NULL").fetchone()[0]
            plan.append((t, "est_id", n))
    if TABLA_REGISTRO_LICEO in tablas_existentes:
        n = conn.execute(f"SELECT COUNT(*) FROM {TABLA_REGISTRO_LICEO}").fetchone()[0]
        plan.append((TABLA_REGISTRO_LICEO, None, n))
    n_estudiantes = conn.execute("SELECT COUNT(*) FROM estudiantes").fetchone()[0]

    print("=" * 60)
    print("Filas a borrar por tabla:")
    print("=" * 60)
    total = 0
    for t, col, n in plan:
        total += n
        print(f"  {t:<32} {n:>6} fila(s)")
    print(f"  {'estudiantes':<32} {n_estudiantes:>6} fila(s)")
    total += n_estudiantes
    print(f"  {'TOTAL':<32} {total:>6} fila(s)\n")

    print("(no se toca: usuarios, expedientes_historicos, configuracion_centro,")
    print(" calendario_escolar, competencias_materia)\n")

    if not COMMIT:
        print("(dry-run) Nada se borró. Corre de nuevo con --commit para aplicar.")
        conn.close()
        return

    for t, col, n in plan:
        if col:
            conn.execute(f"DELETE FROM {t} WHERE {col} IS NOT NULL")
        else:
            conn.execute(f"DELETE FROM {t}")
    conn.execute("DELETE FROM estudiantes")

    conn.commit()
    print(f"✓ Borrado: {total} fila(s) en {len(plan) + 1} tabla(s).")
    print("✓ usuarios y expedientes_historicos quedaron intactos.")
    conn.close()


if __name__ == "__main__":
    main()
