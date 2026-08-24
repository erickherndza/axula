#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fijar_anio_escolar.py
======================
Corrige configuracion_centro.anio_escolar_activo. No hay ninguna pantalla en
la app para editar este valor (el módulo que lo hacía se eliminó en la
sesión 14 junto con /config), así que quedó fijo en un valor incorrecto
("2027-2028", un año adelantado del real) desde antes. Este script existe
solo para evitar tener que pegar comandos Python largos en la shell de
Render, que corta las líneas.

Uso:
    python3 scripts/fijar_anio_escolar.py 2026-2027
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
    if len(sys.argv) != 2 or "-" not in sys.argv[1]:
        print("Uso: python3 scripts/fijar_anio_escolar.py 2026-2027")
        sys.exit(1)

    nuevo_anio = sys.argv[1].strip()
    conn = sqlite3.connect(DB_PATH)
    actual = conn.execute(
        "SELECT anio_escolar_activo FROM configuracion_centro WHERE id=1"
    ).fetchone()
    print(f"BD: {DB_PATH}")
    print(f"Año escolar activo ANTES: {actual[0] if actual else '(sin fila id=1)'}")

    conn.execute(
        "UPDATE configuracion_centro SET anio_escolar_activo=? WHERE id=1",
        (nuevo_anio,),
    )
    conn.commit()

    nuevo = conn.execute(
        "SELECT anio_escolar_activo FROM configuracion_centro WHERE id=1"
    ).fetchone()
    print(f"Año escolar activo AHORA:  {nuevo[0] if nuevo else '(sin fila id=1)'}")
    conn.close()


if __name__ == "__main__":
    main()
