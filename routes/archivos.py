# -*- coding: utf-8 -*-
"""Blueprint: archivos — Biblioteca de Archivos Digitales Institucionales"""

import os
import uuid
import logging
from datetime import datetime
from flask import (
    Blueprint, render_template, request, jsonify, session,
    send_from_directory, abort,
)

from core.constants import ROLES_DIRECTORA, ROLES_SUPER
from core.database import get_db
from core.auth import login_required, _normalizar_rol, get_usuario
from core.helpers import _validar_magic_archivo

logger = logging.getLogger("axula")

archivos_bp = Blueprint("archivos_bp", __name__)

UPLOAD_DIR       = os.path.join("uploads", "archivos")
MAX_SIZE_BYTES   = 10 * 1024 * 1024   # 10 MB
TIPOS_PERMITIDOS = {
    "application/pdf":                                                   ("pdf",  "PDF"),
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ("docx", "Word"),
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":       ("xlsx", "Excel"),
    "application/msword":                                                ("docx", "Word"),
    "application/vnd.ms-excel":                                          ("xlsx", "Excel"),
    "image/jpeg":                                                        ("jpg",  "Imagen"),
    "image/png":                                                         ("png",  "Imagen"),
}
EXTENSIONES_PERMITIDAS = {".pdf", ".docx", ".xlsx", ".doc", ".xls", ".jpg", ".jpeg", ".png"}

CATEGORIAS = {
    "acta":           "Acta",
    "circular":       "Circular",
    "planificacion":  "Planificación",
    "expediente":     "Expediente",
    "reporte":        "Reporte",
    "formulario":     "Formulario",
    "otro":           "Otro",
}

# Niveles de acceso y qué roles los pueden ver
_ACCESO_ROLES = {
    "institucional": {
        "directora", "superusuario", "coordinador_general",
        "coordinador_primer_ciclo", "coordinador_segundo_ciclo",
        "psicologa_primer_ciclo", "psicologa_segundo_ciclo",
        "secretaria", "secretaria_docente", "asistente_directora",
    },
    "psicologico": {"directora", "superusuario", "psicologa_primer_ciclo", "psicologa_segundo_ciclo"},
    "financiero":  {"directora", "superusuario", "coordinador_general", "auxiliar_contabilidad"},
}


def _puede_ver_acceso(rol: str, acceso: str) -> bool:
    return rol in _ACCESO_ROLES.get(acceso, set())


def _accesos_visibles(rol: str) -> list:
    return [acc for acc, roles in _ACCESO_ROLES.items() if rol in roles]


# ── PORTAL ───────────────────────────────────────────────────────────────────

@archivos_bp.route("/archivos")
@login_required
def portal_archivos():
    rol = _normalizar_rol(session.get("rol", ""))
    if rol == "padre":
        abort(403)
    u = get_usuario()
    return render_template("archivos.html",
        categorias=CATEGORIAS,
        accesos_visibles=_accesos_visibles(rol),
        current_user=u,
    )


# ── API: LISTAR ───────────────────────────────────────────────────────────────

@archivos_bp.route("/api/archivos")
@login_required
def listar_archivos():
    rol      = _normalizar_rol(session.get("rol", ""))
    user_id  = session.get("user_id")
    categoria = request.args.get("categoria", "")
    busqueda  = request.args.get("q", "").strip()[:80]

    accesos = _accesos_visibles(rol)

    db = get_db()

    # Directora y superusuario ven todo
    if rol in ROLES_DIRECTORA:
        cond = "1=1"
        params = []
    else:
        # Ve archivos de su nivel de acceso + siempre los propios
        placeholders = ",".join("?" * len(accesos))
        cond = f"(acceso IN ({placeholders}) OR subido_por = ?)"
        params = accesos + [user_id]

    if categoria:
        cond += " AND categoria = ?"
        params.append(categoria)

    if busqueda:
        cond += " AND (nombre LIKE ? OR descripcion LIKE ?)"
        params += [f"%{busqueda}%", f"%{busqueda}%"]

    rows = db.execute(f"""
        SELECT a.id, a.nombre, a.descripcion, a.tipo_archivo, a.categoria,
               a.acceso, a.tamanio_kb, a.fecha_subida, a.ruta_archivo,
               u.nombre AS subido_por_nombre, a.subido_por,
               a.estudiante_id
        FROM archivos_digitales a
        LEFT JOIN usuarios u ON u.id = a.subido_por
        WHERE a.activo = 1 AND {cond}
        ORDER BY a.fecha_subida DESC
        LIMIT 200
    """, params).fetchall()

    resultado = []
    for r in rows:
        resultado.append({
            "id":               r["id"],
            "nombre":           r["nombre"],
            "descripcion":      r["descripcion"] or "",
            "tipo_archivo":     r["tipo_archivo"],
            "categoria":        r["categoria"],
            "categoria_label":  CATEGORIAS.get(r["categoria"], r["categoria"]),
            "acceso":           r["acceso"],
            "tamanio_kb":       r["tamanio_kb"] or 0,
            "fecha_subida":     r["fecha_subida"],
            "subido_por":       r["subido_por_nombre"] or "—",
            "es_propio":        r["subido_por"] == user_id,
            "puede_eliminar":   rol in ROLES_DIRECTORA or r["subido_por"] == user_id,
        })

    return jsonify({"archivos": resultado, "total": len(resultado)})


# ── API: SUBIR ────────────────────────────────────────────────────────────────

@archivos_bp.route("/api/archivos/subir", methods=["POST"])
@login_required
def subir_archivo():
    rol     = _normalizar_rol(session.get("rol", ""))
    user_id = session.get("user_id")

    if rol == "padre":
        return jsonify({"error": "Sin permisos"}), 403

    archivo = request.files.get("archivo")
    if not archivo or not archivo.filename:
        return jsonify({"error": "No se recibió ningún archivo"}), 400

    # Validar extensión
    ext = os.path.splitext(archivo.filename)[1].lower()
    if ext not in EXTENSIONES_PERMITIDAS:
        return jsonify({"error": f"Tipo de archivo no permitido. Usa: PDF, DOCX, XLSX, JPG o PNG"}), 400

    # Leer contenido para validar tamaño
    contenido = archivo.read()
    if len(contenido) > MAX_SIZE_BYTES:
        return jsonify({"error": "El archivo supera el límite de 10 MB"}), 400

    # Validar magic bytes — ignora el Content-Type del cliente
    if not _validar_magic_archivo(contenido, ext):
        logger.warning(
            f"[ARCHIVOS] Magic bytes no coinciden: ext={ext} "
            f"user_id={user_id} filename={archivo.filename!r}"
        )
        return jsonify({"error": "El contenido del archivo no corresponde a su extensión"}), 400

    # Validar datos del form
    nombre      = request.form.get("nombre", "").strip()[:200]
    descripcion = request.form.get("descripcion", "").strip()[:500]
    categoria   = request.form.get("categoria", "otro")
    acceso      = request.form.get("acceso", "institucional")

    if not nombre:
        nombre = os.path.splitext(archivo.filename)[0][:200]
    if categoria not in CATEGORIAS:
        categoria = "otro"
    if acceso not in _ACCESO_ROLES:
        acceso = "institucional"

    # Solo psicóloga/directora puede subir archivos psicológicos
    if acceso == "psicologico" and rol not in {"psicologa_primer_ciclo", "psicologa_segundo_ciclo"} | ROLES_DIRECTORA:
        acceso = "institucional"

    # Solo finanzas/directora puede subir archivos financieros
    if acceso == "financiero" and rol not in {"auxiliar_contabilidad"} | ROLES_DIRECTORA:
        acceso = "institucional"

    # Tipo de archivo derivado de la extensión validada (no del Content-Type del cliente)
    tipo_archivo = ext.lstrip(".")

    # Guardar en disco con nombre UUID
    nombre_archivo = f"{uuid.uuid4().hex}{ext}"
    ruta_completa = os.path.join(UPLOAD_DIR, nombre_archivo)
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    with open(ruta_completa, "wb") as f:
        f.write(contenido)

    tamanio_kb = len(contenido) // 1024

    # Insertar en DB
    db = get_db()
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur = db.execute("""
        INSERT INTO archivos_digitales
            (nombre, descripcion, tipo_archivo, categoria, acceso,
             ruta_archivo, tamanio_kb, subido_por, rol_origen, fecha_subida, activo)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
    """, (nombre, descripcion, tipo_archivo, categoria, acceso,
          nombre_archivo, tamanio_kb, user_id, rol, ahora))
    db.commit()

    logger.info(f"[ARCHIVOS] Subido: {nombre} por user_id={user_id} rol={rol} acceso={acceso}")

    return jsonify({
        "ok": True,
        "id": cur.lastrowid,
        "nombre": nombre,
        "tamanio_kb": tamanio_kb,
    })


# ── API: DESCARGAR ────────────────────────────────────────────────────────────

@archivos_bp.route("/api/archivos/<int:archivo_id>/descargar")
@login_required
def descargar_archivo(archivo_id):
    rol     = _normalizar_rol(session.get("rol", ""))
    user_id = session.get("user_id")

    db = get_db()
    row = db.execute(
        "SELECT * FROM archivos_digitales WHERE id = ? AND activo = 1",
        (archivo_id,)
    ).fetchone()

    if not row:
        abort(404)

    # Verificar acceso
    if rol not in ROLES_DIRECTORA:
        if not _puede_ver_acceso(rol, row["acceso"]) and row["subido_por"] != user_id:
            abort(403)

    ruta = os.path.join(UPLOAD_DIR, row["ruta_archivo"])
    if not os.path.exists(ruta):
        abort(404)

    # Determinar nombre de descarga con extensión correcta
    ext = os.path.splitext(row["ruta_archivo"])[1]
    nombre_descarga = row["nombre"] + ext

    return send_from_directory(
        os.path.abspath(UPLOAD_DIR),
        row["ruta_archivo"],
        as_attachment=True,
        download_name=nombre_descarga,
    )


# ── API: ARCHIVOS POR ESTUDIANTE ──────────────────────────────────────────────

@archivos_bp.route("/api/archivos/estudiante/<int:est_id>", methods=["GET"])
@login_required
def archivos_por_estudiante(est_id):
    """Archivos digitales vinculados a un estudiante específico (expediente)."""
    rol     = _normalizar_rol(session.get("rol", ""))
    user_id = session.get("user_id")

    _ROLES_PUEDE_VER = {
        "directora", "superusuario", "coordinador_general",
        "coordinador_primer_ciclo", "coordinador_segundo_ciclo",
        "psicologa_primer_ciclo", "psicologa_segundo_ciclo",
        "secretaria", "secretaria_docente", "asistente_directora",
    }
    if rol not in _ROLES_PUEDE_VER:
        return jsonify({"error": "Sin permisos"}), 403

    db = get_db()

    # Psicólogas solo ven psicológico + institucional, no financiero
    if "psicologa" in rol:
        accesos = ("institucional", "psicologico")
    elif rol in {"secretaria", "secretaria_docente", "asistente_directora"}:
        accesos = ("institucional",)
    else:
        accesos = ("institucional", "psicologico", "financiero")

    placeholders = ",".join("?" * len(accesos))
    rows = db.execute(f"""
        SELECT a.id, a.nombre, a.descripcion, a.tipo_archivo, a.categoria,
               a.acceso, a.tamanio_kb, a.fecha_subida,
               u.nombre AS subido_por_nombre, a.subido_por
        FROM archivos_digitales a
        LEFT JOIN usuarios u ON u.id = a.subido_por
        WHERE a.activo = 1
          AND a.estudiante_id = ?
          AND a.acceso IN ({placeholders})
        ORDER BY a.fecha_subida DESC
    """, [est_id] + list(accesos)).fetchall()

    resultado = []
    for r in rows:
        resultado.append({
            "id":              r["id"],
            "nombre":          r["nombre"],
            "descripcion":     r["descripcion"] or "",
            "tipo_archivo":    r["tipo_archivo"],
            "categoria":       r["categoria"],
            "categoria_label": CATEGORIAS.get(r["categoria"], r["categoria"]),
            "acceso":          r["acceso"],
            "tamanio_kb":      r["tamanio_kb"] or 0,
            "fecha_subida":    r["fecha_subida"],
            "subido_por":      r["subido_por_nombre"] or "—",
            "puede_eliminar":  rol in ROLES_DIRECTORA or r["subido_por"] == user_id,
        })

    return jsonify({"archivos": resultado})


# ── API: ELIMINAR ─────────────────────────────────────────────────────────────

@archivos_bp.route("/api/archivos/<int:archivo_id>", methods=["DELETE"])
@login_required
def eliminar_archivo(archivo_id):
    rol     = _normalizar_rol(session.get("rol", ""))
    user_id = session.get("user_id")

    db = get_db()
    row = db.execute(
        "SELECT id, subido_por, ruta_archivo, nombre FROM archivos_digitales WHERE id = ? AND activo = 1",
        (archivo_id,)
    ).fetchone()

    if not row:
        return jsonify({"error": "Archivo no encontrado"}), 404

    # Solo directora o quien lo subió puede eliminar
    if rol not in ROLES_DIRECTORA and row["subido_por"] != user_id:
        return jsonify({"error": "Sin permisos para eliminar este archivo"}), 403

    # Soft delete — no borramos el archivo físico por seguridad
    db.execute("UPDATE archivos_digitales SET activo = 0 WHERE id = ?", (archivo_id,))
    db.commit()

    logger.info(f"[ARCHIVOS] Eliminado id={archivo_id} '{row['nombre']}' por user_id={user_id}")

    return jsonify({"ok": True})
