# -*- coding: utf-8 -*-
"""Blueprint: digitador — Portal de Digitación de datos académicos"""

import sqlite3
import logging
import json as _json
import os
from datetime import datetime, date, timedelta
from flask import (
    Blueprint, render_template, request, jsonify, session,
    redirect, url_for, Response,
)

from core.constants import *
from core.database import get_db, cache_get, cache_set, cache_bust
from core.auth import (
    _normalizar_rol, login_required, get_usuario,
    _csrf_token, _csrf_check,
)
from core.helpers import *
from core.helpers import _anio_escolar_actual, _periodo_actual, _audit, _nota_estado, _color_nota

logger = logging.getLogger("axula")

digitador_bp = Blueprint("digitador_bp", __name__)

def _digitador_required(f):
    """Solo digitador, secretaria_docente, coordinadores y directora."""
    import functools
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user_id"):
            return redirect("/login")
        rol = _normalizar_rol(session.get("rol", ""))
        permitidos = {"digitador", "secretaria_docente", "directora",
                      "coordinador_general", "coordinador_primer_ciclo",
                      "coordinador_segundo_ciclo", "asistente_directora"}
        if rol not in permitidos:
            return jsonify({"error": "Sin permisos para esta sección"}), 403
        return f(*args, **kwargs)
    return decorated


@digitador_bp.route("/digitador")
@login_required
def portal_digitador():
    u = get_usuario()
    rol = _normalizar_rol(u.get("rol", ""))
    if rol not in {"digitador", "secretaria_docente", "directora",
                   "coordinador_general", "coordinador_primer_ciclo",
                   "coordinador_segundo_ciclo", "asistente_directora"}:
        return redirect("/")
    return render_template("digitador.html", usuario=u, current_user=u)


# ── LISTAR ESTUDIANTES PARA DIGITACIÓN ───────────────────────────────────────

@digitador_bp.route("/api/digitador/estudiantes")
@login_required
@_digitador_required
def listar_estudiantes_digitador():
    grado = request.args.get("grado", "")
    mencion = request.args.get("mencion", "")
    seccion = request.args.get("seccion", "")
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        sql = """
            SELECT id, nombre, apellido, grado, curso, condicion, cedula,
                   ciclo, seccion, tiene_notas
            FROM estudiantes WHERE condicion='ACTIVO'
        """
        params = []
        if grado:
            sql += " AND grado=?"
            params.append(grado)
        if mencion:
            sql += " AND curso=?"
            params.append(mencion)
        if seccion:
            sql += " AND seccion=?"
            params.append(seccion)
        sql += " ORDER BY apellido, nombre"
        rows = conn.execute(sql, params).fetchall()
    return jsonify([dict(r) for r in rows])


# ── DIGITAR CALIFICACIÓN ─────────────────────────────────────────────────────

@digitador_bp.route("/api/digitador/calificacion", methods=["POST"])
@login_required
@_digitador_required
def digitar_calificacion():
    d = request.get_json(silent=True) or {}
    u = get_usuario()
    est_id = d.get("estudiante_id")
    materia = d.get("materia", "").strip()
    periodo = d.get("periodo", "").strip()
    nota = d.get("nota")

    if not all([est_id, materia, periodo, nota is not None]):
        return jsonify({"error": "Faltan campos obligatorios"}), 400

    try:
        nota = float(nota)
    except (ValueError, TypeError):
        return jsonify({"error": "Nota debe ser numérica"}), 400

    anio = _anio_escolar_actual()

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        # Verificar si ya existe
        existe = conn.execute("""
            SELECT id FROM calificaciones_periodo
            WHERE estudiante_id=? AND materia=? AND periodo=? AND anio_escolar=?
        """, (est_id, materia, periodo, anio)).fetchone()

        if existe:
            conn.execute("""
                UPDATE calificaciones_periodo SET nota=?, registrado_por=?,
                       fecha_registro=datetime('now')
                WHERE id=?
            """, (nota, u["id"], existe[0]))
        else:
            conn.execute("""
                INSERT INTO calificaciones_periodo
                (estudiante_id, materia, periodo, nota, anio_escolar, registrado_por)
                VALUES (?,?,?,?,?,?)
            """, (est_id, materia, periodo, nota, anio, u["id"]))

        conn.commit()
        cache_bust()

    _audit("calificacion_digitada",
           f"Nota {nota} en {materia} P{periodo} para est#{est_id}",
           "calificaciones_periodo", est_id)
    return jsonify({"ok": True, "estado": _nota_estado(nota)})


# ── DIGITAR LOTE (múltiples notas de una vez) ────────────────────────────────

@digitador_bp.route("/api/digitador/calificacion-lote", methods=["POST"])
@login_required
@_digitador_required
def digitar_calificacion_lote():
    d = request.get_json(silent=True) or {}
    u = get_usuario()
    notas = d.get("notas", [])
    if not notas:
        return jsonify({"error": "No hay notas para guardar"}), 400

    anio = _anio_escolar_actual()
    guardadas = 0
    errores = []

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        for item in notas:
            try:
                est_id = item["estudiante_id"]
                materia = item["materia"]
                periodo = item["periodo"]
                nota = float(item["nota"])

                existe = conn.execute("""
                    SELECT id FROM calificaciones_periodo
                    WHERE estudiante_id=? AND materia=? AND periodo=? AND anio_escolar=?
                """, (est_id, materia, periodo, anio)).fetchone()

                if existe:
                    conn.execute(
                        "UPDATE calificaciones_periodo SET nota=?, registrado_por=? WHERE id=?",
                        (nota, u["id"], existe[0]))
                else:
                    conn.execute("""
                        INSERT INTO calificaciones_periodo
                        (estudiante_id, materia, periodo, nota, anio_escolar, registrado_por)
                        VALUES (?,?,?,?,?,?)
                    """, (est_id, materia, periodo, nota, anio, u["id"]))
                guardadas += 1
            except Exception as ex:
                errores.append(f"Error en est#{item.get('estudiante_id','?')}: {ex}")

        conn.commit()
        cache_bust()

    return jsonify({"ok": True, "guardadas": guardadas, "errores": errores})


# ── VER NOTAS DE UN ESTUDIANTE ───────────────────────────────────────────────

@digitador_bp.route("/api/digitador/notas/<int:est_id>")
@login_required
@_digitador_required
def ver_notas_estudiante(est_id):
    anio = request.args.get("anio", _anio_escolar_actual())
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        est = conn.execute(
            "SELECT id, nombre, apellido, grado, curso FROM estudiantes WHERE id=?",
            (est_id,)
        ).fetchone()
        if not est:
            return jsonify({"error": "Estudiante no encontrado"}), 404

        notas = conn.execute("""
            SELECT materia, periodo, nota, fecha_registro
            FROM calificaciones_periodo
            WHERE estudiante_id=? AND anio_escolar=?
            ORDER BY materia, periodo
        """, (est_id, anio)).fetchall()

    return jsonify({
        "estudiante": dict(est),
        "notas": [dict(n) for n in notas],
        "anio": anio,
    })


# ── VERIFICAR DATOS DE ESTUDIANTES ──────────────────────────────────────────

@digitador_bp.route("/api/digitador/verificar-datos")
@login_required
@_digitador_required
def verificar_datos():
    """Detecta estudiantes con datos incompletos o inconsistentes."""
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row

        # Sin cédula
        sin_cedula = conn.execute("""
            SELECT id, nombre, apellido, grado, curso
            FROM estudiantes WHERE condicion='ACTIVO'
            AND (cedula IS NULL OR cedula = '')
        """).fetchall()

        # Sin grado
        sin_grado = conn.execute("""
            SELECT id, nombre, apellido, grado, curso
            FROM estudiantes WHERE condicion='ACTIVO'
            AND (grado IS NULL OR grado = '')
        """).fetchall()

        # Duplicados potenciales (mismo nombre+apellido)
        duplicados = conn.execute("""
            SELECT nombre, apellido, COUNT(*) as total
            FROM estudiantes WHERE condicion='ACTIVO'
            GROUP BY LOWER(nombre), LOWER(apellido)
            HAVING total > 1
        """).fetchall()

        # Sin notas registradas
        sin_notas = conn.execute("""
            SELECT e.id, e.nombre, e.apellido, e.grado, e.curso
            FROM estudiantes e
            WHERE e.condicion='ACTIVO' AND e.tiene_notas = 0
            ORDER BY e.grado, e.apellido
        """).fetchall()

    return jsonify({
        "sin_cedula": [dict(r) for r in sin_cedula],
        "sin_grado": [dict(r) for r in sin_grado],
        "duplicados": [dict(r) for r in duplicados],
        "sin_notas": [dict(r) for r in sin_notas],
    })


# ── RESUMEN DIGITADOR ───────────────────────────────────────────────────────

@digitador_bp.route("/api/digitador/resumen")
@login_required
@_digitador_required
def resumen_digitador():
    anio = _anio_escolar_actual()
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        total_est = conn.execute(
            "SELECT COUNT(*) FROM estudiantes WHERE condicion='ACTIVO'"
        ).fetchone()[0]

        con_notas = conn.execute("""
            SELECT COUNT(DISTINCT estudiante_id) FROM calificaciones_periodo
            WHERE anio_escolar=?
        """, (anio,)).fetchone()[0]

        total_calif = conn.execute(
            "SELECT COUNT(*) FROM calificaciones_periodo WHERE anio_escolar=?",
            (anio,)
        ).fetchone()[0]

        por_periodo = conn.execute("""
            SELECT periodo, COUNT(*) as total
            FROM calificaciones_periodo WHERE anio_escolar=?
            GROUP BY periodo ORDER BY periodo
        """, (anio,)).fetchall()

    return jsonify({
        "total_estudiantes": total_est,
        "con_notas": con_notas,
        "sin_notas": total_est - con_notas,
        "total_calificaciones": total_calif,
        "por_periodo": [dict(r) for r in por_periodo],
    })


# ═══════════════════════════════════════════════════════════════════════════
#  MVP: INSCRIPCIÓN Y REGISTRO DE ESTUDIANTES
# ═══════════════════════════════════════════════════════════════════════════

@digitador_bp.route("/api/digitador/registrar-estudiante", methods=["POST"])
@login_required
@_digitador_required
def registrar_estudiante():
    """Registra un nuevo estudiante en el sistema."""
    d = request.get_json(silent=True) or {}
    u = get_usuario()

    nombre = d.get("nombre", "").strip()
    apellido = d.get("apellido", "").strip()
    if not nombre or not apellido:
        return jsonify({"error": "Nombre y apellido son requeridos"}), 400

    cedula = d.get("cedula", "").strip()
    grado = d.get("grado", "4to")
    mencion = d.get("mencion", "").strip()
    seccion = d.get("seccion", "A").strip()
    edad = d.get("edad", 0)
    sexo = d.get("sexo", "")
    telefono = d.get("telefono", "")
    direccion = d.get("direccion", "")
    nombre_tutor = d.get("nombre_tutor", "")
    telefono_tutor = d.get("telefono_tutor", "")

    # Curso = "4TO MULTIMEDIA" format
    curso = f"{grado.upper()} {mencion.upper()}" if mencion else grado.upper()

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        # Check duplicate cedula
        if cedula:
            dup = conn.execute(
                "SELECT id FROM estudiantes WHERE cedula=?", (cedula,)
            ).fetchone()
            if dup:
                return jsonify({"error": f"Ya existe un estudiante con cédula {cedula}"}), 400

        conn.execute("""
            INSERT INTO estudiantes
            (nombre, apellido, cedula, grado, curso, seccion, edad, condicion, ciclo)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (nombre, apellido, cedula, grado, curso, seccion,
              edad, "ACTIVO", "segundo_ciclo"))
        est_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        # Create inscription record
        anio = _anio_escolar_actual()
        conn.execute("""
            INSERT INTO inscripciones
            (estudiante_id, anio_escolar, grado, mencion, seccion, tipo, registrado_por)
            VALUES (?,?,?,?,?,?,?)
        """, (est_id, anio, grado, mencion, seccion, "nueva", u["id"]))

        conn.commit()
        cache_bust()

    _audit("estudiante_registrado", f"Nuevo: {nombre} {apellido} ({grado} {mencion})",
           "estudiantes", est_id)
    return jsonify({"ok": True, "id": est_id, "mensaje": f"Estudiante {nombre} {apellido} registrado"})


@digitador_bp.route("/api/digitador/editar-estudiante/<int:est_id>", methods=["PATCH"])
@login_required
@_digitador_required
def editar_estudiante_digitador(est_id):
    """Edita datos de un estudiante existente."""
    d = request.get_json(silent=True) or {}
    campos = []
    params = []
    permitidos = ["nombre", "apellido", "cedula", "grado", "curso", "seccion",
                  "edad", "condicion", "ciclo"]
    for campo in permitidos:
        if campo in d:
            campos.append(f"{campo}=?")
            params.append(d[campo])

    # Si cambian grado+mencion, recalcular curso
    if "mencion" in d and "grado" in d:
        curso = f"{d['grado'].upper()} {d['mencion'].upper()}" if d["mencion"] else d["grado"].upper()
        campos.append("curso=?")
        params.append(curso)

    if not campos:
        return jsonify({"error": "Nada que actualizar"}), 400

    params.append(est_id)
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.execute(f"UPDATE estudiantes SET {','.join(campos)} WHERE id=?", params)
        conn.commit()
        cache_bust()

    return jsonify({"ok": True})


@digitador_bp.route("/api/digitador/asignar-mencion-bulk", methods=["POST"])
@login_required
@_digitador_required
def asignar_mencion_bulk():
    """Asigna mención en masa a estudiantes de un grado/sección sin mención asignada."""
    d = request.get_json(silent=True) or {}
    grado   = d.get("grado", "").strip().upper()
    seccion = d.get("seccion", "").strip().upper()
    mencion = d.get("mencion", "").strip()
    solo_vacias = d.get("solo_vacias", True)   # por defecto solo actualiza los que no tienen

    MENCIONES_VALIDAS = ["Multimedia", "Teatro", "Música", "Artes Visuales", "Danza"]
    GRADOS_ARTES = {"4TO", "5TO", "6TO"}

    if not grado:
        return jsonify({"error": "Grado requerido"}), 400
    if mencion not in MENCIONES_VALIDAS:
        return jsonify({"error": f"Mención inválida. Válidas: {', '.join(MENCIONES_VALIDAS)}"}), 400
    if grado not in GRADOS_ARTES:
        return jsonify({"error": "Mención solo aplica a 4TO, 5TO y 6TO (Bachillerato en Artes)"}), 400

    curso = f"{grado} {mencion.upper()}"
    params = [mencion, curso, grado]
    cond = "WHERE grado=?"
    if solo_vacias:
        cond += " AND (mencion IS NULL OR mencion='')"
    if seccion:
        cond += " AND seccion=?"
        params.append(seccion)

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        cur = conn.execute(f"UPDATE estudiantes SET mencion=?, curso=? {cond}", params)
        conn.commit()
        n = cur.rowcount
        cache_bust()

    logger.info(f"asignar_mencion_bulk: {n} estudiantes → {grado}/{seccion or 'todas'} = {mencion}")
    return jsonify({"ok": True, "actualizados": n, "grado": grado, "seccion": seccion, "mencion": mencion})


@digitador_bp.route("/api/digitador/cargar-notas-coordinador", methods=["POST"])
@login_required
@_digitador_required
def cargar_notas_coordinador():
    """
    Carga un archivo .xlsm/.xlsx de Registro del Coordinador (formato BJ).
    Detecta automáticamente materia, grado, sección, mención y períodos.
    Inserta/actualiza en materias_calificaciones.
    """
    import tempfile, unicodedata
    from difflib import SequenceMatcher
    from core.excel_notas import parsear_registro_coordinador

    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"ok": False, "error": "No se recibió archivo"}), 400

    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in (".xlsx", ".xls", ".xlsm"):
        return jsonify({"ok": False, "error": "Formato no válido. Usa .xlsx o .xlsm"}), 400

    # Guardar temporalmente
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        f.save(tmp.name)
        tmp_path = tmp.name

    try:
        datos = parsear_registro_coordinador(tmp_path)
    except Exception as e:
        os.unlink(tmp_path)
        logger.error(f"[EXCEL] Error parseando {f.filename}: {e}")
        return jsonify({"ok": False, "error": f"Error al leer el archivo: {e}"}), 400
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

    if not datos["hojas"]:
        return jsonify({
            "ok": False,
            "error": "No se encontraron hojas con formato reconocido. Se esperan hojas nombradas como 'CF 1ERO A' (primer ciclo) o 'CF 4TO A MÚSICA' (segundo ciclo).",
            "advertencias": datos.get("advertencias", [])
        }), 400

    materia = datos["materia"]
    anio    = _anio_escolar_actual()

    # ── Helper de normalización para matching ──────────────────────────────────
    def _norm(s):
        s = unicodedata.normalize("NFD", str(s or ""))
        s = "".join(c for c in s if unicodedata.category(c) != "Mn")
        import re
        return re.sub(r"\s+", " ", s).strip().lower()

    def _similar(a, b):
        return SequenceMatcher(None, _norm(a), _norm(b)).ratio()

    resumen = {
        "materia":     materia,
        "hojas":       len(datos["hojas"]),
        "cargados":    0,
        "actualizados": 0,
        "sin_match":   [],
        "advertencias": datos.get("advertencias", []),
    }

    with sqlite3.connect(DATABASE, timeout=15) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")

        for hoja in datos["hojas"]:
            grado   = hoja["grado"]
            seccion = hoja["seccion"]
            mencion = hoja["mencion"]
            tipo    = hoja["tipo"]
            ciclo   = "primer_ciclo" if grado in ("1ERO","2DO","3ERO") else "segundo_ciclo"

            # Índice de estudiantes del grado en BD
            rows_bd = conn.execute(
                "SELECT id, nombre, apellido FROM estudiantes WHERE grado=? AND condicion='ACTIVO'",
                (grado,)
            ).fetchall()
            idx_bd = {_norm(f"{r['nombre']} {r['apellido']}"): r["id"] for r in rows_bd}

            for alumno in hoja["alumnos"]:
                if alumno["estado"] == "RETIRADO":
                    continue

                nombre_pdf = alumno["nombre"]
                clave      = _norm(nombre_pdf)

                # Búsqueda exacta primero
                est_id = idx_bd.get(clave)

                # Fuzzy si no encontró exacto
                if est_id is None:
                    mejor = max(idx_bd.items(), key=lambda kv: _similar(kv[0], clave), default=(None, 0))
                    if mejor[0] and _similar(mejor[0], clave) >= 0.82:
                        est_id = mejor[1]

                if est_id is None:
                    resumen["sin_match"].append(f"[{grado}] {nombre_pdf}")
                    continue

                # INSERT OR REPLACE en materias_calificaciones
                existente = conn.execute(
                    "SELECT id FROM materias_calificaciones WHERE estudiante_id=? AND materia=? AND grado=? AND anio_escolar=?",
                    (est_id, materia, grado, anio)
                ).fetchone()

                if existente:
                    conn.execute("""
                        UPDATE materias_calificaciones
                        SET p1=?, p2=?, p3=?, p4=?, promedio=?, tipo=?, ciclo=?
                        WHERE id=?
                    """, (alumno["p1"], alumno["p2"], alumno["p3"], alumno["p4"],
                          alumno["promedio"], tipo, ciclo, existente["id"]))
                    resumen["actualizados"] += 1
                else:
                    conn.execute("""
                        INSERT INTO materias_calificaciones
                            (estudiante_id, materia, grado, p1, p2, p3, p4, promedio, tipo, ciclo, anio_escolar)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?)
                    """, (est_id, materia, grado,
                          alumno["p1"], alumno["p2"], alumno["p3"], alumno["p4"],
                          alumno["promedio"], tipo, ciclo, anio))
                    resumen["cargados"] += 1

        conn.commit()

    total = resumen["cargados"] + resumen["actualizados"]
    return jsonify({
        "ok":      True,
        "mensaje": (
            f"✓ {materia} cargada — "
            f"{resumen['cargados']} nuevos, {resumen['actualizados']} actualizados "
            f"en {resumen['hojas']} hoja(s)."
        ),
        **resumen,
    })


@digitador_bp.route("/api/digitador/buscar-estudiante")
@login_required
@_digitador_required
def buscar_estudiante_digitador():
    """Búsqueda rápida de estudiantes."""
    q = request.args.get("q", "").strip()
    if len(q) < 2:
        return jsonify([])
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT id, nombre, apellido, grado, curso, cedula, condicion, seccion
            FROM estudiantes
            WHERE (nombre LIKE ? OR apellido LIKE ? OR cedula LIKE ?)
            ORDER BY apellido, nombre LIMIT 30
        """, (f"%{q}%", f"%{q}%", f"%{q}%")).fetchall()
    return jsonify([dict(r) for r in rows])
