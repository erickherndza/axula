# CLAUDE.md — TecnoAuladom / Axula
# Contexto específico de este proyecto. Claude Code lee primero ~/.claude/CLAUDE.md
# y luego este archivo — ambos aplican en conjunto.

---

## Stack

- Flask + SQLite (WAL mode) + Python 3 + ReportLab + openpyxl + Groq API
- Arquitectura Blueprint: /core/ + /routes/ (20 blueprints) + app.py factory
- Iniciar local: cd /Users/erickhernandez/elearning && python3 app.py
- DB local: database.db
- **Deploy: git push origin main → Render auto-deploya (~5-10 min) → hard refresh en browser**
- **NO es PythonAnywhere** — ese es el otro proyecto (plantillas-web)

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
