#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dropear_coherencia_fila_v1.py
==============================
Elimina la tabla vestigial `coherencia_horizontal_fila` — estructura de la
v1 de Coherencia Horizontal (commit 2e8d684, 2026-08-24), reemplazada al
día siguiente por coherencia_periodo + coherencia_rae cuando el coordinador
entregó la plantilla oficial real (commit 962b52b).

La tabla ya NO está en TABLAS_NUEVAS (no se recrea al reiniciar Flask) y
ningún código la referencia. Este script solo limpia la BD de producción,
que sí la creó el día que estuvo desplegada la v1.

DESTRUCTIVO: hace DROP TABLE. Por eso el dry-run imprime primero cuántas
filas se perderían y su contenido, para revisar antes de confirmar.

Uso:
    python3 scripts/dropear_coherencia_fila_v1.py            # dry-run
    python3 scripts/dropear_coherencia_fila_v1.py --commit   # dropea
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

TABLA = "coherencia_horizontal_fila"


def main():
    commit = "--commit" in sys.argv
    print(f"Modo: {'APLICAR DROP' if commit else 'DRY-RUN (sin cambios)'}")
    print(f"BD: {DB_PATH}\n")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    existe = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (TABLA,)
    ).fetchone()

    if not existe:
        print(f"La tabla '{TABLA}' no existe en esta BD — nada que hacer.")
        conn.close()
        return

    n = conn.execute(f"SELECT COUNT(*) FROM {TABLA}").fetchone()[0]
    print(f"Tabla '{TABLA}' encontrada — {n} fila(s).\n")

    if n:
        print("Contenido que se perderá al dropear:")
        for r in conn.execute(f"SELECT * FROM {TABLA} ORDER BY id").fetchall():
            print(f"  {dict(r)}")
        print()

    if commit:
        conn.execute(f"DROP TABLE {TABLA}")
        conn.commit()
        print(f"✓ Tabla '{TABLA}' eliminada.")
    else:
        print(f"Dry-run: la tabla '{TABLA}' ({n} fila(s)) se eliminaría con --commit.")

    conn.close()


if __name__ == "__main__":
    main()
