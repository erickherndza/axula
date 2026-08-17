# -*- coding: utf-8 -*-
"""Blueprint: poa — Plan Operativo Anual (plantilla CBJ)"""

import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash, g

from core.constants import ROLES_COORD
from core.database import get_db
from core.auth import login_required, get_usuario, _csrf_check, _normalizar_rol
from core.helpers import _anio_escolar_actual

logger = logging.getLogger("axula")

poa_bp = Blueprint("poa_bp", __name__)


def _es_admin(u):
    return _normalizar_rol(u.get("rol", "")) in ROLES_COORD


@poa_bp.route("/poa")
@login_required
def poa_index():
    u = get_usuario()
    conn = get_db()
    admin = _es_admin(u)
    if admin:
        poas = conn.execute(
            """SELECT p.*, us.nombre AS docente_nombre
               FROM poa p
               JOIN usuarios us ON us.id = p.docente_id
               ORDER BY p.fecha_creacion DESC"""
        ).fetchall()
    else:
        poas = conn.execute(
            """SELECT p.*, ? AS docente_nombre
               FROM poa p
               WHERE p.docente_id = ?
               ORDER BY p.fecha_creacion DESC""",
            (u["nombre"], u["id"]),
        ).fetchall()
    return render_template("poa/index.html", poas=poas, es_admin=admin)


@poa_bp.route("/poa/nuevo", methods=["GET", "POST"])
@login_required
def poa_nuevo():
    u = get_usuario()
    anio = _anio_escolar_actual()
    if request.method == "POST":
        if not _csrf_check():
            flash("Token de seguridad inválido.", "error")
            return redirect(url_for("poa_bp.poa_nuevo"))
        asignatura       = request.form.get("asignatura", "").strip()
        area             = request.form.get("area", "").strip()
        anio_form        = request.form.get("anio_escolar", anio).strip()
        trimestre        = request.form.get("trimestre") or None
        objetivo_general = request.form.get("objetivo_general", "").strip()
        integrantes      = request.form.get("integrantes", "").strip()
        responsable_mesa = request.form.get("responsable_mesa", "").strip()
        if not asignatura:
            flash("El Área / Equipo es obligatorio.", "error")
            return redirect(url_for("poa_bp.poa_nuevo"))
        conn = get_db()
        cur = conn.execute(
            """INSERT INTO poa
               (docente_id, anio_escolar, asignatura, trimestre,
                objetivo_general, area, integrantes, responsable_mesa)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (u["id"], anio_form, asignatura, trimestre,
             objetivo_general, area, integrantes, responsable_mesa),
        )
        conn.commit()
        flash("POA creado. Ahora agrega las actividades.", "success")
        return redirect(url_for("poa_bp.poa_editar", poa_id=cur.lastrowid))
    return render_template("poa/nuevo.html", anio=anio, materia_prof=u.get("materia", ""))


@poa_bp.route("/poa/<int:poa_id>/editar", methods=["GET", "POST"])
@login_required
def poa_editar(poa_id):
    u = get_usuario()
    conn = get_db()
    admin = _es_admin(u)

    if admin:
        poa = conn.execute("SELECT * FROM poa WHERE id = ?", (poa_id,)).fetchone()
    else:
        poa = conn.execute(
            "SELECT * FROM poa WHERE id = ? AND docente_id = ?",
            (poa_id, u["id"]),
        ).fetchone()

    if not poa:
        flash("POA no encontrado.", "error")
        return redirect(url_for("poa_bp.poa_index"))

    if request.method == "POST":
        if not _csrf_check():
            flash("Token de seguridad inválido.", "error")
            return redirect(url_for("poa_bp.poa_editar", poa_id=poa_id))

        if poa["docente_id"] != u["id"] and not admin:
            flash("Sin permiso para editar este POA.", "error")
            return redirect(url_for("poa_bp.poa_index"))

        accion = request.form.get("accion")

        if accion == "agregar_actividad" and poa["estado"] == "borrador":
            actividad_val = request.form.get("actividad", "").strip()
            conn.execute(
                """INSERT INTO poa_actividad
                   (poa_id, objetivo, actividad, acciones, recursos, cantidad,
                    presupuesto, cuando, evidencia, responsable)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    poa_id,
                    actividad_val,  # objetivo = actividad (NOT NULL workaround)
                    actividad_val,
                    request.form.get("acciones", "").strip(),
                    request.form.get("recursos", "").strip(),
                    request.form.get("cantidad", "").strip(),
                    float(request.form.get("presupuesto") or 0),
                    request.form.get("cuando", "").strip(),
                    request.form.get("evidencia", "").strip(),
                    request.form.get("responsable", "").strip(),
                ),
            )
            conn.commit()

        elif accion == "eliminar_actividad" and poa["estado"] == "borrador":
            conn.execute(
                "DELETE FROM poa_actividad WHERE id = ? AND poa_id = ?",
                (request.form.get("actividad_id"), poa_id),
            )
            conn.commit()

        elif accion == "cambiar_estado_actividad":
            nuevo_estado = request.form.get("nuevo_estado", "pendiente")
            if nuevo_estado in ("pendiente", "en_proceso", "completada"):
                conn.execute(
                    "UPDATE poa_actividad SET estado = ? WHERE id = ? AND poa_id = ?",
                    (nuevo_estado, request.form.get("actividad_id"), poa_id),
                )
                conn.commit()

        elif accion == "enviar" and poa["estado"] == "borrador":
            conn.execute(
                "UPDATE poa SET estado = 'enviado', fecha_actualizacion = datetime('now') WHERE id = ?",
                (poa_id,),
            )
            conn.commit()
            flash("POA enviado para revisión.", "success")
            return redirect(url_for("poa_bp.poa_index"))

        elif accion == "aprobar" and admin and poa["estado"] == "enviado":
            conn.execute(
                "UPDATE poa SET estado = 'aprobado', fecha_actualizacion = datetime('now') WHERE id = ?",
                (poa_id,),
            )
            conn.commit()
            flash("POA aprobado.", "success")
            return redirect(url_for("poa_bp.poa_index"))

        elif accion == "devolver" and admin and poa["estado"] in ("enviado", "aprobado"):
            conn.execute(
                "UPDATE poa SET estado = 'borrador', fecha_actualizacion = datetime('now') WHERE id = ?",
                (poa_id,),
            )
            conn.commit()
            flash("POA devuelto a borrador.", "success")

        return redirect(url_for("poa_bp.poa_editar", poa_id=poa_id))

    # GET — lista de actividades como list[dict]
    raw_actividades = conn.execute(
        "SELECT * FROM poa_actividad WHERE poa_id = ? ORDER BY id",
        (poa_id,),
    ).fetchall()

    actividades = [dict(act) for act in raw_actividades]

    es_propietario = (poa["docente_id"] == u["id"])
    puede_editar   = es_propietario and poa["estado"] == "borrador"

    return render_template(
        "poa/editar.html",
        poa=poa,
        actividades=actividades,
        es_admin=admin,
        puede_editar=puede_editar,
    )
