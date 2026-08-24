# -*- coding: utf-8 -*-
"""
Blueprint: coherencia — Coherencia Horizontal (planeamiento curricular MINERD)

La Coherencia Horizontal es un principio de planeamiento curricular del
MINERD: exige que todas las asignaturas que un/a estudiante cursa en un
mismo grado estén alineadas entre sí (objetivos, contenidos, indicadores de
logro), en vez de funcionar de forma aislada. Se distingue de la
"Coherencia Vertical" (progresión de una misma asignatura a través de los
grados), que no es lo que cubre este módulo.

Pensado para 4TO y 5TO de Secundaria, Modalidad en Artes: un estudiante
cursa un Componente Académico (Lengua Española, Inglés, Matemática,
Ciencias Sociales, Ciencias de la Naturaleza, Educación Física, FIHR) y un
Componente Artístico según su mención (Multimedia, Artes Visuales, Música,
Teatro, Danza). La matriz documenta, por período, cómo se articula cada
área con las demás.

Sigue el mismo patrón que routes/poa.py: tabla encabezado
(coherencia_horizontal) + tabla de filas (coherencia_horizontal_fila),
formularios server-rendered con CSRF, dueño edita lo suyo / admin ve todo.
"""

import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash

from core.constants import ROLES_COORD
from core.database import get_db
from core.auth import login_required, get_usuario, _csrf_check, _normalizar_rol
from core.helpers import _anio_escolar_actual, _get_config_centro

logger = logging.getLogger("axula")

coherencia_bp = Blueprint("coherencia_bp", __name__)


def _es_admin(u):
    return _normalizar_rol(u.get("rol", "")) in ROLES_COORD


@coherencia_bp.route("/coherencia")
@login_required
def coherencia_index():
    u = get_usuario()
    conn = get_db()
    admin = _es_admin(u)
    if admin:
        matrices = conn.execute(
            """SELECT m.*, us.nombre AS docente_nombre,
                      (SELECT COUNT(*) FROM coherencia_horizontal_fila f WHERE f.matriz_id = m.id) AS n_filas
               FROM coherencia_horizontal m
               JOIN usuarios us ON us.id = m.docente_id
               ORDER BY m.fecha_creacion DESC"""
        ).fetchall()
    else:
        matrices = conn.execute(
            """SELECT m.*, ? AS docente_nombre,
                      (SELECT COUNT(*) FROM coherencia_horizontal_fila f WHERE f.matriz_id = m.id) AS n_filas
               FROM coherencia_horizontal m
               WHERE m.docente_id = ?
               ORDER BY m.fecha_creacion DESC""",
            (u["nombre"], u["id"]),
        ).fetchall()
    return render_template("coherencia/index.html", matrices=matrices, es_admin=admin)


@coherencia_bp.route("/coherencia/nueva", methods=["GET", "POST"])
@login_required
def coherencia_nueva():
    u = get_usuario()
    anio = _anio_escolar_actual()
    centro_cfg = _get_config_centro()

    if request.method == "POST":
        if not _csrf_check():
            flash("Token de seguridad inválido.", "error")
            return redirect(url_for("coherencia_bp.coherencia_nueva"))

        grado   = request.form.get("grado", "").strip()
        seccion = request.form.get("seccion", "").strip()
        mencion = request.form.get("mencion", "").strip()
        periodo = request.form.get("periodo", "").strip()
        centro  = request.form.get("centro", "").strip() or centro_cfg.get("nombre", "")

        if not grado:
            flash("El grado es obligatorio.", "error")
            return redirect(url_for("coherencia_bp.coherencia_nueva"))

        conn = get_db()
        cur = conn.execute(
            """INSERT INTO coherencia_horizontal
               (docente_id, anio_escolar, centro, grado, seccion, mencion, periodo)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (u["id"], anio, centro, grado, seccion, mencion, periodo),
        )
        conn.commit()
        flash("Matriz creada. Ahora agrega las filas de articulación.", "success")
        return redirect(url_for("coherencia_bp.coherencia_editar", matriz_id=cur.lastrowid))

    return render_template(
        "coherencia/nueva.html",
        anio=anio,
        centro_nombre=centro_cfg.get("nombre", ""),
        grado_prof=(u.get("grado", "") or "").split(",")[0].strip(),
        mencion_prof=u.get("mencion", ""),
    )


@coherencia_bp.route("/coherencia/<int:matriz_id>/editar", methods=["GET", "POST"])
@login_required
def coherencia_editar(matriz_id):
    u = get_usuario()
    conn = get_db()
    admin = _es_admin(u)

    matriz = conn.execute("SELECT * FROM coherencia_horizontal WHERE id = ?", (matriz_id,)).fetchone()
    if not matriz:
        flash("Matriz no encontrada.", "error")
        return redirect(url_for("coherencia_bp.coherencia_index"))

    es_propietario = (matriz["docente_id"] == u["id"])
    if not es_propietario and not admin:
        flash("Sin permiso para ver esta matriz.", "error")
        return redirect(url_for("coherencia_bp.coherencia_index"))

    puede_editar = es_propietario

    if request.method == "POST":
        if not puede_editar:
            flash("Sin permiso para editar esta matriz.", "error")
            return redirect(url_for("coherencia_bp.coherencia_editar", matriz_id=matriz_id))
        if not _csrf_check():
            flash("Token de seguridad inválido.", "error")
            return redirect(url_for("coherencia_bp.coherencia_editar", matriz_id=matriz_id))

        accion = request.form.get("accion")

        if accion == "agregar_fila":
            area      = request.form.get("area", "").strip()
            contenido = request.form.get("contenido", "").strip()
            if not area or not contenido:
                flash("Cada fila necesita al menos Área/Asignatura y Contenido.", "error")
            else:
                orden = conn.execute(
                    "SELECT COALESCE(MAX(orden), -1) + 1 FROM coherencia_horizontal_fila WHERE matriz_id = ?",
                    (matriz_id,),
                ).fetchone()[0]
                conn.execute(
                    """INSERT INTO coherencia_horizontal_fila
                       (matriz_id, area, competencias, contenido, indicador, articulacion, orden)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        matriz_id, area,
                        request.form.get("competencias", "").strip(),
                        contenido,
                        request.form.get("indicador", "").strip(),
                        request.form.get("articulacion", "").strip(),
                        orden,
                    ),
                )
                conn.execute(
                    "UPDATE coherencia_horizontal SET fecha_actualizacion = datetime('now') WHERE id = ?",
                    (matriz_id,),
                )
                conn.commit()

        elif accion == "eliminar_fila":
            conn.execute(
                "DELETE FROM coherencia_horizontal_fila WHERE id = ? AND matriz_id = ?",
                (request.form.get("fila_id"), matriz_id),
            )
            conn.execute(
                "UPDATE coherencia_horizontal SET fecha_actualizacion = datetime('now') WHERE id = ?",
                (matriz_id,),
            )
            conn.commit()

        return redirect(url_for("coherencia_bp.coherencia_editar", matriz_id=matriz_id))

    filas = conn.execute(
        "SELECT * FROM coherencia_horizontal_fila WHERE matriz_id = ? ORDER BY orden, id",
        (matriz_id,),
    ).fetchall()

    return render_template(
        "coherencia/editar.html",
        matriz=matriz,
        filas=filas,
        es_admin=admin,
        puede_editar=puede_editar,
    )


@coherencia_bp.route("/coherencia/<int:matriz_id>/eliminar", methods=["POST"])
@login_required
def coherencia_eliminar(matriz_id):
    u = get_usuario()
    conn = get_db()
    admin = _es_admin(u)

    matriz = conn.execute("SELECT * FROM coherencia_horizontal WHERE id = ?", (matriz_id,)).fetchone()
    if not matriz:
        flash("Matriz no encontrada.", "error")
        return redirect(url_for("coherencia_bp.coherencia_index"))
    if matriz["docente_id"] != u["id"] and not admin:
        flash("Sin permiso para eliminar esta matriz.", "error")
        return redirect(url_for("coherencia_bp.coherencia_index"))
    if not _csrf_check():
        flash("Token de seguridad inválido.", "error")
        return redirect(url_for("coherencia_bp.coherencia_index"))

    conn.execute("DELETE FROM coherencia_horizontal_fila WHERE matriz_id = ?", (matriz_id,))
    conn.execute("DELETE FROM coherencia_horizontal WHERE id = ?", (matriz_id,))
    conn.commit()
    flash("Matriz eliminada.", "success")
    return redirect(url_for("coherencia_bp.coherencia_index"))


@coherencia_bp.route("/coherencia/<int:matriz_id>/imprimir")
@login_required
def coherencia_imprimir(matriz_id):
    u = get_usuario()
    conn = get_db()
    admin = _es_admin(u)

    matriz = conn.execute(
        """SELECT m.*, us.nombre AS docente_nombre
           FROM coherencia_horizontal m
           JOIN usuarios us ON us.id = m.docente_id
           WHERE m.id = ?""",
        (matriz_id,),
    ).fetchone()
    if not matriz:
        return "Matriz no encontrada", 404
    if matriz["docente_id"] != u["id"] and not admin:
        return "Sin permiso para ver esta matriz.", 403

    filas = conn.execute(
        "SELECT * FROM coherencia_horizontal_fila WHERE matriz_id = ? ORDER BY orden, id",
        (matriz_id,),
    ).fetchall()

    return render_template(
        "coherencia/imprimir.html",
        matriz=matriz,
        filas=filas,
        centro=_get_config_centro(),
    )
