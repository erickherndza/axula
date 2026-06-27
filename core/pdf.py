# -*- coding: utf-8 -*-
"""Generación de PDFs — acuerdo de compromiso y boletín."""

import logging
from io import BytesIO
from datetime import datetime

logger = logging.getLogger("axula")

def _generar_pdf_acuerdo(ac):
    """Genera el PDF del acuerdo con firmas incrustadas."""
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                     Table, TableStyle, HRFlowable, Image as RLImage)
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
    import io, json, base64

    PAGE_W, PAGE_H = A4
    MARGIN = 2 * cm
    W = PAGE_W - 2 * MARGIN

    C_HEADER = colors.HexColor("#024959")
    C_ACCENT = colors.HexColor("#037F8C")
    C_GRAY   = colors.HexColor("#6b7280")
    C_LIGHT  = colors.HexColor("#f0f9fa")
    C_BORDER = colors.HexColor("#d1e8ec")

    def ps(name, **kw):
        defs = dict(fontName="Helvetica", fontSize=10, leading=14,
                    textColor=colors.HexColor("#1a1a2e"))
        defs.update(kw)
        return ParagraphStyle(name, **defs)

    st_titulo   = ps("t",  fontName="Helvetica-Bold", fontSize=13, textColor=C_HEADER, alignment=TA_CENTER, spaceAfter=2)
    st_sub      = ps("s",  fontSize=9, textColor=C_GRAY, alignment=TA_CENTER, spaceAfter=1)
    st_sección  = ps("se", fontName="Helvetica-Bold", fontSize=10, textColor=C_ACCENT, spaceBefore=10, spaceAfter=4)
    st_body     = ps("b",  fontSize=9, leading=13, alignment=TA_JUSTIFY)
    st_item     = ps("i",  fontSize=9, leading=13, leftIndent=12)
    st_center   = ps("c",  fontSize=9, alignment=TA_CENTER)
    st_small    = ps("sm", fontSize=7.5, textColor=C_GRAY, alignment=TA_CENTER)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=MARGIN,
        title=f"Acuerdo-Compromiso {ac.get('numero_acuerdo','')}"
    )
    story = []

    # ── Configuración del centro desde BD ────────────────────────────────────
    _cfg          = _get_config_centro()
    _nombre       = _cfg.get("nombre",    "Centro Educativo en Artes Benito Juárez")
    _modalidad    = _cfg.get("modalidad", "Modalidad en Artes · Nivel Secundario")
    _direccion    = _cfg.get("direccion", "Prolongación Ovando, Cristo Rey, Santo Domingo, D.N.")
    _pais         = _cfg.get("pais",      "República Dominicana")
    _telefono     = _cfg.get("telefono",  "(809) 563-0241")
    _correo       = _cfg.get("email",     "centroenartesbenitojuarez@gmail.com")
    _logo_b64     = _cfg.get("logo_base64")

    # ── Logo desde BD ────────────────────────────────────────────────────────
    import base64 as _b64, io as _io
    _logo_img = None
    if _logo_b64 and _logo_b64.startswith("data:image/"):
        try:
            _, _raw = _logo_b64.split(",", 1)
            _logo_img = RLImage(_io.BytesIO(_b64.b64decode(_raw)), width=2.2*cm, height=2.2*cm)
            _logo_img.hAlign = "CENTER"
        except Exception:
            pass

    # ── Columna central: datos del centro ────────────────────────────────────
    _col_centro = [
        Paragraph(f"República Dominicana · Ministerio de Educación",
                  ps("rdom", fontSize=7, textColor=C_GRAY, alignment=TA_CENTER, spaceAfter=1)),
        Paragraph(_nombre,
                  ps("cnom", fontName="Helvetica-Bold", fontSize=13, textColor=C_HEADER,
                     alignment=TA_CENTER, leading=15, spaceAfter=2)),
        Paragraph(_modalidad,
                  ps("cmod", fontSize=8, textColor=C_GRAY, alignment=TA_CENTER, spaceAfter=3)),
        Paragraph(f"{_direccion} · {_pais}",
                  ps("cdir", fontSize=7.5, textColor=colors.HexColor("#444"),
                     alignment=TA_CENTER, spaceAfter=1)),
        Paragraph(f"Tel: {_telefono}  ·  {_correo}",
                  ps("ctel", fontSize=7.5, textColor=colors.HexColor("#444"), alignment=TA_CENTER)),
    ]

    # ── Columna derecha: título del documento ────────────────────────────────
    _col_titulo = [
        Paragraph("ACUERDO-COMPROMISO<br/>PEDAGÓGICO",
                  ps("xtit", fontName="Helvetica-Bold", fontSize=11, textColor=C_HEADER,
                     alignment=TA_RIGHT, leading=14, spaceAfter=4)),
        Paragraph(f"No. {ac.get('numero_acuerdo','S/N')}",
                  ps("xnum", fontSize=9, textColor=C_ACCENT, alignment=TA_RIGHT,
                     fontName="Helvetica-Bold", spaceAfter=2)),
        Paragraph(f"Fecha: {ac.get('fecha_acuerdo','—')}",
                  ps("xfec", fontSize=8, textColor=C_GRAY, alignment=TA_RIGHT)),
    ]

    _LOGO_W = 2.4*cm
    _TIT_W  = 4.5*cm
    if _logo_img:
        header_data = [[_logo_img, _col_centro, _col_titulo]]
        col_ws      = [_LOGO_W, W - _LOGO_W - _TIT_W, _TIT_W]
    else:
        header_data = [[_col_centro, _col_titulo]]
        col_ws      = [W - _TIT_W, _TIT_W]

    header_t = Table(header_data, colWidths=col_ws)
    header_t.setStyle(TableStyle([
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("ALIGN",         (-1,0),(-1,-1), "RIGHT"),
        ("TOPPADDING",    (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
        ("LEFTPADDING",   (0,0), (-1,-1), 3),
        ("RIGHTPADDING",  (0,0), (-1,-1), 3),
    ]))
    story.append(header_t)
    story.append(HRFlowable(width=W, thickness=2, color=C_HEADER, spaceBefore=8, spaceAfter=10))

    # ── Datos del estudiante ─────────────────────────────────────────────────
    story.append(Paragraph("DATOS DEL ESTUDIANTE", st_sección))
    info_data = [[
        Paragraph("<b>Estudiante:</b>", ps("l", fontSize=8, textColor=C_GRAY)),
        Paragraph(f"{ac.get('est_nombre','')} {ac.get('est_apellido','')}", ps("v", fontSize=9)),
        Paragraph("<b>Grado:</b>", ps("l", fontSize=8, textColor=C_GRAY)),
        Paragraph(f"{ac.get('grado','')} · {ac.get('curso','')}", ps("v", fontSize=9)),
    ]]
    info_t = Table(info_data, colWidths=[2*cm, W/2-2*cm, 1.8*cm, W/2-1.8*cm])
    info_t.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(-1,-1), C_LIGHT),
        ("BOX", (0,0),(-1,-1), 0.5, C_BORDER),
        ("TOPPADDING",(0,0),(-1,-1),5), ("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("LEFTPADDING",(0,0),(-1,-1),7), ("RIGHTPADDING",(0,0),(-1,-1),7),
    ]))
    story.append(info_t)
    story.append(Spacer(1, 8))

    # ── Contenido del acuerdo ────────────────────────────────────────────────
    contenido = ac.get("contenido_completo", "")
    if contenido:
        story.append(Paragraph("CONTENIDO DEL ACUERDO", st_sección))
        # Eliminar la sección ## FIRMAS del final antes de procesar
        # (las firmas van en el bloque dedicado al pie del PDF)
        contenido_sin_firmas = contenido
        for _marker in ["## FIRMAS", "## FIRMA", "# FIRMAS", "# FIRMA"]:
            _mi = contenido_sin_firmas.upper().rfind(_marker.upper())
            if _mi >= 0:
                contenido_sin_firmas = contenido_sin_firmas[:_mi].rstrip()
                break
        in_list = False
        for linea in contenido_sin_firmas.split("\n"):
            linea_raw = linea.rstrip()
            linea     = linea_raw.strip()
            if not linea:
                in_list = False
                continue

            # Encabezados ## y ###
            if linea.startswith("### "):
                txt = linea[4:].strip().replace("**","").replace("*","")
                story.append(Paragraph(txt, ps("h3", fontName="Helvetica-Bold", fontSize=9,
                                                textColor=colors.HexColor("#037F8C"), spaceBefore=8, spaceAfter=2)))
            elif linea.startswith("## "):
                txt = linea[3:].strip().replace("**","").replace("*","")
                story.append(Paragraph(txt, ps("h2", fontName="Helvetica-Bold", fontSize=10,
                                                textColor=C_HEADER, spaceBefore=12, spaceAfter=4)))
            elif linea.startswith("# "):
                txt = linea[2:].strip().replace("**","").replace("*","")
                story.append(Paragraph(txt, ps("h1", fontName="Helvetica-Bold", fontSize=11,
                                                textColor=C_HEADER, spaceBefore=14, spaceAfter=6)))
            # Items de lista
            elif linea.startswith(("- ", "• ", "* ")):
                txt = linea[2:].strip().replace("**","<b>",1).replace("**","</b>",1)
                story.append(Paragraph("&bull; " + txt, st_item))
            # Línea horizontal
            elif linea.startswith("---"):
                story.append(HRFlowable(width=W, thickness=0.5, color=C_BORDER, spaceAfter=4))
            # Texto normal — limpiar markdown inline
            else:
                txt = linea.replace("**", "").replace("__","").replace("*","").replace("_","")
                if txt:
                    story.append(Paragraph(txt, st_body))
    else:
        # Mostrar compromisos por partes si no hay contenido completo
        for clave, label in [
            ("compromisos_estudiante", "Compromisos del Estudiante"),
            ("compromisos_familia",    "Compromisos de la Familia"),
            ("compromisos_centro",     "Compromisos del Centro"),
        ]:
            raw = ac.get(clave)
            if not raw: continue
            try:
                items = json.loads(raw) if isinstance(raw, str) else raw
            except Exception:
                items = [str(raw)]
            story.append(Paragraph(label.upper(), st_sección))
            for item in (items if isinstance(items, list) else [items]):
                story.append(Paragraph(f"• {item}", st_item))

    story.append(Spacer(1, 14))

    # ── Base legal ───────────────────────────────────────────────────────────
    if ac.get("base_legal"):
        story.append(HRFlowable(width=W, thickness=0.5, color=C_BORDER))
        story.append(Paragraph(f"<i>Base legal: {ac['base_legal']}</i>",
                               ps("bl", fontSize=7.5, textColor=C_GRAY, spaceBefore=4, spaceAfter=8)))

    # ── Firmas ───────────────────────────────────────────────────────────────
    story.append(HRFlowable(width=W, thickness=1, color=C_HEADER, spaceBefore=8, spaceAfter=8))
    story.append(Paragraph("FIRMAS DE LOS COMPROMETIDOS", st_sección))

    def _firma_cell(firma_b64, label, sublabel=""):
        """Genera celda con imagen de firma o línea de firma."""
        elements = []
        if firma_b64 and firma_b64.startswith("data:image/"):
            try:
                header, data = firma_b64.split(",", 1)
                img_bytes = base64.b64decode(data)
                img_buf = io.BytesIO(img_bytes)
                img = RLImage(img_buf, width=4.5*cm, height=2*cm)
                img.hAlign = "CENTER"
                elements.append(img)
            except Exception:
                elements.append(Paragraph("_" * 28, st_center))
        else:
            elements.append(Spacer(1, 1.8*cm))
            elements.append(Paragraph("_" * 28, st_center))
        elements.append(Paragraph(f"<b>{label}</b>", st_small))
        if sublabel:
            elements.append(Paragraph(sublabel, st_small))
        return elements

    # Fila 1: Estudiante + Tutor
    f1_est   = _firma_cell(None, "Estudiante", ac.get("est_nombre","") + " " + ac.get("est_apellido",""))
    f1_tutor = _firma_cell(ac.get("firma_tutor"), "Padre / Madre / Tutor/a")
    # Fila 2: Coordinador + Psicóloga/Director
    f2_coord = _firma_cell(ac.get("firma_coordinador"), "Coordinador/a")
    f2_psico = _firma_cell(ac.get("firma_psicologa") or ac.get("firma_director"),
                           "Orientador/a o Director/a", ac.get("generado_por_nombre",""))

    from reportlab.platypus import KeepTogether

    def _firma_tabla(cel_izq, cel_der):
        data = [[cel_izq, cel_der]]
        t = Table(data, colWidths=[W/2-0.5*cm]*2, hAlign="CENTER")
        t.setStyle(TableStyle([
            ("VALIGN", (0,0),(-1,-1), "BOTTOM"),
            ("ALIGN",  (0,0),(-1,-1), "CENTER"),
            ("TOPPADDING",(0,0),(-1,-1),4),
            ("BOTTOMPADDING",(0,0),(-1,-1),4),
        ]))
        return t

    story.append(_firma_tabla(f1_est, f1_tutor))
    story.append(Spacer(1, 10))
    story.append(_firma_tabla(f2_coord, f2_psico))

    # ── Estado de firmas ─────────────────────────────────────────────────────
    story.append(Spacer(1, 8))
    if ac.get("firmado"):
        story.append(Paragraph(
            f"✓ Documento firmado digitalmente el {ac.get('fecha_firma','—')}",
            ps("ok", fontSize=8, textColor=colors.HexColor("#15803d"), alignment=TA_CENTER)
        ))
    else:
        story.append(Paragraph(
            "⚠ Pendiente de firma — este documento no tiene validez hasta ser firmado por todas las partes",
            ps("pend", fontSize=7.5, textColor=colors.HexColor("#b45309"), alignment=TA_CENTER)
        ))

    # ── Footer ───────────────────────────────────────────────────────────────
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width=W, thickness=0.5, color=C_BORDER))
    from datetime import date as _d
    story.append(Paragraph(
        f"Generado por Axula · C.E. Benito Juárez · {_d.today().strftime('%d/%m/%Y')}",
        ps("ft", fontSize=7, textColor=C_GRAY, alignment=TA_CENTER, spaceBefore=4)
    ))

    doc.build(story)
    buf.seek(0)

    from flask import Response
    nombre = f"{ac.get('est_nombre','')}_{ac.get('est_apellido','')}".replace(" ","_")
    fname  = f"Acuerdo_{ac.get('numero_acuerdo','SN')}_{nombre}.pdf"
    return Response(
        buf.read(),
        mimetype="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'}
    )


