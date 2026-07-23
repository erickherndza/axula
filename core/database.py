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
    """
    Devuelve la conexión SQLite del request actual.
    Reutiliza la misma conexión si ya fue abierta en este request (via Flask g).
    La conexión se cierra automáticamente al finalizar el request
    gracias al teardown_appcontext registrado en app.py.
    """
    from flask import g
    if "db" not in g:
        conn = sqlite3.connect(DATABASE, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=2000")
        conn.execute("PRAGMA temp_store=MEMORY")
        g.db = conn
    return g.db

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
            "CREATE INDEX IF NOT EXISTS idx_matcal_est ON materias_calificaciones(estudiante_id)",
            "CREATE INDEX IF NOT EXISTS idx_matcal_est_anio ON materias_calificaciones(estudiante_id, anio_escolar)",
            "CREATE INDEX IF NOT EXISTS idx_matcal_anio_est ON materias_calificaciones(anio_escolar, estudiante_id)",
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

    # ── calificaciones_periodo.grado — permite filtrar notas por grado ──────────
    # Sin esta columna, las notas de 4TO se mezclan con las de 5TO tras
    # la promoción porque calificaciones_periodo no sabía a qué grado pertenecían.
    try:
        cols_cp = [r[1] for r in conn.execute("PRAGMA table_info(calificaciones_periodo)").fetchall()]
        if "grado" not in cols_cp:
            conn.execute("ALTER TABLE calificaciones_periodo ADD COLUMN grado TEXT")
            conn.commit()
            logger.info("  ✓ calificaciones_periodo.grado agregado")
        # Backfill primario: usar grado de materias_calificaciones (más confiable).
        # Se corre siempre para cubrir registros nuevos que aún tengan NULL.
        conn.execute("""
            UPDATE calificaciones_periodo
            SET grado = (
                SELECT mc.grado
                FROM materias_calificaciones mc
                WHERE mc.estudiante_id = calificaciones_periodo.estudiante_id
                  AND mc.anio_escolar  = calificaciones_periodo.anio_escolar
                  AND mc.grado IS NOT NULL
                LIMIT 1
            )
            WHERE grado IS NULL
        """)
        conn.commit()
        # Corrección del backfill anterior que usaba grado_actual del estudiante:
        # si un alumno fue promovido, sus calificaciones_periodo deben tener
        # grado_origen (el grado en que cursó esas materias), NO el grado actual.
        conn.execute("""
            UPDATE calificaciones_periodo
            SET grado = (
                SELECT UPPER(p.grado_origen)
                FROM promociones p
                WHERE p.estudiante_id = calificaciones_periodo.estudiante_id
                  AND p.estado = 'PROMOVIDO'
                ORDER BY p.fecha DESC
                LIMIT 1
            )
            WHERE EXISTS (
                SELECT 1 FROM promociones p
                WHERE p.estudiante_id = calificaciones_periodo.estudiante_id
                  AND p.estado = 'PROMOVIDO'
            )
            AND UPPER(grado) = (
                SELECT UPPER(e.grado) FROM estudiantes e
                WHERE e.id = calificaciones_periodo.estudiante_id LIMIT 1
            )
        """)
        conn.commit()
        logger.info("  ✓ calificaciones_periodo.grado: backfill + corrección aplicados")
    except Exception as _e:
        logger.warning(f"[db] migración calificaciones_periodo.grado: {_e}")

    # ── reportes.caso_id (enlace reporte → caso escalado) ────────────────────
    try:
        cols_rep = [r[1] for r in conn.execute("PRAGMA table_info(reportes)").fetchall()]
        if "caso_id" not in cols_rep:
            conn.execute("ALTER TABLE reportes ADD COLUMN caso_id INTEGER")
            conn.commit()
            logger.info("  ✓ reportes.caso_id agregado")
    except Exception as _e:
        logger.warning(f"[db] migración reportes.caso_id: {_e}")

    # Fix puntual: sincronizar curso con grado para estudiantes promovidos
    # con código anterior que solo actualizaba grado pero no curso.
    # "4TO MULTIMEDIA" con grado=5TO → "5TO MULTIMEDIA"
    try:
        with sqlite3.connect(DATABASE, timeout=10) as _c:
            fixed = _c.execute("""
                UPDATE estudiantes
                SET curso = UPPER(grado) ||
                            CASE WHEN INSTR(curso, ' ') > 0
                                 THEN SUBSTR(curso, INSTR(curso, ' '))
                                 ELSE '' END
                WHERE grado IS NOT NULL
                  AND curso IS NOT NULL
                  AND UPPER(grado) != UPPER(
                        CASE WHEN INSTR(curso, ' ') > 0
                             THEN SUBSTR(curso, 1, INSTR(curso, ' ') - 1)
                             ELSE curso END)
            """).rowcount
            _c.commit()
            if fixed:
                logger.info(f"  ✓ curso sincronizado con grado: {fixed} estudiante(s)")
    except Exception as _e:
        logger.warning(f"[db] fix curso/grado: {_e}")

    logger.info("  ── Migración completada ✓")

    # H12: sembrar catálogo de materias si está vacío
    try:
        with sqlite3.connect(DATABASE, timeout=10) as _c:
            _c.row_factory = sqlite3.Row
            n_mat = _c.execute("SELECT COUNT(*) FROM materias").fetchone()[0]
            if n_mat == 0:
                from .helpers import sembrar_catalogo_materias
                insertados = sembrar_catalogo_materias(_c)
                _c.commit()
                if insertados:
                    logger.info(f"  ✓ Catálogo materias sembrado: {insertados} entradas")
    except Exception as _e:
        logger.warning(f"[db] seed catálogo materias: {_e}")

    # H13: sembrar materias 5TO/6TO MULTIMEDIA en catálogo (si aún no están)
    try:
        with sqlite3.connect(DATABASE, timeout=10) as _c:
            _c.row_factory = sqlite3.Row
            from .constants import PLAN_ARTES
            import unicodedata as _ud
            def _norm_m(s):
                s = (s or "").strip().lower()
                return _ud.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
            _nuevas = []
            for _mencion, _planes in PLAN_ARTES.items():
                for _grado_k, _mats in _planes.items():
                    for _nom, _ in _mats:
                        _norm = _norm_m(_nom)
                        existe = _c.execute(
                            "SELECT 1 FROM materias WHERE nombre_norm=?", (_norm,)
                        ).fetchone()
                        if not existe:
                            _c.execute(
                                "INSERT OR IGNORE INTO materias (nombre_canonico, nombre_norm) VALUES (?,?)",
                                (_nom, _norm)
                            )
                            _nuevas.append(_nom)
            _c.commit()
            if _nuevas:
                logger.info(f"  ✓ Materias nuevas al catálogo: {', '.join(_nuevas)}")
    except Exception as _e:
        logger.warning(f"[db] seed materias PLAN_ARTES: {_e}")

    # H3: sembrar CEs de Lenguaje Visual si no existen
    try:
        with sqlite3.connect(DATABASE, timeout=10) as _c:
            _c.row_factory = sqlite3.Row
            n_ce = _c.execute(
                "SELECT COUNT(*) FROM competencias_materia WHERE materia=?",
                ("Lenguaje Visual, Dibujo y Creación de Personajes",)
            ).fetchone()[0]
            if n_ce == 0:
                from .helpers import sembrar_competencias_materia
                _ces_lenguaje_visual = [
                    {"numero": 1, "descripcion": "Argumenta el rol del lenguaje visual y artesanal y su evolución a través de la historia.", "periodo_eval": "P1"},
                    {"numero": 2, "descripcion": "Identifica los principales elementos presentes en el lenguaje visual y artesanal como formas, estructuras, colores, texturas, figura-fondo, composición, luz y sombras, tamaños, escalas, equilibrios, unidad, variedad, espacialidades, materiales y formatos.", "periodo_eval": "P2"},
                    {"numero": 3, "descripcion": "Analiza aspectos connotativos y denotativos de imágenes de diferentes estilos artísticos.", "periodo_eval": "P2"},
                    {"numero": 4, "descripcion": "Elabora obras artísticas visuales y artesanales haciendo uso de los elementos básicos y técnicas.", "periodo_eval": "P3"},
                    {"numero": 5, "descripcion": "Describe las características extrínsecas (aspecto físico) e intrínsecas (personalidad) de los personajes ya existentes.", "periodo_eval": "P2"},
                    {"numero": 6, "descripcion": "Comprende el método de organización de la información para el desarrollo de la personalidad del personaje.", "periodo_eval": "P3"},
                    {"numero": 7, "descripcion": "Diseña con formas geométricas básicas la estructura interna del personaje.", "periodo_eval": "P3"},
                    {"numero": 8, "descripcion": "Desarrolla conceptos físicos del personaje, aplica el model sheet.", "periodo_eval": "P4"},
                    {"numero": 9, "descripcion": "Digitaliza los personajes y sus elementos evidenciando la aplicación del color, texturas, profundidad, perspectiva y detalles realizados con la tableta gráfica dentro de Photoshop.", "periodo_eval": "P4"},
                ]
                insertados = sembrar_competencias_materia(
                    _c, "Lenguaje Visual, Dibujo y Creación de Personajes", _ces_lenguaje_visual
                )
                _c.commit()
                if insertados:
                    logger.info(f"  ✓ CEs sembradas: Lenguaje Visual ({insertados} competencias)")
    except Exception as _e:
        logger.warning(f"[db] seed CE Lenguaje Visual: {_e}")


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
