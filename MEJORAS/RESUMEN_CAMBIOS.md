# Adecuación curricular — resumen de cambios (Axula)

Alcance de esta corrección, según lo acordado: **Multimedia, Artes Visuales, Música y Teatro** (Danza queda intacta por ahora). Se corrigió nomenclatura y se reconectó `core/ia.py` al currículo oficial. No se tocó la interfaz de asignación de materias del profesor (sigue siendo texto libre).

## 1. Qué estaba mal

- `PLAN_ARTES` (en `core/constants.py`) — el catálogo de grado→materia→horas que usa todo el sistema (asignación de profesores, seed de la tabla `materias`, endpoint `/api/plan-estudio`) — tenía nombres **inventados** para Artes Visuales, Música y Teatro (ej. "Lenguaje Plástico y Visual", "Escultura y Cerámica", "Actuación I — Técnicas Básicas"). Ninguno de esos nombres existe en los planes oficiales del MINERD. Multimedia sí estaba correcto.
- `core/curriculo_teatro.py`, `curriculo_musica.py` y `curriculo_artes_visuales.py` (el currículo oficial detallado, usado para dar contexto a la IA) tenían: nombres de materias con errores de tipeo por una mala extracción del PDF original ("Ma quillaje y Vestuario", "Te oría y Entrenamiento Musical"), materias completas faltantes (todo 4to grado de Artes Visuales, dos materias de 6to de Teatro, "Instrumento III - Guitarra" en Música), y —el hallazgo más serio— **contenido de una materia mezclado dentro de otra** (ej. "Actuación para Cine" tenía el elemento de competencia real de "Maquillaje y Vestuario"; "Videoarte" tenía el de "Animación"). Esto se verificó y corrigió línea por línea contra los 4 PDFs oficiales que enviaste.
- `core/ia.py` generaba las planificaciones de clase, rúbricas y estrategias usando un diccionario (`CURRICULUM_ARTES`, en `constants.py`) cuyas claves casi nunca coincidían con los nombres reales de materias — así que la IA casi siempre trabajaba **sin contexto curricular oficial**, sin importar la mención.

## 2. Qué se corrigió

| Archivo | Cambio |
|---|---|
| `core/curriculo_teatro.py` | Reescrito completo: 16 → 18 materias, 10 nombres corregidos, 7 contaminaciones de contenido corregidas (2 más de las detectadas inicialmente). |
| `core/curriculo_musica.py` | Reescrito completo: 31 → 32 materias, se eliminó el nivel "Instrumento IV" (no existe oficialmente, era una inconsistencia del propio PDF), se agregó una función que combina las 4 especializaciones de instrumento cuando se pide el nombre genérico ("Instrumento I/II/III"), 6 contaminaciones corregidas. |
| `core/curriculo_artes_visuales.py` | Reescrito completo: 11 → 20 materias (faltaba *todo* 4to grado + "Grabado" de 5to), 4 contaminaciones de contenido corregidas. |
| `core/curriculo_multimedia.py` | 16 → 19 materias (se agregaron Diseño Gráfico, Publicidad y Creatividad, Producción de Proyecto Emprendedor), se corrigieron las horas de "Medios de Comunicación" y "Redes Sociales", 9 contaminaciones de contenido corregidas. |
| `core/constants.py` | `PLAN_ARTES["ARTES VISUALES"]`, `["MÚSICA"]` y `["TEATRO"]` reemplazados con los nombres, grados y horas oficiales (verificados: cada grado suma exactamente 40h). `["MULTIMEDIA"]` y `["DANZA"]` no se tocaron. |
| `core/ia.py` | Ahora importa `get_asignatura`/`formatear_contexto` de `core/curriculo.py` (el dispatcher que ya existía pero no se usaba) en vez de los diccionarios rotos. Las 3 funciones de generación de prompts (planificación, rúbrica, estrategia) quedan conectadas al currículo oficial real de las 4 menciones. |

Verificación final: las 80 materias específicas de las 4 menciones en `PLAN_ARTES` ahora encuentran contenido real en el currículo oficial (0 fallos de búsqueda), y los tres generadores de prompts de `ia.py` se probaron con una materia de cada mención.

## 3. Importante: qué NO se tocó (fuera de este alcance)

- **Danza**: sin cambios, como acordamos (no había PDF oficial disponible).
- **La forma en que el profesor se asigna una materia** (campo de texto libre con el buscador aproximado en `profesor.py`/`helpers.py`) no se modificó. Con los nombres ya corregidos debería fallar mucho menos, pero sigue siendo texto libre, no un selector.
- Encontré un tercer diccionario, independiente de todo lo anterior, en `core/helpers.py` (función `_construir_prompt_asignacion`, línea ~2651): solo tiene 10 materias de Multimedia y ignora la mención del profesor. No aparece usado por ninguna ruta en los archivos que me compartiste, así que no lo toqué, pero si en algún momento genera "documentos de asignación" para Teatro/Música/Artes Visuales, va a devolver vacío — vale la pena revisarlo si tienes esa función activa en producción.
- `core/constants.py` tiene un bloque de ~1100 líneas duplicado byte por byte (`CURRICULUM_ARTES`, `CLUSTER_META`, `DB_TABLAS_META`, `DEFAULTS_CENTRO` definidos dos veces). No afecta el funcionamiento porque es contenido idéntico, pero es basura de mantenimiento — puedo limpiarlo en otra pasada si quieres.

## 4. Antes de subir esto a producción

**Migración de base de datos**: `PLAN_ARTES` alimenta la tabla `materias` (ver H13 en `core/database.py`) de forma aditiva — al reiniciar la app con estos archivos, los nombres nuevos se agregan al catálogo, pero **los nombres viejos (inventados) que ya estén en `materias_calificaciones`, `asistencia` o en el perfil de un profesor (`usuarios.materia`/`asignaturas`) no se renombran solos**. Si ya tienes profesores asignados con los nombres viejos (ej. "Escultura y Cerámica"), habrá que reasignarlos manualmente a los nombres oficiales nuevos (ej. "Diseño Bi y Tridimensional" o el que corresponda) para que el emparejamiento siga funcionando. Si quieres, te ayudo a armar un script de migración que mapee automáticamente los nombres viejos a los nuevos usando el histórico de `PLAN_ARTES`.

**Cómo instalar**: reemplaza los 6 archivos adjuntos en `core/` por los tuyos actuales (mismos nombres). No requieren cambios en ningún otro archivo del proyecto.
