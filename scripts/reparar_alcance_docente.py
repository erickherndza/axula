#!/usr/bin/env python3
"""
scripts/reparar_alcance_docente.py
Repara datos corruptos en usuarios.grado y usuarios.mencion.

Problemas que corrige:
  R-1: grado='todos'  → '' (vacío = sin restricción de grado)
  R-2: mencion con slug de guión bajo o sin acento →
       'artes_visuales' → 'artes_visuales' (se mantiene; el backend normaliza al buscar)
       'musica'         → 'musica'          (idem)
       PERO si están en formato incorrecto como 'MULTIMEDIA,ARTES_VISUALES' → 'multimedia,artes_visuales'

Uso:
  python3 scripts/reparar_alcance_docente.py          # dry-run (solo muestra)
  python3 scripts/reparar_alcance_docente.py --apply  # escribe en la BD
"""
import sqlite3
import os
import sys

# Ruta de la BD (misma lógica que constants.py)
_en_render = os.path.exists("/opt/render")
DATABASE = os.environ.get("DATABASE_PATH", "/data/database.db" if _en_render else "database.db")

apply = "--apply" in sys.argv

print(f"BD: {DATABASE}")
print(f"Modo: {'ESCRIBIR' if apply else 'DRY-RUN (sin cambios)'}\n")

with sqlite3.connect(DATABASE, timeout=15) as conn:
    conn.row_factory = sqlite3.Row
    profesores = conn.execute(
        "SELECT id, nombre, grado, mencion FROM usuarios WHERE rol='profesor'"
    ).fetchall()

cambios = []

for p in profesores:
    uid   = p["id"]
    nombre = p["nombre"]
    grado  = (p["grado"] or "").strip()
    mencion = (p["mencion"] or "").strip()

    nuevo_grado  = grado
    nuevo_mencion = mencion

    # R-1: sentinel 'todos' → vacío
    if grado.lower() == "todos":
        nuevo_grado = ""

    # R-2: normalizar menciones a slugs minúscula sin emoji
    # (el backend ya normaliza al canónico al consultar, pero limpiemos igual)
    if mencion:
        parts = [m.strip().lower() for m in mencion.split(",") if m.strip()]
        # Quitar emojis/caracteres no-alfa
        def _clean(s):
            return "".join(c for c in s if c.isalpha() or c in "_, ").strip()
        parts = [_clean(m) for m in parts if _clean(m)]
        nuevo_mencion = ",".join(parts)

    if nuevo_grado != grado or nuevo_mencion != mencion:
        cambios.append({
            "id": uid, "nombre": nombre,
            "grado_antes": grado,   "grado_despues": nuevo_grado,
            "mencion_antes": mencion, "mencion_despues": nuevo_mencion,
        })

if not cambios:
    print("No se encontraron filas que necesiten reparación.")
else:
    print(f"Filas a reparar: {len(cambios)}\n")
    for c in cambios:
        print(f"  [{c['id']}] {c['nombre']}")
        if c["grado_antes"] != c["grado_despues"]:
            print(f"    grado:   {c['grado_antes']!r}  →  {c['grado_despues']!r}")
        if c["mencion_antes"] != c["mencion_despues"]:
            print(f"    mencion: {c['mencion_antes']!r}  →  {c['mencion_despues']!r}")

    if apply:
        print("\nAplicando cambios...")
        for c in cambios:
            conn.execute(
                "UPDATE usuarios SET grado=?, mencion=? WHERE id=?",
                (c["grado_despues"], c["mencion_despues"], c["id"])
            )
        conn.commit()
        print(f"✓ {len(cambios)} filas actualizadas.")
    else:
        print("\nEjecuta con --apply para escribir los cambios.")
