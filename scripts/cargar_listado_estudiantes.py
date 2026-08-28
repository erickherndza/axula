#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cargar_listado_estudiantes.py
==============================
CLI para cargar (o actualizar) el roster de `estudiantes` a partir de
CUALQUIER "Listado de Estudiantes" oficial (una hoja, encabezado
"GRADO:"/"ÁREA:" + tabla de alumnos). La lógica de lectura/matching vive en
core/importar_listado.py — este script solo la invoca y muestra el reporte.

También disponible desde el navegador en /profesor → "Cargar Excel" →
"Listado de Estudiantes" (mismo resultado, con preview antes de confirmar).

Uso:
    # Dry-run (no escribe en BD) — SIEMPRE correr esto primero
    python3 scripts/cargar_listado_estudiantes.py "Listado_Estudiantes_4TO_B_Musica.xlsx"

    # Carga real
    python3 scripts/cargar_listado_estudiantes.py "Listado_Estudiantes_4TO_B_Musica.xlsx" --commit
"""
import os
import sys
import sqlite3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.importar_listado import leer_listado, construir_plan, aplicar_carga  # noqa: E402

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
        print("Uso: python3 scripts/cargar_listado_estudiantes.py <archivo.xlsx> [--commit]")
        sys.exit(1)
    path = ARGS[0]
    if not os.path.exists(path):
        print(f"No existe el archivo: {path}")
        sys.exit(1)

    grado, seccion, mencion, alumnos = leer_listado(path)

    print(f"Archivo: {path}")
    print(f"Grado detectado: {grado!r} · Sección: {seccion!r} · Mención: {mencion!r}")
    print(f"Alumnos en el archivo: {len(alumnos)}")
    print(f"Modo: {'COMMIT (escribe en BD)' if COMMIT else 'DRY-RUN (solo muestra qué haría)'}")
    print(f"BD: {DB_PATH}\n")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    if COMMIT:
        nuevos, actualizados = aplicar_carga(conn, grado, seccion, mencion, alumnos)
    else:
        _curso, _ciclo, plan = construir_plan(conn, grado, seccion, mencion, alumnos)
        nuevos = sum(1 for p in plan if p["accion"] == "nuevo")
        actualizados = sum(1 for p in plan if p["accion"] == "actualiza")
        for p in plan:
            etiqueta = "[NUEVO]    " if p["accion"] == "nuevo" else "[ACTUALIZA]"
            detalle = ", ".join(p["cambios"]) if p["cambios"] else "sin cambios"
            print(f"  {etiqueta} #{p['no']:>2} {p['nombre']} {p['apellido']}  ({detalle})")
            if p["advertencia"]:
                print(f"              ⚠ {p['advertencia']}")

    if COMMIT:
        print(f"\n✓ Guardado: {nuevos} nuevo(s), {actualizados} actualizado(s).")
    else:
        print(f"\n(dry-run) Se crearían {nuevos} nuevo(s), se actualizarían {actualizados}.")
        print("Corre de nuevo con --commit para aplicar los cambios.")

    conn.close()


if __name__ == "__main__":
    main()
