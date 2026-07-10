#!/usr/bin/env python3
"""
Carga P1 y P2 de "Diseño Básico y Expresión Visual" para 4TO MULTIMEDIA
desde los datos del Registro del Coordinador (2025-2026).

Usa INSERT OR IGNORE — no pisa datos existentes.
Fuente: 4TO. GRADO - DISEÑO BÁSICO (MULT) 25-26.xlsm (sección 2)

Uso:
    cd /path/to/elearning
    python3 scripts/cargar_diseno_basico_p12.py [--commit]

    Sin --commit: solo preview (dry-run)
    Con --commit:  escribe en BD
"""
import sys
import os
import difflib
import sqlite3

# ── Datos parseados del Excel (sección 2, cols 55-56 = P1, P2) ──────────────
# Formato: (nombre_excel, apellido_excel, p1, p2)
DATOS_EXCEL = [
    ("Edinso Manuel",    "Abreu Valdez",          71,  88),
    ("Alberto",          "Alcántara Cuevas",       81,  82),
    ("Trino Sahino",     "Arias Rosa",             74,  75),
    ("Harolin Maciel",   "Beriguete",              93,  94),
    ("Arianny",          "Bretón Fermín",          91,  95),
    ("Edison Alexander", "Chacón",                 70, None),  # P2 ausente
    ("Sharibel",         "Clase",                  74, None),  # P2 ausente (RETIRADO)
    ("Saviel",           "Del Rosario",            93,  94),
    ("Juan",             "Del Rosario Mesa",       83,  70),
    ("Yulian Miguel",    "Del Villar Lorenzo",     85,  80),
    ("Wagner Silvilio",  "Estepan Ramírez",        84,  85),
    ("Juan Ramón",       "Fernández Díaz",         79,  90),
    ("Jadiel Alexander", "Maldonado Castillo",     80,  92),
    ("Miguel Angel",     "Martinez Medina",        81,  90),
    ("Gabi Nataniel",    "Martinez Medina",        80,  85),
    ("Francisco",        "Mendez Valdez",          83,  92),
    ("Lismerlin",        "Moreno Manzueta",        79, None),  # P2 ausente
    ("Gabriela",         "Núñez Peña",             93,  94),
    ("Jose Junior",      "Perez",                  88,  85),
    ("Yadiel Alberto",   "Pimentel Feliz",         87,  83),
    ("Diana",            "Ramirez De La Cruz",     92,  94),
    ("Yamilka",          "Ramirez Sanchez",        84,  65),
    ("Jesus Enmanuel",   "Reynoso",                80,  65),
    ("Densel Eduardo",   "Rodriguez Perez",        94,  99),
    ("Angel Luis",       "Shepharh Manzueta",      80,  85),
    ("Matius",           "Silfa Álvarez",          93,  96),
    ("Jorlenny Massiel", "Solano Ceballos",        91,  98),
    ("Micaias Moises",   "Torres Cabrera",         79,  75),
    ("Victor Rafael",    "Vazquez Duran",          80,  74),
    ("Samuel Alexander", "Veloz Contreras",        70,  85),
    ("Josue Francisco",  "Fabre Rodríguez",        84,  88),
]

MATERIA   = "Diseño Básico y Expresión Visual"
ANIO      = "2025-2026"
GRADO     = "4TO"
PROF_FALLBACK = 1  # ID de profesor de respaldo (se busca primero)

import unicodedata
def norm(s):
    s = (s or "").lower().strip()
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")


def main():
    commit = "--commit" in sys.argv

    db_path = os.environ.get("DATABASE", "database.db")
    if not os.path.exists(db_path):
        # Buscar en /data/ (Render persistent disk)
        if os.path.exists("/data/database.db"):
            db_path = "/data/database.db"
        else:
            print(f"ERROR: BD no encontrada en {db_path}")
            sys.exit(1)

    print(f"BD: {db_path}")
    print(f"Modo: {'COMMIT' if commit else 'DRY-RUN (agrega --commit para escribir)'}")
    print()

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Índice de 4TO MULTIMEDIA (activos + retirados para no perder nadie)
    ests = conn.execute(
        "SELECT id, nombre, apellido FROM estudiantes "
        "WHERE UPPER(TRIM(grado)) = 'ACTIVO' OR UPPER(TRIM(grado)) = '4TO' "
    ).fetchall()
    # Filtrar los de MULTIMEDIA o 4TO
    ests_mm = conn.execute(
        "SELECT id, nombre, apellido FROM estudiantes "
        "WHERE UPPER(TRIM(grado)) = '4TO' AND UPPER(curso) LIKE '%MULTIMEDIA%'"
    ).fetchall()

    # Obtener profesor_id para Diseño Básico (el que tenga más registros)
    prof_row = conn.execute(
        "SELECT profesor_id, COUNT(*) as c FROM calificaciones_periodo "
        "WHERE materia = ? GROUP BY profesor_id ORDER BY c DESC LIMIT 1",
        (MATERIA,)
    ).fetchone()
    prof_id = prof_row["profesor_id"] if prof_row else PROF_FALLBACK

    insertados = 0
    ignorados  = 0
    sin_match  = []

    for nombre_ex, apellido_ex, p1, p2 in DATOS_EXCEL:
        key = norm(f"{nombre_ex} {apellido_ex}")

        best_score, best_est = 0.0, None
        for e in ests_mm:
            db_key = norm(f"{e['nombre']} {e['apellido']}")
            sc = difflib.SequenceMatcher(None, key, db_key).ratio()
            if sc > best_score:
                best_score, best_est = sc, e

        if best_score < 0.75:
            # Segundo intento con todos los de la escuela (por si el filtro MULTIMEDIA falló)
            for e in conn.execute("SELECT id, nombre, apellido FROM estudiantes").fetchall():
                db_key = norm(f"{e['nombre']} {e['apellido']}")
                sc = difflib.SequenceMatcher(None, key, db_key).ratio()
                if sc > best_score:
                    best_score, best_est = sc, e

        if best_score < 0.75 or best_est is None:
            sin_match.append(f"{nombre_ex} {apellido_ex} (score={best_score:.2f})")
            continue

        est_id = best_est["id"]
        tag    = f"{nombre_ex} {apellido_ex} → {best_est['nombre']} {best_est['apellido']} (ID={est_id}, sc={best_score:.2f})"

        for periodo, nota in [("P1", p1), ("P2", p2)]:
            if nota is None:
                continue

            # Verificar si ya existe
            existe = conn.execute(
                "SELECT 1 FROM calificaciones_periodo "
                "WHERE estudiante_id=? AND materia=? AND periodo=? AND anio_escolar=?",
                (est_id, MATERIA, periodo, ANIO)
            ).fetchone()

            if existe:
                print(f"  [SKIP] {tag} | {periodo}={nota} (ya existe)")
                ignorados += 1
                continue

            if commit:
                conn.execute(
                    "INSERT OR IGNORE INTO calificaciones_periodo "
                    "(estudiante_id, profesor_id, materia, periodo, calificacion, "
                    " anio_escolar, observacion, origen, grado) "
                    "VALUES (?,?,?,?,?,?,?,?,?)",
                    (est_id, prof_id, MATERIA, periodo, float(nota),
                     ANIO, "Cargado desde registro coordinador 2025-2026", "importacion", GRADO)
                )
            print(f"  {'[INSERT]' if commit else '[DRY]  '} {tag} | {periodo}={nota}")
            insertados += 1

    if commit:
        conn.commit()

    print()
    print(f"{'Insertados' if commit else 'Pendientes'}: {insertados}")
    print(f"Skipped (ya existían): {ignorados}")
    if sin_match:
        print(f"SIN MATCH ({len(sin_match)}):")
        for s in sin_match:
            print(f"  {s}")

    conn.close()


if __name__ == "__main__":
    main()
