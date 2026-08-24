# Mandato para Claude Code — Sección "Coherencia Horizontal" en Aula

Prompt listo para pegar en Claude Code. Instruye la creación de una sección/módulo llamado **Coherencia Horizontal** dentro de una plataforma de aula (LMS / gestión de clase), basada en la investigación curricular del MINERD (4to y 5to de Secundaria, Modalidad en Artes).

---

## Prompt

```
Quiero que crees una sección llamada "Coherencia Horizontal" dentro de la aplicación de Aula.

CONTEXTO
La "Coherencia Horizontal" es un principio de planeamiento curricular del MINERD
(República Dominicana): exige que todas las asignaturas que un/a estudiante cursa
en un mismo grado estén alineadas entre sí (objetivos, contenidos, indicadores de
logro), en lugar de funcionar de forma aislada. Se distingue de la "Coherencia
Vertical" (progresión de una misma asignatura a través de los grados).

Esta sección está pensada para 4to y 5to de Secundaria, Modalidad en Artes,
donde un/a estudiante cursa un Componente Académico (Lengua Española, Lenguas
Extranjeras, Matemática, Ciencias Sociales, Ciencias de la Naturaleza, Educación
Física, Formación Integral Humana y Religiosa) y un Componente Artístico según su
mención (Artes Aplicadas, Artes Escénicas —Danza/Teatro—, Artes Visuales, Música).

Antes de escribir código: explora la estructura del proyecto actual (framework,
convenciones de carpetas, componentes existentes, capa de datos) y sigue esos
mismos patrones. No asumas un stack si el repo ya define uno.

OBJETIVO
Crear una sección de "Coherencia Horizontal" donde un/a docente pueda planificar
un período (unidad, bimestre o trimestre) para una sección/aula, registrando
cómo se articulan entre sí las asignaturas de ese grado.

DATOS DE LA SECCIÓN (encabezado del formulario)
- Centro educativo
- Grado (4to / 5to) y sección (texto libre)
- Mención de la Modalidad en Artes (Artes Aplicadas, Danza, Teatro, Artes
  Visuales, Música)
- Período de planificación (texto libre o rango de fechas)

MATRIZ DE COHERENCIA HORIZONTAL (cuerpo del formulario)
Tabla editable, con filas añadibles/eliminables por el usuario. Columnas:
1. Área / Asignatura (texto o selector con las asignaturas listadas arriba)
2. Competencia(s) Fundamental(es) (texto largo)
3. Contenido / Unidad del período (texto largo)
4. Indicador de logro (texto largo)
5. Punto de articulación horizontal — con qué otra(s) asignatura(s) de la misma
   fila se conecta y cómo (texto largo)

REQUISITOS FUNCIONALES
- Crear, editar, guardar y eliminar una matriz de Coherencia Horizontal por
  sección/aula y período.
- Listar las matrices ya creadas (por centro, grado, sección, período).
- Exportar una matriz a PDF o imprimible, conservando el formato de tabla.
- Validar que cada fila tenga al menos el Área/Asignatura y el Contenido
  antes de guardar.
- (Opcional, si el proyecto ya maneja autenticación/roles) Restringir la
  creación/edición a usuarios con rol docente o coordinador académico.

CRITERIOS DE ACEPTACIÓN
- Puedo crear una nueva matriz, llenar el encabezado y añadir varias filas.
- Puedo guardar la matriz y volver a abrirla con los mismos datos.
- Puedo exportar/imprimir la matriz y se ve como una tabla legible.
- El formulario impide guardar una fila vacía.
- El código sigue las convenciones ya existentes en el repo (nombres,
  estructura de carpetas, estilo de componentes, capa de datos).

Al terminar, muéstrame qué archivos creaste o modificaste y cómo probar la
sección manualmente.
```

---

## Notas de uso

- Este prompt es un punto de partida: ajusta la sección **CONTEXTO** si tu app de Aula ya tiene su propio modelo de datos para asignaturas, secciones o períodos, para que Claude Code lo reutilice en vez de crear uno nuevo.
- Si tu proyecto ya tiene un stack definido (por ejemplo, Next.js + Postgres, o Django), puedes añadir esa línea explícitamente en CONTEXTO para ahorrarle a Claude Code el paso de exploración.
- La estructura de columnas de la matriz es la misma que se propuso en la investigación curricular (documento Word entregado antes), para que ambos artefactos queden consistentes.
