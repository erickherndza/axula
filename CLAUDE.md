# CLAUDE.md — TecnoAuladom / Axula
# Contexto específico de este proyecto. Claude Code lee primero ~/.claude/CLAUDE.md
# y luego este archivo — ambos aplican en conjunto.

---

## Stack

- Flask + SQLite (WAL mode) + Python 3 + ReportLab + openpyxl + Groq API
- Arquitectura Blueprint: /core/ + /routes/ (20 blueprints) + app.py factory
- Iniciar: cd /Users/erickhernandez/elearning && python3 app.py
- DB: database.db

## Patrones críticos — nunca romper

- _normalizar_rol()         # normalización de roles
- _get_config_centro()      # datos institucionales desde BD
- _anio_escolar_actual()    # año escolar activo
- CSRF: header X-CSRF-Token en todos los POST
- CSS: NUNCA hardcodear colores — siempre var(--surface), var(--border), var(--text)
- data-theme NUNCA en <html> — lo maneja theme.js

## Tema UI

Power BI light mode · Teal: #038C8C, #024959, #012840

## Módulos completados

- Autenticación y 8 roles
- Expediente estudiantil (ind_conducta, ind_psico, ind_academico, ind_logros)
- Boletín PDF con header institucional
- Acuerdo-compromiso en /acuerdo/<est_id> (página dedicada, no modal)
- 4 portales administrativos (Secretaría, Digitador, Finanzas, Evaluación Competencias)
- Evaluación por competencias Ordenanza 04-2023
- Generación PDF/Excel
- Registro de estudiantes MVP
- **Carga masiva de notas desde PDF** — scripts/cargar_notas_pdf.py (2026-06-27)

## Datos cargados en BD (año escolar 2025-2026)

- 7,493 registros en materias_calificaciones
- 772 alumnos procesados (1ERO–6TO, todas las secciones y menciones)
- 771 con tiene_notas=1
- Distribución: 1ERO=1413 · 2DO=952 · 3ERO=1543 · 4TO=1220 · 5TO=1282 · 6TO=1083
- 6 alumnos sin match en BD (nombres distintos entre PDF y sistema)
- 66 con datos parciales (páginas con `###` = período incompleto)

## Script de carga de notas — scripts/cargar_notas_pdf.py

```bash
# Dry-run (no escribe en BD)
.venv/bin/python3 scripts/cargar_notas_pdf.py --dry-run

# Carga real
.venv/bin/python3 scripts/cargar_notas_pdf.py
```

- Fuente: PDFs en /notas/ (1 página por alumno, pypdf para extracción)
- Extrae: nombre, sección, mención (4TO-6TO), PC1-PC4, CF por materia
- Materias académicas: 9 (primer ciclo) / 7 (segundo ciclo)
- Materias técnicas: 6-8 por mención (MÚSICA/TEATRO/ARTES VISUALES/MULTIMEDIA)
- Matching: exacto → fuzzy 0.82 (difflib.SequenceMatcher)
- `###` en un período → se guarda como 0.0 (boletín incompleto)
- PDFs en /notas/: "Boletin de calificaciones AC Xer. Grado.pdf"

## Credenciales sistema (passwords reseteados 2026-06-27)

| Usuario | Password | Rol |
|---------|----------|-----|
| directora | 1 | Directora |
| admin | Admin2026! | Coordinador General |
| secre01 | Secre2026! | Secretaria Docente |
| kerlynf | Digit2026! | Digitador |
| rodriguez | Conta2026! | Aux. Contabilidad |
| sicologa01 | Psico2026! | Psicóloga |

## En desarrollo

- Motor conductual Fase 1:
  - Extender cuaderno_anecdotico con tags positivos/negativos
  - Semáforo: VERDE >70, AMARILLO 50-70, ROJO <50
  - Score = 40% notas + 35% asistencia + 25% balance tags
  - Scikit-learn se agrega en Fase 3

## Verificar que funciona después de cada cambio

python3 -c "import app; print('OK')"

## Design System (actualizado 2026-07-02)

- Fuente: **Manrope** (primaria) → DM Sans / Syne (fallback) · DM Mono (mono)
- Light mode: paleta **warm neutral** — bg `#F7F4EF`, surface `#FFFFFF`, text `#201C16`
- Accent: **Teal Axula** `#038C8C` (light) / Royal Blue `#2661F6` (dark mode se mantiene)
- Borders light: `#E8E1D8` (cálido, no azul)
- Hover light: `#F0EBE3`
- Semantic: danger `#C9352B`, warn `#C48A1E`, success `#2E9E68`
- KPI cards: top border gradient teal/verde/coral/ámbar según tipo
- Todos los overrides centralizados en `static/theme.css` (al final del archivo)

## Log de sesiones

### 2026-07-10 (sesión 6 — Motor de Promoción MINERD completo)

**Motor de Promoción** (`core/promocion_engine.py` — nuevo):
- Reglas Ordenanza MINERD: 0 reprobadas → PROMOVIDO · 1-2 → RECUPERACION · 3+ → NO_PROMOVIDO
- Primer ciclo (1RO-3RO) y segundo ciclo (4TO-5TO): mismas reglas, sin completiva
- 6TO: nota_final = promedio_anual × 0.80 + nota_completiva × 0.20
- Asistencia > 20% → reprueba automática esa materia
- Funciones puras (evaluar) separadas de ejecutores (escriben en BD)
- Transacción única en lote: si falla 1 → rollback completo
- 6TO EGRESADO → UPDATE estudiantes SET condicion='EGRESADO'

**Migraciones BD** (`core/constants.py`):
- 7 columnas nuevas en `promociones` y `recuperaciones_pedagogicas`
- Tabla nueva `promocion_detalle_materias` — log inmutable por materia

**Blueprint** (`routes/promocion.py` — nuevo, 9 rutas bajo `/api/promocion/`):
- GET  `/preview` — vista previa por grado sin escribir
- GET  `/estudiante/<id>` — evaluación individual
- POST `/ejecutar` — lote con transacción única
- POST `/ejecutar/<id>` — individual
- POST `/post-recuperacion/<id>` — re-evalúa tras agosto
- GET  `/historial` — historial de promociones
- GET  `/detalle/<prom_id>` — detalle por materia
- POST `/completiva/<id>` — guarda nota completiva 6TO (80/20 precalculado)
- POST `/recuperacion/<id>` — guarda nota de recuperación agosto

**UI coordinador** (`templates/coordinador.html`):
- Panel Promoción: KPIs actualizados (RECUPERACION en lugar de CONDICIONADO, +PENDIENTES)
- Panel Completiva 6TO: selector de estudiantes, tabla con preview en vivo del cálculo 80/20
- Panel Recuperación Agosto: busca por grado, inputs por materia, guardar + re-evaluar inline

### 2026-07-03 (sesión 5 — carga Excel coordinador con preview/confirm)

**UI: Registro del Coordinador** (`routes/digitador.py`, `templates/digitador.html`):
- `POST /api/digitador/preview-notas-coordinador`: parsea Excel, fuzzy-match (umbral 0.72),
  retorna matched (con notas actuales vs nuevas) + unmatched. Sin escritura en BD.
- `POST /api/digitador/confirmar-notas-coordinador`: guarda en `calificaciones_periodo`
  con `origen='importacion'`; respeta precedencia manual; dispara `recalcular_kpis_estudiante`.
- UI paso 1→2: archivo → tabla comparativa P1-P4 actual/Excel con cambios en violeta →
  lista de sin-match → botones Cancelar / Guardar en sistema.
- Diseño Básico P1/P2 fix pendiente de prueba por coordinador.
- Flujo: coordinador sube .xlsm → ve preview → confirma → KPIs recalculados.

**Pendientes para coordinador:**
- Probar carga de Registro del Coordinador desde portal digitador
- Verificar que P1-P4 de Diseño Básico queden reflejados en boletín
- Correr en Render shell: `python3 scripts/recalcular_conductual.py --commit`

### 2026-07-03 (sesión 4 — fix-axula.md fases 2-4)

**Phase 2 — Fuente canónica de notas** (`core/helpers.py`, `routes/calificaciones.py`, `core/constants.py`):
- `obtener_notas_estudiante(conn, est_id, anio)`: lee calificaciones_periodo (manual) con fallback a materias_calificaciones (PDF)
- `recalcular_kpis_estudiante(conn, est_id, anio)`: recalcula p_acad + acad_p1-p4 en estudiantes después de cada escritura
- `registrar_calificacion()` llama al recalculator automáticamente por cada estudiante en el batch
- Migración: columna `origen TEXT DEFAULT 'manual'` en calificaciones_periodo
- Tablas nuevas: `config_evaluacion_pesos` (pesos por profesor) + `notas_componentes` (5 componentes)

**H10 — registro_notas_periodo → canónica** (`core/evaluacion_engine.py`):
- `cerrar_periodo()` ahora escribe en `calificaciones_periodo` con `origen='actividades'`
- Precedencia: manual > actividades > importacion (nota manual nunca se pisa)
- KPIs recalculados automáticamente al cerrar período

**H4 — Cierre de período bloqueante** (`core/evaluacion_engine.py`, `routes/evaluacion.py`):
- Si hay alumnos sin calificar → retorna `requiere_confirmacion=True` con conteo, no aplica 0 en silencio
- Route acepta `forzar=true` para confirmar y proceder

**H5 — Redirect evaluacion v1 → v2** (`routes/evaluacion.py`):
- `/evaluacion` redirige a `/evaluacion/panel` (v2)

**H6 — Desacoplar hardcoded references** (parcial):
- `routes/finanzas.py`: ambos PDF ahora usan `_get_config_centro()` para el nombre del centro
- `routes/casos.py`: prompt de IA usa `_get_config_centro()` en lugar de string literal
- `core/constants.py`: DEFAULT 'MULTIMEDIA' eliminado de tabla `asignaciones`

**Pendiente H3** (motor CE): requiere confirmación del coordinador sobre qué versión
del registro entregó el distrito para 2025-2026. No implementado hasta confirmar.

### 2026-07-03 (sesión 3 — Motor Conductual, boletín fixes, mobile UI)

**Motor Conductual Fase 1** (`core/helpers.py`):
- `calcular_motor_conductual(conn, est_id)`: score = 40% p_acad + 35% asistencia + 25% tags
- Semáforo VERDE >70 / AMARILLO 50-70 / ROJO <50 / ND (sin datos)
- Si asistencia=0: redistribuye pesos entre notas y tags (65% notas / 35% tags)
- API GET `/api/conductual/<est_id>` con RLS para profesor
- Columnas `score_conductual` + `semaforo` en tabla `estudiantes` (auto-migradas)
- `scripts/recalcular_conductual.py --commit` — poblar BD en Render shell (pendiente)
- KPIs VERDE/AMARILLO/ROJO en dashboard index.html
- Card semáforo en perfil del estudiante (JS async)

**Bugs corregidos**:
- Bug #2: RLS en `/api/progreso/<est_id>` — profesor solo ve sus alumnos
- Bug #3: `grado + "MULTIMEDIA"` hardcodeado en asistencia → usa `d.get("curso")`
- Bug #4: Profesores veían todos los reportes → filtro `autor_id=?`

**Boletín PDF** (`routes/calificaciones.py`):
- `_norm()` con unicodedata NFKD (normalización de acentos)
- `_norm_sin_nivel()` + `_norm_sin_nivel_to_canon` — fusiona "Fotografía" con "Fotografía I"
- `boletin_view` (HTML): misma lógica de merge que `boletin_estudiante` (JSON)
- Eliminadas líneas 927-932 que duplicaban entradas con alias fallback
- ALIAS_MATERIAS: "Introducción a la Historia del Arte universal y Dominicano" → nombre canónico
- "Diseño Básico y Expresión Visual" P1/P2 = None (datos ausentes del PDF, carga manual pendiente)

**Perfil estudiante** (`templates/perfil.html`):
- 5 secciones se ocultan (display:none) si API devuelve lista vacía:
  cuaderno anecdótico, asistencia mensual, narrativas, casos, documentos

**Mobile UI** (`templates/profesor.html` + `templates/index.html`):
- Portal docente: overflow-x:hidden global, nav comprimido, hero columnar,
  controls de pase en grid 2-col, tabla plan con scroll horizontal
- Pase de lista: toggle "Marcar Ausentes" / "Marcar Presentes" — no marcados = implícito
- Dashboard: welcome screen comprimido (44px→28px), notif panel centrado,
  wc-cards 2 columnas en mobile, overflow-x:hidden en ambos bloques CSS
- Nav dashboard: icono Dashboard visible en mobile (texto oculto)

### 2026-07-02 (sesión 2 — layout mobile-first + bugfixes QA)
- Rediseño layout mobile-first (estructura, NO colores):
  - Nav links movidos del topbar al sidebar ("Menú" section al tope)
  - Topbar simplificado: hamburger + logo + bell + avatar
  - Sidebar overlay en tablet/mobile (<1025px): position:fixed, left:-240px, z-index:400
  - Overlay backdrop z-index:399, closeSidebarMobile() al tocar item
  - sb-mobile-header (logo + X) visible solo en ≤1024px
- Revert de paleta warm neutral (Erick prefiere azul original) → git revert d01eb56
- QA flujo de profesor — 4 bugs detectados:
  - Bug #1 (boletín HTTP 500): INTENCIONAL — solo coordinador/directora genera boletines
  - Bug #2 fix: RLS en /api/progreso/<est_id> — profesor solo ve sus alumnos via calificaciones_periodo
  - Bug #3 fix: asistencia lote → reemplazado grado+MULTIMEDIA hardcodeado por curso real del request
  - Bug #4 fix: reportes — profesor solo ve reportes que él creó (autor_id=?)

### 2026-07-02
- Fix KPIs del listado (470 alumnos con materias_calificaciones pero p_acad=0)
  → script: scripts/recalcular_kpis.py --commit (correr en Render shell)
- Fix notas vacías (34 filas con promedio=0 y p1>0) → recalculadas
- Fix prom_modulos música/teatro/artes (accent-safe LIKE patterns en SQL)
- Feature: "Carga por Listado Simple" en digitador.html — Excel template + upload fuzzy
  - GET /api/digitador/plantilla-notas → Excel con alumnos sin notas
  - POST /api/digitador/cargar-notas-listado → fuzzy match ≥0.82, non-destructive
- Rediseño visual completo (paleta warm neutral + Manrope):
  - theme.css: light mode → warm neutral, accent teal, Manrope global
  - axula-design.css: KPI card borders → colores semánticos
  - index.html: KPI zone en card contenedora, alert strip coral, Manrope

### 2026-06-27
- Carga masiva de notas 2025-2026 desde 6 PDFs (1ERO–6TO)
- Script: scripts/cargar_notas_pdf.py — pypdf, regex, fuzzy matching
- 7,493 registros insertados en materias_calificaciones
- Fix: `###` (período incompleto en PDF) → 0.0 en vez de romper la extracción
- Fix login: rate limiter bloqueado + sicologa01 tenía hash scrypt → reseteado a pbkdf2
- Todos los passwords principales reseteados con generate_password_hash(pbkdf2:sha256)

### 2026-04-28
- Modularización Blueprint completada (20 blueprints)
- CLAUDE.md global instalado en ~/.claude/
- Skill dev-debug-ia integrada globalmente
- Pendiente: implementar motor conductual Fase 1
