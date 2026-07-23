# -*- coding: utf-8 -*-
"""
Blueprint: Motor de Promoción Estudiantil
Prefijo: /api/promocion
Auth:     coord_required (coordinador o directora)

Reglas MINERD implementadas en core/promocion_engine.py
"""
import logging
import traceback as _tb

from flask import Blueprint, jsonify, request, session

from core.database import get_db

log = logging.getLogger(__name__)
from core.helpers import _anio_escolar_actual, _audit
from core.auth import login_required, coord_required
from core.promocion_engine import (
    evaluar_estudiante,
    evaluar_grado,
    resumen_grado,
    ejecutar_promocion_lote,
    ejecutar_promocion_estudiante,
    evaluar_post_recuperacion,
    _norm_grado,
)

promocion_bp = Blueprint("promocion", __name__, url_prefix="/api/promocion")


# ── Helpers locales ───────────────────────────────────────────────────────────

def _anio_param() -> str:
    return (
        request.args.get("anio_escolar")
        or request.args.get("anio")
        or _anio_escolar_actual()
    )


def _uid() -> int:
    return session.get("uid") or session.get("user_id") or 0


# ── Rutas ─────────────────────────────────────────────────────────────────────

@promocion_bp.route("/preview")
@login_required
@coord_required
def preview():
    """
    GET /api/promocion/preview?grado=4TO&anio_escolar=2025-2026

    Vista previa sin escribir en BD.
    Retorna resumen + lista de estudiantes con su estado calculado.
    """
    grado = _norm_grado(request.args.get("grado", ""))
    anio  = _anio_param()

    if not grado:
        return jsonify({"ok": False, "error": "Parámetro 'grado' requerido"}), 400

    db = get_db()
    resultados = evaluar_grado(db, grado, anio)

    return jsonify({
        "ok":        True,
        "grado":     grado,
        "anio_escolar": anio,
        "resumen":   resumen_grado(resultados),
        "estudiantes": resultados,
    })


@promocion_bp.route("/estudiante/<int:est_id>")
@login_required
@coord_required
def preview_estudiante(est_id: int):
    """
    GET /api/promocion/estudiante/123?anio_escolar=2025-2026

    Evaluación individual sin escribir en BD.
    """
    try:
        anio = _anio_param()
        db   = get_db()
        res  = evaluar_estudiante(db, est_id, anio)

        if "error" in res:
            return jsonify({"ok": False, "error": res["error"]}), 404

        return jsonify({"ok": True, **res})
    except Exception as exc:
        log.exception("preview_estudiante est_id=%s", est_id)
        return jsonify({"ok": False, "error": str(exc), "traceback": _tb.format_exc()}), 500


@promocion_bp.route("/ejecutar", methods=["POST"])
@login_required
@coord_required
def ejecutar_lote():
    """
    POST /api/promocion/ejecutar
    Body JSON:
    {
      "grado": "5TO",
      "anio_escolar": "2025-2026",
      "estudiante_ids": [1, 2, 3],
      "observacion": "Cierre año escolar 2025-2026"
    }

    Ejecuta la promoción en una sola transacción.
    """
    d    = request.get_json(silent=True) or {}
    grado = _norm_grado(d.get("grado", ""))
    anio  = d.get("anio_escolar") or _anio_escolar_actual()
    ids   = d.get("estudiante_ids", [])
    obs   = d.get("observacion", "")

    if not grado:
        return jsonify({"ok": False, "error": "Campo 'grado' requerido"}), 400
    if not ids:
        return jsonify({"ok": False, "error": "Campo 'estudiante_ids' requerido"}), 400

    db = get_db()
    try:
        res = ejecutar_promocion_lote(db, grado, anio, ids, _uid(), observacion=obs)
        _audit(db, _uid(), "promocion_lote",
               f"grado={grado} anio={anio} promovidos={res.get('promovidos',0)} "
               f"recuperacion={res.get('recuperacion',0)} no_promovidos={res.get('no_promovidos',0)}")
        db.commit()
    except Exception as exc:
        db.rollback()
        log.exception("ejecutar_lote grado=%s anio=%s", grado, anio)
        return jsonify({"ok": False, "error": str(exc)}), 500

    return jsonify(res), 200 if res["ok"] else 500


@promocion_bp.route("/ejecutar/<int:est_id>", methods=["POST"])
@login_required
@coord_required
def ejecutar_individual(est_id: int):
    """
    POST /api/promocion/ejecutar/123
    Body JSON:
    {
      "anio_escolar": "2025-2026",
      "forzar": false,
      "observacion": ""
    }
    """
    d     = request.get_json(silent=True) or {}
    anio  = d.get("anio_escolar") or _anio_escolar_actual()
    forzar = bool(d.get("forzar", False))
    obs   = d.get("observacion", "")

    db  = get_db()
    res = ejecutar_promocion_estudiante(
        db, est_id, anio, _uid(), forzar=forzar, observacion=obs
    )

    if res.get("ok"):
        _audit(db, _uid(), "promocion_individual",
               f"est_id={est_id} anio={anio} estado={res['estado']}")
        db.commit()
        return jsonify(res)

    # requiere_confirmacion → 409, error real → 500
    status = 409 if res.get("requiere_confirmacion") else 500
    return jsonify(res), status


@promocion_bp.route("/post-recuperacion/<int:est_id>", methods=["POST"])
@login_required
@coord_required
def post_recuperacion(est_id: int):
    """
    POST /api/promocion/post-recuperacion/123
    Body JSON: { "anio_escolar": "2025-2026", "observacion": "" }

    Re-evalúa y ejecuta la promoción luego de ingresar notas de recuperación de agosto.
    Las notas ya deben estar guardadas en recuperaciones_pedagogicas.nota_recuperacion.
    """
    d    = request.get_json(silent=True) or {}
    anio = d.get("anio_escolar") or _anio_escolar_actual()
    obs  = d.get("observacion", "Recuperación agosto")

    db  = get_db()
    res = ejecutar_promocion_estudiante(
        db, est_id, anio, _uid(),
        post_recuperacion=True,
        observacion=obs,
    )

    if res.get("ok"):
        _audit(db, _uid(), "promocion_post_recuperacion",
               f"est_id={est_id} anio={anio} estado={res['estado']}")
        db.commit()
        return jsonify(res)

    return jsonify(res), 500


@promocion_bp.route("/historial")
@login_required
@coord_required
def historial():
    """
    GET /api/promocion/historial?grado=5TO&anio_escolar=2025-2026&est_id=123

    Historial de promociones. Los tres parámetros son opcionales.
    """
    grado   = _norm_grado(request.args.get("grado", ""))
    anio    = request.args.get("anio_escolar") or request.args.get("anio") or ""
    est_id  = request.args.get("est_id", type=int)

    db = get_db()
    filtros = []
    params  = []

    if grado:
        filtros.append("UPPER(TRIM(e.grado)) = ?")
        params.append(grado)
    if anio:
        filtros.append("p.anio_escolar = ?")
        params.append(anio)
    if est_id:
        filtros.append("p.estudiante_id = ?")
        params.append(est_id)

    where = ("WHERE " + " AND ".join(filtros)) if filtros else ""

    rows = db.execute(
        f"""
        SELECT p.id, p.estudiante_id, e.nombre, e.apellido, e.seccion, e.mencion,
               p.grado_origen, p.grado_destino, p.anio_escolar, p.estado,
               p.mats_reprobadas, p.mats_total, p.mats_recuperacion,
               p.tiene_completiva, p.ciclo, p.fecha, p.observacion,
               u.nombre AS ejecutado_por_nombre
        FROM   promociones p
        JOIN   estudiantes e ON e.id = p.estudiante_id
        LEFT JOIN usuarios u ON u.id = p.ejecutado_por
        {where}
        ORDER  BY p.fecha DESC
        LIMIT  500
        """,
        params,
    ).fetchall()

    return jsonify({
        "ok":   True,
        "total": len(rows),
        "data": [dict(r) for r in rows],
    })


@promocion_bp.route("/detalle/<int:prom_id>")
@login_required
@coord_required
def detalle_promocion(prom_id: int):
    """
    GET /api/promocion/detalle/42

    Detalle por materia de una promoción específica.
    """
    db = get_db()

    encabezado = db.execute(
        """
        SELECT p.*, e.nombre, e.apellido, e.seccion, e.mencion
        FROM   promociones p
        JOIN   estudiantes e ON e.id = p.estudiante_id
        WHERE  p.id = ?
        """,
        (prom_id,),
    ).fetchone()

    if not encabezado:
        return jsonify({"ok": False, "error": "Promoción no encontrada"}), 404

    materias = db.execute(
        """
        SELECT materia, promedio_anual, nota_completiva, nota_final_efectiva,
               aprobada, reprobada_asistencia, pct_inasistencia, estado_materia, snapshot_en
        FROM   promocion_detalle_materias
        WHERE  promocion_id = ?
        ORDER  BY materia
        """,
        (prom_id,),
    ).fetchall()

    return jsonify({
        "ok":        True,
        "promocion": dict(encabezado),
        "materias":  [dict(m) for m in materias],
    })


@promocion_bp.route("/completiva/<int:est_id>", methods=["POST"])
@login_required
@coord_required
def guardar_completiva(est_id: int):
    """
    POST /api/promocion/completiva/123
    Body JSON:
    {
      "anio_escolar": "2025-2026",
      "notas": [
        {"materia": "Matemática", "nota_completiva": 82.5},
        {"materia": "Lengua Española", "nota_completiva": 75.0}
      ]
    }

    Guarda nota_completiva en recuperaciones_pedagogicas para cada materia.
    Usa INSERT OR REPLACE para ser idempotente.
    """
    d    = request.get_json(silent=True) or {}
    anio = d.get("anio_escolar") or _anio_escolar_actual()
    notas = d.get("notas", [])

    if not notas:
        return jsonify({"ok": False, "error": "Campo 'notas' requerido"}), 400

    db       = get_db()
    guardadas = 0

    for item in notas:
        materia        = (item.get("materia") or "").strip()
        nota_completiva = item.get("nota_completiva")
        if not materia or nota_completiva is None:
            continue
        try:
            nota_completiva = float(nota_completiva)
        except (TypeError, ValueError):
            continue
        if not (0 <= nota_completiva <= 100):
            continue

        # Calcular nota_final_completiva = promedio_anual × 0.80 + completiva × 0.20
        row = db.execute(
            "SELECT promedio FROM materias_calificaciones WHERE estudiante_id=? AND materia=? AND anio_escolar=?",
            (est_id, materia, anio),
        ).fetchone()
        promedio_anual     = row["promedio"] if row else None
        nota_final_comp    = None
        if promedio_anual is not None:
            nota_final_comp = round(promedio_anual * 0.80 + nota_completiva * 0.20, 2)

        db.execute(
            """
            INSERT INTO recuperaciones_pedagogicas
                (estudiante_id, materia, anio_escolar, nota_completiva,
                 nota_final_completiva, registrado_por, actualizado)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(estudiante_id, materia, anio_escolar) DO UPDATE SET
                nota_completiva       = excluded.nota_completiva,
                nota_final_completiva = excluded.nota_final_completiva,
                registrado_por        = excluded.registrado_por,
                actualizado           = datetime('now')
            """,
            (est_id, materia, anio, nota_completiva, nota_final_comp, _uid()),
        )
        guardadas += 1

    db.commit()
    _audit(db, _uid(), "completiva_guardada",
           f"est_id={est_id} anio={anio} materias={guardadas}")

    return jsonify({"ok": True, "guardadas": guardadas})


@promocion_bp.route("/recuperacion/<int:est_id>", methods=["POST"])
@login_required
@coord_required
def guardar_recuperacion(est_id: int):
    """
    POST /api/promocion/recuperacion/123
    Body JSON:
    {
      "anio_escolar": "2025-2026",
      "notas": [
        {"materia": "Matemática", "nota_recuperacion": 74.0}
      ]
    }

    Guarda nota_recuperacion en recuperaciones_pedagogicas.
    Idempotente — actualiza si ya existe.
    """
    d     = request.get_json(silent=True) or {}
    anio  = d.get("anio_escolar") or _anio_escolar_actual()
    notas = d.get("notas", [])

    if not notas:
        return jsonify({"ok": False, "error": "Campo 'notas' requerido"}), 400

    db        = get_db()
    guardadas = 0

    for item in notas:
        materia       = (item.get("materia") or "").strip()
        nota_rec      = item.get("nota_recuperacion")
        if not materia or nota_rec is None:
            continue
        try:
            nota_rec = float(nota_rec)
        except (TypeError, ValueError):
            continue
        if not (0 <= nota_rec <= 100):
            continue

        estado = "APROBADA" if nota_rec >= 70 else "REPROBADA"

        db.execute(
            """
            INSERT INTO recuperaciones_pedagogicas
                (estudiante_id, materia, anio_escolar,
                 nota_recuperacion, estado_recuperacion, registrado_por, actualizado)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(estudiante_id, materia, anio_escolar) DO UPDATE SET
                nota_recuperacion  = excluded.nota_recuperacion,
                estado_recuperacion = excluded.estado_recuperacion,
                registrado_por     = excluded.registrado_por,
                actualizado        = datetime('now')
            """,
            (est_id, materia, anio, nota_rec, estado, _uid()),
        )
        guardadas += 1

    db.commit()
    _audit(db, _uid(), "recuperacion_guardada",
           f"est_id={est_id} anio={anio} materias={guardadas}")

    return jsonify({"ok": True, "guardadas": guardadas})


# ── Récord de Notas ───────────────────────────────────────────────────────────

@promocion_bp.route("/record-notas/<int:est_id>")
@login_required
@coord_required
def record_notas_pdf(est_id: int):
    """
    GET /api/promocion/record-notas/123?anio_escolar=2025-2026

    Genera el Récord de Notas en PDF.
    Conforme Ordenanza No. 1-2016 MINERD (Pruebas Nacionales).
    """
    import io
    import unicodedata
    import datetime as _dt
    import base64 as _b64

    from flask import make_response
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle,
        Paragraph, Spacer, HRFlowable
    )
    from reportlab.platypus import Image as RLImage
    from core.helpers import _get_config_centro

    anio = request.args.get("anio_escolar") or _anio_escolar_actual()
    db   = get_db()

    # 1. Datos del estudiante
    est = db.execute("SELECT * FROM estudiantes WHERE id = ?", (est_id,)).fetchone()
    if not est:
        return jsonify({"ok": False, "error": "Estudiante no encontrado"}), 404
    est = dict(est)

    # 2. Materias — deduplicar (misma materia en MAYÚS y Title Case)
    def _norm(s):
        return unicodedata.normalize("NFKD", (s or "").lower().strip()) \
                          .encode("ascii", "ignore").decode("ascii")

    rows = db.execute(
        "SELECT materia, p1, p2, p3, p4, promedio FROM materias_calificaciones "
        "WHERE estudiante_id=? AND anio_escolar=? ORDER BY materia",
        (est_id, anio),
    ).fetchall()

    seen: dict = {}
    for r in rows:
        key = _norm(r["materia"])
        if key not in seen or (r["promedio"] or 0) > (seen[key]["promedio"] or 0):
            seen[key] = dict(r)

    ACAD_KEYS = ["lengua", "matem", "social", "natural", "fisica", "ingles",
                 "formacion", "fihr", "historia del arte", "historia dominicana",
                 "educacion artistica"]
    materias_acad = []
    materias_tecn = []
    for key, m in sorted(seen.items(), key=lambda x: x[1]["materia"].lower()):
        if any(a in key for a in ACAD_KEYS):
            materias_acad.append(m)
        else:
            materias_tecn.append(m)

    # 4 áreas Pruebas Nacionales (Ord. 1-2016)
    AREAS_MINERD = [
        ("Lengua Española",           ["lengua"]),
        ("Matemática",                ["matem"]),
        ("Ciencias Sociales",         ["social"]),
        ("Ciencias de la Naturaleza", ["natural"]),
    ]
    notas_minerd = []
    for nombre_area, claves in AREAS_MINERD:
        val = next((m["promedio"] for k, m in seen.items() if any(c in k for c in claves)), None)
        notas_minerd.append((nombre_area, val))

    vals_mn = [v for _, v in notas_minerd if v]
    prom_presentacion = round(sum(vals_mn) / len(vals_mn), 2) if vals_mn else None
    todos_prom = [m["promedio"] for m in seen.values() if m["promedio"]]
    prom_general = round(sum(todos_prom) / len(todos_prom), 2) if todos_prom else None

    # 3. Config centro
    cfg    = _get_config_centro()
    nom_c  = cfg.get("nombre",    "C.E. Benito Juárez")
    mod_c  = cfg.get("modalidad", "Modalidad en Artes · Nivel Secundario")
    dir_c  = cfg.get("direccion", "")
    tel_c  = cfg.get("telefono",  "")
    lg_b64 = cfg.get("logo_base64")

    # 4. Paleta
    C_HEADER  = colors.HexColor("#024959")
    C_ACCENT  = colors.HexColor("#037F8C")
    C_LIGHT   = colors.HexColor("#f0f9fa")
    C_BORDER  = colors.HexColor("#d1e8ec")
    C_GRAY    = colors.HexColor("#6b7280")
    C_GREEN   = colors.HexColor("#15803d")
    C_RED     = colors.HexColor("#b91c1c")
    C_ROW_ALT = colors.HexColor("#f8fafb")

    def ps(name, **kw):
        d = dict(fontName="Helvetica", fontSize=9, leading=12,
                 textColor=colors.HexColor("#1a1a2e"))
        d.update(kw)
        return ParagraphStyle(name, **d)

    st_label = ps("lb", fontName="Helvetica-Bold", fontSize=8, textColor=C_GRAY)
    st_value = ps("vl", fontSize=9)
    st_th    = ps("th", fontName="Helvetica-Bold", fontSize=7.5, textColor=colors.white)
    st_td    = ps("td", fontSize=8)
    st_tdc   = ps("tc", fontSize=8, alignment=TA_CENTER)
    st_note  = ps("nt", fontName="Helvetica-Oblique", fontSize=7, textColor=C_GRAY, alignment=TA_CENTER)
    st_sect  = ps("sc", fontName="Helvetica-Bold", fontSize=8, textColor=C_HEADER, spaceBefore=8, spaceAfter=3)

    def fmt(v):
        if v is None: return "—"
        try:   return f"{float(v):.1f}"
        except: return "—"

    # 5. Construir PDF
    buf = io.BytesIO()
    PW, PH = A4
    MAR = 1.8 * cm
    W   = PW - 2 * MAR

    doc = SimpleDocTemplate(buf, pagesize=A4,
        leftMargin=MAR, rightMargin=MAR, topMargin=MAR, bottomMargin=MAR,
        title=f"Récord de Notas — {est.get('nombre','')} {est.get('apellido','')}",
        author="Axula — MINERD")
    story = []

    # Encabezado
    logo_img = None
    if lg_b64 and lg_b64.startswith("data:image/"):
        try:
            _, _raw = lg_b64.split(",", 1)
            logo_img = RLImage(io.BytesIO(_b64.b64decode(_raw)), width=2*cm, height=2*cm)
        except Exception:
            pass

    centro_col = [
        Paragraph("REPÚBLICA DOMINICANA — MINISTERIO DE EDUCACIÓN — MINERD",
                  ps("brd", fontSize=7, textColor=C_GRAY, alignment=TA_CENTER, spaceAfter=1)),
        Paragraph(nom_c, ps("bn", fontName="Helvetica-Bold", fontSize=12, textColor=C_HEADER,
                             alignment=TA_CENTER, leading=14, spaceAfter=2)),
        Paragraph(mod_c, ps("bm", fontSize=8, textColor=C_GRAY, alignment=TA_CENTER)),
    ]
    info_line = " · ".join(filter(None, [dir_c, tel_c]))
    if info_line:
        centro_col.append(Paragraph(info_line, ps("bi", fontSize=7, textColor=C_GRAY, alignment=TA_CENTER)))

    tit_col = [
        Paragraph("RÉCORD DE<br/>NOTAS", ps("rt", fontName="Helvetica-Bold", fontSize=10,
                   textColor=C_HEADER, alignment=TA_RIGHT, leading=13, spaceAfter=4)),
        Paragraph(f"Año Escolar<br/>{anio}", ps("ra", fontSize=8, textColor=C_ACCENT,
                   alignment=TA_RIGHT, leading=11)),
    ]
    TW = 3.2 * cm
    LW = 2.3 * cm
    hdr_data = [[logo_img, centro_col, tit_col]] if logo_img else [[centro_col, tit_col]]
    hdr_cols = [LW, W-LW-TW, TW] if logo_img else [W-TW, TW]
    hdr = Table(hdr_data, colWidths=hdr_cols)
    hdr.setStyle(TableStyle([
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("TOPPADDING",(0,0),(-1,-1),0), ("BOTTOMPADDING",(0,0),(-1,-1),0),
        ("LEFTPADDING",(0,0),(-1,-1),3), ("RIGHTPADDING",(0,0),(-1,-1),3),
    ]))
    story += [hdr,
              HRFlowable(width=W, thickness=2, color=C_HEADER, spaceBefore=6, spaceAfter=4),
              HRFlowable(width=W, thickness=1, color=C_ACCENT, spaceAfter=8)]

    # Datos del estudiante
    nombre_est = f"{est.get('nombre','').strip()} {est.get('apellido','').strip()}".upper()
    condicion  = est.get("condicion") or "ACTIVO"
    cond_label = "CANDIDATO A PRUEBAS NACIONALES" if condicion == "CANDIDATO_PRUEBAS" else condicion
    cond_color = C_GREEN if condicion == "CANDIDATO_PRUEBAS" else C_GRAY

    info_data = [
        [Paragraph("<b>Nombre:</b>",    st_label), Paragraph(nombre_est, st_value),
         Paragraph("<b>Cédula:</b>",    st_label), Paragraph(est.get("cedula") or "—", st_value)],
        [Paragraph("<b>Grado:</b>",     st_label), Paragraph(est.get("grado") or "—", st_value),
         Paragraph("<b>Mención:</b>",   st_label), Paragraph(est.get("mencion") or est.get("curso") or "—", st_value)],
        [Paragraph("<b>Condición:</b>", st_label),
         Paragraph(cond_label, ps("cl", fontSize=9, fontName="Helvetica-Bold", textColor=cond_color)),
         Paragraph("<b>Año Escolar:</b>", st_label), Paragraph(anio, st_value)],
    ]
    info_t = Table(info_data, colWidths=[2.5*cm, W/2-2.5*cm, 2.5*cm, W/2-2.5*cm])
    info_t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),C_LIGHT), ("BOX",(0,0),(-1,-1),0.5,C_BORDER),
        ("INNERGRID",(0,0),(-1,-1),0.3,C_BORDER),
        ("TOPPADDING",(0,0),(-1,-1),5), ("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("LEFTPADDING",(0,0),(-1,-1),7), ("RIGHTPADDING",(0,0),(-1,-1),7),
    ]))
    story.append(info_t)
    if condicion == "CANDIDATO_PRUEBAS":
        story.append(Spacer(1, 3))
        story.append(Paragraph(
            "Habilitado como candidato a Pruebas Nacionales — Ordenanza No. 1-2016 MINERD",
            ps("ord", fontSize=7, textColor=C_ACCENT, alignment=TA_CENTER,
               fontName="Helvetica-Oblique")))

    # Función para construir tabla de materias
    def tabla_materias(materias, titulo):
        if not materias:
            return
        story.append(Spacer(1, 8))
        story.append(Paragraph(titulo, st_sect))
        CW = [W*0.38, W*0.10, W*0.10, W*0.10, W*0.10, W*0.12, W*0.10]
        head = [Paragraph(h, st_th) for h in
                ["Asignatura", "P1", "P2", "P3", "P4", "Promedio", "Estado"]]
        trows = [head]
        ts = [
            ("BACKGROUND",(0,0),(-1,0),C_HEADER),
            ("ALIGN",(1,0),(-1,-1),"CENTER"), ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ("TOPPADDING",(0,0),(-1,-1),4), ("BOTTOMPADDING",(0,0),(-1,-1),4),
            ("LEFTPADDING",(0,0),(-1,-1),5), ("RIGHTPADDING",(0,0),(-1,-1),5),
            ("BOX",(0,0),(-1,-1),0.5,C_BORDER), ("INNERGRID",(0,0),(-1,-1),0.3,C_BORDER),
        ]
        for i, m in enumerate(materias, 1):
            prom = m.get("promedio")
            apro = (prom or 0) >= 70
            c_p  = C_GREEN if apro else C_RED
            trows.append([
                Paragraph(m["materia"].title(), st_td),
                Paragraph(fmt(m.get("p1")), st_tdc),
                Paragraph(fmt(m.get("p2")), st_tdc),
                Paragraph(fmt(m.get("p3")), st_tdc),
                Paragraph(fmt(m.get("p4")), st_tdc),
                Paragraph(fmt(prom), ps(f"p{i}", fontSize=8, fontName="Helvetica-Bold",
                                         alignment=TA_CENTER, textColor=c_p)),
                Paragraph("APROBADA" if apro else "REPROBADA",
                           ps(f"e{i}", fontSize=7, alignment=TA_CENTER, textColor=c_p)),
            ])
            ts.append(("BACKGROUND",(0,i),(-1,i), C_ROW_ALT if i%2==0 else colors.white))
        t = Table(trows, colWidths=CW, repeatRows=1)
        t.setStyle(TableStyle(ts))
        story.append(t)

    mencion = (est.get("mencion") or "").upper()
    tabla_materias(materias_acad, "ÁREA ACADÉMICA")
    tabla_materias(materias_tecn, f"ÁREA TÉCNICA — MENCIÓN {mencion}" if mencion else "ÁREA TÉCNICA")

    # Nota de presentación MINERD
    story += [Spacer(1,10),
              HRFlowable(width=W, thickness=0.5, color=C_BORDER, spaceAfter=4),
              Paragraph("NOTA DE PRESENTACIÓN PARA PRUEBAS NACIONALES", st_sect),
              Paragraph(
                  "Promedio de las 4 áreas evaluadas (Ord. No. 1-2016). "
                  "Nota final bachillerato = 70% nota de centro + 30% Prueba Nacional.",
                  ps("np", fontSize=7, textColor=C_GRAY, spaceAfter=5))]

    mn_rows = [[Paragraph("<b>Área</b>", st_label),
                Paragraph("<b>Promedio de Centro</b>",
                          ps("ph", fontName="Helvetica-Bold", fontSize=8, alignment=TA_CENTER))]]
    for nombre_area, val in notas_minerd:
        apro = (val or 0) >= 70
        mn_rows.append([
            Paragraph(nombre_area, st_td),
            Paragraph(fmt(val), ps(f"m{nombre_area[:3]}", fontSize=9, fontName="Helvetica-Bold",
                                    alignment=TA_CENTER,
                                    textColor=C_GREEN if apro else (C_GRAY if val is None else C_RED))),
        ])
    apro_p = (prom_presentacion or 0) >= 70
    mn_rows.append([
        Paragraph("<b>Promedio General de Presentación</b>",
                  ps("mpk", fontName="Helvetica-Bold", fontSize=9, textColor=C_HEADER)),
        Paragraph(fmt(prom_presentacion),
                  ps("mpv", fontName="Helvetica-Bold", fontSize=11, alignment=TA_CENTER,
                     textColor=C_GREEN if apro_p else C_RED)),
    ])
    mn_t = Table(mn_rows, colWidths=[W*0.65, W*0.35])
    mn_t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),C_LIGHT),
        ("BACKGROUND",(0,-1),(-1,-1),colors.HexColor("#ecfdf5")),
        ("BOX",(0,0),(-1,-1),0.5,C_BORDER), ("INNERGRID",(0,0),(-1,-1),0.3,C_BORDER),
        ("TOPPADDING",(0,0),(-1,-1),5), ("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("LEFTPADDING",(0,0),(-1,-1),8), ("RIGHTPADDING",(0,0),(-1,-1),8),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
    ]))
    story.append(mn_t)

    # Promedio general
    story.append(Spacer(1, 5))
    pg_apro = (prom_general or 0) >= 70
    pg_t = Table([[
        Paragraph("Promedio General (todas las asignaturas):",
                  ps("pgl", fontName="Helvetica-Bold", fontSize=9)),
        Paragraph(fmt(prom_general),
                  ps("pgv", fontName="Helvetica-Bold", fontSize=12, alignment=TA_CENTER,
                     textColor=C_GREEN if pg_apro else C_RED)),
    ]], colWidths=[W*0.65, W*0.35])
    pg_t.setStyle(TableStyle([
        ("BOX",(0,0),(-1,-1),0.5,C_BORDER),
        ("TOPPADDING",(0,0),(-1,-1),6), ("BOTTOMPADDING",(0,0),(-1,-1),6),
        ("LEFTPADDING",(0,0),(-1,-1),8), ("RIGHTPADDING",(0,0),(-1,-1),8),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
    ]))
    story.append(pg_t)

    # Firmas
    MESES = ["enero","febrero","marzo","abril","mayo","junio","julio",
             "agosto","septiembre","octubre","noviembre","diciembre"]
    hoy = _dt.date.today()
    fecha_txt = f"Santo Domingo, {hoy.day} de {MESES[hoy.month-1]} de {hoy.year}"
    story += [Spacer(1,20),
              Paragraph(fecha_txt, ps("fch", alignment=TA_CENTER, fontSize=8, textColor=C_GRAY)),
              Spacer(1,18)]

    ln = "_" * 28
    firma_t = Table([[
        Paragraph(f"{ln}<br/><b>Director/a del Centro</b>",
                  ps("f1", alignment=TA_CENTER, fontSize=8, leading=14)),
        Paragraph(f"{ln}<br/><b>Secretaria Docente</b>",
                  ps("f2", alignment=TA_CENTER, fontSize=8, leading=14)),
        Paragraph(f"{ln}<br/><b>Director/a del Distrito</b>",
                  ps("f3", alignment=TA_CENTER, fontSize=8, leading=14)),
    ]], colWidths=[W/3]*3)
    firma_t.setStyle(TableStyle([
        ("TOPPADDING",(0,0),(-1,-1),4), ("BOTTOMPADDING",(0,0),(-1,-1),4),
        ("ALIGN",(0,0),(-1,-1),"CENTER"), ("VALIGN",(0,0),(-1,-1),"BOTTOM"),
    ]))
    story.append(firma_t)
    story += [Spacer(1,12),
              HRFlowable(width=W, thickness=0.5, color=C_BORDER, spaceAfter=3),
              Paragraph(f"Generado por Axula · {nom_c} · {fecha_txt}", st_note)]

    doc.build(story)
    buf.seek(0)

    nombre_archivo = f"record_{est.get('apellido','').replace(' ','_')}_{est_id}.pdf"
    resp = make_response(buf.read())
    resp.headers["Content-Type"]        = "application/pdf"
    resp.headers["Content-Disposition"] = f'inline; filename="{nombre_archivo}"'
    return resp
