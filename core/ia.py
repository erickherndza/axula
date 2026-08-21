# -*- coding: utf-8 -*-
"""Cliente Groq y constructores de prompts de IA."""

import os
import re
import logging
from .constants import CURRICULUM_ARTES, CURRICULUM_MULTIMEDIA, PLAN_ARTES, PLAN_MULTIMEDIA

logger = logging.getLogger("axula")

# ── Sanitización anti-prompt-injection ──────────────────────────────────────
_INJECTION_PATTERNS = re.compile(
    r"(ignore\s+(all\s+)?previous\s+instructions?|"
    r"disregard\s+(all\s+)?previous|"
    r"forget\s+(all\s+)?previous|"
    r"you\s+are\s+now|"
    r"act\s+as\s+if|"
    r"pretend\s+you\s+are|"
    r"system\s+prompt|"
    r"</?(system|user|assistant)>|"
    r"\[INST\]|\[/INST\]|"
    r"<<SYS>>|<</SYS>>)",
    re.IGNORECASE,
)

def _sanitizar_campo(valor, max_len=200):
    """
    Elimina patrones de prompt-injection y trunca al máximo permitido.
    Úsalo en todos los campos de usuario antes de insertarlos en un prompt.
    """
    if valor is None:
        return ""
    s = str(valor).strip()
    s = _INJECTION_PATTERNS.sub("[OMITIDO]", s)
    return s[:max_len]

groq_client = None  # Se inicializa en la primera llamada a la IA

def _get_groq_client():
    """Lazy Groq client — solo se importa cuando se llama la IA."""
    from groq import Groq
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY no configurado. Agrégalo en el archivo .env y reinicia el servidor."
        )
    # max_retries=0: el SDK reintenta con time.sleep() bloqueante por defecto.
    # En un worker sync de gunicorn eso puede exceder el --timeout del proceso
    # y lo mata (WORKER TIMEOUT) devolviendo una respuesta vacía al cliente.
    # Preferimos que la excepción suba de inmediato y la maneje la ruta.
    return Groq(api_key=api_key, timeout=30.0, max_retries=0)


def _get_anthropic_client():
    """Lazy Claude client — límites de tokens/minuto muy por encima de Groq
    free tier, así que aquí sí se puede dejar el retry por defecto del SDK."""
    from anthropic import Anthropic
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY no configurado. Agrégalo en el archivo .env y reinicia el servidor."
        )
    return Anthropic(api_key=api_key)


def construir_prompt(e):
    """
    Construye el prompt pedagógico para el LLM, adaptado por mención.
    Soporta: Multimedia, Música, Teatro, Artes Visuales y genérico.
    """
    # Sanitizar campos de texto libre
    curso     = _sanitizar_campo(e.get('curso', '4to'))
    categoria = _sanitizar_campo(e.get('categoria', 'Estable'))
    tendencia = _sanitizar_campo(e.get('tendencia', 'igual'))

    # Detectar mención normalizada
    mencion_raw = str(e.get('mencion') or '').upper().strip()
    if 'MUSIC' in mencion_raw or 'MÚSICA' in mencion_raw:
        mencion_label = 'Música'
    elif 'TEATRO' in mencion_raw:
        mencion_label = 'Teatro'
    elif 'VISUAL' in mencion_raw or 'ARTES VISUALES' in mencion_raw:
        mencion_label = 'Artes Visuales'
    elif 'MULTIMEDIA' in mencion_raw or 'MULTI' in mencion_raw:
        mencion_label = 'Multimedia'
    else:
        mencion_label = mencion_raw or 'Artes'

    def _pct(v):
        try: return f"{float(v):.1f}"
        except: return "0"

    # ── Construir sección de módulos técnicos según mención ──
    modulos = []

    plan_accion_hint = ""

    if mencion_label == 'Multimedia':
        if e.get('p_foto'):   modulos.append(f"Fotografía: {_pct(e['p_foto'])}%")
        if e.get('p_lv'):     modulos.append(f"Lenguaje Visual: {_pct(e['p_lv'])}%")
        if e.get('p_diseno'): modulos.append(f"Diseño: {_pct(e['p_diseno'])}%")
        plan_accion_hint = "los módulos de Fotografía, Lenguaje Visual y Diseño"

    elif mencion_label == 'Música':
        if e.get('p_instrumento'):      modulos.append(f"Instrumento: {_pct(e['p_instrumento'])}%")
        if e.get('p_canto'):            modulos.append(f"Canto Coral: {_pct(e['p_canto'])}%")
        if e.get('p_lenguaje_musical'): modulos.append(f"Lenguaje Musical: {_pct(e['p_lenguaje_musical'])}%")
        plan_accion_hint = "los módulos de Instrumento, Canto Coral y Lenguaje Musical"

    elif mencion_label == 'Teatro':
        if e.get('p_entrenamiento'):   modulos.append(f"Entrenamiento Vocal/Corporal: {_pct(e['p_entrenamiento'])}%")
        if e.get('p_expresion'):       modulos.append(f"Expresión y Lenguaje Teatral: {_pct(e['p_expresion'])}%")
        if e.get('p_historia_teatro'): modulos.append(f"Historia del Teatro: {_pct(e['p_historia_teatro'])}%")
        plan_accion_hint = "los módulos de Entrenamiento, Expresión Teatral e Historia del Teatro"

    elif mencion_label == 'Artes Visuales':
        if e.get('p_dibujo'):       modulos.append(f"Dibujo: {_pct(e['p_dibujo'])}%")
        if e.get('p_pintura'):      modulos.append(f"Pintura: {_pct(e['p_pintura'])}%")
        if e.get('p_historia_arte'):modulos.append(f"Historia del Arte: {_pct(e['p_historia_arte'])}%")
        plan_accion_hint = "los módulos de Dibujo, Pintura e Historia del Arte"

    # Para TODOS: fallback a materias_extras si las columnas específicas están vacías
    if not modulos and e.get('materias_extras'):
        for nombre, datos in e['materias_extras'].items():
            prom = datos.get('promedio')
            if prom and float(prom) > 0:
                modulos.append(f"{nombre.title()}: {_pct(prom)}%")
        if not plan_accion_hint:
            plan_accion_hint = f"las asignaturas técnicas de la mención {mencion_label}"

    # Último fallback genérico
    if not plan_accion_hint:
        plan_accion_hint = f"las asignaturas técnicas de la mención {mencion_label}"

    modulos_txt = ", ".join(modulos) if modulos else "No registrados aún"

    silencioso_txt = (
        "SÍ — Rendimiento alto con autoestima crítica (Caso Silencioso)"
        if e.get('silencioso') else "No"
    )

    return f"""Eres un orientador pedagógico experto en educación artística en República Dominicana,
especializado en la Modalidad de Artes del bachillerato dominicano, mención {mencion_label}.

Analiza el siguiente perfil y genera un plan pedagógico estructurado.

═══════════════════════════════════════
DATOS DEL ESTUDIANTE
═══════════════════════════════════════
Curso: {curso}
Mención: {mencion_label}
Estado actual: {categoria}
Tendencia académica: {tendencia}

MÉTRICAS PRINCIPALES:
- Promedio Académico General: {e.get('p_acad', 0)}%
- Promedio Conductual: {e.get('p_cond', 0) or 'No registrado'}%
- Promedio Emocional: {e.get('p_emocional', 0) or 'No registrado'}%
- Índice de Autoestima: {e.get('p_auto', 0) or 'No registrado'}%
- Motivación: {e.get('motivacion', 0) or 'No registrado'}%
- Asistencia: {e.get('asistencia', 0) or 'No registrado'}%
- Proyección cierre de año (IA): {e.get('proyeccion', 0)}%

MÓDULOS TÉCNICOS — {mencion_label.upper()}:
{modulos_txt}
Promedio módulos técnicos: {e.get('prom_modulos', 0)}%

Índice de Riesgo: {e.get('indice_riesgo', 0)} — Nivel: {e.get('nivel_riesgo', 'N/D')}

¿Es Caso Silencioso?: {silencioso_txt}
═══════════════════════════════════════

Genera una respuesta con exactamente estas 4 secciones:

1. DIAGNÓSTICO (2-3 oraciones): Análisis del perfil académico, técnico y emocional actual en el contexto de la mención {mencion_label}.

2. FORTALEZAS (2-3 puntos): Aspectos positivos identificados en el perfil.

3. PLAN DE ACCIÓN (3-4 acciones concretas): Estrategias pedagógicas específicas para
   la Modalidad de Artes, mención {mencion_label}, mencionando {plan_accion_hint} donde aplique.

4. SEGUIMIENTO (1-2 oraciones): Cuándo y cómo verificar el progreso.

Usa lenguaje profesional pero accesible para un docente de bachillerato.
Sé específico con la mención {mencion_label}. Máximo 300 palabras."""


# ── RUTAS ───────────────────────────────────────────────────────────────────


def construir_prompt_planificacion(materia, grado, tema, duracion_clases, nivel_grupo, mencion="MULTIMEDIA"):
    """Genera un prompt para planificación de clase basado en el currículo MINERD."""
    # Buscar en CURRICULUM_ARTES primero, luego fallback a CURRICULUM_MULTIMEDIA
    curr = CURRICULUM_ARTES.get(materia, CURRICULUM_MULTIMEDIA.get(materia, {}))
    mencion_real = curr.get("mencion", mencion)

    saberes_c = "\n".join([f"  • {s}" for s in curr.get("saberes_conceptuales", [])[:6]])
    saberes_p = "\n".join([f"  • {s}" for s in curr.get("saberes_procedimentales", [])[:4]])
    indicadores = "\n".join([f"  • {s}" for s in curr.get("indicadores_logro", [])[:5]])

    return f"""Eres un experto en planificación curricular para la Modalidad de Artes, mención {mencion_real} del bachillerato dominicano (MINERD).

Genera una planificación de clases completa y detallada basada en el currículo oficial.

═══════════════════════════════════════
DATOS DE LA PLANIFICACIÓN
═══════════════════════════════════════
Asignatura: {materia.replace('_', ' ')}
Competencia oficial: {curr.get('competencia', '')}
Grado: {grado}
Tema específico a trabajar: {tema}
Duración: {duracion_clases} clases de 45 minutos
Nivel del grupo: {nivel_grupo}

SABERES CONCEPTUALES DEL CURRÍCULO OFICIAL:
{saberes_c}

SABERES PROCEDIMENTALES:
{saberes_p}

INDICADORES DE LOGRO OFICIALES:
{indicadores}

Evidencia de desempeño esperada: {curr.get('evidencias', '')}
═══════════════════════════════════════

Genera la planificación con estas secciones exactas:

1. COMPETENCIAS A DESARROLLAR
Menciona las competencias fundamentales y específicas del MINERD que aplican.

2. OBJETIVO DE APRENDIZAJE
Una oración clara y medible usando verbos de acción.

3. MOTIVACIÓN INICIAL (10 min)
Actividad creativa y atractiva para activar saberes previos.

4. DESARROLLO DE LA CLASE
Describe {duracion_clases} momentos de clase con:
- Actividad principal
- Recursos necesarios (materiales, tecnología disponible en RD)
- Tiempo estimado
- Rol del docente y del estudiante

5. ACTIVIDAD PRÁCTICA
Proyecto concreto alineado a la evidencia de desempeño oficial.

6. EVALUACIÓN
- Técnica de evaluación (según el MINERD)
- Criterios observables
- Instrumento sugerido (rúbrica, portafolio, lista de cotejo)

7. RECURSOS Y MATERIALES
Lista de recursos accesibles en centros educativos dominicanos.

8. INTEGRACIÓN CON OTRAS ASIGNATURAS
Cómo conectar este tema con las otras materias de la mención {mencion_real}.

Usa un lenguaje práctico, motivador y accesible para docentes de bachillerato dominicano.
Máximo 600 palabras."""


def construir_prompt_rubrica(materia, indicador, nivel, mencion="MULTIMEDIA"):
    """Genera un prompt para crear una rúbrica de evaluación oficial."""
    curr = CURRICULUM_ARTES.get(materia, CURRICULUM_MULTIMEDIA.get(materia, {}))
    mencion_real = curr.get("mencion", mencion)
    todos_indicadores = curr.get("indicadores_logro", [])

    return f"""Eres un experto en evaluación educativa para la Modalidad de Artes Multimedia del MINERD de República Dominicana.

Crea una rúbrica de evaluación completa y lista para usar en el aula.

═══════════════════════════════════════
DATOS DE LA RÚBRICA
═══════════════════════════════════════
Asignatura: {materia.replace('_', ' ')}
Competencia: {curr.get('competencia', '')}
Indicador de logro a evaluar: {indicador}
Grado: {nivel}
Evidencia de desempeño: {curr.get('evidencias', '')}

TODOS LOS INDICADORES DE ESTA ASIGNATURA:
{chr(10).join([f'• {i}' for i in todos_indicadores])}
═══════════════════════════════════════

Genera una rúbrica con EXACTAMENTE este formato:

RÚBRICA DE EVALUACIÓN
Asignatura: {materia.replace('_', ' ')} | Indicador: {indicador}

TABLA DE CRITERIOS (4 niveles: Excelente/Bueno/En desarrollo/Inicio):
Crea entre 4 y 5 criterios de evaluación observables, con descripción para cada nivel.
Asigna un peso porcentual a cada criterio que sume 100%.

ESCALA DE CALIFICACIÓN:
Excelente (90-100): descripción
Bueno (75-89): descripción
En desarrollo (60-74): descripción
Inicio (0-59): descripción

INDICACIONES PARA EL DOCENTE:
Máximo 3 recomendaciones prácticas para aplicar esta rúbrica.

Usa lenguaje claro, criterios observables y medibles.
Máximo 400 palabras."""


def construir_prompt_estrategia(materia, problema, perfil_grupo, mencion="MULTIMEDIA"):
    """Genera estrategias didácticas para superar dificultades específicas."""
    curr = CURRICULUM_ARTES.get(materia, CURRICULUM_MULTIMEDIA.get(materia, {}))
    mencion_real = curr.get("mencion", mencion)

    return f"""Eres un orientador pedagógico especializado en la Modalidad de Artes Multimedia del bachillerato dominicano.

Un docente necesita estrategias didácticas para superar una dificultad específica en el aula.

═══════════════════════════════════════
SITUACIÓN
═══════════════════════════════════════
Asignatura: {materia.replace('_', ' ')}
Competencia: {curr.get('competencia', '')}
Dificultad o problema identificado: {problema}
Perfil del grupo: {perfil_grupo}
═══════════════════════════════════════

Genera una respuesta con estas 3 secciones:

1. DIAGNÓSTICO DE LA DIFICULTAD
Analiza por qué puede estar ocurriendo este problema en el contexto de la Modalidad de Artes dominicana.

2. ESTRATEGIAS DIDÁCTICAS (3 estrategias concretas)
Para cada estrategia indica:
- Nombre de la estrategia
- Cómo implementarla paso a paso
- Materiales necesarios (accesibles en RD)
- Tiempo estimado

3. SEGUIMIENTO Y VERIFICACIÓN
Cómo saber si la estrategia funcionó, con indicadores observables.

Sé específico y práctico para el contexto dominicano. Máximo 400 palabras."""


# ── PLANIFICACIÓN SECUENCIAL (Materias Básicas) ──────────────────────────────

def construir_prompt_secuencial(area_nombre, grado, periodo, numero_unidad, titulo, semanas):
    """
    Prompt ampliado para generar una unidad de Secuencia Didáctica MINERD completa.
    Incluye Situación de Aprendizaje, Preguntas Generadoras, Competencias Específicas,
    actividades con INICIO/DESARROLLO/CIERRE por semana, rúbricas e bibliografía.
    """
    area_s   = _sanitizar_campo(area_nombre, 80)
    grado_s  = _sanitizar_campo(grado, 20)
    titulo_s = _sanitizar_campo(titulo, 150)

    return f"""Eres un experto en currículo del Nivel Secundario dominicano (MINERD), Modalidad Académica.
Redacta una SECUENCIA DIDÁCTICA completa según el formato oficial MINERD 2018, con el mismo nivel de detalle que aparece en las secuencias publicadas por el ministerio (30+ páginas).

DATOS:
- Materia: {area_s}
- Grado: {grado_s} de Secundaria
- Período: P{periodo}
- Unidad N°: {numero_unidad}
- Título de la Unidad: {titulo_s}
- Duración: {semanas} semanas (5-7 horas/semana)

INSTRUCCIONES DE FORMATO:
- Todas las secciones deben ser EXTENSAS y DETALLADAS, como en los documentos reales del MINERD.
- Las estrategias deben tener INICIO / DESARROLLO / CIERRE para CADA semana, con tiempos, nombres de actividades, pasos, preguntas orientadoras, organización del aula y puesta en común.
- Usa viñeta • para listas. Usa \\n para saltos de línea DENTRO de strings JSON (nunca saltos literales).
- Devuelve ÚNICAMENTE el JSON. Sin texto antes ni después, sin bloques markdown.

JSON REQUERIDO (completa cada campo con contenido real y extenso):
{{
  "situacion_aprendizaje": "Párrafo narrativo de 150-200 palabras que contextualiza la unidad con una situación real o problema del entorno del estudiante dominicano. Debe motivar la curiosidad, conectar con la vida cotidiana y plantear el desafío de aprendizaje que guiará toda la unidad.",

  "preguntas_generadoras": ["¿Pregunta esencial 1 que abarca toda la unidad?", "¿Pregunta 2 que conecta el tema con la vida real?", "¿Pregunta 3 de reflexión crítica?", "¿Pregunta 4 de aplicación práctica?"],

  "competencias_especificas": "• Competencia 1 (Competencia Ética y Ciudadana): descripción de cómo se desarrolla en esta unidad.\\n• Competencia 2 (Competencia Comunicativa): descripción específica.\\n• Competencia 3 (Pensamiento Lógico, Creativo y Crítico): descripción.\\n• Competencia 4 (Resolución de Problemas): descripción.\\n• Competencia 5 (Científico-Tecnológica): descripción.",

  "objetivos": ["Objetivo 1 con verbo infinitivo que describe qué construirán los estudiantes", "Objetivo 2 específico y medible", "Objetivo 3 vinculado a la competencia fundamental"],

  "indicadores": ["Indicador 1: utiliza lenguaje específico de {area_s} para describir situaciones del entorno", "Indicador 2: resuelve problemas aplicando los conceptos de la unidad", "Indicador 3: comunica resultados de forma oral, escrita y gráfica", "Indicador 4: trabaja colaborativamente valorando los aportes de sus compañeros", "Indicador 5: aplica el conocimiento en situaciones nuevas del contexto dominicano"],

  "conceptuales": "• Concepto 1: definición clara y precisa.\\n• Concepto 2: descripción con ejemplos del contexto.\\n• Concepto 3: definición formal.\\n• Concepto 4: descripción.\\n• Concepto 5: descripción.\\n• Concepto 6: descripción.\\n• Concepto 7: descripción.",

  "procedimentales": "• Procedimiento 1: verbo de acción + descripción detallada del proceso.\\n• Procedimiento 2: descripción.\\n• Procedimiento 3: descripción.\\n• Procedimiento 4: descripción.\\n• Procedimiento 5: descripción.\\n• Procedimiento 6: descripción.",

  "actitudinales": "• Actitud 1: descripción vinculada al trabajo colaborativo.\\n• Actitud 2: descripción vinculada al pensamiento crítico.\\n• Actitud 3: valoración de la diversidad y los aportes ajenos.\\n• Actitud 4: disposición para revisar y mejorar el propio trabajo.",

  "estrategias": "SEMANA 1 — [Nombre temático de la semana]\\n\\nINICIO (20 min):\\n• Actividad de activación: [descripción detallada, preguntas que hace el docente, qué hacen los estudiantes].\\n• Pregunta orientadora: ¿[pregunta específica]?\\n\\nDESARROLLO (3h 30min):\\n• Actividad 1 — [nombre]: [descripción paso a paso, organización del aula (parejas/equipos), materiales, qué produce cada grupo].\\n• Actividad 2 — [nombre]: [descripción detallada con pasos y preguntas orientadoras].\\n• Actividad 3 — [nombre]: [descripción].\\n\\nCIERRE (20 min):\\n• Puesta en común: [cómo se socializa, quién presenta, qué se registra en pizarrón].\\n• Reflexión metacognitiva: ¿Qué aprendiste hoy? ¿Qué fue difícil?\\n• Tarea: [si aplica].\\n\\n---\\n\\nSEMANA 2 — [Nombre temático]\\n\\nINICIO (20 min):\\n• [descripción].\\n\\nDESARROLLO (3h 30min):\\n• Actividad 1 — [nombre]: [descripción detallada].\\n• Actividad 2 — [nombre]: [descripción].\\n\\nCIERRE (20 min):\\n• [descripción].\\n\\n[Repetir estructura para las {semanas} semanas]\\n\\n---\\n\\nEstrategias transversales: trabajo cooperativo en parejas heterogéneas, preguntas orientadoras del docente tipo socrático, registro colectivo en pizarrón, uso de TIC para exploración y verificación de resultados.",

  "recursos": "• Materiales físicos: [lista específica con cantidades].\\n• Tecnología: [dispositivos, apps o plataformas disponibles en RD].\\n• Impresos: [fichas, cuadernos, libros de texto MINERD].\\n• Espacio: [organización del aula].\\n• Recursos del docente: [guías, planillas de seguimiento].",

  "tipo_evaluacion": "formativa_sumativa",

  "instrumentos": "• Lista de cotejo: criterios para observar participación y construcción del conocimiento durante las actividades (semanas 1-2).\\n• Ficha de registro: tabla que completan los estudiantes durante las actividades de exploración.\\n• Rúbrica de producción escrita/oral: niveles Destacado / Satisfactorio / Básico / En Proceso / Insuficiente para evaluar el trabajo de la semana 3.\\n• Prueba situacional escrita: problema contextualizado de 3 ítems que evalúa comprensión y aplicación (semana {semanas}).",

  "criterios": "• Criterio 1: [descripción observable y medible vinculada al indicador 1].\\n• Criterio 2: [descripción].\\n• Criterio 3: [descripción].\\n• Criterio 4: [descripción].\\n• Criterio 5: comunica sus razonamientos de forma clara usando el lenguaje propio de {area_s}.",

  "bibliografia": "• Ministerio de Educación de la República Dominicana (2016). Diseño Curricular Nivel Secundario, {area_s}. Santo Domingo: MINERD.\\n• Libro de texto de {area_s} de {grado_s} (ed. vigente). Santo Domingo: MINERD.\\n• [Referencia adicional específica del tema].\\n• [Recurso digital recomendado para docentes y estudiantes en RD].",

  "transversalidades": {{"ambiental": false, "genero": false, "tics": true, "riesgo": false}}
}}

Rellena TODOS los campos con contenido real, extenso y específico para {area_s} de {grado_s} en República Dominicana. El campo "estrategias" debe incluir el INICIO, DESARROLLO y CIERRE completo para CADA una de las {semanas} semanas. No uses placeholders como [descripción] — escribe el contenido real."""


# ── WRAPPER CENTRALIZADO CON CONTROL DE TOKENS ──────────────────────────────

# Límite de tokens de entrada antes de truncar (deja margen para la respuesta)
_MAX_INPUT_TOKENS = 3500

def _contar_tokens(texto: str) -> int:
    """Cuenta tokens usando tiktoken (cl100k_base — compatible con LLaMA 3)."""
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(texto))
    except Exception:
        # Fallback: ~4 chars por token
        return len(texto) // 4


def _truncar_prompt(texto: str, max_tokens: int = _MAX_INPUT_TOKENS) -> tuple[str, int, int]:
    """
    Trunca el texto al límite de tokens conservando el inicio (instrucciones).
    Returns: (texto_truncado, tokens_original, tokens_final)
    """
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        tokens = enc.encode(texto)
        original = len(tokens)
        if original <= max_tokens:
            return texto, original, original
        truncados = tokens[:max_tokens]
        return enc.decode(truncados), original, max_tokens
    except Exception:
        # Fallback: truncar por chars
        original = len(texto) // 4
        if original <= max_tokens:
            return texto, original, original
        chars = max_tokens * 4
        return texto[:chars], original, max_tokens


def llamar_ia(
    messages: list,
    model: str = "openai/gpt-oss-120b",
    max_tokens: int = 800,
    temperature: float = 0.7,
    top_p: float = 0.9,
) -> tuple:
    """
    Wrapper centralizado para llamadas a Groq API.

    - Cuenta tokens de entrada antes de enviar
    - Trunca automáticamente si supera _MAX_INPUT_TOKENS
    - Loguea tokens usados por llamada

    Returns: (contenido: str, tokens_totales: int)
    Raises: RuntimeError si la API falla
    """
    # Contar tokens de todos los mensajes
    texto_completo = " ".join(m.get("content", "") for m in messages)
    tokens_antes = _contar_tokens(texto_completo)

    # Truncar el último mensaje user si es muy largo
    if tokens_antes > _MAX_INPUT_TOKENS:
        for i in range(len(messages) - 1, -1, -1):
            if messages[i].get("role") == "user":
                texto_user = messages[i]["content"]
                texto_truncado, orig, final = _truncar_prompt(
                    texto_user,
                    max_tokens=_MAX_INPUT_TOKENS - (tokens_antes - _contar_tokens(texto_user))
                )
                messages = list(messages)  # copia para no mutar el original
                messages[i] = {**messages[i], "content": texto_truncado}
                logger.info(
                    f"[IA] Prompt truncado: {orig} → {final} tokens "
                    f"(ahorrado: {orig - final} tokens)"
                )
                break

    try:
        client = _get_groq_client()
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
        )
        contenido = completion.choices[0].message.content.strip()
        tokens_usados = completion.usage.total_tokens if completion.usage else max_tokens
        logger.info(f"[IA] Groq OK — modelo={model} tokens={tokens_usados}")
        return contenido, tokens_usados
    except Exception as ex:
        logger.error(f"[IA] Error Groq: {ex}")
        raise RuntimeError(f"Error al llamar a la IA: {ex}") from ex


# ── CACHÉ SEMÁNTICO DE IA ────────────────────────────────────────────────────

def _keywords_ia(texto):
    """Extrae palabras clave significativas (4+ chars, sin stopwords)."""
    STOPS = {
        "para", "como", "una", "con", "que", "del", "los", "las", "por",
        "este", "esta", "sus", "son", "tiene", "hacer", "clase", "tema",
        "nivel", "grupo", "sobre", "cada", "sera", "seran", "entre",
    }
    words = re.findall(r"[a-záéíóúñü]{4,}", str(texto).lower())
    return set(w for w in words if w not in STOPS)


def _similitud_ia(ref_tipo, ref_grado, ref_materia, ref_tema,
                  tipo, grado, materia, tema):
    """Score 0-100: tipo(20) + grado(20) + materia(30) + keywords_tema(30)."""
    score = 0
    if ref_tipo and tipo and ref_tipo.lower() == tipo.lower():
        score += 20
    if ref_grado and grado and ref_grado.lower() == grado.lower():
        score += 20
    if ref_materia and materia and ref_materia.lower() == materia.lower():
        score += 30
    kw_ref = _keywords_ia(ref_tema or "")
    kw_new = _keywords_ia(tema or "")
    if kw_ref and kw_new:
        overlap = len(kw_ref & kw_new) / max(len(kw_ref), len(kw_new))
        score += round(overlap * 30)
    elif not kw_ref and not kw_new:
        score += 30  # ambos vacíos → tema idéntico
    return score


def buscar_cache_semantico(tipo, grado, materia, tema):
    """
    Busca en ia_cache la planificación más similar.
    Returns: dict con 'id', 'contenido', 'score', 'tema' | None si score < 70
    """
    import sqlite3 as _sq
    from .constants import DATABASE as _DB
    try:
        with _sq.connect(_DB, timeout=5) as conn:
            conn.row_factory = _sq.Row
            rows = conn.execute(
                "SELECT id, tipo, grado, materia, tema, contenido, tokens_usados, usos "
                "FROM ia_cache WHERE tipo=? AND LOWER(materia)=LOWER(?) "
                "ORDER BY usos DESC LIMIT 20",
                (tipo, materia)
            ).fetchall()
    except Exception:
        return None

    best, best_score = None, 0
    for row in rows:
        sc = _similitud_ia(
            row["tipo"], row["grado"], row["materia"], row["tema"] or "",
            tipo, grado, materia, tema,
        )
        if sc > best_score:
            best_score = sc
            best = row

    if best and best_score >= 70:
        return {
            "id": best["id"],
            "contenido": best["contenido"],
            "score": best_score,
            "tema": best["tema"],
        }
    return None


def guardar_cache_ia(tipo, grado, materia, tema, periodo, contenido, tokens, usuario_id):
    """Inserta o actualiza entrada en ia_cache."""
    import sqlite3 as _sq
    from .constants import DATABASE as _DB
    try:
        with _sq.connect(_DB, timeout=5) as conn:
            conn.row_factory = _sq.Row
            existe = conn.execute(
                "SELECT id FROM ia_cache WHERE tipo=? AND LOWER(grado)=LOWER(?) "
                "AND LOWER(materia)=LOWER(?) AND LOWER(tema)=LOWER(?)",
                (tipo, grado, materia, tema)
            ).fetchone()
            if existe:
                conn.execute(
                    "UPDATE ia_cache SET contenido=?, tokens_usados=?, "
                    "ultimo_uso=datetime('now'), usos=usos+1 WHERE id=?",
                    (contenido, tokens, existe["id"])
                )
            else:
                conn.execute(
                    "INSERT INTO ia_cache (tipo, grado, materia, periodo, tema, contenido, "
                    "tokens_usados, usos, creado_por, creado_en, ultimo_uso) "
                    "VALUES (?,?,?,?,?,?,?,1,?,datetime('now'),datetime('now'))",
                    (tipo, grado, materia, periodo or "", tema, contenido, tokens, usuario_id)
                )
            conn.commit()
    except Exception as ex:
        logger.warning(f"[AI_CACHE] Error guardando: {ex}")


def incrementar_uso_cache(cache_id):
    """Incrementa el contador de uso de un registro de caché."""
    import sqlite3 as _sq
    from .constants import DATABASE as _DB
    try:
        with _sq.connect(_DB, timeout=5) as conn:
            conn.execute(
                "UPDATE ia_cache SET usos=usos+1, ultimo_uso=datetime('now') WHERE id=?",
                (cache_id,)
            )
            conn.commit()
    except Exception:
        pass
