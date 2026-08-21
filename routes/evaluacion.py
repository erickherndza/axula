# -*- coding: utf-8 -*-
"""Blueprint: evaluacion — Sistema de evaluación por competencias Ord.04-2023"""

import sqlite3
import logging
import json as _json
import os
import time as _time
from datetime import datetime, date, timedelta
from flask import (
    Blueprint, render_template, request, jsonify, session,
    redirect, url_for,
)

from core.constants import *
from core.database import get_db, cache_get, cache_set, cache_bust, cache_delete
from core.auth import (
    _normalizar_rol, login_required, get_usuario,
    _csrf_token, _csrf_check, rate_limited,
)
from core.helpers import *
from core.helpers import (
    _get_profesor, _resolver_alcance_profesor, _anio_escolar_actual,
    _periodo_actual, _audit,
)
from core import grades as G
from core.ia import generar_con_fallback
from core.evaluacion_engine import (
    get_puntos_usados_periodo, validar_puntos_actividad,
    calcular_nota_periodo, calcular_nota_final_area,
    get_estado_estudiante_periodo, cerrar_periodo,
    TOTAL_PUNTOS_PERIODO,
)

logger = logging.getLogger("axula")

evaluacion_bp = Blueprint("evaluacion_bp", __name__)


def _parse_periodo(p) -> int:
    """Convierte 'P1', '1', 1 → entero 1-4."""
    if isinstance(p, int):
        return p
    s = str(p).strip().upper().lstrip('P')
    return int(s) if s else 1


def _get_anio_escolar_id(conn, anio_texto: str) -> int:
    """Retorna el id de anios_escolares para el texto dado, creando si no existe."""
    row = conn.execute(
        "SELECT id FROM anios_escolares WHERE nombre = ?", [anio_texto]
    ).fetchone()
    if row:
        return row['id']
    conn.execute(
        "INSERT INTO anios_escolares (nombre, activo) VALUES (?, 0)", [anio_texto]
    )
    conn.commit()
    return conn.execute(
        "SELECT id FROM anios_escolares WHERE nombre = ?", [anio_texto]
    ).fetchone()['id']

# ── COMPETENCIAS FUNDAMENTALES (Ord. 04-2023) ────────────────────────────────
COMPETENCIAS_FUNDAMENTALES = {
    "COM": "Comunicativa",
    "PL":  "Pensamiento Lógico",
    "EC":  "Ética y Ciudadana",
    "CT":  "Científica y Tecnológica",
}

TIPOS_ACTIVIDAD = {
    "tarea":          "Tarea",
    "prueba_corta":   "Prueba Corta",
    "prueba_parcial": "Prueba Parcial",
    "proyecto":       "Proyecto",
    "participacion":  "Participación",
    "examen":         "Examen",
}

# Materias básicas usan competencias fundamentales
MATERIAS_BASICAS = {
    "Lengua Española", "Inglés", "Matemática", "Ciencias Sociales",
    "Ciencias de la Naturaleza", "Formación Integral Humana y Religiosa",
    "Educación Física", "Idioma Inglés", "Idioma Francés",
}


def _es_materia_basica(materia):
    """Determina si una materia es básica (secuencia) o técnica (planificación)."""
    materia_norm = materia.strip()
    for mb in MATERIAS_BASICAS:
        if mb.lower() in materia_norm.lower() or materia_norm.lower() in mb.lower():
            return True
    return False


def _get_tipo_evaluacion(profesor):
    """Retorna 'basica' o 'tecnica' según el perfil del profesor."""
    tipo_doc = (profesor.get("tipo_docencia") or "basica").strip().lower()
    if tipo_doc == "tecnica":
        return "tecnica"
    return "basica"


# ── PORTAL DE EVALUACIÓN ─────────────────────────────────────────────────────

@evaluacion_bp.route("/evaluacion")
@login_required
def portal_evaluacion():
    # H5: redirigir v1 → v2 (portal_evaluacion_panel)
    return redirect(url_for("evaluacion_bp.portal_evaluacion_panel"))


# ── CRUD ACTIVIDADES ─────────────────────────────────────────────────────────

@evaluacion_bp.route("/api/evaluacion/actividades", methods=["GET"])
@login_required
def listar_actividades():
    prof = _get_profesor()
    if not prof:
        return jsonify({"error": "No autorizado"}), 403

    materia = request.args.get("materia", "")
    periodo = request.args.get("periodo", "")
    grado = request.args.get("grado", "")
    anio = request.args.get("anio", _anio_escolar_actual())

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        sql = """
            SELECT * FROM actividades_evaluacion
            WHERE docente_id = ? AND anio_escolar = ?
        """
        params = [prof["id"], anio]
        if materia:
            sql += " AND materia = ?"
            params.append(materia)
        if periodo:
            sql += " AND periodo = ?"
            params.append(_parse_periodo(periodo))
        if grado:
            sql += " AND grado = ?"
            params.append(grado)
        sql += " ORDER BY fecha_creacion DESC"
        rows = conn.execute(sql, params).fetchall()

    result = []
    for r in rows:
        d = dict(r)
        d["competencias"] = _json.loads(d.get("competencias") or "[]")
        result.append(d)
    return jsonify(result)


@evaluacion_bp.route("/api/evaluacion/actividades", methods=["POST"])
@login_required
def crear_actividad():
    prof = _get_profesor()
    if not prof:
        return jsonify({"error": "No autorizado"}), 403

    d = request.get_json(silent=True) or {}
    titulo = d.get("titulo", "").strip()
    tipo = d.get("tipo", "").strip()
    materia = d.get("materia", "").strip()
    grado = d.get("grado", "").strip()
    periodo = d.get("periodo", "").strip()
    peso = d.get("peso", 0)
    competencias = d.get("competencias", [])  # list of competencia codes
    mencion = d.get("mencion", "").strip()

    if not all([titulo, tipo, materia, grado, periodo]):
        return jsonify({"error": "Faltan campos obligatorios"}), 400

    try:
        peso = float(peso)
    except (ValueError, TypeError):
        peso = 0

    anio = _anio_escolar_actual()

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        anio_id = _get_anio_escolar_id(conn, anio)
        conn.execute("""
            INSERT INTO actividades_evaluacion
            (docente_id, materia, grado, mencion, periodo, anio_escolar_id, anio_escolar,
             tipo, titulo, descripcion, peso, valor_puntos, competencias)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            prof["id"], materia, grado, mencion, _parse_periodo(periodo),
            anio_id, anio,
            tipo, titulo, d.get("descripcion", ""), peso,
            int(peso) if peso else 10,
            _json.dumps(competencias),
        ))
        act_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()

    return jsonify({"ok": True, "id": act_id})


@evaluacion_bp.route("/api/evaluacion/actividades/<int:act_id>", methods=["DELETE"])
@login_required
def eliminar_actividad(act_id):
    prof = _get_profesor()
    if not prof:
        return jsonify({"error": "No autorizado"}), 403

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.execute(
            "DELETE FROM notas_actividad WHERE actividad_id=?", (act_id,))
        conn.execute(
            "DELETE FROM actividades_evaluacion WHERE id=? AND docente_id=?",
            (act_id, prof["id"]))
        conn.commit()

    return jsonify({"ok": True})


# ── NOTAS POR ACTIVIDAD ─────────────────────────────────────────────────────

@evaluacion_bp.route("/api/evaluacion/notas/<int:act_id>", methods=["GET"])
@login_required
def ver_notas_actividad(act_id):
    """Retorna las notas de todos los estudiantes para una actividad."""
    prof = _get_profesor()
    if not prof:
        return jsonify({"error": "No autorizado"}), 403

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row

        # Get activity info
        act = conn.execute(
            "SELECT * FROM actividades_evaluacion WHERE id=?", (act_id,)
        ).fetchone()
        if not act:
            return jsonify({"error": "Actividad no encontrada"}), 404

        # Get students for this grade/mention
        sql_est = """
            SELECT id, nombre, apellido, grado, curso, seccion
            FROM estudiantes WHERE condicion='ACTIVO' AND grado=?
        """
        params_est = [act["grado"]]
        if act["mencion"]:
            sql_est += " AND curso=?"
            params_est.append(act["mencion"])
        sql_est += " ORDER BY apellido, nombre"
        estudiantes = conn.execute(sql_est, params_est).fetchall()

        # Get existing grades
        notas = conn.execute(
            "SELECT est_id, nota FROM notas_actividad WHERE actividad_id=?",
            (act_id,)
        ).fetchall()
        notas_map = {n["est_id"]: n["nota"] for n in notas}

    result = []
    for e in estudiantes:
        result.append({
            "id": e["id"],
            "nombre": e["nombre"],
            "apellido": e["apellido"],
            "grado": e["grado"],
            "nota": notas_map.get(e["id"]),
        })

    return jsonify({
        "actividad": dict(act),
        "estudiantes": result,
    })


@evaluacion_bp.route("/api/evaluacion/notas/<int:act_id>", methods=["POST"])
@login_required
def guardar_notas_actividad(act_id):
    """Guarda/actualiza notas de una actividad para múltiples estudiantes."""
    prof = _get_profesor()
    if not prof:
        return jsonify({"error": "No autorizado"}), 403

    d = request.get_json(silent=True) or {}
    notas = d.get("notas", {})  # {estudiante_id: nota}

    if not notas:
        return jsonify({"error": "No hay notas para guardar"}), 400

    guardadas = 0
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        for est_id_str, nota in notas.items():
            est_id = int(est_id_str)
            try:
                nota_val = float(nota) if nota is not None and nota != "" else None
            except (ValueError, TypeError):
                continue

            if nota_val is None:
                conn.execute(
                    "DELETE FROM notas_actividad WHERE actividad_id=? AND est_id=?",
                    (act_id, est_id))
            else:
                conn.execute("""
                    INSERT INTO notas_actividad (actividad_id, est_id, nota, puntuacion_obtenida)
                    VALUES (?,?,?,?)
                    ON CONFLICT(actividad_id, est_id) DO UPDATE SET
                        nota=excluded.nota,
                        puntuacion_obtenida=excluded.puntuacion_obtenida
                """, (act_id, est_id, nota_val, nota_val))
                guardadas += 1

        conn.commit()
        cache_delete("api_datos_all")

    return jsonify({"ok": True, "guardadas": guardadas})


# ── RESUMEN POR COMPETENCIAS ────────────────────────────────────────────────

@evaluacion_bp.route("/api/evaluacion/resumen-competencias")
@login_required
def resumen_competencias():
    """Calcula nota por competencia para un grupo de estudiantes."""
    prof = _get_profesor()
    if not prof:
        return jsonify({"error": "No autorizado"}), 403

    materia = request.args.get("materia", "")
    grado = request.args.get("grado", "")
    periodo = request.args.get("periodo", "")
    mencion = request.args.get("mencion", "")
    anio = request.args.get("anio", _anio_escolar_actual())

    if not all([materia, grado, periodo]):
        return jsonify({"error": "Materia, grado y período requeridos"}), 400

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row

        # Get all activities for this materia/periodo
        sql_act = """
            SELECT id, titulo, tipo, peso, competencias
            FROM actividades_evaluacion
            WHERE docente_id=? AND materia=? AND grado=? AND periodo=? AND anio_escolar=?
              AND activa=1
        """
        params_act = [prof["id"], materia, grado, _parse_periodo(periodo), anio]
        if mencion:
            sql_act += " AND mencion=?"
            params_act.append(mencion)
        actividades = conn.execute(sql_act, params_act).fetchall()

        if not actividades:
            return jsonify({"estudiantes": [], "actividades": [], "competencias": {}})

        # Get students
        sql_est = "SELECT id, nombre, apellido FROM estudiantes WHERE condicion='ACTIVO' AND grado=?"
        params_est = [grado]
        if mencion:
            sql_est += " AND curso=?"
            params_est.append(mencion)
        sql_est += " ORDER BY apellido, nombre"
        estudiantes = conn.execute(sql_est, params_est).fetchall()

        # Get all grades
        act_ids = [a["id"] for a in actividades]
        if act_ids:
            placeholders = ",".join("?" * len(act_ids))
            notas_raw = conn.execute(f"""
                SELECT actividad_id, est_id, nota
                FROM notas_actividad WHERE actividad_id IN ({placeholders})
            """, act_ids).fetchall()
        else:
            notas_raw = []

    # Build lookup: {(act_id, est_id): nota}
    notas_map = {}
    for n in notas_raw:
        notas_map[(n["actividad_id"], n["est_id"])] = n["nota"]

    # Calculate per-student, per-competencia averages
    es_basica = _es_materia_basica(materia)
    acts_data = []
    for a in actividades:
        comps = _json.loads(a["competencias"] or "[]")
        acts_data.append({
            "id": a["id"], "titulo": a["titulo"], "tipo": a["tipo"],
            "peso": a["peso"], "competencias": comps,
        })

    result_estudiantes = []
    for e in estudiantes:
        est_id = e["id"]
        # Compute per-competencia scores
        comp_scores = {}  # {comp_code: [notas]}

        for act in acts_data:
            nota = notas_map.get((act["id"], est_id))
            if nota is None:
                continue
            for comp in act["competencias"]:
                comp_scores.setdefault(comp, []).append(nota)

        # Promedio por competencia → grades.py
        comp_averages = G.promediar_notas_por_competencia([
            {"competencias": act["competencias"],
             "nota": notas_map.get((act["id"], est_id))}
            for act in acts_data
        ])

        # Promedio general de competencias → grades.py
        promedio = G.promedio_competencias(comp_averages)

        result_estudiantes.append({
            "id": est_id,
            "nombre": e["nombre"],
            "apellido": e["apellido"],
            "competencias": comp_averages,
            "promedio": promedio,
            "estado": G.clasificar_nota(promedio),
            "color":  G.color_nota(promedio),
        })

    # Competencias used
    if es_basica:
        comps_usadas = COMPETENCIAS_FUNDAMENTALES
    else:
        # For técnicas, collect unique competencias from activities
        comps_usadas = {}
        for act in acts_data:
            for c in act["competencias"]:
                if c not in comps_usadas:
                    comps_usadas[c] = c  # Use code as label for custom

    return jsonify({
        "estudiantes": result_estudiantes,
        "actividades": acts_data,
        "competencias": comps_usadas,
        "es_basica": es_basica,
        "materia": materia,
        "periodo": periodo,
    })


# ── INFO DEL PROFESOR ────────────────────────────────────────────────────────

@evaluacion_bp.route("/api/evaluacion/retroalimentacion-ia", methods=["POST"])
@login_required
@rate_limited(max_calls=15, window=3600)
def retroalimentacion_ia():
    """
    Genera retroalimentación pedagógica IA para un estudiante basada en
    sus promedios por competencia. Usa LLaMA 3.3 70B vía Groq.
    """
    d = request.get_json(silent=True) or {}
    nombre       = str(d.get("nombre", "el estudiante"))[:60]
    materia      = str(d.get("materia", "la materia"))[:80]
    competencias = d.get("competencias", {})  # {codigo: promedio}
    promedio     = d.get("promedio")

    if not competencias:
        return jsonify({"error": "Sin datos de competencias"}), 400

    # Construir descripción de competencias para el prompt
    lineas = []
    LABELS = {
        "etica":         "Competencia Ética y Ciudadana",
        "comunicativa":  "Competencia Comunicativa",
        "pensamiento":   "Competencia Pensamiento Lógico, Creativo y Crítico",
        "resolucion":    "Competencia Resolución de Problemas",
        "cientifica":    "Competencia Científico-Tecnológica",
        "ambiental":     "Competencia Ambiental y de la Salud",
        "personal":      "Competencia Desarrollo Personal y Espiritual",
    }
    for cod, val in competencias.items():
        if val is None: continue
        label = LABELS.get(cod, cod)
        nivel = ("Destacado" if val >= 89 else "Satisfactorio" if val >= 80
                 else "Básico" if val >= 70 else "En Proceso" if val >= 60 else "Insuficiente")
        lineas.append(f"- {label}: {val} ({nivel})")

    if not lineas:
        return jsonify({"error": "Sin notas registradas"}), 400

    prompt = f"""Eres un docente especialista en evaluación por competencias del bachillerato dominicano (MINERD, Ord. 04-2023).

Estudiante: {nombre}
Materia: {materia}
Promedio general: {promedio if promedio else 'N/A'}

Resultados por competencia:
{chr(10).join(lineas)}

Genera una retroalimentación pedagógica breve (máximo 4 oraciones) que:
1. Destaque la competencia más fuerte del estudiante
2. Identifique la competencia que más necesita refuerzo
3. Proponga UNA estrategia concreta de mejora
4. Use un tono constructivo y motivador, apropiado para bachillerato en artes

Responde SOLO con el párrafo de retroalimentación, sin títulos, sin bullets."""

    try:
        texto = generar_con_fallback(prompt, max_tokens=250, temperature=0.6)
        return jsonify({"ok": True, "retroalimentacion": texto})
    except Exception as ex:
        logger.warning(f"[EVAL-IA] Error IA: {ex}")
        return jsonify({"error": "Servicio IA no disponible temporalmente"}), 503


@evaluacion_bp.route("/api/evaluacion/informe-pdf")
@login_required
def informe_competencias_pdf():
    """Genera HTML imprimible del informe de competencias."""
    from flask import make_response
    import datetime

    materia = request.args.get("materia", "")
    grado   = request.args.get("grado", "")
    periodo = request.args.get("periodo", "")
    mencion = request.args.get("mencion", "")
    anio    = request.args.get("anio", _anio_escolar_actual())

    if not all([materia, grado, periodo]):
        return "Faltan parámetros: materia, grado, periodo", 400

    # Reusar la lógica del endpoint resumen (mismo request context, mismos args)
    data = resumen_competencias().get_json()

    centro = _get_config_centro()
    ahora  = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

    LABELS_COMP = {
        "etica":"Ética y Ciudadana","comunicativa":"Comunicativa",
        "pensamiento":"Pensamiento Lógico","resolucion":"Resolución de Problemas",
        "cientifica":"Científico-Tecnológica","ambiental":"Amb. y Salud","personal":"Des. Personal",
    }
    NIVEL_COLOR = {"destacado":"#4dffb4","satisfactorio":"#60b8f0","basico":"#c8f060",
                   "en_proceso":"#f7b731","insuficiente":"#ff6b6b"}

    comps     = data.get("competencias", {})
    comp_keys = list(comps.keys())
    estuds    = data.get("estudiantes", [])

    filas = ""
    for i, e in enumerate(estuds, 1):
        nivel    = e.get("estado", "")
        col_fin  = NIVEL_COLOR.get(nivel, "#aaa")
        celdas   = "".join(
            f'<td style="text-align:center;color:{"#4dffb4" if (e["competencias"].get(k) or 0)>=89 else "#f7b731" if (e["competencias"].get(k) or 0)>=70 else "#ff6b6b"}">'
            f'{e["competencias"].get(k) or "—"}</td>'
            for k in comp_keys
        )
        filas += (
            f'<tr><td>{i}</td>'
            f'<td><b>{e["apellido"]}, {e["nombre"]}</b></td>'
            f'{celdas}'
            f'<td style="text-align:center;font-weight:800;color:{col_fin}">{e["promedio"] or "—"}</td>'
            f'<td style="text-align:center;font-size:10px;color:{col_fin}">{nivel.replace("_"," ").title()}</td>'
            f'</tr>'
        )

    th_comps = "".join(f'<th>{LABELS_COMP.get(k, k)}</th>' for k in comp_keys)

    html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>
body{{font-family:Arial,sans-serif;font-size:11pt;color:#111;margin:20px;}}
h1{{font-size:16pt;margin-bottom:2px;}} .sub{{font-size:10pt;color:#666;margin-bottom:16px;}}
table{{width:100%;border-collapse:collapse;}} thead th{{background:#111;color:#c8f060;
padding:7px 8px;font-size:9pt;text-align:left;}}
tbody tr:nth-child(even){{background:#f9f9f9;}}
td{{padding:6px 8px;border-bottom:1px solid #eee;font-size:9pt;vertical-align:middle;}}
@page{{margin:12mm;size:A4 landscape;}} @media print{{.no-print{{display:none;}}}}
</style></head><body>
<h1>Informe de Evaluación por Competencias</h1>
<div class="sub">
  {centro.get("nombre","C.E. Benito Juárez")} · Materia: <b>{materia}</b> · Grado: <b>{grado}</b>
  {f'· Mención: <b>{mencion}</b>' if mencion else ''} · Período: <b>{periodo}</b> · Año: <b>{anio}</b><br>
  Generado: {ahora} · {len(estuds)} estudiantes
</div>
<button class="no-print" onclick="window.print()"
  style="margin-bottom:14px;padding:7px 18px;background:#111;color:#c8f060;border:1px solid #333;
         border-radius:6px;cursor:pointer;">🖨 Imprimir / Guardar PDF</button>
<table><thead><tr>
  <th>#</th><th>Estudiante</th>{th_comps}<th>Promedio</th><th>Nivel</th>
</tr></thead><tbody>{filas}</tbody></table>
</body></html>"""

    resp = make_response(html)
    resp.headers["Content-Type"] = "text/html; charset=utf-8"
    return resp



@evaluacion_bp.route("/api/evaluacion/mi-perfil")
@login_required
def mi_perfil_evaluacion():
    prof = _get_profesor()
    if not prof:
        return jsonify({"error": "No autorizado"}), 403

    tipo = _get_tipo_evaluacion(prof)
    alcance = _resolver_alcance_profesor(prof)

    return jsonify({
        "profesor": {
            "id": prof["id"],
            "nombre": prof["nombre"],
            "materia": prof.get("materia", ""),
            "grado": prof.get("grado", ""),
            "mencion": prof.get("mencion", ""),
            "tipo_docencia": prof.get("tipo_docencia", "basica"),
        },
        "tipo_evaluacion": tipo,
        "alcance": alcance,
        "competencias": COMPETENCIAS_FUNDAMENTALES if tipo == "basica" else {},
        "tipos_actividad": TIPOS_ACTIVIDAD,
    })


# ═══════════════════════════════════════════════════════════════════
# SISTEMA DE EVALUACIÓN v2 — MODELO DE PUNTUACIÓN LIBRE (Ord.04-2023)
# ═══════════════════════════════════════════════════════════════════

@evaluacion_bp.route("/evaluacion/panel")
@login_required
def panel_asignaciones():
    """Vista principal del panel de evaluación v2."""
    prof = _get_profesor()
    if not prof:
        return redirect("/")
    materia  = request.args.get("materia", prof.get("materia", ""))
    grado    = request.args.get("grado", prof.get("grado", ""))
    mencion  = request.args.get("mencion", prof.get("mencion", ""))
    periodo  = request.args.get("periodo", _periodo_actual(), type=int)

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        ae_row = conn.execute(
            "SELECT id FROM anios_escolares WHERE activo=1 LIMIT 1"
        ).fetchone()
        anio_id = ae_row["id"] if ae_row else 1

    return render_template(
        "evaluacion/panel_asignaciones.html",
        materia=materia,
        grado=grado,
        mencion=mencion,
        periodo_activo=periodo,
        anio_escolar_id=anio_id,
        usuario=get_usuario(),
    )


TIPOS_ACTIVIDAD_V2 = {
    "tarea":         "Tarea",
    "proyecto":      "Proyecto",
    "participacion": "Participación",
    "prueba":        "Prueba",
    "exposicion":    "Exposición",
    "otro":          "Otro",
}


@evaluacion_bp.route("/evaluacion/actividades/periodo-status")
@login_required
def periodo_status():
    """
    GET /evaluacion/actividades/periodo-status
    Retorna puntos usados/disponibles + actividades del período.
    Params: materia, docente_id (opcional), periodo, anio_escolar_id (opcional)
    """
    prof = _get_profesor()
    if not prof:
        return jsonify({"error": "No autorizado"}), 403

    materia        = request.args.get("materia", "").strip()
    periodo_raw    = request.args.get("periodo", "1")
    anio_esc_id    = request.args.get("anio_escolar_id", 1, type=int)
    docente_id     = request.args.get("docente_id", prof["id"], type=int)

    if not materia:
        return jsonify({"error": "Parámetro 'materia' requerido"}), 400

    try:
        periodo = _parse_periodo(periodo_raw)
    except (ValueError, AttributeError):
        return jsonify({"error": "Período inválido"}), 400

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row

        actividades = conn.execute("""
            SELECT id, titulo, tipo, valor_puntos, fecha_entrega, activa
            FROM actividades_evaluacion
            WHERE materia = ? AND docente_id = ?
              AND periodo = ? AND anio_escolar_id = ?
              AND activa = 1
            ORDER BY fecha_creacion
        """, [materia, docente_id, periodo, anio_esc_id]).fetchall()

        pts_usados = sum(a['valor_puntos'] for a in actividades)

    puede_cerrar = pts_usados >= 1
    advertencia  = None
    if pts_usados < TOTAL_PUNTOS_PERIODO:
        advertencia = (f"El período tiene {pts_usados}/100 pts asignados. "
                       f"Se recomienda completar hasta 100 pts.")

    return jsonify({
        "periodo":            periodo,
        "total_posible":      TOTAL_PUNTOS_PERIODO,
        "puntos_usados":      pts_usados,
        "puntos_disponibles": TOTAL_PUNTOS_PERIODO - pts_usados,
        "actividades": [
            {
                "id":          a["id"],
                "titulo":      a["titulo"],
                "tipo":        a["tipo"],
                "valor_puntos": a["valor_puntos"],
            }
            for a in actividades
        ],
        "puede_cerrar": puede_cerrar,
        "advertencia":  advertencia,
    })


@evaluacion_bp.route("/evaluacion/actividades/crear", methods=["POST"])
@login_required
def crear_actividad_v2():
    """
    POST /evaluacion/actividades/crear
    Crea actividad con validación de puntos (no superar 100/período).
    """
    prof = _get_profesor()
    if not prof:
        return jsonify({"error": "No autorizado"}), 403

    d = request.get_json(silent=True) or {}

    materia         = str(d.get("materia", "")).strip()
    titulo          = str(d.get("titulo", "")).strip()
    tipo            = str(d.get("tipo", "tarea")).strip()
    valor_puntos    = d.get("valor_puntos")
    periodo_raw     = d.get("periodo", 1)
    anio_esc_id     = int(d.get("anio_escolar_id", 1))
    planificacion_id = d.get("planificacion_id")
    competencia_id  = d.get("competencia_id")
    fecha_entrega   = d.get("fecha_entrega")
    grado           = str(d.get("grado", "")).strip()
    mencion         = str(d.get("mencion", "")).strip()
    descripcion     = str(d.get("descripcion", "")).strip()

    if not materia or not titulo:
        return jsonify({"error": "Campos 'materia' y 'titulo' son requeridos"}), 400

    if not planificacion_id:
        return jsonify({"error": "Debe vincular la actividad a una planificación"}), 400

    if tipo not in TIPOS_ACTIVIDAD_V2:
        return jsonify({"error": f"Tipo inválido. Opciones: {list(TIPOS_ACTIVIDAD_V2)}"}), 400

    try:
        valor_puntos = int(valor_puntos)
        periodo      = _parse_periodo(periodo_raw)
    except (TypeError, ValueError):
        return jsonify({"error": "valor_puntos y periodo deben ser enteros válidos"}), 400

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row

        validacion = validar_puntos_actividad(
            conn, materia, prof["id"], periodo, anio_esc_id, valor_puntos
        )
        if not validacion['valido']:
            return jsonify({"error": validacion['mensaje']}), 400

        ae_row = conn.execute(
            "SELECT nombre FROM anios_escolares WHERE id = ?", [anio_esc_id]
        ).fetchone()
        anio_texto = ae_row['nombre'] if ae_row else _anio_escolar_actual()

        conn.execute("""
            INSERT INTO actividades_evaluacion
                (docente_id, materia, grado, mencion, periodo,
                 anio_escolar_id, anio_escolar, tipo, titulo, descripcion,
                 planificacion_id, competencia_id, valor_puntos, fecha_entrega, activa)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)
        """, [
            prof["id"], materia, grado, mencion, periodo,
            anio_esc_id, anio_texto, tipo, titulo, descripcion,
            planificacion_id, competencia_id, valor_puntos, fecha_entrega,
        ])
        act_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()

    return jsonify({
        "ok":             True,
        "id":             act_id,
        "mensaje":        validacion['mensaje'],
        "puntos_usados":  validacion['puntos_usados'],
        "puntos_disponibles": validacion['puntos_disponibles'],
    })


@evaluacion_bp.route("/evaluacion/actividades/<int:actividad_id>/calificar",
                     methods=["GET"])
@login_required
def calificar_actividad_get(actividad_id):
    """
    GET /evaluacion/actividades/<id>/calificar
    Vista para calificar a todos los estudiantes de una actividad.
    """
    prof = _get_profesor()
    if not prof:
        return redirect("/")

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row

        act = conn.execute(
            "SELECT * FROM actividades_evaluacion WHERE id=? AND docente_id=?",
            [actividad_id, prof["id"]]
        ).fetchone()
        if not act:
            return "Actividad no encontrada o sin permiso", 404

        sql_est = """
            SELECT id, nombre, apellido, grado, curso, seccion
            FROM estudiantes WHERE condicion='ACTIVO'
        """
        params_est = []
        if act["grado"]:
            sql_est += " AND grado=?"
            params_est.append(act["grado"])
        if act["mencion"]:
            sql_est += " AND curso=?"
            params_est.append(act["mencion"])
        sql_est += " ORDER BY apellido, nombre"
        estudiantes = conn.execute(sql_est, params_est).fetchall()

        notas_raw = conn.execute(
            "SELECT est_id, puntuacion_obtenida, nota FROM notas_actividad WHERE actividad_id=?",
            [actividad_id]
        ).fetchall()
        notas_map = {n["est_id"]: n["puntuacion_obtenida"] or n["nota"] for n in notas_raw}

    return render_template(
        "evaluacion/calificar_actividad.html",
        actividad=dict(act),
        estudiantes=[dict(e) for e in estudiantes],
        notas_map=notas_map,
        valor_puntos=act["valor_puntos"],
        usuario=get_usuario(),
    )


@evaluacion_bp.route("/evaluacion/actividades/<int:actividad_id>/calificar",
                     methods=["POST"])
@login_required
def calificar_actividad_post(actividad_id):
    """
    POST /evaluacion/actividades/<id>/calificar
    Body: JSON array [{est_id, puntuacion_obtenida, observacion}]
    """
    prof = _get_profesor()
    if not prof:
        return jsonify({"error": "No autorizado"}), 403

    items = request.get_json(silent=True)
    if not isinstance(items, list):
        return jsonify({"error": "Se esperaba un array JSON"}), 400

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row

        act = conn.execute(
            "SELECT valor_puntos FROM actividades_evaluacion WHERE id=? AND docente_id=?",
            [actividad_id, prof["id"]]
        ).fetchone()
        if not act:
            return jsonify({"error": "Actividad no encontrada o sin permiso"}), 404

        pts_max = act["valor_puntos"]
        guardadas = 0

        for item in items:
            try:
                est_id  = int(item["est_id"])
                pts_obt = float(item.get("puntuacion_obtenida", 0) or 0)
                obs     = str(item.get("observacion", "") or "").strip()
            except (KeyError, TypeError, ValueError):
                continue

            pts_obt = max(0.0, min(float(pts_max), pts_obt))

            conn.execute("""
                INSERT INTO notas_actividad
                    (actividad_id, est_id, nota, puntuacion_obtenida,
                     puntuacion_maxima, observacion)
                VALUES (?,?,?,?,?,?)
                ON CONFLICT(actividad_id, est_id) DO UPDATE SET
                    nota=excluded.nota,
                    puntuacion_obtenida=excluded.puntuacion_obtenida,
                    puntuacion_maxima=excluded.puntuacion_maxima,
                    observacion=excluded.observacion,
                    fecha_registro=CURRENT_TIMESTAMP
            """, [actividad_id, est_id, pts_obt, pts_obt, pts_max, obs])
            guardadas += 1

        conn.commit()
        cache_delete("api_datos_all")

    return jsonify({"ok": True, "guardadas": guardadas})


@evaluacion_bp.route("/evaluacion/periodo/<int:periodo>/resumen")
@login_required
def resumen_periodo_v2(periodo):
    """
    GET /evaluacion/periodo/<periodo>/resumen
    Tabla de estudiantes con notas parciales del período.
    """
    prof = _get_profesor()
    if not prof:
        return redirect("/")

    materia      = request.args.get("materia", "").strip()
    anio_esc_id  = request.args.get("anio_escolar_id", 1, type=int)

    if not materia:
        return "Parámetro 'materia' requerido", 400

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row

        actividades = conn.execute("""
            SELECT id, titulo, tipo, valor_puntos
            FROM actividades_evaluacion
            WHERE materia=? AND docente_id=? AND periodo=?
              AND anio_escolar_id=? AND activa=1
            ORDER BY fecha_creacion
        """, [materia, prof["id"], periodo, anio_esc_id]).fetchall()

        pts_usados = sum(a["valor_puntos"] for a in actividades)

        act_ids = [a["id"] for a in actividades]
        estudiantes_ids = []
        if act_ids:
            ph = ",".join("?" * len(act_ids))
            rows = conn.execute(
                f"SELECT DISTINCT est_id FROM notas_actividad WHERE actividad_id IN ({ph})",
                act_ids
            ).fetchall()
            estudiantes_ids = [r["est_id"] for r in rows]

        est_data = []
        for est_id in estudiantes_ids:
            est_row = conn.execute(
                "SELECT id, nombre, apellido, grado FROM estudiantes WHERE id=?",
                [est_id]
            ).fetchone()
            if not est_row:
                continue

            notas_act = {}
            for act in actividades:
                n = conn.execute(
                    "SELECT puntuacion_obtenida, nota FROM notas_actividad WHERE actividad_id=? AND est_id=?",
                    [act["id"], est_id]
                ).fetchone()
                notas_act[act["id"]] = (n["puntuacion_obtenida"] or n["nota"]) if n else None

            pts_obt = sum(v or 0 for v in notas_act.values())
            nota_parcial = round((pts_obt / pts_usados) * 100, 1) if pts_usados > 0 else None
            estado = get_estado_estudiante_periodo(nota_parcial)

            est_data.append({
                "id":          est_id,
                "nombre":      est_row["nombre"],
                "apellido":    est_row["apellido"],
                "grado":       est_row["grado"],
                "notas":       notas_act,
                "pts_obtenidos": pts_obt,
                "nota_parcial": nota_parcial,
                "estado":      estado,
            })

    return render_template(
        "evaluacion/resumen_periodo.html",
        periodo=periodo,
        materia=materia,
        actividades=[dict(a) for a in actividades],
        estudiantes=est_data,
        pts_usados=pts_usados,
        anio_escolar_id=anio_esc_id,
        usuario=get_usuario(),
    )


@evaluacion_bp.route("/evaluacion/periodo/<int:periodo>/cerrar", methods=["POST"])
@login_required
def cerrar_periodo_route(periodo):
    """
    POST /evaluacion/periodo/<periodo>/cerrar
    Ejecuta el cierre del período: calcula y guarda notas definitivas.
    Roles permitidos: profesor, directora, coordinador_*
    """
    u = get_usuario()
    rol = _normalizar_rol(u.get("rol", ""))
    roles_permitidos = {"profesor", "directora", "coordinador_general",
                        "coordinador_primer_ciclo", "coordinador_segundo_ciclo"}
    if rol not in roles_permitidos:
        return jsonify({"error": "Sin permiso para cerrar períodos"}), 403

    prof = _get_profesor()
    if not prof:
        return jsonify({"error": "No autorizado"}), 403

    d = request.get_json(silent=True) or {}
    materia     = str(d.get("materia", "")).strip()
    anio_esc_id = int(d.get("anio_escolar_id", 1))
    forzar      = bool(d.get("forzar", False))

    if not materia:
        return jsonify({"error": "Campo 'materia' requerido"}), 400

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        resultado = cerrar_periodo(conn, materia, prof["id"], periodo, anio_esc_id,
                                   forzar=forzar)

    if resultado.get("exitoso"):
        _audit(u["id"], "cerrar_periodo",
               f"materia={materia} periodo={periodo} procesados={resultado['procesados']}")

    return jsonify(resultado)


# ══════════════════════════════════════════════════════════════════════════════
#  H3 — Motor de Evaluación por Competencias (CE)
# ══════════════════════════════════════════════════════════════════════════════

@evaluacion_bp.route("/api/evaluacion/ce/<materia>/competencias")
@login_required
def listar_competencias_materia(materia):
    """GET lista de CEs definidas para una materia."""
    import urllib.parse
    materia = urllib.parse.unquote(materia)
    anio = _anio_escolar_actual()
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        ces = conn.execute(
            "SELECT numero, descripcion, periodo_eval, activa "
            "FROM competencias_materia WHERE materia=? AND anio_escolar=? ORDER BY numero",
            (materia, anio)
        ).fetchall()
    return jsonify([dict(r) for r in ces])


@evaluacion_bp.route("/api/evaluacion/ce/configurar", methods=["POST"])
@login_required
def configurar_competencias():
    """
    POST — guarda/actualiza la lista de CEs de una materia.
    Solo coordinadores y directora.
    Body: {materia, ces: [{numero, descripcion, periodo_eval}]}
    """
    u = get_usuario()
    if not u:
        return jsonify({"error": "No autenticado"}), 401

    d = request.get_json(silent=True) or {}
    materia = (d.get("materia") or "").strip()
    ces     = d.get("ces", [])
    if not materia or not ces:
        return jsonify({"error": "Campos requeridos: materia, ces"}), 400

    from core.helpers import sembrar_competencias_materia
    anio = _anio_escolar_actual()
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        # Desactivar las anteriores si se reemplaza
        conn.execute(
            "UPDATE competencias_materia SET activa=0 WHERE materia=? AND anio_escolar=?",
            (materia, anio)
        )
        for ce in ces:
            conn.execute(
                "INSERT INTO competencias_materia "
                "(materia, numero, descripcion, periodo_eval, anio_escolar, activa, orden) "
                "VALUES (?,?,?,?,?,1,?) "
                "ON CONFLICT(materia, numero, anio_escolar) "
                "DO UPDATE SET descripcion=excluded.descripcion, "
                "periodo_eval=excluded.periodo_eval, activa=1",
                (materia, ce.get("numero"), ce.get("descripcion", ""),
                 ce.get("periodo_eval", "P1"), anio, ce.get("numero", 0))
            )
        conn.commit()
    return jsonify({"ok": True, "guardadas": len(ces)})


@evaluacion_bp.route("/api/evaluacion/ce/nota", methods=["POST"])
@login_required
@rate_limited(max_calls=120, window=60)
def guardar_nota_ce():
    """
    POST — guarda la nota de una CE para un estudiante.
    Body: {estudiante_id, materia, ce_numero, nota, anio_escolar?}
    o batch: [{...}, {...}]
    """
    prof = _get_profesor()
    if not prof:
        return jsonify({"error": "No autenticado"}), 401

    data = request.get_json(silent=True) or {}
    registros = data if isinstance(data, list) else [data]
    anio = _anio_escolar_actual()

    guardados  = 0
    errores    = []
    resultados = []

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        for item in registros:
            est_id    = item.get("estudiante_id")
            materia   = (item.get("materia") or "").strip()
            ce_numero = item.get("ce_numero")
            nota      = item.get("nota")
            item_anio = item.get("anio_escolar") or anio

            if not all([est_id, materia, ce_numero is not None, nota is not None]):
                errores.append(f"Datos incompletos: {item}")
                continue
            try:
                nota = float(nota)
                if not (0 <= nota <= 100):
                    raise ValueError
            except (ValueError, TypeError):
                errores.append(f"Nota inválida: {nota}")
                continue

            try:
                from core.helpers import guardar_nota_ce_y_recalcular
                res = guardar_nota_ce_y_recalcular(
                    conn, est_id, prof["id"], materia, int(ce_numero), nota, item_anio
                )
                conn.commit()
                guardados += 1
                resultados.append({"estudiante_id": est_id, "ce": ce_numero, **res})
            except Exception as _e:
                errores.append(str(_e))

    return jsonify({"ok": True, "guardados": guardados,
                    "errores": errores, "resultados": resultados})


@evaluacion_bp.route("/api/evaluacion/ce/notas/<int:est_id>/<path:materia>")
@login_required
def notas_ce_estudiante(est_id, materia):
    """GET — todas las CE notas de un estudiante en una materia."""
    import urllib.parse
    materia = urllib.parse.unquote(materia)
    anio = _anio_escolar_actual()
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        notas = conn.execute(
            "SELECT nc.ce_numero, nc.nota, nc.periodo, cm.descripcion "
            "FROM notas_competencias_ce nc "
            "LEFT JOIN competencias_materia cm "
            "  ON cm.materia=nc.materia AND cm.numero=nc.ce_numero AND cm.anio_escolar=nc.anio_escolar "
            "WHERE nc.estudiante_id=? AND nc.materia=? AND nc.anio_escolar=?",
            (est_id, materia, anio)
        ).fetchall()
        from core.helpers import calcular_cf_por_ce
        cf_data = calcular_cf_por_ce(conn, est_id, materia, anio)

    return jsonify({
        "notas_ce": [dict(r) for r in notas],
        "calculo": cf_data,
    })


@evaluacion_bp.route("/api/evaluacion/ce/registro/<path:materia>")
@login_required
def registro_ce_materia(materia):
    """
    GET — vista registro: todos los estudiantes con sus CEs para una materia.
    Equivalente digital del papel que entrega el profesor a coordinación.
    Query params: ?grado=4to&mencion=MULTIMEDIA
    """
    import urllib.parse
    materia = urllib.parse.unquote(materia)
    grado   = request.args.get("grado", "")
    mencion = request.args.get("mencion", "")
    anio    = _anio_escolar_actual()
    prof    = _get_profesor()
    if not prof:
        return jsonify({"error": "No autenticado"}), 401

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row

        # CEs de la materia
        ces = conn.execute(
            "SELECT numero, descripcion, periodo_eval FROM competencias_materia "
            "WHERE materia=? AND anio_escolar=? AND activa=1 ORDER BY numero",
            (materia, anio)
        ).fetchall()

        # Estudiantes del grado/mención
        q = "SELECT id, nombre, apellido, grado, curso FROM estudiantes WHERE 1=1"
        params = []
        if grado:
            q += " AND LOWER(grado) LIKE ?"
            params.append(f"%{grado.lower()}%")
        if mencion:
            q += " AND UPPER(curso) LIKE ?"
            params.append(f"%{mencion.upper()}%")
        q += " ORDER BY apellido, nombre"
        estudiantes = conn.execute(q, params).fetchall()

        # Notas CE de todos los estudiantes
        notas_bulk = conn.execute(
            "SELECT estudiante_id, ce_numero, nota FROM notas_competencias_ce "
            "WHERE materia=? AND anio_escolar=?",
            (materia, anio)
        ).fetchall()
        notas_idx = {}  # {est_id: {ce_numero: nota}}
        for r in notas_bulk:
            eid = r["estudiante_id"]; ce = r["ce_numero"]; nota = r["nota"]
            notas_idx.setdefault(eid, {})[ce] = nota

        from core.helpers import calcular_cf_por_ce
        registros = []
        for est in estudiantes:
            eid = est["id"]
            cf_data = calcular_cf_por_ce(conn, eid, materia, anio)
            registros.append({
                "id":      eid,
                "nombre":  f"{est['nombre']} {est['apellido']}",
                "grado":   est["grado"],
                "curso":   est["curso"],
                "ces":     notas_idx.get(eid, {}),
                "p1":      cf_data["p1"],
                "p2":      cf_data["p2"],
                "p3":      cf_data["p3"],
                "p4":      cf_data["p4"],
                "cf":      cf_data["cf"],
                "completo": cf_data["cf_completo"],
            })

    return jsonify({
        "materia":      materia,
        "competencias": [dict(c) for c in ces],
        "estudiantes":  registros,
    })
