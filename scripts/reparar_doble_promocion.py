#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reparar_doble_promocion.py
==========================
Detecta y repara el efecto dominó del cierre de año escolar:
  4TO → promueve a 5TO → loop de 5TO los ve → promueve a 6TO (incorrecto)
  5TO → promueve a 6TO → 6TO los ve → candidato (incorrecto)

Estrategia de detección:
  Un alumno fue doblemente promovido si en materias_calificaciones tiene filas
  del año escolar actual (ej: 2025-2026) con un GRADO inferior al que tiene ahora
  en la tabla estudiantes.

  Ejemplo: alumno con grado='6TO' pero tiene MC con grado_origen='4TO' en el
  anio_escolar — fue promovido dos veces en el mismo cierre.

Dado que MC no tiene columna 'grado', usamos la tabla 'promociones':
  Si un alumno tiene una fila en promociones con grado_origen=X para el año,
  y su grado actual en estudiantes es 2 pasos por encima de X, fue doblemente
  promovido. Revertimos al grado_destino correcto (X+1).

Uso:
    python3 scripts/reparar_doble_promocion.py                # diagnóstico
    python3 scripts/reparar_doble_promocion.py --commit       # aplica correcciones
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

# Mapa de siguiente grado (igual que en promocion_engine.py)
SIGUIENTE = {
    "1ERO": "2DO",
    "2DO":  "3RO",
    "3RO":  "4TO",
    "3ERO": "4TO",
    "4TO":  "5TO",
    "5TO":  "6TO",
    "6TO":  "CANDIDATO_PRUEBAS",
}
ANTERIOR = {v: k for k, v in SIGUIENTE.items() if v != "CANDIDATO_PRUEBAS"}
# Para candidatos: el grado correcto sería 6TO (siguen siendo 6TO hasta titularse)


def main():
    commit = "--commit" in sys.argv
    print(f"Modo: {'APLICAR CORRECCIONES' if commit else 'DIAGNÓSTICO (sin cambios)'}")
    print(f"BD: {DB_PATH}\n")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    anio = input("Año escolar cerrado (ej: 2025-2026): ").strip()
    if not anio:
        print("Año requerido.")
        conn.close()
        return

    # ── Detectar dobles-promociones ──────────────────────────────────────────
    # Un alumno con entrada en 'promociones' donde:
    #   grado_origen  = G
    #   grado_destino = SIGUIENTE[G]  (lo que debería ser)
    # Pero su grado actual en estudiantes = SIGUIENTE[SIGUIENTE[G]]  (fue un paso más)
    candidatos = conn.execute(
        """
        SELECT e.id, e.nombre, e.apellido, e.grado AS grado_actual, e.curso,
               p.grado_origen, p.grado_destino AS grado_destino_registrado,
               e.condicion
        FROM   promociones p
        JOIN   estudiantes e ON e.id = p.estudiante_id
        WHERE  p.anio_escolar = ?
        ORDER  BY p.grado_origen, e.apellido, e.nombre
        """,
        (anio,),
    ).fetchall()

    dobles = []
    for r in candidatos:
        g_origen   = r["grado_origen"]
        g_correcto = SIGUIENTE.get(g_origen)       # adonde debía ir
        g_actual   = r["grado_actual"]

        if not g_correcto:
            continue

        # Si el alumno está ahora en el grado SIGUIENTE al correcto → doble-promoción
        g_extra = SIGUIENTE.get(g_correcto)
        if g_actual == g_extra or (g_correcto == "6TO" and g_actual == "6TO" and r["grado_destino_registrado"] == "CANDIDATO_PRUEBAS"):
            # Verificar también el caso candidato: condicion=CANDIDATO_PRUEBAS pero origen era 5TO
            dobles.append({
                "id":          r["id"],
                "nombre":      f"{r['nombre']} {r['apellido']}",
                "curso":       r["curso"],
                "condicion":   r["condicion"],
                "grado_origen":    g_origen,
                "grado_correcto":  g_correcto,
                "grado_actual":    g_actual,
            })

    # Caso especial: condicion=CANDIDATO_PRUEBAS pero origen era 4TO o 3RO
    candidatos_extra = conn.execute(
        """
        SELECT e.id, e.nombre, e.apellido, e.grado AS grado_actual, e.curso,
               e.condicion, p.grado_origen, p.grado_destino AS grado_dest
        FROM   promociones p
        JOIN   estudiantes e ON e.id = p.estudiante_id
        WHERE  p.anio_escolar = ?
          AND  e.condicion = 'CANDIDATO_PRUEBAS'
          AND  p.grado_origen NOT IN ('6TO', '5TO')
        """,
        (anio,),
    ).fetchall()
    for r in candidatos_extra:
        g_correcto = SIGUIENTE.get(r["grado_origen"])
        if g_correcto:
            dobles.append({
                "id":             r["id"],
                "nombre":         f"{r['nombre']} {r['apellido']}",
                "curso":          r["curso"],
                "condicion":      r["condicion"],
                "grado_origen":   r["grado_origen"],
                "grado_correcto": g_correcto,
                "grado_actual":   f"CANDIDATO (grado={r['grado_actual']})",
            })

    if not dobles:
        print("✅ No se detectaron dobles-promociones para el año", anio)
        conn.close()
        return

    print(f"⚠️  {len(dobles)} alumno(s) con doble-promoción detectados:\n")
    for d in dobles:
        print(
            f"  [{d['id']:4d}] {d['nombre']:<30s} "
            f"origen={d['grado_origen']} → correcto={d['grado_correcto']} → "
            f"actual={d['grado_actual']}"
        )

    if not commit:
        print(f"\nEjecuta con --commit para aplicar las correcciones.")
        conn.close()
        return

    print("\nAplicando correcciones...")
    reparados = 0
    for d in dobles:
        est_id      = d["id"]
        g_correcto  = d["grado_correcto"]

        # Reconstruir curso: grado_correcto + mención actual
        curso_actual = d["curso"] or ""
        partes = curso_actual.split(None, 1)
        mencion = partes[1] if len(partes) > 1 else ""
        nuevo_curso = f"{g_correcto} {mencion}".strip() if mencion else g_correcto

        conn.execute(
            """UPDATE estudiantes
               SET grado = ?, curso = ?, condicion = 'ACTIVO'
               WHERE id = ?""",
            (g_correcto, nuevo_curso, est_id),
        )
        # Corregir la fila de promociones para que refleje el destino real
        conn.execute(
            """UPDATE promociones
               SET grado_destino = ?,
                   observacion   = COALESCE(observacion,'') || ' [CORREGIDO: doble-promoción reparada]'
               WHERE estudiante_id = ? AND anio_escolar = ?""",
            (g_correcto, est_id, anio),
        )
        print(f"  ✓ [{est_id}] {d['nombre']} → {g_correcto} ({nuevo_curso})")
        reparados += 1

    conn.commit()
    print(f"\n{reparados} alumno(s) corregidos. Reinicia la app para ver los cambios.")
    conn.close()


if __name__ == "__main__":
    main()
