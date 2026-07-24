#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
revertir_candidatos.py
======================
Revierte estudiantes que quedaron con condicion='CANDIDATO_PRUEBAS' de forma
incorrecta por el bug de doble-promoción en cadena (loop ascendente + ejecución
sin snapshot previo).

Raíz del problema:
  - cerrar_anio_escolar() iteraba GRADOS en orden ascendente y ejecutaba
    promociones en el mismo paso → un alumno promovido de 4TO a 5TO era
    encontrado de nuevo por el loop de 5TO y promovido a 6TO, luego a
    CANDIDATO_PRUEBAS.
  - El UPSERT en 'promociones' sobreescribe grado_origen → la tabla no
    conserva el grado original.
  - Para CANDIDATO_PRUEBAS: solo se actualiza 'condicion'; grado permanece
    en '6TO' y los KPIs fueron NULEados durante la cascada 5TO→6TO.

MODOS:
  1. Sin flags  → Diagnóstico: lista todos los CANDIDATO_PRUEBAS
  2. --fix-multimedia    → Revierte los MULTIMEDIA a 5TO (20 alumnos)
  3. --fix-mencion MENCION GRADO_CORRECTO
                         → Revierte una mención completa a un grado
  4. --from-csv ARCHIVO  → Revierte según CSV: est_id,grado_correcto[,mencion]
  5. Agregar --commit    → Aplica los cambios en BD

EJEMPLOS:
    python3 scripts/revertir_candidatos.py
    python3 scripts/revertir_candidatos.py --fix-multimedia
    python3 scripts/revertir_candidatos.py --fix-multimedia --commit
    python3 scripts/revertir_candidatos.py --fix-mencion MÚSICA 5TO --commit
    python3 scripts/revertir_candidatos.py --from-csv fixes.csv --commit
"""
import csv
import os
import sqlite3
import sys

# ── Path a la BD ──────────────────────────────────────────────────────────────
_en_render = os.path.exists("/data")
DB_PATH = os.environ.get(
    "DATABASE_PATH",
    "/data/database.db"
    if _en_render
    else os.path.join(os.path.dirname(__file__), "..", "database.db"),
)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("DATABASE_PATH", DB_PATH)

from core.helpers import obtener_notas_estudiante  # noqa: E402

# Año escolar afectado (el que se cerró mal)
ANIO_AFECTADO = "2025-2026"

# Menciones para búsqueda (LIKE patterns, acepta variaciones de acento)
MENCIONES_KEYWORDS = {
    "MULTIMEDIA":     "MULTIMEDIA",
    "MÚSICA":         "M%SICA",   # cubre MÚSICA y MUSICA
    "TEATRO":         "TEATRO",
    "ARTES VISUALES": "ARTES%VISUALES",
    "DANZA":          "DANZA",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _todos_candidatos(conn) -> list[dict]:
    """Retorna todos los CANDIDATO_PRUEBAS con info de promociones."""
    rows = conn.execute(
        """
        SELECT  e.id, e.nombre, e.apellido, e.grado, e.curso, e.condicion,
                e.mencion,
                COALESCE(p.grado_origen, '') AS grado_origen_prom,
                COALESCE(p.grado_destino, '') AS grado_destino_prom
        FROM    estudiantes e
        LEFT JOIN promociones p
               ON p.estudiante_id = e.id AND p.anio_escolar = ?
        WHERE   e.condicion = 'CANDIDATO_PRUEBAS'
        ORDER   BY e.curso, e.apellido, e.nombre
        """,
        (ANIO_AFECTADO,),
    ).fetchall()
    return [dict(r) for r in rows]


def _recalcular_kpis(conn, est_id: int) -> dict | None:
    """Recalcula KPIs desde obtener_notas_estudiante() (misma lógica que motor)."""
    notas = obtener_notas_estudiante(conn, est_id, ANIO_AFECTADO)
    if not notas:
        return None

    per_sums: dict[int, list[float]] = {1: [], 2: [], 3: [], 4: []}
    for mat_data in notas.values():
        for i in range(1, 5):
            v = mat_data.get(f"p{i}", 0.0)
            if v and v > 0:
                per_sums[i].append(v)

    acad_p = {
        i: round(sum(per_sums[i]) / len(per_sums[i]), 2) if per_sums[i] else 0.0
        for i in range(1, 5)
    }

    promedios = [d["promedio"] for d in notas.values() if d.get("promedio") and d["promedio"] > 0]
    p_acad = round(sum(promedios) / len(promedios), 2) if promedios else 0.0

    return {
        "p_acad":  p_acad,
        "acad_p1": acad_p[1],
        "acad_p2": acad_p[2],
        "acad_p3": acad_p[3],
        "acad_p4": acad_p[4],
    }


def _revertir_estudiante(conn, est_id: int, grado_correcto: str,
                          mencion: str, commit: bool, verbose: bool = True) -> bool:
    """
    Revierte un estudiante a grado_correcto ACTIVO.
    - Actualiza grado, curso, condicion en estudiantes
    - Actualiza promociones para reflejar el estado correcto
    - Recalcula KPIs desde MC
    """
    est = conn.execute(
        "SELECT nombre, apellido, grado, curso, condicion FROM estudiantes WHERE id = ?",
        (est_id,),
    ).fetchone()
    if not est:
        print(f"  ERROR: estudiante {est_id} no encontrado")
        return False

    nombre = f"{est['nombre']} {est['apellido']}"
    nuevo_curso = f"{grado_correcto} {mencion}".strip() if mencion else grado_correcto

    if verbose:
        print(
            f"  [{est_id:4d}] {nombre:<35s} "
            f"{est['grado']}/{est['condicion']} → {grado_correcto} ACTIVO  ({nuevo_curso})"
        )

    if not commit:
        return True

    # 1. Revertir grado, curso, condicion
    conn.execute(
        """UPDATE estudiantes
           SET grado = ?, curso = ?, condicion = 'ACTIVO'
           WHERE id = ?""",
        (grado_correcto, nuevo_curso, est_id),
    )

    # 2. Revertir fila en promociones (marcar como corregido)
    conn.execute(
        """UPDATE promociones
           SET grado_destino = ?,
               estado        = 'PROMOVIDO',
               observacion   = COALESCE(observacion, '') ||
                               ' [CORREGIDO: cascada doble-promoción revertida a ' || ? || ']'
           WHERE estudiante_id = ? AND anio_escolar = ?""",
        (grado_correcto, grado_correcto, est_id, ANIO_AFECTADO),
    )

    # 3. Recalcular KPIs (fueron NULEados durante la cascada)
    kpis = _recalcular_kpis(conn, est_id)
    if kpis:
        conn.execute(
            """UPDATE estudiantes
               SET p_acad    = ?,
                   acad_p1   = ?,
                   acad_p2   = ?,
                   acad_p3   = ?,
                   acad_p4   = ?,
                   tiene_notas = 1
               WHERE id = ?""",
            (kpis["p_acad"], kpis["acad_p1"], kpis["acad_p2"],
             kpis["acad_p3"], kpis["acad_p4"], est_id),
        )
    else:
        print(f"    ⚠ No se encontraron notas para recalcular KPIs de [{est_id}]")

    return True


# ── Modos de operación ────────────────────────────────────────────────────────

def modo_diagnostico(conn):
    candidatos = _todos_candidatos(conn)
    print(f"\nTotal CANDIDATO_PRUEBAS en BD: {len(candidatos)}\n")

    # Agrupar por curso actual
    grupos: dict[str, list[dict]] = {}
    for c in candidatos:
        key = c["curso"] or "(sin curso)"
        grupos.setdefault(key, []).append(c)

    print(f"{'Curso actual':<25}  {'Cant':>5}  {'grado_origen prom':>18}  Ejemplo")
    print("─" * 80)
    for curso, alumnos in sorted(grupos.items()):
        go = alumnos[0]["grado_origen_prom"] or "—"
        ejemplo = f"{alumnos[0]['nombre']} {alumnos[0]['apellido']}"
        print(f"{curso:<25}  {len(alumnos):>5}  {go:>18}  {ejemplo}")

    print(f"\nTotal: {len(candidatos)} estudiantes\n")
    print("OPCIONES DE REPARACIÓN:")
    print("  python3 scripts/revertir_candidatos.py --fix-multimedia --commit")
    print("  python3 scripts/revertir_candidatos.py --fix-mencion MÚSICA 5TO --commit")
    print("  python3 scripts/revertir_candidatos.py --from-csv fixes.csv --commit")
    print("\n  Formato CSV (fixes.csv):")
    print("    est_id,grado_correcto,mencion")
    print("    123,5TO,MULTIMEDIA")
    print("    456,4TO,TEATRO")


def modo_fix_multimedia(conn, commit: bool):
    rows = conn.execute(
        """
        SELECT  e.id, e.nombre, e.apellido, e.grado, e.curso, e.condicion, e.mencion
        FROM    estudiantes e
        WHERE   e.condicion = 'CANDIDATO_PRUEBAS'
          AND   upper(e.curso) LIKE '%MULTIMEDIA%'
        ORDER   BY e.apellido, e.nombre
        """,
    ).fetchall()

    print(f"\nMULTIMEDIA — CANDIDATO_PRUEBAS encontrados: {len(rows)}")
    print("Todos serán revertidos a 5TO MULTIMEDIA ACTIVO.")
    print("(Los 3 que completaron el proceso se re-promueven manualmente desde la UI.)\n")

    reparados = 0
    for r in rows:
        ok = _revertir_estudiante(conn, r["id"], "5TO", "MULTIMEDIA", commit)
        if ok:
            reparados += 1

    if commit:
        conn.commit()
        print(f"\n✅ {reparados} estudiantes revertidos a 5TO MULTIMEDIA ACTIVO.")
        print("→ Reinicia la app en Render, luego re-promueve los 3 legítimos vía UI.")
    else:
        print(f"\n(Dry-run) Se revertirían {reparados} estudiantes. Agrega --commit para aplicar.")


def modo_fix_mencion(conn, mencion: str, grado_correcto: str, commit: bool):
    # Busca por mencion en la columna 'mencion' o en el campo 'curso'
    rows = conn.execute(
        """
        SELECT  e.id, e.nombre, e.apellido, e.grado, e.curso, e.condicion, e.mencion
        FROM    estudiantes e
        WHERE   e.condicion = 'CANDIDATO_PRUEBAS'
          AND   (upper(e.mencion) = upper(?)
                 OR upper(e.curso) LIKE upper('%' || ? || '%'))
        ORDER   BY e.apellido, e.nombre
        """,
        (mencion, mencion),
    ).fetchall()

    print(f"\n{mencion.upper()} — CANDIDATO_PRUEBAS encontrados: {len(rows)}")
    print(f"Todos serán revertidos a {grado_correcto} {mencion} ACTIVO.\n")

    reparados = 0
    for r in rows:
        ok = _revertir_estudiante(conn, r["id"], grado_correcto, mencion, commit)
        if ok:
            reparados += 1

    if commit:
        conn.commit()
        print(f"\n✅ {reparados} estudiantes revertidos a {grado_correcto} {mencion} ACTIVO.")
    else:
        print(f"\n(Dry-run) Se revertirían {reparados} estudiantes. Agrega --commit para aplicar.")


def modo_fix_segundo_ciclo(conn, commit: bool):
    """
    Revierte TODOS los CANDIDATO_PRUEBAS del segundo ciclo (4TO-6TO) a 5TO ACTIVO.
    Detecta la mención desde e.mencion o extrayendo la segunda palabra de e.curso.
    Los estudiantes que legitimamente completaron 6TO se re-promueven manualmente desde la UI.
    """
    # Menciones conocidas del segundo ciclo
    MENCIONES_SEGUNDO_CICLO = [
        "MULTIMEDIA", "MÚSICA", "MUSICA", "TEATRO",
        "ARTES VISUALES", "DANZA",
    ]

    # Construir cláusula LIKE para cualquier mención
    like_clauses = " OR ".join(
        [f"upper(e.curso) LIKE '%{m}%'" for m in MENCIONES_SEGUNDO_CICLO]
        + ["upper(e.mencion) IN ('MULTIMEDIA','MÚSICA','MUSICA','TEATRO','ARTES VISUALES','DANZA')"]
    )

    rows = conn.execute(
        f"""
        SELECT  e.id, e.nombre, e.apellido, e.grado, e.curso, e.condicion,
                COALESCE(e.mencion, '') AS mencion
        FROM    estudiantes e
        WHERE   e.condicion = 'CANDIDATO_PRUEBAS'
          AND   ({like_clauses})
        ORDER   BY e.curso, e.apellido, e.nombre
        """,
    ).fetchall()

    print(f"\nSEGUNDO CICLO (todas las menciones) — CANDIDATO_PRUEBAS: {len(rows)}")
    print("Todos serán revertidos a 5TO <MENCIÓN> ACTIVO.\n")

    # Contar por mención
    conteo: dict[str, int] = {}
    for r in rows:
        # Extraer mención del campo curso si e.mencion está vacío
        mencion = r["mencion"].strip()
        if not mencion:
            partes = (r["curso"] or "").split(None, 1)
            mencion = partes[1] if len(partes) > 1 else ""
        conteo[mencion] = conteo.get(mencion, 0) + 1

    for m, c in sorted(conteo.items()):
        print(f"  {m:<20} → {c} alumnos")
    print()

    reparados = 0
    for r in rows:
        mencion = r["mencion"].strip()
        if not mencion:
            partes = (r["curso"] or "").split(None, 1)
            mencion = partes[1] if len(partes) > 1 else ""

        ok = _revertir_estudiante(conn, r["id"], "5TO", mencion, commit)
        if ok:
            reparados += 1

    if commit:
        conn.commit()
        print(f"\n✅ {reparados} estudiantes revertidos a 5TO ACTIVO (por mención).")
        print("→ Reinicia la app en Render.")
        print("→ Luego re-promueve via UI a los estudiantes que sí completaron 6TO.")
    else:
        print(f"\n(Dry-run) Se revertirían {reparados} estudiantes. Agrega --commit para aplicar.")


def modo_from_csv(conn, csv_path: str, commit: bool):
    if not os.path.exists(csv_path):
        print(f"ERROR: archivo no encontrado: {csv_path}")
        return

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        filas = list(reader)

    print(f"\nCSV: {csv_path} — {len(filas)} filas\n")

    reparados = 0
    errores   = 0
    for fila in filas:
        try:
            est_id = int(fila["est_id"])
            grado  = fila["grado_correcto"].strip().upper()
            mencion = fila.get("mencion", "").strip()
            ok = _revertir_estudiante(conn, est_id, grado, mencion, commit)
            if ok:
                reparados += 1
            else:
                errores += 1
        except (KeyError, ValueError) as e:
            print(f"  SKIP fila inválida: {fila} — {e}")
            errores += 1

    if commit:
        conn.commit()
        print(f"\n✅ {reparados} revertidos. {errores} errores.")
    else:
        print(f"\n(Dry-run) {reparados} se revertirían. Agrega --commit para aplicar.")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    commit = "--commit" in args
    args = [a for a in args if a != "--commit"]

    print(f"Modo: {'APLICAR CAMBIOS' if commit else 'DRY-RUN (sin cambios)'}")
    print(f"BD:   {DB_PATH}")
    print(f"Año:  {ANIO_AFECTADO}\n")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    if not args:
        modo_diagnostico(conn)

    elif args[0] == "--fix-multimedia":
        modo_fix_multimedia(conn, commit)

    elif args[0] == "--fix-segundo-ciclo":
        modo_fix_segundo_ciclo(conn, commit)

    elif args[0] == "--fix-mencion" and len(args) >= 3:
        mencion       = args[1]
        grado_correcto = args[2].upper()
        modo_fix_mencion(conn, mencion, grado_correcto, commit)

    elif args[0] == "--from-csv" and len(args) >= 2:
        modo_from_csv(conn, args[1], commit)

    else:
        print("Uso:")
        print("  python3 scripts/revertir_candidatos.py")
        print("  python3 scripts/revertir_candidatos.py --fix-segundo-ciclo [--commit]")
        print("  python3 scripts/revertir_candidatos.py --fix-multimedia [--commit]")
        print("  python3 scripts/revertir_candidatos.py --fix-mencion MÚSICA 5TO [--commit]")
        print("  python3 scripts/revertir_candidatos.py --from-csv fixes.csv [--commit]")

    conn.close()


if __name__ == "__main__":
    main()
