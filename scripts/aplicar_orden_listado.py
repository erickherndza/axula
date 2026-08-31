#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
aplicar_orden_listado.py
=========================
Fija estudiantes.orden_lista = posición del alumno dentro de su bloque
(grado + mención/sección) del "Listado de Estudiantes" oficial del
coordinador — el mismo orden en que Pase de Lista muestra el roster
(routes/profesor.py::portal_profesor, ORDER BY ... orden_lista) debe
coincidir con el orden real en que el profesor pasa lista en clase, en
vez de un orden alfabético que solo coincide con el del Excel por
casualidad.

Reutiliza el mismo parser/matching que scripts/cargar_listado_estudiantes.py
(core/importar_listado.py) — NO crea ni actualiza datos del estudiante,
solo el campo orden_lista de quien ya matchea en la BD. Un alumno del
archivo que no matchea ningún estudiante existente se reporta pero no
se toca nada (correr primero cargar_listado_estudiantes.py si el roster
todavía no está cargado).

Uso:
    # Dry-run (no escribe en BD) — SIEMPRE correr esto primero
    python3 scripts/aplicar_orden_listado.py "LISTADO AÑO 2026-2027.xlsx"

    # Aplicar de verdad
    python3 scripts/aplicar_orden_listado.py "LISTADO AÑO 2026-2027.xlsx" --commit
"""
import os
import sys
import sqlite3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.importar_listado import leer_listado, buscar_existente  # noqa: E402

_en_render = os.path.exists("/data")
DB_PATH = os.environ.get(
    "DATABASE_PATH",
    "/data/database.db" if _en_render
    else os.path.join(os.path.dirname(__file__), "..", "database.db"),
)

COMMIT = "--commit" in sys.argv
ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]


def main():
    if not ARGS:
        print("Uso: python3 scripts/aplicar_orden_listado.py <archivo.xlsx> [--commit]")
        sys.exit(1)
    path = ARGS[0]
    if not os.path.exists(path):
        print(f"No existe el archivo: {path}")
        sys.exit(1)

    bloques = leer_listado(path)

    print(f"Archivo: {path}")
    print(f"Bloques detectados: {len(bloques)}")
    print(f"Modo: {'COMMIT (escribe en BD)' if COMMIT else 'DRY-RUN (solo muestra qué haría)'}")
    print(f"BD: {DB_PATH}\n")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    total_ok = total_sin_match = total_omitidos = 0

    for b in bloques:
        etiqueta = f"{b['grado']}" + (f" Sec.{b['seccion']}" if b['seccion'] else "") + (f" {b['mencion']}" if b['mencion'] else "")
        if b.get("sin_mencion_detectada"):
            print(f"=== ⚠ {etiqueta} — sin mención en el archivo, omitido ({len(b['alumnos'])} alumno(s)) ===")
            total_omitidos += len(b["alumnos"])
            continue

        sin_match = []
        cambios = 0
        for i, alumno in enumerate(b["alumnos"], start=1):
            row = buscar_existente(conn, alumno, b["grado"], b["mencion"])
            if not row:
                sin_match.append(f"#{i:>2} {alumno['nombre']} {alumno['apellido']}")
                continue
            if COMMIT:
                conn.execute("UPDATE estudiantes SET orden_lista=? WHERE id=?", (i, row["id"]))
            cambios += 1

        print(f"=== {etiqueta} — {len(b['alumnos'])} alumno(s): {cambios} con orden fijado, {len(sin_match)} sin match ===")
        for s in sin_match:
            print(f"  ⚠ sin match: {s}")
        total_ok += cambios
        total_sin_match += len(sin_match)

    if COMMIT:
        conn.commit()
        print(f"\n✓ orden_lista fijado en {total_ok} estudiante(s).")
    else:
        print(f"\n(dry-run) Se fijaría orden_lista en {total_ok} estudiante(s).")
        print("Corre de nuevo con --commit para aplicar los cambios.")
    if total_sin_match:
        print(f"⚠ {total_sin_match} alumno(s) del archivo no matchearon ningún estudiante existente "
              f"— probablemente falta cargar el roster primero con cargar_listado_estudiantes.py.")
    if total_omitidos:
        print(f"⚠ {total_omitidos} alumno(s) omitidos por bloques sin mención detectada en el archivo.")

    conn.close()


if __name__ == "__main__":
    main()
