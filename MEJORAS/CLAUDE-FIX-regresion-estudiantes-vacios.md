# CLAUDE.md — Fix regresión: profesor multi-grado no ve estudiantes de ningún curso

## [ACCIÓN]
Corregir la regresión post-refactor del formulario docente por la cual un profesor de mención (ej. Multimedia, grados 4to+5to) recibe cero estudiantes en el portal docente, blindando el backend contra los dos estados de datos que producen resultado vacío: el sentinel `grado='todos'` y valores de mención que no coinciden con el formato de `estudiantes.curso`.

## [MÓDULO]
Portal docente (`routes/profesor.py`) + resolución de alcance (`core/helpers.py:_resolver_alcance_profesor`) + formulario docente unificado (partial/JS del refactor anterior).

## [QUÉ]

### Diagnóstico (verificado por simulación contra el código actual)
La query de `portal_profesor` y de `mis_estudiantes` filtra:
`grado LIKE '%<g>%' [OR ...] AND curso LIKE '%<mencion>%' [OR ...]`
con `estudiantes.curso = "{grado} {MENCION}"` (ej. `"4to MULTIMEDIA"`, ver `core/excel.py:304`).

Solo dos estados producen 0 filas para un profesor técnica/multimedia:

**R-1. `usuarios.grado = 'todos'`.**
`_getGradosSeleccionados()` (JS) devuelve el sentinel `'todos'` cuando ciclo='ambos' y ningún chip de grado está marcado. Ni `_resolver_alcance_profesor` ni las queries manejan ese sentinel → `grado LIKE '%todos%'` → 0 filas SIEMPRE. Vector post-refactor: si los chips de grado no se re-marcan al abrir el modal de edición (mismatch de value/separador), guardar el perfil sobrescribe `'4to,5to'` con `'todos'`.

**R-2. Mismatch de valor de mención.**
Si el partial regenerado emite checkboxes de mención con `value` distinto al slug original `'multimedia'` (ej. label con emoji `'🎬 Multimedia'`, o clave con formato divergente), el guardado persiste ese valor y `curso LIKE '%🎬 MULTIMEDIA%'` → 0 filas. Los values de mención DEBEN ser substring del formato de `curso` tras `.upper()`: `MULTIMEDIA`, `TEATRO`, `MÚSICA`, `ARTES VISUALES`, `DANZA` (o los slugs originales en minúscula, que LIKE case-insensitive también matchea — EXCEPTO `artes_visuales` con guión bajo, que NO matchea `"ARTES VISUALES"`).

**R-3 (latente, del fix anterior). Split de asignaturas.**
Si `_setChecks` quedó con `split(/[|,]/)` aplicado a asignaturas, fragmenta materias con comas en el nombre ("Lenguaje Visual, Dibujo y Creación de Personajes", "Identidad, Cultura y Emprendimiento"). El separador mixto `[|,]` es válido SOLO para grados y menciones; asignaturas se separan únicamente por `|`.

### Fix requerido

1. **Backend defensivo — `_resolver_alcance_profesor` (core/helpers.py):**
   - Tratar `grado_raw` en {`'todos'`, `''`, `None`} como "sin restricción de grado": si ciclo es primer/segundo usar los grados del ciclo; si ciclo es 'ambos' o vacío, devolver `grados=[]` (sin cláusula de grado en la query) o los 6 grados.
   - Normalizar menciones: mapear con un dict canónico antes de armar el filtro:
     `{'multimedia':'MULTIMEDIA','artes_visuales':'ARTES VISUALES','musica':'MÚSICA','teatro':'TEATRO','danza':'DANZA'}`
     y strip de cualquier carácter no alfabético inicial (emojis). Aplicar `unicodedata` para tolerar MUSICA/MÚSICA en ambos lados si es necesario.
2. **Sanitizar en el guardado — `routes/usuarios.py:editar_usuario` y `crear_usuario`:**
   - Rechazar o normalizar `grado='todos'` → guardar `''` (vacío = sin restricción) y registrar en log.
   - Normalizar `mencion` entrante a los slugs canónicos en minúscula; rechazar valores fuera del catálogo.
3. **Frontend — formulario unificado:**
   - Los `value` de los chips de mención vuelven a los slugs originales: `multimedia`, `artes_visuales`, `musica`, `teatro`, `danza`. El label puede tener emoji; el value NO.
   - `_getGradosSeleccionados()`: eliminar el sentinel `'todos'` — con ciclo='ambos' y 0 chips, devolver `''` (el backend resuelve el alcance).
   - Al abrir edición, verificar en consola/test que los chips de grado se re-marcan con `'4to,5to'` (separador coma) y mención con slug.
   - `_setChecks`: separador por parámetro — `,` para grados/menciones, `|` para asignaturas. Nunca regex mixto en asignaturas.
4. **Reparación de datos en producción (Render/SQLite):** script one-off `scripts/reparar_alcance_docente.py` que:
   - `UPDATE usuarios SET grado='' WHERE grado='todos';`
   - Normalice menciones al slug canónico (strip de emojis/espacios, lower, mapear 'artes visuales'→'artes_visuales').
   - Imprima antes/después de cada fila modificada (dry-run con flag `--apply`).
5. **Log de diagnóstico:** en `portal_profesor` y `mis_estudiantes`, cuando la query devuelva 0 estudiantes, loggear el alcance resuelto y los parámetros SQL (`logger.warning`), para que este fallo nunca vuelva a ser silencioso.

## [ARCHIVOS]
- `core/helpers.py` — `_resolver_alcance_profesor`: sentinel 'todos', normalización de menciones.
- `routes/usuarios.py` — sanitización de `grado` y `mencion` en POST/PATCH.
- `routes/profesor.py` — log de alcance en resultado vacío (portal_profesor + mis_estudiantes).
- Partial/JS del formulario docente (creados en el refactor anterior) — values de mención, `_getGradosSeleccionados`, `_setChecks` por separador.
- `scripts/reparar_alcance_docente.py` — nuevo, con dry-run.
- NO tocar: `core/excel.py` (formato de curso es la referencia), `core/constants.py`.

## [CRITERIOS]
1. Profesor tecnica + mencion multimedia + grado '4to,5to' → portal muestra estudiantes de '4to MULTIMEDIA' y '5to MULTIMEDIA'.
2. Fila con `grado='todos'` (dato legacy) → tras el fix backend, el profesor ve los estudiantes de su ciclo/mención (no cero) incluso ANTES de correr el script de reparación.
3. Mención con emoji o 'ARTES VISUALES'/'artes_visuales' en DB → filtro matchea estudiantes con curso '4to ARTES VISUALES'.
4. Guardar desde el modal con ciclo='ambos' y 0 grados marcados ya no persiste 'todos'.
5. Reabrir el modal tras guardar '4to,5to' + multimedia + materias con comas en el nombre → todos los chips re-marcados exactamente.
6. Test unitario nuevo para `_resolver_alcance_profesor` cubriendo: 'todos', '', slugs con guión bajo, emoji, multi-grado.
7. Query vacía genera warning en logs con alcance y parámetros.

## [RESTRICCIONES]
- Fix mínimo: no cambiar el esquema ni el formato de `estudiantes.curso`.
- El script de reparación corre en dry-run por defecto; `--apply` explícito para escribir. Backup del .db antes de aplicar (Render: descargar copia).
- Compatibilidad hacia atrás: el backend debe leer correctamente TODOS los formatos históricos de mención (slug minúscula, mayúscula, con espacio, con emoji) — la normalización en lectura es la defensa; la sanitización en escritura evita nuevos casos.
- Commits atómicos: (1) backend defensivo + tests, (2) frontend values/sentinel, (3) script de reparación, (4) logging.

## Lección transferible
Un `LIKE '%valor%'` que depende de que dos capas (formulario y datos importados) coincidan en formato es un contrato implícito sin validación. Cuando refactorices el productor (el formulario), el consumidor (la query) falla en silencio con conjunto vacío. Regla: todo valor que viaja de UI a filtro SQL pasa por un catálogo canónico validado en el backend, y el resultado vacío se loggea con sus parámetros — nunca debe ser indistinguible de "no hay datos".
