#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
diag_5to_multimedia.py
========================
Diagnóstico de solo lectura: muestra TODOS los estudiantes que matchean
grado LIKE '%5to%' AND curso LIKE '%MULTIMEDIA%' — la misma condición que
usa portal_profesor() para armar el roster — para ver por qué el conteo
no coincide con la lista real (debería ser 23).

Uso:
    python3 scripts/diag_5to_multimedia.py
"""
import os
import sqlite3

_en_render = os.path.exists("/data")
DB_PATH = os.environ.get(
    "DATABASE_PATH",
    "/data/database.db" if _en_render
    else os.path.join(os.path.dirname(__file__), "..", "database.db"),
)


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    print(f"BD: {DB_PATH}\n")

    rows = conn.execute("""
        SELECT id, nombre, apellido, cedula, grado, curso, mencion, seccion, condicion
        FROM estudiantes
        WHERE (condicion IS NULL OR condicion NOT IN ('RETIRADO','TRANSFERIDO'))
          AND grado LIKE '%5to%'
          AND curso LIKE '%MULTIMEDIA%'
        ORDER BY apellido, nombre
    """).fetchall()

    print(f"Total que matchean grado LIKE '%5to%' AND curso LIKE '%MULTIMEDIA%': {len(rows)}\n")
    for r in rows:
        print(f"  id={r['id']:<5} {r['apellido']:<28} {r['nombre']:<22} "
              f"cedula={r['cedula']!r:<14} grado={r['grado']!r:<10} curso={r['curso']!r:<30} "
              f"mencion={r['mencion']!r:<12} seccion={r['seccion']!r}")

    print("\n--- Agrupado por valor exacto de grado ---")
    for r in conn.execute("""
        SELECT grado, COUNT(*) n FROM estudiantes
        WHERE (condicion IS NULL OR condicion NOT IN ('RETIRADO','TRANSFERIDO'))
          AND grado LIKE '%5to%' AND curso LIKE '%MULTIMEDIA%'
        GROUP BY grado
    """).fetchall():
        print(f"  grado={r['grado']!r:<15} {r['n']}")

    print("\n--- Cédulas duplicadas dentro de este grupo ---")
    ceds = {}
    for r in rows:
        if r["cedula"]:
            ceds.setdefault(r["cedula"], []).append(r)
    for ced, lst in ceds.items():
        if len(lst) > 1:
            print(f"  cedula={ced}: {[(x['id'], x['nombre'], x['apellido']) for x in lst]}")

    conn.close()


if __name__ == "__main__":
    main()
