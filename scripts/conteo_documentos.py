#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
conteo_documentos.py
=====================
Diagnóstico de solo lectura: cuenta cuántos registros hay en la BD por
materia/mención, en las dos tablas que guardan "documentos" académicos:

  1. materias_calificaciones — notas del año escolar activo (PDF/manual/Excel),
     agrupadas por curso del estudiante (ej: "4to MULTIMEDIA") y por materia.
  2. expedientes_historicos — expedientes digitalizados (25+ años de archivo
     físico), agrupados por sistema_educativo ('bachillerato'/'secundaria')
     y mención.

No escribe nada en la BD.

Uso:
    python3 scripts/conteo_documentos.py
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
    if not os.path.exists(DB_PATH) or os.path.getsize(DB_PATH) == 0:
        print(f"BD vacía o inexistente en: {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    print(f"BD: {DB_PATH}\n")

    tablas = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}

    # ── 1. materias_calificaciones por curso (grado+mención) ──────────────
    if "materias_calificaciones" in tablas:
        print("=" * 70)
        print("MATERIAS_CALIFICACIONES — por curso del estudiante (año activo)")
        print("=" * 70)
        rows = conn.execute("""
            SELECT COALESCE(e.curso, '(sin curso)') AS curso, COUNT(*) AS n
            FROM materias_calificaciones mc
            JOIN estudiantes e ON e.id = mc.estudiante_id
            GROUP BY COALESCE(e.curso, '(sin curso)')
            ORDER BY n DESC
        """).fetchall()
        total = sum(r["n"] for r in rows)
        for r in rows:
            print(f"  {r['curso']:<30} {r['n']:>6}")
        print(f"  {'TOTAL':<30} {total:>6}\n")

        print("-" * 70)
        print("MATERIAS_CALIFICACIONES — por nombre de materia (top 40)")
        print("-" * 70)
        rows = conn.execute("""
            SELECT materia, COUNT(*) AS n
            FROM materias_calificaciones
            GROUP BY materia
            ORDER BY n DESC
            LIMIT 40
        """).fetchall()
        for r in rows:
            print(f"  {r['materia']:<50} {r['n']:>6}")
        print()
    else:
        print("(no existe la tabla materias_calificaciones)\n")

    # ── 2. expedientes_historicos por sistema + mención ────────────────────
    if "expedientes_historicos" in tablas:
        print("=" * 70)
        print("EXPEDIENTES_HISTORICOS — por sistema educativo + mención")
        print("=" * 70)
        rows = conn.execute("""
            SELECT COALESCE(sistema_educativo, '(sin sistema)') AS sistema,
                   COALESCE(NULLIF(TRIM(mencion), ''), '(sin mención)') AS mencion,
                   COUNT(*) AS n
            FROM expedientes_historicos
            GROUP BY sistema, mencion
            ORDER BY sistema, n DESC
        """).fetchall()
        total = 0
        for r in rows:
            print(f"  {r['sistema']:<14} {r['mencion']:<25} {r['n']:>6}")
            total += r["n"]
        print(f"  {'TOTAL':<14} {'':<25} {total:>6}\n")
    else:
        print("(no existe la tabla expedientes_historicos)\n")

    conn.close()


if __name__ == "__main__":
    main()
