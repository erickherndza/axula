#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
resetear_notas_todos.py
=========================
Borra TODAS las notas del sistema (todos los grados/menciones) para volver
a empezar de cero, después de que un fix de grado dejó estudiantes sin
notas (y por lo tanto sin poder evaluarse para promoción). Pensado para
usarse junto con la recarga de listados actualizados por grado.

Borra (irreversible):
  - materias_calificaciones     (notas de PDF/Excel)
  - calificaciones_periodo      (notas manuales — fuente "oficial")
  - notas_componentes           (examen/máscota/participación/etc.)
  - notas_competencias_ce       (evaluación por competencias)
  - notas_actividad             (notas de asignaciones)

Y resetea a 0 las columnas de `estudiantes` que cachean esas notas
(p_acad, acad_p1-4, tiene_notas, prom_modulos, y los módulos técnicos de
las 4 menciones: fotografía/lenguaje visual/diseño, instrumento/canto/
lenguaje musical, entrenamiento/expresión/historia del teatro, dibujo/
pintura/historia del arte) — si no se resetean, el perfil sigue mostrando
números viejos aunque las tablas de origen ya estén vacías.

NO TOCA: estudiantes.grado/curso/mencion/condicion, asistencia, cuaderno
anecdótico/casos, ni el historial de promociones (recuperaciones_
pedagogicas, promociones, promocion_detalle_materias).

Uso:
    # Dry-run (no escribe en BD) — SIEMPRE correr esto primero
    python3 scripts/resetear_notas_todos.py

    # Borrado real
    python3 scripts/resetear_notas_todos.py --commit
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

TABLAS_NOTAS = [
    "materias_calificaciones",
    "calificaciones_periodo",
    "notas_componentes",
    "notas_competencias_ce",
    "notas_actividad",
]

COLUMNAS_A_RESETEAR = [
    "p_acad", "acad_p1", "acad_p2", "acad_p3", "acad_p4", "tiene_notas", "prom_modulos",
    # MULTIMEDIA
    "fotografia_p1", "fotografia_p2", "fotografia_p3", "fotografia_p4", "p_foto",
    "lv_p1", "lv_p2", "lv_p3", "lv_p4", "p_lv",
    "diseno_p1", "diseno_p2", "diseno_p3", "diseno_p4", "p_diseno",
    # MÚSICA
    "instrumento_p1", "instrumento_p2", "instrumento_p3", "instrumento_p4", "p_instrumento",
    "canto_p1", "canto_p2", "canto_p3", "canto_p4", "p_canto",
    "lenguaje_musical_p1", "lenguaje_musical_p2", "lenguaje_musical_p3", "lenguaje_musical_p4", "p_lenguaje_musical",
    # TEATRO
    "entrenamiento_p1", "entrenamiento_p2", "entrenamiento_p3", "entrenamiento_p4", "p_entrenamiento",
    "expresion_p1", "expresion_p2", "expresion_p3", "expresion_p4", "p_expresion",
    "historia_teatro_p1", "historia_teatro_p2", "historia_teatro_p3", "historia_teatro_p4", "p_historia_teatro",
    # ARTES VISUALES
    "dibujo_p1", "dibujo_p2", "dibujo_p3", "dibujo_p4", "p_dibujo",
    "pintura_p1", "pintura_p2", "pintura_p3", "pintura_p4", "p_pintura",
    "historia_arte_p1", "historia_arte_p2", "historia_arte_p3", "historia_arte_p4", "p_historia_arte",
]


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    print(f"BD: {DB_PATH}")
    print(f"Modo: {'COMMIT (borra en serio)' if COMMIT else 'DRY-RUN (solo muestra qué haría)'}\n")

    cols_existentes = {r[1] for r in conn.execute("PRAGMA table_info(estudiantes)").fetchall()}
    cols_a_resetear = [c for c in COLUMNAS_A_RESETEAR if c in cols_existentes]
    cols_faltantes = [c for c in COLUMNAS_A_RESETEAR if c not in cols_existentes]
    if cols_faltantes:
        print(f"(nota: estas columnas no existen en esta BD y se omiten: {cols_faltantes})\n")

    print("=" * 60)
    print("Filas a borrar por tabla:")
    print("=" * 60)
    total_filas = 0
    for tabla in TABLAS_NOTAS:
        existe = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (tabla,)
        ).fetchone()
        if not existe:
            print(f"  {tabla:<28} (no existe en esta BD, se omite)")
            continue
        n = conn.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
        total_filas += n
        print(f"  {tabla:<28} {n:>6} fila(s)")
    print(f"  {'TOTAL':<28} {total_filas:>6} fila(s)\n")

    n_con_notas = conn.execute(
        "SELECT COUNT(*) FROM estudiantes WHERE tiene_notas=1 OR p_acad>0"
    ).fetchone()[0]
    print(f"Estudiantes con KPIs de notas cacheados que se resetearán a 0: {n_con_notas}\n")

    if not COMMIT:
        print("(dry-run) Nada se borró. Corre de nuevo con --commit para aplicar.")
        conn.close()
        return

    for tabla in TABLAS_NOTAS:
        existe = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (tabla,)
        ).fetchone()
        if existe:
            conn.execute(f"DELETE FROM {tabla}")

    set_clause = ", ".join(f"{c}=0" for c in cols_a_resetear)
    conn.execute(f"UPDATE estudiantes SET {set_clause}")

    conn.commit()
    print(f"✓ Borrado: {total_filas} fila(s) de notas en {len(TABLAS_NOTAS)} tablas.")
    print(f"✓ Reseteadas {len(cols_a_resetear)} columnas de KPIs en {n_con_notas} estudiante(s) con notas.")
    conn.close()


if __name__ == "__main__":
    main()
