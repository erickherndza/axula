#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
recalcular_kpis_notas0.py
=========================
Corrige estudiantes que tienen filas en materias_calificaciones pero tienen
tiene_notas=0 / p_acad=0 en la tabla estudiantes.

Usa recalcular_kpis_estudiante() — la función canónica del motor (misma
lógica que la app), leyendo calificaciones_periodo + materias_calificaciones.

Uso:
    python3 scripts/recalcular_kpis_notas0.py            # dry-run
    python3 scripts/recalcular_kpis_notas0.py --commit   # aplica cambios
"""
import os
import sqlite3
import sys

# ── Ruta a la BD ──────────────────────────────────────────────────────────────
_en_render = os.path.exists("/data")
DB_PATH = os.environ.get(
    "DATABASE_PATH",
    "/data/database.db"
    if _en_render
    else os.path.join(os.path.dirname(__file__), "..", "database.db"),
)

# Añadir raíz del proyecto al path para importar core.*
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("DATABASE_PATH", DB_PATH)  # constants.py lo lee

from core.helpers import obtener_notas_estudiante  # noqa: E402


def _recalcular(conn, est_id: int, anio: str) -> dict | None:
    """
    Calcula KPIs desde obtener_notas_estudiante() y retorna el dict de
    valores a actualizar, o None si no hay datos.
    """
    notas = obtener_notas_estudiante(conn, est_id, anio)
    if not notas:
        return None

    per_sums = {1: [], 2: [], 3: [], 4: []}
    for mat_data in notas.values():
        for i in range(1, 5):
            v = mat_data.get(f"p{i}", 0.0)
            if v and v > 0:
                per_sums[i].append(v)

    acad_p = {}
    for i in range(1, 5):
        acad_p[i] = (
            round(sum(per_sums[i]) / len(per_sums[i]), 2) if per_sums[i] else 0.0
        )

    promedios = [d["promedio"] for d in notas.values() if d["promedio"] and d["promedio"] > 0]
    p_acad = round(sum(promedios) / len(promedios), 2) if promedios else 0.0

    if p_acad <= 0:
        return None

    return {
        "p_acad":  p_acad,
        "acad_p1": acad_p[1],
        "acad_p2": acad_p[2],
        "acad_p3": acad_p[3],
        "acad_p4": acad_p[4],
    }


def main():
    commit = "--commit" in sys.argv
    print(f"Modo: {'APLICAR CAMBIOS' if commit else 'DRY-RUN (sin cambios)'}")
    print(f"BD: {DB_PATH}\n")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Año escolar actual (mismo cálculo que _anio_escolar_actual)
    import datetime
    hoy = datetime.date.today()
    if hoy.month >= 8:
        anio = f"{hoy.year}-{hoy.year + 1}"
    else:
        anio = f"{hoy.year - 1}-{hoy.year}"

    print(f"Año escolar: {anio}\n")

    # Estudiantes que tienen MC rows pero p_acad=0 o tiene_notas=0
    candidatos = conn.execute(
        """
        SELECT DISTINCT mc.estudiante_id
        FROM   materias_calificaciones mc
        JOIN   estudiantes e ON e.id = mc.estudiante_id
        WHERE  mc.anio_escolar = ?
          AND  (e.p_acad IS NULL OR e.p_acad = 0 OR e.tiene_notas = 0 OR e.tiene_notas IS NULL)
        ORDER  BY mc.estudiante_id
        """,
        (anio,),
    ).fetchall()

    ids = [r[0] for r in candidatos]
    print(f"Candidatos con MC rows pero p_acad=0/tiene_notas=0: {len(ids)}\n")

    actualizados = 0
    sin_datos    = 0

    for est_id in ids:
        est = conn.execute(
            "SELECT nombre, apellido, grado, mencion FROM estudiantes WHERE id=?",
            (est_id,),
        ).fetchone()
        nombre = f"{est['nombre']} {est['apellido']}" if est else f"ID {est_id}"
        grado  = f"{est['grado']} {est['mencion'] or ''}".strip() if est else "?"

        kpis = _recalcular(conn, est_id, anio)
        if not kpis:
            sin_datos += 1
            print(f"  SKIP [{est_id}] {nombre} ({grado}) — sin notas válidas en CP+MC")
            continue

        print(
            f"  FIX  [{est_id}] {nombre} ({grado}) "
            f"→ p_acad={kpis['p_acad']} "
            f"P1={kpis['acad_p1']} P2={kpis['acad_p2']} "
            f"P3={kpis['acad_p3']} P4={kpis['acad_p4']}"
        )

        if commit:
            conn.execute(
                """
                UPDATE estudiantes
                SET  p_acad    = ?,
                     acad_p1   = ?,
                     acad_p2   = ?,
                     acad_p3   = ?,
                     acad_p4   = ?,
                     tiene_notas = 1
                WHERE id = ?
                """,
                (
                    kpis["p_acad"],
                    kpis["acad_p1"],
                    kpis["acad_p2"],
                    kpis["acad_p3"],
                    kpis["acad_p4"],
                    est_id,
                ),
            )
        actualizados += 1

    if commit:
        conn.commit()
        print(f"\nActualizados: {actualizados}  Sin datos: {sin_datos}")
        print("Commit OK. Reinicia la app en Render para limpiar caché.")
    else:
        print(f"\nPrevisualización: {actualizados} se actualizarían, {sin_datos} sin datos")
        print("Ejecuta con --commit para aplicar.")

    conn.close()


if __name__ == "__main__":
    main()
