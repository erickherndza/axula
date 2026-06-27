# -*- coding: utf-8 -*-
"""Blueprint: secretaria — Portal administrativo de Secretaría"""

import sqlite3
import logging
import json as _json
import os
import time as _time
from datetime import datetime, date, timedelta
from io import BytesIO
from flask import (
    Blueprint, render_template, request, jsonify, session,
    redirect, url_for, g, send_from_directory, Response, send_file,
)

from core.constants import *
from core.database import get_db, cache_get, cache_set, cache_bust
from core.auth import (
    _hash, _check_password, _normalizar_rol, _ciclo_del_rol,
    login_required, coord_required, admin_required, directora_required,
    _csrf_token, _csrf_check, csrf_protected, rate_limited,
    get_usuario,
)
from core.helpers import *
from core.helpers import _anio_escolar_actual, _audit

logger = logging.getLogger("axula")

secretaria_bp = Blueprint("secretaria_bp", __name__)

def _secretaria_required(f):
    """Solo secretaria, secretaria_docente, coordinadores y directora."""
    import functools
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user_id"):
            return redirect("/login")
        rol = _normalizar_rol(session.get("rol", ""))
        permitidos = {"secretaria", "secretaria_docente", "directora",
                      "coordinador_general", "coordinador_primer_ciclo",
                      "coordinador_segundo_ciclo", "asistente_directora",
                      "superusuario"}
        if rol not in permitidos:
            return jsonify({"error": "Sin permisos para esta sección"}), 403
        return f(*args, **kwargs)
    return decorated


# ── PORTAL SECRETARÍA ────────────────────────────────────────────────────────

@secretaria_bp.route("/secretaria")
@login_required
def portal_secretaria():
    u = get_usuario()
    rol = _normalizar_rol(u.get("rol", ""))
    if rol not in {"secretaria", "secretaria_docente", "directora",
                   "coordinador_general", "coordinador_primer_ciclo",
                   "coordinador_segundo_ciclo", "asistente_directora",
                   "superusuario"}:
        return redirect("/")
    return render_template("secretaria.html", usuario=u, current_user=u)


# ── DOCUMENTOS (certificados, cartas, constancias, records) ──────────────────

@secretaria_bp.route("/api/secretaria/documentos", methods=["GET"])
@login_required
@_secretaria_required
def listar_documentos():
    tipo = request.args.get("tipo", "")
    estado = request.args.get("estado", "")
    buscar = request.args.get("buscar", "").strip()
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        sql = """
            SELECT d.*, e.nombre as est_nombre, e.apellido as est_apellido,
                   e.grado, e.curso, u.nombre as generado_nombre
            FROM documentos_admin d
            LEFT JOIN estudiantes e ON e.id = d.estudiante_id
            LEFT JOIN usuarios u ON u.id = d.generado_por
            WHERE 1=1
        """
        params = []
        if tipo:
            sql += " AND d.tipo = ?"
            params.append(tipo)
        if estado:
            sql += " AND d.estado = ?"
            params.append(estado)
        if buscar:
            sql += " AND (e.nombre LIKE ? OR e.apellido LIKE ? OR d.titulo LIKE ?)"
            params.extend([f"%{buscar}%"] * 3)
        sql += " ORDER BY d.creado_en DESC LIMIT 200"
        rows = conn.execute(sql, params).fetchall()
    return jsonify([dict(r) for r in rows])


@secretaria_bp.route("/api/secretaria/documentos", methods=["POST"])
@login_required
@_secretaria_required
def crear_documento():
    d = request.get_json(silent=True) or {}
    u = get_usuario()
    tipo = d.get("tipo", "").strip()
    if not tipo:
        return jsonify({"error": "Tipo de documento requerido"}), 400

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        # Generar número de documento
        anio = datetime.now().year
        count = conn.execute(
            "SELECT COUNT(*) FROM documentos_admin WHERE tipo=? AND fecha_emision LIKE ?",
            (tipo, f"{anio}%")
        ).fetchone()[0]
        numero = f"{tipo.upper()[:3]}-{anio}-{count+1:04d}"

        conn.execute("""
            INSERT INTO documentos_admin
            (tipo, estudiante_id, titulo, contenido, destinatario, numero_doc,
             estado, generado_por, observaciones)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (
            tipo, d.get("estudiante_id"), d.get("titulo", f"Documento {numero}"),
            d.get("contenido", ""), d.get("destinatario", ""),
            numero, d.get("estado", "borrador"), u["id"],
            d.get("observaciones", ""),
        ))
        doc_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()
        cache_bust()

    _audit("documento_creado", f"Documento {numero} ({tipo})", "documentos_admin", doc_id)
    return jsonify({"ok": True, "id": doc_id, "numero": numero})


@secretaria_bp.route("/api/secretaria/documentos/<int:doc_id>", methods=["PATCH"])
@login_required
@_secretaria_required
def actualizar_documento(doc_id):
    d = request.get_json(silent=True) or {}
    campos = []
    params = []
    for campo in ["titulo", "contenido", "destinatario", "estado", "observaciones", "fecha_entrega"]:
        if campo in d:
            campos.append(f"{campo}=?")
            params.append(d[campo])
    if not campos:
        return jsonify({"error": "Nada que actualizar"}), 400
    params.append(doc_id)
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.execute(f"UPDATE documentos_admin SET {','.join(campos)} WHERE id=?", params)
        conn.commit()
        cache_bust()
    _audit("documento_actualizado", f"Documento #{doc_id} actualizado", "documentos_admin", doc_id)
    return jsonify({"ok": True})


@secretaria_bp.route("/api/secretaria/documentos/<int:doc_id>", methods=["DELETE"])
@login_required
@_secretaria_required
def eliminar_documento(doc_id):
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.execute("DELETE FROM documentos_admin WHERE id=?", (doc_id,))
        conn.commit()
        cache_bust()
    return jsonify({"ok": True})


# ── INSCRIPCIONES ────────────────────────────────────────────────────────────

@secretaria_bp.route("/api/secretaria/inscripciones", methods=["GET"])
@login_required
@_secretaria_required
def listar_inscripciones():
    anio = request.args.get("anio", _anio_escolar_actual())
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT i.*, e.nombre, e.apellido, e.cedula
            FROM inscripciones i
            LEFT JOIN estudiantes e ON e.id = i.estudiante_id
            WHERE i.anio_escolar = ? AND i.estado = 'activa'
            ORDER BY i.creado_en DESC
        """, (anio,)).fetchall()
    return jsonify([dict(r) for r in rows])


@secretaria_bp.route("/api/secretaria/inscripciones", methods=["POST"])
@login_required
@_secretaria_required
def crear_inscripcion():
    d = request.get_json(silent=True) or {}
    u = get_usuario()
    est_id = d.get("estudiante_id")
    if not est_id:
        return jsonify({"error": "Estudiante requerido"}), 400

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.execute("""
            INSERT INTO inscripciones
            (estudiante_id, anio_escolar, grado, mencion, seccion, tipo,
             procedencia, documentos_entregados, monto_inscripcion, registrado_por, observaciones)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (
            est_id, d.get("anio_escolar", _anio_escolar_actual()),
            d.get("grado", ""), d.get("mencion", ""), d.get("seccion", "A"),
            d.get("tipo", "nueva"), d.get("procedencia", ""),
            _json.dumps(d.get("documentos_entregados", [])),
            d.get("monto_inscripcion", 0), u["id"], d.get("observaciones", ""),
        ))
        insc_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()
        cache_bust()

    _audit("inscripcion_creada", f"Inscripción estudiante #{est_id}", "inscripciones", insc_id)
    return jsonify({"ok": True, "id": insc_id})


# ── RETIROS Y TRASLADOS ─────────────────────────────────────────────────────

@secretaria_bp.route("/api/secretaria/retiros", methods=["GET"])
@login_required
@_secretaria_required
def listar_retiros():
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT r.*, e.nombre, e.apellido, e.grado, e.curso
            FROM retiros_traslados r
            LEFT JOIN estudiantes e ON e.id = r.estudiante_id
            ORDER BY r.creado_en DESC LIMIT 100
        """).fetchall()
    return jsonify([dict(r) for r in rows])


@secretaria_bp.route("/api/secretaria/retiros", methods=["POST"])
@login_required
@_secretaria_required
def crear_retiro():
    d = request.get_json(silent=True) or {}
    u = get_usuario()
    est_id = d.get("estudiante_id")
    if not est_id:
        return jsonify({"error": "Estudiante requerido"}), 400

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        # Verificar que no esté ya retirado
        cond = conn.execute(
            "SELECT condicion FROM estudiantes WHERE id=?", (est_id,)
        ).fetchone()
        if cond and cond[0] == 'RETIRADO':
            return jsonify({"error": "Este estudiante ya está retirado"}), 400

        conn.execute("""
            INSERT INTO retiros_traslados
            (estudiante_id, tipo, motivo, centro_destino, documentos_entregados,
             procesado_por, observaciones)
            VALUES (?,?,?,?,?,?,?)
        """, (
            est_id, d.get("tipo", "retiro_voluntario"), d.get("motivo", ""),
            d.get("centro_destino", ""),
            _json.dumps(d.get("documentos_entregados", [])),
            u["id"], d.get("observaciones", ""),
        ))
        ret_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        # Cambiar condición del estudiante
        conn.execute("UPDATE estudiantes SET condicion='RETIRADO' WHERE id=?", (est_id,))
        conn.commit()
        cache_bust()

    _audit("retiro_procesado", f"Retiro estudiante #{est_id}", "retiros_traslados", ret_id)
    return jsonify({"ok": True, "id": ret_id})


# ── ESTADÍSTICAS DASHBOARD ───────────────────────────────────────────────────

@secretaria_bp.route("/api/secretaria/resumen")
@login_required
@_secretaria_required
def resumen_secretaria():
    anio = _anio_escolar_actual()
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row

        docs_emitidos = conn.execute(
            "SELECT COUNT(*) FROM documentos_admin WHERE fecha_emision LIKE ?",
            (f"{datetime.now().year}%",)
        ).fetchone()[0]

        docs_por_tipo = conn.execute("""
            SELECT tipo, COUNT(*) as total FROM documentos_admin
            WHERE fecha_emision LIKE ? GROUP BY tipo
        """, (f"{datetime.now().year}%",)).fetchall()

        inscripciones = conn.execute(
            "SELECT COUNT(*) FROM inscripciones WHERE anio_escolar=? AND estado='activa'",
            (anio,)
        ).fetchone()[0]

        retiros = conn.execute(
            "SELECT COUNT(*) FROM retiros_traslados WHERE fecha_retiro LIKE ?",
            (f"{datetime.now().year}%",)
        ).fetchone()[0]

        total_estudiantes = conn.execute(
            "SELECT COUNT(*) FROM estudiantes WHERE condicion='ACTIVO'"
        ).fetchone()[0]

        por_grado = conn.execute(
            "SELECT grado, COUNT(*) as total FROM estudiantes WHERE condicion='ACTIVO' GROUP BY grado ORDER BY grado"
        ).fetchall()

    return jsonify({
        "docs_emitidos": docs_emitidos,
        "docs_por_tipo": [dict(r) for r in docs_por_tipo],
        "inscripciones": inscripciones,
        "retiros": retiros,
        "total_estudiantes": total_estudiantes,
        "por_grado": [dict(r) for r in por_grado],
    })


# ── BÚSQUEDA DE ESTUDIANTES PARA DOCUMENTOS ─────────────────────────────────

@secretaria_bp.route("/api/secretaria/buscar-estudiante")
@login_required
@_secretaria_required
def buscar_estudiante_secretaria():
    q = request.args.get("q", "").strip()
    if len(q) < 2:
        return jsonify([])
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT id, nombre, apellido, grado, curso, cedula, condicion
            FROM estudiantes
            WHERE (nombre LIKE ? OR apellido LIKE ? OR cedula LIKE ?)
            ORDER BY apellido, nombre LIMIT 20
        """, (f"%{q}%", f"%{q}%", f"%{q}%")).fetchall()
    return jsonify([dict(r) for r in rows])



@secretaria_bp.route("/api/secretaria/retiros/<int:ret_id>", methods=["DELETE"])
@login_required
@_secretaria_required
def eliminar_retiro(ret_id):
    """Anula un retiro y reactiva al estudiante."""
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        ret = conn.execute(
            "SELECT estudiante_id FROM retiros_traslados WHERE id=?", (ret_id,)
        ).fetchone()
        if not ret:
            return jsonify({"error": "Retiro no encontrado"}), 404

        conn.execute("DELETE FROM retiros_traslados WHERE id=?", (ret_id,))
        conn.execute(
            "UPDATE estudiantes SET condicion='ACTIVO' WHERE id=?",
            (ret[0],))
        conn.commit()
        cache_bust()

    _audit("retiro_anulado", f"Retiro #{ret_id} anulado, estudiante reactivado",
           "retiros_traslados", ret_id)
    return jsonify({"ok": True})

# ═══════════════════════════════════════════════════════════════════════════
#  NUEVAS FUNCIONALIDADES — Certificados PDF, Record, Documentos entregados
# ═══════════════════════════════════════════════════════════════════════════

# ── GENERAR CERTIFICADO PDF ──────────────────────────────────────────────────

@secretaria_bp.route("/api/secretaria/certificado-pdf", methods=["POST"])
@login_required
@_secretaria_required
def generar_certificado_pdf():
    """Genera certificado en PDF (conducta, estudio, constancia)."""
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import inch
    from io import BytesIO

    d = request.get_json(silent=True) or {}
    tipo = d.get("tipo", "certificado_estudio")
    est_id = d.get("estudiante_id")
    destinatario = d.get("destinatario", "A QUIEN PUEDA INTERESAR")
    contenido_extra = d.get("contenido", "")

    if not est_id:
        return jsonify({"error": "Estudiante requerido"}), 400

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        est = conn.execute(
            "SELECT * FROM estudiantes WHERE id=?", (est_id,)
        ).fetchone()
        if not est:
            return jsonify({"error": "Estudiante no encontrado"}), 404
        est = dict(est)

    from core.helpers import _get_config_centro
    cfg = _get_config_centro()
    centro_nombre = cfg.get("nombre", "Centro Educativo en Artes Benito Juárez")
    centro_dir = cfg.get("direccion", "Santo Domingo, República Dominicana")
    centro_tel = cfg.get("telefono", "")

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    w, h = letter

    # Membrete
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(w/2, h - 1*inch, centro_nombre)
    c.setFont("Helvetica", 10)
    c.drawCentredString(w/2, h - 1.3*inch, centro_dir)
    if centro_tel:
        c.drawCentredString(w/2, h - 1.5*inch, f"Tel: {centro_tel}")

    # Línea decorativa
    c.setStrokeColorRGB(0, 0.47, 0.83)
    c.setLineWidth(2)
    c.line(1*inch, h - 1.7*inch, w - 1*inch, h - 1.7*inch)

    # Tipo de certificado
    titulos = {
        "certificado_conducta": "CERTIFICACIÓN DE BUENA CONDUCTA",
        "certificado_estudio": "CERTIFICACIÓN DE ESTUDIOS",
        "constancia": "CONSTANCIA",
        "record_notas": "RECORD DE NOTAS",
        "carta_permiso": "CARTA",
    }
    titulo = titulos.get(tipo, "CERTIFICACIÓN")
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(w/2, h - 2.3*inch, titulo)

    # Destinatario
    c.setFont("Helvetica-Bold", 11)
    c.drawString(1*inch, h - 3*inch, destinatario)

    # Cuerpo
    c.setFont("Helvetica", 11)
    nombre_completo = f"{est.get('nombre', '')} {est.get('apellido', '')}"
    cedula = est.get("cedula", "N/A")
    grado = est.get("grado", "")
    mencion = est.get("curso", "")

    from datetime import datetime
    fecha_actual = datetime.now().strftime("%d de %B de %Y").replace(
        "January", "enero").replace("February", "febrero").replace("March", "marzo"
    ).replace("April", "abril").replace("May", "mayo").replace("June", "junio"
    ).replace("July", "julio").replace("August", "agosto").replace("September", "septiembre"
    ).replace("October", "octubre").replace("November", "noviembre").replace("December", "diciembre")

    y = h - 3.5*inch

    if tipo == "certificado_conducta":
        texto = (
            f"Certificamos que el/la estudiante {nombre_completo}, "
            f"portador/a de la cédula {cedula}, cursante del {grado} grado "
            f"en la mención de {mencion}, ha mantenido una conducta ejemplar "
            f"durante su permanencia en este centro educativo."
        )
    elif tipo == "certificado_estudio":
        texto = (
            f"Certificamos que el/la estudiante {nombre_completo}, "
            f"portador/a de la cédula {cedula}, se encuentra inscrito/a y "
            f"cursando activamente el {grado} grado en la mención de {mencion} "
            f"en este centro educativo para el año escolar {_anio_escolar_actual()}."
        )
    elif tipo == "constancia":
        texto = (
            f"Hacemos constar que el/la estudiante {nombre_completo}, "
            f"portador/a de la cédula {cedula}, es estudiante activo/a de este "
            f"centro educativo, cursando el {grado} grado, mención {mencion}."
        )
    else:
        texto = contenido_extra or f"Documento referente al estudiante {nombre_completo}."

    # Word wrap
    from reportlab.lib.utils import simpleSplit
    lines = simpleSplit(texto, "Helvetica", 11, w - 2*inch)
    for line in lines:
        c.drawString(1*inch, y, line)
        y -= 16

    if contenido_extra and tipo != "constancia":
        y -= 10
        extra_lines = simpleSplit(contenido_extra, "Helvetica", 11, w - 2*inch)
        for line in extra_lines:
            c.drawString(1*inch, y, line)
            y -= 16

    # Cierre
    y -= 30
    c.drawString(1*inch, y,
        f"Certificación expedida en {centro_dir}, a los {fecha_actual}.")

    # Firma
    y -= 80
    c.setLineWidth(0.5)
    c.setStrokeColorRGB(0, 0, 0)
    c.line(1.5*inch, y, 4*inch, y)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(1.5*inch, y - 14, "Director/a del Centro")

    c.line(4.5*inch, y, 7*inch, y)
    c.drawString(4.5*inch, y - 14, "Secretario/a Docente")

    # Pie
    c.setFont("Helvetica", 8)
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.drawCentredString(w/2, 0.5*inch, f"{centro_nombre} · {centro_dir}")

    c.save()
    buf.seek(0)

    # Also register in documentos_admin
    u = get_usuario()
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        anio = datetime.now().year
        count = conn.execute(
            "SELECT COUNT(*) FROM documentos_admin WHERE tipo=? AND fecha_emision LIKE ?",
            (tipo, f"{anio}%")
        ).fetchone()[0]
        numero = f"{tipo.upper()[:3]}-{anio}-{count+1:04d}"
        conn.execute("""
            INSERT INTO documentos_admin
            (tipo, estudiante_id, titulo, contenido, destinatario, numero_doc,
             estado, generado_por)
            VALUES (?,?,?,?,?,?,?,?)
        """, (tipo, est_id, titulo, contenido_extra, destinatario, numero,
              "emitido", u["id"]))
        conn.commit()

    return send_file(buf, mimetype="application/pdf",
        download_name=f"{tipo}_{est.get('apellido','')}_{est.get('nombre','')}.pdf",
        as_attachment=False)


# ── RECORD DE NOTAS PDF ──────────────────────────────────────────────────────

@secretaria_bp.route("/api/secretaria/record-notas/<int:est_id>")
@login_required
@_secretaria_required
def record_notas_pdf(est_id):
    """Genera record de notas completo en PDF — incluye expedientes históricos digitalizados."""
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import inch
    from io import BytesIO
    from datetime import date as _date_rec
    import json as _jr

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        est = conn.execute("SELECT * FROM estudiantes WHERE id=?", (est_id,)).fetchone()
        if not est:
            return jsonify({"error": "Estudiante no encontrado"}), 404
        est = dict(est)

        # Notas del sistema por período
        notas_sis = conn.execute("""
            SELECT materia, periodo, nota, anio_escolar
            FROM calificaciones_periodo
            WHERE estudiante_id=?
            ORDER BY anio_escolar, materia, periodo
        """, (est_id,)).fetchall()

        # Expedientes históricos digitalizados
        historicos = conn.execute("""
            SELECT anio_escolar, grado, sistema_educativo, seccion, mencion,
                   centro_educativo, materias_json, promedio_general, condicion, es_externo
            FROM expedientes_historicos
            WHERE estudiante_id=?
            ORDER BY anio_escolar ASC
        """, (est_id,)).fetchall()

    # ── Pivot notas del sistema por (año → materia → {P1..P4}) ───────────────
    years_sis = {}
    for n in notas_sis:
        ay = n["anio_escolar"] or "Actual"
        if ay not in years_sis:
            years_sis[ay] = {}
        mat = n["materia"]
        if mat not in years_sis[ay]:
            years_sis[ay][mat] = {"P1": "", "P2": "", "P3": "", "P4": ""}
        years_sis[ay][mat][n["periodo"]] = str(int(n["nota"])) if n["nota"] else ""

    # ── Organizar expedientes históricos ─────────────────────────────────────
    years_hist = {}
    for h in historicos:
        ay = h["anio_escolar"]
        try:
            mats_raw = _jr.loads(h["materias_json"] or "[]")
        except Exception:
            mats_raw = []
        mats = {}
        for m in mats_raw:
            mn = m.get("materia", "")
            if mn:
                def _sv(v):
                    return str(int(float(v))) if v not in (None, "", 0) else ""
                mats[mn] = {
                    "P1": _sv(m.get("p1")), "P2": _sv(m.get("p2")),
                    "P3": _sv(m.get("p3")), "P4": _sv(m.get("p4")),
                    "_prom": str(round(float(m["promedio"]), 1)) if m.get("promedio") else "",
                }
        years_hist[ay] = {
            "grado": h["grado"], "sistema": h["sistema_educativo"],
            "seccion": h["seccion"], "mencion": h["mencion"],
            "centro": h["centro_educativo"],
            "materias": mats, "condicion": h["condicion"],
            "es_externo": h["es_externo"],
        }

    # ── Merge y ordenar todos los años ───────────────────────────────────────
    all_years = sorted(set(years_hist) | set(years_sis))

    from core.helpers import _get_config_centro
    cfg = _get_config_centro()
    centro_nombre = cfg.get("nombre", "Centro Educativo en Artes Benito Juárez")

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    w, h = letter
    page_num = [1]

    def _header():
        c.setFont("Helvetica-Bold", 13)
        c.drawCentredString(w/2, h - 0.7*inch, centro_nombre)
        c.setFont("Helvetica-Bold", 15)
        c.drawCentredString(w/2, h - 1.05*inch, "RECORD DE NOTAS OFICIAL")
        c.setStrokeColorRGB(0, 0.47, 0.83)
        c.setLineWidth(2)
        c.line(0.75*inch, h - 1.2*inch, w - 0.75*inch, h - 1.2*inch)
        c.setFont("Helvetica", 9.5)
        yi = h - 1.48*inch
        nombre_est = f"{est.get('nombre','')} {est.get('apellido','')}"
        c.drawString(0.75*inch, yi, f"Estudiante: {nombre_est}")
        c.drawString(4.2*inch, yi, f"Cédula: {est.get('cedula','N/A')}")
        yi -= 14
        c.drawString(0.75*inch, yi, f"Grado actual: {est.get('grado','')}  ·  Mención: {est.get('curso','')}")
        c.drawString(5.5*inch, yi, f"Pág. {page_num[0]}")
        c.setLineWidth(0.5)
        c.setStrokeColorRGB(0.8, 0.8, 0.8)
        c.line(0.75*inch, yi - 6, w - 0.75*inch, yi - 6)
        return h - 1.82*inch

    y = _header()
    cols = [0.75*inch, 3.35*inch, 4.1*inch, 4.85*inch, 5.6*inch, 6.35*inch]

    if not all_years:
        c.setFont("Helvetica", 10)
        c.setFillColorRGB(0.5, 0.5, 0.5)
        c.drawCentredString(w/2, y - 0.5*inch, "No hay registros de calificaciones disponibles.")
    else:
        for anio_escolar in all_years:
            hist = years_hist.get(anio_escolar)
            sis  = years_sis.get(anio_escolar, {})

            if hist:
                materias = dict(hist["materias"])
                for mat, ps in sis.items():
                    if mat not in materias:
                        materias[mat] = ps
                grado_lbl = hist["grado"]
                sistema   = hist["sistema"] or "secundaria"
                mencion_l = hist.get("mencion") or ""
                condicion = hist.get("condicion") or ""
                externo   = " [Externo]" if hist.get("es_externo") else ""
            else:
                materias  = sis
                grado_lbl = est.get("grado", "")
                sistema   = "secundaria"
                mencion_l = est.get("curso", "")
                condicion = ""
                externo   = ""

            if not materias:
                continue

            needed = (len(materias) * 13) + 45
            if y < needed or y < 2.0*inch:
                c.showPage()
                page_num[0] += 1
                y = _header()

            # Barra de año
            sis_txt = "Bachillerato" if sistema == "bachillerato" else "Secundaria"
            c.setFillColorRGB(0.04, 0.27, 0.49)
            c.rect(0.75*inch, y - 16, w - 1.5*inch, 18, fill=1, stroke=0)
            c.setFillColorRGB(1, 1, 1)
            c.setFont("Helvetica-Bold", 8.5)
            lbl = f"  {anio_escolar}  —  {grado_lbl}  ({sis_txt})"
            if mencion_l:
                lbl += f"  ·  {mencion_l}"
            if externo:
                lbl += externo
            if condicion:
                lbl += f"  ·  {condicion}"
            c.drawString(0.85*inch, y - 10, lbl)
            c.setFillColorRGB(0, 0, 0)
            y -= 22

            # Cabecera columnas
            c.setFont("Helvetica-Bold", 7.5)
            c.setFillColorRGB(0.3, 0.3, 0.3)
            for txt, cx in zip(["Materia", "P1", "P2", "P3", "P4", "Final"], cols):
                c.drawString(cx, y, txt)
            y -= 4
            c.setLineWidth(0.4)
            c.setStrokeColorRGB(0.75, 0.75, 0.75)
            c.line(0.75*inch, y, w - 0.75*inch, y)
            y -= 12
            c.setFillColorRGB(0, 0, 0)
            c.setFont("Helvetica", 8.5)

            for mat, ps in sorted(materias.items()):
                if y < 1.5*inch:
                    c.showPage()
                    page_num[0] += 1
                    y = _header()
                    c.setFont("Helvetica", 8.5)

                p1 = ps.get("P1", "") or ""
                p2 = ps.get("P2", "") or ""
                p3 = ps.get("P3", "") or ""
                p4 = ps.get("P4", "") or ""
                prom_pre = ps.get("_prom", "")
                if prom_pre:
                    final = prom_pre
                else:
                    nums = [float(v) for v in [p1, p2, p3, p4] if v]
                    final = str(round(sum(nums)/len(nums), 1)) if nums else "—"

                c.drawString(cols[0], y, mat[:43])
                for i, v in enumerate([p1, p2, p3, p4]):
                    c.drawString(cols[i+1], y, v if v else "—")
                c.setFont("Helvetica-Bold", 8.5)
                c.drawString(cols[5], y, final)
                c.setFont("Helvetica", 8.5)
                y -= 13

            y -= 8  # espacio entre años

    # Footer
    c.setFont("Helvetica", 7.5)
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.drawCentredString(w/2, 0.5*inch,
        f"Generado el {_date_rec.today().strftime('%d/%m/%Y')} — {centro_nombre} — Axula")
    c.setLineWidth(0.5)
    c.setStrokeColorRGB(0.7, 0.7, 0.7)
    c.line(0.75*inch, 0.65*inch, w - 0.75*inch, 0.65*inch)
    c.save()
    buf.seek(0)

    apellido = est.get('apellido', '')
    nombre_e = est.get('nombre', '')
    return send_file(buf, mimetype="application/pdf",
        download_name=f"record_notas_{apellido}_{nombre_e}.pdf",
        as_attachment=False)


# ── CONTROL DE DOCUMENTOS ENTREGADOS ─────────────────────────────────────────

@secretaria_bp.route("/api/secretaria/documentos-entregados/<int:est_id>", methods=["GET"])
@login_required
@_secretaria_required
def get_documentos_entregados(est_id):
    """Lista qué documentos ha entregado un estudiante."""
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT id, nombre, apellido, grado, curso FROM estudiantes WHERE id=?",
            (est_id,)
        ).fetchone()
        if not row:
            return jsonify({"error": "Estudiante no encontrado"}), 404

        insc = conn.execute("""
            SELECT documentos_entregados, fecha_inscripcion, anio_escolar
            FROM inscripciones WHERE estudiante_id=? ORDER BY creado_en DESC LIMIT 1
        """, (est_id,)).fetchone()

    docs_entregados = []
    if insc and insc["documentos_entregados"]:
        try:
            docs_entregados = _json.loads(insc["documentos_entregados"])
        except Exception as _e:
            logger.warning(f"[secretaria] Excepción silenciada")

    # All possible documents
    docs_requeridos = [
        {"key": "acta_nacimiento", "nombre": "Acta de Nacimiento"},
        {"key": "cedula_padres", "nombre": "Cédula de Padres/Tutores"},
        {"key": "cedula_estudiante", "nombre": "Cédula del Estudiante"},
        {"key": "fotos_2x2", "nombre": "Fotos 2x2"},
        {"key": "record_notas_anterior", "nombre": "Record de Notas Anterior"},
        {"key": "carta_buena_conducta", "nombre": "Carta de Buena Conducta"},
        {"key": "certificado_medico", "nombre": "Certificado Médico"},
        {"key": "seguro_medico", "nombre": "Seguro Médico Escolar"},
        {"key": "formulario_inscripcion", "nombre": "Formulario de Inscripción"},
        {"key": "carta_compromiso", "nombre": "Carta de Compromiso Padres"},
    ]

    result = []
    for doc in docs_requeridos:
        result.append({
            "key": doc["key"],
            "nombre": doc["nombre"],
            "entregado": doc["key"] in docs_entregados,
        })

    return jsonify({
        "estudiante": dict(row),
        "documentos": result,
        "total_entregados": len(docs_entregados),
        "total_requeridos": len(docs_requeridos),
    })


@secretaria_bp.route("/api/secretaria/documentos-entregados/<int:est_id>", methods=["POST"])
@login_required
@_secretaria_required
def actualizar_documentos_entregados(est_id):
    """Actualiza la lista de documentos entregados."""
    d = request.get_json(silent=True) or {}
    docs = d.get("documentos", [])  # list of keys

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        # Update in the latest inscription
        insc = conn.execute(
            "SELECT id FROM inscripciones WHERE estudiante_id=? ORDER BY creado_en DESC LIMIT 1",
            (est_id,)
        ).fetchone()

        if insc:
            conn.execute(
                "UPDATE inscripciones SET documentos_entregados=? WHERE id=?",
                (_json.dumps(docs), insc[0]))
        else:
            # Create a basic inscription record
            u = get_usuario()
            conn.execute("""
                INSERT INTO inscripciones
                (estudiante_id, anio_escolar, grado, documentos_entregados, registrado_por)
                VALUES (?,?,?,?,?)
            """, (est_id, _anio_escolar_actual(), "", _json.dumps(docs), u["id"]))

        conn.commit()

    return jsonify({"ok": True, "total": len(docs)})


# ── HISTORIAL DE INSCRIPCIONES ───────────────────────────────────────────────

@secretaria_bp.route("/api/secretaria/historial-inscripciones/<int:est_id>")
@login_required
@_secretaria_required
def historial_inscripciones(est_id):
    """Historial completo de inscripciones de un estudiante."""
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        est = conn.execute(
            "SELECT id, nombre, apellido FROM estudiantes WHERE id=?",
            (est_id,)
        ).fetchone()
        if not est:
            return jsonify({"error": "Estudiante no encontrado"}), 404

        rows = conn.execute("""
            SELECT i.*, u.nombre as registrado_nombre
            FROM inscripciones i
            LEFT JOIN usuarios u ON u.id = i.registrado_por
            WHERE i.estudiante_id=?
            ORDER BY i.anio_escolar DESC, i.creado_en DESC
        """, (est_id,)).fetchall()

    return jsonify({
        "estudiante": dict(est),
        "inscripciones": [dict(r) for r in rows],
    })


# ═══════════════════════════════════════════════════════════════════════════
#  GESTIÓN DE PERMISOS DEL PERSONAL
# ═══════════════════════════════════════════════════════════════════════════

@secretaria_bp.route("/api/secretaria/permisos", methods=["GET"])
@login_required
@_secretaria_required
def listar_permisos():
    """Lista todos los permisos del personal."""
    estado = request.args.get("estado", "")
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        sql = """
            SELECT p.*, u.nombre as solicitante_nombre, u.rol as solicitante_rol
            FROM permisos_personal p
            LEFT JOIN usuarios u ON u.id = p.usuario_id
            WHERE 1=1
        """
        params = []
        if estado:
            sql += " AND p.estado = ?"
            params.append(estado)
        sql += " ORDER BY p.creado_en DESC LIMIT 200"
        rows = conn.execute(sql, params).fetchall()
    return jsonify([dict(r) for r in rows])


@secretaria_bp.route("/api/secretaria/permisos", methods=["POST"])
@login_required
@_secretaria_required
def crear_permiso():
    """Crea una solicitud de permiso."""
    d = request.get_json(silent=True) or {}
    u = get_usuario()

    usuario_id = d.get("usuario_id")
    if not usuario_id:
        return jsonify({"error": "Selecciona un empleado"}), 400

    fecha_desde = d.get("fecha_desde", "")
    fecha_hasta = d.get("fecha_hasta", "")
    motivo_tipo = d.get("motivo_tipo", "otro")
    motivo_detalle = d.get("motivo_detalle", "")

    if not fecha_desde:
        return jsonify({"error": "Fecha desde es requerida"}), 400

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.execute("""
            INSERT INTO permisos_personal
            (usuario_id, fecha_desde, fecha_hasta, motivo_tipo, motivo_detalle,
             registrado_por, estado)
            VALUES (?,?,?,?,?,?,?)
        """, (
            usuario_id, fecha_desde, fecha_hasta or fecha_desde,
            motivo_tipo, motivo_detalle, u["id"], "pendiente",
        ))
        perm_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()

    _audit("permiso_creado", f"Permiso #{perm_id} para usuario #{usuario_id}",
           "permisos_personal", perm_id)
    return jsonify({"ok": True, "id": perm_id})


@secretaria_bp.route("/api/secretaria/permisos/<int:perm_id>/aprobar", methods=["POST"])
@login_required
@_secretaria_required
def aprobar_permiso(perm_id):
    """Aprueba un permiso pendiente."""
    u = get_usuario()
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.execute(
            "UPDATE permisos_personal SET estado='aprobado', aprobado_por=? WHERE id=?",
            (u["id"], perm_id))
        conn.commit()
    return jsonify({"ok": True})


@secretaria_bp.route("/api/secretaria/permisos/<int:perm_id>/rechazar", methods=["POST"])
@login_required
@_secretaria_required
def rechazar_permiso(perm_id):
    u = get_usuario()
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.execute(
            "UPDATE permisos_personal SET estado='rechazado', aprobado_por=? WHERE id=?",
            (u["id"], perm_id))
        conn.commit()
    return jsonify({"ok": True})


@secretaria_bp.route("/api/secretaria/permisos/<int:perm_id>", methods=["DELETE"])
@login_required
@_secretaria_required
def eliminar_permiso(perm_id):
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.execute("DELETE FROM permisos_personal WHERE id=?", (perm_id,))
        conn.commit()
    return jsonify({"ok": True})


@secretaria_bp.route("/api/secretaria/permisos/<int:perm_id>/pdf")
@login_required
@_secretaria_required
def permiso_pdf(perm_id):
    """Genera documento oficial de permiso en PDF."""
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import inch
    from reportlab.lib.utils import simpleSplit
    from io import BytesIO
    import os

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        perm = conn.execute("""
            SELECT p.*, u.nombre as solicitante_nombre, u.rol as solicitante_rol
            FROM permisos_personal p
            LEFT JOIN usuarios u ON u.id = p.usuario_id
            WHERE p.id=?
        """, (perm_id,)).fetchone()

    if not perm:
        return jsonify({"error": "Permiso no encontrado"}), 404

    from core.helpers import _get_config_centro
    cfg = _get_config_centro()
    centro = cfg.get("nombre", "Centro Educativo en Artes Benito Juárez")
    direccion = cfg.get("direccion", "Prolongación Ovando, Cristo Rey, Santo Domingo, D.N. 10601")
    telefono = cfg.get("telefono", "(809) 563-0241")
    correo = cfg.get("correo", "centroenartesbenitojuarez@gmail.com")

    motivos = {
        "salud": "Salud",
        "maternidad": "Maternidad",
        "fallecimiento": "Fallecimiento Familiar",
        "emergencia": "Emergencia",
        "asunto_juridico": "Asunto Jurídico",
        "otro": "Otro",
    }

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    w, h = letter

    # Logo
    logo_path = os.path.join("static", "logo-benito.jpg")
    if os.path.exists(logo_path):
        try:
            c.drawImage(logo_path, 1*inch, h - 1.5*inch, width=1*inch, height=1*inch,
                       preserveAspectRatio=True, mask='auto')
        except Exception as _e:
            logger.warning(f"[secretaria] Excepción silenciada")

    # Header
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(w/2, h - 0.8*inch, centro)
    c.setFont("Helvetica", 9)
    c.drawCentredString(w/2, h - 1.0*inch, direccion)
    c.drawCentredString(w/2, h - 1.18*inch, f"Tel: {telefono} · {correo}")

    c.setStrokeColorRGB(0, 0.47, 0.83)
    c.setLineWidth(2)
    c.line(0.75*inch, h - 1.4*inch, w - 0.75*inch, h - 1.4*inch)

    # Title
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(w/2, h - 1.9*inch, "SOLICITUD DE PERMISO")

    c.setFont("Helvetica", 10)
    c.drawRightString(w - 1*inch, h - 2.2*inch, f"No. PERM-{perm_id:04d}")

    # Body
    y = h - 2.7*inch
    c.setFont("Helvetica-Bold", 11)
    c.drawString(1*inch, y, "Datos del solicitante:")
    y -= 20
    c.setFont("Helvetica", 11)

    fields = [
        ("Nombre:", perm["solicitante_nombre"] or ""),
        ("Cargo:", (_normalizar_rol(perm["solicitante_rol"] or "")).replace("_", " ").title()),
        ("Fecha desde:", perm["fecha_desde"] or ""),
        ("Fecha hasta:", perm["fecha_hasta"] or perm["fecha_desde"] or ""),
        ("Motivo:", motivos.get(perm["motivo_tipo"], perm["motivo_tipo"])),
    ]

    for label, value in fields:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(1*inch, y, label)
        c.setFont("Helvetica", 10)
        c.drawString(2.8*inch, y, str(value))
        y -= 18

    if perm["motivo_detalle"]:
        y -= 6
        c.setFont("Helvetica-Bold", 10)
        c.drawString(1*inch, y, "Detalle:")
        y -= 16
        c.setFont("Helvetica", 10)
        lines = simpleSplit(perm["motivo_detalle"], "Helvetica", 10, w - 2*inch)
        for line in lines:
            c.drawString(1*inch, y, line)
            y -= 14

    # Estado
    y -= 20
    estado_txt = {"pendiente": "PENDIENTE", "aprobado": "APROBADO", "rechazado": "RECHAZADO"}
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1*inch, y, f"Estado: {estado_txt.get(perm['estado'], perm['estado'])}")

    # Firmas
    y -= 80
    c.setLineWidth(0.5)
    c.setStrokeColorRGB(0, 0, 0)

    c.line(1*inch, y, 3.5*inch, y)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(1*inch, y - 14, "Directora / Coordinador")

    c.line(4.5*inch, y, 7*inch, y)
    c.drawString(4.5*inch, y - 14, "Firma del Solicitante")

    # Footer
    c.setFont("Helvetica", 7)
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.drawCentredString(w/2, 0.5*inch, f"{centro} · {direccion} · Tel: {telefono}")

    c.save()
    buf.seek(0)

    return send_file(buf, mimetype="application/pdf",
        download_name=f"permiso_{perm_id}.pdf", as_attachment=False)


# ── LISTAR PERSONAL (para seleccionar en permisos) ──────────────────────────

@secretaria_bp.route("/api/secretaria/personal")
@login_required
@_secretaria_required
def listar_personal():
    """Lista todo el personal activo para seleccionar en permisos."""
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT id, nombre, username, rol FROM usuarios
            WHERE activo=1 AND rol != 'padre'
            ORDER BY nombre
        """).fetchall()
    return jsonify([dict(r) for r in rows])
