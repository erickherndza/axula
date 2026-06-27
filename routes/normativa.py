# -*- coding: utf-8 -*-
"""Blueprint: normativa — Gestión de documentos oficiales MINERD para RAG"""

import os
import uuid
import logging
from datetime import datetime

from flask import (
    Blueprint, render_template, request, jsonify,
    session, send_from_directory, abort,
)

from core.auth import login_required, _normalizar_rol, get_usuario
from core.constants import ROLES_DIRECTORA, ROLES_COORD
from core.database import get_db
from core.helpers import _validar_magic_archivo
from core.rag import procesar_normativa

logger = logging.getLogger("axula")

normativa_bp = Blueprint("normativa_bp", __name__)

UPLOAD_DIR     = os.path.join("uploads", "normativa")
MAX_SIZE_BYTES = 20 * 1024 * 1024   # 20 MB (documentos legales pueden ser grandes)

TIPOS_PERMITIDOS = {
    "application/pdf":  "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/msword": "docx",
}
EXTENSIONES = {".pdf", ".docx", ".doc"}

TIPOS_DOC = {
    "ordenanza":   "Ordenanza",
    "adendo":      "Adendo",
    "circular":    "Circular Normativa",
    "resolucion":  "Resolución",
    "plan":        "Plan de Estudios",
    "otro":        "Otro",
}

# Roles que pueden subir/gestionar documentos normativos
_ROLES_GESTORES = ROLES_DIRECTORA | ROLES_COORD | {"superusuario"}


def _puede_gestionar(rol: str) -> bool:
    return rol in _ROLES_GESTORES


# ─────────────────────────────────────────────
#  Portal
# ─────────────────────────────────────────────

@normativa_bp.route("/normativa")
@login_required
def portal_normativa():
    rol = _normalizar_rol(session.get("rol", ""))
    if not _puede_gestionar(rol):
        abort(403)
    db   = get_db()
    user = get_usuario()
    docs = db.execute("""
        SELECT n.*, u.nombre AS subido_por_nombre
        FROM normativa_minerd n
        JOIN usuarios u ON u.id = n.subido_por
        WHERE n.activo = 1
        ORDER BY n.fecha_subida DESC
    """).fetchall()
    return render_template("normativa.html", docs=docs, user=user,
                           tipos_doc=TIPOS_DOC, rol=rol)


# ─────────────────────────────────────────────
#  API — listar
# ─────────────────────────────────────────────

@normativa_bp.route("/api/normativa")
@login_required
def api_listar():
    rol = _normalizar_rol(session.get("rol", ""))
    if not _puede_gestionar(rol):
        return jsonify({"ok": False, "msg": "Sin acceso"}), 403
    db   = get_db()
    docs = db.execute("""
        SELECT n.id, n.titulo, n.tipo, n.anio_escolar, n.version,
               n.procesado, n.total_chunks, n.fecha_subida,
               u.nombre AS subido_por_nombre
        FROM normativa_minerd n
        JOIN usuarios u ON u.id = n.subido_por
        WHERE n.activo = 1
        ORDER BY n.fecha_subida DESC
    """).fetchall()
    return jsonify({"ok": True, "docs": [dict(d) for d in docs]})


# ─────────────────────────────────────────────
#  API — subir documento
# ─────────────────────────────────────────────

@normativa_bp.route("/api/normativa/subir", methods=["POST"])
@login_required
def api_subir():
    rol = _normalizar_rol(session.get("rol", ""))
    if not _puede_gestionar(rol):
        return jsonify({"ok": False, "msg": "Sin acceso"}), 403

    titulo      = request.form.get("titulo", "").strip()
    descripcion = request.form.get("descripcion", "").strip()
    tipo        = request.form.get("tipo", "otro").strip()
    anio_esc    = request.form.get("anio_escolar", "").strip()
    version     = request.form.get("version", "").strip()

    if not titulo:
        return jsonify({"ok": False, "msg": "El título es obligatorio"}), 400
    if tipo not in TIPOS_DOC:
        return jsonify({"ok": False, "msg": "Tipo de documento inválido"}), 400

    archivo = request.files.get("archivo")
    if not archivo or not archivo.filename:
        return jsonify({"ok": False, "msg": "No se recibió ningún archivo"}), 400

    ext = os.path.splitext(archivo.filename)[1].lower()
    if ext not in EXTENSIONES:
        return jsonify({"ok": False, "msg": "Solo se aceptan PDF o DOCX"}), 400

    contenido = archivo.read()
    if len(contenido) > MAX_SIZE_BYTES:
        return jsonify({"ok": False, "msg": "Archivo mayor a 20 MB"}), 400

    # Validar magic bytes
    mime_real = _validar_magic_archivo(contenido, ext)
    if not mime_real:
        return jsonify({"ok": False, "msg": "El archivo no es un PDF/DOCX válido"}), 400

    tipo_archivo = TIPOS_PERMITIDOS.get(mime_real, ext.lstrip("."))

    # Guardar archivo
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    nombre_archivo = f"{uuid.uuid4().hex}{ext}"
    ruta_completa  = os.path.join(UPLOAD_DIR, nombre_archivo)
    with open(ruta_completa, "wb") as f:
        f.write(contenido)

    db = get_db()
    cur = db.execute("""
        INSERT INTO normativa_minerd
            (titulo, descripcion, tipo, anio_escolar, version,
             ruta_archivo, tipo_archivo, tamanio_kb,
             subido_por, procesado, fecha_subida)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
    """, (
        titulo, descripcion, tipo, anio_esc, version,
        ruta_completa, tipo_archivo,
        round(len(contenido) / 1024),
        session["user_id"],
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    ))
    normativa_id = cur.lastrowid
    db.commit()

    # Procesar en el mismo request (docs pequeños < 20MB tardan < 2s)
    ok = procesar_normativa(db, normativa_id, ruta_completa)
    estado = "procesado" if ok else "error_procesado"

    logger.info(f"[NORMATIVA] id={normativa_id} '{titulo}' subido por uid={session['user_id']} — {estado}")
    return jsonify({
        "ok":    True,
        "id":    normativa_id,
        "estado": estado,
        "msg":   "Documento subido y procesado correctamente" if ok
                 else "Documento subido pero no se pudo extraer texto (verifica que no esté escaneado como imagen)",
    })


# ─────────────────────────────────────────────
#  API — re-procesar (por si el anterior falló)
# ─────────────────────────────────────────────

@normativa_bp.route("/api/normativa/<int:nid>/reprocesar", methods=["POST"])
@login_required
def api_reprocesar(nid):
    rol = _normalizar_rol(session.get("rol", ""))
    if not _puede_gestionar(rol):
        return jsonify({"ok": False, "msg": "Sin acceso"}), 403
    db  = get_db()
    doc = db.execute("SELECT * FROM normativa_minerd WHERE id=? AND activo=1", (nid,)).fetchone()
    if not doc:
        return jsonify({"ok": False, "msg": "Documento no encontrado"}), 404
    ok = procesar_normativa(db, nid, doc["ruta_archivo"])
    return jsonify({"ok": ok, "msg": "Re-procesado OK" if ok else "Error al procesar — revisa el archivo"})


# ─────────────────────────────────────────────
#  API — eliminar (soft-delete)
# ─────────────────────────────────────────────

@normativa_bp.route("/api/normativa/<int:nid>", methods=["DELETE"])
@login_required
def api_eliminar(nid):
    rol = _normalizar_rol(session.get("rol", ""))
    if rol not in ROLES_DIRECTORA and rol != "superusuario":
        return jsonify({"ok": False, "msg": "Solo la directora puede eliminar normativas"}), 403
    db = get_db()
    db.execute("UPDATE normativa_minerd SET activo=0 WHERE id=?", (nid,))
    db.commit()
    return jsonify({"ok": True})


# ─────────────────────────────────────────────
#  Descarga directa
# ─────────────────────────────────────────────

@normativa_bp.route("/normativa/descargar/<int:nid>")
@login_required
def descargar(nid):
    rol = _normalizar_rol(session.get("rol", ""))
    if not _puede_gestionar(rol):
        abort(403)
    db  = get_db()
    doc = db.execute("SELECT * FROM normativa_minerd WHERE id=? AND activo=1", (nid,)).fetchone()
    if not doc:
        abort(404)
    directorio = os.path.dirname(doc["ruta_archivo"])
    nombre     = os.path.basename(doc["ruta_archivo"])
    return send_from_directory(directorio, nombre, as_attachment=True,
                               download_name=f"{doc['titulo']}.{doc['tipo_archivo']}")
