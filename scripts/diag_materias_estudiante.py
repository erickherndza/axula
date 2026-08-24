#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
diag_materias_estudiante.py
============================
Diagnóstico de solo lectura: imprime TODAS las filas de
materias_calificaciones de un estudiante (cualquier año/grado) para ver
exactamente qué hay en grado/anio_escolar — en particular, filas con
grado o anio_escolar en NULL, que se cuelan en /api/materias/<id> sin
importar el grado actual del estudiante.

Uso:
    python3 scripts/diag_materias_estudiante.py 509
"""
import os
import sqlite3
import sys

_en_render = os.path.exists("/data")
DB_PATH = os.environ.get(
    "DATABASE_PATH",
    "/data/database.db"
    if _en_render
    else os.path.join(os.path.dirname(__file__), "..", "database.db"),
)


def main():
    if len(sys.argv) != 2 or not sys.argv[1].isdigit():
        print("Uso: python3 scripts/diag_materias_estudiante.py <estudiante_id>")
        sys.exit(1)

    est_id = int(sys.argv[1])
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    est = conn.execute(
        "SELECT id, nombre, apellido, grado, curso, condicion FROM estudiantes WHERE id=?",
        (est_id,),
    ).fetchone()
    if not est:
        print(f"No existe estudiante {est_id}")
        return
    print(f"BD: {DB_PATH}")
    print(f"Estudiante [{est['id']}] {est['nombre']} {est['apellido']} — grado actual: {est['grado']!r} curso: {est['curso']!r} condicion: {est['condicion']!r}")
    print()

    rows = conn.execute("""
        SELECT materia, grado, anio_escolar, tipo, p1, p2, p3, p4, promedio, fuente, fecha_carga
        FROM materias_calificaciones
        WHERE estudiante_id = ?
        ORDER BY anio_escolar, grado, materia
    """, (est_id,)).fetchall()

    print(f"Filas en materias_calificaciones: {len(rows)}\n")
    for r in rows:
        d = dict(r)
        marca = ""
        if d["grado"] is None or d["anio_escolar"] is None:
            marca = "  ← SIN ETIQUETAR (grado o anio_escolar en NULL)"
        print(
            f"  materia={d['materia']!r:55} grado={d['grado']!r:8} "
            f"anio={d['anio_escolar']!r:12} tipo={d['tipo']!r:12} "
            f"p1={d['p1']} p2={d['p2']} p3={d['p3']} p4={d['p4']} "
            f"prom={d['promedio']} fuente={d['fuente']!r}{marca}"
        )

    rows_cp = conn.execute("""
        SELECT materia, periodo, calificacion, anio_escolar, grado, origen
        FROM calificaciones_periodo
        WHERE estudiante_id = ?
        ORDER BY anio_escolar, materia, periodo
    """, (est_id,)).fetchall()
    print(f"\nFilas en calificaciones_periodo: {len(rows_cp)}\n")
    for r in rows_cp:
        d = dict(r)
        marca = "  ← SIN ETIQUETAR" if (d["grado"] is None or d["anio_escolar"] is None) else ""
        print(
            f"  materia={d['materia']!r:55} periodo={d['periodo']!r:6} nota={d['calificacion']} "
            f"grado={d['grado']!r:8} anio={d['anio_escolar']!r:12} origen={d['origen']!r}{marca}"
        )

    conn.close()


if __name__ == "__main__":
    main()
