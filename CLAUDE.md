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
- **Coherencia Horizontal del Componente Especializado** (`/coherencia`) — matriz curricular
  por período (RAE/Contenidos/Producto/Recursos) siguiendo la plantilla oficial del centro,
  con exportación a Word editable (2026-08-25/26)
- **UX móvil de Pase de Lista y Cuaderno Anecdótico** — botones táctiles 44px, barra de
  controles compacta, Cuaderno responsive (antes sin ningún `@media`), fecha del incidente
  explícita y obligatoria, selector Grado/Modalidad/Materia en Cuaderno igual que Pase de Lista
  (2026-08-31)
- **Adecuación curricular real** — `PLAN_ARTES` y `core/curriculo_{teatro,musica,
  artes_visuales,multimedia}.py` reescritos contra los 4 PDF oficiales MINERD (Danza pendiente,
  sin PDF); reconectados los 4 generadores de IA (planificación/rúbrica/estrategia/asignación) y
  el catálogo de materias de `/planificacion` — verificado en Render: 16/16 generadores con
  contenido real, 0 profesores afectados (2026-09-01)

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

### 2026-09-04 (sesión 23 — Sistema de Conducta: Strikes/Outs, alineado a Normas MINERD de Convivencia)

**Disparador:** Erick pidió un sistema de disciplina estilo beisbol para sus estudiantes — 3
Strikes (conductas menores) = 1 Out (llamada de atención), 3 Outs en un período = reporte a
coordinación para sanción y reunión con padres. Pidió verificar contra el Manual de Convivencia
del MINERD para clasificar cuáles de sus conductas listadas son "faltas graves".

**Investigación normativa:** el documento real es "Normas del Sistema Educativo Dominicano para
la Convivencia Armoniosa en los Centros Educativos Públicos y Privados" (MINERD/CONANI, 2da ed.
julio 2013, en cumplimiento Ley 136-03 Arts. 48-50) — descargado y leído completo (47 artículos).
Clasifica 3 niveles: Leve (Art.17 — resuelve el docente en el aula, sin proceso), Grave (Art.19 —
evalúa Equipo de Gestión), Muy Grave (Art.21 — **lista cerrada por ley**, Art.26 prohíbe que un
centro agregue categorías nuevas a este nivel; van directo a Dirección/Distrito). Mapeo aplicado:
- Leves (Strike): comer en el aula, llegar tarde, salir sin autorización (explícito Art.17.e),
  sentarse mal, hablar/interrumpir (explícito Art.17.a/c/d).
- Graves (Out directo): malas palabras/insultar a un compañero, faltar el respeto a un profesor
  (ambas explícitas en Art.19.b — "palabras irrespetuosas hacia compañeros/as y/o autoridades"),
  hostigar (si es un hecho aislado, no reiterado).
- Muy graves (Reporte inmediato, salta todo el conteo): bullying/acoso reiterado (Art.21.a — la
  definición oficial de bullying EXIGE reiteración; si "hostigar" se vuelve patrón deja de ser
  grave y pasa a este nivel), pelear/agredir físicamente y amenazar (ambas bajo "Desafío o
  agresión a miembro del centro educativo", Art.21.e).

**Decisión de diseño — no meterlo dentro de `/casos` como un campo más:** antes de escribir
código se auditó `routes/casos.py`/`core/constants.py` — `casos` ya es un sistema de gestión de
casos disciplinarios maduro (ciclo de vida completo: `estado`, `nivel_escala`, timeline de
`caso_acciones`, cierre con sanción formal, Acuerdo-Compromiso con firma digital de padres,
notificación a coordinación), con las sanciones YA rotuladas en lenguaje MINERD
("amonestacion_verbal (Falta leve)", "suspension_1_3 (Falta grave)", "suspension_4_7 (Falta muy
grave)" — `routes/casos.py::casos_page()`). Meter cada "comió en el aula" ahí habría inundado la
bandeja de psicóloga/coordinador con ruido que el Art.17/18 dice que nunca debe llegarles (las
leves las resuelve el docente, sin proceso de consulta). Se encontró que `casos.origen_tipo`/
`origen_id` ya existían en el esquema, pensados exactamente para que otro subsistema
auto-generara un caso — nunca se había usado. Se aprovechó ese enganche.

**Implementación:**
- Tabla nueva `conducta_registro` (`core/constants.py::TABLAS_NUEVAS`) — bitácora liviana de cada
  strike/out/falta individual (nivel, conducta, fecha_incidente, periodo P1-P4, año escolar,
  contexto materia/grado/mención/sección, `caso_id` si disparó un caso). Índice
  `idx_conducta_est_periodo` en `core/database.py`.
- `CONDUCTA_CATALOGO` (`core/constants.py`) — las 11 conductas de Erick, agrupadas por los 3
  niveles MINERD, cada una con clave estable + etiqueta legible.
- `core/helpers.py::registrar_conducta()` — motor de conteo. 3 leves acumuladas en el período =
  1 Out; cada grave = 1 Out directo; cuando el total de Outs del período es múltiplo de 3, llama
  a `_crear_caso_desde_conducta()` (mismo patrón de INSERT que `crear_caso()`, con
  `origen_tipo='conducta_registro'`) y notifica a coordinación — igual que hace
  `agregar_accion_caso()` al escalar. Una falta muy grave salta todo el conteo y genera el caso
  de inmediato (nivel_escala=3, directora/Equipo de Gestión), sin esperar a acumular nada — así
  lo exige el Art.21/35 MINERD. `_periodo_de_fecha()` nuevo (variante de `_periodo_actual()` que
  ya existía, pero a partir de la fecha del incidente, no de "hoy" — el docente puede registrar
  algo de un día anterior).
- 3 rutas nuevas en `routes/casos.py`: `GET /api/conducta/catalogo`, `POST /api/conducta`
  (crea el evento, aplica la mecánica, retorna el conteo + qué disparó), `GET
  /api/conducta/estudiante/<id>` (tally del período actual + historial completo del año, usado
  por el modal y para futura consulta desde perfil).
- `templates/casos.html` — botón "⚾ Conducta" junto a "Nuevo caso" (sidebar), modal propio con
  selector Grado/Modalidad/Materia/Sección **reutilizando** `PLAN_POR_GRADO_MENCION` /
  `MENCIONES_PROF` / `FILTRO_MEN_CASO` (las mismas variables globales que ya alimenta "Nuevo
  Caso" — nunca un catálogo duplicado, lección de la sesión 22b), buscador de estudiante
  (mismo endpoint `/api/datos` acotado), selector de Nivel → pobla la conducta específica desde
  `CONDUCTA_CATALOGO` embebido server-side (sin fetch extra), y un tally en vivo
  ("⚾ Período P1: 2/3 strikes · 1/3 outs") al seleccionar el estudiante. Al registrar, el toast
  reacciona al `trigger` devuelto por el backend (strike normal / OUT / 🚨 reporte generado /
  🚨 falta muy grave). Cuando el evento generó un caso, se recarga la lista y se abre
  automáticamente (`verCaso()`) — el caso aparece con el badge "conducta" (⚠️) que ya existía en
  `renderLista()`, sin tocar el render de la lista.

**Verificado end-to-end antes de dar por bueno** (el `python3` local de este Mac es 3.9.6 y
`core/curriculo_musica.py` usa sintaxis `str | None` de 3.10+ — bloqueo preexistente, documentado
ya en sesión 21b, no relacionado a este cambio; se usó un venv temporal con `python3.12` del
sistema, descartado al terminar):
- `import app` completo sin errores, migración crea `conducta_registro` sin tocar nada más.
- Simulación directa de `registrar_conducta()` contra una copia de la BD: 3 leves → 1er Out (sin
  caso aún) → 1 grave → 2do Out → 3 leves más → 3er Out → genera caso "3 Outs acumulados —
  Período P1" (nivel_escala=2). Una falta muy_grave aislada genera un 2do caso inmediato
  (nivel_escala=3), confirmando que salta el conteo.
- Round-trip HTTP completo con el test client de Flask (login simulado + CSRF real de la
  página): `GET /api/conducta/catalogo`, `POST /api/conducta`, `GET
  /api/conducta/estudiante/<id>` — los 3 devuelven 200 con el payload esperado.
- No se pudo probar visualmente el modal en navegador dentro de esta sesión — pendiente que
  Erick lo prueba en `/casos` y confirme que el flujo Grado→Modalidad→Materia→Estudiante→
  Nivel→Conducta se siente igual de fluido que "Nuevo Caso".

**Pendiente:** Erick debe probar el flujo completo en `/casos` (botón "⚾ Conducta") con un
estudiante real, en varios grados/menciones si aplica, y confirmar que el caso auto-generado al
llegar a 3 Outs o a una falta muy grave se ve bien en el detalle del caso normal.

### 2026-09-01 (sesión 22b — 4to bug de la adecuación curricular: catálogo de materias de `/planificacion` seguía con nombres viejos)

**Disparador:** Erick probó los cambios y reportó que "Crear Rúbrica" seguía mostrando materias
viejas/inventadas que no correspondían al currículo ya corregido.

**Causa raíz — un CUARTO catálogo hardcodeado, este en el frontend:**
`templates/planificacion.html::MATERIAS_POR_MENCION` (JS puro, ~115 líneas) alimenta los 3
selectores de materia de `/planificacion` (Planificación de Clase `p-`, Crear Rúbrica `r-`,
Estrategias Didácticas `e-` — los 3 comparten `actualizarMaterias(prefix)`). Tenía los mismos
nombres inventados que ya se habían corregido en `PLAN_ARTES` — nadie lo tocó porque es JS
embebido en el template, no algo que `core/constants.py` alimente automáticamente.

**Segundo problema, más profundo, que solo salió al revisar el flujo completo:** cada
`<option>` de este catálogo tenía como `value` un slug hecho a mano con guion bajo (ej.
`"Lenguaje_Plastico_Visual"`), no el nombre real de la materia — ese slug es literalmente lo que
se manda al backend (`document.getElementById('r-materia').value`). Ni siquiera arreglando los
textos visibles del catálogo se iba a resolver nada, porque el backend nunca iba a poder
matchear un slug inventado contra los nombres reales de `core/curriculo_*.py`.

**Tercer problema — `cargarIndicadores()` (la función que realmente llena "Crear Rúbrica" con
indicadores) nunca mandaba `mencion` al backend:** `fetch('/api/planificacion/curriculo/' +
materia)` sin `?mencion=`, y `routes/planificacion.py::obtener_curriculo()` cae a
`request.args.get("mencion", "MULTIMEDIA")` — o sea, sin importar qué mención estuviera
seleccionada, SIEMPRE buscaba en el currículo de Multimedia. Mismo bug en `cargarCurriculo()`
(usada por Planificación de Clase) y en el fallback de `actualizarTemas()` — 3 funciones en
total. Los 2 generadores que sí llamaban al backend con el prompt final (`generarRubrica()`,
`generarEstrategia()`, `generarPlanificacion()`) YA mandaban `mencion` correctamente — el bug
estaba solo en las funciones de preview/autocompletado, no en la generación final.

**Fix (`templates/planificacion.html`):**
- `MATERIAS_POR_MENCION` ya no es un objeto hardcodeado — se construye en el momento desde
  `plan_tecnicas` (la misma variable que Flask ya inyecta para el tab ABP, derivada en vivo de
  `PLAN_ARTES`), así que el `value` de cada `<option>` es el nombre EXACTO que
  `core.curriculo.get_asignatura()` puede encontrar por match exacto de diccionario — no un slug
  ni una suposición. Nunca más se desincroniza de `PLAN_ARTES`, porque ya no es una copia.
- `cargarCurriculo()`, `cargarIndicadores()`, y el fallback de `actualizarTemas()` — las 3 ahora
  mandan `?mencion=` (leído del `-mencion` select correspondiente) y usan `encodeURIComponent()`
  en la URL (los nombres reales tienen espacios y acentos, los slugs viejos no — por eso nunca
  hizo falta encodear antes, era un accidente que funcionaba).

**LECCIÓN — un catálogo de materias hardcodeado en el FRONTEND es tan peligroso como uno en el
backend:** esta sesión ya había encontrado y corregido 2 catálogos rotos en Python
(`core/constants.py`, un dict local en `core/helpers.py`) — pero `templates/planificacion.html`
tenía un tercero en JS que nadie relacionó con el mismo bug porque vive en un archivo distinto,
en un lenguaje distinto. Antes de dar una corrección curricular por completa, buscar
`grep -rn "Lenguaje Plástico\|Escultura y Cerámica\|Instrumento Principal"` (o cualquier nombre
inventado conocido) en TODO el repo, no solo en `core/`.

**Pendiente:** Erick va a volver a probar Crear Rúbrica con esta corrección.

### 2026-09-01 (sesión 22 — adecuación curricular real: PLAN_ARTES y core/curriculo_*.py reescritos contra los 4 PDF oficiales)

**Disparador:** Erick trabajó por fuera (otra sesión/herramienta, con los 4 PDF oficiales del
Bachillerato en Artes) el arreglo completo del hallazgo de la sesión 20 — `PLAN_ARTES` para
Artes Visuales/Música/Teatro tenía nombres de materia **inventados**, sin relación con los
documentos reales (Multimedia sí estaba bien). Entregó el trabajo como `MEJORAS/RESUMEN_CAMBIOS.md`
+ 6 archivos para reemplazar en `core/`. Pidió analizar que el reemplazo se hiciera bien.

**Verificado (con pruebas propias, no solo confiando en el resumen):**
- Las 9 combinaciones grado×mención (Artes Visuales/Música/Teatro × 4to/5to/6to) en el
  `PLAN_ARTES` corregido suman **exactamente 40h** cada una.
- Las 80 materias técnicas específicas de las 4 menciones encuentran contenido real en
  `core/curriculo_*.py` — **0 fallos de búsqueda** (probado cargando los módulos de currículo de
  forma aislada con `importlib`, sin necesitar la app completa).
- El combinador de "Instrumento I/II/III" (Música) sí une las 4 especializaciones
  (Guitarra/Teclado/Viento/Percusión) en un solo resultado, confirmado.
- El diff de `constants.py` es quirúrgico — solo las ~87 líneas de `PLAN_ARTES["ARTES VISUALES"/
  "MÚSICA"/"TEATRO"]`, nada más del archivo se tocó (mis cambios de sesiones anteriores, como
  `orden_lista`, siguen intactos).

**2 problemas encontrados en la entrega, corregidos en esta sesión:**
1. **Archivos en el lugar equivocado** — de los 6 archivos, 2 (`constants.py`, `ia.py`) habían
   quedado sueltos en la **raíz del repo** en vez de `core/`, dejando `core/constants.py` y
   `core/ia.py` (los que realmente usa la app) todavía con las versiones viejas rotas. Erick los
   corrigió, pero dejó las 6 copias duplicadas sueltas en la raíz (byte-idénticas a las de
   `core/`, verificado con `diff -q`) — borradas en esta sesión, eran basura pura.
2. **`RESUMEN_CAMBIOS.md` no vio todo el repo — un tercer bug que no detectó:**
   `core/helpers.py::_construir_prompt_asignacion()` (usada activamente por
   `routes/asignaciones.py` para generar documentos de asignación) leía un **tercer diccionario**
   independiente (`CURRICULUM_ARTES`, definido localmente en `helpers.py` línea 2651, con solo
   10 materias de Multimedia) con el mismo problema de nombres de campo rotos
   (`competencia`/`descripcion`/`evidencias` en vez de `elemento_competencia`/`rae`). El resumen
   sí encontró este diccionario pero concluyó "no aparece usado por ninguna ruta" — estaba
   equivocado porque no tenía `routes/asignaciones.py` en su contexto. Corregido para usar
   `core.curriculo.get_asignatura()` igual que las 3 funciones de `core/ia.py` (mismo patrón
   exacto). El diccionario viejo en `helpers.py` línea 2651 quedó huérfano (nada lo usa ya) —
   no se borró, queda pendiente de limpieza.

**LECCIÓN — un resumen de cambios generado por otra sesión/herramienta sin acceso al repo
completo puede tener conclusiones erróneas sobre qué está "sin usar":** antes de confiar en la
afirmación "esta función no se usa en ningún lado", grep contra el repo real, no contra la lista
de archivos que esa sesión tuvo a mano.

**Confirmado en Render:** `python3 scripts/verificar_curriculo_ia.py` corrido en producción —
los 16 generadores probados (4 menciones × planificación/rúbrica/estrategia/asignación)
encontraron contenido curricular real. El fix quedó completamente funcional en vivo.

**`scripts/auditar_materias_profesores.py` corrido contra Render — sin víctimas reales:** de 16
profesores activos, solo 1 perfil salió con una materia "huérfana", y no por el cambio de
currículo — es la cuenta de prueba `prof_artes_qa` (Luis Fernández Artes), cuyo campo de materia
tiene una coma en vez de `|` como separador (`"Instrumento Principal I,Coro y Conjunto Musical
I"`), así que nunca se dividió en dos materias — typo preexistente en datos de prueba, no
relacionado a esta corrección. Carlos David Caminero (el caso multi-mención de sesiones
anteriores) y Erick quedaron con sus materias 100% coincidentes. No hizo falta reasignar nada.

Sin tocar aún (fuera de alcance, ya señalado en `RESUMEN_CAMBIOS.md`): Danza intacta (sin PDF
oficial), y el bloque de ~1100 líneas duplicado en `core/constants.py`
(`CURRICULUM_ARTES`/`CLUSTER_META`/`DB_TABLAS_META`/`DEFAULTS_CENTRO` definidos dos veces — no
afecta funcionamiento, es limpieza pendiente).

### 2026-08-31 (sesión 21b — Cuaderno Anecdótico: selector Grado/Modalidad/Materia, misma composición que Pase de Lista)

**Disparador:** Erick reportó que el Cuaderno Anecdótico "solo está el de multimedia" — con
profesores que ahora dan clases en varios grados y menciones a la vez (ej. Carlos David Caminero:
Multimedia + Artes Visuales), el flujo de "Nuevo Caso" no tenía forma de decir en qué grado/
mención/materia ocurrió la incidencia, y el buscador de estudiante no estaba realmente acotado
al alcance real del profesor.

**Causa raíz encontrada de paso — `/api/datos?q=...` estaba roto:** el buscador de estudiante del
modal "Nuevo Caso" (`buscarEstudiante()`) mandaba `?q=texto`, pero `routes/estudiantes.py::api_datos()`
**nunca leía el parámetro `q`** — el buscador en realidad mostraba siempre los primeros 8
estudiantes del alcance del profesor por orden alfabético, sin importar lo que se escribiera.
Corregido: filtro `nombre/apellido LIKE` agregado, y excluido del caché (`cache_key`) para que un
resultado cacheado sin filtro no se sirva cuando sí hay `q`.

**Feature — mismo selector Grado/Modalidad(Mención)/Sección/Materia que Pase de Lista:**
- `core/helpers.py::resolver_plan_grado_mencion_profesor(prof)` (nuevo) — extrae la lógica que
  ya tenía `routes/profesor.py::portal_profesor()` (plan por grado+mención, filtrado a las
  materias del perfil del profesor con fuzzy-match ≥0.75, fallback al plan completo si nada
  coincide) a un helper reusable, para no duplicarla en dos formularios que evolucionan por
  separado (el mismo patrón de bug ya visto en sesiones anteriores — "una copia evoluciona, la
  otra fosiliza"). `routes/profesor.py` NO se tocó — sigue con su lógica inline propia, para no
  arriesgar una regresión en Pase de Lista ya probado en producción.
- `routes/casos.py::casos_page()` — para rol `profesor`, usa el helper nuevo (acotado a su
  propio alcance real). Para coordinación/dirección/psicóloga (que ya ven todos los casos del
  centro), arma un catálogo completo (los 6 grados × las 5 menciones de 2do ciclo + materias de
  PRIMER_CICLO para 1ro-3ro) sin restricción — mismo selector, sin acotar.
- `templates/casos.html` — nuevo bloque en el modal "Nuevo Caso": Grado → Modalidad (2do ciclo) o
  Sección (1er ciclo, poblada con un fetch a `/api/datos?grado=X` para sacar las secciones reales)
  → Materia. El buscador de estudiante ahora manda `/api/datos?q=texto&grado=X&mencion=Y` (o
  `&seccion=Z`) en vez de una búsqueda global sin acotar.
- `routes/estudiantes.py::api_datos()` — el filtro de grado/mención para rol `profesor` antes
  SIEMPRE aplicaba el alcance completo del profesor, ignorando cualquier `grado`/`mencion` que
  llegara por query string. Ahora, si el valor pedido está DENTRO del alcance real del profesor,
  acota a ese único grado/mención (nunca fuera de él — mismo principio de "acotar, no confiar
  ciegamente" que ya usa `buscar_existente()` en `core/importar_listado.py`).
- `casos.materia/grado/mencion/seccion` — 4 columnas nuevas (migración automática en
  `core/database.py::migrar_bd()`, mismo patrón que `reportes.caso_id`/`calificaciones_periodo.grado`).
  `POST /api/casos` las guarda. El detalle del caso (`renderCasoDetalle()`) ahora muestra esa
  línea de contexto si está presente.

**Corrección en la misma sesión — fecha del incidente explícita, no implícita:** Erick aclaró que
`creado_en` (cuándo se guardó el registro) NO es lo mismo que quería — necesita poder elegir la
fecha en que **ocurrió** el incidente (puede ser un día anterior al que se registra), y que
Fecha/Estudiante/Grado/Mención sean pasos obligatorios antes de poder guardar, no opcionales.
- `casos.fecha_incidente` — columna nueva (TEXT, `YYYY-MM-DD`), separada de `creado_en` (que
  sigue siendo la marca de auditoría real de cuándo se guardó). Backfill automático para casos
  viejos: `fecha_incidente = date(creado_en)` como mejor aproximación disponible.
- Modal "Nuevo Caso": campo Fecha (`<input type="date">`, tope en hoy — no se puede registrar un
  incidente "futuro") como primer campo, encima del selector Grado/Modalidad/Materia.
  `abrirModalNuevoCaso()` la resetea a la fecha real del día cada vez que se abre el modal (JS,
  no el valor renderizado en la carga de la página — para no quedar desactualizada si la pestaña
  lleva rato abierta).
- `crearCaso()` ahora valida en el cliente: fecha, grado, modalidad (si es 2do ciclo) y
  estudiante son obligatorios antes de permitir guardar — antes solo exigía estudiante+título.
  `POST /api/casos` valida lo mismo server-side (`fecha_incidente` y `grado` requeridos, 400 si
  faltan) — no confiar solo en la validación del cliente.
- Listado lateral (`renderLista()`) y detalle del caso muestran `fecha_incidente` (fecha real del
  incidente) en vez de `creado_en` — el detalle además muestra ambas por separado ("Incidente: X
  · Registrado: Y") para no perder el dato de auditoría.

**Verificado localmente** (sin poder levantar el server completo — bloqueado por el mismo
problema preexistente de Python 3.9 vs. sintaxis `list|None` en `core/rls.py`, no relacionado a
este cambio): `resolver_plan_grado_mencion_profesor()` probado directo con un perfil simulado
tipo Carlos (grado='4to,5to', mención='multimedia,artes_visuales') — devuelve correctamente
Fotografía en 4to Multimedia Y Fotografía Artística en 4to Artes Visuales por separado, sin
mezclarlas. Migración de `casos` corrida contra la BD local — las 4 columnas se agregan sin error.

**Pendiente:** confirmar en producción que el modal "Nuevo Caso" muestra el selector correcto
para un profesor multi-mención real (no solo el perfil simulado) y que el buscador de estudiante
ya encuentra por texto en vez de solo listar los primeros 8 alfabéticos.

### 2026-08-31 (sesión 21 — Axula móvil: análisis UX + implementación Pase de Lista/Cuaderno + orden de lista = Excel)

**Disparador:** Erick pidió una versión de Axula optimizada para smartphone/tablet en Pase de
Lista y Cuaderno Anecdótico. Pidió explícitamente investigar estándares de UX/UI móvil primero,
documentar el análisis, y solo implementar después de su revisión — flujo en 2 fases separadas.

**Fase 1 — Análisis (agente en background, sin tocar código):** investigó estándares (Apple HIG,
Material Design, WCAG 2.5.8, thumb-zone research de NN/g) y los aplicó al código real de
`templates/profesor.html` y `templates/casos.html` (análisis estático — el resize del viewport de
Chrome no se aplica de forma confiable en este entorno de automatización, tanto para el agente
como para mí en el intento posterior de verificación visual; no vale la pena seguir intentándolo,
usar análisis de código + confirmación del usuario en su propio teléfono). Documento publicado
como Artifact con 6 hallazgos priorizados. Erick lo revisó y pidió implementar todo.

**Fase 2 — Implementación (commit `cd66d62`):**
- `.ab3` (botones Ausente/Tarde/Excusa): en móvil pasan a su propia fila completa (`flex-basis:100%`
  en `.asist-btns3`) con `min-height:44px` — antes ~26px, bajo el mínimo táctil de Apple/Material/
  WCAG 2.5.8. Se descartó agrandarlos en línea junto al nombre porque aplastaba `.est-nombre` a
  unos pocos px de ancho — mejor bajarlos a una fila propia.
- `.pase-top-bar` (Fecha/Grado/Modalidad/Materia/Sección): cuadrícula compacta 2 columnas en móvil,
  mismo patrón que ya tenía `.lista-controls`. Materia (`.fld-materia`, clase nueva) ocupa la fila
  completa por ser el campo que más cambia.
- Fuente 16px en inputs/selects de ambas pantallas en móvil (antes 12-13px) — evita el zoom
  automático de iOS Safari al enfocar un campo.
- `templates/casos.html` no tenía NINGUNA regla `@media` — agregado bloque completo: `.casos-grid`
  colapsa a 1 columna en móvil (antes 320px+resto, inutilizable en un teléfono), modal "Nuevo Caso"
  se abre como hoja inferior a ancho completo en vez de caja centrada de escritorio.
- Texto de ayuda corregido en Pase de Lista (describía una interacción de "toque cíclico" que no
  existe en la UI real — quedó de una versión anterior del diseño).
- **Bug real encontrado por Erick después del deploy** (no estaba en el análisis original): la
  barra flotante fija de "Guardar lista" tapaba el último estudiante de la lista en móvil, porque
  `position:fixed` no reserva espacio propio en el flujo del documento. Fix: `.lista-grid{padding-
  bottom:100px}` — espacio de reserva permanente al final de la lista, aplica a todos los tamaños.

**Feature nueva — orden de Pase de Lista = orden real del listado del coordinador:**
Erick pidió que el orden de Pase de Lista coincida con "LISTADO AÑO 2026-2027.xlsx". Verificado:
para 4to Multimedia el orden actual (alfabético por apellido) YA coincidía con el orden del Excel
— pero por coincidencia, no por diseño (el Excel resultó estar también ordenado alfabéticamente
en ese bloque). En vez de dejarlo como una coincidencia frágil, se hizo explícito:
- Columna nueva `estudiantes.orden_lista` (INTEGER, NULL) en `core/constants.py::COLUMNAS_ESTUDIANTES`
  — se auto-migra sola al reiniciar (mecanismo ya existente del proyecto, sin tocar la BD a mano).
- `routes/profesor.py::portal_profesor()` — `ORDER BY grado, curso, (orden_lista IS NULL),
  orden_lista, apellido, nombre` (agrupa por curso primero para no interleavear bloques de distinta
  mención que comparten grado cuando un profesor técnico da varias; NULL-tolerant — quien no tenga
  orden importado cae al final de su bloque, alfabético).
- `scripts/aplicar_orden_listado.py` (nuevo) — lee el Excel con `core/importar_listado.py`
  (mismo parser/matching de la sesión 19, reutilizado tal cual) y fija `orden_lista` = posición
  del alumno dentro de su bloque. Dry-run por defecto. NO crea ni actualiza otros datos del
  estudiante, solo el campo de orden — si el alumno del archivo no matchea nadie en BD, se reporta
  y se omite (no crea duplicados).
- **Confirmado por Erick en producción:** ambos fixes (barra flotante + orden de lista) funcionan
  correctamente tras correr el script en Render Shell.

**LECCIÓN — el resize de viewport de Chrome no funciona en este entorno:** tanto el agente de
análisis como yo, en intentos independientes, confirmamos que `resize_window` no cambia el tamaño
real de la ventana/viewport en esta configuración de automatización (probado sobre una ventana ya
abierta y sobre una pestaña nueva propia — ninguna cambió de tamaño). No vale la pena seguir
intentando emulación de dispositivo móvil por este camino; para verificar cambios de CSS responsive
hay que confiar en el análisis estático del código (matemática de breakpoints/box model, que es
determinística) y pedirle confirmación visual a Erick en su propio teléfono después del deploy.

### 2026-08-29 (sesión 20 — fix Fotografía 4to/5to Artes Visuales + hallazgo: PLAN_ARTES no coincide con el currículo real en 3 de 4 menciones)

**Disparador:** Erick reportó que en el perfil de Carlos David Caminero, el selector de materias
de Artes Visuales (con grado=4to seleccionado) no mostraba ninguna opción de Fotografía, aunque
Carlos sí la imparte ahí. Confirmado por Erick: "se imparte en 4to, ya en quinto no se da
fotografía en artes visuales."

**Fix aplicado — "Fotografía Artística" movida de 5to a 4to en `PLAN_ARTES["ARTES VISUALES"]`:**
Corregido en los 3 lugares donde este catálogo vive duplicado (mismo patrón de "copias que
fosilizan" ya visto en sesiones anteriores):
- `core/constants.py` — `PLAN_ARTES["ARTES VISUALES"]["4to"/"5to"]`
- `templates/index.html` — chips de materias en el modal Nuevo/Editar usuario (`mats-artes_visuales`)
- `templates/planificacion.html` — catálogo JS del generador de planificación ABP

**HALLAZGO IMPORTANTE — no confundir dos catálogos distintos que coexisten en el código:**
- `PLAN_ARTES` (`core/constants.py`) — nombre + horas + grado, alimenta selectores de materia y
  el motor de notas/KPIs.
- `CURRICULUM_MULTIMEDIA` / `CURRICULUM_ARTES_VISUALES` / `CURRICULUM_MUSICA` / `CURRICULUM_TEATRO`
  (`core/curriculo_*.py`) — contenido pedagógico real (introducción, RAE, contenidos
  conceptuales/procedimentales/actitudinales) extraído de los 4 documentos oficiales del
  Bachillerato en Artes (MINERD), usado por `core/curriculo.py` → `routes/planificacion.py` para
  inyectar currículo oficial en los prompts de IA. Se nota que es extracción real (no inventada):
  tiene artefactos de OCR como "Instrumento I –Percusión", "C anto Coral I", "Te oría y
  Entrenamiento Musical III". **Este catálogo NO tiene campo `grado` por materia — solo `horas`.**

**El problema real, más allá de Fotografía:** al comparar nombres de materia entre ambos
catálogos para las 4 menciones:
- **MULTIMEDIA** — coinciden bien (por eso el fix de Fotografía se pudo hacer con confianza).
- **ARTES VISUALES** — **cero coincidencias.** `PLAN_ARTES` tiene 12 materias técnicas
  ("Historia del Arte Universal", "Lenguaje Plástico y Visual", "Escultura y Cerámica"...) que NO
  aparecen en el documento real (`CURRICULUM_ARTES_VISUALES` tiene 11 materias totalmente
  distintas: "Modelado I/II", "Diseño Bi y Tridimensional", "Pintura Mural y Decorativa"...).
- **MÚSICA** — mismo problema: `PLAN_ARTES` tiene 13 materias genéricas vs. 31 materias reales
  en `CURRICULUM_MUSICA` (Instrumento I-Guitarra/Teclado/Viento/Percusión, Canto Coral I/II/III,
  Armonía I, Refuerzo Sonoro, Tecnología Musical...).
- **TEATRO** — también difiere (16 materias reales vs. 5 genéricas por grado en `PLAN_ARTES`).

Conclusión: `PLAN_ARTES` para Artes Visuales/Música/Teatro parece haber sido construido con
nombres genéricos en algún momento, no derivado de los documentos oficiales reales. El caso de
Fotografía que reportó Erick es solo un síntoma puntual de un problema más grande en esas 3
menciones.

**Por qué no se pudo corregir de una vez — los 4 PDF originales ya no existen:**
`scripts/indexar_curriculos.py` (script viejo, del sistema institucional) muestra que los 4
documentos (`Bachillerato-multimedia.pdf`, `Bachillerato-en-musicapdf.pdf`,
`Bachillerato-en-teatro.pdf`, `Bachillerato-artes-visuales.pdf`) se indexaron una sola vez a un
sistema RAG (`core.rag.procesar_normativa`) desde la ruta vieja
`/Users/erickhernandez/elearning/uploads/archivos/`, que ya no existe en este Mac. El módulo que
guardaba ese texto completo (`normativa`) fue eliminado en la purga de la sesión 14. Verificado
que `database.db` local no tiene ninguna tabla de normativa/RAG. Sin el campo `grado` en
`core/curriculo_*.py` y sin los PDF originales ni su texto indexado, no hay forma confiable de
reconstruir `PLAN_ARTES` para Artes Visuales/Música/Teatro sin adivinar — mismo tipo de error
que ya se cometió una vez con Fotografía, pero multiplicado por ~58 materias.

**PENDIENTE PARA LA PRÓXIMA SESIÓN:**
Erick va a enviar los 4 documentos oficiales del Bachillerato en Artes (Multimedia ✓ ya
correcto, Artes Visuales, Música, Teatro — estos 3 con discrepancias confirmadas) o al menos la
sección/cuadro de "distribución del tiempo" (asignatura × grado × horas) de cada uno. Con eso:
1. Reconstruir `PLAN_ARTES["ARTES VISUALES"]`, `PLAN_ARTES["MÚSICA"]`, `PLAN_ARTES["TEATRO"]` en
   `core/constants.py` con los nombres y grados reales del documento.
2. Replicar el mismo cambio en `templates/index.html` (chips `mats-artes_visuales`,
   `mats-musica`, `mats-teatro`) y `templates/planificacion.html` (catálogo JS) — los 3 lugares
   donde `PLAN_ARTES` vive duplicado, mismo patrón que el fix de Fotografía de esta sesión.
3. Revisar si `core/curriculo_artes_visuales.py`/`_musica.py`/`_teatro.py` necesitan contenido
   adicional para materias que `PLAN_ARTES` tenga y el currículo real no cubra (o viceversa).
4. Confirmar con Erick si los perfiles de profesores de Artes Visuales/Música/Teatro ya
   existentes en BD tienen materias asignadas con los nombres viejos/genéricos de `PLAN_ARTES` —
   si es así, esos perfiles quedarán con materias "huérfanas" tras la migración de nombres y
   habrá que reasignarlas a mano (mismo patrón de riesgo que `scripts/auditar_materias_profesores.py`
   ya audita para Multimedia).

### 2026-08-28 (sesión 19 — Pase de Lista Grado+Modalidad, cargador adaptativo de Listado de Estudiantes, resets de notas/estudiantes)

**Disparador:** varios hilos que terminaron entrelazados — (1) pase de lista mezclaba estudiantes
de distintos grados/menciones bajo el mismo profesor, (2) separador `|` en materias de
`/mi-perfil` y `/usuarios` poco práctico, (3) el listado oficial de 4to Multimedia 2026-2027 no
terminaba de reflejarse en la plataforma, y (4) un fix de sesiones anteriores había dejado notas
inconsistentes entre grados. Se resolvió todo en cadena porque cada arreglo destapó el siguiente.

**1 — Separador de materias `|` → `,` → `;` → REVERTIDO a `|` (mi_perfil.html, usuarios.html):**
Cambié el separador visible de `|` a `,` a pedido explícito. El almacenamiento en BD siguió
pipe-delimitado en todo momento (muchísimos otros lugares del código hacen `.split('|')` sobre
`materia`/`asignaturas`) — la conversión coma↔pipe ocurría solo en el borde (leer para mostrar,
escribir al guardar). Detecté a medio camino que esto **casi reintroducía un bug ya resuelto**:
el historial (`commit b34d3b9`, jun-2026) muestra que el separador YA fue coma antes y se cambió
A pipe justamente porque materias reales del catálogo (ej. "Lenguaje Visual, Dibujo y Creación de
Personajes", MULTIMEDIA 4to) tienen coma en su propio nombre — usar coma como separador de UI las
parte en dos. Cambié el separador visible a `;` como remedio (no aparece en ningún nombre de
materia del catálogo). **Pero el usuario reportó que esto rompió Pase de Lista de un perfil de
profesor recién creado con varias materias ("solo se cargan dos")** — `portal_profesor()` sigue
parseando `materia`/`asignaturas` con `.split('|')` sin cambios; un perfil guardado durante la
ventana de hoy con `,`/`;` en vez de `|` quedó con el campo entero como una sola cadena larga en
vez de varias materias separadas. Revertido `mi_perfil.html`/`usuarios.html` al estado exacto
previo a esta sesión (`commit 791db03`, `commit 2887270`) — separador `|`, sin conversión de
formato. **Si algún perfil quedó guardado con el separador equivocado durante la sesión de hoy,
hay que volver a guardar sus materias a mano ahora que `|` está de vuelta.**
**LECCIÓN — dos capas:** (1) antes de cambiar un formato de separador/delimitador, revisar
`git log` por si ya se intentó y se revirtió, el motivo suele seguir vigente; (2) un cambio de
formato en la UI de un campo que otro código YA parsea con un delimitador fijo (`portal_profesor()`
usa `.split('|')`) no es solo cosmético — hay que rastrear TODOS los lugares que leen ese campo
antes de tocar cómo se escribe, no solo el punto de entrada/salida que se está editando.

**2 — Pase de Lista mezclaba estudiantes de distinto grado/sección/mención (`routes/profesor.py`,
`routes/asistencia.py`, `templates/profesor.html`):**
`portal_profesor()` cargaba TODOS los estudiantes del alcance del profesor en una sola lista al
entrar a `/profesor`, y `guardarAsistencia()` guardaba asistencia para esa lista completa sin
filtrar por la materia/grado seleccionados — un profesor con grado `4to,5to` que pasaba lista de
una materia de 4to terminaba registrando (falsamente, como "presente") a los alumnos de 5to
también. Fix en dos pasadas:
  - Primera pasada: agregado selector de Grado + Sección en Pase de Lista, con filtrado real del
    roster visible antes de guardar.
  - Segunda pasada (la correcta): para clases técnicas, Sección casi nunca varía (todos los
    alumnos por defecto quedan en `seccion='A'`) — el separador real es la **Modalidad** (mención:
    Multimedia/Teatro/Música/Artes Visuales/Danza). Ahora Pase de Lista alterna automáticamente
    entre Modalidad (2do ciclo) y Sección (1er ciclo) según el grado elegido. El backend
    (`POST /api/asistencia`) valida server-side que cada `estudiante_id` corresponda al
    grado/sección/modalidad declarados — defensa en profundidad, no confía ciegamente en lo que
    mandó el navegador.

**3 — Cargador adaptativo de "Listado de Estudiantes" — `core/importar_listado.py` (nuevo):**
El importador viejo (`/api/cargar-listado`, en `routes/estudiantes.py`) espera el LISTADO
institucional con una hoja POR GRADO nombrada literalmente "4TO"/"5TO (2)" — al subir un archivo
de un solo grado/mención con hoja llamada "Estudiantes 4TO MULTIMEDIA", usaba ese nombre de hoja
completo como si fuera el valor de `grado`, dejando `estudiantes.grado='Estudiantes 4TO
MULTIMEDIA'` y `curso` con texto duplicado várias veces (bug real encontrado en producción,
diagnosticado con `scripts/diag_curso_estudiante.py` contra la BD real de Render). Ahora ese
endpoint viejo RECHAZA archivos con nombre de hoja no reconocido (`commit 2095dcb`) en vez de
corromper datos en silencio.

Se construyó un módulo nuevo (`core/importar_listado.py`) usado tanto por
`scripts/cargar_listado_estudiantes.py` (CLI) como por dos endpoints nuevos en
`routes/profesor.py` (`/api/profesor/preview-listado-estudiantes` y
`/api/profesor/confirmar-listado-estudiantes`, con tarjeta de carga en `/profesor` Y en el
dashboard admin — un profesor solo ve/aplica sus propios grados/menciones, admin/directora sin
restricción). Flujo preview→confirmar: el servidor arma un plan sin escribir nada, el usuario lo
revisa, y solo confirma con un segundo POST — mismo patrón que otras cargas masivas del sistema.

Soporta DOS formatos del mismo tipo de archivo, detectados automáticamente sin que el usuario
tenga que decir cuál es cuál:
  - Un solo bloque por archivo ("Listado_Estudiantes_4TO_A_Multimedia.xlsx").
  - El LISTADO institucional completo del año — una hoja por grado, y dentro de cada hoja varios
    bloques "DATOS DEL ALUMNO" (uno por mención en 2do ciclo, uno por sección en 1er ciclo), con
    el grado/mención en formato y posición inconsistentes ENTRE BLOQUES DEL MISMO ARCHIVO:
    `'4TO A' + 'MUSICA'` (sección pegada al grado) vs. `'5TO' + 'A Musica'` (sección pegada a la
    mención, al revés) vs. `'3ERO' + 'SECCION B'` (1er ciclo, sin mención). El algoritmo busca la
    celda que dice "GRADO" en cada fila de encabezado y toma las siguientes celdas con valor (no
    otra etiqueta) en orden — sin asumir columna fija.

**Batería de bugs reales encontrados probando contra el archivo institucional completo (659-660
alumnos, 20-22 bloques) — cada uno verificado con los datos reales antes de darlo por corregido:**

1. **Token en memoria perdido en redeploy** (`commit d054fb7`) — el diseño original guardaba el
   plan preview en un dict del proceso bajo un token de 15 min. Con `gunicorn --workers 1` y
   varios redeploys seguidos (normal en una sesión de iteración rápida como esta), cualquier
   deploy entre subir el archivo y tocar "Confirmar" borraba el dict — "Confirmar carga" fallaba
   sin dejar rastro claro. Ahora el navegador reenvía los datos completos (grado/sección/mención/
   alumnos) al confirmar, sin depender de estado del servidor entre los dos pasos.
2. **Coincidencia por nombre sin acotar por grado** (`commit 984c8b6`) — el emparejamiento
   nombre+apellido exacto (para alumnos sin cédula) no estaba limitado al grado/mención objetivo.
   27 alumnos de "4to Multimedia" coincidían por nombre exacto con estudiantes YA existentes en
   '3ERO' (personas reales distintas con el mismo nombre) — sin el fix, se habrían reasignado por
   error. Ahora tanto el match exacto como el fuzzy están acotados a
   `UPPER(grado)=UPPER(?) AND mencion` (comparación case-insensitive porque la BD real usa
   MAYÚSCULA: `'4TO'`, `'3ERO'`, verificado con `scripts/diag_roster_profesor.py`).
3. **Formato de grado equivocado** — el parser escribía `grado='4to'` minúscula; la BD real usa
   `'4TO'`/`'5TO'`/`'3ERO'`/`'1ERO'` (2 letras de sufijo para 4to-6to y 2do, mala suerte 3 letras
   para 1ro y 3ro — `_GRADO_SALIDA` en `core/importar_listado.py` mapea esto explícito).
4. **Cédulas duplicadas entre estudiantes DISTINTOS** — 5 pares de alumnos con nombres
   completamente distintos comparten cédula por error de tecleo real del coordinador. Sin
   salvaguarda, se habrían fusionado en un solo registro (`cedula_en_conflicto()`: nombre muy
   distinto pese a cédula igual, `SequenceMatcher <0.5` → a ambos se les quita la cédula del
   archivo, quedan con ID provisional y advertencia visible en el preview).
5. **Duplicados DENTRO del mismo bloque** — mismo alumno repetido, o cédula compartida entre dos
   personas dentro del mismo bloque, no se detectaban porque el plan se calcula contra la BD
   ANTES de escribir nada (dos ocurrencias en el mismo archivo no se ven entre sí sin un paso
   previo) — `resolver_duplicados_intra_bloque()`.
6. **El bug real que reportó el usuario** (`commit 404a771`) — "13 estudiantes de 5to aparecen en
   Multimedia pero según el listado están en otra mención". Verificado celda por celda: dentro
   del bloque "5TO MULTIMEDIA" el archivo real tiene, sin avisar, un SEGUNDO grupo de 17 alumnos
   con su propia fila de encabezado de columnas ("No./NOMBRE/APELLIDO...") pero SIN la fila
   "DATOS DEL ALUMNO / GRADO / MENCIÓN" que le correspondería — defecto del archivo del
   coordinador, no dato mal leído. El parser, al no ver esa etiqueta, absorbía el grupo en
   silencio dentro del bloque anterior. Ahora `_leer_alumnos_bloque()` detecta cuando aparece
   OTRA fila de encabezado dentro de un bloque y corta ahí; el grupo restante se marca
   `sin_mencion_detectada=True` y **no se escribe** (aplicar_carga_multi se niega a adivinar la
   mención) — se muestra con advertencia roja explícita en el preview en vez de mezclarse.
   Mismo defecto encontrado en "3ERO Sección B" (30 alumnos huérfanos más). Con el fix, "5TO
   MULTIMEDIA" da exactamente 23 alumnos (el número real que confirmó el usuario) en vez de 40.

**LECCIÓN PERMANENTE — con datos reales de coordinación, nunca asumir que un archivo tiene una
estructura limpia y consistente:** cada uno de estos 6 bugs solo salió a la luz probando contra
el archivo REAL completo (no un caso de prueba inventado) y varias veces contra la BD real de
producción vía scripts de diagnóstico (`diag_curso_estudiante.py`, `diag_roster_profesor.py`,
`diag_listado_vs_bd.py`, `diag_5to_multimedia.py`, `diag_ids.py` — todos de solo lectura, quedan
en `scripts/` para la próxima vez que algo así no cuadre). Cuando el usuario reporta un número que
no cuadra ("debería ser 23, dice 41"), verificar con una consulta exacta contra la BD real antes
de teorizar — la causa real casi nunca es la primera hipótesis.

**4 — Reset de notas y de estudiantes (a pedido explícito, no construido como botón en la app):**
Un fix de sesiones anteriores dejó notas inconsistentes (algunos estudiantes promovidos, otros no,
mezcla de datos entre grados) y sin notas no se puede evaluar promoción. Y las cargas repetidas
del listado (algunas con el cargador viejo, corruptas) dejaron conteos inflados. Dos scripts,
ambos dry-run por defecto + `--commit`, deliberadamente NO como botón en la UI (una operación de
este tamaño no debería quedar a un clic de cualquier sesión activa):
  - `scripts/resetear_notas_todos.py` — borra las 5 tablas donde el esquema guarda notas reales
    (`materias_calificaciones`, `calificaciones_periodo`, `notas_componentes`,
    `notas_competencias_ce`, `notas_actividad`) y resetea a 0 las ~50 columnas de `estudiantes`
    que las cachean. NO toca asistencia, cuaderno anecdótico/casos/reportes (quedan en el
    expediente de cada estudiante, confirmado con el usuario) ni historial de promociones.
  - `scripts/resetear_estudiantes_todos.py` — borra `estudiantes` + las 24 tablas que dependen de
    `estudiante_id`/`est_id` (lista obtenida EJECUTANDO `migrar_bd()` contra una BD temporal e
    introspeccionando el esquema real vía `PRAGMA table_info` — no escrita a mano; así se
    encontraron 2 tablas que un primer intento con regex sobre el archivo de definiciones se
    había saltado: `inscripciones`, `retiros_traslados`). Mantiene intactos `usuarios` (cuentas de
    login) y, a propósito, `expedientes_historicos` (el archivo digitalizado de 25+ años del
    centro — vinculado a `estudiantes.id` de forma opcional, dataset categóricamente distinto al
    roster del año actual, no algo que este reset deba destruir sin pedirlo aparte).

**Scripts de diagnóstico nuevos en `scripts/` (todos de solo lectura):**
`diag_curso_estudiante.py <nombre>`, `diag_roster_profesor.py <username>`,
`diag_listado_vs_bd.py`, `diag_5to_multimedia.py`, `diag_ids.py <id1> <id2> ...`,
`conteo_documentos.py`.

**Pendiente para la próxima sesión:**
- El coordinador debe confirmar la mención/sección real de los 47 alumnos huérfanos (17 de 5to +
  30 de 3ero B — lista completa de nombres/cédulas ya entregada al usuario en esta sesión) y
  agregar la fila de encabezado faltante en el Excel antes de recargar ese grupo.
- Correr `scripts/resetear_estudiantes_todos.py --commit` de nuevo (los datos actuales en Render
  todavía tienen los 40 de 5to Multimedia mezclados, de antes de este fix) y volver a cargar
  `LISTADO AÑO 2026-2027.xlsx` ya corregido.
- Verificar si el mismo defecto de "grupo sin encabezado" aparece en algún otro grado además de
  3ero B y 5to — no se revisó exhaustivamente cada uno de los 20 bloques uno por uno, solo se
  confirmó que el algoritmo ahora los detecta automáticamente si aparecen.

### 2026-08-25/26 (sesión 18 — fix selector de grado en Planificación + módulo nuevo "Coherencia Horizontal")

**Fix rápido — Estrategias Didácticas solo mostraba materias de 4to** (commit `585ae91`):
El tab "Estrategias Didácticas" de `/planificacion` nunca tuvo un `<select id="e-grado">` —
solo mención y asignatura. `actualizarMaterias('e')` leía `document.getElementById('e-grado')`,
no encontraba el elemento, y caía al fallback hardcodeado `'4to'`. Un profesor de 4to Y 5to
(como Erick) nunca podía generar estrategias para materias de 5to. Los tabs "Planificación de
Clase" (`p-grado`) y "Crear Rúbrica" (`r-grado`) sí tenían el selector — misma familia de bug
que la sesión 17 (una copia del formulario evolucionó, la otra fosilizó). Agregado
`<select id="e-grado">` idéntico a los otros dos. Sin cambios de backend — el nombre de la
materia ya es único por grado dentro de cada mención.

**Módulo nuevo — Coherencia Horizontal del Componente Especializado** (`/coherencia`):

El coordinador pidió una sección para documentar, por asignatura y grado, cómo se articulan
las materias del componente especializado con el resto del currículo — siguiendo una plantilla
Word oficial del centro. Se armó en varias vueltas, cada una corrigiendo algo real:

1. **v1 (commit `2e8d684`)** — construida solo a partir del mandato en texto (sin ver la
   plantilla real): matriz genérica área/competencias/contenido/indicador/articulación,
   modelada sobre `routes/poa.py` (mismo patrón: encabezado + filas, dueño edita lo suyo /
   admin ve todo). Quedó **completamente descartada** un día después al leer el `.docx` real.
2. **Rediseño a la plantilla real (commit `962b52b`)** — el coordinador entregó
   "Coherencia Horizontal componente especializado.docx"; se leyó su XML directamente (no se
   asumió nada) y la estructura real es por completo distinta: encabezado institucional fijo +
   Propósito + identificación (Docente/Asignatura/Mención/Grado) + **4 períodos fijos del
   calendario** (Ago-Oct, Nov-Ene, Feb-Mar, Abr-Jun), cada uno con 1 Competencia Laboral y N
   filas de RAE | Conceptos · Procedimientos · Actitudes y valores | Producto | Recursos.
   Tablas nuevas `coherencia_periodo` + `coherencia_rae` (reemplazan a `coherencia_horizontal_fila`
   de la v1, que quedó vestigial — limpiada con `scripts/dropear_coherencia_fila_v1.py --commit`,
   commit `590e574`). Los 4 períodos se crean solos al crear la matriz, el docente no los agrega.
3. **Exportación a Word** (`routes/generar_coherencia_docx.js`, mismo commit `962b52b`) — reutiliza
   el mecanismo ya existente del generador ABP (`routes/planificacion.py::exportar_planificacion_docx`
   → subprocess a Node con la librería `docx`), no se inventó uno nuevo. Anchos de columna,
   sombreado (`C1E4F5`) y `gridSpan`/`vMerge` calcados celda por celda del XML original —
   verificado comparando el `.docx` generado contra el original antes de dar el commit por bueno.
4. **"Documento en modo solo lectura"** (sin cambio de código) — el `.docx` generado nunca tuvo
   ninguna protección (`documentProtection`, `writeProtection`, "marcar como final" — todos
   ausentes, verificado descomprimiendo el archivo). Lo que se veía era la Vista Protegida de
   Word, que se activa sola en cualquier archivo con Mark-of-the-Web (descargado del navegador).
   Se resuelve del lado del usuario ("Habilitar edición", o guardar el archivo antes de abrirlo
   en vez de abrirlo directo desde la barra de descargas) — no es arreglable desde el servidor.
   Se aprovechó para agregarle metadatos reales (`creator`/`title`/`description` — antes salía
   "Un-named") — commit `8ad8773`.
5. **Bug real de UX — "lleno los 4 períodos y solo se guarda uno"** (commit `fd9a6cb`): cada
   período tenía su propio `<form>` independiente (Competencia Laboral) y su propio mini-form de
   "agregar RAE" — llenar varios y enviar solo el último perdía el resto, porque cada submit
   recargaba toda la página. Rediseñado a **un solo `<form>`** con los 4 períodos dentro; "+
   Agregar fila" ahora es 100% cliente (JS clona una fila editable sin recargar la página); un
   único botón al final ("Guardar todo y generar Word") guarda los 4 períodos completos en un
   solo POST (arrays paralelos `rae_N[]`/`conceptos_N[]`/etc. por índice — filas vacías
   agregadas y no llenadas se descartan solas) y dispara la descarga del `.docx` actualizado vía
   un iframe oculto tras el redirect, sin salir de la página ni bloqueo de pop-ups.
6. **Tipografía del documento** (commit `025a2d4`) — a pedido: títulos (encabezado, Docente/
   Asignatura/Mención/Grado, título de cada período, Competencia Laboral, encabezados de
   columna) en **Times New Roman 12pt**; todo el copy (lo que escribe el docente) en
   **Arial 12pt**. Verificado leyendo `rFonts`/`sz` de cada `<w:r>` del XML resultante, no solo
   visualmente.

**LECCIÓN — verificar contra el artefacto real antes de construir, no contra el mandato en
texto:** la v1 de este módulo se descartó por completo porque se construyó a partir de la
descripción en prosa del mandato (`MEJORAS/coherencia_1.md`) sin haber visto todavía el `.docx`
de la plantilla real. En cuanto el coordinador lo entregó, quedó claro que la estructura no se
parecía en nada. Cuando el usuario menciona que existe un documento/plantilla/ejemplo de
referencia, pedirlo y leerlo (`unzip` + parseo del XML para `.docx`) **antes** de diseñar el
schema o la UI — no asumir la estructura a partir de la descripción.

**Pendiente:** ninguno conocido para este módulo. Erick debe seguir cargando la lista oficial de
estudiantes de 4to y 5to Multimedia para el año 2026-2027 (pendiente heredado de la sesión 17).

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
