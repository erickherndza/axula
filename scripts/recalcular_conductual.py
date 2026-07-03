#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Motor Conductual Fase 1 — recálculo masivo de score_conductual y semaforo.

Uso:
    python3 scripts/recalcular_conductual.py            # dry-run (muestra resumen)
    python3 scripts/recalcular_conductual.py --commit   # escribe en BD

Fórmula: 40% notas + 35% asistencia + 25% balance_tags
Si asistencia=0: redistribuye a 62% notas + 38% tags
Semáforo: VERDE >70 · AMARILLO 50-70 · ROJO <50
"""

import os
import sys
import sqlite3

_en_render = os.path.exists("/data")
DB_PATH = "/data/database.db" if _en_render else os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database.db"
)

DRY_RUN = "--commit" not in sys.argv


def calcular_motor_conductual(conn, est_id):
    row = conn.execute(
        "SELECT p_acad, asistencia FROM estudiantes WHERE id=?", (est_id,)
    ).fetchone()
    p_acad    = float(row[0] or 0) if row else 0.0
    asist_est = float(row[1] or 0) if row else 0.0

    rows_am = conn.execute(
        "SELECT porcentaje FROM asistencia_mensual"
        " WHERE estudiante_id=? AND porcentaje IS NOT NULL AND porcentaje > 0",
        (est_id,)
    ).fetchall()
    if rows_am:
        pcts = [float(r[0]) for r in rows_am]
        asist_est = sum(pcts) / len(pcts)

    tiene_asistencia = asist_est > 0

    ca = conn.execute(
        "SELECT polaridad FROM cuaderno_anecdotico"
        " WHERE estudiante_id=? AND polaridad IN ('positivo','negativo')",
        (est_id,)
    ).fetchall()
    n_pos = sum(1 for r in ca if r[0] == "positivo")
    n_neg = sum(1 for r in ca if r[0] == "negativo")
    total_ca = n_pos + n_neg
    tiene_cuaderno = total_ca > 0
    tags_score = 70.0 if total_ca == 0 else (n_pos / total_ca) * 100.0

    # Sin datos académicos → N/D
    if p_acad == 0 and not tiene_asistencia and not tiene_cuaderno:
        return None, "ND"

    if tiene_asistencia:
        score = 0.40 * p_acad + 0.35 * asist_est + 0.25 * tags_score
    else:
        score = (40 / 65) * p_acad + (25 / 65) * tags_score

    score = round(max(0.0, min(100.0, score)), 1)

    if score > 70:
        semaforo = "VERDE"
    elif score >= 50:
        semaforo = "AMARILLO"
    else:
        semaforo = "ROJO"

    return score, semaforo


def main():
    print(f"DB: {DB_PATH}")
    print(f"Modo: {'DRY-RUN' if DRY_RUN else 'COMMIT'}")
    print()

    conn = sqlite3.connect(DB_PATH, timeout=15)
    estudiantes = conn.execute(
        "SELECT id, nombre, apellido, grado FROM estudiantes ORDER BY grado, apellido"
    ).fetchall()

    print(f"Total estudiantes: {len(estudiantes)}")
    conteo = {"VERDE": 0, "AMARILLO": 0, "ROJO": 0, "ND": 0}
    actualizados = 0

    for est_id, nombre, apellido, grado in estudiantes:
        score, semaforo = calcular_motor_conductual(conn, est_id)
        conteo[semaforo] += 1
        actualizados += 1

        if not DRY_RUN:
            conn.execute(
                "UPDATE estudiantes SET score_conductual=?, semaforo=? WHERE id=?",
                (score, semaforo, est_id)
            )

    if not DRY_RUN:
        conn.commit()
        print(f"✓ {actualizados} estudiantes actualizados en BD")
    else:
        print(f"(dry-run) {actualizados} estudiantes calculados")

    print()
    print("=== Distribución semáforo ===")
    total = len(estudiantes) or 1
    for nivel, cnt in conteo.items():
        bar = "█" * (cnt * 30 // total)
        print(f"  {nivel:8s}: {cnt:4d}  {bar}")

    # Muestra los ROJO para revisión
    if conteo["ROJO"] > 0:
        print()
        print("=== Estudiantes ROJO (score < 50) ===")
        for est_id, nombre, apellido, grado in estudiantes:
            score, semaforo = calcular_motor_conductual(conn, est_id)
            if semaforo == "ROJO":
                print(f"  [{grado}] {nombre} {apellido}  →  {score}")

    conn.close()


if __name__ == "__main__":
    main()
