# CLAUDE.md — Axula (Asistente Personal Docente)
# Contexto específico de este proyecto. Claude Code lee primero ~/.claude/CLAUDE.md
# y luego este archivo — ambos aplican en conjunto.

---

## CAMBIO DE PARADIGMA (sesión 14 — 2026-08-11)

Axula dejó de ser plataforma institucional del C.E. Benito Juárez.
**Ahora es el asistente personal de clases de Erick Hernandez (MULTIMEDIA 4TO/5TO/6TO).**

- Backup completo archivado en: https://github.com/erickherndza/axulafull.git (intocable)
- Este repo (axula.git) = versión personal recortada

### Módulos eliminados
`finanzas` · `secretaria` · `digitador` · `usuarios` · `promocion` · `config`
`portal_padres` · `firmas` · `suministros` · `normativa` · `planificacion_basica`

### Módulos activos (18 blueprints)
`auth` · `estudiantes` · `calificaciones` · `asistencia` · `casos` · `reportes`
`notificaciones` · `calendario` · `profesor` · `planificacion` · `dashboard`
`asignaciones` · `evaluacion` · `ocr` · `expediente` · `analitica` · `archivos` · `asistente`

### Perfil de Erick en BD (id=3)
- username: `erick.hernandez@educacion.edu.do`
- rol: `profesor` · tipo_docencia: `tecnica`
- grado: `4to,5to` · mencion: `MULTIMEDIA`
- materia: `Fotografía|Diseño Básico y Expresión Visual|Diseño Web|Diseño Gráfico|Publicidad y Creatividad`

### Reglas de acceso post-recorte
- Login siempre redirige a `/profesor` (rol único activo)
- `/casos` abierto al profesor (cuaderno anecdótico)
- `/api/evaluacion/ce/configurar` abierto al profesor (configura sus propias CEs)
- SECRET_KEY ya está en Render como env var — no tocar

---

## Stack

- Flask + SQLite (WAL mode) + Python 3 + ReportLab + openpyxl + Groq API + Claude API (Anthropic)
- Arquitectura Blueprint: /core/ + /routes/ (18 blueprints) + app.py factory
- Iniciar local: cd /Users/erickhernandez/elearning && python3 app.py
- DB local: database.db
- **Deploy: git push origin main → Render debería auto-deployar (~5-10 min), pero en sesión 16 el
  auto-deploy no se disparó varias veces — si no ves el cambio, entra a Render → axula → Manual
  Deploy → Deploy latest commit. Verificar SIEMPRE con logs antes de asumir que un fix quedó activo.**
- **NO es PythonAnywhere** — ese es el otro proyecto (plantillas-web)
- **⚠️ Procfile y render.yaml NO tienen efecto en este servicio.** Render usa el "Start Command"
  guardado en Dashboard → axula → Settings → Deploy, que se configuró manualmente y es independiente
  del repo. Cualquier flag de gunicorn (--timeout, --workers, --threads) hay que cambiarlo AHÍ, no en
  el código. Start Command actual (sesión 16): `gunicorn app:app --workers 1 --threads 8 --timeout 120 --bind 0.0.0.0:$PORT`

## Patrones críticos — nunca romper

- _normalizar_rol()         # normalización de roles
- _get_config_centro()      # datos institucionales desde BD
- _anio_escolar_actual()    # año escolar activo
- CSRF: header X-CSRF-Token en todos los POST
- CSS: NUNCA hardcodear colores — siempre var(--surface), var(--border), var(--text)
- data-theme NUNCA en <html> — lo maneja theme.js
- GROQ_API_KEY y ANTHROPIC_API_KEY ya están en Render como env vars — no tocar
- Groq client SIEMPRE con max_retries=0 (core/ia.py) — el retry por defecto del SDK usa
  time.sleep() bloqueante, que puede matar el worker de gunicorn (WORKER TIMEOUT)
- Llamadas IA que puedan tardar/generar mucho texto: preferir varias llamadas cortas orquestadas
  desde el frontend en vez de una sola larga — el timeout real de gunicorn en este servicio es 120s
  (ver Stack arriba), pero cualquier request que se acerque hay que partirlo en pasos

## Tema UI

Power BI light mode · Teal: #038C8C, #024959, #012840

## Módulos completados

- Autenticación (usuario único profesor MULTIMEDIA)
- Expediente estudiantil (ind_conducta, ind_psico, ind_academico, ind_logros)
- Evaluación por competencias Ordenanza 04-2023 — CEs sembradas para todas las menciones
- Generación PDF/Excel
- Registro de estudiantes MVP
- Escáner OCR de documentos (`/escaner`)
- Cuaderno anecdótico (`/casos`) — abierto al profesor
- **Carga masiva de notas desde PDF** — scripts/cargar_notas_pdf.py (2026-06-27)
- **Competencias Modalidad Artes** — scripts/sembrar_competencias_arte.py (2026-08-11)

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

### 2026-08-23 (sesión 17 — retiro de estudiantes + auditoría profunda "notas de grado anterior" + reconexión del motor de promoción)

**Disparador:** con el año escolar 2026-2027 arrancando al día siguiente (24-ago), Erick reportó
que estudiantes ya promovidos (ej. 4TO→5TO Multimedia) seguían mostrando en `/perfil/<id>` las
materias y notas de su grado anterior. Lo que empezó como "un bug" terminó siendo una auditoría
completa del subsistema de grados/promoción — 9 bugs independientes, todos con causa raíz
identificada y verificada con datos reales antes de cada fix (a pedido explícito del usuario:
"no demos pasos a ciegas").

**Parte 1 — Retiro/transferencia de estudiantes (feature nueva):**
- `condicion` en `estudiantes` ya existía (`ACTIVO`/`RETIRADO`/`GRADUADO`) pero
  `POST /api/estudiante/<id>/condicion` solo exigía `@login_required` — cualquier usuario logueado
  podía retirar a un estudiante. Ahora exige `ROLES_DIRECTORA` (directora/superusuario).
- Agregado estado `TRANSFERIDO`.
- **Ningún listado de curso filtraba por condición** — un estudiante RETIRADO seguía apareciendo
  en el dashboard, asistencia, asignaciones, evaluación por competencias, portal del profesor.
  Agregado el filtro `condicion NOT IN ('RETIRADO','TRANSFERIDO')` en los 11 sitios que arman
  esos listados (`routes/estudiantes.py::api_datos`, `asistencia.py` x2, `asignaciones.py` x2,
  `evaluacion.py`, `profesor.py` x3, `dashboard.py`).
- UI de "Editar → Estado" en `perfil.html` reducida de `es_coord or es_directora` a `es_admin`
  (=ROLES_DIRECTORA) solo para el botón de condición — Reportes/Editar datos siguen visibles
  a coordinador.

**Parte 2 — Por qué las notas de 4TO seguían apareciendo en estudiantes ya en 5TO (8 causas):**

1. **`perfil_estudiante()` y `boletin_view()` sin filtro de grado** — ambas leían
   `materias_calificaciones` filtrando solo por `estudiante_id` (o por `anio_escolar` sin
   `grado`). Fix: mismo patrón que ya usaba `boletin_estudiante()` — filtrar por
   `anio_escolar actual` + `grado actual` del estudiante (NULL-tolerant para filas viejas
   sin etiquetar). `commit 1c4aa8d`.
2. **`obtener_notas_estudiante()` (core canónica, usada por `recalcular_kpis_estudiante` y el
   motor de promoción) tampoco filtraba por grado** — ahora acepta `grado=` opcional.
   `commit 1c4aa8d`.
3. **`configuracion_centro.anio_escolar_activo` estaba en `"2027-2028"`** — un año adelantado
   del real (hoy 23-ago-2026, año nuevo empieza 24-ago-2026 → debía ser `"2026-2027"`). No hay
   ninguna pantalla en la app para editar este valor (el módulo `config` que lo hacía se eliminó
   en la sesión 14) — se corrigió a mano en Render Shell con
   `scripts/fijar_anio_escolar.py 2026-2027`. **Si el año escolar activo vuelve a quedar mal,
   nada de lo demás en esta lista funciona correctamente** — es la pieza más crítica.
4. **101 estudiantes tenían KPIs "cacheados" (`p_acad`, `acad_p1-4`, módulos técnicos de las 4
   menciones) con valores de su grado anterior**, aunque las consultas ya estaban arregladas —
   el fix de lectura no borra lo que ya quedó mal escrito de antes. Limpiado con
   `scripts/resetear_kpis_promovidos.py --commit` (dry-run primero, siempre).
5. **El motor de promoción (`core/promocion_engine.py`) estaba completamente desconectado.**
   `routes/promocion.py` se borró en la purga institucional de la sesión 14 (está en la lista
   de "módulos eliminados"), pero el botón "Promover" de `perfil.html` y el motor en
   `core/promocion_engine.py` NUNCA se borraron — quedaron huérfanos. `/api/promocion/estudiante/
   <id>` y `/api/promocion/ejecutar/<id>` daban 404 silencioso desde la sesión 14. Reconectado en
   `routes/promocion.py` (nuevo, solo las 2 rutas que la UI ya esperaba). `commit 153f479`.
6. **Sin el motor, la única forma alcanzable de cambiar `grado` era el editor genérico**
   `PATCH /api/estudiante/<id>` (campo de texto libre en el modal "Editar datos") — sin ninguna
   regla, sin resetear nada. Blindado: si ese endpoint cambia `grado`, ahora también limpia el
   caché de KPIs. `commit 153f479`.
7. **`/api/indicadores/materias/<id>` y `/api/indicadores/<id>`** (los que realmente alimentan
   la sección "Módulos Técnicos" del perfil vía AJAX — NO `/api/materias/<id>`, que ya filtraba
   bien) **no tenían filtro de año/grado en absoluto.** Esta fue la fuga que sobrevivió a los
   primeros 3 fixes — se confirmó con datos reales de Diana (est_id 509) que sus 12 filas de
   4TO/2025-2026 pasaban sin ningún filtro. `commit f69d46d`.
8. **`/api/*` no mandaba ningún header de caché** — un fetch() GET podía quedar servido desde
   caché heurística del navegador después de un deploy, mostrando datos viejos hasta hacer
   hard-refresh. Agregado `Cache-Control: no-store` global a toda respuesta `/api/*` en
   `app.py::security_headers`. `commit 5dc62dd`.
9. **"Récord de Notas" (botón en `perfil.html`, visible a coordinación) apuntaba a
   `/api/promocion/record-notas/<id>`, que nunca existió** — otra ruta huérfana de la purga de
   la sesión 14. Reconstruida en `routes/promocion.py::record_notas()` + plantilla nueva
   `templates/record_notas.html` (página imprimible, un bloque por año escolar — es la vista
   correcta para ver materias de grados anteriores, separada del perfil normal que ahora solo
   muestra el grado/año actual). Al reconstruirla salió un 9no bug heredado: la query original de
   `historial_notas()` (que se extrajo a `core/helpers.py::construir_historial_notas()` para
   reusarla) pedía columnas `nota_recuperacion`/`nota_completiva` que **nunca existieron** en
   `materias_calificaciones` (son de `recuperaciones_pedagogicas`/`promocion_detalle_materias`) —
   bug preexistente a esta sesión, nunca disparado porque nada llamaba ese endpoint en la
   práctica hasta ahora. `commits b34a5f2` + `7e4f00b`.

**Limpieza de deuda encontrada durante la auditoría (no bugs activos, pero riesgo real):**
- Borrados 2 endpoints de promoción "legacy" que SET `grado` sin resetear nada y sin ningún
  caller en templates (`/api/promover/<id>` en `routes/estudiantes.py`,
  `/api/coordinador/promocion-preview` + `/api/coordinador/promocion-ejecutar` en
  `routes/calificaciones.py`) — landmines si alguna vez se llamaban por error.
- Borrado `routes/perfil.py` — 1133 líneas de blueprint duplicado de `routes/estudiantes.py`,
  nunca registrado en `ALL_BLUEPRINTS`, cero referencias en el resto del repo.
- 2 handlers de carga masiva (Excel multi-hoja y boletín escaneado en `routes/estudiantes.py`)
  recalculaban `p_acad` promediando **todo el historial** de `materias_calificaciones` sin
  filtrar año/grado — ahora delegan a `recalcular_kpis_estudiante()` (ya arreglada) en vez de
  reinventar la lógica.
- `feat(perfil)`: cuando un estudiante no tiene notas del grado/año actual, en vez de pantalla
  vacía se muestra el catálogo oficial de materias de su grado/mención (`PLAN_ARTES`) en blanco —
  nuevo helper `core/helpers.py::catalogo_materias_grado()`. `commit 4a0a146`.
- A pedido de Erick: eliminadas del perfil las tarjetas KPI "Promedio Académico", "Bienestar
  Emocional", "Índice Conductual" y el widget "Motor Conductual" (este último mostraba
  "undefined pts" — dependía de `/api/conductual/<id>`, que **también** da 404 desde algún
  refactor anterior; no se investigó más por no ser parte de lo reportado). Backend
  (`calcular_motor_conductual`, columnas `score_conductual`/`semaforo`) intacto por si se
  reactiva. `commit 679273a`.

**LECCIÓN PERMANENTE — por qué este bug tenía 8 causas y no 1:**
El patrón raíz es que `p_acad`/`acad_p1-4`/los ~40 campos de módulos técnicos en `estudiantes`
son un **caché denormalizado**, no la fuente de verdad (`calificaciones_periodo` +
`materias_calificaciones` sí lo son). Encontré **5 implementaciones independientes** que
recalculan ese caché (una con su propio `MODULO_MAP` copiado y pegado 3 veces) y **3 caminos
distintos** que pueden cambiar `estudiantes.grado` (el motor bueno + 2 legacy), y solo 1-2 de
cada grupo invalidaban el caché correctamente. Cada vez que alguien agrega una pantalla nueva
que lee/escribe notas sin pasar por `obtener_notas_estudiante()` / `recalcular_kpis_estudiante()`
(las funciones canónicas, ya arregladas), el bug puede volver a aparecer en un lugar nuevo. Antes
de escribir una consulta nueva contra `materias_calificaciones` o `calificaciones_periodo`,
**usar las funciones canónicas de `core/helpers.py` en vez de escribir SQL ad-hoc.**

**Scripts nuevos en `scripts/` (mantenimiento / diagnóstico, todos con modo dry-run):**
- `resetear_kpis_promovidos.py [--commit]` — limpia KPIs cacheados de un grado anterior.
- `fijar_anio_escolar.py <AAAA-AAAA>` — corrige `configuracion_centro.anio_escolar_activo`
  (comando de una sola línea porque la shell web de Render corta líneas largas/multilínea).
- `diag_materias_estudiante.py <est_id>` — imprime TODAS las filas de
  `materias_calificaciones`/`calificaciones_periodo` de un estudiante, marca las que tienen
  `grado`/`anio_escolar` en NULL.
- `probar_api_materias.py <est_id>` — replica la query de `/api/materias/<id>` directo contra la
  BD, sin HTTP, para descartar caché del navegador como causa de una discrepancia.

**Pendiente para mañana (24-ago, arranque de año escolar 2026-2027):**
- Cargar la lista oficial de estudiantes de 4TO y 5TO Multimedia para el año 2026-2027.
- Verificar que `anio_escolar_activo` siga en `"2026-2027"` antes de cargar nada (Render Shell:
  `SELECT anio_escolar_activo FROM configuracion_centro WHERE id=1`).
- Al promover/matricular, usar el botón "Promover" de `perfil.html` (motor real) — NO editar
  `grado` a mano por "Editar datos" salvo necesidad puntual (el blindaje del punto 5 ya cubre
  ese caso, pero el motor real registra auditoría en `promociones`).
- Pendiente sin resolver, no bloqueante: `/api/conductual/<id>` sigue en 404 (semáforo
  conductual) — mismo patrón que el motor de promoción, no se tocó esta sesión.

### 2026-08-21 (sesión 16 — Groq deprecado + migración a Claude + fix crítico timeout Render)

**Disparador:** el generador de planificación ABP (`/planificacion`) empezó a fallar con
`Error al generar` de la nada — funcionaba 8 días antes, sin ningún cambio de código de por medio.

**Causa raíz 1 — Groq deprecó el modelo en producción:**
`llama-3.3-70b-versatile` (el modelo usado desde el 27-jun-2026) fue anunciado como deprecado
por Groq el 17-jun-2026, pero siguió funcionando en periodo de gracia hasta que Groq lo retiró
de verdad la semana del 21-ago-2026 → 404 `model_not_found`. No fue una regresión nuestra.

- Fix inmediato: modelo cambiado a `openai/gpt-oss-120b` en los ~13 sitios que llamaban a Groq.
- Eso expuso el problema real: `openai/gpt-oss-120b` en el tier gratuito de Groq tiene **8,000
  TPM** (tokens por minuto) vs. los **12,000 TPM** que tenía el modelo viejo → el prompt de ABP
  (~10,200 tokens) que cabía antes ya no cabía → 413 rate_limit_exceeded, y dividiendo en 2
  llamadas + reintentos + dimensionamiento dinámico según headers `x-ratelimit-*` seguía sin ser
  confiable (8,000 TPM es muy poco para este tipo de generación).

**Causa raíz 2 — el timeout real de gunicorn en Render NO es el del repo (la más importante):**
Tras migrar el generador ABP a Claude API (ver abajo), empezó a fallar con
`[CRITICAL] WORKER TIMEOUT` — el worker moría siempre ~30s después de iniciar una llamada a
Claude, sin importar si se usaba streaming o no. Cambiar `--timeout` en `Procfile` y
`render.yaml` no tuvo NINGÚN efecto. Se confirmó con una captura del dashboard de Render que el
**Start Command real** (Settings → Deploy → Start Command) era literalmente:
```
gunicorn app:app
```
Sin `--timeout`, `--workers` ni `--threads` — Render **ignora por completo** `Procfile` y
`render.yaml` en este servicio (fue creado/configurado manualmente en el dashboard, no vía
Blueprint). gunicorn corría con su timeout por defecto (30s), de ahí el patrón exacto de crash.

- **Fix definitivo:** Start Command editado DIRECTAMENTE en el dashboard de Render:
  `gunicorn app:app --workers 1 --threads 8 --timeout 120 --bind 0.0.0.0:$PORT`
- **LECCIÓN PERMANENTE:** cualquier flag de gunicorn (timeout, workers, threads) se cambia en
  Render Dashboard → axula → Settings → Deploy → Start Command. El `Procfile`/`render.yaml` del
  repo no tienen efecto real en este servicio — mantenerlos actualizados solo por documentación,
  pero no asumir que un cambio ahí se aplica sin confirmarlo en el dashboard.

**Migración a Claude API para el generador ABP:**
- Usuario tenía crédito ($4.25) en Anthropic Console sin usar — tier "Start" da 2,000,000 ITPM /
  400,000 OTPM (250x más que Groq free), suficiente de sobra para uso personal de un solo profesor.
- `core/ia.py`: `_get_anthropic_client()` — cliente lazy, mismo patrón que `_get_groq_client()`.
- `ANTHROPIC_API_KEY` agregado a env vars de Render. `anthropic==0.125.0` en requirements.txt.
- `routes/planificacion.py::generar_planificacion_abp()`: modelo `claude-sonnet-5`.
- **Arquitectura final — 3 pasos HTTP independientes** (no 1 sola llamada, ni siquiera con
  streaming): el frontend (`templates/planificacion.html::generarPlanABP()`) hace 3 `fetch()`
  secuenciales — `paso=1` (proyecto+currículo), `paso=2` (fases 1-2), `paso=3` (fases 3-4 +
  instrumentos + ensamble final con inyección de docente/competencias/orden de fases). Cada
  request es corta por sí sola, sin depender de que el timeout de Render esté bien configurado.

**Fallback automático Groq→Claude para el resto de la IA:**
- `core/ia.py::generar_con_fallback(prompt_usuario, prompt_sistema, max_tokens, temperature)`:
  intenta Groq (gratis) primero; si Groq da 429, cae a Claude automáticamente y marca
  `_groq_disabled_until = ahora + 1h` (variable de proceso — con `--workers 1` no hace falta
  cron ni almacenamiento compartido, un chequeo de reloj en cada llamada basta).
- Migradas las 11 llamadas a Groq en `casos.py`, `evaluacion.py`, `perfil.py`, `estudiantes.py`
  y `planificacion.py` (las 4 rutas que no son el generador ABP) para usar este helper.
- Bug preexistente arreglado de paso: `routes/evaluacion.py` usaba `_get_groq_client()` sin
  importarlo — `NameError` silencioso atrapado por el `except Exception` genérico, la
  retroalimentación IA de evaluación por competencias nunca había funcionado.

**Pendiente / a vigilar:**
- Con Claude en `effort: "low"` en pasos 2-3 del ABP, la calidad de las fases generadas es algo
  más simple que con `effort` alto — si el usuario nota contenido pobre, subir a `"medium"` (ya
  no hay riesgo de timeout real, pero cuidado con quedar cerca de los 120s de nuevo).
- Si el crédito de $4.25 en Anthropic Console se agota, avisar al usuario — no hay fallback desde
  Claude hacia otro proveedor, solo Groq→Claude.

**Auto-edición de materias/grado — aclaración (mismo día, misma sesión):**
Erick recordaba que el diseño original de la plataforma era "solo directora asigna/elimina
materias". Verificado en código: eso ya no aplica — `routes/profesor.py::editar_mi_perfil()`
(extendido en sesión 15) permite que CUALQUIER usuario logueado edite su propio `materia` y
`grado` desde `/mi-perfil` → Editar perfil, sin restricción de rol y sin restricción para
*quitar* (es un campo de texto libre separado por `|`, se reemplaza completo con lo que se
envíe). No hace falta la cuenta `directora` para que Erick ajuste sus propias materias del año
escolar. **Confirmado por el usuario: entró a `/mi-perfil` y pudo editar/quitar materias sin
problema.** Queda sin reproducir el reporte inicial de que vía `/usuarios` (cuenta
directora/admin) el cambio no le funcionó — revisar `routes/usuarios.py::api_editar`
(PATCH /api/usuarios/<uid>) solo si se vuelve a reportar; la vía recomendada de ahora en
adelante para que un profesor ajuste sus propias materias/grado es `/mi-perfil`, no `/usuarios`.

### 2026-08-12 (sesión 15 — Usuarios admin + generador planificación 2026)

**Fe de errata — perfil propio editable (commit previo):**
- `routes/profesor.py` → `editar_mi_perfil()` extendido: `CAMPOS_EDITABLES` incluye `materia` y `grado`
- Al actualizar materia: `asignaturas=NULL` para evitar que el campo legacy tome precedencia
- Sesión Flask refrescada al guardar (`session["materia"]`, `session["grado"]`)
- `templates/mi_perfil.html`: chips de materias en modal edición, envía `materia` y `grado`

**Módulo /usuarios rehab ilitado (commits previos):**
- `routes/usuarios.py` — blueprint nuevo: `GET /usuarios`, `GET/PATCH /api/usuarios/<id>`, `POST /api/usuarios`, `POST /api/usuarios/<id>/password`
- `templates/usuarios.html` — tabla + modales edición/creación, usa `apiFetch()` con `X-CSRF-Token`
- `core/database.py` — migración startup: `admin` elevado a `superusuario`
- Acceso restringido a `_ROLES_ADMIN = {"superusuario", "directora"}`

**Fix CSRF en /usuarios:** `var CSRF = '{{ csrf_token }}'` + helper `apiFetch()` que inyecta header automáticamente.

**Fix materia persistente tras edición admin:** campo `asignaturas` tenía precedencia sobre `materia` en portal (`prof.get("asignaturas") or prof.get("materia")`). Fix: `asignaturas=NULL` al editar materia en ambos blueprints (`usuarios.py` y `profesor.py`). En Render Shell: `UPDATE usuarios SET asignaturas=NULL WHERE id=3;`

**Fix Render apuntando a repo incorrecto:** Render estaba conectado a `dipromes` en lugar de `axula`. Usuario reconectó desde Render Settings.

**Generador planificación MINERD 2026 (commit `e19270d`):**
- Archivo: `routes/generar_planificacion_abp.js` (en .gitignore → `git add -f`)
- `W.EL`: 5→6 columnas [2400, 2400, 2400, 3000, 2100, 2100]
- `W.FA`: 9→8 columnas [2000, 1100, 3400, 2000, 1800, 1800, 1200, 1100]
- `bloque2` ELEMENTOS: "Competencias Fundamentales" como fila fusionada ancho completo,
  luego 6 cols: Competencias específicas (Laborales profesionales) | Elemento de la competencia |
  RAE | Contenidos | Problema a resolver | Pregunta desafiante
- `bloque3` FASES: elimina columna CF, 8 cols:
  `*Fases del ABP/ABPr` | Tiempo aproximado | Actividades | Integración STEAM
  (Ciencia, Tecnología, Ingeniería, Artes, Matemática) | Rol del Docente | Rol del estudiante |
  Recursos | Técnicas e Instrumentos de Evaluación
- Nota al pie: `- Anexar los instrumentos de evaluación de cada fase.`
- Campo `curriculo.competencias_especificas` / `curriculo.competencias_laborales` para col nueva;
  fallback a `elementos_competencia` si no existe

**ARQUITECTURA crítica — precedencia de materia:**
```
portal_profesor usa: prof.get("asignaturas") or prof.get("materia")
→ asignaturas siempre debe ser NULL si el profesor no tiene asignaciones personalizadas
→ editar_mi_perfil() y PATCH /api/usuarios/<id> siempre nullifican asignaturas al cambiar materia
```

### 2026-08-11 (sesión 14 — Paradigma: Axula → asistente personal MULTIMEDIA)

**Cambio de paradigma:** El centro y el MINERD ya tienen plataforma propia.
Axula se convierte en asistente personal de clases de Erick (4TO/5TO/6TO MULTIMEDIA).

**Backup:** Historial completo archivado en `axulafull.git` (push directo, remote removido del local).

**Recorte de módulos (commit `7731cbe`):**
- Eliminados 11 blueprints institucionales: finanzas, secretaria, digitador, usuarios, promocion, config, portal_padres, firmas, suministros, normativa, planificacion_basica
- 21,576 líneas borradas · 18 blueprints activos

**Acceso profesor completo (commit `f230325`):**
- Login siempre redirige a `/profesor`
- Sidebar: Reportes, Planificación, Cuaderno anecdótico visibles al profesor
- Welcome cards: Cuaderno anecdótico y Reportes accesibles

**Fix acceso evaluación y casos (commit `1f59264`):**
- `/casos` — eliminado bloqueo de rol (profesor puede usar cuaderno anecdótico)
- `/api/evaluacion/ce/configurar` — profesor puede configurar sus propias CEs

**Fix escáner + perfil + competencias (commit `c45dabe` + `caa0722`):**
- `escaner.html` restaurado (borrado por error en el recorte)
- Perfil Erick en BD: grado `4to,5to`, mencion `MULTIMEDIA`, 5 materias técnicas
- `scripts/sembrar_competencias_arte.py` — 188 CEs para todas las menciones de Artes MINERD
  (MULTIMEDIA · TEATRO · MÚSICA · ARTES VISUALES · DANZA) · 4 CEs por materia · cubre variantes mayúsculas

**Pendiente en Render Shell:**
```bash
python3 scripts/sembrar_competencias_arte.py --commit
```

**ARQUITECTURA POST-RECORTE:**
```
Login → /profesor (único destino)
/casos        → cuaderno anecdótico (abierto al profesor)
/evaluacion   → /evaluacion/panel → panel_asignaciones.html
               usa prof.get("materia") + prof.get("grado") del usuario en BD
/escaner      → OCR de documentos (abierto a cualquier usuario logueado)
competencias_materia → tabla con CEs por materia/año escolar
```

### 2026-07-23 (sesión 13 — UI: RECUPERACION workflow + menciones primer ciclo)

**Fix 1 — RECUPERACION separada de NO_PROMOVIDO en coordinador.html** (commit `beeae4b`):
- Antes, RECUPERACION y NO_PROMOVIDO compartían el mismo botón "↑ Forzar"
- Fix: botón "🟡 Registrar" exclusivo para RECUPERACION (`promRegistrarRecuperacion(estId)`)
  que llama `_promCallEjecutarUno` con `forzarPromovido=false` y obs="Recuperación pedagógica agosto"
- NO_PROMOVIDO mantiene "❌ Forzar" separado

**Fix 2 — Mensajes y labels correctos en perfil.html** (commits `beeae4b`, `c4c5ad6`):
- Dialog RECUPERACION: ahora dice "permanece en grado actual, examen agosto" (antes decía "pasa a siguiente grado")
- `_actualizarUIPromocion` para RECUPERACION: muestra "🟡 Recuperación registrada — examen agosto pendiente" (antes "Recuperación → [mismo grado]")
- Banner informativo en perfil cuando motor = RECUPERACION: explica flujo y próximos pasos
- Botón cuando `p_acad < 70` y sin motor ejecutado: muestra "Repitente — GRADO" (antes "Evaluar y Promover")

**Fix 3 — Menciones (Especialidad) solo existen en 4TO y 5TO** (commit `b6a2940`):
- `index.html`: sidebar Especialidad se oculta cuando filtro activo es primer ciclo
  - Nueva función `_sbActualizarEspecialidad(ciclo)` llamada desde `sbSetCiclo()` y `sbSetGrado()`
  - Al seleccionar primer ciclo: sección Especialidad `display:none`, menciones activas limpiadas
- `usuarios.html`: `onCicloChange('primer_ciclo')` ahora oculta `#bloque-mencion` y desmarca
  todas las menciones activas + llama `onMencionChange()` para limpiar materias técnicas

**REGLA CONFIRMADA — estructura de menciones:**
- Primer ciclo (1ERO, 2DO, 3ERO): NO tienen mención artística
- Segundo ciclo: 4TO y 5TO → MULTIMEDIA / TEATRO / MÚSICA / ARTES VISUALES / DANZA
- 6TO también es segundo ciclo pero los docentes de mención típicamente son de 4TO/5TO

**Pendientes en Render Shell:**
```bash
python3 scripts/recalcular_kpis_notas0.py --commit
python3 scripts/recalcular_conductual.py --commit
python3 scripts/cargar_diseno_basico_p12.py --commit
```

### 2026-07-23 (sesión 12 — Fix motor dedup cross-mención + cierre de año)

**Problema reportado:** El usuario intentó cerrar el año escolar 2025-2026 y recibió:
`Error: Error interno: 'list' object has no attribute 'get'`

**Bug A — `cerrar_anio_escolar()` en `routes/config.py`** (commit `2be15c2`):
- `evaluar_grado()` siempre retornó `list[dict]` — cada dict es el resultado de `evaluar_estudiante()`
- Pero el código hacía `rs.get("estudiantes", [])` como si fuera un dict → error inmediato
- Además `est["id"]` estaba mal — la clave correcta es `est["est_id"]` (o `est.get("est_id")`)
- Fix: `estudiantes = evaluar_grado(...)` directo + `est.get("est_id") or est.get("id")`

**Bug B — Motor dedup incompleto** (commit `922152e`, descubierto en sesión anterior):
- `evaluar_estudiante()` usaba su propio `_norm_mat()` (ASCII only, sin consultar `_MATERIA_SINONIMOS`)
- "HISTORIA DEL ARTE UNIVERSAL Y ESTÉTICA DIGITAL" (materia de TEATRO asignada a alumnos MULTIMEDIA
  por contaminación cross-mención del script de carga PDF) no se unificaba con
  "Introducción a la Historia del Arte universal y Dominicano" → motor veía 2 materias separadas
  → la primera con P3=59/P4=61 (prom 68.75) causaba RECUPERACION incorrecto en estudiante 537
- Fix 1: `_MATERIA_SINONIMOS` en `core/helpers.py` — agrega alias
  `"historia del arte universal y estetica digital"` → canónico Historia del Arte
- Fix 2: `evaluar_estudiante()` ahora usa `_normalizar_clave_materia()` (que consulta `_MATERIA_SINONIMOS`)
  + merge de períodos entre entradas duplicadas + prefiere Proper Case sobre MAYÚSCULAS
- Resultado probado localmente: est 537 pasa de RECUPERACION → PROMOVIDO (13 materias, todas ≥70)

**Script nuevo:** `scripts/recalcular_kpis_notas0.py`
- Corrige estudiantes con MC rows pero `p_acad=0`/`tiene_notas=0` (16 casos detectados)
- Usa `obtener_notas_estudiante()` — misma función que el motor, no lógica paralela
- Correr en Render Shell: `python3 scripts/recalcular_kpis_notas0.py --commit`

**ARQUITECTURA CRÍTICA — cómo funciona la dedup de materias:**
```
obtener_notas_estudiante()    → devuelve dict {materia: {p1,p2,p3,p4,promedio}} SIN dedup
                                Lee CP (manual) primero, MC (PDF) como fallback por período
evaluar_estudiante()          → llama obtener_notas_estudiante(), luego deduplica via
                                _normalizar_clave_materia() que consulta _MATERIA_SINONIMOS
_MATERIA_SINONIMOS            → dict en core/helpers.py línea ~2538
                                clave = nombre normalizado sin acentos, sin puntuación
                                valor = nombre canónico para comparación
_normalizar_clave_materia()   → normaliza + aplica sinónimos en una sola llamada
```

**LECCIÓN CLAVE — evaluar_grado() retorna list, no dict:**
```python
# CORRECTO
estudiantes = evaluar_grado(conn, grado, anio_actual)   # list[dict]
for est in estudiantes:
    est_id = est.get("est_id")                           # clave correcta

# INCORRECTO (bug original)
rs = evaluar_grado(...)
estudiantes = rs.get("estudiantes", [])    # ← AttributeError: list has no .get()
est["id"]                                  # ← KeyError: clave es "est_id"
```

**Pendientes en Render Shell (después del deploy ~5-10 min):**
```bash
# Fix 16 estudiantes con p_acad=0 a pesar de tener notas
python3 scripts/recalcular_kpis_notas0.py --commit

# Pendiente desde sesión anterior
python3 scripts/recalcular_conductual.py --commit
```

**Pendientes de código:**
- Render Shell: `python3 scripts/cargar_diseno_basico_p12.py --commit` (P1/P2 Diseño Básico)
- CRUD UI para `estudiante_perfil_inclusivo` (tabla creada, sin UI)
- Confirmar con dirección CBJ: `max_areas_aplazado=2` y `max_areas_reprueba=4` bajo Ord. 04-2023

---

### 2026-07-23 (sesión 11 — Motor promoción MINERD + banner perfil) ⚠️ SESIÓN INCOMPLETA

**Lo que se implementó (commits ae30342, 5fb83d5, d63a95d):**
- `criterios_promocion`: tabla versionada por ordenanza — Ord. 04-2023 (70 pts / 80% asist) como seed automático
- `estudiante_perfil_inclusivo`: criterios diferenciados TDAH/TEA/NEAE; motor los usa si hay plan_adaptación activo
- `evaluar_estudiante()` extendido: lee criterios desde BD, detecta `caso_limite` (65-69 pts), retorna `requiere_revision_humana`
- `POST /api/promocion/narrativa/<est_id>`: Groq redacta para padres o comité, nunca decide — guarda en `promociones.explicacion_ia`
- `GET /api/promocion/casos-limite`: filtra por `caso_limite=1`
- `perfil_estudiante()` ahora llama `evaluar_estudiante()` y pasa `resultado_motor` al template
- Banner en `perfil.html`: 🔴 REPITE / 🟢 PROMOVIDO / 🟡 RECUPERACIÓN según motor
- Botón "Promover" ahora dice "Registrar Repitiente — XGRADO" en rojo cuando motor = NO_PROMOVIDO
- 2 paneles nuevos en `coordinador.html`: Casos Límite + Narrativa IA

**⚠️ PROBLEMA DE SESIÓN:** El usuario no vio ningún cambio porque Render no había completado el deploy cuando verificó.

**REGLA PERMANENTE:**
- Verificar que el usuario confirme que ve el deploy de la sesión anterior ANTES de escribir código nuevo
- Implementar de a un cambio → push → esperar confirmación del usuario → siguiente cambio
- Hard refresh: Cmd+Shift+R en el browser del usuario después de ~5 min del push

### 2026-07-11 (sesión 10 — Limpieza materias_calificaciones: cross-mención + duplicados)

**Problema:** Estudiantes de 4TO MULTIMEDIA tenían materias de TEATRO y MÚSICA asignadas por error,
y duplicados uppercase/proper-case (ej: "CIENCIAS NATURALES" + "Ciencias Naturales").

**Causa raíz:** `scripts/cargar_notas_pdf.py` (sesión 2026-06-27) procesó PDFs que contenían
todas las secciones de 4TO juntas (MULTIMEDIA+TEATRO+MÚSICA+AV+DANZA). El fuzzy-match asignó
materias de otras menciones a estudiantes MULTIMEDIA. No fue introducido por código de esta sesión
— mis fixes de api_datos() solo hicieron los perfiles accesibles, exponiendo datos sucios preexistentes.

**Script creado:** `scripts/limpiar_materias.py` (dry-run por defecto, `--apply` para escribir)
- Paso 1: Elimina materias técnicas de otra mención por keywords (TEATRO→'danzario','teatral','puesta en escena','caracterizaci'; MÚSICA→'canto coral','instrumental grupal','lenguaje musical, teoria')
- Paso 2: Deduplica por nombre normalizado (unicodedata NFKD + regex roman numerals), conserva el que tiene más datos y prefer proper-case sobre UPPERCASE

**Resultados en Render:**
- `limpiar_materias.py --apply` → 3283 filas eliminadas (170 cross-mención + 3113 dupes)
- Alias cleanup manual → 449 filas más (FIHR, INTRO., Lenguaje Danzario corto, Visual Artesanal)
- Total eliminado: 3732 filas. MC quedó en ~8682 registros limpios.

**LECCIÓN:** Los PDFs de 4TO contenían TODAS las secciones (todas las menciones). El script de carga
asignó materias de TEATRO/MÚSICA a alumnos MULTIMEDIA porque no filtraba por mención del estudiante.
Si se vuelven a cargar PDFs de 4TO-6TO, agregar filtro por `e.curso` antes de insertar en MC.

**Pendiente en Render Shell (Diseño Básico):**
```bash
python3 scripts/cargar_diseno_basico_p12.py --commit
```
Los datos ESTÁN en `calificaciones_periodo` local y Render (cargados previamente).
Sin match: Diana Ramirez De La Cruz y Josue Fabre Rodríguez (ingresar manualmente).

### 2026-07-11 (sesión 9 — Fix blank de 2 segundos: multi-grado + mención con acento)

**Causa raíz:** Dos bugs sinérgicos que hacían que el dashboard del profesor mostrara "Cargando..." ~2s y quedara en blanco.

**Bug 1 — Backend `api_datos()` (`routes/estudiantes.py`)**:
- Profesores con `grado='4to,5to'` en DB → query `AND upper(grado) LIKE '%4TO,5TO%'` → ningún estudiante tiene ese literal → devolvía `[]`
- Profesores con `mencion='musica'` → `LIKE '%MUSICA%'` → `curso='4to MÚSICA'` → no match (acento)
- Fix: usa `_resolver_alcance_profesor()` → genera OR clauses separadas por grado + mención canónica con acento

**Bug 2 — Frontend `filtrar()` (`templates/index.html`)**:
- `PROF_GRADO='4to,5to'` → `gradosActivos=['4to,5to']` (string completo, no array) → filter falla
- `PROF_MENCION='artes_visuales'` → `mencionesActivas=['ARTES_VISUALES']` → `c.includes('ARTES_VISUALES')` falla (underscore vs espacio)
- Fix: `PROF_GRADO.split(/[,|]/)` → array de grados individuales. Slug normalizado: `artes_visuales→ARTES VISUALES`, `musica→MÚSICA`

**Commits:**
- `3ec9006` — regresión estudiantes: sentinel 'todos', mención normalization (sesión anterior)
- `3b98c29` — fix definitivo: multi-grado + mención canónica en api_datos + frontend

**LECCIÓN:** `api_datos()` y `_resolver_alcance_profesor()` son code paths INDEPENDIENTES. Un fix en uno no afecta al otro. Cuando hay un nuevo filtro de profesor, verificar que AMBOS estén alineados.

**Pendiente en Render Shell:**
```bash
python3 scripts/reparar_alcance_docente.py --apply   # normaliza 8 menciones en BD
```

### 2026-07-10 (sesión 8 — Fix asignación docente: 6 bugs modal usuarios)

**Diagnóstico origen:** `MEJORAS/CLAUDE-FIX-asignacion-docente.md` — análisis completo pre-sesión.

**Causa raíz (BUG-1):** `templates/usuarios.html` tenía copia fosilizada del formulario docente:
solo materias de 4to por mención, sin `data-grado`, sin `onGradoChange()`. La versión correcta
vivía en `index.html`. Síntoma: "no salen las materias de 5to" — era arquitectónico, no lógico.

**6 fixes en commit `447d71d` (3 archivos):**
- `usuarios.html`: sección técnicas reemplazada con 4to/5to/6to y `data-grado` para 5 menciones
- `usuarios.html`: grados con `onchange="onGradoChange()"` + función `onGradoChange()` añadida
- `usuarios.html`: `_setChecks` usa `split(/[|,]/)` — grados/menciones se re-marcan al reabrir edición
- `usuarios.html`: `telefono` añadido al body del PATCH (antes se leía pero no se enviaba)
- `usuarios.html` + `index.html`: `abrirEditar()` y `editarUsuario()` llaman `onGradoChange()` tras `onMencionChange()`
- `routes/usuarios.py`: `editar_usuario()` consulta email actual en DB y valida solo si cambió → correos legacy no bloquean el PATCH

**BUG-5 (sesión) aceptado como won't-fix v1:** Sesión del profesor muestra datos viejos tras edición por directora.
Toast recomendado: "El docente debe cerrar sesión y volver a entrar para ver los cambios".

**LECCIÓN:** Cuando un formulario complejo existe en 2 templates, los bugs no son simétricos:
una copia evoluciona y la otra fosiliza. Diagnosticar "qué ruta sirve qué template" antes de buscar
el bug dentro del JS.

### 2026-07-10 (sesión 7 — Fixes motor promoción + notas 4TO MULTIMEDIA)

**Fixes desplegados en Render (commits cb028a2 → f177343):**

- `core/helpers.py` — `obtener_notas_estudiante()`: merge de notas por **período** en lugar de skip por materia completa. Antes: si CP tenía P3/P4 para una materia, `if mat in notas: continue` saltaba los P1/P2 del PDF. Ahora: CP tiene prioridad por período, períodos faltantes se completan desde MC.
- `core/promocion_engine.py` — `calcular_pct_inasistencia_materia()`: umbral mínimo **10 registros** en tabla `asistencia` (granular). Con 1-2 pases sueltos el porcentaje era inválido (1 ausencia/1 total = 100% → reprobaba injustamente).
- `routes/calificaciones.py` — `boletin_estudiante()`: mismo umbral mínimo + filtro por año escolar en query de asistencia. Detección `fue_promovido` reescrita usando DISTINCT grados en MC (más robusta). MC query cambiada a `COALESCE(grado, grado_actual)` para excluir notas de grado anterior.
- `scripts/cargar_diseno_basico_p12.py` — script para cargar P1/P2 de "Diseño Básico y Expresión Visual" para 4TO MULTIMEDIA desde datos del Excel del coordinador.

**ARQUITECTURA CRÍTICA — dos code paths de notas:**
```
boletin_estudiante()       → routes/calificaciones.py  (usado por perfil.html)
obtener_notas_estudiante() → core/helpers.py            (usado por motor promoción y KPIs)
```
Son independientes. Un fix en uno NO afecta al otro. Verificar cuál usa la UI antes de editar.

**FIXES PENDIENTES — Render:**

1. **P1/P2 Diseño Básico** — datos existen en LOCAL pero NO en Render DB. Correr en Render Shell:
   ```bash
   cd /opt/render/project/src && python3 scripts/cargar_diseno_basico_p12.py --commit
   ```
   29/31 alumnos matcheados. Sin match: Diana Ramirez De La Cruz y Josue Fabre Rodríguez (ingresar manualmente).

2. **Fotografía P1/P2/P3 faltantes** — estado INCIERTO. Verificar en Render Shell si MC tiene p1=0/p2=0/p3=0 para el alumno afectado. Si sí → falta de datos (necesita Excel del profesor de Fotografía). Si MC tiene p1>0 y no aparece en boletín → bug de código en commit cb07274.
   ```bash
   python3 -c "
   import sqlite3; conn=sqlite3.connect('/data/database.db'); conn.row_factory=sqlite3.Row
   print([dict(r) for r in conn.execute('SELECT materia,p1,p2,p3,p4,grado FROM materias_calificaciones WHERE estudiante_id=<ID> AND materia LIKE \"%otograf%\"').fetchall()])
   "
   ```

3. **Promovidos 5TO muestran notas 4TO** — NO CONFIRMADO. Tabla `promociones` vacía en Render (nadie promovido formalmente aún). Probar promoviendo un alumno desde coordinador y verificar que perfil muestre catálogo 5TO vacío. El código ya tiene la detección correcta via DISTINCT grados en MC + tabla promociones con filtro anio_escolar.

4. **recalcular_conductual.py** — pendiente desde sesión anterior. Correr en Render Shell:
   ```bash
   python3 scripts/recalcular_conductual.py --commit
   ```

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
