#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
diag_roster_profesor.py
=========================
Diagnóstico de solo lectura para entender por qué /profesor muestra menos
estudiantes de los esperados. No escribe nada en la BD. Muestra:

  1. El perfil crudo del profesor (rol, tipo_docencia, grado, mencion, ciclo,
     asignaturas) tal como está en `usuarios`.
  2. Lo que devuelve _resolver_alcance_profesor() con esos datos — el mismo
     cálculo que hace /profesor.
  3. La consulta EXACTA que arma portal_profesor() para el roster, con el
     conteo real de filas que devuelve.
  4. Todos los valores DISTINCT de `estudiantes.grado` que existen en la BD
     (para detectar variantes corruptas tipo 'Estudiantes 4TO MULTIMEDIA').
  5. Todos los valores DISTINCT de `estudiantes.curso` que contienen
     'MULTIMEDIA', con conteo por valor.
  6. Cuántos estudiantes hay cuyo NOMBRE coincide con alguno del archivo
     Excel más reciente que se le pasó al script (opcional).

Uso:
    python3 scripts/diag_roster_profesor.py <username_profesor>
    python3 scripts/diag_roster_profesor.py erick.hernandez@educacion.edu.do
"""
import os
import sys
import sqlite3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

_en_render = os.path.exists("/data")
DB_PATH = os.environ.get(
    "DATABASE_PATH",
    "/data/database.db" if _en_render
    else os.path.join(os.path.dirname(__file__), "..", "database.db"),
)


def main():
    if len(sys.argv) < 2:
        print("Uso: python3 scripts/diag_roster_profesor.py <username_profesor>")
        sys.exit(1)
    username = sys.argv[1]

    from core.helpers import _resolver_alcance_profesor  # noqa: E402

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    print(f"BD: {DB_PATH}\n")

    prof = conn.execute(
        "SELECT id, nombre, username, rol, tipo_docencia, grado, mencion, ciclo, "
        "asignaturas, materia FROM usuarios WHERE username=?",
        (username,)
    ).fetchone()
    if not prof:
        print(f"No existe ningún usuario con username={username!r}")
        sys.exit(1)

    prof = dict(prof)
    print("=" * 70)
    print("1. PERFIL CRUDO DEL PROFESOR (tabla usuarios)")
    print("=" * 70)
    for k, v in prof.items():
        print(f"  {k:<15} = {v!r}")

    alcance = _resolver_alcance_profesor(prof)
    print("\n" + "=" * 70)
    print("2. _resolver_alcance_profesor() — lo mismo que calcula /profesor")
    print("=" * 70)
    print(f"  grados          = {alcance['grados']}")
    print(f"  menciones       = {alcance['menciones']}")
    print(f"  filtro_mencion  = {alcance['filtro_mencion']}")

    grados_prof    = alcance["grados"]
    menciones_prof = alcance["menciones"]
    filtro_men     = alcance["filtro_mencion"]

    q = ("SELECT id, nombre, apellido, curso, grado, seccion FROM estudiantes "
         "WHERE (condicion IS NULL OR condicion NOT IN ('RETIRADO','TRANSFERIDO'))")
    params = []
    if grados_prof:
        q += " AND (" + " OR ".join(["grado LIKE ?" for _ in grados_prof]) + ")"
        params.extend([f"%{g}%" for g in grados_prof])
    if filtro_men and menciones_prof:
        q += " AND (" + " OR ".join(["curso LIKE ?" for _ in menciones_prof]) + ")"
        params.extend([f"%{m}%" for m in menciones_prof])
    q += " ORDER BY grado, apellido, nombre"

    rows = conn.execute(q, params).fetchall()
    print("\n" + "=" * 70)
    print("3. QUERY EXACTA de portal_profesor() para el roster")
    print("=" * 70)
    print(f"  SQL: {q}")
    print(f"  params: {params}")
    print(f"  → {len(rows)} fila(s)")
    for r in rows[:60]:
        print(f"    id={r['id']:<5} {r['apellido']}, {r['nombre']:<28} "
              f"grado={r['grado']!r:<15} curso={r['curso']!r:<25} seccion={r['seccion']!r}")

    print("\n" + "=" * 70)
    print("4. VALORES DISTINCT de estudiantes.grado (toda la BD)")
    print("=" * 70)
    for r in conn.execute(
        "SELECT grado, COUNT(*) AS n FROM estudiantes GROUP BY grado ORDER BY n DESC"
    ).fetchall():
        print(f"  {r['grado']!r:<40} {r['n']:>4}")

    print("\n" + "=" * 70)
    print("5. VALORES DISTINCT de estudiantes.curso que contienen 'MULTIMEDIA'")
    print("=" * 70)
    for r in conn.execute(
        "SELECT curso, COUNT(*) AS n FROM estudiantes WHERE curso LIKE '%MULTIMEDIA%' "
        "GROUP BY curso ORDER BY n DESC"
    ).fetchall():
        print(f"  {r['curso']!r:<60} {r['n']:>4}")

    print("\n" + "=" * 70)
    print("6. Total estudiantes en la tabla (todos los grados)")
    print("=" * 70)
    total = conn.execute("SELECT COUNT(*) FROM estudiantes").fetchone()[0]
    print(f"  {total} estudiante(s) en total")

    conn.close()


if __name__ == "__main__":
    main()
