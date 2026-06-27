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
- **Carga de notas desde Excel del Coordinador** — core/excel_notas.py + /api/digitador/cargar-notas-coordinador (2026-06-27)
- **Módulo de Promoción MINERD** — /api/coordinador/promocion-preview + promocion-ejecutar + tabla promociones (2026-06-27)
- **Row-Level Security (RLS)** — core/rls.py, 10 endpoints protegidos por ciclo/rol (2026-06-27)

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
| directora | Admin2026! | Directora |
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

## Archivos clave nuevos (2026-06-27)

| Archivo | Función |
|---------|---------|
| `core/excel_notas.py` | Parser .xlsm del coordinador — detecta materia/grado/sección/mención por hoja |
| `core/rls.py` | Row-Level Security — `verificar_acceso_estudiante()`, `sql_filtro_grado()` |
| `scripts/cargar_notas_pdf.py` | Carga masiva notas desde PDFs (ya ejecutado) |
| `core/curriculo.py` | Dispatch unificado de currículo: `get_asignatura(mencion, nombre)`, `formatear_contexto(mencion, nombre)` |

## Parser Excel del Coordinador — core/excel_notas.py

Acepta archivos `XGRADO. GRADO - MATERIA 25-26.xlsm` del coordinador.
- Cada hoja = una sección/mención (ej: `CF 4TO A MÚSICA`)
- Detecta PC1-PC4 y CF aunque estén en filas de celdas combinadas (fila 8 ≠ header row)
- Upload desde dashboard digitador: tarjeta morada "Registro del Coordinador"
- Endpoint: `POST /api/digitador/cargar-notas-coordinador`

## Módulo de Promoción — Ordenanza 04-2023 MINERD

- 0 reprobadas → PROMOVIDO | 1–2 → CONDICIONADO | 3+ → NO PROMOVIDO
- `GET /api/coordinador/promocion-preview?grado=4TO` — calcula estados sin modificar BD
- `POST /api/coordinador/promocion-ejecutar` — mueve estudiantes al siguiente grado
- Tabla `promociones` en BD con UNIQUE(estudiante_id, anio_escolar)
- Panel en coordinador.html al final de la página

## Row-Level Security — core/rls.py

Coordinador primer ciclo → solo 1ERO/2DO/3ERO
Coordinador segundo ciclo → solo 4TO/5TO/6TO
Padres → solo sus hijos vinculados
Intentos denegados → log `[RLS] DENEGADO rol=X uid=Y → estudiante Z`

Endpoints protegidos: resumen_calificaciones, boletin_estudiante, boletin_view, boletin_pdf,
get_recuperaciones, resumen_asistencia, get_asistencia_mensual_est,
get_evaluaciones_narrativas, casos_del_estudiante, historial_por_estudiante (expediente)

## Log de sesiones

### 2026-06-27 (sesión 3 — Ponytail audit: limpieza + unificación currículo)
- **Ponytail instalado**: npm + skill files en `.claude/commands/` y `.claude/skills/`
- **Archivos eliminados** (~7,000 líneas):
  - `new/app.py` (6,613 líneas — monolito abandonado pre-modularización)
  - `app_monolito_backup.py`, `fix_plan.md`, `fixes_applied.md`, `qa_report_auto.md`, `verificar.py`
- **Currículo unificado**: `core/curriculo.py` — dispatch único para 4 menciones
  - `get_asignatura(mencion, nombre)` y `formatear_contexto(mencion, nombre)` reemplazan 4 funciones duplicadas
  - `planificacion.py`: eliminados 2 bloques if/elif + 5 lazy imports dentro de funciones
- Todos los cambios verificados con `python3 -c "import app; print('OK')"` ✓

### 2026-06-27 (sesión 2 — Excel coordinador + Promoción + Seguridad)
- Fix parser `core/excel_notas.py`: CF estaba en fila 8 (celda combinada), no en header row → escaneo multi-fila
- Tarjeta "Registro del Coordinador" (morada) en digitador.html — separada visualmente de Boletín Oficial
- Fix detección en `/api/cargar-boletin`: si el archivo es formato coordinador, da mensaje específico
- **Módulo Promoción MINERD**: tabla `promociones` + 2 endpoints + panel en coordinador.html
- **RLS completo**: `core/rls.py` aplicado a 10 endpoints críticos
- **CSRF hardening**: `@csrf_protected` en 5 endpoints de usuarios + reset-password + recovery/link
- Audit log en intento no autorizado a recovery/link

### 2026-06-27 (sesión 1)
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
