#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
diag_curso_estudiante.py
==========================
Diagnóstico de solo lectura: muestra TODAS las columnas relevantes
(id, nombre, apellido, cedula, grado, curso, mencion, seccion, ciclo,
condicion) de los estudiantes cuyo nombre coincide con lo que se pase,
para ver exactamente qué quedó guardado — sin adivinar por lo que se ve
en pantalla.

Uso:
    python3 scripts/diag_curso_estudiante.py "Amparo Matos"
    python3 scripts/diag_curso_estudiante.py "Feliz Jimenez"
"""
import os
import sqlite3
import sys

_en_render = os.path.exists("/data")
DB_PATH = os.environ.get(
    "DATABASE_PATH",
    "/data/database.db" if _en_render
    else os.path.join(os.path.dirname(__file__), "..", "database.db"),
)


def main():
    if len(sys.argv) < 2:
        print("Uso: python3 scripts/diag_curso_estudiante.py <texto a buscar en nombre/apellido>")
        sys.exit(1)
    q = sys.argv[1]

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """SELECT id, nombre, apellido, cedula, grado, curso, mencion, seccion, ciclo, condicion
           FROM estudiantes
           WHERE nombre LIKE ? OR apellido LIKE ?
           ORDER BY id""",
        (f"%{q}%", f"%{q}%")
    ).fetchall()

    print(f"BD: {DB_PATH}")
    print(f"Coincidencias para {q!r}: {len(rows)}\n")
    for r in rows:
        for k in r.keys():
            print(f"  {k:<12} = {r[k]!r}")
        print()


if __name__ == "__main__":
    main()
