# -*- coding: utf-8 -*-
"""Blueprint: asignaciones"""

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
from core.helpers import _construir_prompt_asignacion, _nota_estado, _resolver_alcance_profesor
from core import grades as G
from core.ia import _get_groq_client, groq_client, construir_prompt, construir_prompt_planificacion, construir_prompt_rubrica, construir_prompt_estrategia
from core.excel import _parsear_boletin_bj, _buscar_o_crear_estudiante, _detectar_mencion_listado, _limpiar_nota
from core.pdf import _generar_pdf_acuerdo

logger = logging.getLogger("axula")

asignaciones_bp = Blueprint("asignaciones_bp", __name__)

@asignaciones_bp.route("/api/asignaciones/generar-criterios", methods=["POST"])
@login_required
def asignaciones_generar_criterios():
    """
    Llama a Groq/IA para generar título, descripción y criterios de evaluación
    diferenciados según materia, tipo y mención. No guarda nada — solo sugiere.
    """
    u = get_usuario()
    data    = request.get_json(force=True) or {}
    materia = (data.get("materia") or "").strip()
    tipo    = (data.get("tipo") or "tarea").strip()
    grado   = (data.get("grado") or u.get("grado") or "4to").strip()
    mencion = (data.get("mencion") or u.get("mencion") or "MULTIMEDIA").strip().upper()

    if not materia:
        return jsonify({"ok": False, "error": "Materia requerida"}), 400

    prompt = _construir_prompt_asignacion(tipo, materia, grado, mencion)

    try:
        import os, json as _json
        groq_key = os.environ.get("GROQ_API_KEY", "")
        if not groq_key:
            # Sin IA: devolver estructura vacía con placeholder
            return jsonify({
                "ok": True,
                "ia": False,
                "titulo": f"{tipo.capitalize()} — {materia}",
                "descripcion": f"Describe aquí la actividad de {tipo} para {materia}.",
                "criterios": [
                    {"nombre": "Criterio 1", "puntaje_max": 25, "descripcion": "Descripción del criterio"},
                    {"nombre": "Criterio 2", "puntaje_max": 25, "descripcion": "Descripción del criterio"},
                    {"nombre": "Criterio 3", "puntaje_max": 25, "descripcion": "Descripción del criterio"},
                    {"nombre": "Criterio 4", "puntaje_max": 25, "descripcion": "Descripción del criterio"},
                ]
            })

        import urllib.request as _req
        payload = _json.dumps({
            "model": "llama3-8b-8192",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 900,
        }).encode()
        req = _req.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=payload,
            headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
            method="POST"
        )
        with _req.urlopen(req, timeout=20) as resp:
            result = _json.loads(resp.read())
        raw = result["choices"][0]["message"]["content"].strip()
        # Limpiar posibles backticks
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        ia_data = _json.loads(raw.strip())
        return jsonify({"ok": True, "ia": True, **ia_data})
    except Exception as e:
        logger.error(f"[asignaciones_generar_criterios] error IA: {e}")
        return jsonify({"ok": False, "error": "Error al generar criterios. Intenta de nuevo."}), 500


@asignaciones_bp.route("/api/asignaciones", methods=["GET"])
@login_required
def asignaciones_listar():
    """Lista asignaciones del profesor autenticado, filtrables por materia/periodo/estado."""
    u       = get_usuario()
    materia = request.args.get("materia", "").strip()
    periodo = request.args.get("periodo", "").strip()
    estado  = request.args.get("estado", "").strip()

    q      = "SELECT * FROM asignaciones WHERE profesor_id=?"
    params = [u["id"]]
    if materia: q += " AND materia=?";  params.append(materia)
    if periodo: q += " AND periodo=?";  params.append(periodo)
    if estado:  q += " AND estado=?";   params.append(estado)
    q += " ORDER BY creado_en DESC"

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        rows = [dict(r) for r in conn.execute(q, params).fetchall()]

    import json as _json
    for r in rows:
        try:
            r["criterios"] = _json.loads(r["criterios"] or "[]")
        except Exception:
            r["criterios"] = []

    return jsonify({"ok": True, "asignaciones": rows})


@asignaciones_bp.route("/api/asignaciones", methods=["POST"])
@login_required
def asignaciones_crear():
    """Crea una nueva asignación (en estado borrador o publicada)."""
    u    = get_usuario()
    data = request.get_json(force=True) or {}

    import json as _json
    titulo      = (data.get("titulo") or "").strip()
    descripcion = (data.get("descripcion") or "").strip()
    materia     = (data.get("materia") or "").strip()
    grado       = (data.get("grado") or u.get("grado") or "4to").strip()
    mencion     = (data.get("mencion") or u.get("mencion") or "MULTIMEDIA").strip().upper()
    tipo        = (data.get("tipo") or "tarea").strip()
    criterios   = data.get("criterios", [])
    puntaje     = float(data.get("puntaje_total") or 100)
    fecha_ent   = (data.get("fecha_entrega") or "").strip() or None
    periodo     = (data.get("periodo") or "P1").strip()
    estado      = (data.get("estado") or "borrador").strip()

    if not titulo or not materia:
        return jsonify({"ok": False, "error": "Título y materia son requeridos"}), 400

    criterios_json = _json.dumps(criterios, ensure_ascii=False)

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        cur = conn.execute(
            """INSERT INTO asignaciones
               (profesor_id, materia, grado, mencion, tipo, titulo, descripcion,
                criterios, puntaje_total, fecha_entrega, periodo, estado)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (u["id"], materia, grado, mencion, tipo, titulo, descripcion,
             criterios_json, puntaje, fecha_ent, periodo, estado)
        )
        new_id = cur.lastrowid

    return jsonify({"ok": True, "id": new_id}), 201


@asignaciones_bp.route("/api/asignaciones/<int:asig_id>", methods=["PATCH"])
@login_required
def asignaciones_actualizar(asig_id):
    """Actualiza una asignación existente del profesor (puede publicar o cerrar)."""
    u    = get_usuario()
    data = request.get_json(force=True) or {}

    import json as _json
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        row = conn.execute(
            "SELECT * FROM asignaciones WHERE id=? AND profesor_id=?",
            (asig_id, u["id"])
        ).fetchone()
        if not row:
            return jsonify({"ok": False, "error": "No encontrada"}), 404

        campos = []
        vals   = []
        for campo in ["titulo", "descripcion", "materia", "tipo", "periodo",
                      "fecha_entrega", "puntaje_total", "estado"]:
            if campo in data:
                campos.append(f"{campo}=?")
                vals.append(data[campo])
        if "criterios" in data:
            campos.append("criterios=?")
            vals.append(_json.dumps(data["criterios"], ensure_ascii=False))
        if not campos:
            return jsonify({"ok": False, "error": "Nada que actualizar"}), 400
        vals.append(asig_id)
        conn.execute(f"UPDATE asignaciones SET {','.join(campos)} WHERE id=?", vals)

    return jsonify({"ok": True})


@asignaciones_bp.route("/api/asignaciones/<int:asig_id>", methods=["DELETE"])
@login_required
def asignaciones_eliminar(asig_id):
    """Elimina una asignación (solo si está en borrador o la crea el mismo profesor)."""
    u = get_usuario()
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        row = conn.execute(
            "SELECT estado FROM asignaciones WHERE id=? AND profesor_id=?",
            (asig_id, u["id"])
        ).fetchone()
        if not row:
            return jsonify({"ok": False, "error": "No encontrada"}), 404
        conn.execute("DELETE FROM entregas_asignacion WHERE asignacion_id=?", (asig_id,))
        conn.execute("DELETE FROM asignaciones WHERE id=?", (asig_id,))
    return jsonify({"ok": True})


@asignaciones_bp.route("/api/asignaciones/<int:asig_id>/calificar", methods=["POST"])
@login_required
def asignaciones_calificar(asig_id):
    """
    Registra o actualiza la nota de uno o varios estudiantes para una asignación.
    Body: {"entregas": [{"estudiante_id": X, "nota": 85, "observacion": "...", "entregado": true}]}
    Si entregado=false la nota queda NULL y se registra como "No entregó".
    """
    u    = get_usuario()
    data = request.get_json(force=True) or {}
    entregas = data.get("entregas", [])

    if not entregas:
        return jsonify({"ok": False, "error": "Sin entregas"}), 400

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        asig = conn.execute(
            "SELECT * FROM asignaciones WHERE id=? AND profesor_id=?",
            (asig_id, u["id"])
        ).fetchone()
        if not asig:
            return jsonify({"ok": False, "error": "No encontrada"}), 404

        guardadas = 0
        for e in entregas:
            est_id    = e.get("estudiante_id")
            entregado = e.get("entregado", True)   # True = sí entregó
            nota_raw  = e.get("nota")
            obs       = (e.get("observacion") or "").strip() or None

            if est_id is None:
                continue

            if not entregado:
                # Marcar como No entregó — nota NULL, entregado=0
                conn.execute(
                    """INSERT INTO entregas_asignacion
                           (asignacion_id, estudiante_id, nota, observacion, entregado)
                       VALUES (?,?,NULL,?,0)
                       ON CONFLICT(asignacion_id, estudiante_id)
                       DO UPDATE SET nota=NULL,
                                     observacion=excluded.observacion,
                                     entregado=0,
                                     calificado_en=datetime('now')""",
                    (asig_id, est_id, obs)
                )
                guardadas += 1
            elif nota_raw is not None:
                # Entregó con nota
                conn.execute(
                    """INSERT INTO entregas_asignacion
                           (asignacion_id, estudiante_id, nota, observacion, entregado)
                       VALUES (?,?,?,?,1)
                       ON CONFLICT(asignacion_id, estudiante_id)
                       DO UPDATE SET nota=excluded.nota,
                                     observacion=excluded.observacion,
                                     entregado=1,
                                     calificado_en=datetime('now')""",
                    (asig_id, est_id, float(nota_raw), obs)
                )
                guardadas += 1

    return jsonify({"ok": True, "guardadas": guardadas})


@asignaciones_bp.route("/api/asignaciones/<int:asig_id>/notas", methods=["GET"])
@login_required
def asignaciones_notas(asig_id):
    """Devuelve las notas de todos los estudiantes para una asignación."""
    u = get_usuario()
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        asig = conn.execute(
            "SELECT * FROM asignaciones WHERE id=? AND profesor_id=?",
            (asig_id, u["id"])
        ).fetchone()
        if not asig:
            return jsonify({"ok": False, "error": "No encontrada"}), 404

        import json as _json
        asig_dict = dict(asig)
        try:
            asig_dict["criterios"] = _json.loads(asig_dict.get("criterios") or "[]")
        except Exception:
            asig_dict["criterios"] = []

        entregas = conn.execute(
            """SELECT ea.*, e.nombre, e.apellido, e.id as est_id
               FROM entregas_asignacion ea
               JOIN estudiantes e ON e.id = ea.estudiante_id
               WHERE ea.asignacion_id=?
               ORDER BY e.apellido, e.nombre""",
            (asig_id,)
        ).fetchall()

    return jsonify({
        "ok": True,
        "asignacion": asig_dict,
        "entregas": [dict(r) for r in entregas]
    })


@asignaciones_bp.route("/api/asignaciones/<int:asig_id>/reporte", methods=["GET"])
@login_required
def asignaciones_reporte(asig_id):
    """
    Devuelve resumen estadístico de una asignación:
    promedio, aprobados, reprobados, distribución por rangos,
    y lista completa de estudiantes con su nota (incluyendo pendientes).
    """
    u = get_usuario()
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        asig = conn.execute(
            "SELECT * FROM asignaciones WHERE id=? AND profesor_id=?",
            (asig_id, u["id"])
        ).fetchone()
        if not asig:
            return jsonify({"ok": False, "error": "No encontrada"}), 404

        import json as _json
        asig_dict = dict(asig)
        try:
            asig_dict["criterios"] = _json.loads(asig_dict.get("criterios") or "[]")
        except Exception:
            asig_dict["criterios"] = []

        # Todos los estudiantes del grado/mención del profesor
        # ── Nueva lógica multi-grado ──
        _alc    = _resolver_alcance_profesor(u)
        grados_prof    = _alc["grados"]
        menciones_prof = _alc["menciones"]
        _fmen          = _alc["filtro_mencion"]
        eq = "SELECT id, nombre, apellido FROM estudiantes WHERE 1=1"
        ep = []
        if grados_prof:
            eq += " AND (" + " OR ".join(["grado LIKE ?" for _ in grados_prof]) + ")"
            ep.extend([f"%{g}%" for g in grados_prof])
        if _fmen and menciones_prof:
            eq += " AND (" + " OR ".join(["curso LIKE ?" for _ in menciones_prof]) + ")"
            ep.extend([f"%{m}%" for m in menciones_prof])
        eq += " ORDER BY apellido, nombre"
        todos = [dict(r) for r in conn.execute(eq, ep).fetchall()]

        # Notas registradas
        entregas_rows = conn.execute(
            "SELECT estudiante_id, nota, observacion FROM entregas_asignacion WHERE asignacion_id=?",
            (asig_id,)
        ).fetchall()
        notas_map = {r["estudiante_id"]: dict(r) for r in entregas_rows}

    puntaje_max = float(asig_dict.get("puntaje_total") or 100)

    estudiantes_reporte = []
    notas_vals = []
    for est in todos:
        entrega    = notas_map.get(est["id"])
        entregado  = entrega["entregado"] if entrega else None
        nota_raw   = entrega["nota"] if entrega else None
        obs        = entrega["observacion"] if entrega else None

        if entregado == 0:
            estado = "no_entrego"
            nota   = None
            pct    = None
        elif nota_raw is not None:
            nota  = nota_raw
            pct   = round(nota / puntaje_max * 100, 1)
            # Convertir a escala 0-100 y clasificar con grades.py
            estado = G.clasificar_nota(pct)
        else:
            nota   = None
            pct    = None
            estado = "pendiente"

        estudiantes_reporte.append({
            "id": est["id"], "nombre": est["nombre"], "apellido": est["apellido"],
            "nota": nota, "porcentaje": pct, "observacion": obs,
            "estado": estado, "color": G.COLORES.get(estado, "#888"),
        })
        if nota is not None:
            notas_vals.append(nota)

    total       = len(estudiantes_reporte)
    calificados = len(notas_vals)
    pendientes  = total - calificados
    aprobados   = sum(1 for e in estudiantes_reporte if e["estado"] in ("destacado","satisfactorio","basico"))
    en_proceso  = sum(1 for e in estudiantes_reporte if e["estado"] == "en_proceso")
    reprobados  = sum(1 for e in estudiantes_reporte if e["estado"] == "insuficiente")
    promedio    = round(sum(notas_vals) / calificados, 2) if calificados else None
    nota_max    = max(notas_vals) if notas_vals else None
    nota_min    = min(notas_vals) if notas_vals else None

    # Distribución en 4 rangos
    def rango(n):
        p = n / puntaje_max * 100
        if p >= 89: return "D · Destacado (89-100)"
        if p >= 80: return "S · Satisfactorio (80-88)"
        if p >= 70: return "B · Básico (70-79)"
        return "Reprobado (<65)"

    distribucion = {}
    for n in notas_vals:
        r = rango(n)
        distribucion[r] = distribucion.get(r, 0) + 1

    return jsonify({
        "ok": True,
        "asignacion": asig_dict,
        "resumen": {
            "total": total, "calificados": calificados, "pendientes": pendientes,
            "aprobados": aprobados, "reprobados": reprobados,
            "promedio": promedio, "nota_max": nota_max, "nota_min": nota_min,
            "pct_aprobacion": round(aprobados / calificados * 100, 1) if calificados else 0,
            "distribucion": distribucion,
        },
        "estudiantes": estudiantes_reporte
    })


@asignaciones_bp.route("/api/estudiante/<int:est_id>/asignaciones", methods=["GET"])
@login_required
def asignaciones_por_estudiante(est_id):
    """
    Devuelve todas las asignaciones publicadas para el grado/mención
    del estudiante, junto con su nota si ya fue calificado.
    Filtra por: materia, periodo, tipo (opcionales).
    """
    u = get_usuario()
    materia = request.args.get("materia", "").strip()
    periodo = request.args.get("periodo", "").strip()
    tipo    = request.args.get("tipo", "").strip()

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        est = conn.execute(
            "SELECT id, grado, curso FROM estudiantes WHERE id=?", (est_id,)
        ).fetchone()
        if not est:
            return jsonify({"ok": False, "error": "Estudiante no encontrado"}), 404

        est_grado   = (est["grado"] or "").strip()
        est_mencion_raw = (est["curso"] or "").strip().upper()
        # Última palabra del campo curso = mención (ej: "4to MULTIMEDIA" → "MULTIMEDIA")
        # split() seguro: valida que haya al menos una palabra antes de acceder [-1]
        partes = est_mencion_raw.split()
        mencion_kw = partes[-1] if len(partes) > 1 else (partes[0] if partes else "")

        q = """
            SELECT a.*, u.nombre AS profesor_nombre
            FROM asignaciones a
            LEFT JOIN usuarios u ON u.id = a.profesor_id
            WHERE a.estado = 'publicada'
              AND (a.grado LIKE ? OR a.grado = '')
              AND (a.mencion LIKE ? OR a.mencion = '' OR a.mencion = 'GENERAL')
        """
        params = [f"%{est_grado}%", f"%{mencion_kw}%"]
        if materia: q += " AND a.materia=?";  params.append(materia)
        if periodo: q += " AND a.periodo=?";  params.append(periodo)
        if tipo:    q += " AND a.tipo=?";     params.append(tipo)
        q += " ORDER BY a.fecha_entrega DESC, a.creado_en DESC"

        asigs = [dict(r) for r in conn.execute(q, params).fetchall()]

        import json as _json
        for a in asigs:
            try:
                a["criterios"] = _json.loads(a.get("criterios") or "[]")
            except Exception:
                a["criterios"] = []
            entrega = conn.execute(
                "SELECT nota, observacion, calificado_en, entregado FROM entregas_asignacion "
                "WHERE asignacion_id=? AND estudiante_id=?",
                (a["id"], est_id)
            ).fetchone()
            if entrega is not None:
                # entregado=0 → no entregó (nota NULL)
                if entrega["entregado"] == 0 or (entrega["entregado"] is None and entrega["nota"] is None):
                    a["nota_estudiante"] = None
                    a["observacion"]     = entrega["observacion"]
                    a["calificado_en"]   = entrega["calificado_en"]
                    a["porcentaje"]      = None
                    a["estado_nota"]     = "no_entrego"
                elif entrega["nota"] is not None:
                    pmax = float(a.get("puntaje_total") or 100)
                    nota = entrega["nota"]
                    a["nota_estudiante"] = nota
                    a["observacion"]     = entrega["observacion"]
                    a["calificado_en"]   = entrega["calificado_en"]
                    a["porcentaje"]      = round(nota / pmax * 100, 1)
                    a["estado_nota"]     = _nota_estado(nota / pmax * 100)
                else:
                    a["nota_estudiante"] = None
                    a["observacion"]     = entrega["observacion"]
                    a["calificado_en"]   = entrega["calificado_en"]
                    a["porcentaje"]      = None
                    a["estado_nota"]     = "pendiente"
            else:
                a["nota_estudiante"] = None
                a["observacion"]     = None
                a["calificado_en"]   = None
                a["porcentaje"]      = None
                a["estado_nota"]     = "pendiente"

    return jsonify({"ok": True, "asignaciones": asigs, "total": len(asigs)})


@asignaciones_bp.route("/api/asignaciones/<int:asig_id>/exportar-csv", methods=["GET"])
@login_required
def asignaciones_exportar_csv(asig_id):
    """Exporta las notas de una asignación como archivo CSV descargable."""
    u = get_usuario()
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        asig = conn.execute(
            "SELECT * FROM asignaciones WHERE id=? AND profesor_id=?",
            (asig_id, u["id"])
        ).fetchone()
        if not asig:
            return jsonify({"ok": False, "error": "No encontrada"}), 404

        asig_dict = dict(asig)
        # ── Nueva lógica multi-grado ──
        _alc    = _resolver_alcance_profesor(u)
        grados_prof    = _alc["grados"]
        menciones_prof = _alc["menciones"]
        _fmen          = _alc["filtro_mencion"]
        eq = "SELECT id, nombre, apellido FROM estudiantes WHERE 1=1"
        ep = []
        if grados_prof:
            eq += " AND (" + " OR ".join(["grado LIKE ?" for _ in grados_prof]) + ")"
            ep.extend([f"%{g}%" for g in grados_prof])
        if _fmen and menciones_prof:
            eq += " AND (" + " OR ".join(["curso LIKE ?" for _ in menciones_prof]) + ")"
            ep.extend([f"%{m}%" for m in menciones_prof])
        eq += " ORDER BY apellido, nombre"
        todos = [dict(r) for r in conn.execute(eq, ep).fetchall()]

        notas_map = {
            r["estudiante_id"]: dict(r) for r in conn.execute(
                "SELECT estudiante_id, nota, observacion FROM entregas_asignacion WHERE asignacion_id=?",
                (asig_id,)
            ).fetchall()
        }

    import io, csv
    puntaje_max = float(asig_dict.get("puntaje_total") or 100)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["#", "Apellido", "Nombre", "Nota", "/ " + str(puntaje_max), "Porcentaje", "Estado", "Observación"])
    for i, est in enumerate(todos, 1):
        entrega    = notas_map.get(est["id"])
        entregado  = entrega.get("entregado", 1) if entrega else None
        nota_raw   = entrega["nota"] if entrega and entrega["nota"] is not None else None
        obs        = entrega["observacion"] if entrega else ""

        if entregado == 0:
            nota_str = ""; pct = ""; estado = "No entregó"
        elif nota_raw is not None:
            pct_val  = round(nota_raw / puntaje_max * 100, 1)
            nota_str = str(nota_raw)
            pct      = str(pct_val) + "%"
            estado   = G.ETIQUETAS.get(G.clasificar_nota(pct_val), "—")
        else:
            nota_str = ""; pct = ""; estado = "Pendiente"

        writer.writerow([i, est["apellido"], est["nombre"], nota_str, "", pct, estado, obs or ""])

    titulo_safe = asig_dict.get("titulo", "asignacion").replace(" ", "_").replace("/", "-")[:40]
    filename = f"notas_{titulo_safe}_{asig_dict.get('periodo', 'P1')}.csv"
    from flask import Response
    return Response(
        output.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


