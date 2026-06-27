#!/usr/bin/env python3
"""
Ejecuta una migración SQL numerada sobre database.db
Uso: python3 scripts/run_migration.py 004
"""
import sys
import sqlite3
import os
import re


def run_migration(num: str):
    base = os.path.dirname(os.path.abspath(__file__))
    db_path  = os.path.join(base, '..', 'database.db')
    sql_path = os.path.join(base, '..', 'migrations', f'{num}_evaluacion_mejorada.sql')

    if not os.path.exists(sql_path):
        print(f"ERROR: No se encontró {sql_path}")
        sys.exit(1)

    with open(sql_path, 'r', encoding='utf-8') as f:
        sql = f.read()

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        # Strip comments and split by ';'
        # Preserve BEGIN/COMMIT as individual statements
        statements = []
        for stmt in sql.split(';'):
            cleaned = re.sub(r'--[^\n]*', '', stmt).strip()
            if cleaned:
                statements.append(cleaned)

        for stmt in statements:
            preview = ' '.join(stmt.split())[:80]
            try:
                conn.execute(stmt)
                conn.commit()
                print(f"  OK: {preview}...")
            except sqlite3.OperationalError as e:
                msg = str(e).lower()
                if 'duplicate column name' in msg:
                    print(f"  SKIP (columna ya existe): {preview}...")
                elif 'already exists' in msg and 'table' in msg:
                    print(f"  SKIP (tabla ya existe): {preview}...")
                elif 'no such table' in msg and 'rename' in msg.lower():
                    print(f"  SKIP (tabla origen no existe): {preview}...")
                elif 'cannot commit' in msg or 'no transaction is active' in msg:
                    print(f"  SKIP (control): {preview}...")
                else:
                    print(f"\n  ERROR: {e}")
                    print(f"  Statement: {stmt[:200]}")
                    raise

        print(f"\n✓ Migración {num} completada exitosamente.")

        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        print(f"\nTablas en DB ({len(tables)}):")
        for t in tables:
            print(f"  - {t['name']}")

    finally:
        conn.close()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python3 scripts/run_migration.py <numero>")
        sys.exit(1)
    run_migration(sys.argv[1])
