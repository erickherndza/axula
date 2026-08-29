#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cargar_listado_estudiantes.py
==============================
CLI para cargar (o actualizar) el roster de `estudiantes` a partir de
CUALQUIER "Listado de Estudiantes" oficial — desde un archivo de un solo
grado/mención hasta el LISTADO institucional completo del año (una hoja
por grado, varios bloques "DATOS DEL ALUMNO" por hoja, uno por mención o
sección). La lógica de lectura/matching vive en core/importar_listado.py —
este script solo la invoca y muestra el reporte.

También disponible desde el navegador en /profesor → "Cargar Excel" →
"Listado de Estudiantes" (mismo resultado, con preview antes de confirmar).

Uso:
    # Dry-run (no escribe en BD) — SIEMPRE correr esto primero
    python3 scripts/cargar_listado_estudiantes.py "LISTADO AÑO 2026-2027.xlsx"

    # Carga real
    python3 scripts/cargar_listado_estudiantes.py "LISTADO AÑO 2026-2027.xlsx" --commit
"""
import os
import sys
import sqlite3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.importar_listado import leer_listado, construir_plan_multi, aplicar_carga_multi  # noqa: E402

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

    bloques = leer_listado(path)
    total_alumnos = sum(len(b["alumnos"]) for b in bloques)

    print(f"Archivo: {path}")
    print(f"Bloques detectados (grado/sección/mención): {len(bloques)}")
    print(f"Alumnos en el archivo: {total_alumnos}")
    print(f"Modo: {'COMMIT (escribe en BD)' if COMMIT else 'DRY-RUN (solo muestra qué haría)'}")
    print(f"BD: {DB_PATH}\n")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    resumen = construir_plan_multi(conn, bloques)
    for r in resumen:
        etiqueta_bloque = f"{r['grado']}" + (f" Sec.{r['seccion']}" if r['seccion'] else "") + (f" {r['mencion']}" if r['mencion'] else "")
        print(f"=== {etiqueta_bloque} — {len(r['plan'])} alumno(s): {r['nuevos']} nuevo(s), {r['actualizados']} actualizado(s) ===")
        if not COMMIT:
            for p in r["plan"]:
                etiqueta = "[NUEVO]    " if p["accion"] == "nuevo" else "[ACTUALIZA]"
                detalle = ", ".join(p["cambios"]) if p["cambios"] else "sin cambios"
                print(f"  {etiqueta} #{p['no']:>2} {p['nombre']} {p['apellido']}  ({detalle})")
                if p["advertencia"]:
                    print(f"              ⚠ {p['advertencia']}")

    nuevos_total = sum(r["nuevos"] for r in resumen)
    actualizados_total = sum(r["actualizados"] for r in resumen)

    if COMMIT:
        nuevos_total, actualizados_total = aplicar_carga_multi(conn, bloques)
        print(f"\n✓ Guardado: {nuevos_total} nuevo(s), {actualizados_total} actualizado(s) en {len(bloques)} bloque(s).")
    else:
        print(f"\n(dry-run) Se crearían {nuevos_total} nuevo(s), se actualizarían {actualizados_total} en total.")
        print("Corre de nuevo con --commit para aplicar los cambios.")

    conn.close()


if __name__ == "__main__":
    main()
