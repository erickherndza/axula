# Sistema de Notas y Promociones — Axula
## Brief técnico: motor de reglas MINERD + capa de explicación con Groq

---

## 1. Principio de diseño

**La IA (Groq) nunca decide una promoción.** La decisión sale de un motor de reglas determinístico, versionado por ordenanza, escrito en Python puro (sin LLM). Groq entra **después**, solo para explicar, redactar y señalar casos límite para revisión humana.

Esto es clave para auditoría frente a MINERD y padres: si alguien cuestiona una decisión, existe un cálculo reproducible y trazable, separado de cualquier generación de texto.

---

## 2. Fuente normativa

⚠️ **CORRECCIÓN:** La norma vigente para Inicial, Primario y Secundario **no es la Ordenanza 1'96/1'98** — quedó sustituida en estos aspectos por la **Ordenanza 04-2023** ("Sistema de Evaluación de los Aprendizajes en correspondencia con el currículo vigente de los niveles Inicial, Primario y Secundario"), vigente **a partir del año escolar 2023-2024**. Fuente: Dirección de Educación Primaria, `ministeriodeeducacion.gob.do`.

La Ordenanza 04-2023 unifica el mínimo aprobatorio en **70 puntos** (escala 0-100) tanto para Primario como para Secundario — no 65 como establecía la vieja 1'96 para Nivel Básico. Este documento usa la 04-2023 como fuente principal para los umbrales numéricos. La 1'96/1'98 se referencia solo donde aporta contexto estructural (Educación de Adultos, Técnico-Profesional, Educación Especial), ya que no confirmé si esos regímenes específicos también fueron actualizados por ordenanzas posteriores (existe además una Ordenanza 04-2024 para secundaria de adultos que no llegué a verificar en detalle).

⚠️ **Antes de producción — vacío pendiente:** no logré confirmar con fuentes públicas accesibles el número exacto de asignaturas reprobadas que activa "promoción condicional" vs. "repite grado" bajo la 04-2023 (el PDF oficial es un escaneo sin texto extraíble). Esto **hay que confirmarlo directamente con la dirección de C.E. Benito Juárez** o con el texto impreso de la ordenanza antes de codificar el motor de reglas — no asumir que se mantienen los umbrales de "2 asignaturas = promovido con pendientes / 4 = repite" de la 1'96, aunque es probable que la lógica general se conserve.

---

## 3. Criterios de promoción por nivel

### 3.1 Nivel Primario (antes "Nivel Básico") — según Ordenanza 04-2023

| Regla | Condición | Resultado |
|---|---|---|
| Promoción directa | Calificación ≥ **70 pts** en todas las áreas/competencias + asistencia ≥ 80% | `promovido` |
| Recuperación pedagógica | Calificación < 70 pts en una o más áreas | activa proceso de recuperación (actividades complementarias/tutorías) |
| Repite por inasistencia | Inasistencia por debajo del 80% requerido, sin causa justificada | `reprobado` (independiente de notas) |
| Repite grado (NEAE) | Estudiante con Necesidades Específicas de Apoyo Educativo que no avanza pese a ajustes, según determinación de equipo multidisciplinario | puede repetir **solo un grado por ciclo educativo** (Art. 17) — nunca puede ser excluido del centro por repitencia |

- El umbral de 70 puntos y el 80% de asistencia mínima están confirmados por la Ordenanza 04-2023.
- **Pendiente de confirmar:** el número exacto de asignaturas reprobadas que distingue "promoción condicional" de "repite el grado" bajo la 04-2023 (ver nota de la sección 2). La 1'96 usaba 2 vs. 4 asignaturas — probable que la lógica se conserve, pero no verificado.
- 8vo grado / fin de ciclo (Pruebas Nacionales): bajo la Ordenanza 1-2016, la nota de presentación del centro pesa 70% y la prueba nacional 30%. Nota final mínima para aprobar: 70 puntos.

### 3.2 Nivel Secundario / Nivel Medio, Modalidad Académica

⚠️ La tabla siguiente combina el umbral confirmado por la 04-2023 (70 pts, ya vigente en la 1'96 para Medio) con la estructura procedimental de la 1'96/1'98 (pruebas completivas, extraordinarias, número de asignaturas pendientes). Esta parte estructural **no la vi actualizada explícitamente** en las fuentes que revisé — vale la pena confirmarla igual antes de codificar.

**Referencia histórica (Art. 56–69, Ordenanza 1'96/1'98):**

| Regla | Condición | Resultado |
|---|---|---|
| Aprobación de asignatura | Calificación fin de semestre ≥ 70 pts (70% parciales + 30% prueba fin de semestre) | `aprobada` |
| Pruebas completivas | Nota fin de semestre entre 0–69 pts → completivas (50% completiva + 50% promedio parciales) | según resultado |
| Repite asignatura | Inasistencia > 20% sin causa justificada en el semestre | `reprobada` (por inasistencia) |
| Promoción directa | Aprobó **todas** las asignaturas/áreas del grado | `promovido` |
| Promoción con pendientes | Reprobó **hasta 2** asignaturas/áreas (1er o 2do semestre) | `promovido` con asignaturas pendientes — debe aprobarlas antes de terminar el grado siguiente |
| Repite grado | Reprobó **4 o más** asignaturas/áreas del grado | `reprobado` |
| Repite (post-extraordinarias) | Tras pruebas extraordinarias reprueba 3 o más (incluyendo por inasistencia) | `reprobado` |

- Escala literal: A=90-100 (Excelente), B=80-89 (Muy Bueno), C=70-79 (Bueno), D=0-69 (Deficiente) (Art. 59).
- Pruebas extraordinarias: 70% la prueba + 30% promedio de parciales del semestre, mínimo 70 pts (Art. 66).
- Bachillerato: requiere aprobar todas las asignaturas + Pruebas Nacionales (30%) + Servicio Social Estudiantil (Art. 71).

### 3.3 Modalidad Técnico-Profesional (Art. 77, 81–85)

- Asignatura práctica: suma de tareas ≥ 65 → aprobada; 40–64 → promovido condicional; < 40 → reprobada.
- Promoción de semestre: reprueba hasta 3 asignaturas → promovido condicional (con recuperación, mínimo 70 pts para validar).
- Reprueba 4+ → repite semestre.

### 3.4 Educación de Adultos (Art. 102–106)

- Promoción por ciclo: calificación fin de ciclo ≥ 65 pts en las tres áreas.
- Promoción condicional: reprueba hasta 3 asignaturas → recuperación (tutoría 3h/semana × 3 semanas) + prueba completiva (50%) + nota previa (50%).
- Reprueba 4+ → repite semestre del ciclo.

### 3.5 Educación Especial / Perfiles inclusivos (Art. 110–117, + Ordenanza 05-2024)

La Ordenanza 1'96 establece que estudiantes con necesidades educativas especiales integrados al aula regular se evalúan con los **mismos criterios** del nivel/grado (Art. 117), pero el Art. 112 contempla diversificación curricular (aula diferencial, programa en el hogar, taller laboral protegido) cuando no es posible la integración total.

Para los perfiles TDAH/TEA que ya tienes scopeados bajo el marco DUA/UDL y la Ordenanza 05-2024, esto significa: **el motor de reglas no debe aplicar el criterio estándar ciegamente** — debe verificar primero si el estudiante tiene un Plan de Adaptación Curricular activo, y si lo tiene, aplicar los criterios diferenciados definidos en ese plan en vez del umbral genérico de 65/70 puntos.

---

## 4. Modelo de datos propuesto

```
criterios_promocion
├── id
├── ordenanza (ej: "04-2023", "1'96", "1'98", "05-2024") — SIEMPRE versionar, la norma cambia
├── nivel (inicial | primario | secundario_academico | secundario_tecnico | adultos | especial)
├── grado
├── nota_minima_area (int)
├── max_areas_reprobadas_aplazado (int)
├── max_areas_reprobadas_reprueba (int)
├── asistencia_minima_pct (int)
├── vigente_desde / vigente_hasta

estudiante_perfil_inclusivo
├── estudiante_id
├── perfil (tdah | tea | otro)
├── plan_adaptacion_id (FK)
├── criterios_diferenciados_json

promocion_resultado
├── id
├── estudiante_id
├── periodo (año escolar)
├── nivel / grado
├── resultado_regla (promovido | aplazado | reprobado | promovido_condicional)
├── areas_reprobadas (json)
├── asistencia_pct
├── requiere_revision_humana (bool)
├── explicacion_ia (texto generado por Groq)
├── revisado_por (docente_id, nullable)
├── fecha_calculo
├── fecha_decision_final
```

---

## 5. Flujo del proceso

```
1. Notas + asistencia del período (blueprint `evaluaciones`, ya existente)
        ↓
2. Motor de reglas (Python puro, según tabla criterios_promocion)
   → ¿tiene plan_adaptacion activo? usa criterios diferenciados
   → si no, usa criterios estándar del nivel/grado
        ↓
3. Resultado preliminar: promovido / aplazado / reprobado / condicional
        ↓
4. ¿Caso límite? (ej. 63-67 pts, perfil inclusivo, contradicción nota-observación docente)
        ↓ sí                              ↓ no
   Cola de revisión                  continúa directo
   (comité docente)                        ↓
        ↓                                  ↓
5. Groq API: genera explicación en lenguaje natural (boletín narrativo)
   Input: resultado + notas + observaciones cualitativas del profesor
   Output: texto explicativo, NUNCA el resultado en sí
        ↓
6. Notificación a padres / registro en Axula
```

---

## 6. Casos de uso concretos para Groq

1. **Boletín narrativo para padres** — traduce el resultado ya calculado a lenguaje claro, citando el artículo/criterio aplicado.
2. **Clasificación de observaciones docentes** — texto libre del profesor → etiquetas (progreso, conducta, necesidad de apoyo) para detectar contradicciones con la nota numérica.
3. **Resumen para comité de revisión** — cuando un caso queda en zona gris, genera un resumen de contexto (historial, adaptaciones aplicadas, observaciones) para la reunión del comité.
4. **Redacción de aplicación de adaptaciones DUA/UDL** — describe cómo se aplicaron las adaptaciones curriculares y si se cumplieron los criterios diferenciados, en vez de aplicar el umbral estándar.

**Regla de prompt:** el prompt a Groq siempre incluye el resultado del motor de reglas como dato fijo ("el sistema determinó: en recuperación pedagógica en Matemática, promedio 62/100, mínimo requerido 70"). Se le pide **redactar**, nunca **decidir**. Modelo sugerido: Llama 3.1 8B o 70B vía Groq — suficiente para generación de texto explicativo, con la ventaja de baja latencia para procesar boletines de un curso completo en lote.

---

## 7. Próximos pasos sugeridos

- [ ] **Prioridad alta:** confirmar con dirección de C.E. Benito Juárez el umbral exacto de asignaturas reprobadas para "promoción condicional" vs. "repite grado" bajo la Ordenanza 04-2023 (no confirmado en este brief).
- [ ] Confirmar si existe una Ordenanza 04-2024 aplicable a Secundaria de Adultos que también deba incorporarse.
- [ ] Definir el rango exacto de "caso límite" para activar revisión humana (ej. ±3 puntos del umbral de 70).
- [ ] Diseñar el schema de `plan_adaptacion_id` en conjunto con el módulo inclusivo TDAH/TEA ya scopeado.
- [ ] Prompt engineering para la capa Groq: definir tono, longitud del boletín, y bloqueo estricto para que nunca emita un veredicto de promoción por su cuenta.
- [ ] Nuevo blueprint `promociones/` separado de `evaluaciones/`.
