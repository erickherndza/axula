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
