# -*- coding: utf-8 -*-
"""Acceso a BD, caché en memoria, migraciones y seed de admin."""

import os
import sqlite3
import time as _time
import logging

from .constants import (
    DATABASE, COLUMNAS_ESTUDIANTES, TABLAS_NUEVAS,
    MIGRACIONES_ESPECIALES, _CACHE_TTL,
)

logger = logging.getLogger("axula")

__all__ = [
    "_CACHE",
    "_seed_admin",
    "cache_bust",
    "cache_get",
    "cache_set",
    "get_db",
    "migrar_bd",
]


# ── Conexión a BD ────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DATABASE, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=2000")
    conn.execute("PRAGMA temp_store=MEMORY")
    return conn

# ── CACHÉ SIMPLE EN MEMORIA ──────────────────────────────────────────────────
_CACHE = {}

def cache_get(key):
    entry = _CACHE.get(key)
    if entry and (_time.time() - entry['ts']) < _CACHE_TTL:
        return entry['val']
    return None

def cache_set(key, val):
    _CACHE[key] = {'val': val, 'ts': _time.time()}

def cache_bust():
    """Llama esto después de cualquier escritura a la BD."""
    _CACHE.clear()


# ── MIGRACIÓN DE BD ──────────────────────────────────────────────────────────

def migrar_bd():
    """
    Ejecuta toda la migración al arrancar Flask.
    - Crea tablas que no existen
    - Agrega columnas nuevas a tablas existentes
    - Ejecuta migraciones especiales puntuales
    Nunca borra datos. Siempre seguro de correr.
    """
    logger.info("  ── Migrando base de datos...")

    with sqlite3.connect(DATABASE, timeout=10) as conn:

        # ── WAL mode + índices ───────────────────────────────────────
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=2000")
        conn.execute("PRAGMA temp_store=MEMORY")
        conn.execute("PRAGMA mmap_size=134217728")
        for _idx in [
            "CREATE INDEX IF NOT EXISTS idx_est_grado ON estudiantes(grado)",
            "CREATE INDEX IF NOT EXISTS idx_est_ciclo ON estudiantes(ciclo)",
            "CREATE INDEX IF NOT EXISTS idx_asist_est ON asistencia(estudiante_id, fecha)",
            "CREATE INDEX IF NOT EXISTS idx_notif_dest ON notificaciones(destinatario_id, leida)",
            "CREATE INDEX IF NOT EXISTS idx_calif_est ON calificaciones_periodo(estudiante_id, periodo)",
            "CREATE INDEX IF NOT EXISTS idx_casos_est ON casos(estudiante_id, estado)",
            "CREATE INDEX IF NOT EXISTS idx_cuaderno_est ON cuaderno_anecdotico(estudiante_id)",
            "CREATE INDEX IF NOT EXISTS idx_reportes_est ON reportes(estudiante_id, estado)",
            "CREATE INDEX IF NOT EXISTS idx_ausencias_sem ON ausencias_semanales(estudiante_id, semana)",
        ]:
            try:
                conn.execute(_idx)
            except Exception:
                pass
        conn.commit()
        logger.info("  ✓ WAL mode + índices de rendimiento activados")

        # ── Paso 1: Crear tablas nuevas ───────────────────────────
        for sql in TABLAS_NUEVAS:
            try:
                conn.execute(sql)
            except Exception as ex:
                logger.error(f"  ⚠ Error creando tabla: {ex}")
        conn.commit()

        # ── Paso 2: Crear tabla 'estudiantes' si no existe ─────────
        cols_sql = ",\n                    ".join(
            f"{col} {tipo} DEFAULT {default}"
            for col, tipo, default in COLUMNAS_ESTUDIANTES
        )
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS estudiantes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre      TEXT,
                apellido    TEXT,
                curso       TEXT,
                {cols_sql}
            )
        """)
        conn.commit()

        # ── Paso 2b: Agregar columnas nuevas si la tabla ya existía ──
        try:
            cols_existentes = {
                row[1] for row in
                conn.execute("PRAGMA table_info(estudiantes)").fetchall()
            }
            cols_base = {'id', 'nombre', 'apellido', 'curso'}
            agregadas = []
            for col, tipo, default in COLUMNAS_ESTUDIANTES:
                if col not in cols_existentes and col not in cols_base:
                    try:
                        conn.execute(
                            f"ALTER TABLE estudiantes ADD COLUMN {col} {tipo} DEFAULT {default}"
                        )
                        agregadas.append(col)
                    except Exception as ex:
                        logger.warning(f"  ⚠ No se pudo agregar '{col}': {ex}")
            conn.commit()
            if agregadas:
                logger.info(f"  ✓ Columnas nuevas agregadas: {', '.join(agregadas)}")
            else:
                logger.info("  ✓ Esquema estudiantes — sin cambios")
        except Exception as ex:
            logger.error(f"  ⚠ Error verificando columnas: {ex}")

        # ── Paso 3: Migraciones especiales ───────────────────────────
        for desc, sql, verificar_col, en_tabla in MIGRACIONES_ESPECIALES:
            try:
                cols = {
                    row[1] for row in
                    conn.execute(f"PRAGMA table_info({en_tabla})").fetchall()
                }
                if verificar_col in cols:
                    continue
                conn.execute(sql)
                conn.commit()
                logger.info(f"  ✓ Migración especial ejecutada: {desc}")
            except Exception as ex:
                logger.error(f"  ⚠ Error en migración '{desc}': {ex}")

        # ── Paso 4: Corregir NOT NULL en acuerdos_compromiso.caso_id ──
        try:
            tbl_info = conn.execute("PRAGMA table_info(acuerdos_compromiso)").fetchall()
            caso_notnull = any(
                row[1] == "caso_id" and row[3] == 1
                for row in tbl_info
            )
            if caso_notnull:
                logger.info("  ── Corrigiendo NOT NULL en acuerdos_compromiso.caso_id...")
                conn.executescript("""
                    PRAGMA foreign_keys = OFF;
                    CREATE TABLE IF NOT EXISTS acuerdos_v2 (
                        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                        caso_id             INTEGER,
                        estudiante_id       INTEGER NOT NULL,
                        generado_por        INTEGER NOT NULL,
                        fecha_acuerdo       TEXT DEFAULT (date('now')),
                        numero_acuerdo      TEXT,
                        compromisos_estudiante TEXT,
                        compromisos_familia    TEXT,
                        compromisos_centro     TEXT,
                        base_legal          TEXT,
                        contenido_completo  TEXT,
                        firmado             INTEGER DEFAULT 0,
                        fecha_firma         TEXT,
                        observaciones       TEXT,
                        creado_en           TEXT DEFAULT (datetime('now'))
                    );
                    INSERT OR IGNORE INTO acuerdos_v2
                        SELECT id, caso_id, estudiante_id, generado_por,
                               fecha_acuerdo, numero_acuerdo,
                               compromisos_estudiante, compromisos_familia,
                               compromisos_centro, base_legal, contenido_completo,
                               firmado, fecha_firma, observaciones, creado_en
                        FROM acuerdos_compromiso;
                    DROP TABLE acuerdos_compromiso;
                    ALTER TABLE acuerdos_v2 RENAME TO acuerdos_compromiso;
                    PRAGMA foreign_keys = ON;
                """)
                conn.commit()
                logger.info("  ✓ acuerdos_compromiso.caso_id ahora es nullable")
        except Exception as ex:
            logger.error(f"  ⚠ Error migrando acuerdos_compromiso: {ex}")

    # ── reportes.caso_id (enlace reporte → caso escalado) ────────────────────
    try:
        cols_rep = [r[1] for r in conn.execute("PRAGMA table_info(reportes)").fetchall()]
        if "caso_id" not in cols_rep:
            conn.execute("ALTER TABLE reportes ADD COLUMN caso_id INTEGER")
            conn.commit()
            logger.info("  ✓ reportes.caso_id agregado")
    except Exception as _e:
        logger.warning(f"[db] migración reportes.caso_id: {_e}")

    logger.info("  ── Migración completada ✓")


def _seed_admin(hash_func):
    """
    Crea usuarios por defecto si no existen.
    Recibe hash_func (la función _hash de auth.py) para no crear dependencia circular.
    """
    import secrets as _s
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        # Migrar rol antiguo
        conn.execute("UPDATE usuarios SET rol='coordinador_general' WHERE rol='coordinador'")
        conn.commit()

        n = conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
        if n == 0:
            pwd_admin = os.environ.get("SEED_PASSWORD_ADMIN", _s.token_urlsafe(10))
            conn.execute(
                "INSERT INTO usuarios (username, password, nombre, rol) VALUES (?,?,?,?)",
                ("admin", hash_func(pwd_admin), "Coordinador General", "coordinador_general"),
            )
            conn.commit()
            logger.info("  ╔══════════════════════════════════════════════╗")
            logger.info("  ║  USUARIO ADMIN CREADO — GUARDA ESTAS CLAVES ║")
            logger.info(f"  ║  Usuario:    admin                           ║")
            logger.info(f"  ║  Contraseña: {pwd_admin:<32}║")
            logger.info("  ║  Cámbiala desde el panel de usuarios.        ║")
            logger.info("  ╚══════════════════════════════════════════════╝")

        # Búsqueda case-insensitive: evita crear duplicado si rol está como 'Directora'
        existe_directora = conn.execute(
            "SELECT id FROM usuarios WHERE lower(rol)='directora' LIMIT 1"
        ).fetchone()
        if not existe_directora:
            pwd_dir = os.environ.get("SEED_PASSWORD_DIRECTORA", _s.token_urlsafe(10))
            conn.execute(
                "INSERT INTO usuarios (username, password, nombre, rol, activo) VALUES (?,?,?,?,1)",
                ("directora", hash_func(pwd_dir), "Dirección General", "directora"),
            )
            conn.commit()
            logger.info("  ╔══════════════════════════════════════════════╗")
            logger.info("  ║  DIRECTORA CREADA — GUARDA ESTAS CLAVES     ║")
            logger.info(f"  ║  Usuario:    directora                       ║")
            logger.info(f"  ║  Contraseña: {pwd_dir:<32}║")
            logger.info("  ║  Cámbiala desde el panel de usuarios.        ║")
            logger.info("  ╚══════════════════════════════════════════════╝")
