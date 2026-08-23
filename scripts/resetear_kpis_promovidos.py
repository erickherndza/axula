#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
resetear_kpis_promovidos.py
============================
Limpia los KPIs "cacheados" en la tabla estudiantes (p_acad, acad_p1-p4,
asistencia_p1-p4, fotografia_p1-p4, lv_p1-p4, diseno_p1-p4, p_foto, p_lv,
p_diseno, prom_modulos) cuando esos valores YA NO corresponden al grado
actual del estudiante para el año escolar activo.

Por qué hace falta: cuando se promueve a un estudiante (ej. 4TO→5TO),
ejecutar_promocion_estudiante() resetea p_acad/acad_p*/asistencia_p* a NULL,
pero SOLO si la promoción se ejecutó por ese camino (routes/promocion.py).
Si el grado se editó a mano (/mi-perfil, /usuarios) o si algo volvió a
llamar recalcular_kpis_estudiante() ANTES del fix que filtra por grado
(commit 1c4aa8d), esos campos quedaron con las notas del grado anterior.
Esto también limpia los campos de módulos técnicos, que
ejecutar_promocion_estudiante() nunca tocaba.

Un estudiante se considera "candidato a reset" si:
  - está ACTIVO
  - tiene algún KPI/módulo con valor > 0 en la tabla estudiantes
  - obtener_notas_estudiante(conn, est_id, anio_actual, grado=su_grado_actual)
    no devuelve NADA — es decir, no hay ninguna fila de calificaciones_periodo
    ni materias_calificaciones para su grado actual en el año activo, por lo
    tanto el valor guardado solo puede venir de un grado/año anterior.

Uso:
    python3 scripts/resetear_kpis_promovidos.py            # dry-run
    python3 scripts/resetear_kpis_promovidos.py --commit   # aplica cambios
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

from core.helpers import obtener_notas_estudiante, _anio_escolar_actual  # noqa: E402

CAMPOS_RESET = [
    "p_acad", "acad_p1", "acad_p2", "acad_p3", "acad_p4",
    "asistencia_p1", "asistencia_p2", "asistencia_p3", "asistencia_p4",
    "fotografia_p1", "fotografia_p2", "fotografia_p3", "fotografia_p4",
    "lv_p1", "lv_p2", "lv_p3", "lv_p4",
    "diseno_p1", "diseno_p2", "diseno_p3", "diseno_p4",
    "p_foto", "p_lv", "p_diseno", "prom_modulos",
]


def main():
    commit = "--commit" in sys.argv
    print(f"Modo: {'APLICAR CAMBIOS' if commit else 'DRY-RUN (sin cambios)'}")
    print(f"BD: {DB_PATH}\n")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    anio = _anio_escolar_actual()
    print(f"Año escolar activo (config o cálculo por fecha): {anio}\n")

    cols_sql = ", ".join(CAMPOS_RESET)
    filtro_sql = " OR ".join(f"{c} IS NOT NULL AND {c} != 0" for c in CAMPOS_RESET)

    candidatos = conn.execute(f"""
        SELECT id, nombre, apellido, grado, curso, mencion, {cols_sql}
        FROM estudiantes
        WHERE (condicion IS NULL OR condicion = 'ACTIVO')
          AND ({filtro_sql})
        ORDER BY grado, apellido, nombre
    """).fetchall()

    print(f"Estudiantes ACTIVOS con algún KPI/módulo != 0: {len(candidatos)}\n")

    a_resetear = []
    conservados = 0

    for est in candidatos:
        grado_actual = (est["grado"] or "").strip().upper()
        if not grado_actual:
            continue
        notas = obtener_notas_estudiante(conn, est["id"], anio, grado=grado_actual)
        if notas:
            conservados += 1
            continue  # sí hay notas reales del grado/año actual — no tocar
        a_resetear.append(est)

    print(f"Con notas válidas del grado/año actual (se conservan): {conservados}")
    print(f"SIN notas del grado/año actual → KPIs son de un grado anterior: {len(a_resetear)}\n")

    for est in a_resetear:
        nombre = f"{est['nombre']} {est['apellido']}"
        grado  = f"{est['grado']} {est['mencion'] or ''}".strip()
        valores_previos = {c: est[c] for c in CAMPOS_RESET if est[c]}
        print(f"  RESET [{est['id']}] {nombre} ({grado}) — limpia: {list(valores_previos.keys())}")

        if commit:
            sets = ", ".join(f"{c} = NULL" for c in CAMPOS_RESET)
            conn.execute(
                f"UPDATE estudiantes SET {sets}, tiene_notas = 0 WHERE id = ?",
                (est["id"],),
            )

    if commit:
        conn.commit()
        print(f"\n✓ {len(a_resetear)} estudiantes actualizados.")
    else:
        print(f"\nDry-run: {len(a_resetear)} estudiantes se actualizarían con --commit.")

    conn.close()


if __name__ == "__main__":
    main()
