# -*- coding: utf-8 -*-
"""Blueprint: planificacion"""

import sqlite3
import logging
import json as _json
import os
import re
import time as _time
from datetime import datetime, date, timedelta
from io import BytesIO
from flask import (
    Blueprint, render_template, request, jsonify, session,
    redirect, url_for, g, send_from_directory, Response, send_file,
)

from core.constants import *
from core.database import get_db, cache_get, cache_set, cache_bust, _CACHE
from core.auth import (
    _hash, _check_password, _normalizar_rol, _ciclo_del_rol,
    login_required, coord_required, admin_required, directora_required,
    _csrf_token, _csrf_check, csrf_protected, rate_limited,
    get_usuario,
)
from core.helpers import *
from core.ia import (
    _get_groq_client, groq_client, construir_prompt,
    construir_prompt_planificacion, construir_prompt_rubrica, construir_prompt_estrategia,
    buscar_cache_semantico, guardar_cache_ia, incrementar_uso_cache,
)
from core.excel import _parsear_boletin_bj, _buscar_o_crear_estudiante, _detectar_mencion_listado, _limpiar_nota
from core.pdf import _generar_pdf_acuerdo
from core.rag import buscar_chunks
from core.curriculo import get_asignatura as _curriculo_get, formatear_contexto as _curriculo_fmt, COMPETENCIAS_FUNDAMENTALES, FASES_ABP, ELEMENTOS_STEAM

logger = logging.getLogger("axula")

planificacion_bp = Blueprint("planificacion_bp", __name__)

@planificacion_bp.route("/planificacion")
@login_required
def planificacion():
    """Dashboard del Asistente de Planificación Docente."""
    u = get_usuario()
    # Pasar el plan de materias técnicas por mención para el tab ABP
    # Solo materias técnicas (no las 7 académicas comunes)
    MATS_ACAD = {"Lengua Española","Inglés","Matemática","Ciencias Sociales",
                 "Ciencias de la Naturaleza","Formación Integral Humana y Religiosa","Educación Física"}
    plan_tecnicas = {}
    for mencion, grados in PLAN_ARTES.items():
        plan_tecnicas[mencion] = {}
        for grado, materias in grados.items():
            plan_tecnicas[mencion][grado] = [
                {"nombre": n, "horas": h}
                for n, h in materias if n not in MATS_ACAD
            ]
    return render_template(
        "planificacion.html",
        current_user=u,
        plan_tecnicas=plan_tecnicas,
    )


@planificacion_bp.route("/api/planificacion/generar", methods=["POST"])
@login_required
@rate_limited(max_calls=20, window=60)
def generar_planificacion():
    """Genera una planificación de clase con LLaMA 3. Usa caché semántico si score >= 70%."""
    from core.ia import _sanitizar_campo
    data    = request.json
    materia = _sanitizar_campo(data.get("materia", ""), 80)
    grado   = _sanitizar_campo(data.get("grado", "4to"), 20)
    tema    = _sanitizar_campo(data.get("tema", ""), 300)
    duracion= data.get("duracion", 2)
    nivel   = _sanitizar_campo(data.get("nivel_grupo", "Intermedio"), 50)
    mencion = _sanitizar_campo(data.get("mencion", "MULTIMEDIA"), 40)
    u       = get_usuario()

    if not materia or not tema:
        return jsonify({"error": "Materia y tema son requeridos"}), 400

    # ── Caché semántico ──────────────────────────────────────────────────────
    cache = buscar_cache_semantico("planificacion", grado, materia, tema)

    if cache and cache["score"] == 100:
        # Coincidencia exacta — devolver sin llamar a Groq
        incrementar_uso_cache(cache["id"])
        return jsonify({
            "resultado": cache["contenido"],
            "tipo": "planificacion",
            "from_cache": True,
            "cache_score": 100,
        })

    if cache and cache["score"] >= 70:
        # Coincidencia parcial — prompt de adaptación (mucho más corto)
        adaptation_prompt = (
            f"Tienes esta planificación de {materia.replace('_',' ')} en {grado} "
            f"sobre \"{cache['tema']}\":\n\n"
            f"{cache['contenido'][:900]}\n\n"
            f"--- Adaptación solicitada ---\n"
            f"Nuevo tema: \"{tema}\"\n"
            f"Nivel del grupo: {nivel} | Duración: {duracion} clases\n\n"
            f"Actualiza SOLO las secciones que cambien por el nuevo tema "
            f"(Objetivo, Motivación Inicial, Desarrollo, Actividad Práctica). "
            f"Mantén la estructura de 8 secciones. Máximo 500 palabras."
        )
        try:
            completion = _get_groq_client().chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content":
                        "Eres un experto en planificación curricular para la Modalidad de Artes "
                        f"mención {mencion} del bachillerato dominicano. Respondes en español."},
                    {"role": "user", "content": adaptation_prompt},
                ],
                temperature=0.6,
                max_tokens=800,
                top_p=0.9,
            )
            resultado = completion.choices[0].message.content.strip()
            tokens    = completion.usage.total_tokens if completion.usage else 800
            guardar_cache_ia("planificacion", grado, materia, tema, None, resultado, tokens, u["id"])
            return jsonify({
                "resultado": resultado,
                "tipo": "planificacion",
                "from_cache": False,
                "cache_score": cache["score"],
                "tokens_ahorrados": True,
            })
        except Exception as ex:
            logger.error(f"[IA] generar_planificacion: {ex}")
            return jsonify({"error": "Error al generar la planificación. Intenta de nuevo."}), 500

    # ── Generación completa ──────────────────────────────────────────────────
    try:
        # RAG: enriquecer con normativa MINERD subida por el centro
        _rag_ctx = ""
        try:
            _rag_ctx = buscar_chunks(get_db(), f"planificación {materia} {grado} {tema}", top_k=3, max_chars_total=1800, mencion=mencion)
        except Exception:
            pass
        _sys_content = (
            "Eres un experto en planificación curricular para la Modalidad de Artes "
            f"mención {mencion} del bachillerato dominicano (C.E. Benito Juárez). "
            "Respondes siempre en español con planificaciones prácticas, "
            "creativas y alineadas al currículo oficial del MINERD."
        )
        if _rag_ctx:
            _sys_content += f"\n\n{_rag_ctx}"

        completion = _get_groq_client().chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": _sys_content,
                },
                {
                    "role": "user",
                    "content": construir_prompt_planificacion(materia, grado, tema, duracion, nivel, mencion)
                }
            ],
            temperature=0.7,
            max_tokens=1200,
            top_p=0.9,
        )
        resultado = completion.choices[0].message.content.strip()
        tokens    = completion.usage.total_tokens if completion.usage else 1200
        guardar_cache_ia("planificacion", grado, materia, tema, None, resultado, tokens, u["id"])
        return jsonify({"resultado": resultado, "tipo": "planificacion", "from_cache": False})

    except Exception as ex:
        logger.error(f"[IA] generar_planificacion completa: {ex}")
        return jsonify({"error": "Error al generar la planificación. Intenta de nuevo."}), 500


@planificacion_bp.route("/api/planificacion/rubrica", methods=["POST"])
@login_required
@rate_limited(max_calls=20, window=60)
def generar_rubrica():
    """Genera una rúbrica de evaluación alineada al currículo MINERD."""
    from core.ia import _sanitizar_campo
    data = request.json
    materia   = _sanitizar_campo(data.get("materia", ""), 80)
    indicador = _sanitizar_campo(data.get("indicador", ""), 300)
    nivel     = _sanitizar_campo(data.get("nivel", "4to"), 20)

    if not materia or not indicador:
        return jsonify({"error": "Materia e indicador son requeridos"}), 400

    try:
        completion = _get_groq_client().chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un experto en evaluación educativa para la Modalidad de Artes "
                        "del bachillerato dominicano. Creas rúbricas prácticas y alineadas al MINERD."
                    )
                },
                {
                    "role": "user",
                    "content": construir_prompt_rubrica(materia, indicador, nivel)
                }
            ],
            temperature=0.5,
            max_tokens=800,
            top_p=0.9
        )
        resultado = completion.choices[0].message.content.strip()
        return jsonify({"resultado": resultado, "tipo": "rubrica"})

    except Exception as ex:
        logger.error(f"[IA] generar_rubrica: {ex}")
        return jsonify({"error": "Error al generar la rúbrica. Intenta de nuevo."}), 500


@planificacion_bp.route("/api/planificacion/estrategia", methods=["POST"])
@login_required
@rate_limited(max_calls=20, window=60)
def generar_estrategia():
    """Genera estrategias didácticas para superar dificultades específicas."""
    from core.ia import _sanitizar_campo
    data = request.json
    materia  = _sanitizar_campo(data.get("materia", ""), 80)
    problema = _sanitizar_campo(data.get("problema", ""), 400)
    perfil   = _sanitizar_campo(data.get("perfil_grupo", ""), 200)

    if not materia or not problema:
        return jsonify({"error": "Materia y problema son requeridos"}), 400

    try:
        completion = _get_groq_client().chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un orientador pedagógico experto en la Modalidad de Artes "
                        "del bachillerato dominicano. Ofreces estrategias didácticas prácticas "
                        "y contextualizadas para el sistema educativo de RD."
                    )
                },
                {
                    "role": "user",
                    "content": construir_prompt_estrategia(materia, problema, perfil)
                }
            ],
            temperature=0.7,
            max_tokens=700,
            top_p=0.9
        )
        resultado = completion.choices[0].message.content.strip()
        return jsonify({"resultado": resultado, "tipo": "estrategia"})

    except Exception as ex:
        logger.error(f"[IA] generar_estrategia: {ex}")
        return jsonify({"error": "Error al generar estrategias. Intenta de nuevo."}), 500


@planificacion_bp.route("/api/planificacion/guardar", methods=["POST"])
@login_required
def guardar_planificacion():
    """Guarda una planificación generada en el historial."""
    u = get_usuario()
    d = request.get_json(silent=True) or {}
    contenido = (d.get("contenido") or "").strip()
    materia   = (d.get("materia") or "").strip()
    grado     = (d.get("grado") or "").strip()
    tema      = (d.get("tema") or "").strip()
    if not contenido:
        return jsonify({"error": "Sin contenido para guardar"}), 400
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.execute("""
            INSERT INTO historial_planificaciones
                (profesor_id, materia, grado, tema, nivel_grupo, contenido,
                 estudiante_id, nombre_estudiante, fecha)
            VALUES (?,?,?,?,?,?,?,?,date('now'))
        """, (
            u["id"], materia, grado, tema,
            d.get("nivel_grupo",""),
            contenido,
            d.get("estudiante_id"),
            d.get("nombre_estudiante","")
        ))
        conn.commit()
        rid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    return jsonify({"ok": True, "id": rid})


@planificacion_bp.route("/api/planificacion/historial", methods=["GET"])
@login_required
def historial_planificaciones():
    """Devuelve el historial de planificaciones del usuario."""
    u = get_usuario()
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT id, materia, grado, tema, nivel_grupo,
                   nombre_estudiante, fecha,
                   substr(contenido,1,120) as preview
            FROM historial_planificaciones
            WHERE profesor_id=?
            ORDER BY fecha DESC, id DESC
            LIMIT 50
        """, (u["id"],)).fetchall()
    return jsonify([dict(r) for r in rows])


@planificacion_bp.route("/api/planificacion/historial/<int:pid>", methods=["GET"])
@login_required
def get_planificacion(pid):
    u = get_usuario()
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM historial_planificaciones WHERE id=? AND profesor_id=?",
            (pid, u["id"])
        ).fetchone()
    if not row:
        return jsonify({"error": "No encontrado"}), 404
    return jsonify(dict(row))


@planificacion_bp.route("/api/planificacion/historial/<int:pid>", methods=["DELETE"])
@login_required
def eliminar_planificacion(pid):
    u = get_usuario()
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.execute(
            "DELETE FROM historial_planificaciones WHERE id=? AND profesor_id=?",
            (pid, u["id"])
        )
        conn.commit()
    return jsonify({"ok": True})


@planificacion_bp.route("/api/planificacion/curriculo/<materia>")
@login_required
def obtener_curriculo(materia):
    """
    Devuelve datos curriculares oficiales de una materia.
    Acepta ?mencion=MULTIMEDIA|ARTES VISUALES|MUSICA|TEATRO para buscar en el módulo correcto.
    Formato de respuesta compatible con el front-end existente.
    """
    mencion = request.args.get("mencion", "MULTIMEDIA").upper().strip()
    # Normalizar nombre: "Lenguaje_Visual" → "Lenguaje Visual"
    nombre_limpio = materia.replace("_", " ").strip()

    raw = _curriculo_get(mencion, nombre_limpio)

    # Si no encontró en los módulos nuevos, intentar el dict viejo
    if not raw:
        raw = CURRICULUM_ARTES.get(materia, CURRICULUM_ARTES.get(nombre_limpio, {}))

    if raw:
        # Unificar formatos: módulos nuevos vs dict viejo
        datos = {
            "competencia":  raw.get("competencia") or raw.get("elemento_competencia", "")[:120],
            "descripcion":  raw.get("descripcion") or raw.get("elemento_competencia", ""),
            "horas":        raw.get("horas", raw.get("horas_semana", 2)),
            "saberes_conceptuales":    raw.get("saberes_conceptuales") or raw.get("conceptuales", []),
            "saberes_procedimentales": raw.get("saberes_procedimentales") or raw.get("procedimentales", []),
            "saberes_actitudinales":   raw.get("saberes_actitudinales") or raw.get("actitudinales", []),
            "indicadores_logro":       raw.get("indicadores_logro") or raw.get("rae", []),
            "evidencias":              raw.get("evidencias", "Portafolio o proyecto integrador"),
        }
    else:
        datos = {
            "competencia":             f"Competencia — {nombre_limpio}",
            "descripcion":             f"Asignatura del plan de estudios MINERD — Mención {mencion.title()}.",
            "horas":                   2,
            "saberes_conceptuales":    ["Contenidos conceptuales según plan MINERD"],
            "saberes_procedimentales": ["Procedimientos según plan MINERD"],
            "saberes_actitudinales":   ["Actitudes y valores"],
            "indicadores_logro":       ["El estudiante demuestra dominio de los contenidos"],
            "evidencias":              "Portafolio o proyecto integrador",
        }
    return jsonify(datos)


@planificacion_bp.route("/api/planificacion/generar-abp", methods=["POST"])
@login_required
@rate_limited(max_calls=20, window=60)
def generar_planificacion_abp():
    """
    Genera el JSON estructurado completo para una planificación ABP MINERD
    usando LLaMA 3.3-70B con fidelidad al currículo oficial de Bachillerato
    en Artes (MINERD). Soporta todas las menciones: Multimedia, Artes Visuales,
    Música y Teatro. Inyecta los saberes oficiales de la asignatura como contexto.
    """
    u = get_usuario()
    data = request.get_json(silent=True) or {}

    asignatura   = (data.get("asignatura") or "").strip()
    grado        = (data.get("grado") or "4to").strip()
    mencion      = (data.get("mencion") or "MULTIMEDIA").strip().upper()
    titulo       = (data.get("titulo_proyecto") or "").strip()
    fecha_inicio = (data.get("fecha_inicio") or "").strip()
    fecha_cierre = (data.get("fecha_cierre") or "").strip()
    duracion     = (data.get("duracion") or "").strip()
    producto     = (data.get("producto_final") or "").strip()
    contexto_ia  = (data.get("contexto_adicional") or "").strip()

    if not asignatura:
        return jsonify({"error": "La asignatura es requerida"}), 400

    nombre_docente = u.get("nombre", "")

    # ── CONTEXTO OFICIAL DEL CURRÍCULO ─────────────────────────────────────
    curriculo_oficial = _curriculo_fmt(mencion, asignatura)
    datos_oficiales   = _curriculo_get(mencion, asignatura)

    # ── CONTEXTO RAG — normativa vigente subida por el centro ─────────────
    rag_contexto = ""
    try:
        rag_consulta = f"planificación {asignatura} {grado} bachillerato artes {mencion.lower()} ordenanza"
        rag_contexto = buscar_chunks(get_db(), rag_consulta, top_k=4, max_chars_total=2500, mencion=mencion)
    except Exception as _rag_err:
        logger.warning(f"[RAG] No se pudo recuperar contexto: {_rag_err}")

    # ── PROMPT DEL SISTEMA ─────────────────────────────────────────────────
    prompt_sistema = f"""Eres un experto en planificación curricular ABP para la Modalidad en Artes del MINERD
de la República Dominicana, especializado en Bachillerato en Arte Multimedia
(C.E. Benito Juárez — Mención {mencion}).

Conoces el esquema oficial MINERD/DEMA con sus 4 bloques: IDENTIFICACIÓN,
ELEMENTOS DE LA UNIDAD, FASES ABP (4 fases) e INSTRUMENTOS DE EVALUACIÓN.

REGLAS CRÍTICAS:
1. SIEMPRE respondes ÚNICAMENTE con JSON válido, sin texto antes ni después, sin markdown.
2. NO repites contenido entre secciones — cada campo debe tener información única y específica.
3. Usas EXCLUSIVAMENTE los saberes oficiales que te proporciono del plan MINERD,
   no inventes contenidos genéricos. Si amplías, mantén el enfoque oficial.
4. Las actividades deben ser ESPECÍFICAS de la asignatura, con verbos de acción
   (investiga, diseña, produce, presenta), no frases vacías.
5. La integración STEAM debe incluir los 5 elementos (Ciencia, Tecnología, Ingeniería, Arte, Matemática)
   con ejemplos aplicados al proyecto concreto.
6. Las 4 fases ABP son fijas y en este orden: Exploración e Investigación, Diseño y Planificación,
   Desarrollo y Construcción, Presentación y Evaluación.

{rag_contexto if rag_contexto else ""}"""

    # ── PROMPT DEL USUARIO ─────────────────────────────────────────────────
    prompt_usuario = f"""Genera una planificación ABP oficial MINERD para:

DATOS DEL PROYECTO:
- Asignatura: {asignatura}
- Docente: {nombre_docente}
- Grado: {grado} — Mención {mencion.title()}
- Título del proyecto: {titulo if titulo else "(inventa un título creativo y específico al proyecto)"}
- Fecha inicio: {fecha_inicio if fecha_inicio else "(período actual)"}
- Fecha cierre: {fecha_cierre if fecha_cierre else "(al finalizar el período)"}
- Duración: {duracion if duracion else "2 meses (8 semanas aproximadamente)"}
- Producto final esperado: {producto if producto else "(sugiere el producto final típico de esta asignatura)"}
{f"- Contexto adicional del docente: {contexto_ia}" if contexto_ia else ""}

CURRÍCULO OFICIAL MINERD PARA ESTA ASIGNATURA:
{curriculo_oficial if curriculo_oficial else "(No hay datos oficiales — usa tu conocimiento del currículo de Bachillerato en Arte Multimedia MINERD)"}

INSTRUCCIONES ESPECÍFICAS PARA EL JSON:

1. **curriculo.contenidos**: Usa los saberes oficiales listados arriba. Selecciona
   los 4-6 más relevantes al proyecto propuesto. NO los repitas entre conceptuales,
   procedimentales y actitudinales — cada categoría debe tener contenido distinto.

2. **curriculo.rae**: Usa los RAEs oficiales listados arriba, o derívalos del
   Elemento de Competencia oficial.

3. **curriculo.elementos_competencia**: Cita el Elemento de Competencia oficial
   (párrafo completo) y añade 2-3 indicadores observables derivados.

4. **curriculo.problema**: Redacta un párrafo contextual que explique una
   situación real de los estudiantes dominicanos que el proyecto viene a resolver.
   Debe conectar con la realidad del joven dominicano.

5. **curriculo.pregunta**: Formula UNA pregunta desafiante abierta que guíe
   todo el proyecto. Debe empezar con "¿Cómo..." o "¿De qué manera...".

6. **fases**: Genera LAS 4 FASES en orden. Cada fase debe tener:
   - Actividades concretas (3-5 actividades con verbos de acción) distribuidas
     en momentos de Inicio, Desarrollo y Cierre.
   - Los 5 elementos STEAM aplicados específicamente al proyecto.
   - Roles específicos del docente y del estudiante (no genéricos).
   - Recursos materiales/digitales concretos.
   - Instrumentos de evaluación específicos (lista de cotejo, rúbrica, registro anecdótico, etc).

7. **instrumentos**: Genera lista de cotejo con 6-8 criterios específicos al producto final,
   rúbrica de proceso con 3 niveles de dominio, rúbrica final con 4 criterios de 20 pts c/u.

ESTRUCTURA JSON EXACTA (sin markdown, sin texto extra):

{{
  "docente": {{
    "nombre_completo": "{nombre_docente}",
    "asignatura": "{asignatura}",
    "grado": "{grado} {mencion.title()}",
    "mencion": "{mencion.title()}",
    "centro": "Centro Educativo en Artes Benito Juárez",
    "modulo": "{datos_oficiales.get('modulo', 'Formación Artístico-Cultural')}",
    "horas_semanales": "{datos_oficiales.get('horas', '')}"
  }},
  "proyecto": {{
    "titulo": "título creativo específico del proyecto",
    "fecha_inicio": "{fecha_inicio}",
    "fecha_cierre": "{fecha_cierre}",
    "duracion": "{duracion if duracion else '2 meses'}",
    "metodologia": "ABP",
    "producto_final": "descripción específica del producto final con características técnicas"
  }},
  "curriculo": {{
    "rae": ["RAE 1 (usar los oficiales)", "RAE 2", "RAE 3"],
    "contenidos": {{
      "conceptuales": ["contenido conceptual 1", "contenido 2", "contenido 3", "contenido 4"],
      "procedimentales": ["procedimiento 1", "procedimiento 2", "procedimiento 3", "procedimiento 4"],
      "actitudinales": ["actitud 1", "actitud 2", "actitud 3"]
    }},
    "elementos_competencia": ["elemento competencia oficial", "indicador observable 1", "indicador observable 2"],
    "problema": "párrafo contextualizado sobre la situación real que motiva el proyecto",
    "pregunta": "¿Pregunta desafiante abierta que guíe todo el proyecto?"
  }},
  "fases": [
    {{
      "numero": 1,
      "nombre": "Exploración e Investigación",
      "tiempo": "2 semanas",
      "competencias_especificas": ["competencia laboral 1", "competencia laboral 2"],
      "actividades_inicio": ["actividad 1", "actividad 2"],
      "actividades_desarrollo": ["actividad 1", "actividad 2", "actividad 3"],
      "actividades_cierre": ["actividad de cierre"],
      "steam": {{
        "ciencia": "aplicación científica específica",
        "tecnologia": "herramientas tecnológicas a usar",
        "ingenieria": "análisis estructural/proceso",
        "arte": "dimensión artística/estética",
        "matematica": "dimensión matemática/lógica"
      }},
      "rol_docente": ["acción docente 1", "acción docente 2", "acción docente 3"],
      "rol_estudiante": ["acción estudiante 1", "acción estudiante 2"],
      "recursos": ["recurso 1", "recurso 2", "recurso 3"],
      "instrumentos_evaluacion": ["instrumento 1", "instrumento 2"]
    }},
    {{
      "numero": 2,
      "nombre": "Diseño y Planificación",
      "tiempo": "2 semanas",
      "competencias_especificas": ["..."],
      "actividades_inicio": ["..."],
      "actividades_desarrollo": ["..."],
      "actividades_cierre": ["..."],
      "steam": {{"ciencia": "...", "tecnologia": "...", "ingenieria": "...", "arte": "...", "matematica": "..."}},
      "rol_docente": ["..."],
      "rol_estudiante": ["..."],
      "recursos": ["..."],
      "instrumentos_evaluacion": ["..."]
    }},
    {{
      "numero": 3,
      "nombre": "Desarrollo y Construcción",
      "tiempo": "3 semanas",
      "competencias_especificas": ["..."],
      "actividades_inicio": ["..."],
      "actividades_desarrollo": ["..."],
      "actividades_cierre": ["..."],
      "steam": {{"ciencia": "...", "tecnologia": "...", "ingenieria": "...", "arte": "...", "matematica": "..."}},
      "rol_docente": ["..."],
      "rol_estudiante": ["..."],
      "recursos": ["..."],
      "instrumentos_evaluacion": ["..."]
    }},
    {{
      "numero": 4,
      "nombre": "Presentación y Evaluación",
      "tiempo": "1 semana",
      "competencias_especificas": ["..."],
      "actividades_inicio": ["..."],
      "actividades_desarrollo": ["..."],
      "actividades_cierre": ["..."],
      "steam": {{"ciencia": "...", "tecnologia": "...", "ingenieria": "...", "arte": "...", "matematica": "..."}},
      "rol_docente": ["..."],
      "rol_estudiante": ["..."],
      "recursos": ["..."],
      "instrumentos_evaluacion": ["..."]
    }}
  ],
  "instrumentos": {{
    "lista_cotejo": [
      "criterio observable 1",
      "criterio observable 2",
      "criterio observable 3",
      "criterio observable 4",
      "criterio observable 5",
      "criterio observable 6"
    ],
    "rubrica_proceso": [
      {{"criterio": "Investigación", "destacado": "...", "satisfactorio": "...", "basico": "...", "en_proceso": "..."}},
      {{"criterio": "Trabajo en equipo", "destacado": "...", "satisfactorio": "...", "basico": "...", "en_proceso": "..."}},
      {{"criterio": "Creatividad", "destacado": "...", "satisfactorio": "...", "basico": "...", "en_proceso": "..."}}
    ],
    "rubrica_final": [
      {{"criterio": "Criterio 1", "excelente_20": "...", "bueno_15": "...", "basico_10": "...", "bajo_5": "..."}},
      {{"criterio": "Criterio 2", "excelente_20": "...", "bueno_15": "...", "basico_10": "...", "bajo_5": "..."}},
      {{"criterio": "Criterio 3", "excelente_20": "...", "bueno_15": "...", "basico_10": "...", "bajo_5": "..."}},
      {{"criterio": "Criterio 4", "excelente_20": "...", "bueno_15": "...", "basico_10": "...", "bajo_5": "..."}}
    ]
  }}
}}"""

    try:
        completion = _get_groq_client().chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": prompt_sistema},
                {"role": "user",   "content": prompt_usuario},
            ],
            temperature=0.65,
            max_tokens=6500,
            top_p=0.9,
        )
        raw = completion.choices[0].message.content.strip()

        # Limpiar posibles bloques markdown
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        if raw.endswith("```"):
            raw = raw[:-3].strip()

        plan_json = _json.loads(raw)

        # ── POST-PROCESAMIENTO: INYECTAR COMPETENCIAS FUNDAMENTALES OFICIALES ──
        # La IA NO genera las 7 competencias (evita el bug de duplicados).
        # Las inyectamos desde el código con los nombres oficiales exactos.
        if "curriculo" not in plan_json:
            plan_json["curriculo"] = {}
        plan_json["curriculo"]["competencias_fundamentales"] = list(COMPETENCIAS_FUNDAMENTALES)

        # Asegurar que los datos del docente sean los correctos (no lo que la IA invente)
        plan_json["docente"] = plan_json.get("docente", {})
        plan_json["docente"]["nombre_completo"] = nombre_docente
        plan_json["docente"]["asignatura"] = asignatura
        plan_json["docente"]["grado"] = f"{grado} {mencion.title()}"
        plan_json["docente"]["mencion"] = mencion.title()
        plan_json["docente"]["centro"] = "Centro Educativo en Artes Benito Juárez"
        if datos_oficiales.get("modulo"):
            plan_json["docente"]["modulo"] = datos_oficiales["modulo"]
        if datos_oficiales.get("horas"):
            plan_json["docente"]["horas_semanales"] = datos_oficiales["horas"]

        # Validación: las 4 fases deben estar en orden
        if "fases" in plan_json and isinstance(plan_json["fases"], list):
            nombres_correctos = list(FASES_ABP)
            for i, fase in enumerate(plan_json["fases"][:4]):
                if i < len(nombres_correctos):
                    fase["nombre"] = nombres_correctos[i]
                    fase["numero"] = i + 1

        return jsonify({"ok": True, "plan": plan_json})

    except _json.JSONDecodeError as ex:
        logger.error(f"[IA] ABP JSON inválido: {ex}")
        return jsonify({"error": "La IA devolvió un formato inesperado. Intenta de nuevo."}), 500
    except Exception as ex:
        logger.error(f"[IA] Error generando planificación ABP: {ex}")
        return jsonify({"error": "Error generando la planificación. Intenta de nuevo."}), 500


@planificacion_bp.route("/api/planificacion/exportar-docx", methods=["POST"])
@login_required
def exportar_planificacion_docx():
    """
    Recibe el JSON del plan ABP y genera el .docx oficial MINERD.
    Devuelve el archivo para descarga directa.
    """
    import json as _json
    import subprocess
    import tempfile
    import os

    data = request.get_json(silent=True) or {}
    plan = data.get("plan")
    if not plan:
        return jsonify({"error": "Se requiere el plan en formato JSON"}), 400

    # Rutas del script generador
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "generar_planificacion_abp.js")
    if not os.path.exists(script_path):
        return jsonify({"error": "Generador de documentos no encontrado"}), 500

    try:
        # Escribir JSON a archivo temporal
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False, encoding='utf-8'
        ) as tmp_in:
            _json.dump(plan, tmp_in, ensure_ascii=False)
            tmp_in_path = tmp_in.name

        # Archivo de salida temporal
        tmp_out = tempfile.NamedTemporaryFile(suffix='.docx', delete=False)
        tmp_out_path = tmp_out.name
        tmp_out.close()

        # Ejecutar el generador Node.js
        # Asegurar que docx esté disponible localmente en el directorio del proyecto
        import shutil
        node_bin  = shutil.which("node") or "node"
        npm_bin   = shutil.which("npm")  or "npm"
        proj_dir  = os.path.dirname(os.path.abspath(__file__))
        node_mod  = os.path.join(proj_dir, "node_modules", "docx")

        # Si docx no está instalado localmente, instalarlo ahora
        if not os.path.exists(node_mod):
            install = subprocess.run(
                [npm_bin, "install", "docx", "--prefix", proj_dir],
                capture_output=True, text=True, timeout=120
            )
            if install.returncode != 0:
                return jsonify({"error": f"No se pudo instalar el módulo docx: {install.stderr[:200]}"}), 500

        result = subprocess.run(
            [node_bin, script_path, tmp_in_path, tmp_out_path],
            capture_output=True, text=True, timeout=30,
            cwd=proj_dir  # ejecutar desde el directorio del proyecto
        )

        os.unlink(tmp_in_path)

        if result.returncode != 0:
            return jsonify({"error": f"Error generando documento: {result.stderr}"}), 500

        # Nombre del archivo de descarga
        asignatura = (plan.get("docente") or {}).get("asignatura", "Planificacion")
        titulo = (plan.get("proyecto") or {}).get("titulo", "ABP")
        nombre_archivo = f"Plan_ABP_{asignatura.replace(' ','_')}_{titulo[:30].replace(' ','_')}.docx"

        from flask import send_file
        return send_file(
            tmp_out_path,
            as_attachment=True,
            download_name=nombre_archivo,
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )

    except subprocess.TimeoutExpired:
        return jsonify({"error": "Tiempo de generación agotado"}), 504
    except Exception as ex:
        logger.error(f"[IA] Error exportando DOCX: {ex}")
        return jsonify({"error": "Error al exportar el documento. Intenta de nuevo."}), 500




# ── MIGRACIÓN AUTOMÁTICA DE BASE DE DATOS ───────────────────────────────────
#
# CÓMO AGREGAR UNA FUNCIÓN NUEVA SIN BORRAR LA BASE DE DATOS:
#
#   1. Nueva columna en 'estudiantes':
#      → Agrégala a COLUMNAS_ESTUDIANTES abajo. Flask la crea al reiniciar.
#
#   2. Nueva tabla completa:
#      → Agrégala a TABLAS_NUEVAS abajo con su CREATE TABLE IF NOT EXISTS.
#
#   3. Cambio de tipo o renombrar columna (SQLite no lo permite directo):
#      → Agrega la entrada a MIGRACIONES_ESPECIALES con tu lógica SQL.
#
#   Nunca borres database.db. Solo reinicia Flask y listo.
# ────────────────────────────────────────────────────────────────────────────

# ── 1. COLUMNAS de la tabla estudiantes ──────────────────────────────────────
# Formato: (nombre_columna, tipo_sql, valor_default)


