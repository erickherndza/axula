# fix-axula.md

Plan de corrección para la plataforma Axula, ordenado por dependencia técnica.
Cada etapa incluye el diagnóstico, el archivo afectado, la corrección conceptual
y comandos `grep`/verificación para Claude Code.

**Regla de oro de esta auditoría:** el código compila e importa con una BD que
ya tiene datos; eso oculta bugs que solo aparecen en ramas no ejecutadas o en
instalación limpia. Verificar siempre contra BD vacía además de la de producción.

Auditoría realizada el 3 de julio de 2026 sobre el snapshot `axula-main.zip`.
12 hallazgos. Se corrigen en 4 fases: primero lo que rompe arranque y seguridad,
luego los datos, luego el motor de evaluación, luego la UI y la multi-centro.

---

## Resumen de hallazgos

| # | Hallazgo | Severidad | Fase |
|---|----------|-----------|------|
| 1 | `import os` faltante en `core/database.py` (arranque limpio roto) | Crítico latente | 0 |
| 2 | Escalación de privilegios en firmas de acuerdos (`casos.py`) | Seguridad alta | 0 |
| 7 | Bugs de `/profesor`: multigrado, filtro asignaturas, traceback expuesto | Media / seguridad | 0 |
| 8 | APIs devuelven 302 a login en vez de 401 JSON; thread de backup por request | Menor | 0 |
| 11 | `materias_calificaciones` sin año escolar + UNIQUE sobreescribe histórico | Crítico (datos) | 1 |
| 12 | Identidad de materias por string, sin catálogo con IDs | Alto (datos) | 1 |
| 9 | Nota manual del profesor invisible en KPIs/perfil/dashboard | Alto (consistencia) | 2 |
| 10 | `registro_notas_periodo` desconectado del boletín/perfil/padres | Crítico (consistencia) | 2 |
| 3 | Motor de evaluación desalineado del modelo MINERD por competencias | Alto (correctitud) | 3 |
| 4 | Cierre de período: alumnos sin calificar cuentan como 0 sin aviso | Alto (correctitud) | 3 |
| 5 | Dos portales de evaluación paralelos (`/evaluacion` v1 y v2) | Media (UX) | 4 |
| 6 | Acoplamiento a C.E. Benito Juárez / MULTIMEDIA (~180 refs) | Media (escalabilidad) | 4 |

**Dependencias entre fases:** la Fase 1 (catálogo de materias + año escolar) es
prerrequisito de la Fase 2 (tabla canónica de notas). La tabla canónica de la
Fase 2 es prerrequisito del motor por competencias de la Fase 3. La Fase 4 (UX y
multi-centro) puede hacerse en paralelo pero rinde más después de la 3.

---

## FASE 0 — Arranque, seguridad y correcciones inmediatas

Cambios de bajo riesgo y alto impacto. No tocan el modelo de datos. Hacer primero.

### Hallazgo 1 — `import os` faltante en `core/database.py`

**Diagnóstico.** `_seed_admin()` usa `os.environ.get()` pero el módulo nunca
importa `os`. En producción no explota porque la BD ya tiene usuarios y esa rama
no corre. En instalación limpia (Render recrea disco, restauración desde cero,
clon nuevo) la app muere con `NameError: name 'os' is not defined` antes de
arrancar. Confirmado: con BD vacía el import falla exactamente ahí.

**Corrección.** Agregar `import os` al bloque de imports (cerca de la línea 4,
junto a `import sqlite3`).

**Verificación:**
```bash
grep -n "^import os" core/database.py
rm -f /tmp/test_limpia.db && DATABASE_PATH=/tmp/test_limpia.db python3 -c "import app; print('ARRANQUE LIMPIO OK')"
```

### Hallazgo 2 — Escalación de privilegios en firmas de acuerdos

**Diagnóstico.** En `routes/casos.py` (~línea 574), `guardar_firma()` tiene dos
huecos de autorización:

- **Rama con token (padre/tutor):** el token se valida contra `token_firma`,
  pero `rol_firmante` se toma del body sin restricción. Un tutor con su enlace
  legítimo puede enviar `rol_firmante: "director"` y falsificar la firma del
  director, coordinador o psicóloga, e incluso disparar `firmado=1`.
- **Rama con sesión (staff):** solo verifica que haya usuario autenticado. No
  cruza el rol de sesión contra `rol_firmante`, así que cualquier profesor o
  digitador puede firmar como director.

**Corrección conceptual.**
- Rama token: forzar `rol_firmante = "tutor"` en el servidor, ignorando lo que
  venga en el body.
- Rama staff: mapear rol de sesión → campo de firma permitido
  (`coordinador` → `firma_coordinador`, `director`/`directora` → `firma_director`,
  `psicologa` → `firma_psicologa`). Rechazar con 403 si el rol de sesión no
  corresponde al `rol_firmante` solicitado.
- Aplicar el mismo criterio de solo-lectura autorizada a `acuerdo_pdf_firmado`.

**Verificación:**
```bash
grep -n "rol_firmante" routes/casos.py
# Debe existir una asignación server-side rol_firmante="tutor" en la rama token,
# y un map rol_sesion->campo_firma en la rama staff. Ningún uso directo de
# data.get("rol_firmante") para decidir a quién se firma.
```

### Hallazgo 7 — Bugs de `/profesor`

**Diagnóstico (3 sub-bugs en `routes/profesor.py`, `portal_profesor`).**
- Toma `grados_prof[0]`: un profesor multigrado solo ve el plan del primer grado.
- Filtro de asignaturas por match exacto en minúsculas; si el perfil dice
  "Taller de Fotografía" y el plan dice "Fotografía", el filtro no matchea y el
  fallback muestra el plan completo — el profesor ve materias que no imparte, sin
  aviso.
- El handler de excepción devuelve el **traceback al navegador**
  (`err_detail[:1000]`) — divulgación de rutas internas y estructura de código.

**Corrección conceptual.**
- Iterar sobre todos los grados del alcance del profesor, no solo el primero;
  construir el plan como unión de los planes por grado que imparte.
- Filtro de asignaturas tolerante: normalizar (sin acentos, minúsculas) y usar
  coincidencia por inclusión, no igualdad exacta. Si no hay coincidencia, mostrar
  un aviso explícito ("no se detectaron materias asignadas") en vez de caer al
  plan completo en silencio.
- En producción, el handler de excepción debe registrar el traceback en el log y
  devolver una página de error genérica al usuario, sin detalles internos.

**Verificación:**
```bash
grep -n "grados_prof\[0\]" routes/profesor.py   # no debe quedar
grep -n "err_detail\[:1000\]\|format_exc()" routes/profesor.py  # no debe exponerse al cliente
```

### Hallazgo 8 — Menores: 302 en APIs y thread de backup por request

**Diagnóstico.**
- Endpoints protegidos devuelven `302` (redirect a login) cuando no hay sesión,
  en vez de `401` JSON. El `fetch` del frontend sigue el redirect y recibe HTML,
  rompiendo el manejo de errores. Confirmado en `/api/coordinador/resumen`,
  `/api/archivos`.
- `respaldo_diario` lanza un hilo en **cada** GET. El lock interno evita
  respaldos duplicados, pero crear un thread por request es desperdicio.

**Corrección conceptual.**
- El decorador de auth debe distinguir rutas `/api/*`: para ellas responder
  `401` con cuerpo JSON `{"error": "no autenticado"}` en vez de redirect.
- En `respaldo_diario`, chequear `_ultimo_respaldo == _hoy()` antes de crear el
  hilo; solo lanzarlo si toca respaldo.

**Verificación:**
```bash
grep -n "def api_login_required\|401" core/*.py | head
grep -n "_ultimo_respaldo\|_hoy()" core/backup.py app.py
```

---

## FASE 1 — Cimientos de datos: catálogo de materias y año escolar

Prerrequisito de todo el trabajo de consistencia de notas. Requiere migración.

### Hallazgo 12 — Catálogo de materias con IDs

**Diagnóstico.** No existe una tabla de materias. Cada fuente (carga masiva,
manual, evaluación) escribe el nombre de la materia como texto libre. El boletín
reconcilia con heurísticas de normalización (acentos, mayúsculas, sufijos romanos
`_norm_sin_nivel` para "Fotografía" == "Fotografía I"). Cada choque de nombres ha
requerido un parche nuevo; el patrón seguirá hasta que exista identidad estable.

**Corrección conceptual.**
- Crear tabla `materias` (`id`, `nombre_canonico`, `nombre_normalizado`, `area`,
  `tipo` académico/técnico/artística, `ciclo`, `activa`).
- Semilla desde los nombres distintos ya presentes en `materias_calificaciones`
  y `calificaciones_periodo`, resolviendo duplicados por normalización.
- Agregar `materia_id` (FK a `materias`) a las tablas de notas. Mantener el campo
  de texto durante la transición como respaldo, pero la lógica nueva resuelve por
  `materia_id`.
- Un helper `resolver_materia_id(nombre)` centraliza el matching difuso en un solo
  lugar (en vez de repetirlo en cada vista).

**Verificación:**
```bash
grep -rn "_norm_sin_nivel\|_canon_sin_nivel" routes/ core/  # debería reducirse a resolver_materia_id
sqlite3 axula.db "SELECT COUNT(DISTINCT nombre_canonico) FROM materias;"
python3 -c "from core.evaluacion_engine import resolver_materia_id; print(resolver_materia_id('Fotografía I'))"
```

### Hallazgo 11 — Año escolar en `materias_calificaciones`

**Diagnóstico.** `materias_calificaciones` tiene `UNIQUE(estudiante_id, materia)`
y ninguna columna de año escolar (solo `fecha_carga`). Al cargar los boletines de
2026-2027, las notas nuevas **sobreescribirán** las de 2025-2026 — pérdida
silenciosa de histórico. El boletín además consulta sin filtro de año, mezclando
épocas.

**Corrección conceptual.**
- Agregar columna `anio_escolar` con default = año actual para los registros
  existentes.
- Cambiar la restricción a `UNIQUE(estudiante_id, materia_id, anio_escolar)`
  (junto con el `materia_id` del Hallazgo 12).
- Todas las lecturas de esta tabla (boletín, perfil, KPIs) filtran por
  `anio_escolar`.

**Verificación:**
```bash
sqlite3 axula.db "PRAGMA table_info(materias_calificaciones);" | grep anio_escolar
grep -rn "FROM materias_calificaciones" routes/ core/ scripts/ | grep -v "anio" 
# ^ toda lectura debe filtrar por anio; revisar las que no lo hacen
```

---

## FASE 2 — Una sola fuente de verdad para las notas

El corazón del pedido: que la nota de cada estudiante se corresponda entre el
perfil, el boletín y el portal de padres. Depende de la Fase 1.

### Diagnóstico del flujo actual

Hoy hay **tres caminos de captura** que escriben en **cuatro almacenes**, y cada
vista lee una combinación distinta:

- `materias_calificaciones` ← carga masiva (PDF/Excel/digitador). La leen boletín,
  perfil, expediente, y el recalculador de KPIs.
- `calificaciones_periodo` ← nota manual del profesor. La lee el boletín (como
  overlay), pero **no** el recalculador de KPIs.
- `registro_notas_periodo` ← módulo `/evaluacion` (actividades + puntos). **Solo
  la lee el propio motor de evaluación.** Nadie más.
- `estudiantes.p_acad / acad_p1..p4` ← caché de KPIs recalculado por script, que
  solo mira `materias_calificaciones`. La leen perfil, listados y dashboard.

De ahí las inconsistencias que se ven en pantalla.

### Hallazgo 9 — Nota manual invisible en KPIs/perfil/dashboard

**Diagnóstico.** `registrar_calificacion()` guarda en `calificaciones_periodo` y
el boletín la muestra, pero `scripts/recalcular_kpis.py` recalcula `p_acad` y
`acad_p1..p4` **solo desde `materias_calificaciones`**. Resultado: el boletín dice
85 y el perfil dice 0 (o la nota vieja del Excel).

### Hallazgo 10 — `registro_notas_periodo` es un callejón sin salida

**Diagnóstico.** El profesor que usa el flujo moderno de evaluación produce notas
en `registro_notas_periodo`, que no llegan al boletín, al perfil, a los KPIs ni al
portal de padres. Todo ese trabajo es invisible fuera del propio módulo. Es la
ruptura más grave del flujo.

### Corrección conceptual (resuelve 9 y 10 juntos)

Designar **`calificaciones_periodo` como tabla canónica** y convertir el resto en
afluentes o cachés derivados. No sincronizar las cuatro entre sí (multiplica los
puntos de falla): una sola fuente de verdad, y todo lo demás deriva de ella.

1. Extender `calificaciones_periodo` con `origen TEXT` (`manual` | `actividades` |
   `importacion`) y `materia_id FK`.
2. Los tres caminos de captura desembocan ahí:
   - Carga masiva → upsert con `origen='importacion'`. `materias_calificaciones`
     queda como staging de importación (o se migra y retira).
   - Cierre de período del módulo `/evaluacion` → upsert de la nota calculada con
     `origen='actividades'`. **Esta única conexión revive el callejón sin salida
     del Hallazgo 10.**
   - Entrada manual → `origen='manual'` (ya existe).
3. Precedencia explícita al hacer upsert: `manual > actividades > importacion`,
   con auditoría de quién pisó qué nota (ya hay `_audit`, reutilizarlo).
4. KPIs como caché derivado: función `recalcular_kpis_estudiante(est_id)` que lee
   **solo la canónica** y se invoca al final de cada escritura (los tres caminos).
   El script manual pasa de ser el mecanismo de consistencia a ser herramienta de
   reparación.
5. Un solo helper de lectura `obtener_notas_estudiante(est_id, anio)` en el engine.
   Boletín, perfil, portal de padres y dashboard lo consumen. Así, por
   construcción, el boletín y el perfil muestran el mismo número.

**Verificación:**
```bash
grep -n "origen" core/constants.py | grep calificaciones_periodo
grep -rn "def recalcular_kpis_estudiante\|def obtener_notas_estudiante" core/
# El cierre de periodo debe escribir en la canónica:
grep -n "calificaciones_periodo" core/evaluacion_engine.py
# Boletín, perfil y padres deben usar el helper compartido, no queries sueltas:
grep -rn "obtener_notas_estudiante" routes/calificaciones.py routes/perfil.py routes/portal_padres.py
```

**Prueba de consistencia (la que valida el pedido del usuario):**
```bash
# Registrar una nota manual y confirmar que perfil y boletín coinciden:
python3 - <<'EOF'
import app
c = app.app.test_client()
# (autenticar como profesor, registrar nota 85 en una materia/periodo,
#  luego leer /api/calificaciones/boletin/<id> y el perfil del mismo alumno;
#  ambos deben devolver 85 para esa materia/periodo)
EOF
```

---

## FASE 3 — Motor de evaluación alineado al modelo MINERD

Hace que las notas sean correctas según la normativa, no solo consistentes.
Depende de la tabla canónica (Fase 2).

> **Advertencia de alcance.** La fórmula descrita corresponde a los registros de
> grado vigentes bajo las Ordenanzas 04-2021 / 02-2022. El header del engine
> menciona la 04-2023. **Antes de implementar, confirmar con la coordinación del
> C.E. Benito Juárez qué versión del registro entregó el distrito para el año
> escolar 2025-2026.** Las casillas RP y la ponderación 70/30 deben coincidir
> exactamente con el papel que los profesores transcriben. Si el distrito entregó
> otra versión, esa manda.

### Hallazgo 3 — Alineación al modelo por competencias

**Diagnóstico.** El sistema calcula por materia: presupuesto de 100 puntos por
período, `(obtenido/posible)×100`, y la nota final es promedio simple de períodos.
El registro oficial exige nota **por competencia específica** (CE1–CE7), con
casillas P1, P2, RP, P3, P4, RP, y una fórmula final ponderada 70/30. `competencia_id`
existe en la tabla de actividades pero es opcional y el engine lo ignora. No existe
la Recuperación Pedagógica (RP), que es casilla obligatoria y derecho del alumno
(<70 → actividades complementarias).

**Corrección conceptual.**
1. Tabla `competencias_especificas_basicas` (`id`, `area_codigo`, `ciclo`,
   `grado`, `orden` 1–7, `codigo` p.ej. `CE1-MAT`, `descripcion_corta`,
   `descripcion_oficial`, `bloque` `'70'`|`'30'`). Semilla: las 7 CE por área
   básica de los registros oficiales (1er ciclo: registro 1ro–3ro; 2do ciclo:
   registros 4to–6to). El patrón ya existe en `core/curriculo_*.py` para técnicas.
2. `competencia_id` obligatorio cuando `_es_materia_basica(materia)`; validar en
   `crear_actividad_v2`.
3. En `evaluacion_engine.py`:
   - `calcular_nota_periodo_por_ce(est, materia, ce_id, periodo)` =
     `(obtenido/posible)*100` dentro de esa CE.
   - `calcular_cf_oficial(est, materia)`:
     - 70% = suma(P y RP de CE1–CE4) × 0.70/16
     - 30% = suma(P y RP de CE5–CE7) × 0.30/12
     - CF = redondeo(70% + 30%)
   - Nuevo tipo de actividad `recuperacion_pedagogica`: ligada a una CE y a un
     bloque (P1–P2 o P3–P4), solo asignable a alumnos con promedio de esa CE < 70.
4. La nota por CE y la CF se escriben en la tabla canónica (Fase 2), con `ce_id`
   opcional. El boletín por competencias sale de la misma tabla, sin otra migración.

**Verificación:**
```bash
python3 -c "from core.evaluacion_engine import calcular_cf_oficial; print('OK')"
# Test con el ejemplo del registro oficial: 70%=57 + 30%=26 → CF debe dar 83.
sqlite3 axula.db "SELECT codigo, bloque FROM competencias_especificas_basicas WHERE area_codigo='MAT' ORDER BY orden;"
```

### Hallazgo 4 — Cierre de período con alumnos sin calificar = 0

**Diagnóstico.** Al cerrar un período, "las actividades sin calificar cuentan como
0". Un profesor que cierra con una actividad a medias hunde las notas de todo el
curso sin advertencia. `periodo_status` avisa sobre puntos sin asignar, pero no
sobre **alumnos sin calificar**.

**Corrección conceptual.** Antes de permitir el cierre, contar alumnos sin
calificar por actividad y mostrar advertencia bloqueante (o confirmación
explícita): "N estudiantes sin calificar en 'Título' recibirán 0". Nunca aplicar
el 0 en silencio.

**Verificación:**
```bash
grep -n "def periodo_status\|sin calificar\|sin_calificar" routes/evaluacion.py
# La respuesta de cierre debe incluir un conteo de alumnos sin nota por actividad.
```

---

## FASE 4 — Practicidad de la UI y multi-centro

No cambia correctitud; hace la plataforma usable por profesores reales y por
otros centros. Puede correr en paralelo, rinde más después de la Fase 3.

### Hallazgo 5 — Unificar los dos portales de evaluación

**Diagnóstico.** Coexisten `/evaluacion` (v1, modal + filtros) y
`/evaluacion/panel` (v2, presupuesto de puntos). Vocabulario ajeno al registro
físico: la UI habla de "actividades", "puntos", "planificación" cuando el profesor
de básicas piensa en "secuencia", "competencias", "P1–P4, RP".

**Corrección conceptual.**
- Retirar v1 → redirect a v2.
- Vocabulario del registro físico en toda la UI de básicas. "Actividad" se
  mantiene pero agrupada bajo "Secuencia del período"; "Puntos disponibles" →
  "Instrumentos del período (suman 100 pts)"; selector de CE con código oficial y
  descripción corta.
- **Vista registro** (espejo del registro físico): grilla alumnos × P1 P2 RP P3 P4
  RP por CE, con tabs de CE, semáforo <70, y export PDF/Excel con el layout del
  registro físico para transcripción directa.
- Reducir fricción de entrada: (a) si el profesor no tiene planificación, ofrecer
  crear una secuencia mínima inline con las CE del período, en vez del error seco
  "Debe vincular la actividad a una planificación"; (b) calificación en grilla con
  navegación por teclado (Tab/Enter avanza de celda, como Excel); (c) al abrir el
  panel, aterrizar en el período activo del calendario escolar, sin pedir filtrar
  materia/grado/período cada vez.

**Verificación:**
```bash
grep -rn "portal_evaluacion\|evaluacion.html" templates/ routes/  # v1 debe redirigir
# La vista registro debe existir y exportar con layout MINERD.
```

### Hallazgo 6 — Desacoplar del C.E. Benito Juárez / MULTIMEDIA

**Contexto normativo.** El nivel secundario dominicano tiene tres modalidades
oficiales (Ley 66-97, Ord. 03-2013): Académica, Técnico-Profesional y en Artes.
"Ciencias", "informática", "finanzas" no son modalidades; son salidas/opciones
dentro de ellas. Adaptar Axula a un liceo de Ciencias (Académica) solo requiere el
catálogo en BD. Adaptarlo a un politécnico (Técnico-Profesional) implica además un
modelo de evaluación por módulos formativos que hoy no existe — cambio mayor,
fuera del alcance de este documento salvo decisión explícita.

**Diagnóstico.** ~180 referencias hardcodeadas a menciones de artes fuera de los
archivos de currículo. `"Centro Educativo en Artes Benito Juárez"` como fallback
en 10+ sitios. Patrones problemáticos:
- Plan de estudio en código (`PLAN_ARTES`, `PLAN_MULTIMEDIA`, `CURRICULUM_ARTES`
  en `constants.py`). Para otro liceo hay que editar Python y redesplegar.
- `MULTIMEDIA` como default silencioso en 6+ puntos (incluido el schema:
  `mencion TEXT NOT NULL DEFAULT 'MULTIMEDIA'`). Un profesor de Música sin mención
  configurada ve el plan de Multimedia sin aviso.
- Mención derivada por `split()[-1]` sobre el curso; menciones de dos palabras
  ("ARTES VISUALES", "CINE Y FOTOGRAFÍA") rompen el parseo. Los parches accent-safe
  LIKE fueron síntoma de esta raíz.
- Nombre del centro pintado directo en PDF (`finanzas.py:1581`) y en un prompt de
  IA (`casos.py:440`), saltándose `_get_config_centro()`.

**Corrección conceptual.**
- Mover el plan de estudio a BD (tabla `planes_estudio` / `plan_materias`),
  siguiendo la filosofía del geo-kit `cliente.json`: catálogo en datos, código
  genérico. `PLAN_ARTES` queda como semilla inicial de un centro, no como fuente.
- Eliminar `MULTIMEDIA` como default: si falta la mención, error explícito o
  selección obligatoria, nunca fallback silencioso. Quitar el default del schema.
- `estudiantes.mencion` pasa a FK de un catálogo de menciones/modalidades; dejar
  de derivar por `split()`.
- Todo uso del nombre del centro pasa por `_get_config_centro()`, incluidos el PDF
  de finanzas y el prompt de casos.
- El parser de boletines del formato Benito Juárez se mantiene como "adaptador de
  importación" configurable, no en el núcleo de `estudiantes.py`.

**Verificación:**
```bash
grep -rn "MULTIMEDIA" routes/ core/ | grep -v curriculo_ | wc -l   # debe bajar drásticamente
grep -rn "Benito" routes/ core/ app.py | grep -v "_get_config_centro\|adaptador\|import"  # solo el adaptador
grep -n "DEFAULT 'MULTIMEDIA'" core/constants.py   # no debe quedar
```

---

## Orden de ejecución recomendado

1. **Fase 0 completa** — arranque, seguridad, `/profesor`, 401/backup. Bajo riesgo,
   desbloquea confianza en el sistema. El Hallazgo 1 ya está corregido en la copia
   de auditoría.
2. **Fase 1** — catálogo de materias (12) + año escolar (11). Migración con backup
   previo de `axula.db`.
3. **Fase 2** — tabla canónica y helpers compartidos (9, 10). Aquí se resuelve el
   pedido central de correspondencia de notas entre vistas.
4. **Fase 3** — motor por competencias y RP (3, 4). Confirmar versión del registro
   con la coordinación antes de empezar.
5. **Fase 4** — UI unificada y multi-centro (5, 6). En paralelo si hay banda.

**Antes de cada fase con migración:** `cp axula.db axula.db.bak-$(date +%F)` y
correr la verificación de arranque limpio del Hallazgo 1.

**Protocolo dev-debug-ia aplicable a cada hallazgo:** Reproducir → Aislar →
Hipótesis → Verificar → Fix. Causa raíz antes del parche. La lección transferible
de esta auditoría: *un import que "funciona" y un boletín que "muestra notas" no
prueban que el sistema sea correcto; solo prueban que la rama feliz corrió una vez
con datos que la disimulan. La correctitud se verifica ejecutando las ramas que
producción nunca toca — BD vacía, alumno irregular, segundo año escolar.*
