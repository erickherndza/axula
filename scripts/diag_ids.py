#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
diag_ids.py
============
Diagnóstico de solo lectura: muestra los campos completos de una lista de
IDs de `estudiantes`, en el orden dado.

Uso:
    python3 scripts/diag_ids.py 1470 1471 1472 1473
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


def main():
    if len(sys.argv) < 2:
        print("Uso: python3 scripts/diag_ids.py <id1> <id2> ...")
        sys.exit(1)
    ids = [int(a) for a in sys.argv[1:]]

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    print(f"BD: {DB_PATH}\n")

    for i in ids:
        r = conn.execute(
            """SELECT id, nombre, apellido, cedula, grado, curso, mencion, seccion, ciclo, condicion
               FROM estudiantes WHERE id=?""",
            (i,)
        ).fetchone()
        if not r:
            print(f"id={i}: NO EXISTE")
            continue
        print(f"id={r['id']:<6} {r['nombre']} {r['apellido']}")
        print(f"   cedula={r['cedula']!r} grado={r['grado']!r} curso={r['curso']!r} "
              f"mencion={r['mencion']!r} seccion={r['seccion']!r} ciclo={r['ciclo']!r} condicion={r['condicion']!r}")

    conn.close()


if __name__ == "__main__":
    main()
