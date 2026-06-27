-- ============================================================
-- MIGRACIÓN 004: Sistema de evaluación mejorado
-- TecnoAuladom · Ordenanza 04-2023 MINERD
-- Ejecutar con: python3 scripts/run_migration.py 004
-- ============================================================

PRAGMA foreign_keys = OFF;
BEGIN TRANSACTION;

-- ────────────────────────────────────────────────
-- 0. TABLA: anios_escolares (NUEVA — referenciada por spec)
-- ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS anios_escolares (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre  TEXT NOT NULL UNIQUE,
    activo  INTEGER NOT NULL DEFAULT 0
);

INSERT OR IGNORE INTO anios_escolares (nombre, activo) VALUES ('2025-2026', 1);

-- ────────────────────────────────────────────────
-- 1. TABLA: competencias_materia (NUEVA)
-- ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS competencias_materia (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    materia_id  INTEGER,
    materia     TEXT,
    ciclo       TEXT NOT NULL DEFAULT 'modalidad'
                     CHECK(ciclo IN ('1er_ciclo','2do_ciclo','modalidad')),
    tipo        TEXT NOT NULL DEFAULT 'especifica'
                     CHECK(tipo IN ('fundamental','especifica')),
    nombre      TEXT NOT NULL,
    descripcion TEXT,
    activa      INTEGER NOT NULL DEFAULT 1,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_comp_materia ON competencias_materia(materia_id);

-- ────────────────────────────────────────────────
-- 2. BACKUP tablas existentes
-- ────────────────────────────────────────────────
DROP TABLE IF EXISTS actividades_evaluacion_old;
DROP TABLE IF EXISTS notas_actividad_old;

ALTER TABLE actividades_evaluacion RENAME TO actividades_evaluacion_old;
ALTER TABLE notas_actividad        RENAME TO notas_actividad_old;

-- ────────────────────────────────────────────────
-- 3. TABLA: actividades_evaluacion (NUEVA — schema completo)
-- ────────────────────────────────────────────────
CREATE TABLE actividades_evaluacion (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    -- Identificación del docente y materia
    docente_id          INTEGER NOT NULL,
    materia_id          INTEGER,
    materia             TEXT,
    grado               TEXT,
    mencion             TEXT DEFAULT 'MULTIMEDIA',
    -- Período y año escolar
    periodo             INTEGER CHECK(periodo BETWEEN 1 AND 4),
    anio_escolar_id     INTEGER,
    anio_escolar        TEXT,
    -- Definición de la actividad
    tipo                TEXT NOT NULL DEFAULT 'tarea'
                             CHECK(tipo IN ('tarea','proyecto','participacion',
                                            'prueba','exposicion','otro')),
    titulo              TEXT,
    descripcion         TEXT,
    -- Vinculación curricular
    planificacion_id    INTEGER,
    competencia_id      INTEGER REFERENCES competencias_materia(id),
    competencias        TEXT,
    -- Puntuación (modelo libre — suma del período debe ser 100)
    valor_puntos        INTEGER NOT NULL DEFAULT 10,
    -- Campos de compatibilidad con sistema anterior
    calificacion        REAL,
    peso                REAL DEFAULT 1.0,
    max_puntos          REAL DEFAULT 100.0,
    observaciones       TEXT,
    -- Fechas y control
    fecha_entrega       DATE,
    activa              INTEGER NOT NULL DEFAULT 1,
    fecha               TEXT DEFAULT (date('now')),
    registrado_por      TEXT,
    creado              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_creacion      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_act_eval_docente
    ON actividades_evaluacion(docente_id, materia, periodo);
CREATE INDEX IF NOT EXISTS idx_act_eval_materia_id
    ON actividades_evaluacion(materia_id, periodo, anio_escolar_id);

-- ────────────────────────────────────────────────
-- 4. MIGRAR datos a actividades_evaluacion nueva
-- ────────────────────────────────────────────────
INSERT INTO actividades_evaluacion (
    id, docente_id, materia_id, materia, grado, mencion,
    periodo, anio_escolar_id, anio_escolar,
    tipo, titulo, descripcion,
    planificacion_id, competencias,
    valor_puntos, calificacion, peso, max_puntos, observaciones,
    activa, fecha, registrado_por, creado, fecha_creacion
)
SELECT
    id,
    profesor_id,                    -- docente_id
    NULL,                           -- materia_id (sin tabla materias aún)
    materia,
    grado,
    COALESCE(mencion, 'MULTIMEDIA'),
    CASE periodo
        WHEN 'P1' THEN 1 WHEN 'P2' THEN 2
        WHEN 'P3' THEN 3 WHEN 'P4' THEN 4
        ELSE CAST(REPLACE(COALESCE(periodo,''), 'P', '') AS INTEGER)
    END,
    1,                              -- anio_escolar_id → año seeded (2025-2026)
    anio_escolar,
    CASE tipo
        WHEN 'prueba_corta'   THEN 'prueba'
        WHEN 'prueba_parcial' THEN 'prueba'
        WHEN 'examen'         THEN 'prueba'
        WHEN 'tarea'          THEN 'tarea'
        WHEN 'proyecto'       THEN 'proyecto'
        WHEN 'participacion'  THEN 'participacion'
        WHEN 'exposicion'     THEN 'exposicion'
        ELSE 'otro'
    END,
    titulo,
    descripcion,
    NULL,                           -- planificacion_id
    competencias,
    CAST(COALESCE(peso, 10) AS INTEGER),
    calificacion,
    peso,
    max_puntos,
    observaciones,
    1,
    fecha,
    registrado_por,
    creado,
    COALESCE(fecha_creacion, creado)
FROM actividades_evaluacion_old;

-- ────────────────────────────────────────────────
-- 5. TABLA: notas_actividad (NUEVA — schema completo)
-- ────────────────────────────────────────────────
CREATE TABLE notas_actividad (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    actividad_id        INTEGER NOT NULL,
    est_id              INTEGER NOT NULL,
    nota                REAL,
    puntuacion_obtenida REAL,
    puntuacion_maxima   REAL,
    observacion         TEXT,
    fecha_registro      DATETIME DEFAULT CURRENT_TIMESTAMP,
    creado_en           TEXT DEFAULT (datetime('now')),
    UNIQUE(actividad_id, est_id)
);

-- ────────────────────────────────────────────────
-- 6. MIGRAR datos a notas_actividad nueva
-- ────────────────────────────────────────────────
INSERT INTO notas_actividad (
    id, actividad_id, est_id, nota, puntuacion_obtenida, creado_en
)
SELECT
    id,
    actividad_id,
    estudiante_id,      -- est_id
    nota,
    nota,               -- puntuacion_obtenida = nota anterior
    creado_en
FROM notas_actividad_old;

-- ────────────────────────────────────────────────
-- 7. TABLA: registro_notas_periodo (NUEVA)
-- ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS registro_notas_periodo (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    est_id              INTEGER NOT NULL,
    materia_id          INTEGER,
    materia             TEXT,
    docente_id          INTEGER NOT NULL,
    anio_escolar_id     INTEGER NOT NULL DEFAULT 1,
    anio_escolar        TEXT,
    periodo             INTEGER NOT NULL CHECK(periodo BETWEEN 1 AND 4),
    nota_calculada      REAL,
    nota_manual         REAL,
    total_pts_posibles  INTEGER,
    total_pts_obtenidos REAL,
    cerrado             INTEGER NOT NULL DEFAULT 0,
    fecha_cierre        DATETIME,
    observacion         TEXT,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(est_id, materia, docente_id, anio_escolar_id, periodo)
);

CREATE INDEX IF NOT EXISTS idx_rnp_est
    ON registro_notas_periodo(est_id, anio_escolar_id);
CREATE INDEX IF NOT EXISTS idx_rnp_materia
    ON registro_notas_periodo(materia, periodo, anio_escolar_id);

-- ────────────────────────────────────────────────
-- 8. TABLA: proyectos_evaluacion (NUEVA)
-- ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS proyectos_evaluacion (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    actividad_id          INTEGER NOT NULL UNIQUE,
    descripcion_extendida TEXT,
    rubrica               TEXT,
    archivo_adjunto       TEXT,
    created_at            DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (actividad_id) REFERENCES actividades_evaluacion(id) ON DELETE CASCADE
);

COMMIT;
PRAGMA foreign_keys = ON;
