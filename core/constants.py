# -*- coding: utf-8 -*-
"""Constantes puras del sistema Axula — sin código ejecutable."""

import os

# En Render: DATABASE_PATH=/data/database.db (disco persistente)
# En local:  database.db (raíz del proyecto)
DATABASE  = os.environ.get("DATABASE_PATH", "database.db")
FOTOS_DIR = os.environ.get("FOTOS_DIR", os.path.join("static", "fotos"))

# ── JERARQUÍA DE ROLES ──────────────────────────────────────
#
#  directora                → todo sin excepción (funciones exclusivas)
#  coordinador_general      → casi todo, sin funciones de dirección, ve ambos ciclos
#  coordinador_primer/segundo_ciclo → su ciclo, sin funciones de dirección
#  psicologa_primer/segundo_ciclo   → su ciclo, solo orientación
#  profesor / secretaria / digitador / finanzas → sus secciones propias
#
ROLES_DIRECTORA = {"directora", "superusuario"}          # funciones exclusivas de dirección
ROLES_SUPER     = {"directora", "coordinador_general", "superusuario"}  # ven ambos ciclos
ROLES_COORD     = {                                      # todo el nivel coordinación
    "directora", "coordinador_general",
    "coordinador_primer_ciclo", "coordinador_segundo_ciclo",
    "superusuario",
}
ROLES_ADMIN     = ROLES_COORD                            # alias histórico (no usar nuevo código)
ROLES_PSICOLOGA = {"psicologa_primer_ciclo", "psicologa_segundo_ciclo"}

ROLES_DISPONIBLES = {
    "superusuario":               "Super Usuario",
    "directora":                  "Directora",
    "coordinador_general":        "Coordinador General",
    "coordinador_primer_ciclo":   "Coordinador 1er Ciclo",
    "coordinador_segundo_ciclo":  "Coordinador 2do Ciclo",
    "psicologa_primer_ciclo":     "Psicóloga 1er Ciclo",
    "psicologa_segundo_ciclo":    "Psicóloga 2do Ciclo",
    "profesor":                   "Profesor/a",
    "secretaria":                 "Secretaria",
    "secretaria_docente":         "Secretaria Docente",
    "digitador":                  "Digitador/a",
    "auxiliar_contabilidad":      "Auxiliar Contabilidad",
    "suministros":                "Encargado/a Suministros",
    "asistente_directora":        "Asistente de Dirección",
    "padre":                      "Padre/Madre/Tutor",
}

DOMINIOS_INSTITUCIONALES = {"educacion.edu.do", "minerd.gob.do", "minerd.edu.do"}

_CACHE_TTL = 90  # segundos

PLAN_ARTES = {
    "MULTIMEDIA": {
        "4to": [
            ("Identidad, Cultura y Emprendimiento", 2),
            ("Historia del Arte Universal y la Estética Digital", 4),
            ("Lenguaje Musical", 2), ("Lenguaje Danzario y Teatral", 2),
            ("Lenguaje Visual, Dibujo y Creación de Personajes", 5),
            ("Diseño Básico y Expresión Visual", 4), ("Fotografía", 4),
            ("Lengua Española", 3), ("Inglés", 4), ("Matemática", 3),
            ("Ciencias Sociales", 2), ("Ciencias de la Naturaleza", 3),
            ("Formación Integral Humana y Religiosa", 1), ("Educación Física", 1),
        ],
        "5to": [
            ("Diseño Web", 6), ("Diseño Gráfico", 4), ("Publicidad y Creatividad", 3),
            ("Operación de Cámara de Video", 4), ("Guión", 4), ("Medios de Comunicación", 2),
            ("Lengua Española", 3), ("Inglés", 4), ("Matemática", 3),
            ("Ciencias Sociales", 2), ("Ciencias de la Naturaleza", 3),
            ("Formación Integral Humana y Religiosa", 1), ("Educación Física", 1),
        ],
        "6to": [
            ("Redes Sociales", 2), ("Producción Audiovisual", 4), ("Videoarte", 5),
            ("Animación", 4), ("Edición, Sonido y Musicalización", 4),
            ("Producción de Proyecto Emprendedor", 4),
            ("Lengua Española", 3), ("Inglés", 4), ("Matemática", 3),
            ("Ciencias Sociales", 2), ("Ciencias de la Naturaleza", 3),
            ("Formación Integral Humana y Religiosa", 1), ("Educación Física", 1),
        ],
    },
    "ARTES VISUALES": {
        "4to": [
            ("Identidad, Cultura y Emprendimiento", 2), ("Historia del Arte Universal", 4),
            ("Lenguaje Plástico y Visual", 6), ("Dibujo Técnico y Artístico", 4),
            ("Pintura y Técnicas Mixtas", 4),
            ("Lengua Española", 3), ("Inglés", 4), ("Matemática", 3),
            ("Ciencias Sociales", 2), ("Ciencias de la Naturaleza", 3),
            ("Formación Integral Humana y Religiosa", 1), ("Educación Física", 1),
        ],
        "5to": [
            ("Escultura y Cerámica", 5), ("Grabado y Serigrafía", 4),
            ("Diseño y Comunicación Visual", 4), ("Fotografía Artística", 3),
            ("Apreciación del Arte Dominicano y del Caribe", 3),
            ("Lengua Española", 3), ("Inglés", 4), ("Matemática", 3),
            ("Ciencias Sociales", 2), ("Ciencias de la Naturaleza", 3),
            ("Formación Integral Humana y Religiosa", 1), ("Educación Física", 1),
        ],
        "6to": [
            ("Arte Digital y Multimedia", 4), ("Gestión y Producción Artística", 4),
            ("Proyecto de Producción en Artes Visuales", 6),
            ("Taller de Restauración y Patrimonio", 3),
            ("Lengua Española", 3), ("Inglés", 4), ("Matemática", 3),
            ("Ciencias Sociales", 2), ("Ciencias de la Naturaleza", 3),
            ("Formación Integral Humana y Religiosa", 1), ("Educación Física", 1),
        ],
    },
    "MÚSICA": {
        "4to": [
            ("Identidad, Cultura y Emprendimiento", 2), ("Historia de la Música Universal", 4),
            ("Teoría y Solfeo", 4), ("Instrumento Principal I", 6),
            ("Coro y Conjunto Musical I", 3),
            ("Lengua Española", 3), ("Inglés", 4), ("Matemática", 3),
            ("Ciencias Sociales", 2), ("Ciencias de la Naturaleza", 3),
            ("Formación Integral Humana y Religiosa", 1), ("Educación Física", 1),
        ],
        "5to": [
            ("Instrumento Principal II", 6), ("Armonía y Contrapunto", 4),
            ("Coro y Conjunto Musical II", 3), ("Música Dominicana y del Caribe", 3),
            ("Composición y Arreglos Básicos", 4),
            ("Lengua Española", 3), ("Inglés", 4), ("Matemática", 3),
            ("Ciencias Sociales", 2), ("Ciencias de la Naturaleza", 3),
            ("Formación Integral Humana y Religiosa", 1), ("Educación Física", 1),
        ],
        "6to": [
            ("Instrumento Principal III", 6), ("Producción Musical Digital", 5),
            ("Dirección Coral y Orquestal", 3), ("Proyecto Musical Emprendedor", 4),
            ("Música de Cámara", 2),
            ("Lengua Española", 3), ("Inglés", 4), ("Matemática", 3),
            ("Ciencias Sociales", 2), ("Ciencias de la Naturaleza", 3),
            ("Formación Integral Humana y Religiosa", 1), ("Educación Física", 1),
        ],
    },
    "TEATRO": {
        "4to": [
            ("Identidad, Cultura y Emprendimiento", 2), ("Historia del Teatro Universal", 4),
            ("Expresión Corporal y Movimiento Escénico", 4), ("Técnica Vocal y Dicción", 3),
            ("Actuación I — Técnicas Básicas", 6),
            ("Lengua Española", 3), ("Inglés", 4), ("Matemática", 3),
            ("Ciencias Sociales", 2), ("Ciencias de la Naturaleza", 3),
            ("Formación Integral Humana y Religiosa", 1), ("Educación Física", 1),
        ],
        "5to": [
            ("Actuación II — Stanislavski y Métodos", 6), ("Dramaturgia y Guión Teatral", 4),
            ("Escenografía e Iluminación", 3), ("Teatro Dominicano y del Caribe", 3),
            ("Montaje Teatral I", 4),
            ("Lengua Española", 3), ("Inglés", 4), ("Matemática", 3),
            ("Ciencias Sociales", 2), ("Ciencias de la Naturaleza", 3),
            ("Formación Integral Humana y Religiosa", 1), ("Educación Física", 1),
        ],
        "6to": [
            ("Actuación III — Proyecto Escénico", 6), ("Dirección Teatral", 4),
            ("Gestión Cultural y Producción Teatral", 3), ("Montaje Teatral II — Obra Final", 5),
            ("Lengua Española", 3), ("Inglés", 4), ("Matemática", 3),
            ("Ciencias Sociales", 2), ("Ciencias de la Naturaleza", 3),
            ("Formación Integral Humana y Religiosa", 1), ("Educación Física", 1),
        ],
    },
    "DANZA": {
        "4to": [
            ("Identidad, Cultura y Emprendimiento", 2), ("Historia de la Danza Universal", 4),
            ("Técnica de Danza Clásica I", 5), ("Técnica de Danza Folklórica Dominicana I", 4),
            ("Expresión Corporal y Acondicionamiento Físico", 3),
            ("Lengua Española", 3), ("Inglés", 4), ("Matemática", 3),
            ("Ciencias Sociales", 2), ("Ciencias de la Naturaleza", 3),
            ("Formación Integral Humana y Religiosa", 1), ("Educación Física", 1),
        ],
        "5to": [
            ("Técnica de Danza Clásica II", 5), ("Técnica de Danza Moderna y Contemporánea", 4),
            ("Técnica de Danza Folklórica II", 3), ("Composición Coreográfica I", 4),
            ("Música Aplicada a la Danza", 2),
            ("Lengua Española", 3), ("Inglés", 4), ("Matemática", 3),
            ("Ciencias Sociales", 2), ("Ciencias de la Naturaleza", 3),
            ("Formación Integral Humana y Religiosa", 1), ("Educación Física", 1),
        ],
        "6to": [
            ("Técnica de Danza Clásica III", 5), ("Composición Coreográfica II — Proyecto Final", 5),
            ("Gestión y Producción en Danza", 3), ("Danza Urbana y Contemporánea", 3),
            ("Montaje y Puesta en Escena", 4),
            ("Lengua Española", 3), ("Inglés", 4), ("Matemática", 3),
            ("Ciencias Sociales", 2), ("Ciencias de la Naturaleza", 3),
            ("Formación Integral Humana y Religiosa", 1), ("Educación Física", 1),
        ],
    },
    # Primer Ciclo — mismo plan para todas las menciones (1ro, 2do, 3ro)
    # Las materias técnicas son: Educación Artística e Idioma Francés
    "PRIMER_CICLO": {
        "1ro": [
            ("Lengua Española", 7), ("Idioma Inglés", 4), ("Idioma Francés", 3),
            ("Matemática", 6), ("Ciencias Sociales", 3), ("Ciencias de la Naturaleza", 4),
            ("Educación Artística", 3), ("Educación Física", 3),
            ("Formación Integral Humana y Religiosa", 2),
        ],
        "2do": [
            ("Lengua Española", 7), ("Idioma Inglés", 4), ("Idioma Francés", 3),
            ("Matemática", 6), ("Ciencias Sociales", 3), ("Ciencias de la Naturaleza", 4),
            ("Educación Artística", 3), ("Educación Física", 3),
            ("Formación Integral Humana y Religiosa", 2),
        ],
        "3ro": [
            ("Lengua Española", 7), ("Idioma Inglés", 4), ("Idioma Francés", 3),
            ("Matemática", 6), ("Ciencias Sociales", 3), ("Ciencias de la Naturaleza", 4),
            ("Educación Artística", 3), ("Educación Física", 3),
            ("Formación Integral Humana y Religiosa", 2),
        ],
    },
}


COLUMNAS_ESTUDIANTES = [
    # — Identificación —
    ("id_evaluacion",     "TEXT",    "''"),
    ("cedula",            "TEXT",    "''"),
    ("grado",             "TEXT",    "'4to'"),
    ("condicion",         "TEXT",    "'ACTIVO'"),
    ("edad",              "REAL",    0),
    # — Comportamiento (indicadores académicos) —
    ("puntualidad",       "REAL",    0),
    ("tareas",            "REAL",    0),
    ("participacion",     "REAL",    0),
    ("comprension",       "REAL",    0),
    ("rendimiento",       "REAL",    0),
    # — Fotografía por período —
    ("fotografia_p1",     "REAL",    0), ("fotografia_p2", "REAL", 0),
    ("fotografia_p3",     "REAL",    0), ("fotografia_p4", "REAL", 0),
    # — Lenguaje Visual por período —
    ("lv_p1",             "REAL",    0), ("lv_p2",         "REAL", 0),
    ("lv_p3",             "REAL",    0), ("lv_p4",         "REAL", 0),
    # — Diseño por período —
    ("diseno_p1",         "REAL",    0), ("diseno_p2",     "REAL", 0),
    ("diseno_p3",         "REAL",    0), ("diseno_p4",     "REAL", 0),
    # — Asistencia por período —
    ("asistencia_p1",     "REAL",    0), ("asistencia_p2", "REAL", 0),
    ("asistencia_p3",     "REAL",    0), ("asistencia_p4", "REAL", 0),
    # — Promedios académicos por período —
    ("acad_p1",           "REAL",    0), ("acad_p2",       "REAL", 0),
    ("acad_p3",           "REAL",    0), ("acad_p4",       "REAL", 0),
    # — Promedios finales —
    ("p_acad",            "REAL",    0),
    ("p_cond",            "REAL",    0),
    ("p_auto",            "REAL",    0),
    ("p_emocional",       "REAL",    0),
    ("p_foto",            "REAL",    0),
    ("p_lv",              "REAL",    0),
    ("p_diseno",          "REAL",    0),
    ("prom_modulos",      "REAL",    0),
    ("asistencia",        "REAL",    0),
    # — Conductuales —
    ("interrupciones",    "REAL",    0),
    ("uso_celular",       "TEXT",    "''"),
    ("conflictos",        "REAL",    0),
    ("desafia_autoridad", "REAL",    0),
    ("distraccion",       "REAL",    0),
    ("falta_respeto",     "REAL",    0),
    # — Emocionales —
    ("motivacion",        "REAL",    0),
    ("estado_emocional",  "REAL",    0),
    ("interes_futuro",    "REAL",    0),
    ("apoyo_familiar",    "REAL",    0),
    # — Análisis y riesgo —
    ("indice_riesgo",     "REAL",    0),
    ("nivel_riesgo",      "TEXT",    "''"),
    ("categoria",         "TEXT",    "''"),
    ("reporte",           "TEXT",    "''"),
    ("color",             "TEXT",    "''"),
    ("silencioso",        "INTEGER", 0),
    ("proyeccion",        "REAL",    0),
    ("tendencia",         "TEXT",    "''"),
    ("ia_analisis",       "TEXT",    "NULL"),
    ("cluster_id",        "INTEGER", "NULL"),
    ("cluster_label",     "TEXT",    "NULL"),
    ("cluster_color",     "TEXT",    "NULL"),
    ("cluster_score",     "REAL",    "NULL"),
    # — Foto de perfil —
    ("foto_path",         "TEXT",    "NULL"),
    # — Notas del coordinador —
    ("notas_coord",       "TEXT",    "NULL"),
    # — Ciclo y sección (primer ciclo 1ro-3ro, segundo ciclo 4to-6to) —
    ("ciclo",             "TEXT",    "'segundo_ciclo'"),
    ("seccion",           "TEXT",    "'A'"),
    ("tiene_notas",       "INTEGER", 0),
    # — Mención —
    ("mencion",           "TEXT",    "NULL"),
    # ── MÚSICA — Módulos técnicos ────────────────────────────────────────────
    ("instrumento_p1",     "REAL",    0), ("instrumento_p2",     "REAL", 0),
    ("instrumento_p3",     "REAL",    0), ("instrumento_p4",     "REAL", 0),
    ("p_instrumento",      "REAL",    0),
    ("canto_p1",           "REAL",    0), ("canto_p2",           "REAL", 0),
    ("canto_p3",           "REAL",    0), ("canto_p4",           "REAL", 0),
    ("p_canto",            "REAL",    0),
    ("lenguaje_musical_p1","REAL",    0), ("lenguaje_musical_p2","REAL", 0),
    ("lenguaje_musical_p3","REAL",    0), ("lenguaje_musical_p4","REAL", 0),
    ("p_lenguaje_musical", "REAL",    0),
    # ── TEATRO — Módulos técnicos ────────────────────────────────────────────
    ("entrenamiento_p1",   "REAL",    0), ("entrenamiento_p2",   "REAL", 0),
    ("entrenamiento_p3",   "REAL",    0), ("entrenamiento_p4",   "REAL", 0),
    ("p_entrenamiento",    "REAL",    0),
    ("expresion_p1",       "REAL",    0), ("expresion_p2",       "REAL", 0),
    ("expresion_p3",       "REAL",    0), ("expresion_p4",       "REAL", 0),
    ("p_expresion",        "REAL",    0),
    ("historia_teatro_p1", "REAL",    0), ("historia_teatro_p2", "REAL", 0),
    ("historia_teatro_p3", "REAL",    0), ("historia_teatro_p4", "REAL", 0),
    ("p_historia_teatro",  "REAL",    0),
    # ── ARTES VISUALES — Módulos técnicos ───────────────────────────────────
    ("dibujo_p1",          "REAL",    0), ("dibujo_p2",          "REAL", 0),
    ("dibujo_p3",          "REAL",    0), ("dibujo_p4",          "REAL", 0),
    ("p_dibujo",           "REAL",    0),
    ("pintura_p1",         "REAL",    0), ("pintura_p2",         "REAL", 0),
    ("pintura_p3",         "REAL",    0), ("pintura_p4",         "REAL", 0),
    ("p_pintura",          "REAL",    0),
    ("historia_arte_p1",   "REAL",    0), ("historia_arte_p2",   "REAL", 0),
    ("historia_arte_p3",   "REAL",    0), ("historia_arte_p4",   "REAL", 0),
    ("p_historia_arte",    "REAL",    0),
    # ← AGREGA COLUMNAS NUEVAS AQUÍ — se crean solas al reiniciar Flask
]

# ── 2. TABLAS NUEVAS (se crean si no existen) ────────────────────────────────
# Agrega el CREATE TABLE IF NOT EXISTS de cada tabla nueva aquí.

TABLAS_NUEVAS = [
    # — Registro oficial del liceo (identidad por cédula) —
    """
    CREATE TABLE IF NOT EXISTS registro_liceo (
        cedula          TEXT PRIMARY KEY,
        nombre          TEXT NOT NULL,
        apellido        TEXT NOT NULL,
        sexo            TEXT,
        nacimiento      TEXT,
        edad            INTEGER,
        telefono        TEXT,
        grado           TEXT,
        mencion         TEXT,
        es_provisional  INTEGER DEFAULT 0,
        fecha_carga     TEXT DEFAULT (date('now'))
    )
    """,
    # — Historial de planificaciones docentes —
    """
    CREATE TABLE IF NOT EXISTS historial_planificaciones (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha           TEXT DEFAULT (date('now')),
        materia         TEXT,
        grado           TEXT,
        periodo         TEXT,
        tema            TEXT,
        nivel_grupo     TEXT,
        contenido       TEXT,
        estudiante_id   INTEGER,
        nombre_estudiante TEXT DEFAULT '',
        tipo            TEXT,
        profesor_id     INTEGER
    )
    """,
    # — Calificaciones dinámicas por materia (cualquier materia, cualquier grado) —
    """
    CREATE TABLE IF NOT EXISTS materias_calificaciones (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        estudiante_id INTEGER NOT NULL,
        cedula        TEXT,
        materia       TEXT NOT NULL,
        grado         TEXT,
        p1            REAL DEFAULT 0,
        p2            REAL DEFAULT 0,
        p3            REAL DEFAULT 0,
        p4            REAL DEFAULT 0,
        promedio      REAL DEFAULT 0,
        tipo          TEXT DEFAULT 'académico',
        ciclo         TEXT DEFAULT 'segundo_ciclo',
        fuente        TEXT,
        profesor      TEXT,
        fecha_carga   TEXT DEFAULT (date('now')),
        UNIQUE(estudiante_id, materia)
    )
    """,
    # — Expedientes históricos (digitalización de archivos físicos 25+ años) —
    """
    CREATE TABLE IF NOT EXISTS expedientes_historicos (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        -- Identificación del estudiante
        cedula              TEXT,
        nombre              TEXT NOT NULL,
        apellido            TEXT NOT NULL,
        fecha_nacimiento    TEXT,
        estudiante_id       INTEGER,          -- vinculado a estudiantes activos si aplica
        -- Datos académicos del año
        anio_escolar        TEXT NOT NULL,    -- ej: "2000-2001", "2016-2017"
        grado               TEXT NOT NULL,    -- ej: "1ro Bachiller", "4to Secundaria"
        sistema_educativo   TEXT NOT NULL,    -- 'bachillerato' | 'secundaria'
        seccion             TEXT,
        mencion             TEXT,
        centro_educativo    TEXT DEFAULT 'Centro Educativo en Artes Benito Juárez',
        es_externo          INTEGER DEFAULT 0,  -- 1 = viene de otro centro
        -- Notas (JSON: [{materia, p1, p2, p3, p4, promedio, tipo}])
        materias_json       TEXT NOT NULL DEFAULT '[]',
        promedio_general    REAL,
        condicion           TEXT,             -- 'Aprobado','Reprobado','Promovido'
        -- Metadatos de digitación
        fuente              TEXT DEFAULT 'manual',  -- 'manual' | 'excel'
        digitado_por        INTEGER,
        fecha_digitacion    TEXT DEFAULT (date('now')),
        observaciones       TEXT,
        validado            INTEGER DEFAULT 0,
        validado_por        INTEGER,
        FOREIGN KEY (estudiante_id) REFERENCES estudiantes(id),
        FOREIGN KEY (digitado_por)  REFERENCES usuarios(id)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_exp_hist_nombre
    ON expedientes_historicos(LOWER(apellido), LOWER(nombre))
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_exp_hist_cedula
    ON expedientes_historicos(cedula) WHERE cedula IS NOT NULL
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_exp_hist_estudiante
    ON expedientes_historicos(estudiante_id) WHERE estudiante_id IS NOT NULL
    """,
    # — Cache semántico de IA (reutilización de planificaciones y respuestas) —
    """
    CREATE TABLE IF NOT EXISTS ia_cache (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        tipo            TEXT NOT NULL,      -- 'planificacion','asignacion','estrategia','rubrica','abp'
        grado           TEXT,
        materia         TEXT,
        periodo         TEXT,
        tema            TEXT,
        nivel_grupo     TEXT,
        parametros_json TEXT,               -- JSON con todos los params de la solicitud
        contenido       TEXT NOT NULL,      -- respuesta completa del LLM
        tokens_usados   INTEGER DEFAULT 0,
        usos            INTEGER DEFAULT 1,  -- cuántas veces se reutilizó
        creado_por      INTEGER,
        creado_en       TEXT DEFAULT (datetime('now')),
        ultimo_uso      TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (creado_por) REFERENCES usuarios(id)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_ia_cache_lookup
    ON ia_cache(tipo, grado, materia)
    """,
    # — Mapeos de columnas recordados por archivo/maestro —
    """
    CREATE TABLE IF NOT EXISTS mapeos_excel (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre_archivo  TEXT,
        materia         TEXT,
        col_nombre      TEXT,
        col_apellido    TEXT,
        col_nombre_completo TEXT,
        col_p1          TEXT,
        col_p2          TEXT,
        col_p3          TEXT,
        col_p4          TEXT,
        fecha_uso   TEXT DEFAULT (date('now')),
        UNIQUE(nombre_archivo)
    )
    """,
    # ── REPORTES (conducta, psicológico, académico, incidente) ──────────────
    """
    CREATE TABLE IF NOT EXISTS reportes (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        estudiante_id   INTEGER NOT NULL,
        tipo            TEXT NOT NULL,
        subtipo         TEXT,
        titulo          TEXT,
        descripcion     TEXT NOT NULL,
        severidad       TEXT DEFAULT 'Media',
        reportado_por   TEXT,
        fecha           TEXT DEFAULT (date('now')),
        estado          TEXT DEFAULT 'Abierto',
        seguimiento     TEXT,
        fecha_cierre    TEXT,
        FOREIGN KEY (estudiante_id) REFERENCES estudiantes(id)
    )
    """,
    # ── PATRONES ML ──────────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS ml_clusters (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha_calculo   TEXT DEFAULT (datetime('now')),
        n_clusters      INTEGER,
        features_usadas TEXT,
        resumen         TEXT
    )
    """,
    # ── USUARIOS (login) ─────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS usuarios (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        username    TEXT UNIQUE NOT NULL,
        email       TEXT,
        password    TEXT NOT NULL,
        nombre      TEXT NOT NULL,
        rol         TEXT NOT NULL DEFAULT 'profesor',
        materia     TEXT,
        grado       TEXT,
        mencion     TEXT,
        asignaturas TEXT,
        activo      INTEGER DEFAULT 1,
        creado      TEXT DEFAULT (date('now'))
    )
    """,
    # ── ASISTENCIA ──────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS asistencia (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        estudiante_id   INTEGER NOT NULL,
        profesor_id     INTEGER NOT NULL,
        materia         TEXT NOT NULL,
        fecha           TEXT NOT NULL,
        periodo         INTEGER NOT NULL DEFAULT 1,
        estado          TEXT NOT NULL DEFAULT 'presente',
        horas_clase     INTEGER NOT NULL DEFAULT 1,
        observacion     TEXT,
        FOREIGN KEY (estudiante_id) REFERENCES estudiantes(id),
        FOREIGN KEY (profesor_id) REFERENCES usuarios(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS calificaciones_periodo (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        estudiante_id   INTEGER NOT NULL,
        profesor_id     INTEGER NOT NULL,
        materia         TEXT NOT NULL,
        periodo         TEXT NOT NULL,
        calificacion    REAL NOT NULL,
        anio_escolar    TEXT NOT NULL,
        observacion     TEXT,
        creado          TEXT DEFAULT (datetime('now')),
        actualizado     TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (estudiante_id) REFERENCES estudiantes(id),
        FOREIGN KEY (profesor_id)   REFERENCES usuarios(id),
        UNIQUE (estudiante_id, materia, periodo, anio_escolar)
    )
    """,
    # ── TOKENS DE RECUPERACIÓN DE CONTRASEÑA ─────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS recovery_tokens (
        token       TEXT PRIMARY KEY,
        user_id     INTEGER NOT NULL,
        expires     TEXT NOT NULL,
        creado_en   TEXT DEFAULT (datetime('now'))
    )
    """,
    # ── LOGROS Y RECONOCIMIENTOS ─────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS logros (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        estudiante_id   INTEGER NOT NULL,
        tipo            TEXT DEFAULT 'reconocimiento',
        titulo          TEXT NOT NULL,
        descripcion     TEXT,
        fecha           TEXT,
        registrado_por  TEXT,
        creado          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (estudiante_id) REFERENCES estudiantes(id)
    )
    """,
    # ── PERÍODOS BLOQUEADOS (cierre de calificaciones) ──────────────────
    """
    CREATE TABLE IF NOT EXISTS periodos_bloqueados (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        periodo         TEXT NOT NULL,          -- 'P1','P2','P3','P4'
        anio_escolar    TEXT NOT NULL,
        bloqueado_por   INTEGER NOT NULL,       -- FK usuarios.id
        bloqueado_en    TEXT DEFAULT (datetime('now')),
        motivo          TEXT DEFAULT 'Cierre de período',
        UNIQUE(periodo, anio_escolar)
    )
    """,
    # ── ASIGNACIONES (tareas, exámenes, proyectos) ────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS asignaciones (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        profesor_id     INTEGER NOT NULL,
        materia         TEXT NOT NULL,
        grado           TEXT NOT NULL,
        mencion         TEXT NOT NULL DEFAULT 'MULTIMEDIA',
        tipo            TEXT NOT NULL DEFAULT 'tarea',   -- 'tarea','examen','proyecto'
        titulo          TEXT NOT NULL,
        descripcion     TEXT,
        criterios       TEXT,                           -- JSON: [{nombre, puntaje_max, descripcion}]
        puntaje_total   REAL DEFAULT 100,
        fecha_asignacion TEXT DEFAULT (date('now')),
        fecha_entrega   TEXT,
        periodo         TEXT DEFAULT 'P1',              -- P1..P4
        estado          TEXT DEFAULT 'borrador',        -- 'borrador','publicada','cerrada'
        creado_en       TEXT DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS entregas_asignacion (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        asignacion_id   INTEGER NOT NULL,
        estudiante_id   INTEGER NOT NULL,
        nota            REAL,
        observacion     TEXT,
        entregado       INTEGER DEFAULT 1,
        calificado_en   TEXT DEFAULT (datetime('now')),
        UNIQUE(asignacion_id, estudiante_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS notas_actividad (
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
    )
    """,
    # ── RECUPERACIONES PEDAGÓGICAS (Ord.04-2023 Art.28) ─────────────────────────
    """
    CREATE TABLE IF NOT EXISTS recuperaciones_pedagogicas (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        estudiante_id       INTEGER NOT NULL,
        materia             TEXT NOT NULL,
        anio_escolar        TEXT NOT NULL,
        nota_recuperacion   REAL,     -- 1ra oportunidad: < 70 → actividades complementarias
        nota_completiva     REAL,     -- 2da: evaluación completiva al final del año (peso 50%)
        nota_extraordinaria REAL,     -- 3ra: evaluación extraordinaria antes del nuevo año
        nota_final_ajustada REAL,     -- calculada automáticamente
        observacion         TEXT,
        registrado_por      INTEGER,  -- FK usuarios.id
        actualizado         TEXT DEFAULT (datetime('now')),
        UNIQUE(estudiante_id, materia, anio_escolar)
    )
    """,
    # ── PORTAL DE PADRES — vínculos padre↔estudiante ────────────────────────
    """
    CREATE TABLE IF NOT EXISTS vinculos_padre_estudiante (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        padre_id        INTEGER NOT NULL,  -- FK usuarios.id (rol='padre')
        estudiante_id   INTEGER NOT NULL,  -- FK estudiantes.id
        parentesco      TEXT DEFAULT 'padre/madre',  -- padre, madre, tutor, abuelo, etc.
        creado          TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (padre_id)     REFERENCES usuarios(id),
        FOREIGN KEY (estudiante_id) REFERENCES estudiantes(id),
        UNIQUE(padre_id, estudiante_id)
    )
    """,
    # ── HISTORIAL DE CAMBIOS (Audit Log) ─────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS audit_log (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id      INTEGER,           -- quién hizo el cambio
        usuario_nombre  TEXT,              -- nombre en el momento (por si se borra)
        accion          TEXT NOT NULL,     -- 'calificacion', 'asistencia', 'usuario', 'recuperacion', etc.
        entidad         TEXT,              -- 'calificaciones_periodo', 'estudiantes', etc.
        entidad_id      INTEGER,           -- id del registro afectado
        descripcion     TEXT,              -- texto legible: "Cambió nota de Matemáticas P2: 75 → 82"
        valor_anterior  TEXT,              -- JSON del estado anterior
        valor_nuevo     TEXT,              -- JSON del nuevo estado
        ip              TEXT,              -- IP del cliente
        creado          TEXT DEFAULT (datetime('now'))
    )
    """,
    # ── NOTIFICACIONES ────────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS notificaciones (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        destinatario_id INTEGER NOT NULL,  -- FK usuarios.id (coordinador/directora)
        tipo            TEXT NOT NULL,     -- 'riesgo_nota','riesgo_asistencia','caso_nuevo','sistema'
        titulo          TEXT NOT NULL,
        mensaje         TEXT NOT NULL,
        url             TEXT,              -- link al perfil/sección relevante
        leida           INTEGER DEFAULT 0,
        creado          TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (destinatario_id) REFERENCES usuarios(id)
    )
    """,
    # ── CONFIGURACIÓN DEL CENTRO (membrete, logo, contacto) ─────────────────
    """
    CREATE TABLE IF NOT EXISTS configuracion_centro (
        id          INTEGER PRIMARY KEY DEFAULT 1,
        nombre      TEXT DEFAULT 'Centro Educativo en Artes Benito Juárez',
        modalidad   TEXT DEFAULT 'Modalidad en Artes · Nivel Secundario',
        direccion   TEXT DEFAULT 'Prolongación Ovando, Cristo Rey, Santo Domingo, D.N.',
        pais        TEXT DEFAULT 'República Dominicana',
        telefono    TEXT DEFAULT '(809) 563-0241',
        email       TEXT DEFAULT 'centroenartesbenitojuarez@gmail.com',
        logo_base64 TEXT,
        actualizado TEXT DEFAULT (datetime('now'))
    )
    """,
    # ← AGREGA CREATE TABLE IF NOT EXISTS DE TABLAS NUEVAS AQUÍ
    # ── CUADERNO ANECDÓTICO ──────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS cuaderno_anecdotico (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        estudiante_id       INTEGER NOT NULL,
        autor_id            INTEGER NOT NULL,
        fecha               TEXT NOT NULL DEFAULT (date('now')),
        tipo                TEXT NOT NULL DEFAULT 'conductual',
        descripcion         TEXT NOT NULL,
        seguimiento         TEXT,
        convertido_reporte  INTEGER DEFAULT 0,
        visible_en_perfil   INTEGER DEFAULT 1,
        privado             INTEGER DEFAULT 0,
        creado_en           TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (estudiante_id) REFERENCES estudiantes(id),
        FOREIGN KEY (autor_id)      REFERENCES usuarios(id)
    )
    """,
    # ── CALENDARIO ESCOLAR ───────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS calendario_escolar (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha       TEXT NOT NULL UNIQUE,
        tipo        TEXT NOT NULL DEFAULT 'feriado',
        descripcion TEXT,
        anio_escolar TEXT DEFAULT '2025-2026',
        creado_por  INTEGER,
        creado_en   TEXT DEFAULT (datetime('now'))
    )
    """,
    # ── ASISTENCIA MENSUAL (resumen validado por el maestro) ─────────────────
    """
    CREATE TABLE IF NOT EXISTS asistencia_mensual (
        id                      INTEGER PRIMARY KEY AUTOINCREMENT,
        estudiante_id           INTEGER NOT NULL,
        profesor_id             INTEGER NOT NULL,
        materia                 TEXT NOT NULL,
        mes                     INTEGER NOT NULL,
        anio                    INTEGER NOT NULL,
        dias_habiles            INTEGER DEFAULT 0,
        dias_clase_impartidos   INTEGER DEFAULT 0,
        dias_asistio            INTEGER DEFAULT 0,
        porcentaje              REAL DEFAULT 0,
        validado                INTEGER DEFAULT 0,
        fecha_validacion        TEXT,
        observacion             TEXT,
        FOREIGN KEY (estudiante_id) REFERENCES estudiantes(id),
        FOREIGN KEY (profesor_id)   REFERENCES usuarios(id),
        UNIQUE (estudiante_id, profesor_id, materia, mes, anio)
    )
    """,
    # ── EVALUACIONES NARRATIVAS DEL PROFESOR ─────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS evaluaciones_narrativas (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        estudiante_id   INTEGER NOT NULL,
        profesor_id     INTEGER NOT NULL,
        periodo         INTEGER NOT NULL DEFAULT 1,
        anio_escolar    TEXT DEFAULT '2025-2026',
        texto           TEXT NOT NULL,
        creado_en       TEXT DEFAULT (datetime('now')),
        actualizado_en  TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (estudiante_id) REFERENCES estudiantes(id),
        FOREIGN KEY (profesor_id)   REFERENCES usuarios(id),
        UNIQUE (estudiante_id, profesor_id, periodo, anio_escolar)
    )
    """,
    # ══════════════════════════════════════════════════════════════════
    # SISTEMA DE GESTIÓN DE CASOS — AlertasTracking v1.0
    # ══════════════════════════════════════════════════════════════════

    # — Notificaciones a psicóloga/coordinación —
    """
    CREATE TABLE IF NOT EXISTS notificaciones (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        destinatario_id INTEGER NOT NULL,          -- usuario que recibe
        origen_tipo     TEXT NOT NULL,             -- 'asistencia'|'reporte'|'caso'|'sistema'
        origen_id       INTEGER,                   -- id del reporte/asistencia que la generó
        estudiante_id   INTEGER NOT NULL,
        titulo          TEXT NOT NULL,
        cuerpo          TEXT,
        leida           INTEGER DEFAULT 0,
        creada_en       TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (destinatario_id) REFERENCES usuarios(id),
        FOREIGN KEY (estudiante_id)   REFERENCES estudiantes(id)
    )
    """,

    # — Casos de seguimiento (abre psicóloga/coordinación) —
    """
    CREATE TABLE IF NOT EXISTS casos (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        estudiante_id   INTEGER NOT NULL,
        abierto_por     INTEGER NOT NULL,          -- usuario que abrió el caso
        tipo            TEXT NOT NULL,             -- 'asistencia'|'conducta'|'academico'|'familiar'
        titulo          TEXT NOT NULL,
        descripcion     TEXT,
        estado          TEXT DEFAULT 'Abierto',    -- 'Abierto'|'En seguimiento'|'Resuelto'|'Escalado'
        nivel_escala    INTEGER DEFAULT 1,         -- 1=psicóloga 2=coordinador 3=directora
        origen_tipo     TEXT,                      -- qué lo originó
        origen_id       INTEGER,
        creado_en       TEXT DEFAULT (datetime('now')),
        cerrado_en      TEXT,
        FOREIGN KEY (estudiante_id) REFERENCES estudiantes(id),
        FOREIGN KEY (abierto_por)   REFERENCES usuarios(id)
    )
    """,

    # — Acciones dentro de un caso (línea de tiempo) —
    """
    CREATE TABLE IF NOT EXISTS caso_acciones (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        caso_id         INTEGER NOT NULL,
        actor_id        INTEGER NOT NULL,          -- quién hizo la acción
        tipo_accion     TEXT NOT NULL,             -- 'nota'|'cita'|'reunion_profesor'|'reunion_coordinador'|'reunion_padres'|'escalar'|'acuerdo'|'resolucion'
        descripcion     TEXT NOT NULL,
        fecha_accion    TEXT DEFAULT (date('now')),
        fecha_programada TEXT,                     -- para citas futuras
        participantes   TEXT,                      -- JSON array de nombres
        resultado       TEXT,
        adjunto_id      INTEGER,                   -- link a acuerdo_compromiso si aplica
        creado_en       TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (caso_id)   REFERENCES casos(id),
        FOREIGN KEY (actor_id)  REFERENCES usuarios(id)
    )
    """,

    # — Acuerdo-Compromiso formal —
    """
    CREATE TABLE IF NOT EXISTS acuerdos_compromiso (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        caso_id             INTEGER,
        estudiante_id       INTEGER NOT NULL,
        generado_por        INTEGER NOT NULL,      -- psicóloga que lo generó
        fecha_acuerdo       TEXT DEFAULT (date('now')),
        numero_acuerdo      TEXT,                  -- ej: "AC-2026-001"
        compromisos_estudiante  TEXT,              -- JSON array
        compromisos_familia     TEXT,              -- JSON array
        compromisos_centro      TEXT,              -- JSON array
        base_legal          TEXT,                  -- artículos MINERD aplicados
        contenido_completo  TEXT,                  -- texto completo generado por IA
        firmado             INTEGER DEFAULT 0,
        fecha_firma         TEXT,
        observaciones       TEXT,
        creado_en           TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (caso_id)       REFERENCES casos(id),
        FOREIGN KEY (estudiante_id) REFERENCES estudiantes(id),
        FOREIGN KEY (generado_por)  REFERENCES usuarios(id)
    )
    """,

    # — Registro de ausencias semanales (para trigger de alerta) —
    """
    CREATE TABLE IF NOT EXISTS ausencias_semanales (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        estudiante_id   INTEGER NOT NULL,
        semana          TEXT NOT NULL,             -- formato ISO: 2026-W12
        total_ausencias INTEGER DEFAULT 0,
        materias        TEXT,                      -- JSON: {materia: n_ausencias}
        alerta_enviada  INTEGER DEFAULT 0,
        alerta_id       INTEGER,                   -- FK a notificaciones
        actualizado_en  TEXT DEFAULT (datetime('now')),
        UNIQUE (estudiante_id, semana),
        FOREIGN KEY (estudiante_id) REFERENCES estudiantes(id)
    )
    """,
    # ── Módulos Administrativos ──────────────────────────────────────────────
    """CREATE TABLE IF NOT EXISTS documentos_admin (
        id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT NOT NULL,
        estudiante_id INTEGER, titulo TEXT NOT NULL, contenido TEXT,
        destinatario TEXT, numero_doc TEXT,
        estado TEXT DEFAULT 'borrador', generado_por INTEGER NOT NULL,
        fecha_emision TEXT DEFAULT (date('now')), fecha_entrega TEXT,
        observaciones TEXT, creado_en TEXT DEFAULT (datetime('now')))""",
    """CREATE TABLE IF NOT EXISTS inscripciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT, estudiante_id INTEGER,
        anio_escolar TEXT NOT NULL, grado TEXT NOT NULL, mencion TEXT,
        seccion TEXT DEFAULT 'A', fecha_inscripcion TEXT DEFAULT (date('now')),
        tipo TEXT DEFAULT 'nueva', procedencia TEXT,
        documentos_entregados TEXT, monto_inscripcion REAL DEFAULT 0,
        pagado INTEGER DEFAULT 0, registrado_por INTEGER NOT NULL,
        estado TEXT DEFAULT 'activa', observaciones TEXT,
        creado_en TEXT DEFAULT (datetime('now')))""",
    """CREATE TABLE IF NOT EXISTS retiros_traslados (
        id INTEGER PRIMARY KEY AUTOINCREMENT, estudiante_id INTEGER NOT NULL,
        tipo TEXT NOT NULL, motivo TEXT, centro_destino TEXT,
        fecha_retiro TEXT DEFAULT (date('now')), documentos_entregados TEXT,
        procesado_por INTEGER NOT NULL, estado TEXT DEFAULT 'procesado',
        observaciones TEXT, creado_en TEXT DEFAULT (datetime('now')))""",
    """CREATE TABLE IF NOT EXISTS categorias_gasto (
        id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL UNIQUE,
        tipo TEXT DEFAULT 'gasto', activa INTEGER DEFAULT 1)""",
    """CREATE TABLE IF NOT EXISTS movimientos_financieros (
        id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT NOT NULL,
        categoria_id INTEGER, concepto TEXT NOT NULL, descripcion TEXT,
        monto REAL NOT NULL, fecha TEXT DEFAULT (date('now')),
        comprobante TEXT, proveedor TEXT, registrado_por INTEGER NOT NULL,
        aprobado_por INTEGER, estado TEXT DEFAULT 'registrado',
        observaciones TEXT, creado_en TEXT DEFAULT (datetime('now')))""",
    """CREATE TABLE IF NOT EXISTS presupuestos (
        id INTEGER PRIMARY KEY AUTOINCREMENT, anio_escolar TEXT NOT NULL,
        categoria_id INTEGER, concepto TEXT NOT NULL,
        monto_asignado REAL DEFAULT 0, monto_ejecutado REAL DEFAULT 0,
        estado TEXT DEFAULT 'activo', creado_por INTEGER NOT NULL,
        creado_en TEXT DEFAULT (datetime('now')))""",
    """CREATE TABLE IF NOT EXISTS permisos_personal (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL,
        fecha_desde TEXT NOT NULL,
        fecha_hasta TEXT,
        motivo_tipo TEXT NOT NULL,
        motivo_detalle TEXT,
        estado TEXT DEFAULT 'pendiente',
        registrado_por INTEGER NOT NULL,
        aprobado_por INTEGER,
        creado_en TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id))""",
    # ── ESCÁNER OCR — historial de documentos digitalizados ──────────────────
    """CREATE TABLE IF NOT EXISTS escaneos_documentos (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id      INTEGER NOT NULL,
        tipo_documento  TEXT NOT NULL DEFAULT 'otro',
        confianza       TEXT DEFAULT 'media',
        nombre_archivo  TEXT,
        texto_extraido  TEXT,
        datos_json      TEXT,
        creado_en       TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
    )""",
    # ── PROMOCIÓN DE ESTUDIANTES — Ordenanza 04-2023 MINERD ──────────────────
    """CREATE TABLE IF NOT EXISTS promociones (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        estudiante_id    INTEGER NOT NULL,
        grado_origen     TEXT    NOT NULL,
        grado_destino    TEXT    NOT NULL,
        anio_escolar     TEXT    NOT NULL,
        estado           TEXT    NOT NULL,
        mats_reprobadas  INTEGER DEFAULT 0,
        mats_total       INTEGER DEFAULT 0,
        ejecutado_por    INTEGER,
        fecha            TEXT    DEFAULT (datetime('now')),
        observacion      TEXT    DEFAULT '',
        UNIQUE(estudiante_id, anio_escolar),
        FOREIGN KEY (estudiante_id) REFERENCES estudiantes(id),
        FOREIGN KEY (ejecutado_por) REFERENCES usuarios(id)
    )""",
]


MIGRACIONES_ESPECIALES = [
    ("Agregar columna profesor a materias_calificaciones",
     "ALTER TABLE materias_calificaciones ADD COLUMN profesor TEXT",
     "profesor", "materias_calificaciones"),
    ("Agregar columna grado a usuarios",
     "ALTER TABLE usuarios ADD COLUMN grado TEXT",
     "grado", "usuarios"),
    ("Agregar columna mencion a usuarios",
     "ALTER TABLE usuarios ADD COLUMN mencion TEXT",
     "mencion", "usuarios"),
    ("Agregar columna asignaturas a usuarios",
     "ALTER TABLE usuarios ADD COLUMN asignaturas TEXT",
     "asignaturas", "usuarios"),
    ("Agregar columna tipo a materias_calificaciones",
     "ALTER TABLE materias_calificaciones ADD COLUMN tipo TEXT DEFAULT 'académico'",
     "tipo", "materias_calificaciones"),
    ("Agregar columna ciclo a materias_calificaciones",
     "ALTER TABLE materias_calificaciones ADD COLUMN ciclo TEXT DEFAULT 'segundo_ciclo'",
     "ciclo", "materias_calificaciones"),
    ("Agregar columna ciclo a usuarios",
     "ALTER TABLE usuarios ADD COLUMN ciclo TEXT",
     "ciclo", "usuarios"),
    ("Agregar columna nombre_estudiante a historial_planificaciones",
     "ALTER TABLE historial_planificaciones ADD COLUMN nombre_estudiante TEXT DEFAULT ''",
     "nombre_estudiante", "historial_planificaciones"),
    ("Agregar columna profesor_id a historial_planificaciones",
     "ALTER TABLE historial_planificaciones ADD COLUMN profesor_id INTEGER",
     "profesor_id", "historial_planificaciones"),
    ("Agregar columna tema a historial_planificaciones",
     "ALTER TABLE historial_planificaciones ADD COLUMN tema TEXT DEFAULT ''",
     "tema", "historial_planificaciones"),
    ("Agregar columna nivel_grupo a historial_planificaciones",
     "ALTER TABLE historial_planificaciones ADD COLUMN nivel_grupo TEXT DEFAULT ''",
     "nivel_grupo", "historial_planificaciones"),
    ("Agregar columna grado a historial_planificaciones",
     "ALTER TABLE historial_planificaciones ADD COLUMN grado TEXT DEFAULT ''",
     "grado", "historial_planificaciones"),
    ("Agregar columna email a usuarios",
     "ALTER TABLE usuarios ADD COLUMN email TEXT",
     "email", "usuarios"),
    ("Agregar columna tiene_notas a estudiantes",
     "ALTER TABLE estudiantes ADD COLUMN tiene_notas INTEGER DEFAULT 0",
     "tiene_notas", "estudiantes"),
    ("Agregar columna telefono a usuarios",
     "ALTER TABLE usuarios ADD COLUMN telefono TEXT",
     "telefono", "usuarios"),
    ("Agregar columna foto_perfil a usuarios",
     "ALTER TABLE usuarios ADD COLUMN foto_perfil TEXT",
     "foto_perfil", "usuarios"),
    ("Agregar columna bio a usuarios",
     "ALTER TABLE usuarios ADD COLUMN bio TEXT",
     "bio", "usuarios"),
    ("Agregar columna departamento a usuarios",
     "ALTER TABLE usuarios ADD COLUMN departamento TEXT",
     "departamento", "usuarios"),
    ("Agregar columna titulo_academico a usuarios",
     "ALTER TABLE usuarios ADD COLUMN titulo_academico TEXT",
     "titulo_academico", "usuarios"),
    ("Agregar columna fecha_ingreso a usuarios",
     "ALTER TABLE usuarios ADD COLUMN fecha_ingreso TEXT",
     "fecha_ingreso", "usuarios"),
    ("Agregar columna tipo_docencia a usuarios",
     "ALTER TABLE usuarios ADD COLUMN tipo_docencia TEXT DEFAULT 'ambas'",
     "tipo_docencia", "usuarios"),
    # ── Firmas digitales en acuerdos-compromiso ──────────────────────────────
    ("Agregar firma_tutor a acuerdos_compromiso",
     "ALTER TABLE acuerdos_compromiso ADD COLUMN firma_tutor TEXT",
     "firma_tutor", "acuerdos_compromiso"),
    ("Agregar firma_coordinador a acuerdos_compromiso",
     "ALTER TABLE acuerdos_compromiso ADD COLUMN firma_coordinador TEXT",
     "firma_coordinador", "acuerdos_compromiso"),
    ("Agregar firma_psicologa a acuerdos_compromiso",
     "ALTER TABLE acuerdos_compromiso ADD COLUMN firma_psicologa TEXT",
     "firma_psicologa", "acuerdos_compromiso"),
    ("Agregar firma_director a acuerdos_compromiso",
     "ALTER TABLE acuerdos_compromiso ADD COLUMN firma_director TEXT",
     "firma_director", "acuerdos_compromiso"),
    ("Agregar token_firma a acuerdos_compromiso",
     "ALTER TABLE acuerdos_compromiso ADD COLUMN token_firma TEXT",
     "token_firma", "acuerdos_compromiso"),
    ("Agregar entregado a entregas_asignacion",
     "ALTER TABLE entregas_asignacion ADD COLUMN entregado INTEGER DEFAULT 1",
     "entregado", "entregas_asignacion"),
    # ← AGREGA MIGRACIONES PUNTUALES AQUÍ
]


# ── CONSTANTES ADICIONALES (extraídas del monolito) ──────────────

PLAN_MULTIMEDIA = PLAN_ARTES["MULTIMEDIA"]


CURRICULUM_ARTES = {
    # ── MATERIAS TÉCNICAS MULTIMEDIA 4TO ──────────────────────────────────────
    "Fotografía": {
        "mencion": "MULTIMEDIA", "grado": "4to",
        "competencia": "DCM.1.2 — Diseño y Creatividad Multimedia",
        "descripcion": "Ejecuta el proceso del uso de la cámara fotográfica en proyectos de expresión artística aplicando técnicas novedosas y creativas.",
        "saberes_conceptuales": [
            "Historia de la fotografía y su evolución digital",
            "Componentes de la cámara: diafragma, obturador, ISO",
            "Profundidad de campo y tipos de objetivos",
            "Iluminación de estudio y natural",
            "Leyes de composición: horizonte, mirada, tercios",
            "Planos y ángulos fotográficos",
            "Manipulación de imagen digital y dispositivo móvil",
        ],
        "saberes_procedimentales": [
            "Uso correcto de la cámara fotográfica",
            "Manejo del diafragma, obturador e ISO",
            "Realización de producciones fotográficas",
            "Fotografía como medio de expresión artística",
        ],
        "indicadores_logro": [
            "Explica antecedentes y evolución de la fotografía",
            "Realiza fotografías aplicando reglas de composición",
            "Manipula correctamente cámara y dispositivo móvil",
            "Domina técnicas de iluminación en diferentes ambientes",
            "Valora la fotografía como expresión artística y comunicación",
        ],
        "evidencias": "Exposición fotográfica o portafolio digital",
        "horas": 4,
    },
    "Lenguaje_Visual": {
        "mencion": "MULTIMEDIA", "grado": "4to",
        "competencia": "AA.1.1 — Animación Artística y Comunicación Visual",
        "descripcion": "Comunica a través del lenguaje visual las características de la personalidad conceptualizada utilizando medios tradicionales y digitales.",
        "saberes_conceptuales": [
            "Formas, color, textura, composición y profundidad",
            "Figura-fondo, luz y sombras, escala y proporción",
            "Diseño de personajes y model sheet",
            "Tableta gráfica y software Photoshop",
            "Aspectos connotativos y denotativos de imágenes",
        ],
        "saberes_procedimentales": [
            "Identificar y aplicar elementos del lenguaje visual",
            "Elaborar obras artísticas con técnicas básicas y digitales",
            "Diseñar personajes con metodología de model sheet",
            "Digitalizar personajes con color, texturas y profundidad",
        ],
        "indicadores_logro": [
            "Identifica elementos del lenguaje visual: forma, color, textura",
            "Analiza aspectos connotativos y denotativos de imágenes",
            "Diseña personajes originales con model sheet",
            "Digitaliza personajes con tableta gráfica en Photoshop",
        ],
        "evidencias": "Portafolio de obras / Proyecto de digitalización de personaje",
        "horas": 5,
    },
    "Diseño": {
        "mencion": "MULTIMEDIA", "grado": "4to",
        "competencia": "DCM.1.1 — Diseño Básico y Expresión Visual",
        "descripcion": "Emplea atributos físicos y visuales de la forma en la creación de mensajes gráficos.",
        "saberes_conceptuales": [
            "Concepto, clasificación y función del diseño",
            "El proceso de diseño como método de solución de problemas",
            "Elementos conceptuales: punto, línea, plano, color, textura",
            "Leyes de la Gestalt sobre percepción visual",
            "Señalética y sus aplicaciones comunicativas",
        ],
        "saberes_procedimentales": [
            "Utilizar modelo de solución de problemas en diseño",
            "Crear comunicaciones efectivas por medio de figuras y formas",
            "Elaborar proyectos de comunicación gráfica",
        ],
        "indicadores_logro": [
            "Identifica y aplica conceptos básicos de diseño gráfico",
            "Comunica mensajes e ideas de forma visual efectiva",
            "Aplica elementos visuales: punto, línea, plano, color, textura",
            "Reconoce y aplica leyes de la Gestalt en proyectos",
        ],
        "evidencias": "Portafolio de proyectos / Creación de logo o señalética",
        "horas": 4,
    },
    "Identidad_Cultura_Emprendimiento": {
        "mencion": "TODAS", "grado": "4to",
        "competencia": "CF — Competencia de Ciudadanía y Emprendimiento",
        "descripcion": "Desarrolla la identidad cultural dominicana y caribeña vinculada al emprendimiento artístico.",
        "saberes_conceptuales": [
            "Identidad cultural dominicana y caribeña",
            "Historia del arte dominicano",
            "Emprendimiento y gestión de proyectos artísticos",
            "Derechos culturales y propiedad intelectual",
        ],
        "saberes_procedimentales": [
            "Analizar manifestaciones culturales del entorno",
            "Diseñar proyectos artísticos con visión emprendedora",
        ],
        "indicadores_logro": [
            "Valora y explica la identidad cultural dominicana en las artes",
            "Diseña un proyecto artístico con perspectiva de emprendimiento",
        ],
        "evidencias": "Proyecto de emprendimiento artístico-cultural",
        "horas": 2,
    },
    "Historia_Arte_Universal": {
        "mencion": "TODAS", "grado": "4to",
        "competencia": "CF — Pensamiento Lógico, Creativo y Crítico",
        "descripcion": "Analiza el desarrollo del arte universal desde la prehistoria hasta la era digital.",
        "saberes_conceptuales": [
            "Arte prehistórico, antiguo, medieval y renacentista",
            "Barroco, Neoclasicismo, Romanticismo e Impresionismo",
            "Vanguardias del siglo XX: Cubismo, Surrealismo, Expresionismo",
            "Arte contemporáneo y digital",
            "Arte dominicano y del Caribe en contexto universal",
        ],
        "saberes_procedimentales": [
            "Analizar obras de arte en su contexto histórico-cultural",
            "Comparar movimientos artísticos y sus características",
        ],
        "indicadores_logro": [
            "Sitúa cronológicamente los principales movimientos artísticos",
            "Analiza obras representativas de cada período",
            "Conecta el arte universal con expresiones artísticas dominicanas",
        ],
        "evidencias": "Análisis de obra de arte / Presentación oral o escrita",
        "horas": 4,
    },
    # ── MULTIMEDIA 5TO ────────────────────────────────────────────────────────
    "Diseño_Web": {
        "mencion": "MULTIMEDIA", "grado": "5to",
        "competencia": "DCM.2.1 — Producción Digital y Web",
        "descripcion": "Diseña y desarrolla sitios web funcionales aplicando principios de usabilidad y diseño visual.",
        "saberes_conceptuales": [
            "HTML y CSS básico: estructura y estilos",
            "Principios de UX/UI y usabilidad web",
            "Diseño responsivo y accesibilidad",
            "Herramientas: Figma, WordPress",
            "Tendencias en diseño web",
        ],
        "saberes_procedimentales": [
            "Crear páginas web con HTML y CSS",
            "Aplicar principios de diseño visual en interfaces",
            "Planificar y ejecutar proyectos web",
        ],
        "indicadores_logro": [
            "Diseña interfaces web siguiendo principios de usabilidad",
            "Crea páginas web funcionales con HTML y CSS",
            "Aplica diseño responsivo para múltiples dispositivos",
        ],
        "evidencias": "Sitio web funcional publicado o portafolio digital",
        "horas": 6,
    },
    "Diseño_Grafico": {
        "mencion": "MULTIMEDIA", "grado": "5to",
        "competencia": "DCM.2.2 — Comunicación Gráfica y Visual",
        "descripcion": "Desarrolla proyectos de comunicación gráfica utilizando herramientas digitales profesionales.",
        "saberes_conceptuales": [
            "Tipografía: clasificación, legibilidad y combinación",
            "Color en diseño gráfico: psicología y aplicación",
            "Identidad corporativa y branding",
            "Adobe Illustrator o Inkscape",
            "Diseño editorial: revistas, afiches, publicaciones",
        ],
        "saberes_procedimentales": [
            "Crear piezas gráficas profesionales para diferentes medios",
            "Desarrollar identidades visuales completas",
        ],
        "indicadores_logro": [
            "Diseña piezas gráficas con tipografía y color efectivos",
            "Crea sistemas de identidad visual para marcas o eventos",
            "Produce diseños editoriales (afiche, revista, brochure)",
        ],
        "evidencias": "Portafolio de diseño gráfico / Proyecto de identidad visual",
        "horas": 4,
    },
    "Publicidad_Creatividad": {
        "mencion": "MULTIMEDIA", "grado": "5to",
        "competencia": "DCM.2.3 — Comunicación Publicitaria",
        "descripcion": "Crea campañas publicitarias creativas aplicando estrategias de comunicación y marketing.",
        "saberes_conceptuales": [
            "Fundamentos de la publicidad y el marketing",
            "Estrategias creativas y Brief publicitario",
            "Publicidad digital y redes sociales",
            "Ética publicitaria y responsabilidad social",
        ],
        "saberes_procedimentales": [
            "Diseñar campañas publicitarias multimediales",
            "Crear contenido para redes sociales con propósito comunicativo",
        ],
        "indicadores_logro": [
            "Elabora briefs y estrategias creativas publicitarias",
            "Diseña campañas publicitarias para diferentes medios",
        ],
        "evidencias": "Campaña publicitaria completa (digital y/o impresa)",
        "horas": 3,
    },
    "Camara_Video": {
        "mencion": "MULTIMEDIA", "grado": "5to",
        "competencia": "DCM.2.4 — Operación de Cámara de Video",
        "descripcion": "Opera cámaras de video profesional aplicando técnicas de iluminación, composición y narrativa.",
        "saberes_conceptuales": [
            "Tipos de cámaras y configuraciones técnicas",
            "Composición cinematográfica: planos, ángulos, movimientos",
            "Iluminación para video: clave, relleno, contraluz",
            "Narrativa visual y lenguaje cinematográfico",
        ],
        "saberes_procedimentales": [
            "Operar cámaras de video con configuraciones manuales",
            "Planificar grabaciones con criterio narrativo",
        ],
        "indicadores_logro": [
            "Opera cámaras de video con dominio técnico",
            "Aplica principios de composición cinematográfica",
            "Planifica producciones de video con criterio artístico",
        ],
        "evidencias": "Cortometraje o pieza audiovisual editada",
        "horas": 4,
    },
    "Guion": {
        "mencion": "MULTIMEDIA", "grado": "5to",
        "competencia": "DCM.2.5 — Narrativa y Escritura Audiovisual",
        "descripcion": "Desarrolla guiones para producciones audiovisuales aplicando estructura dramática y lenguaje cinematográfico.",
        "saberes_conceptuales": [
            "Estructura del guión: formato literario y técnico",
            "Desarrollo de personajes y arcos narrativos",
            "Géneros audiovisuales: ficción, documental, publicidad",
            "Guión técnico y story board",
        ],
        "saberes_procedimentales": [
            "Escribir guiones en formato profesional",
            "Crear story boards para producciones",
        ],
        "indicadores_logro": [
            "Escribe guiones literarios y técnicos en formato profesional",
            "Crea personajes con motivaciones y conflictos claros",
            "Elabora story boards detallados para producciones",
        ],
        "evidencias": "Guión completo con story board de cortometraje",
        "horas": 4,
    },
    "Medios_Comunicacion": {
        "mencion": "MULTIMEDIA", "grado": "5to",
        "competencia": "DCM.2.6 — Análisis de Medios",
        "descripcion": "Analiza los medios de comunicación y su impacto en la sociedad dominicana.",
        "saberes_conceptuales": [
            "Historia y evolución de los medios de comunicación",
            "Medios digitales: redes sociales y su impacto social",
            "Ética en los medios y fake news",
            "El periodismo visual y fotoperiodismo",
        ],
        "saberes_procedimentales": [
            "Analizar críticamente mensajes mediáticos",
            "Producir contenido responsable para medios digitales",
        ],
        "indicadores_logro": [
            "Analiza el impacto de los medios en la sociedad dominicana",
            "Produce contenido mediático responsable y ético",
        ],
        "evidencias": "Análisis crítico de medios / Proyecto de comunicación",
        "horas": 2,
    },
    # ── MULTIMEDIA 6TO ────────────────────────────────────────────────────────
    "Produccion_Audiovisual": {
        "mencion": "MULTIMEDIA", "grado": "6to",
        "competencia": "DCM.3.1 — Producción Audiovisual Avanzada",
        "descripcion": "Planifica y ejecuta producciones audiovisuales completas integrando todas las etapas del proceso.",
        "saberes_conceptuales": [
            "Pre-producción: desarrollo, presupuesto, casting",
            "Producción: dirección, fotografía, sonido en set",
            "Post-producción: edición, corrección de color, sonorización",
            "Distribución y exhibición audiovisual",
        ],
        "saberes_procedimentales": [
            "Gestionar todas las etapas de una producción audiovisual",
            "Dirigir equipos técnicos y creativos",
            "Editar y post-producir material audiovisual",
        ],
        "indicadores_logro": [
            "Planifica y ejecuta proyectos audiovisuales completos",
            "Dirige y coordina equipos de producción",
            "Realiza post-producción profesional de video y audio",
        ],
        "evidencias": "Cortometraje o documental final producido y exhibido",
        "horas": 4,
    },
    "Animacion": {
        "mencion": "MULTIMEDIA", "grado": "6to",
        "competencia": "DCM.3.2 — Animación Digital",
        "descripcion": "Crea animaciones digitales 2D aplicando principios de animación y storytelling visual.",
        "saberes_conceptuales": [
            "Historia y principios de animación (Disney, Pixar)",
            "Animación 2D: frame a frame y motion graphics",
            "Introducción a animación 3D: modelado básico",
            "Software: Adobe Animate, Blender básico",
        ],
        "saberes_procedimentales": [
            "Crear animaciones 2D con principios de movimiento",
            "Desarrollar motion graphics para proyectos digitales",
        ],
        "indicadores_logro": [
            "Aplica principios de animación en proyectos digitales",
            "Crea animaciones 2D con movimiento fluido y expresivo",
            "Produce motion graphics para proyectos de comunicación",
        ],
        "evidencias": "Proyecto de animación o motion graphics publicado",
        "horas": 4,
    },
    "Edicion_Sonido": {
        "mencion": "MULTIMEDIA", "grado": "6to",
        "competencia": "DCM.3.3 — Edición, Sonido y Musicalización",
        "descripcion": "Edita y produce audio para proyectos multimedia aplicando técnicas profesionales.",
        "saberes_conceptuales": [
            "Grabación y captación de audio profesional",
            "Edición de audio con DAW (Audacity, GarageBand)",
            "Musicalización y diseño sonoro para video",
            "Mezcla y masterización básica",
        ],
        "saberes_procedimentales": [
            "Grabar, editar y mezclar audio para proyectos audiovisuales",
            "Crear bandas sonoras y diseños sonoros originales",
        ],
        "indicadores_logro": [
            "Graba y edita audio con calidad técnica adecuada",
            "Crea diseños sonoros para proyectos multimedia",
            "Realiza mezclas sincronizadas con imagen",
        ],
        "evidencias": "Banda sonora original para proyecto audiovisual",
        "horas": 4,
    },
    "Videoarte": {
        "mencion": "MULTIMEDIA", "grado": "6to",
        "competencia": "DCM.3.4 — Arte y Expresión Audiovisual",
        "descripcion": "Crea obras de videoarte explorando las posibilidades expresivas del video como medio artístico.",
        "saberes_conceptuales": [
            "Historia del videoarte: Nam June Paik, Bill Viola",
            "El video como medio de expresión artística contemporánea",
            "Instalaciones de video y arte digital interactivo",
            "Derechos de autor y licencias Creative Commons",
        ],
        "saberes_procedimentales": [
            "Crear obras de videoarte con intención conceptual",
            "Experimentar con edición no lineal y efectos visuales",
        ],
        "indicadores_logro": [
            "Crea obras de videoarte con concepto artístico definido",
            "Aplica técnicas de edición creativa y efectos visuales",
            "Contextualiza su obra en la tradición del videoarte",
        ],
        "evidencias": "Obra de videoarte exhibida o instalación",
        "horas": 5,
    },
    "Redes_Sociales": {
        "mencion": "MULTIMEDIA", "grado": "6to",
        "competencia": "DCM.3.5 — Comunicación Digital",
        "descripcion": "Gestiona estratégicamente las redes sociales para proyectos artísticos y culturales.",
        "saberes_conceptuales": [
            "Estrategia de contenidos para redes sociales",
            "Plataformas: Instagram, TikTok, YouTube, LinkedIn",
            "Métricas y analítica de redes sociales",
            "Marca personal del artista digital",
        ],
        "saberes_procedimentales": [
            "Planificar y ejecutar estrategias de contenido digital",
            "Crear y gestionar perfiles profesionales de artista",
        ],
        "indicadores_logro": [
            "Diseña estrategias de contenido para plataformas digitales",
            "Gestiona perfiles profesionales con criterio artístico",
            "Analiza métricas y ajusta estrategias de comunicación",
        ],
        "evidencias": "Portfolio digital / Campaña de redes sociales",
        "horas": 2,
    },
    # ── ARTES VISUALES 4TO ────────────────────────────────────────────────────
    "Lenguaje_Plastico_Visual": {
        "mencion": "ARTES VISUALES", "grado": "4to",
        "competencia": "AV.1.1 — Lenguaje Plástico y Visual",
        "descripcion": "Desarrolla la capacidad de expresión plástica utilizando los elementos formales del arte.",
        "saberes_conceptuales": [
            "Elementos plásticos: punto, línea, forma, color, textura",
            "Principios de composición artística",
            "Color: teoría, armonías y psicología",
            "Perspectiva y representación del espacio",
            "Medios y materiales plásticos tradicionales",
        ],
        "saberes_procedimentales": [
            "Aplicar elementos plásticos en composiciones visuales",
            "Experimentar con diferentes materiales y técnicas",
        ],
        "indicadores_logro": [
            "Aplica correctamente los elementos plásticos en sus obras",
            "Experimenta con diversas técnicas y materiales artísticos",
            "Crea composiciones originales con criterio estético personal",
        ],
        "evidencias": "Portafolio de obras plásticas en técnicas mixtas",
        "horas": 6,
    },
    "Dibujo_Tecnico_Artistico": {
        "mencion": "ARTES VISUALES", "grado": "4to",
        "competencia": "AV.1.2 — Representación Visual Técnica",
        "descripcion": "Domina técnicas de dibujo artístico y técnico para la representación precisa del mundo visual.",
        "saberes_conceptuales": [
            "Dibujo a pulso: encaje, proporción, sombreado",
            "Perspectiva cónica y axonométrica",
            "Retrato y figura humana: proporciones",
            "Naturaleza muerta y bodegón",
        ],
        "saberes_procedimentales": [
            "Representar objetos y figuras con precisión técnica",
            "Aplicar perspectiva en composiciones",
        ],
        "indicadores_logro": [
            "Dibuja objetos y figuras con proporciones correctas",
            "Aplica perspectiva en representaciones espaciales",
            "Realiza retratos y figura humana con técnica adecuada",
        ],
        "evidencias": "Cuaderno de dibujo con series técnicas y artísticas",
        "horas": 4,
    },
    "Pintura_Tecnicas_Mixtas": {
        "mencion": "ARTES VISUALES", "grado": "4to",
        "competencia": "AV.1.3 — Expresión Pictórica",
        "descripcion": "Experimenta con técnicas pictóricas variadas desarrollando una voz artística personal.",
        "saberes_conceptuales": [
            "Acuarela: técnica húmedo sobre húmedo y seco",
            "Acrílico: capas, veladuras y texturas",
            "Óleo: técnica directa e indirecta",
            "Técnicas mixtas: collage, encáustica, assemblage",
            "Historia del movimiento pictórico dominicano",
        ],
        "saberes_procedimentales": [
            "Dominar técnicas básicas de pintura",
            "Crear obras con intención expresiva personal",
        ],
        "indicadores_logro": [
            "Aplica técnicas de acuarela, acrílico y/o óleo con destreza",
            "Crea obras originales con técnicas mixtas",
            "Expresa ideas y emociones a través de la pintura",
        ],
        "evidencias": "Serie de obras pictóricas / Exposición artística",
        "horas": 4,
    },
    # ── ARTES VISUALES 5TO ────────────────────────────────────────────────────
    "Escultura_Ceramica": {
        "mencion": "ARTES VISUALES", "grado": "5to",
        "competencia": "AV.2.1 — Expresión Tridimensional",
        "descripcion": "Crea objetos artísticos tridimensionales con diferentes materiales y técnicas.",
        "saberes_conceptuales": [
            "Escultura: modelado, talla y construcción",
            "Arcilla y cerámica: técnicas de construcción y quema",
            "Escultura con materiales reciclados y alternativos",
            "Escultura dominicana: artistas y tradiciones",
        ],
        "saberes_procedimentales": [
            "Modelar piezas con arcilla usando técnicas tradicionales",
            "Construir esculturas con materiales variados",
        ],
        "indicadores_logro": [
            "Modela y construye piezas tridimensionales con técnica",
            "Produce piezas cerámicas completando el proceso",
            "Crea esculturas con materiales alternativos",
        ],
        "evidencias": "Serie de piezas escultóricas o cerámicas",
        "horas": 5,
    },
    "Grabado_Serigrafia": {
        "mencion": "ARTES VISUALES", "grado": "5to",
        "competencia": "AV.2.2 — Arte de Reproducción",
        "descripcion": "Domina técnicas de grabado y serigrafía como formas de expresión artística.",
        "saberes_conceptuales": [
            "Historia del grabado: xilografía, calcografía",
            "Serigrafía: proceso y aplicaciones artísticas",
            "Grabado en linóleo y materiales alternativos",
        ],
        "saberes_procedimentales": [
            "Realizar grabados en linóleo",
            "Ejecutar el proceso completo de serigrafía",
        ],
        "indicadores_logro": [
            "Ejecuta grabados con técnica de reducción y estampado",
            "Realiza serigrafía artística completa",
            "Produce series de estampas con coherencia artística",
        ],
        "evidencias": "Serie de grabados / Serigrafías",
        "horas": 4,
    },
    "Diseno_Comunicacion_Visual": {
        "mencion": "ARTES VISUALES", "grado": "5to",
        "competencia": "AV.2.3 — Diseño y Comunicación Visual",
        "descripcion": "Aplica principios de diseño gráfico en proyectos de comunicación visual.",
        "saberes_conceptuales": [
            "Tipografía aplicada a proyectos visuales",
            "Diseño de cartel y comunicación gráfica",
            "Imagen digital: Photoshop / GIMP",
            "Diseño para impresión y pantalla",
        ],
        "saberes_procedimentales": [
            "Crear piezas gráficas para comunicación visual",
            "Usar herramientas digitales en proyectos artísticos",
        ],
        "indicadores_logro": [
            "Diseña carteles y piezas de comunicación visual efectivas",
            "Usa herramientas digitales para crear arte visual",
        ],
        "evidencias": "Serie de carteles / Proyecto de comunicación visual",
        "horas": 4,
    },
    # ── ARTES VISUALES 6TO ────────────────────────────────────────────────────
    "Arte_Digital_Multimedia": {
        "mencion": "ARTES VISUALES", "grado": "6to",
        "competencia": "AV.3.1 — Arte Digital",
        "descripcion": "Crea obras de arte digital integrando herramientas tecnológicas y conceptos artísticos.",
        "saberes_conceptuales": [
            "Arte digital: instalaciones, net art, arte generativo",
            "Fotografía artística avanzada y manipulación digital",
            "Video arte y arte interactivo",
            "NFT y arte en el mundo digital",
        ],
        "saberes_procedimentales": [
            "Crear obras de arte digital con concepto artístico",
            "Integrar tecnología en proyectos artísticos",
        ],
        "indicadores_logro": [
            "Crea obras de arte digital con intención conceptual clara",
            "Integra herramientas tecnológicas en proyectos artísticos",
        ],
        "evidencias": "Exposición de arte digital / Portfolio digital",
        "horas": 4,
    },
    "Proyecto_Artes_Visuales": {
        "mencion": "ARTES VISUALES", "grado": "6to",
        "competencia": "AV.3.2 — Proyecto de Producción en Artes Visuales",
        "descripcion": "Desarrolla un proyecto artístico personal de envergadura que integra todo el aprendizaje del bachillerato.",
        "saberes_conceptuales": [
            "Gestión de proyectos artísticos: planificación, ejecución",
            "Curatoría y montaje de exposiciones",
            "Portafolio artístico profesional",
            "Artistas dominicanos contemporáneos como referentes",
        ],
        "saberes_procedimentales": [
            "Desarrollar proyecto artístico personal con metodología",
            "Montar y presentar exposición artística",
        ],
        "indicadores_logro": [
            "Desarrolla un proyecto artístico original de envergadura",
            "Monta y presenta una exposición artística con criterio curatorial",
            "Produce un portafolio artístico profesional",
        ],
        "evidencias": "Exposición de obra propia / Portafolio artístico profesional",
        "horas": 6,
    },
    # ── MÚSICA 4TO ────────────────────────────────────────────────────────────
    "Teoria_Solfeo": {
        "mencion": "MÚSICA", "grado": "4to",
        "competencia": "MUS.1.1 — Lenguaje Musical Fundamental",
        "descripcion": "Desarrolla el lenguaje musical básico: lectura, escritura y comprensión teórica.",
        "saberes_conceptuales": [
            "El pentagrama, claves y notas musicales",
            "Figuras y valores rítmicos",
            "Compases: binario, ternario, cuaternario",
            "Escalas mayores y menores, intervalos",
            "Acordes básicos y dinámica musical",
        ],
        "saberes_procedimentales": [
            "Leer y escribir música en notación convencional",
            "Entonar melodías y solfear con precisión",
        ],
        "indicadores_logro": [
            "Lee y escribe música en notación convencional",
            "Solfea melodías con entonación y ritmo correctos",
            "Identifica elementos del lenguaje musical en obras",
        ],
        "evidencias": "Dictados musicales / Ejercicios de solfeo",
        "horas": 4,
    },
    "Instrumento_Principal_I": {
        "mencion": "MÚSICA", "grado": "4to",
        "competencia": "MUS.1.2 — Ejecución Instrumental Básica",
        "descripcion": "Desarrolla la técnica básica del instrumento asignado.",
        "saberes_conceptuales": [
            "Historia y características del instrumento",
            "Postura, técnica y mantenimiento del instrumento",
            "Repertorio básico dominicano e internacional",
            "Escalas y ejercicios técnicos",
        ],
        "saberes_procedimentales": [
            "Ejecutar el instrumento con técnica básica correcta",
            "Interpretar piezas del repertorio básico asignado",
        ],
        "indicadores_logro": [
            "Ejecuta el instrumento con postura y técnica correcta",
            "Interpreta piezas básicas del repertorio asignado",
            "Demuestra disciplina en la práctica instrumental",
        ],
        "evidencias": "Recital o audición de fin de período",
        "horas": 6,
    },
    "Coro_Conjunto_Musical_I": {
        "mencion": "MÚSICA", "grado": "4to",
        "competencia": "MUS.1.3 — Musicalización Grupal",
        "descripcion": "Desarrolla la capacidad de hacer música en conjunto aplicando técnicas corales.",
        "saberes_conceptuales": [
            "Técnica vocal: respiración, emisión, resonancia",
            "Tipos de voces vocales",
            "Repertorio coral dominicano y latinoamericano",
            "Dinámica y expresión en coro",
        ],
        "saberes_procedimentales": [
            "Cantar en coro con afinación y expresión",
            "Memorizar e interpretar repertorio coral",
        ],
        "indicadores_logro": [
            "Canta en coro con afinación y expresión adecuadas",
            "Interpreta repertorio coral dominicano con calidad",
            "Respeta indicaciones del director en ensayos",
        ],
        "evidencias": "Presentación coral pública o grabación",
        "horas": 3,
    },
    # ── MÚSICA 5TO ────────────────────────────────────────────────────────────
    "Instrumento_Principal_II": {
        "mencion": "MÚSICA", "grado": "5to",
        "competencia": "MUS.2.1 — Ejecución Instrumental Intermedia",
        "descripcion": "Profundiza la técnica instrumental con repertorio de mayor complejidad.",
        "saberes_conceptuales": [
            "Técnica instrumental intermedia",
            "Fraseo musical, articulación y dinámica",
            "Repertorio clásico, contemporáneo y dominicano",
            "Análisis de obras musicales",
        ],
        "saberes_procedimentales": [
            "Ejecutar repertorio intermedio con dominio técnico",
            "Interpretar con expresividad musical",
        ],
        "indicadores_logro": [
            "Ejecuta obras de nivel intermedio con técnica y musicalidad",
            "Interpreta con expresión y fraseo adecuados",
            "Analiza obras del repertorio en su contexto histórico",
        ],
        "evidencias": "Recital de fin de año con obras variadas",
        "horas": 6,
    },
    "Armonia_Contrapunto": {
        "mencion": "MÚSICA", "grado": "5to",
        "competencia": "MUS.2.2 — Análisis y Composición Musical",
        "descripcion": "Comprende y aplica los principios de la armonía tonal y el contrapunto.",
        "saberes_conceptuales": [
            "Formación de acordes y sus inversiones",
            "Progresiones armónicas funcionales",
            "Contrapunto: movimientos y especies básicas",
            "Análisis armónico de obras clásicas y populares",
        ],
        "saberes_procedimentales": [
            "Analizar progresiones armónicas en obras",
            "Componer melodías con acompañamiento armónico",
        ],
        "indicadores_logro": [
            "Construye y clasifica acordes en diferentes tonalidades",
            "Analiza la armonía de obras musicales variadas",
            "Compone ejercicios de armonía básica",
        ],
        "evidencias": "Composición armónica original / Análisis de obra",
        "horas": 4,
    },
    "Musica_Dominicana_Caribe": {
        "mencion": "MÚSICA", "grado": "5to",
        "competencia": "MUS.2.3 — Identidad Musical Dominicana",
        "descripcion": "Estudia y ejecuta la música dominicana y del Caribe en su contexto cultural.",
        "saberes_conceptuales": [
            "Géneros dominicanos: merengue, bachata, palo, salve",
            "Instrumentos típicos: tambora, güira, acordeón",
            "Ritmos del Caribe: son, cumbia, reggae, calipso",
            "Compositores e intérpretes dominicanos destacados",
        ],
        "saberes_procedimentales": [
            "Interpretar ritmos y géneros musicales dominicanos",
            "Analizar la estructura de géneros caribeños",
        ],
        "indicadores_logro": [
            "Identifica y ejecuta géneros musicales dominicanos",
            "Analiza el contexto histórico-cultural de la música dominicana",
            "Valora la diversidad musical del Caribe",
        ],
        "evidencias": "Presentación de repertorio de música dominicana",
        "horas": 3,
    },
    "Composicion_Arreglos": {
        "mencion": "MÚSICA", "grado": "5to",
        "competencia": "MUS.2.4 — Composición y Arreglos Básicos",
        "descripcion": "Crea composiciones y arreglos musicales originales aplicando principios armónicos.",
        "saberes_conceptuales": [
            "Proceso de composición musical",
            "Arreglos para pequeño ensamble",
            "Forma musical: binaria, ternaria, rondó",
            "Software de notación: MuseScore / Sibelius básico",
        ],
        "saberes_procedimentales": [
            "Componer piezas musicales originales cortas",
            "Realizar arreglos simples para grupos disponibles",
        ],
        "indicadores_logro": [
            "Compone piezas originales con estructura definida",
            "Realiza arreglos musicales básicos para ensamble",
            "Usa software de notación para transcribir sus obras",
        ],
        "evidencias": "Composición original escrita y ejecutada",
        "horas": 4,
    },
    # ── MÚSICA 6TO ────────────────────────────────────────────────────────────
    "Instrumento_Principal_III": {
        "mencion": "MÚSICA", "grado": "6to",
        "competencia": "MUS.3.1 — Ejecución Instrumental Avanzada",
        "descripcion": "Desarrolla dominio técnico e interpretativo avanzado del instrumento principal.",
        "saberes_conceptuales": [
            "Técnica instrumental avanzada",
            "Interpretación con profundidad musical",
            "Repertorio de concierto: clásico, contemporáneo y dominicano",
            "La carrera musical: oportunidades profesionales en RD",
        ],
        "saberes_procedimentales": [
            "Ejecutar obras avanzadas con dominio técnico e interpretativo",
            "Preparar y presentar un recital completo",
        ],
        "indicadores_logro": [
            "Ejecuta obras avanzadas con dominio técnico e interpretativo",
            "Presenta un recital completo con obras variadas",
            "Demuestra musicalidad y madurez interpretativa",
        ],
        "evidencias": "Recital de graduación / Concierto final",
        "horas": 6,
    },
    "Produccion_Musical_Digital": {
        "mencion": "MÚSICA", "grado": "6to",
        "competencia": "MUS.3.2 — Producción Musical Digital",
        "descripcion": "Produce música digital utilizando DAW y herramientas de producción contemporáneas.",
        "saberes_conceptuales": [
            "DAW (Digital Audio Workstation): GarageBand, FL Studio",
            "MIDI y síntesis de sonido básica",
            "Mezcla y masterización básica",
            "Producción de géneros dominicanos en formato digital",
        ],
        "saberes_procedimentales": [
            "Producir pistas musicales con DAW",
            "Integrar instrumentos reales y virtuales en producción",
        ],
        "indicadores_logro": [
            "Produce pistas musicales con calidad técnica en DAW",
            "Integra instrumentos acústicos y digitales",
            "Crea producciones de géneros dominicanos en formato digital",
        ],
        "evidencias": "EP o single producido y masterizado",
        "horas": 5,
    },
    # ── TEATRO 4TO ────────────────────────────────────────────────────────────
    "Expresion_Corporal_Movimiento": {
        "mencion": "TEATRO", "grado": "4to",
        "competencia": "TEA.1.1 — Expresión Corporal y Movimiento Escénico",
        "descripcion": "Desarrolla la conciencia y dominio del cuerpo como instrumento expresivo del actor.",
        "saberes_conceptuales": [
            "El cuerpo como instrumento expresivo del actor",
            "Conciencia corporal: tensión, relajación, equilibrio",
            "El espacio escénico y su uso",
            "Ritmo y tiempo en la expresión corporal",
        ],
        "saberes_procedimentales": [
            "Desarrollar conciencia corporal en el espacio escénico",
            "Aplicar técnicas de relajación y tensión expresiva",
        ],
        "indicadores_logro": [
            "Demuestra conciencia corporal y dominio del espacio",
            "Aplica técnicas de expresión corporal con intención comunicativa",
            "Crea secuencias de movimiento con sentido expresivo",
        ],
        "evidencias": "Ejercicio de expresión corporal sin diálogo",
        "horas": 4,
    },
    "Tecnica_Vocal_Diccion": {
        "mencion": "TEATRO", "grado": "4to",
        "competencia": "TEA.1.2 — Instrumento Vocal del Actor",
        "descripcion": "Desarrolla la voz como instrumento con técnica, proyección y expresividad.",
        "saberes_conceptuales": [
            "Anatomía de la voz: aparato fonador",
            "Respiración diafragmática y soporte vocal",
            "Resonadores y proyección de la voz",
            "Dicción y articulación para el teatro",
        ],
        "saberes_procedimentales": [
            "Desarrollar respiración diafragmática para actuación",
            "Proyectar la voz con claridad y sin esfuerzo",
        ],
        "indicadores_logro": [
            "Proyecta la voz con claridad en el espacio escénico",
            "Articula con dicción correcta en diferentes registros",
            "Adapta la voz a personajes y situaciones dramáticas",
        ],
        "evidencias": "Monólogo con trabajo vocal evidente",
        "horas": 3,
    },
    "Actuacion_I": {
        "mencion": "TEATRO", "grado": "4to",
        "competencia": "TEA.1.3 — Actuación Básica",
        "descripcion": "Desarrolla fundamentos de la actuación teatral con improvisación y técnicas básicas.",
        "saberes_conceptuales": [
            "El juego dramático y la improvisación",
            "Personaje: construcción y motivaciones básicas",
            "El conflicto dramático y la acción escénica",
            "El ensayo y la repetición en el proceso creativo",
        ],
        "saberes_procedimentales": [
            "Improvisar escenas con objetivos claros",
            "Construir personajes con motivaciones definidas",
        ],
        "indicadores_logro": [
            "Improvisa con presencia escénica y objetivos claros",
            "Construye personajes con motivaciones coherentes",
            "Actúa en escenas cortas con concentración y técnica",
        ],
        "evidencias": "Presentación de escenas cortas o improvisaciones",
        "horas": 6,
    },
    # ── TEATRO 5TO ────────────────────────────────────────────────────────────
    "Actuacion_II": {
        "mencion": "TEATRO", "grado": "5to",
        "competencia": "TEA.2.1 — Actuación Intermedia",
        "descripcion": "Profundiza en el método Stanislavski para la construcción de personajes complejos.",
        "saberes_conceptuales": [
            "Sistema Stanislavski: si mágico, circunstancias dadas",
            "Objetivos, super-objetivos y acción física",
            "Brecht y el teatro épico: distanciamiento",
            "Análisis de textos dramáticos",
        ],
        "saberes_procedimentales": [
            "Aplicar el método Stanislavski en la actuación",
            "Analizar textos dramáticos para su interpretación",
        ],
        "indicadores_logro": [
            "Aplica principios del método Stanislavski",
            "Construye personajes con objetivos y subtexto",
            "Interpreta textos con profundidad y verdad escénica",
        ],
        "evidencias": "Escena de obra clásica o contemporánea",
        "horas": 6,
    },
    "Dramaturgia_Guion_Teatral": {
        "mencion": "TEATRO", "grado": "5to",
        "competencia": "TEA.2.2 — Escritura Dramática",
        "descripcion": "Desarrolla habilidades de escritura dramática para textos teatrales originales.",
        "saberes_conceptuales": [
            "Estructura dramática: planteamiento, desarrollo, desenlace",
            "Tipos de conflicto dramático",
            "Diálogo teatral y subtexto",
            "Teatro dominicano: autores y obras representativas",
        ],
        "saberes_procedimentales": [
            "Escribir textos dramáticos con estructura clara",
            "Crear personajes con voz propia en el diálogo",
        ],
        "indicadores_logro": [
            "Escribe obras teatrales con estructura dramática coherente",
            "Crea personajes con diálogos auténticos y reveladores",
            "Adapta textos literarios al formato teatral",
        ],
        "evidencias": "Obra teatral corta escrita y presentada",
        "horas": 4,
    },
    "Escenografia_Iluminacion": {
        "mencion": "TEATRO", "grado": "5to",
        "competencia": "TEA.2.3 — Diseño Escénico",
        "descripcion": "Diseña y construye elementos escenográficos e iluminación para producciones teatrales.",
        "saberes_conceptuales": [
            "Historia de la escenografía teatral",
            "Elementos de la escenografía: ciclorama, bambalinas",
            "Iluminación teatral: tipos de luces y efectos",
            "Vestuario y caracterización del personaje",
        ],
        "saberes_procedimentales": [
            "Diseñar y construir escenografías básicas",
            "Planificar iluminación para producciones teatrales",
        ],
        "indicadores_logro": [
            "Diseña escenografías que apoyan la narrativa teatral",
            "Planifica y ejecuta iluminación básica para escenas",
            "Crea vestuario y caracterización coherente con el personaje",
        ],
        "evidencias": "Diseño escenográfico para montaje teatral",
        "horas": 3,
    },
    # ── TEATRO 6TO ────────────────────────────────────────────────────────────
    "Actuacion_III": {
        "mencion": "TEATRO", "grado": "6to",
        "competencia": "TEA.3.1 — Actuación Avanzada y Proyecto Escénico",
        "descripcion": "Desarrolla un proyecto escénico completo integrando todas las herramientas actorales adquiridas.",
        "saberes_conceptuales": [
            "Construcción de un papel de envergadura",
            "Proceso de montaje: ensayos, temporada",
            "Teatro contemporáneo dominicano",
            "La carrera teatral: oportunidades en RD y el Caribe",
        ],
        "saberes_procedimentales": [
            "Protagonizar obras de mayor complejidad dramática",
            "Colaborar en el proceso completo de montaje",
        ],
        "indicadores_logro": [
            "Protagoniza obras con madurez y profundidad actoral",
            "Colabora efectivamente en el proceso de montaje",
            "Demuestra manejo de todas las herramientas actorales",
        ],
        "evidencias": "Obra teatral completa presentada al público",
        "horas": 6,
    },
    "Montaje_Teatral_Final": {
        "mencion": "TEATRO", "grado": "6to",
        "competencia": "TEA.3.2 — Producción Teatral",
        "descripcion": "Gestiona y produce una obra teatral completa como proyecto final del bachillerato.",
        "saberes_conceptuales": [
            "Gestión cultural y producción teatral",
            "Relaciones con el público y difusión",
            "Presupuesto y financiamiento de proyectos teatrales",
            "El teatro como empresa cultural sostenible",
        ],
        "saberes_procedimentales": [
            "Planificar y ejecutar una producción teatral completa",
            "Gestionar recursos humanos y materiales",
        ],
        "indicadores_logro": [
            "Planifica y ejecuta una producción teatral completa",
            "Gestiona recursos con eficiencia y creatividad",
            "Presenta la obra al público con éxito",
        ],
        "evidencias": "Producción teatral completa: obra presentada al público",
        "horas": 5,
    },
    # ── DANZA 4TO ─────────────────────────────────────────────────────────────
    "Tecnica_Danza_Clasica_I": {
        "mencion": "DANZA", "grado": "4to",
        "competencia": "DAN.1.1 — Técnica Clásica Básica",
        "descripcion": "Desarrolla la técnica básica de ballet como fundamento para las técnicas dancísticas.",
        "saberes_conceptuales": [
            "Postura y alineación corporal en ballet",
            "Las cinco posiciones de pies y brazos",
            "Vocabulario básico: pliés, tendus, dégagés",
            "Port de bras y coordinación de brazos",
            "Musicalidad y fraseo en danza",
        ],
        "saberes_procedimentales": [
            "Ejecutar ejercicios de barra con técnica correcta",
            "Realizar ejercicios de centro con coordinación",
        ],
        "indicadores_logro": [
            "Ejecuta ejercicios de barra con postura y técnica correcta",
            "Realiza combinaciones de centro con coordinación",
            "Demuestra musicalidad en la ejecución",
        ],
        "evidencias": "Evaluación técnica / Video de clase",
        "horas": 5,
    },
    "Tecnica_Danza_Folklorica_I": {
        "mencion": "DANZA", "grado": "4to",
        "competencia": "DAN.1.2 — Identidad Dancística Dominicana",
        "descripcion": "Estudia y ejecuta las danzas folklóricas dominicanas como patrimonio cultural.",
        "saberes_conceptuales": [
            "Orígenes de la danza folklórica dominicana",
            "Manifestaciones dancísticas: palo, salve, tumba, gagá",
            "Indumentaria y elementos escénicos del folklore",
            "La danza como expresión de identidad cultural",
        ],
        "saberes_procedimentales": [
            "Ejecutar danzas folklóricas dominicanas con técnica básica",
            "Investigar manifestaciones culturales locales",
        ],
        "indicadores_logro": [
            "Ejecuta danzas folklóricas con calidad técnica",
            "Explica el contexto cultural de cada danza",
            "Valora el folklore como expresión de identidad nacional",
        ],
        "evidencias": "Presentación folklórica en evento escolar",
        "horas": 4,
    },
    "Expresion_Corporal_Danza": {
        "mencion": "DANZA", "grado": "4to",
        "competencia": "DAN.1.3 — Acondicionamiento para la Danza",
        "descripcion": "Desarrolla las capacidades físicas necesarias para la práctica segura de la danza.",
        "saberes_conceptuales": [
            "Anatomía básica aplicada a la danza",
            "Calentamiento, elongación y enfriamiento",
            "Flexibilidad y fuerza para bailarines",
            "Prevención de lesiones en danza",
        ],
        "saberes_procedimentales": [
            "Ejecutar rutinas de calentamiento y elongación",
            "Desarrollar flexibilidad y fuerza para la danza",
        ],
        "indicadores_logro": [
            "Ejecuta rutinas de calentamiento correctamente",
            "Demuestra mejoras en flexibilidad y fuerza",
            "Aplica principios de cuidado corporal en la práctica",
        ],
        "evidencias": "Evaluación de condición física / Registro de progreso",
        "horas": 3,
    },
    # ── DANZA 5TO ─────────────────────────────────────────────────────────────
    "Tecnica_Danza_Clasica_II": {
        "mencion": "DANZA", "grado": "5to",
        "competencia": "DAN.2.1 — Técnica Clásica Intermedia",
        "descripcion": "Profundiza en la técnica de ballet y danza clásica con mayor complejidad.",
        "saberes_conceptuales": [
            "Vocabulario intermedio de ballet",
            "Allegro y adagio en la técnica clásica",
            "Zapatillas de punta para estudiantes femeninas",
            "Variaciones del repertorio clásico",
        ],
        "saberes_procedimentales": [
            "Ejecutar combinaciones intermedias con técnica",
            "Interpretar variaciones del repertorio clásico",
        ],
        "indicadores_logro": [
            "Ejecuta combinaciones intermedias con técnica y estilo",
            "Interpreta variaciones del repertorio clásico",
            "Demuestra musicalidad y control en la ejecución",
        ],
        "evidencias": "Variación de ballet presentada en espectáculo",
        "horas": 5,
    },
    "Danza_Moderna_Contemporanea": {
        "mencion": "DANZA", "grado": "5to",
        "competencia": "DAN.2.2 — Técnica Moderna y Contemporánea",
        "descripcion": "Desarrolla vocabulario de danza moderna y contemporánea.",
        "saberes_conceptuales": [
            "Historia de la danza moderna: Duncan, Graham",
            "Técnica Graham: contraction y release",
            "Danza contemporánea e improvisación",
            "El cuerpo en el espacio: kinesfera y niveles",
        ],
        "saberes_procedimentales": [
            "Ejecutar técnica Graham y vocabulario moderno",
            "Explorar la improvisación como herramienta creativa",
        ],
        "indicadores_logro": [
            "Ejecuta vocabulario de danza moderna con técnica",
            "Improvisa con conciencia del cuerpo y espacio",
            "Crea frases de movimiento con calidad expresiva",
        ],
        "evidencias": "Solo o dúo de danza moderna/contemporánea",
        "horas": 4,
    },
    "Composicion_Coreografica_I": {
        "mencion": "DANZA", "grado": "5to",
        "competencia": "DAN.2.3 — Creación Coreográfica",
        "descripcion": "Desarrolla herramientas de composición coreográfica para la creación de obras.",
        "saberes_conceptuales": [
            "Elementos de la danza: espacio, tiempo, energía, cuerpo",
            "Principios de composición: unidad, variedad",
            "Formas coreográficas: ABA, tema y variación",
            "Relación danza-música en la creación",
        ],
        "saberes_procedimentales": [
            "Aplicar principios de composición en frases de movimiento",
            "Desarrollar estudios coreográficos con estructura",
        ],
        "indicadores_logro": [
            "Aplica elementos de la danza en la composición",
            "Crea obras coreográficas con estructura clara",
            "Trabaja el proceso creativo con metodología",
        ],
        "evidencias": "Estudio coreográfico original presentado",
        "horas": 4,
    },
    # ── DANZA 6TO ─────────────────────────────────────────────────────────────
    "Composicion_Coreografica_II": {
        "mencion": "DANZA", "grado": "6to",
        "competencia": "DAN.3.1 — Proyecto Coreográfico Final",
        "descripcion": "Crea un proyecto coreográfico de envergadura como culminación del bachillerato.",
        "saberes_conceptuales": [
            "Proceso coreográfico completo: concept, research, creation",
            "La danza en el mundo contemporáneo dominicano",
            "Montaje y producción de espectáculo de danza",
            "La carrera en danza: oportunidades en RD",
        ],
        "saberes_procedimentales": [
            "Crear un proyecto coreográfico completo",
            "Dirigir y montar un espectáculo de danza",
        ],
        "indicadores_logro": [
            "Crea un proyecto coreográfico original de envergadura",
            "Monta y presenta un espectáculo de danza completo",
            "Demuestra madurez artística en su propuesta",
        ],
        "evidencias": "Espectáculo de danza presentado al público",
        "horas": 5,
    },
    "Danza_Urbana_Contemporanea": {
        "mencion": "DANZA", "grado": "6to",
        "competencia": "DAN.3.2 — Danza Urbana y Culturas Populares",
        "descripcion": "Estudia y ejecuta estilos de danza urbana y contemporánea dominicana.",
        "saberes_conceptuales": [
            "Hip hop, reggaeton dancehall y breakdance",
            "Danza urbana dominicana: influencias y estilos",
            "La danza como expresión de identidad juvenil",
            "Freestyle e improvisación urbana",
        ],
        "saberes_procedimentales": [
            "Ejecutar estilos de danza urbana básicos",
            "Crear rutinas de danza urbana original",
        ],
        "indicadores_logro": [
            "Ejecuta estilos de danza urbana con técnica y estilo",
            "Crea rutinas de danza urbana con identidad propia",
            "Valora la danza urbana como expresión cultural contemporánea",
        ],
        "evidencias": "Battle o presentación de danza urbana",
        "horas": 3,
    },
}

CURRICULUM_MULTIMEDIA = {
    k: v for k, v in CURRICULUM_ARTES.items()
    if v.get("mencion") in ("MULTIMEDIA", "TODAS")
}

CLUSTER_META = [
    {"label": "Alto rendimiento estable",    "color": "#4dffb4", "icon": "⭐",
     "desc": "Buen desempeño académico y emocional. Bajo riesgo.",
     "accion": "Mantener seguimiento regular. Oportunidades de liderazgo."},
    {"label": "Rendimiento medio, conducta variable", "color": "#c8f060", "icon": "📊",
     "desc": "Notas aceptables pero con irregularidades conductuales.",
     "accion": "Refuerzo de hábitos. Entrevista trimestral."},
    {"label": "Riesgo conductual",            "color": "#ffc94d", "icon": "⚠️",
     "desc": "Conflictos frecuentes o bajo autocontrol. Académico variable.",
     "accion": "Intervención conductual. Coordinación con psicología."},
    {"label": "Caso silencioso",              "color": "#60b8f0", "icon": "🔇",
     "desc": "Alto rendimiento pero señales de malestar emocional.",
     "accion": "Entrevista de bienestar. Seguimiento emocional discreto."},
    {"label": "En crisis – intervención urgente", "color": "#ff6b6b", "icon": "🚨",
     "desc": "Múltiples indicadores de riesgo simultáneos.",
     "accion": "Intervención inmediata. Reporte a coordinación y psicología."},
]

DB_TABLAS_META = {
    "estudiantes":              {"label": "Estudiantes",             "icon": "👥"},
    "materias_calificaciones":  {"label": "Calificaciones",          "icon": "📊"},
    "asistencia":               {"label": "Asistencia",              "icon": "📅"},
    "reportes":                 {"label": "Reportes",                "icon": "📋"},
    "cuaderno_anecdotico":      {"label": "Cuaderno Anecdótico",     "icon": "📓"},
    "logros":                   {"label": "Logros",                  "icon": "🏆"},
    "historial_planificaciones":{"label": "Planificaciones",         "icon": "📝"},
    "registro_liceo":           {"label": "Registro Liceo",          "icon": "🏫"},
    "ml_clusters":              {"label": "Clusters ML",             "icon": "🔬"},
    "recovery_tokens":          {"label": "Tokens Recuperación",     "icon": "🔑"},
}

DEFAULTS_CENTRO = {
    "nombre":    "Centro Educativo en Artes Benito Juárez",
    "modalidad": "Modalidad en Artes · Nivel Secundario",
    "direccion": "Prolongación Ovando, Cristo Rey, Santo Domingo, D.N.",
    "pais":      "República Dominicana",
    "telefono":  "(809) 563-0241",
    "email":     "centroenartesbenitojuarez@gmail.com",
    "logo_base64": None,
}


PLAN_MULTIMEDIA = PLAN_ARTES["MULTIMEDIA"]

CURRICULUM_ARTES = {
    # ── MATERIAS TÉCNICAS MULTIMEDIA 4TO ──────────────────────────────────────
    "Fotografía": {
        "mencion": "MULTIMEDIA", "grado": "4to",
        "competencia": "DCM.1.2 — Diseño y Creatividad Multimedia",
        "descripcion": "Ejecuta el proceso del uso de la cámara fotográfica en proyectos de expresión artística aplicando técnicas novedosas y creativas.",
        "saberes_conceptuales": [
            "Historia de la fotografía y su evolución digital",
            "Componentes de la cámara: diafragma, obturador, ISO",
            "Profundidad de campo y tipos de objetivos",
            "Iluminación de estudio y natural",
            "Leyes de composición: horizonte, mirada, tercios",
            "Planos y ángulos fotográficos",
            "Manipulación de imagen digital y dispositivo móvil",
        ],
        "saberes_procedimentales": [
            "Uso correcto de la cámara fotográfica",
            "Manejo del diafragma, obturador e ISO",
            "Realización de producciones fotográficas",
            "Fotografía como medio de expresión artística",
        ],
        "indicadores_logro": [
            "Explica antecedentes y evolución de la fotografía",
            "Realiza fotografías aplicando reglas de composición",
            "Manipula correctamente cámara y dispositivo móvil",
            "Domina técnicas de iluminación en diferentes ambientes",
            "Valora la fotografía como expresión artística y comunicación",
        ],
        "evidencias": "Exposición fotográfica o portafolio digital",
        "horas": 4,
    },
    "Lenguaje_Visual": {
        "mencion": "MULTIMEDIA", "grado": "4to",
        "competencia": "AA.1.1 — Animación Artística y Comunicación Visual",
        "descripcion": "Comunica a través del lenguaje visual las características de la personalidad conceptualizada utilizando medios tradicionales y digitales.",
        "saberes_conceptuales": [
            "Formas, color, textura, composición y profundidad",
            "Figura-fondo, luz y sombras, escala y proporción",
            "Diseño de personajes y model sheet",
            "Tableta gráfica y software Photoshop",
            "Aspectos connotativos y denotativos de imágenes",
        ],
        "saberes_procedimentales": [
            "Identificar y aplicar elementos del lenguaje visual",
            "Elaborar obras artísticas con técnicas básicas y digitales",
            "Diseñar personajes con metodología de model sheet",
            "Digitalizar personajes con color, texturas y profundidad",
        ],
        "indicadores_logro": [
            "Identifica elementos del lenguaje visual: forma, color, textura",
            "Analiza aspectos connotativos y denotativos de imágenes",
            "Diseña personajes originales con model sheet",
            "Digitaliza personajes con tableta gráfica en Photoshop",
        ],
        "evidencias": "Portafolio de obras / Proyecto de digitalización de personaje",
        "horas": 5,
    },
    "Diseño": {
        "mencion": "MULTIMEDIA", "grado": "4to",
        "competencia": "DCM.1.1 — Diseño Básico y Expresión Visual",
        "descripcion": "Emplea atributos físicos y visuales de la forma en la creación de mensajes gráficos.",
        "saberes_conceptuales": [
            "Concepto, clasificación y función del diseño",
            "El proceso de diseño como método de solución de problemas",
            "Elementos conceptuales: punto, línea, plano, color, textura",
            "Leyes de la Gestalt sobre percepción visual",
            "Señalética y sus aplicaciones comunicativas",
        ],
        "saberes_procedimentales": [
            "Utilizar modelo de solución de problemas en diseño",
            "Crear comunicaciones efectivas por medio de figuras y formas",
            "Elaborar proyectos de comunicación gráfica",
        ],
        "indicadores_logro": [
            "Identifica y aplica conceptos básicos de diseño gráfico",
            "Comunica mensajes e ideas de forma visual efectiva",
            "Aplica elementos visuales: punto, línea, plano, color, textura",
            "Reconoce y aplica leyes de la Gestalt en proyectos",
        ],
        "evidencias": "Portafolio de proyectos / Creación de logo o señalética",
        "horas": 4,
    },
    "Identidad_Cultura_Emprendimiento": {
        "mencion": "TODAS", "grado": "4to",
        "competencia": "CF — Competencia de Ciudadanía y Emprendimiento",
        "descripcion": "Desarrolla la identidad cultural dominicana y caribeña vinculada al emprendimiento artístico.",
        "saberes_conceptuales": [
            "Identidad cultural dominicana y caribeña",
            "Historia del arte dominicano",
            "Emprendimiento y gestión de proyectos artísticos",
            "Derechos culturales y propiedad intelectual",
        ],
        "saberes_procedimentales": [
            "Analizar manifestaciones culturales del entorno",
            "Diseñar proyectos artísticos con visión emprendedora",
        ],
        "indicadores_logro": [
            "Valora y explica la identidad cultural dominicana en las artes",
            "Diseña un proyecto artístico con perspectiva de emprendimiento",
        ],
        "evidencias": "Proyecto de emprendimiento artístico-cultural",
        "horas": 2,
    },
    "Historia_Arte_Universal": {
        "mencion": "TODAS", "grado": "4to",
        "competencia": "CF — Pensamiento Lógico, Creativo y Crítico",
        "descripcion": "Analiza el desarrollo del arte universal desde la prehistoria hasta la era digital.",
        "saberes_conceptuales": [
            "Arte prehistórico, antiguo, medieval y renacentista",
            "Barroco, Neoclasicismo, Romanticismo e Impresionismo",
            "Vanguardias del siglo XX: Cubismo, Surrealismo, Expresionismo",
            "Arte contemporáneo y digital",
            "Arte dominicano y del Caribe en contexto universal",
        ],
        "saberes_procedimentales": [
            "Analizar obras de arte en su contexto histórico-cultural",
            "Comparar movimientos artísticos y sus características",
        ],
        "indicadores_logro": [
            "Sitúa cronológicamente los principales movimientos artísticos",
            "Analiza obras representativas de cada período",
            "Conecta el arte universal con expresiones artísticas dominicanas",
        ],
        "evidencias": "Análisis de obra de arte / Presentación oral o escrita",
        "horas": 4,
    },
    # ── MULTIMEDIA 5TO ────────────────────────────────────────────────────────
    "Diseño_Web": {
        "mencion": "MULTIMEDIA", "grado": "5to",
        "competencia": "DCM.2.1 — Producción Digital y Web",
        "descripcion": "Diseña y desarrolla sitios web funcionales aplicando principios de usabilidad y diseño visual.",
        "saberes_conceptuales": [
            "HTML y CSS básico: estructura y estilos",
            "Principios de UX/UI y usabilidad web",
            "Diseño responsivo y accesibilidad",
            "Herramientas: Figma, WordPress",
            "Tendencias en diseño web",
        ],
        "saberes_procedimentales": [
            "Crear páginas web con HTML y CSS",
            "Aplicar principios de diseño visual en interfaces",
            "Planificar y ejecutar proyectos web",
        ],
        "indicadores_logro": [
            "Diseña interfaces web siguiendo principios de usabilidad",
            "Crea páginas web funcionales con HTML y CSS",
            "Aplica diseño responsivo para múltiples dispositivos",
        ],
        "evidencias": "Sitio web funcional publicado o portafolio digital",
        "horas": 6,
    },
    "Diseño_Grafico": {
        "mencion": "MULTIMEDIA", "grado": "5to",
        "competencia": "DCM.2.2 — Comunicación Gráfica y Visual",
        "descripcion": "Desarrolla proyectos de comunicación gráfica utilizando herramientas digitales profesionales.",
        "saberes_conceptuales": [
            "Tipografía: clasificación, legibilidad y combinación",
            "Color en diseño gráfico: psicología y aplicación",
            "Identidad corporativa y branding",
            "Adobe Illustrator o Inkscape",
            "Diseño editorial: revistas, afiches, publicaciones",
        ],
        "saberes_procedimentales": [
            "Crear piezas gráficas profesionales para diferentes medios",
            "Desarrollar identidades visuales completas",
        ],
        "indicadores_logro": [
            "Diseña piezas gráficas con tipografía y color efectivos",
            "Crea sistemas de identidad visual para marcas o eventos",
            "Produce diseños editoriales (afiche, revista, brochure)",
        ],
        "evidencias": "Portafolio de diseño gráfico / Proyecto de identidad visual",
        "horas": 4,
    },
    "Publicidad_Creatividad": {
        "mencion": "MULTIMEDIA", "grado": "5to",
        "competencia": "DCM.2.3 — Comunicación Publicitaria",
        "descripcion": "Crea campañas publicitarias creativas aplicando estrategias de comunicación y marketing.",
        "saberes_conceptuales": [
            "Fundamentos de la publicidad y el marketing",
            "Estrategias creativas y Brief publicitario",
            "Publicidad digital y redes sociales",
            "Ética publicitaria y responsabilidad social",
        ],
        "saberes_procedimentales": [
            "Diseñar campañas publicitarias multimediales",
            "Crear contenido para redes sociales con propósito comunicativo",
        ],
        "indicadores_logro": [
            "Elabora briefs y estrategias creativas publicitarias",
            "Diseña campañas publicitarias para diferentes medios",
        ],
        "evidencias": "Campaña publicitaria completa (digital y/o impresa)",
        "horas": 3,
    },
    "Camara_Video": {
        "mencion": "MULTIMEDIA", "grado": "5to",
        "competencia": "DCM.2.4 — Operación de Cámara de Video",
        "descripcion": "Opera cámaras de video profesional aplicando técnicas de iluminación, composición y narrativa.",
        "saberes_conceptuales": [
            "Tipos de cámaras y configuraciones técnicas",
            "Composición cinematográfica: planos, ángulos, movimientos",
            "Iluminación para video: clave, relleno, contraluz",
            "Narrativa visual y lenguaje cinematográfico",
        ],
        "saberes_procedimentales": [
            "Operar cámaras de video con configuraciones manuales",
            "Planificar grabaciones con criterio narrativo",
        ],
        "indicadores_logro": [
            "Opera cámaras de video con dominio técnico",
            "Aplica principios de composición cinematográfica",
            "Planifica producciones de video con criterio artístico",
        ],
        "evidencias": "Cortometraje o pieza audiovisual editada",
        "horas": 4,
    },
    "Guion": {
        "mencion": "MULTIMEDIA", "grado": "5to",
        "competencia": "DCM.2.5 — Narrativa y Escritura Audiovisual",
        "descripcion": "Desarrolla guiones para producciones audiovisuales aplicando estructura dramática y lenguaje cinematográfico.",
        "saberes_conceptuales": [
            "Estructura del guión: formato literario y técnico",
            "Desarrollo de personajes y arcos narrativos",
            "Géneros audiovisuales: ficción, documental, publicidad",
            "Guión técnico y story board",
        ],
        "saberes_procedimentales": [
            "Escribir guiones en formato profesional",
            "Crear story boards para producciones",
        ],
        "indicadores_logro": [
            "Escribe guiones literarios y técnicos en formato profesional",
            "Crea personajes con motivaciones y conflictos claros",
            "Elabora story boards detallados para producciones",
        ],
        "evidencias": "Guión completo con story board de cortometraje",
        "horas": 4,
    },
    "Medios_Comunicacion": {
        "mencion": "MULTIMEDIA", "grado": "5to",
        "competencia": "DCM.2.6 — Análisis de Medios",
        "descripcion": "Analiza los medios de comunicación y su impacto en la sociedad dominicana.",
        "saberes_conceptuales": [
            "Historia y evolución de los medios de comunicación",
            "Medios digitales: redes sociales y su impacto social",
            "Ética en los medios y fake news",
            "El periodismo visual y fotoperiodismo",
        ],
        "saberes_procedimentales": [
            "Analizar críticamente mensajes mediáticos",
            "Producir contenido responsable para medios digitales",
        ],
        "indicadores_logro": [
            "Analiza el impacto de los medios en la sociedad dominicana",
            "Produce contenido mediático responsable y ético",
        ],
        "evidencias": "Análisis crítico de medios / Proyecto de comunicación",
        "horas": 2,
    },
    # ── MULTIMEDIA 6TO ────────────────────────────────────────────────────────
    "Produccion_Audiovisual": {
        "mencion": "MULTIMEDIA", "grado": "6to",
        "competencia": "DCM.3.1 — Producción Audiovisual Avanzada",
        "descripcion": "Planifica y ejecuta producciones audiovisuales completas integrando todas las etapas del proceso.",
        "saberes_conceptuales": [
            "Pre-producción: desarrollo, presupuesto, casting",
            "Producción: dirección, fotografía, sonido en set",
            "Post-producción: edición, corrección de color, sonorización",
            "Distribución y exhibición audiovisual",
        ],
        "saberes_procedimentales": [
            "Gestionar todas las etapas de una producción audiovisual",
            "Dirigir equipos técnicos y creativos",
            "Editar y post-producir material audiovisual",
        ],
        "indicadores_logro": [
            "Planifica y ejecuta proyectos audiovisuales completos",
            "Dirige y coordina equipos de producción",
            "Realiza post-producción profesional de video y audio",
        ],
        "evidencias": "Cortometraje o documental final producido y exhibido",
        "horas": 4,
    },
    "Animacion": {
        "mencion": "MULTIMEDIA", "grado": "6to",
        "competencia": "DCM.3.2 — Animación Digital",
        "descripcion": "Crea animaciones digitales 2D aplicando principios de animación y storytelling visual.",
        "saberes_conceptuales": [
            "Historia y principios de animación (Disney, Pixar)",
            "Animación 2D: frame a frame y motion graphics",
            "Introducción a animación 3D: modelado básico",
            "Software: Adobe Animate, Blender básico",
        ],
        "saberes_procedimentales": [
            "Crear animaciones 2D con principios de movimiento",
            "Desarrollar motion graphics para proyectos digitales",
        ],
        "indicadores_logro": [
            "Aplica principios de animación en proyectos digitales",
            "Crea animaciones 2D con movimiento fluido y expresivo",
            "Produce motion graphics para proyectos de comunicación",
        ],
        "evidencias": "Proyecto de animación o motion graphics publicado",
        "horas": 4,
    },
    "Edicion_Sonido": {
        "mencion": "MULTIMEDIA", "grado": "6to",
        "competencia": "DCM.3.3 — Edición, Sonido y Musicalización",
        "descripcion": "Edita y produce audio para proyectos multimedia aplicando técnicas profesionales.",
        "saberes_conceptuales": [
            "Grabación y captación de audio profesional",
            "Edición de audio con DAW (Audacity, GarageBand)",
            "Musicalización y diseño sonoro para video",
            "Mezcla y masterización básica",
        ],
        "saberes_procedimentales": [
            "Grabar, editar y mezclar audio para proyectos audiovisuales",
            "Crear bandas sonoras y diseños sonoros originales",
        ],
        "indicadores_logro": [
            "Graba y edita audio con calidad técnica adecuada",
            "Crea diseños sonoros para proyectos multimedia",
            "Realiza mezclas sincronizadas con imagen",
        ],
        "evidencias": "Banda sonora original para proyecto audiovisual",
        "horas": 4,
    },
    "Videoarte": {
        "mencion": "MULTIMEDIA", "grado": "6to",
        "competencia": "DCM.3.4 — Arte y Expresión Audiovisual",
        "descripcion": "Crea obras de videoarte explorando las posibilidades expresivas del video como medio artístico.",
        "saberes_conceptuales": [
            "Historia del videoarte: Nam June Paik, Bill Viola",
            "El video como medio de expresión artística contemporánea",
            "Instalaciones de video y arte digital interactivo",
            "Derechos de autor y licencias Creative Commons",
        ],
        "saberes_procedimentales": [
            "Crear obras de videoarte con intención conceptual",
            "Experimentar con edición no lineal y efectos visuales",
        ],
        "indicadores_logro": [
            "Crea obras de videoarte con concepto artístico definido",
            "Aplica técnicas de edición creativa y efectos visuales",
            "Contextualiza su obra en la tradición del videoarte",
        ],
        "evidencias": "Obra de videoarte exhibida o instalación",
        "horas": 5,
    },
    "Redes_Sociales": {
        "mencion": "MULTIMEDIA", "grado": "6to",
        "competencia": "DCM.3.5 — Comunicación Digital",
        "descripcion": "Gestiona estratégicamente las redes sociales para proyectos artísticos y culturales.",
        "saberes_conceptuales": [
            "Estrategia de contenidos para redes sociales",
            "Plataformas: Instagram, TikTok, YouTube, LinkedIn",
            "Métricas y analítica de redes sociales",
            "Marca personal del artista digital",
        ],
        "saberes_procedimentales": [
            "Planificar y ejecutar estrategias de contenido digital",
            "Crear y gestionar perfiles profesionales de artista",
        ],
        "indicadores_logro": [
            "Diseña estrategias de contenido para plataformas digitales",
            "Gestiona perfiles profesionales con criterio artístico",
            "Analiza métricas y ajusta estrategias de comunicación",
        ],
        "evidencias": "Portfolio digital / Campaña de redes sociales",
        "horas": 2,
    },
    # ── ARTES VISUALES 4TO ────────────────────────────────────────────────────
    "Lenguaje_Plastico_Visual": {
        "mencion": "ARTES VISUALES", "grado": "4to",
        "competencia": "AV.1.1 — Lenguaje Plástico y Visual",
        "descripcion": "Desarrolla la capacidad de expresión plástica utilizando los elementos formales del arte.",
        "saberes_conceptuales": [
            "Elementos plásticos: punto, línea, forma, color, textura",
            "Principios de composición artística",
            "Color: teoría, armonías y psicología",
            "Perspectiva y representación del espacio",
            "Medios y materiales plásticos tradicionales",
        ],
        "saberes_procedimentales": [
            "Aplicar elementos plásticos en composiciones visuales",
            "Experimentar con diferentes materiales y técnicas",
        ],
        "indicadores_logro": [
            "Aplica correctamente los elementos plásticos en sus obras",
            "Experimenta con diversas técnicas y materiales artísticos",
            "Crea composiciones originales con criterio estético personal",
        ],
        "evidencias": "Portafolio de obras plásticas en técnicas mixtas",
        "horas": 6,
    },
    "Dibujo_Tecnico_Artistico": {
        "mencion": "ARTES VISUALES", "grado": "4to",
        "competencia": "AV.1.2 — Representación Visual Técnica",
        "descripcion": "Domina técnicas de dibujo artístico y técnico para la representación precisa del mundo visual.",
        "saberes_conceptuales": [
            "Dibujo a pulso: encaje, proporción, sombreado",
            "Perspectiva cónica y axonométrica",
            "Retrato y figura humana: proporciones",
            "Naturaleza muerta y bodegón",
        ],
        "saberes_procedimentales": [
            "Representar objetos y figuras con precisión técnica",
            "Aplicar perspectiva en composiciones",
        ],
        "indicadores_logro": [
            "Dibuja objetos y figuras con proporciones correctas",
            "Aplica perspectiva en representaciones espaciales",
            "Realiza retratos y figura humana con técnica adecuada",
        ],
        "evidencias": "Cuaderno de dibujo con series técnicas y artísticas",
        "horas": 4,
    },
    "Pintura_Tecnicas_Mixtas": {
        "mencion": "ARTES VISUALES", "grado": "4to",
        "competencia": "AV.1.3 — Expresión Pictórica",
        "descripcion": "Experimenta con técnicas pictóricas variadas desarrollando una voz artística personal.",
        "saberes_conceptuales": [
            "Acuarela: técnica húmedo sobre húmedo y seco",
            "Acrílico: capas, veladuras y texturas",
            "Óleo: técnica directa e indirecta",
            "Técnicas mixtas: collage, encáustica, assemblage",
            "Historia del movimiento pictórico dominicano",
        ],
        "saberes_procedimentales": [
            "Dominar técnicas básicas de pintura",
            "Crear obras con intención expresiva personal",
        ],
        "indicadores_logro": [
            "Aplica técnicas de acuarela, acrílico y/o óleo con destreza",
            "Crea obras originales con técnicas mixtas",
            "Expresa ideas y emociones a través de la pintura",
        ],
        "evidencias": "Serie de obras pictóricas / Exposición artística",
        "horas": 4,
    },
    # ── ARTES VISUALES 5TO ────────────────────────────────────────────────────
    "Escultura_Ceramica": {
        "mencion": "ARTES VISUALES", "grado": "5to",
        "competencia": "AV.2.1 — Expresión Tridimensional",
        "descripcion": "Crea objetos artísticos tridimensionales con diferentes materiales y técnicas.",
        "saberes_conceptuales": [
            "Escultura: modelado, talla y construcción",
            "Arcilla y cerámica: técnicas de construcción y quema",
            "Escultura con materiales reciclados y alternativos",
            "Escultura dominicana: artistas y tradiciones",
        ],
        "saberes_procedimentales": [
            "Modelar piezas con arcilla usando técnicas tradicionales",
            "Construir esculturas con materiales variados",
        ],
        "indicadores_logro": [
            "Modela y construye piezas tridimensionales con técnica",
            "Produce piezas cerámicas completando el proceso",
            "Crea esculturas con materiales alternativos",
        ],
        "evidencias": "Serie de piezas escultóricas o cerámicas",
        "horas": 5,
    },
    "Grabado_Serigrafia": {
        "mencion": "ARTES VISUALES", "grado": "5to",
        "competencia": "AV.2.2 — Arte de Reproducción",
        "descripcion": "Domina técnicas de grabado y serigrafía como formas de expresión artística.",
        "saberes_conceptuales": [
            "Historia del grabado: xilografía, calcografía",
            "Serigrafía: proceso y aplicaciones artísticas",
            "Grabado en linóleo y materiales alternativos",
        ],
        "saberes_procedimentales": [
            "Realizar grabados en linóleo",
            "Ejecutar el proceso completo de serigrafía",
        ],
        "indicadores_logro": [
            "Ejecuta grabados con técnica de reducción y estampado",
            "Realiza serigrafía artística completa",
            "Produce series de estampas con coherencia artística",
        ],
        "evidencias": "Serie de grabados / Serigrafías",
        "horas": 4,
    },
    "Diseno_Comunicacion_Visual": {
        "mencion": "ARTES VISUALES", "grado": "5to",
        "competencia": "AV.2.3 — Diseño y Comunicación Visual",
        "descripcion": "Aplica principios de diseño gráfico en proyectos de comunicación visual.",
        "saberes_conceptuales": [
            "Tipografía aplicada a proyectos visuales",
            "Diseño de cartel y comunicación gráfica",
            "Imagen digital: Photoshop / GIMP",
            "Diseño para impresión y pantalla",
        ],
        "saberes_procedimentales": [
            "Crear piezas gráficas para comunicación visual",
            "Usar herramientas digitales en proyectos artísticos",
        ],
        "indicadores_logro": [
            "Diseña carteles y piezas de comunicación visual efectivas",
            "Usa herramientas digitales para crear arte visual",
        ],
        "evidencias": "Serie de carteles / Proyecto de comunicación visual",
        "horas": 4,
    },
    # ── ARTES VISUALES 6TO ────────────────────────────────────────────────────
    "Arte_Digital_Multimedia": {
        "mencion": "ARTES VISUALES", "grado": "6to",
        "competencia": "AV.3.1 — Arte Digital",
        "descripcion": "Crea obras de arte digital integrando herramientas tecnológicas y conceptos artísticos.",
        "saberes_conceptuales": [
            "Arte digital: instalaciones, net art, arte generativo",
            "Fotografía artística avanzada y manipulación digital",
            "Video arte y arte interactivo",
            "NFT y arte en el mundo digital",
        ],
        "saberes_procedimentales": [
            "Crear obras de arte digital con concepto artístico",
            "Integrar tecnología en proyectos artísticos",
        ],
        "indicadores_logro": [
            "Crea obras de arte digital con intención conceptual clara",
            "Integra herramientas tecnológicas en proyectos artísticos",
        ],
        "evidencias": "Exposición de arte digital / Portfolio digital",
        "horas": 4,
    },
    "Proyecto_Artes_Visuales": {
        "mencion": "ARTES VISUALES", "grado": "6to",
        "competencia": "AV.3.2 — Proyecto de Producción en Artes Visuales",
        "descripcion": "Desarrolla un proyecto artístico personal de envergadura que integra todo el aprendizaje del bachillerato.",
        "saberes_conceptuales": [
            "Gestión de proyectos artísticos: planificación, ejecución",
            "Curatoría y montaje de exposiciones",
            "Portafolio artístico profesional",
            "Artistas dominicanos contemporáneos como referentes",
        ],
        "saberes_procedimentales": [
            "Desarrollar proyecto artístico personal con metodología",
            "Montar y presentar exposición artística",
        ],
        "indicadores_logro": [
            "Desarrolla un proyecto artístico original de envergadura",
            "Monta y presenta una exposición artística con criterio curatorial",
            "Produce un portafolio artístico profesional",
        ],
        "evidencias": "Exposición de obra propia / Portafolio artístico profesional",
        "horas": 6,
    },
    # ── MÚSICA 4TO ────────────────────────────────────────────────────────────
    "Teoria_Solfeo": {
        "mencion": "MÚSICA", "grado": "4to",
        "competencia": "MUS.1.1 — Lenguaje Musical Fundamental",
        "descripcion": "Desarrolla el lenguaje musical básico: lectura, escritura y comprensión teórica.",
        "saberes_conceptuales": [
            "El pentagrama, claves y notas musicales",
            "Figuras y valores rítmicos",
            "Compases: binario, ternario, cuaternario",
            "Escalas mayores y menores, intervalos",
            "Acordes básicos y dinámica musical",
        ],
        "saberes_procedimentales": [
            "Leer y escribir música en notación convencional",
            "Entonar melodías y solfear con precisión",
        ],
        "indicadores_logro": [
            "Lee y escribe música en notación convencional",
            "Solfea melodías con entonación y ritmo correctos",
            "Identifica elementos del lenguaje musical en obras",
        ],
        "evidencias": "Dictados musicales / Ejercicios de solfeo",
        "horas": 4,
    },
    "Instrumento_Principal_I": {
        "mencion": "MÚSICA", "grado": "4to",
        "competencia": "MUS.1.2 — Ejecución Instrumental Básica",
        "descripcion": "Desarrolla la técnica básica del instrumento asignado.",
        "saberes_conceptuales": [
            "Historia y características del instrumento",
            "Postura, técnica y mantenimiento del instrumento",
            "Repertorio básico dominicano e internacional",
            "Escalas y ejercicios técnicos",
        ],
        "saberes_procedimentales": [
            "Ejecutar el instrumento con técnica básica correcta",
            "Interpretar piezas del repertorio básico asignado",
        ],
        "indicadores_logro": [
            "Ejecuta el instrumento con postura y técnica correcta",
            "Interpreta piezas básicas del repertorio asignado",
            "Demuestra disciplina en la práctica instrumental",
        ],
        "evidencias": "Recital o audición de fin de período",
        "horas": 6,
    },
    "Coro_Conjunto_Musical_I": {
        "mencion": "MÚSICA", "grado": "4to",
        "competencia": "MUS.1.3 — Musicalización Grupal",
        "descripcion": "Desarrolla la capacidad de hacer música en conjunto aplicando técnicas corales.",
        "saberes_conceptuales": [
            "Técnica vocal: respiración, emisión, resonancia",
            "Tipos de voces vocales",
            "Repertorio coral dominicano y latinoamericano",
            "Dinámica y expresión en coro",
        ],
        "saberes_procedimentales": [
            "Cantar en coro con afinación y expresión",
            "Memorizar e interpretar repertorio coral",
        ],
        "indicadores_logro": [
            "Canta en coro con afinación y expresión adecuadas",
            "Interpreta repertorio coral dominicano con calidad",
            "Respeta indicaciones del director en ensayos",
        ],
        "evidencias": "Presentación coral pública o grabación",
        "horas": 3,
    },
    # ── MÚSICA 5TO ────────────────────────────────────────────────────────────
    "Instrumento_Principal_II": {
        "mencion": "MÚSICA", "grado": "5to",
        "competencia": "MUS.2.1 — Ejecución Instrumental Intermedia",
        "descripcion": "Profundiza la técnica instrumental con repertorio de mayor complejidad.",
        "saberes_conceptuales": [
            "Técnica instrumental intermedia",
            "Fraseo musical, articulación y dinámica",
            "Repertorio clásico, contemporáneo y dominicano",
            "Análisis de obras musicales",
        ],
        "saberes_procedimentales": [
            "Ejecutar repertorio intermedio con dominio técnico",
            "Interpretar con expresividad musical",
        ],
        "indicadores_logro": [
            "Ejecuta obras de nivel intermedio con técnica y musicalidad",
            "Interpreta con expresión y fraseo adecuados",
            "Analiza obras del repertorio en su contexto histórico",
        ],
        "evidencias": "Recital de fin de año con obras variadas",
        "horas": 6,
    },
    "Armonia_Contrapunto": {
        "mencion": "MÚSICA", "grado": "5to",
        "competencia": "MUS.2.2 — Análisis y Composición Musical",
        "descripcion": "Comprende y aplica los principios de la armonía tonal y el contrapunto.",
        "saberes_conceptuales": [
            "Formación de acordes y sus inversiones",
            "Progresiones armónicas funcionales",
            "Contrapunto: movimientos y especies básicas",
            "Análisis armónico de obras clásicas y populares",
        ],
        "saberes_procedimentales": [
            "Analizar progresiones armónicas en obras",
            "Componer melodías con acompañamiento armónico",
        ],
        "indicadores_logro": [
            "Construye y clasifica acordes en diferentes tonalidades",
            "Analiza la armonía de obras musicales variadas",
            "Compone ejercicios de armonía básica",
        ],
        "evidencias": "Composición armónica original / Análisis de obra",
        "horas": 4,
    },
    "Musica_Dominicana_Caribe": {
        "mencion": "MÚSICA", "grado": "5to",
        "competencia": "MUS.2.3 — Identidad Musical Dominicana",
        "descripcion": "Estudia y ejecuta la música dominicana y del Caribe en su contexto cultural.",
        "saberes_conceptuales": [
            "Géneros dominicanos: merengue, bachata, palo, salve",
            "Instrumentos típicos: tambora, güira, acordeón",
            "Ritmos del Caribe: son, cumbia, reggae, calipso",
            "Compositores e intérpretes dominicanos destacados",
        ],
        "saberes_procedimentales": [
            "Interpretar ritmos y géneros musicales dominicanos",
            "Analizar la estructura de géneros caribeños",
        ],
        "indicadores_logro": [
            "Identifica y ejecuta géneros musicales dominicanos",
            "Analiza el contexto histórico-cultural de la música dominicana",
            "Valora la diversidad musical del Caribe",
        ],
        "evidencias": "Presentación de repertorio de música dominicana",
        "horas": 3,
    },
    "Composicion_Arreglos": {
        "mencion": "MÚSICA", "grado": "5to",
        "competencia": "MUS.2.4 — Composición y Arreglos Básicos",
        "descripcion": "Crea composiciones y arreglos musicales originales aplicando principios armónicos.",
        "saberes_conceptuales": [
            "Proceso de composición musical",
            "Arreglos para pequeño ensamble",
            "Forma musical: binaria, ternaria, rondó",
            "Software de notación: MuseScore / Sibelius básico",
        ],
        "saberes_procedimentales": [
            "Componer piezas musicales originales cortas",
            "Realizar arreglos simples para grupos disponibles",
        ],
        "indicadores_logro": [
            "Compone piezas originales con estructura definida",
            "Realiza arreglos musicales básicos para ensamble",
            "Usa software de notación para transcribir sus obras",
        ],
        "evidencias": "Composición original escrita y ejecutada",
        "horas": 4,
    },
    # ── MÚSICA 6TO ────────────────────────────────────────────────────────────
    "Instrumento_Principal_III": {
        "mencion": "MÚSICA", "grado": "6to",
        "competencia": "MUS.3.1 — Ejecución Instrumental Avanzada",
        "descripcion": "Desarrolla dominio técnico e interpretativo avanzado del instrumento principal.",
        "saberes_conceptuales": [
            "Técnica instrumental avanzada",
            "Interpretación con profundidad musical",
            "Repertorio de concierto: clásico, contemporáneo y dominicano",
            "La carrera musical: oportunidades profesionales en RD",
        ],
        "saberes_procedimentales": [
            "Ejecutar obras avanzadas con dominio técnico e interpretativo",
            "Preparar y presentar un recital completo",
        ],
        "indicadores_logro": [
            "Ejecuta obras avanzadas con dominio técnico e interpretativo",
            "Presenta un recital completo con obras variadas",
            "Demuestra musicalidad y madurez interpretativa",
        ],
        "evidencias": "Recital de graduación / Concierto final",
        "horas": 6,
    },
    "Produccion_Musical_Digital": {
        "mencion": "MÚSICA", "grado": "6to",
        "competencia": "MUS.3.2 — Producción Musical Digital",
        "descripcion": "Produce música digital utilizando DAW y herramientas de producción contemporáneas.",
        "saberes_conceptuales": [
            "DAW (Digital Audio Workstation): GarageBand, FL Studio",
            "MIDI y síntesis de sonido básica",
            "Mezcla y masterización básica",
            "Producción de géneros dominicanos en formato digital",
        ],
        "saberes_procedimentales": [
            "Producir pistas musicales con DAW",
            "Integrar instrumentos reales y virtuales en producción",
        ],
        "indicadores_logro": [
            "Produce pistas musicales con calidad técnica en DAW",
            "Integra instrumentos acústicos y digitales",
            "Crea producciones de géneros dominicanos en formato digital",
        ],
        "evidencias": "EP o single producido y masterizado",
        "horas": 5,
    },
    # ── TEATRO 4TO ────────────────────────────────────────────────────────────
    "Expresion_Corporal_Movimiento": {
        "mencion": "TEATRO", "grado": "4to",
        "competencia": "TEA.1.1 — Expresión Corporal y Movimiento Escénico",
        "descripcion": "Desarrolla la conciencia y dominio del cuerpo como instrumento expresivo del actor.",
        "saberes_conceptuales": [
            "El cuerpo como instrumento expresivo del actor",
            "Conciencia corporal: tensión, relajación, equilibrio",
            "El espacio escénico y su uso",
            "Ritmo y tiempo en la expresión corporal",
        ],
        "saberes_procedimentales": [
            "Desarrollar conciencia corporal en el espacio escénico",
            "Aplicar técnicas de relajación y tensión expresiva",
        ],
        "indicadores_logro": [
            "Demuestra conciencia corporal y dominio del espacio",
            "Aplica técnicas de expresión corporal con intención comunicativa",
            "Crea secuencias de movimiento con sentido expresivo",
        ],
        "evidencias": "Ejercicio de expresión corporal sin diálogo",
        "horas": 4,
    },
    "Tecnica_Vocal_Diccion": {
        "mencion": "TEATRO", "grado": "4to",
        "competencia": "TEA.1.2 — Instrumento Vocal del Actor",
        "descripcion": "Desarrolla la voz como instrumento con técnica, proyección y expresividad.",
        "saberes_conceptuales": [
            "Anatomía de la voz: aparato fonador",
            "Respiración diafragmática y soporte vocal",
            "Resonadores y proyección de la voz",
            "Dicción y articulación para el teatro",
        ],
        "saberes_procedimentales": [
            "Desarrollar respiración diafragmática para actuación",
            "Proyectar la voz con claridad y sin esfuerzo",
        ],
        "indicadores_logro": [
            "Proyecta la voz con claridad en el espacio escénico",
            "Articula con dicción correcta en diferentes registros",
            "Adapta la voz a personajes y situaciones dramáticas",
        ],
        "evidencias": "Monólogo con trabajo vocal evidente",
        "horas": 3,
    },
    "Actuacion_I": {
        "mencion": "TEATRO", "grado": "4to",
        "competencia": "TEA.1.3 — Actuación Básica",
        "descripcion": "Desarrolla fundamentos de la actuación teatral con improvisación y técnicas básicas.",
        "saberes_conceptuales": [
            "El juego dramático y la improvisación",
            "Personaje: construcción y motivaciones básicas",
            "El conflicto dramático y la acción escénica",
            "El ensayo y la repetición en el proceso creativo",
        ],
        "saberes_procedimentales": [
            "Improvisar escenas con objetivos claros",
            "Construir personajes con motivaciones definidas",
        ],
        "indicadores_logro": [
            "Improvisa con presencia escénica y objetivos claros",
            "Construye personajes con motivaciones coherentes",
            "Actúa en escenas cortas con concentración y técnica",
        ],
        "evidencias": "Presentación de escenas cortas o improvisaciones",
        "horas": 6,
    },
    # ── TEATRO 5TO ────────────────────────────────────────────────────────────
    "Actuacion_II": {
        "mencion": "TEATRO", "grado": "5to",
        "competencia": "TEA.2.1 — Actuación Intermedia",
        "descripcion": "Profundiza en el método Stanislavski para la construcción de personajes complejos.",
        "saberes_conceptuales": [
            "Sistema Stanislavski: si mágico, circunstancias dadas",
            "Objetivos, super-objetivos y acción física",
            "Brecht y el teatro épico: distanciamiento",
            "Análisis de textos dramáticos",
        ],
        "saberes_procedimentales": [
            "Aplicar el método Stanislavski en la actuación",
            "Analizar textos dramáticos para su interpretación",
        ],
        "indicadores_logro": [
            "Aplica principios del método Stanislavski",
            "Construye personajes con objetivos y subtexto",
            "Interpreta textos con profundidad y verdad escénica",
        ],
        "evidencias": "Escena de obra clásica o contemporánea",
        "horas": 6,
    },
    "Dramaturgia_Guion_Teatral": {
        "mencion": "TEATRO", "grado": "5to",
        "competencia": "TEA.2.2 — Escritura Dramática",
        "descripcion": "Desarrolla habilidades de escritura dramática para textos teatrales originales.",
        "saberes_conceptuales": [
            "Estructura dramática: planteamiento, desarrollo, desenlace",
            "Tipos de conflicto dramático",
            "Diálogo teatral y subtexto",
            "Teatro dominicano: autores y obras representativas",
        ],
        "saberes_procedimentales": [
            "Escribir textos dramáticos con estructura clara",
            "Crear personajes con voz propia en el diálogo",
        ],
        "indicadores_logro": [
            "Escribe obras teatrales con estructura dramática coherente",
            "Crea personajes con diálogos auténticos y reveladores",
            "Adapta textos literarios al formato teatral",
        ],
        "evidencias": "Obra teatral corta escrita y presentada",
        "horas": 4,
    },
    "Escenografia_Iluminacion": {
        "mencion": "TEATRO", "grado": "5to",
        "competencia": "TEA.2.3 — Diseño Escénico",
        "descripcion": "Diseña y construye elementos escenográficos e iluminación para producciones teatrales.",
        "saberes_conceptuales": [
            "Historia de la escenografía teatral",
            "Elementos de la escenografía: ciclorama, bambalinas",
            "Iluminación teatral: tipos de luces y efectos",
            "Vestuario y caracterización del personaje",
        ],
        "saberes_procedimentales": [
            "Diseñar y construir escenografías básicas",
            "Planificar iluminación para producciones teatrales",
        ],
        "indicadores_logro": [
            "Diseña escenografías que apoyan la narrativa teatral",
            "Planifica y ejecuta iluminación básica para escenas",
            "Crea vestuario y caracterización coherente con el personaje",
        ],
        "evidencias": "Diseño escenográfico para montaje teatral",
        "horas": 3,
    },
    # ── TEATRO 6TO ────────────────────────────────────────────────────────────
    "Actuacion_III": {
        "mencion": "TEATRO", "grado": "6to",
        "competencia": "TEA.3.1 — Actuación Avanzada y Proyecto Escénico",
        "descripcion": "Desarrolla un proyecto escénico completo integrando todas las herramientas actorales adquiridas.",
        "saberes_conceptuales": [
            "Construcción de un papel de envergadura",
            "Proceso de montaje: ensayos, temporada",
            "Teatro contemporáneo dominicano",
            "La carrera teatral: oportunidades en RD y el Caribe",
        ],
        "saberes_procedimentales": [
            "Protagonizar obras de mayor complejidad dramática",
            "Colaborar en el proceso completo de montaje",
        ],
        "indicadores_logro": [
            "Protagoniza obras con madurez y profundidad actoral",
            "Colabora efectivamente en el proceso de montaje",
            "Demuestra manejo de todas las herramientas actorales",
        ],
        "evidencias": "Obra teatral completa presentada al público",
        "horas": 6,
    },
    "Montaje_Teatral_Final": {
        "mencion": "TEATRO", "grado": "6to",
        "competencia": "TEA.3.2 — Producción Teatral",
        "descripcion": "Gestiona y produce una obra teatral completa como proyecto final del bachillerato.",
        "saberes_conceptuales": [
            "Gestión cultural y producción teatral",
            "Relaciones con el público y difusión",
            "Presupuesto y financiamiento de proyectos teatrales",
            "El teatro como empresa cultural sostenible",
        ],
        "saberes_procedimentales": [
            "Planificar y ejecutar una producción teatral completa",
            "Gestionar recursos humanos y materiales",
        ],
        "indicadores_logro": [
            "Planifica y ejecuta una producción teatral completa",
            "Gestiona recursos con eficiencia y creatividad",
            "Presenta la obra al público con éxito",
        ],
        "evidencias": "Producción teatral completa: obra presentada al público",
        "horas": 5,
    },
    # ── DANZA 4TO ─────────────────────────────────────────────────────────────
    "Tecnica_Danza_Clasica_I": {
        "mencion": "DANZA", "grado": "4to",
        "competencia": "DAN.1.1 — Técnica Clásica Básica",
        "descripcion": "Desarrolla la técnica básica de ballet como fundamento para las técnicas dancísticas.",
        "saberes_conceptuales": [
            "Postura y alineación corporal en ballet",
            "Las cinco posiciones de pies y brazos",
            "Vocabulario básico: pliés, tendus, dégagés",
            "Port de bras y coordinación de brazos",
            "Musicalidad y fraseo en danza",
        ],
        "saberes_procedimentales": [
            "Ejecutar ejercicios de barra con técnica correcta",
            "Realizar ejercicios de centro con coordinación",
        ],
        "indicadores_logro": [
            "Ejecuta ejercicios de barra con postura y técnica correcta",
            "Realiza combinaciones de centro con coordinación",
            "Demuestra musicalidad en la ejecución",
        ],
        "evidencias": "Evaluación técnica / Video de clase",
        "horas": 5,
    },
    "Tecnica_Danza_Folklorica_I": {
        "mencion": "DANZA", "grado": "4to",
        "competencia": "DAN.1.2 — Identidad Dancística Dominicana",
        "descripcion": "Estudia y ejecuta las danzas folklóricas dominicanas como patrimonio cultural.",
        "saberes_conceptuales": [
            "Orígenes de la danza folklórica dominicana",
            "Manifestaciones dancísticas: palo, salve, tumba, gagá",
            "Indumentaria y elementos escénicos del folklore",
            "La danza como expresión de identidad cultural",
        ],
        "saberes_procedimentales": [
            "Ejecutar danzas folklóricas dominicanas con técnica básica",
            "Investigar manifestaciones culturales locales",
        ],
        "indicadores_logro": [
            "Ejecuta danzas folklóricas con calidad técnica",
            "Explica el contexto cultural de cada danza",
            "Valora el folklore como expresión de identidad nacional",
        ],
        "evidencias": "Presentación folklórica en evento escolar",
        "horas": 4,
    },
    "Expresion_Corporal_Danza": {
        "mencion": "DANZA", "grado": "4to",
        "competencia": "DAN.1.3 — Acondicionamiento para la Danza",
        "descripcion": "Desarrolla las capacidades físicas necesarias para la práctica segura de la danza.",
        "saberes_conceptuales": [
            "Anatomía básica aplicada a la danza",
            "Calentamiento, elongación y enfriamiento",
            "Flexibilidad y fuerza para bailarines",
            "Prevención de lesiones en danza",
        ],
        "saberes_procedimentales": [
            "Ejecutar rutinas de calentamiento y elongación",
            "Desarrollar flexibilidad y fuerza para la danza",
        ],
        "indicadores_logro": [
            "Ejecuta rutinas de calentamiento correctamente",
            "Demuestra mejoras en flexibilidad y fuerza",
            "Aplica principios de cuidado corporal en la práctica",
        ],
        "evidencias": "Evaluación de condición física / Registro de progreso",
        "horas": 3,
    },
    # ── DANZA 5TO ─────────────────────────────────────────────────────────────
    "Tecnica_Danza_Clasica_II": {
        "mencion": "DANZA", "grado": "5to",
        "competencia": "DAN.2.1 — Técnica Clásica Intermedia",
        "descripcion": "Profundiza en la técnica de ballet y danza clásica con mayor complejidad.",
        "saberes_conceptuales": [
            "Vocabulario intermedio de ballet",
            "Allegro y adagio en la técnica clásica",
            "Zapatillas de punta para estudiantes femeninas",
            "Variaciones del repertorio clásico",
        ],
        "saberes_procedimentales": [
            "Ejecutar combinaciones intermedias con técnica",
            "Interpretar variaciones del repertorio clásico",
        ],
        "indicadores_logro": [
            "Ejecuta combinaciones intermedias con técnica y estilo",
            "Interpreta variaciones del repertorio clásico",
            "Demuestra musicalidad y control en la ejecución",
        ],
        "evidencias": "Variación de ballet presentada en espectáculo",
        "horas": 5,
    },
    "Danza_Moderna_Contemporanea": {
        "mencion": "DANZA", "grado": "5to",
        "competencia": "DAN.2.2 — Técnica Moderna y Contemporánea",
        "descripcion": "Desarrolla vocabulario de danza moderna y contemporánea.",
        "saberes_conceptuales": [
            "Historia de la danza moderna: Duncan, Graham",
            "Técnica Graham: contraction y release",
            "Danza contemporánea e improvisación",
            "El cuerpo en el espacio: kinesfera y niveles",
        ],
        "saberes_procedimentales": [
            "Ejecutar técnica Graham y vocabulario moderno",
            "Explorar la improvisación como herramienta creativa",
        ],
        "indicadores_logro": [
            "Ejecuta vocabulario de danza moderna con técnica",
            "Improvisa con conciencia del cuerpo y espacio",
            "Crea frases de movimiento con calidad expresiva",
        ],
        "evidencias": "Solo o dúo de danza moderna/contemporánea",
        "horas": 4,
    },
    "Composicion_Coreografica_I": {
        "mencion": "DANZA", "grado": "5to",
        "competencia": "DAN.2.3 — Creación Coreográfica",
        "descripcion": "Desarrolla herramientas de composición coreográfica para la creación de obras.",
        "saberes_conceptuales": [
            "Elementos de la danza: espacio, tiempo, energía, cuerpo",
            "Principios de composición: unidad, variedad",
            "Formas coreográficas: ABA, tema y variación",
            "Relación danza-música en la creación",
        ],
        "saberes_procedimentales": [
            "Aplicar principios de composición en frases de movimiento",
            "Desarrollar estudios coreográficos con estructura",
        ],
        "indicadores_logro": [
            "Aplica elementos de la danza en la composición",
            "Crea obras coreográficas con estructura clara",
            "Trabaja el proceso creativo con metodología",
        ],
        "evidencias": "Estudio coreográfico original presentado",
        "horas": 4,
    },
    # ── DANZA 6TO ─────────────────────────────────────────────────────────────
    "Composicion_Coreografica_II": {
        "mencion": "DANZA", "grado": "6to",
        "competencia": "DAN.3.1 — Proyecto Coreográfico Final",
        "descripcion": "Crea un proyecto coreográfico de envergadura como culminación del bachillerato.",
        "saberes_conceptuales": [
            "Proceso coreográfico completo: concept, research, creation",
            "La danza en el mundo contemporáneo dominicano",
            "Montaje y producción de espectáculo de danza",
            "La carrera en danza: oportunidades en RD",
        ],
        "saberes_procedimentales": [
            "Crear un proyecto coreográfico completo",
            "Dirigir y montar un espectáculo de danza",
        ],
        "indicadores_logro": [
            "Crea un proyecto coreográfico original de envergadura",
            "Monta y presenta un espectáculo de danza completo",
            "Demuestra madurez artística en su propuesta",
        ],
        "evidencias": "Espectáculo de danza presentado al público",
        "horas": 5,
    },
    "Danza_Urbana_Contemporanea": {
        "mencion": "DANZA", "grado": "6to",
        "competencia": "DAN.3.2 — Danza Urbana y Culturas Populares",
        "descripcion": "Estudia y ejecuta estilos de danza urbana y contemporánea dominicana.",
        "saberes_conceptuales": [
            "Hip hop, reggaeton dancehall y breakdance",
            "Danza urbana dominicana: influencias y estilos",
            "La danza como expresión de identidad juvenil",
            "Freestyle e improvisación urbana",
        ],
        "saberes_procedimentales": [
            "Ejecutar estilos de danza urbana básicos",
            "Crear rutinas de danza urbana original",
        ],
        "indicadores_logro": [
            "Ejecuta estilos de danza urbana con técnica y estilo",
            "Crea rutinas de danza urbana con identidad propia",
            "Valora la danza urbana como expresión cultural contemporánea",
        ],
        "evidencias": "Battle o presentación de danza urbana",
        "horas": 3,
    },
}

CURRICULUM_MULTIMEDIA = {
    k: v for k, v in CURRICULUM_ARTES.items()
    if v.get("mencion") in ("MULTIMEDIA", "TODAS")
}

CLUSTER_META = [
    {"label": "Alto rendimiento estable",    "color": "#4dffb4", "icon": "⭐",
     "desc": "Buen desempeño académico y emocional. Bajo riesgo.",
     "accion": "Mantener seguimiento regular. Oportunidades de liderazgo."},
    {"label": "Rendimiento medio, conducta variable", "color": "#c8f060", "icon": "📊",
     "desc": "Notas aceptables pero con irregularidades conductuales.",
     "accion": "Refuerzo de hábitos. Entrevista trimestral."},
    {"label": "Riesgo conductual",            "color": "#ffc94d", "icon": "⚠️",
     "desc": "Conflictos frecuentes o bajo autocontrol. Académico variable.",
     "accion": "Intervención conductual. Coordinación con psicología."},
    {"label": "Caso silencioso",              "color": "#60b8f0", "icon": "🔇",
     "desc": "Alto rendimiento pero señales de malestar emocional.",
     "accion": "Entrevista de bienestar. Seguimiento emocional discreto."},
    {"label": "En crisis – intervención urgente", "color": "#ff6b6b", "icon": "🚨",
     "desc": "Múltiples indicadores de riesgo simultáneos.",
     "accion": "Intervención inmediata. Reporte a coordinación y psicología."},
]

DB_TABLAS_META = {
    "estudiantes":              {"label": "Estudiantes",             "icon": "👥"},
    "materias_calificaciones":  {"label": "Calificaciones",          "icon": "📊"},
    "asistencia":               {"label": "Asistencia",              "icon": "📅"},
    "reportes":                 {"label": "Reportes",                "icon": "📋"},
    "cuaderno_anecdotico":      {"label": "Cuaderno Anecdótico",     "icon": "📓"},
    "logros":                   {"label": "Logros",                  "icon": "🏆"},
    "historial_planificaciones":{"label": "Planificaciones",         "icon": "📝"},
    "registro_liceo":           {"label": "Registro Liceo",          "icon": "🏫"},
    "ml_clusters":              {"label": "Clusters ML",             "icon": "🔬"},
    "recovery_tokens":          {"label": "Tokens Recuperación",     "icon": "🔑"},
}

DEFAULTS_CENTRO = {
    "nombre":    "Centro Educativo en Artes Benito Juárez",
    "modalidad": "Modalidad en Artes · Nivel Secundario",
    "direccion": "Prolongación Ovando, Cristo Rey, Santo Domingo, D.N.",
    "pais":      "República Dominicana",
    "telefono":  "(809) 563-0241",
    "email":     "centroenartesbenitojuarez@gmail.com",
    "logo_base64": None,
}
