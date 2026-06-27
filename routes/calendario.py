# -*- coding: utf-8 -*-
"""Blueprint: calendario"""

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
from core.helpers import _anio_escolar_actual, _audit, _generar_ics, _get_config_centro, _parse_ics_date
from core.ia import _get_groq_client, groq_client, construir_prompt, construir_prompt_planificacion, construir_prompt_rubrica, construir_prompt_estrategia
from core.excel import _parsear_boletin_bj, _buscar_o_crear_estudiante, _detectar_mencion_listado, _limpiar_nota
from core.pdf import _generar_pdf_acuerdo

logger = logging.getLogger("axula")

calendario_bp = Blueprint("calendario_bp", __name__)

@calendario_bp.route("/calendario")
@login_required
def vista_calendario():
    """Vista visual del calendario escolar."""
    u = get_usuario()
    rol = _normalizar_rol(u.get("rol", ""))
    puede_editar = rol in {"directora","coordinador_general","coordinador_primer_ciclo","coordinador_segundo_ciclo"}
    return render_template("calendario.html", current_user=u, puede_editar=puede_editar)


@calendario_bp.route("/api/calendario", methods=["GET"])
@login_required
def get_calendario():
    anio = request.args.get("anio_escolar", "2025-2026")
    mes  = request.args.get("mes", "")
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        q = "SELECT * FROM calendario_escolar WHERE anio_escolar=?"
        p = [anio]
        if mes:
            q += " AND substr(fecha,1,7)=?"
            p.append(mes)
        q += " ORDER BY fecha"
        rows = conn.execute(q, p).fetchall()
    return jsonify([dict(r) for r in rows])


@calendario_bp.route("/api/calendario", methods=["POST"])
@login_required
def crear_dia_calendario():
    u = get_usuario()
    rol_n = _normalizar_rol(u.get("rol",""))
    if rol_n not in {"directora","coordinador_general","coordinador_primer_ciclo","coordinador_segundo_ciclo"}:
        return jsonify({"error": "Sin permisos"}), 403

    data = request.get_json() or {}
    fecha       = data.get("fecha","").strip()
    tipo        = data.get("tipo","feriado")
    descripcion = data.get("descripcion","").strip()
    anio        = data.get("anio_escolar","2025-2026")

    if not fecha:
        return jsonify({"error": "La fecha es requerida"}), 400

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        try:
            conn.execute("""
                INSERT INTO calendario_escolar (fecha, tipo, descripcion, anio_escolar, creado_por)
                VALUES (?,?,?,?,?)
            """, (fecha, tipo, descripcion, anio, u["id"]))
            conn.commit()
        except Exception:
            conn.execute("""
                UPDATE calendario_escolar
                   SET tipo=?, descripcion=?, anio_escolar=?
                 WHERE fecha=?
            """, (tipo, descripcion, anio, fecha))
            conn.commit()
    return jsonify({"ok": True})


@calendario_bp.route("/api/calendario/<fecha>", methods=["DELETE"])
@login_required
def eliminar_dia_calendario(fecha):
    u = get_usuario()
    rol_n = _normalizar_rol(u.get("rol",""))
    if rol_n not in {"directora","coordinador_general"}:
        return jsonify({"error": "Sin permisos"}), 403
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.execute("DELETE FROM calendario_escolar WHERE fecha=?", (fecha,))
        conn.commit()
    return jsonify({"ok": True})


@calendario_bp.route("/api/calendario/dias-habiles", methods=["GET"])
@login_required
def get_dias_habiles():
    """Retorna el total de días hábiles de un mes dado el calendario escolar."""
    import calendar as _cal
    mes  = int(request.args.get("mes", 1))
    anio = int(request.args.get("anio", 2025))
    anio_esc = request.args.get("anio_escolar", "2025-2026")

    # Total de días del mes
    _, total_dias = _cal.monthrange(anio, mes)

    # Días no laborables del calendario escolar en ese mes
    mes_str = f"{anio:04d}-{mes:02d}"
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        no_laborables = conn.execute("""
            SELECT fecha FROM calendario_escolar
            WHERE substr(fecha,1,7)=? AND anio_escolar=?
        """, (mes_str, anio_esc)).fetchall()
        fechas_no_lab = {r[0] for r in no_laborables}

    # Contar días hábiles (lunes–viernes que no estén en el calendario)
    habiles = 0
    for dia in range(1, total_dias + 1):
        import datetime as _dt
        d = _dt.date(anio, mes, dia)
        fecha_str = d.isoformat()
        if d.weekday() < 5 and fecha_str not in fechas_no_lab:  # 0=Lun, 4=Vie
            habiles += 1

    return jsonify({
        "mes": mes, "anio": anio,
        "total_dias": total_dias,
        "dias_habiles": habiles,
        "dias_no_laborables": len(fechas_no_lab),
        "fechas_no_laborables": list(fechas_no_lab)
    })


# ══════════════════════════════════════════════════════════════════════════════
#  INTEGRACIÓN GOOGLE CALENDAR
#  Sin OAuth — usa el formato iCal estándar (.ics):
#  • EXPORTAR: genera un .ics descargable para importar a Google Calendar
#  • IMPORTAR: lee un .ics de Google Calendar (URL pública) y sincroniza
# ══════════════════════════════════════════════════════════════════════════════


@calendario_bp.route("/api/config-centro", methods=["GET"])
@login_required
def get_config_centro():
    """Devuelve la configuración actual del centro (sin el logo en base64 completo)."""
    cfg = _get_config_centro()
    # Indicar si tiene logo sin devolver los bytes completos en el GET
    tiene_logo = bool(cfg.get("logo_base64"))
    resp = {k: v for k, v in cfg.items() if k != "logo_base64"}
    resp["tiene_logo"] = tiene_logo
    # Si tiene logo, devolver una vista previa (primeros chars suficientes para <img src>)
    if tiene_logo:
        resp["logo_preview"] = cfg["logo_base64"]  # data URL completo para preview
    return jsonify({"ok": True, "config": resp})


@calendario_bp.route("/api/config-centro", methods=["POST"])
@login_required
def save_config_centro():
    """
    Guarda la configuración del centro.
    Acepta JSON con los campos de texto, o multipart/form-data con el logo.
    Solo coordinadores y directora pueden modificar.
    """
    u = get_usuario()
    rol_n = _normalizar_rol(u.get("rol", ""))
    if rol_n not in ROLES_COORD and not u.get("es_directora"):
        return jsonify({"error": "Sin permisos"}), 403

    campos = {}

    # Modo multipart (logo + campos)
    if request.content_type and "multipart" in request.content_type:
        for campo in ["nombre", "modalidad", "direccion", "pais", "telefono", "email"]:
            val = request.form.get(campo, "").strip()
            if val:
                campos[campo] = val
        # Logo
        if "logo" in request.files:
            file = request.files["logo"]
            if file and file.filename:
                ext = file.filename.rsplit(".", 1)[-1].lower()
                if ext not in ("jpg", "jpeg", "png", "gif", "webp"):
                    return jsonify({"error": "Formato de imagen no válido. Usa JPG, PNG o WebP"}), 400
                import base64 as _b64
                data = file.read()
                if len(data) > 500_000:  # 500 KB máx
                    return jsonify({"error": "El logo no puede superar 500 KB"}), 400
                mime = "image/jpeg" if ext in ("jpg","jpeg") else f"image/{ext}"
                campos["logo_base64"] = f"data:{mime};base64,{_b64.b64encode(data).decode()}"
    else:
        # Modo JSON (solo campos de texto)
        d = request.get_json(force=True) or {}
        for campo in ["nombre", "modalidad", "direccion", "pais", "telefono", "email"]:
            if campo in d:
                campos[campo] = str(d[campo]).strip()

    if not campos:
        return jsonify({"error": "No se recibieron datos para guardar"}), 400

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        exists = conn.execute("SELECT id FROM configuracion_centro WHERE id=1").fetchone()
        if exists:
            # UPDATE solo los campos que vinieron en la request
            for col, val in campos.items():
                conn.execute(
                    f"UPDATE configuracion_centro SET {col}=?, actualizado=datetime('now') WHERE id=1",
                    (val,)
                )
        else:
            # Primera vez — insertar con defaults + lo que llegó
            base = dict(DEFAULTS_CENTRO)
            base.update(campos)
            conn.execute(
                """INSERT INTO configuracion_centro
                   (id, nombre, modalidad, direccion, pais, telefono, email, logo_base64)
                   VALUES (1,?,?,?,?,?,?,?)""",
                (base["nombre"], base["modalidad"], base["direccion"],
                 base["pais"], base["telefono"], base["email"], base.get("logo_base64"))
            )

    _audit("config_centro", f"Configuración del centro actualizada por {u['nombre']}",
           "configuracion_centro")

    return jsonify({"ok": True, "campos_guardados": list(campos.keys())})


@calendario_bp.route("/api/calendario/exportar-ics")
@login_required
def exportar_calendario_ics():
    """
    Exporta el calendario escolar como archivo .ics compatible con
    Google Calendar, Apple Calendar y Outlook.
    ?anio_escolar=2025-2026
    """
    anio = request.args.get("anio_escolar", _anio_escolar_actual())
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT fecha, tipo, descripcion FROM calendario_escolar "
            "WHERE anio_escolar=? ORDER BY fecha",
            (anio,)
        ).fetchall()

    if not rows:
        return jsonify({"error": "Sin eventos en el calendario para este año"}), 404

    eventos = [dict(r) for r in rows]
    ics_content = _generar_ics(eventos)

    from flask import Response
    return Response(
        ics_content,
        mimetype="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="calendario_bj_{anio}.ics"',
            "Content-Type": "text/calendar; charset=utf-8",
        }
    )


@calendario_bp.route("/api/calendario/importar-ics", methods=["POST"])
@login_required
def importar_calendario_ics():
    """
    Importa eventos desde un archivo .ics subido o desde una URL pública
    de Google Calendar (formato iCal).

    Body (multipart): file=<archivo.ics>   ← subir archivo
    Body (JSON):      { "url": "https://calendar.google.com/calendar/ical/..." }

    Los eventos se agregan al calendario_escolar con tipo='google_calendar'.
    No sobreescribe eventos existentes — hace UPSERT por fecha+descripcion.
    """
    u = get_usuario()
    rol_n = _normalizar_rol(u.get("rol", ""))
    if rol_n not in ROLES_COORD and not u.get("es_directora"):
        return jsonify({"error": "Sin permisos"}), 403

    anio = request.args.get("anio_escolar", _anio_escolar_actual())
    ics_text = None

    # Modo 1: archivo subido
    if "file" in request.files:
        f = request.files["file"]
        if not f.filename.lower().endswith(".ics"):
            return jsonify({"error": "El archivo debe ser .ics"}), 400
        raw_bytes = f.read()
        if not raw_bytes:
            return jsonify({"error": "El archivo está vacío"}), 400
        # Intentar UTF-8, luego latin-1 como fallback; quitar BOM si existe
        try:
            ics_text = raw_bytes.decode("utf-8-sig")   # utf-8-sig strips BOM automáticamente
        except Exception:
            ics_text = raw_bytes.decode("latin-1", errors="ignore")
        logger.info(f"[ics] archivo={f.filename} bytes={len(raw_bytes)} primeras_lineas={repr(ics_text[:200])}")

    # Modo 2: URL pública de Google Calendar
    elif request.is_json:
        d = request.get_json() or {}
        url = (d.get("url") or "").strip()
        if not url:
            return jsonify({"error": "Proporciona un archivo .ics o una URL de Google Calendar"}), 400
        # Validar que sea una URL de Google Calendar
        if "google.com/calendar" not in url and "googleusercontent.com" not in url:
            # Aceptar también URLs genéricas .ics
            if not url.endswith(".ics") and "ical" not in url.lower():
                return jsonify({"error": "La URL debe ser de Google Calendar o un archivo .ics público"}), 400
        try:
            import urllib.request as _ureq
            req = _ureq.Request(url, headers={"User-Agent": "Axula/1.0"})
            with _ureq.urlopen(req, timeout=15) as resp:
                ics_text = resp.read().decode("utf-8", errors="ignore")
        except Exception as ex:
            logger.warning(f"[CALENDARIO] Error descargando ICS: {ex}")
            return jsonify({
                "error": "No se pudo descargar el calendario. Verifica que la URL sea correcta y el calendario sea público.",
                "ayuda": "Asegúrate de que el calendario sea público. En Google Calendar: "
                         "Configuración del calendario → Permisos de acceso → Hacer público → "
                         "Copiar la dirección en formato iCal"
            }), 400
    else:
        return jsonify({"error": "Envía un archivo .ics o JSON con {url: ...}"}), 400

    # ── Parser iCal manual ────────────────────────────────────────────────────
    eventos = []
    current = {}
    in_event = False

    for raw_line in ics_text.splitlines():
        line = raw_line.strip()

        if line == "BEGIN:VEVENT":
            in_event = True
            current = {}
            continue
        if line == "END:VEVENT":
            in_event = False
            if current.get("fecha"):
                eventos.append(current)
            current = {}
            continue

        if not in_event:
            continue

        # Manejar líneas continuadas (empiezan con espacio o tab)
        if raw_line.startswith((" ", "\t")) and eventos:
            # Continuación de la línea anterior — ignorar por simplicidad
            continue

        if ":" in line:
            key, _, val = line.partition(":")
            key = key.split(";")[0].upper()  # quitar parámetros como VALUE=DATE
            val = val.strip()

            if key == "DTSTART":
                current["fecha"] = _parse_ics_date(val)
            elif key == "SUMMARY":
                current["titulo"] = val
            elif key == "DESCRIPTION":
                current["descripcion"] = val.replace("\\n", " ").replace("\\,", ",")[:200]
            elif key == "STATUS" and val == "CANCELLED":
                current["cancelado"] = True
            elif key == "RRULE" and "FREQ=YEARLY" in val.upper():
                current["rrule_yearly"] = True

    # ── Filtrar y expandir recurrencias anuales ───────────────────────────────
    anio_partes = anio.split("-")
    año_inicio  = int(anio_partes[0]) if anio_partes else 2025
    año_fin     = int(anio_partes[1]) if len(anio_partes) > 1 else año_inicio + 1

    eventos_filtrados = []
    for ev in eventos:
        if ev.get("cancelado") or not ev.get("fecha"):
            continue
        if ev.get("rrule_yearly"):
            # Generar la ocurrencia para cada año del rango escolar
            try:
                mes_dia = ev["fecha"][5:]  # "MM-DD"
                titulo  = ev.get("titulo") or ev.get("descripcion") or "Evento"
                for yr in range(año_inicio, año_fin + 1):
                    eventos_filtrados.append({"fecha": f"{yr}-{mes_dia}", "titulo": titulo})
            except Exception:
                pass
            continue
        try:
            año_ev = int(ev["fecha"][:4])
            if año_ev < año_inicio or año_ev > año_fin:
                continue
        except Exception:
            continue
        eventos_filtrados.append(ev)

    if not eventos_filtrados:
        return jsonify({
            "ok": False,
            "error": f"No se encontraron eventos en el rango {anio} (parseados: {len(eventos)})",
            "total_parseados": len(eventos),
        })

    # ── Insertar en BD ────────────────────────────────────────────────────────
    insertados = 0
    actualizados = 0
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        for ev in eventos_filtrados:
            titulo = (ev.get("titulo") or ev.get("descripcion") or "Evento Google Calendar")[:200]
            existing = conn.execute(
                "SELECT id FROM calendario_escolar WHERE fecha=?", (ev["fecha"],)
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE calendario_escolar SET descripcion=?, tipo='google_calendar' WHERE fecha=?",
                    (titulo, ev["fecha"])
                )
                actualizados += 1
            else:
                try:
                    conn.execute(
                        """INSERT INTO calendario_escolar
                           (fecha, tipo, descripcion, anio_escolar, creado_por)
                           VALUES (?,?,?,?,?)""",
                        (ev["fecha"], "google_calendar", titulo, anio, u["id"])
                    )
                    insertados += 1
                except Exception as _e:
                    logger.warning(f"[calendario] Excepción silenciada")

    # Audit
    _audit("importar_calendario",
           f"Importados {insertados} eventos Google Calendar, {actualizados} actualizados ({anio})",
           "calendario_escolar")

    return jsonify({
        "ok": True,
        "insertados":  insertados,
        "actualizados": actualizados,
        "total_parseados": len(eventos),
        "en_rango": len(eventos_filtrados),
        "anio_escolar": anio,
    })


@calendario_bp.route("/api/calendario/sincronizar-gcal", methods=["POST"])
@login_required
def sincronizar_gcal():
    """
    Sincronización rápida desde una URL iCal guardada en .env como GCAL_URL.
    Si no hay URL, devuelve instrucciones.
    POST sin body — usa la URL configurada automáticamente.
    """
    u = get_usuario()
    if _normalizar_rol(u.get("rol", "")) not in ROLES_COORD and not u.get("es_directora"):
        return jsonify({"error": "Sin permisos"}), 403

    gcal_url = os.environ.get("GCAL_URL", "").strip()
    if not gcal_url:
        return jsonify({
            "ok": False,
            "error": "GCAL_URL no configurada",
            "ayuda": (
                "En Google Calendar: abre el calendario del centro → "
                "⋮ Configuración → Integraciones → Dirección en formato iCal → "
                "copia esa URL y agrégala en tu .env como:\n"
                "GCAL_URL=https://calendar.google.com/calendar/ical/TU_CALENDARIO/public/basic.ics"
            )
        })

    anio = request.args.get("anio_escolar", _anio_escolar_actual())

    # Delegar al endpoint de importación
    from flask import Request as _Req
    import json as _json
    with app.test_request_context(
        f"/api/calendario/importar-ics?anio_escolar={anio}",
        method="POST",
        data=_json.dumps({"url": gcal_url}),
        content_type="application/json",
        headers={"Cookie": request.headers.get("Cookie", "")}
    ):
        # Llamar la lógica directamente (no via HTTP)
        pass

    # Llamada directa a la lógica
    try:
        import urllib.request as _ureq
        req = _ureq.Request(gcal_url, headers={"User-Agent": "Axula/1.0"})
        with _ureq.urlopen(req, timeout=15) as resp:
            ics_text = resp.read().decode("utf-8", errors="ignore")
    except Exception as ex:
        return jsonify({"ok": False, "error": f"Error al conectar con Google Calendar: {ex}"})

    # Reusar el parser (misma lógica que importar_calendario_ics)
    # Guardamos URL y procesamos
    os.environ["_GCAL_ICS_TEMP"] = ics_text

    # Redirect to import logic by calling it directly
    from flask import Request
    with app.test_request_context(
        "/api/calendario/importar-ics",
        method="POST",
        json={"url": gcal_url}
    ):
        pass

    # Parse inline
    eventos = []
    current = {}
    in_event = False
    for raw_line in ics_text.splitlines():
        line = raw_line.strip()
        if line == "BEGIN:VEVENT":
            in_event = True; current = {}; continue
        if line == "END:VEVENT":
            in_event = False
            if current.get("fecha"): eventos.append(current)
            current = {}; continue
        if not in_event or ":" not in line: continue
        key, _, val = line.partition(":")
        key = key.split(";")[0].upper()
        if key in ("DTSTART", "DTSTART;VALUE=DATE"):
            current["fecha"] = _parse_ics_date(val)
        elif key == "SUMMARY":
            current["titulo"] = val
        elif key == "STATUS" and val == "CANCELLED":
            current["cancelado"] = True

    anio_partes = anio.split("-")
    año_i = int(anio_partes[0]) if anio_partes else 2025
    año_f = int(anio_partes[1]) if len(anio_partes) > 1 else año_i + 1

    eventos_ok = [e for e in eventos if not e.get("cancelado") and e.get("fecha")
                  and año_i <= int(e["fecha"][:4]) <= año_f]

    insertados = actualizados = 0
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        for ev in eventos_ok:
            titulo = (ev.get("titulo") or "Evento")[:200]
            ex_row = conn.execute(
                "SELECT id FROM calendario_escolar WHERE fecha=?", (ev["fecha"],)
            ).fetchone()
            if ex_row:
                conn.execute(
                    "UPDATE calendario_escolar SET descripcion=?,tipo='google_calendar' WHERE fecha=?",
                    (titulo, ev["fecha"])
                )
                actualizados += 1
            else:
                try:
                    conn.execute(
                        "INSERT INTO calendario_escolar (fecha,tipo,descripcion,anio_escolar,creado_por) "
                        "VALUES (?,?,?,?,?)",
                        (ev["fecha"], "google_calendar", titulo, anio, u["id"])
                    )
                    insertados += 1
                except Exception as _e:
                    logger.warning(f"[calendario] Excepción silenciada")

    _audit("sincronizar_gcal",
           f"Sync GCal: {insertados} nuevos, {actualizados} actualizados ({anio})",
           "calendario_escolar")

    return jsonify({
        "ok": True,
        "insertados": insertados,
        "actualizados": actualizados,
        "total_en_gcal": len(eventos),
        "en_rango": len(eventos_ok),
    })


# ══════════════════════════════════════════════════════════════════════════════
#  ASISTENCIA MENSUAL
# ══════════════════════════════════════════════════════════════════════════════


