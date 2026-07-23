# CLAUDE.md — Fix: asignación de ciclo/grados/materias docentes no se guarda ni muestra 5to

## [ACCIÓN]
Corregir el flujo completo de asignación docente (ciclo, grados, mención, materias, teléfono) en el módulo de gestión de usuarios, eliminando la duplicación de formularios entre `templates/index.html` y `templates/usuarios.html`, y unificando el catálogo de materias con `PLAN_ARTES` como única fuente de verdad.

## [MÓDULO]
Gestión de usuarios (directora/coordinación) + Portal docente.

## [QUÉ]

### Diagnóstico confirmado (root cause, en orden de impacto)

**BUG-1 — Template desactualizado (causa de "no salen materias de 5to").**
`templates/usuarios.html` (ruta `/usuarios`, `routes/config.py:vista_usuarios`) contiene una copia vieja del formulario docente: solo las 6 materias de **4to** de cada mención, sin atributo `data-grado` y sin `onGradoChange()`. La versión correcta y completa (4to/5to/6to con filtrado por grado) vive en `templates/index.html` (~línea 2975+). Las materias de 5to Multimedia (Diseño Web, Diseño Gráfico, Publicidad y Creatividad, Operación de Cámara de Video, Guión, Medios de Comunicación) ya existen en `core/constants.py` → `PLAN_ARTES["MULTIMEDIA"]["5to"]`.

**BUG-2 — Separador inconsistente (causa de "guardo y no se guarda").**
En `usuarios.html`, `guardarUsuario()` serializa grados y menciones con `join(',')` pero `_setChecks()` (usado por `abrirEditar()`) hace `split('|')`. Resultado: con multi-valor (`'4to,5to'`) ningún checkbox se re-marca al reabrir → el usuario percibe que el guardado falló aunque el PATCH sí persistió. Nota: materias usan `join('|')` y sí coinciden; solo grados y menciones están rotos.

**BUG-3 — `telefono` omitido del body.**
En `usuarios.html`, `guardarUsuario()` lee `u-telefono` en una variable pero **no la incluye** en el objeto `body` del PATCH. El backend (`routes/usuarios.py:editar_usuario`, lista `allowed`) sí acepta `telefono`. El teléfono nunca se guarda desde esa página.

**BUG-4 — Validación de email bloquea el PATCH completo.**
`guardarUsuario()` siempre reenvía el `email` cargado. `editar_usuario()` valida con `_validar_email_usuario()` (solo dominios en `DOMINIOS_INSTITUCIONALES`). Si el usuario tiene guardado un correo no institucional (creado por script, seed o versión previa), **todo el guardado devuelve 400** — no solo el campo email.

**BUG-5 — Sesión obsoleta del profesor.**
`routes/auth.py` (login, ~línea 443) guarda `materia/grado/mencion/tipo_docencia` en `session` (no guarda `asignaturas` ni `ciclo`). `core/auth.py:get_usuario()` lee de sesión. Tras la actualización de la directora, el profesor ve datos viejos en todo lo que dependa de `get_usuario()` hasta re-login. (`_get_profesor()` en `core/helpers.py` sí lee de DB — el portal docente principal está bien.)

**BUG-6 (menor) — `index.html:editarUsuario()` no llama `onGradoChange()`** tras marcar los grados, así que al abrir edición el filtrado por grado no se aplica y se muestran materias de todos los grados.

### Fix requerido (mínimo, en orden)

1. **Unificar el formulario docente.** Extraer el bloque completo (tipo docencia + ciclo/grados + mención + materias) de `index.html` a un partial Jinja `templates/partials/_form_docente.html` y su JS compartido a `static/js/form_docente.js`. Incluirlo con `{% include %}` en `index.html` y `usuarios.html`. El partial debe ser la versión de `index.html` (con `data-grado` y `onGradoChange()`).
2. **Generar los checkboxes de materias técnicas dinámicamente desde `PLAN_ARTES`** (server-side en el partial con Jinja iterando `PLAN_ARTES`, o client-side vía el endpoint existente `/api/plan-estudio?grado=X&mencion=Y`). Objetivo: cero listas de materias hardcodeadas en HTML. Excluir del render las materias comunes (Lengua Española, Inglés, Matemática, etc.) que ya están en el bloque de básicas.
3. **Corregir `_setChecks`** para aceptar separador parametrizable o detectar ambos: `valoresStr.split(/[|,]/)`. Grados y menciones deben re-marcarse correctamente con valores multi (`'4to,5to'`).
4. **Añadir `telefono` al body** de `guardarUsuario()` en el JS unificado.
5. **Backend `editar_usuario()` (routes/usuarios.py):** validar email **solo si cambió** — comparar contra el valor actual en DB antes de aplicar `_validar_email_usuario()`. Si el email entrante es idéntico al guardado, omitir validación (grandfathering de correos legacy).
6. **Llamar `onGradoChange()` y `onMencionChange()`** al final de la carga en editar (ambas páginas, vía el JS unificado).
7. **Sesión:** en login, guardar también `asignaturas` y `ciclo` en session; y tras un PATCH exitoso a `/api/usuarios/<uid>`, si `uid == session['user_id']` refrescar los campos de sesión desde DB. Documentar en el toast del guardado: "El docente debe cerrar sesión y volver a entrar para ver los cambios" (solución simple aceptable para v1).

## [ARCHIVOS]
- `templates/usuarios.html` — reemplazar bloque docente por include del partial; eliminar copia vieja de materias y sus funciones JS duplicadas.
- `templates/index.html` — reemplazar bloque docente por el mismo include; mover JS a `static/js/form_docente.js`.
- `templates/partials/_form_docente.html` — **nuevo** (fuente: versión de index.html, materias desde PLAN_ARTES).
- `static/js/form_docente.js` — **nuevo** (onTipoDocencia, onCicloChange, onGradoChange, onMencionChange, _setChecks corregido, _getGrados/_getMenciones/_getMaterias, guardado con telefono).
- `routes/usuarios.py` — `editar_usuario()`: validación de email solo si cambió.
- `routes/auth.py` — login: añadir `asignaturas` y `ciclo` a session.
- `core/auth.py` — `get_usuario()`: exponer `asignaturas` y `ciclo` desde session.
- NO tocar: `core/constants.py` (PLAN_ARTES es la fuente de verdad y está correcta), `routes/profesor.py` (lee de DB, funciona).

## [CRITERIOS]
1. Con mención Multimedia + grados 4to y 5to marcados, el formulario muestra las 6 materias de 4to **y** las 6 de 5to (Diseño Web, Diseño Gráfico, Publicidad y Creatividad, Operación de Cámara de Video, Guión, Medios de Comunicación), filtradas por `data-grado`.
2. Guardar un profesor con `grado='4to,5to'`, mención multimedia y materias de ambos grados → reabrir el modal muestra **exactamente** los mismos chips marcados (grados, mención y materias).
3. El teléfono editado persiste y aparece al reabrir.
4. Un usuario con email legacy no institucional puede ser editado (grados/materias) sin error 400; cambiar el email a uno no institucional sí sigue rechazándose.
5. El mismo formulario (partial + JS) funciona idéntico en `/` (index) y `/usuarios` — verificar ambos.
6. Cero listas de materias técnicas hardcodeadas en HTML: `grep -rn "Diseño Básico y Expresión Visual" templates/` solo debe aparecer en el partial generado desde PLAN_ARTES (o en ninguno si es client-side).
7. Tests existentes siguen pasando; añadir test de `editar_usuario` con email legacy.

## [RESTRICCIONES]
- Fix mínimo por bug; no refactorizar rutas ni el modelo de datos (los campos `grado`, `mencion`, `asignaturas` siguen siendo TEXT con separadores `,` y `|` respectivamente — no cambiar el formato de almacenamiento en esta fase).
- No romper compatibilidad con datos existentes en producción (Render/SQLite): el fix de `_setChecks` debe leer tanto datos viejos como nuevos.
- No modificar `PLAN_ARTES` ni la Ordenanza 04-2023.
- Paleta y estilos de Axula intactos (teal `#038C8C`, navy `#024959`).
- Guard anti-regresión: añadir comentario `<!-- FUENTE ÚNICA: partials/_form_docente.html — NO duplicar este bloque -->` donde estaba cada copia, y opcionalmente un check de CI que falle si `class="chk-mencion"` aparece en más de un template fuera del partial (mismo patrón del CI guard de jaconsultingsrl).
- Commits atómicos: (1) extracción del partial sin cambios funcionales, (2) materias dinámicas desde PLAN_ARTES, (3) fixes de _setChecks + telefono, (4) fix backend email, (5) sesión.

## Lección transferible de la sesión
Cuando un formulario complejo vive copiado en dos templates, los bugs no son simétricos: una copia evoluciona y la otra fosiliza. El síntoma ("no salen las materias de 5to") apuntaba a lógica, pero la causa era arquitectónica — igual que el phantom domain de JA Consulting. Regla: si un bloque UI aparece dos veces, extraer a partial **antes** de corregir el bug dentro de él.
