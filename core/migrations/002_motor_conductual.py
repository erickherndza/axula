"""
Migración 002 — Motor Conductual (Fase 1)
Extiende cuaderno_anecdotico con polaridad y tags.
Crea tabla de métricas conductuales para el semáforo por sección.

Ejecución: python3 core/migrations/002_motor_conductual.py
Es idempotente (se puede correr varias veces sin daño).
"""

import sqlite3
import sys
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'database.db')


DDL = [
    # 1. Polaridad en cuaderno_anecdotico (ALTER es seguro si columna no existe)
    """
    ALTER TABLE cuaderno_anecdotico
    ADD COLUMN polaridad TEXT NOT NULL DEFAULT 'neutro'
    """,

    # 2. Tags libres en cuaderno_anecdotico (JSON array de strings)
    """
    ALTER TABLE cuaderno_anecdotico
    ADD COLUMN tags TEXT DEFAULT '[]'
    """,

    # 3. Catálogo de tags predefinidos
    """
    CREATE TABLE IF NOT EXISTS conductor_tags_catalogo (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        tag         TEXT NOT NULL UNIQUE,
        polaridad   TEXT NOT NULL CHECK(polaridad IN ('positivo','negativo')),
        icono       TEXT DEFAULT '',
        activo      INTEGER DEFAULT 1
    )
    """,

    # 4. Métricas conductuales calculadas por estudiante / año escolar
    """
    CREATE TABLE IF NOT EXISTS metricas_conductuales (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        estudiante_id       INTEGER NOT NULL,
        anio_escolar        TEXT NOT NULL,
        score_total         REAL DEFAULT 0,
        score_notas         REAL DEFAULT 0,
        score_asistencia    REAL DEFAULT 0,
        score_tags          REAL DEFAULT 0,
        nivel               TEXT DEFAULT 'ROJO'
                                CHECK(nivel IN ('VERDE','AMARILLO','ROJO')),
        tags_positivos      INTEGER DEFAULT 0,
        tags_negativos      INTEGER DEFAULT 0,
        total_registros     INTEGER DEFAULT 0,
        calculado_en        TEXT DEFAULT (datetime('now')),
        UNIQUE(estudiante_id, anio_escolar),
        FOREIGN KEY (estudiante_id) REFERENCES estudiantes(id)
    )
    """,

    # Índice para consulta rápida por sección
    """
    CREATE INDEX IF NOT EXISTS idx_metricas_anio
        ON metricas_conductuales(anio_escolar, nivel)
    """,
]

TAGS_INICIALES = [
    # Positivos
    ('Participación activa',     'positivo', '✋'),
    ('Trabajo en equipo',        'positivo', '🤝'),
    ('Puntualidad',              'positivo', '⏰'),
    ('Iniciativa propia',        'positivo', '💡'),
    ('Respeto al docente',       'positivo', '🎓'),
    ('Entrega de tarea',         'positivo', '📋'),
    ('Actitud positiva',         'positivo', '😊'),
    ('Ayuda a compañeros',       'positivo', '🙏'),
    # Negativos
    ('Distracción en clase',     'negativo', '📵'),
    ('Falta de respeto',         'negativo', '🚫'),
    ('Conflicto con compañeros', 'negativo', '⚠️'),
    ('Uso del celular',          'negativo', '📱'),
    ('Inasistencia justificada', 'negativo', '🏠'),
    ('Inasistencia injustificada','negativo','❌'),
    ('No entregó tarea',         'negativo', '📝'),
    ('Desafía autoridad',        'negativo', '🔴'),
    ('Abandona el aula',         'negativo', '🚪'),
    ('Interrupción constante',   'negativo', '🗣️'),
]


def run():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    errors = []

    for ddl in DDL:
        stmt = ddl.strip()
        try:
            cur.execute(stmt)
            conn.commit()
        except sqlite3.OperationalError as e:
            msg = str(e)
            # ALTER TABLE falla si columna ya existe — es seguro ignorarlo
            if 'duplicate column' in msg.lower() or 'already exists' in msg.lower():
                print(f"  [skip] {msg}")
            else:
                errors.append(f"DDL FALLÓ: {msg}\nSQL: {stmt[:80]}")

    # Insertar tags iniciales (ignora duplicados por UNIQUE)
    for tag, pol, icono in TAGS_INICIALES:
        try:
            cur.execute(
                "INSERT OR IGNORE INTO conductor_tags_catalogo (tag, polaridad, icono) VALUES (?,?,?)",
                (tag, pol, icono)
            )
        except sqlite3.Error as e:
            errors.append(f"Tag insert falló ({tag}): {e}")
    conn.commit()

    conn.close()

    if errors:
        print("\n⚠️  Errores en migración:")
        for e in errors:
            print(" ", e)
        sys.exit(1)
    else:
        print("✅ Migración 002_motor_conductual completada.")


if __name__ == '__main__':
    run()
