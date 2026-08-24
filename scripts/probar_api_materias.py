#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
probar_api_materias.py
========================
Ejecuta EXACTAMENTE la misma lógica que GET /api/materias/<id>
(routes/estudiantes.py::get_materias_estudiante) directamente contra la BD,
sin pasar por HTTP ni por el navegador — para descartar caché del browser
como causa de que /perfil/<id> siga mostrando materias de un grado anterior.

Uso:
    python3 scripts/probar_api_materias.py 509
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

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("DATABASE_PATH", DB_PATH)

from core.helpers import _anio_escolar_actual  # noqa: E402


def main():
    if len(sys.argv) != 2 or not sys.argv[1].isdigit():
        print("Uso: python3 scripts/probar_api_materias.py <estudiante_id>")
        sys.exit(1)

    estudiante_id = int(sys.argv[1])
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    anio = _anio_escolar_actual()
    print(f"BD: {DB_PATH}")
    print(f"_anio_escolar_actual() calculado AHORA MISMO: {anio!r}")

    est_row = conn.execute(
        "SELECT grado FROM estudiantes WHERE id=?", (estudiante_id,)
    ).fetchone()
    grado_actual = (est_row["grado"] if est_row else "") or ""
    print(f"grado_actual leído AHORA MISMO de estudiantes.id={estudiante_id}: {grado_actual!r}")
    print()

    rows = conn.execute("""
        SELECT materia, p1, p2, p3, p4, promedio, fecha_carga, fuente,
               COALESCE(tipo, 'académico') as tipo,
               COALESCE(profesor, '') as profesor
        FROM materias_calificaciones
        WHERE estudiante_id = ?
          AND (anio_escolar = ? OR anio_escolar IS NULL)
          AND (grado IS NULL OR UPPER(grado) = UPPER(?))
        ORDER BY CASE COALESCE(tipo,'académico')
                      WHEN 'académico' THEN 0 ELSE 1 END,
                 materia
    """, (estudiante_id, anio, grado_actual)).fetchall()

    print(f"Filas que devuelve la query EXACTA de /api/materias/{estudiante_id}: {len(rows)}")
    for r in rows:
        print(f"  {dict(r)}")

    conn.close()


if __name__ == "__main__":
    main()
