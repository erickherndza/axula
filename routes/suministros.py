# -*- coding: utf-8 -*-
"""Blueprint: suministros — Inventario, movimientos y raciones diarias"""

import sqlite3
import logging
from datetime import datetime, date
from flask import (
    Blueprint, render_template, request, jsonify, session, abort,
)

from core.constants import DATABASE, ROLES_DIRECTORA, ROLES_SUPER
from core.database import get_db
from core.auth import login_required, _normalizar_rol, get_usuario

logger = logging.getLogger("axula")

suministros_bp = Blueprint("suministros_bp", __name__)

RACIONES_PERSONAL = 50  # fijo siempre

CATEGORIAS_SUMINISTRO = {
    "alimento":        "Alimento",
    "material_oficina": "Material de Oficina",
    "limpieza":        "Limpieza",
    "otro":            "Otro",
}

UNIDADES = ["raciones", "unidades", "kg", "lb", "litros", "cajas", "paquetes", "resmas"]


def _sumi_required(f):
    import functools
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user_id"):
            from flask import redirect
            return redirect("/login")
        rol = _normalizar_rol(session.get("rol", ""))
        permitidos = {"suministros", "directora", "superusuario",
                      "coordinador_general"}
        if rol not in permitidos:
            return jsonify({"error": "Sin permisos para esta sección"}), 403
        return f(*args, **kwargs)
    return decorated


def _estudiantes_activos_hoy():
    """Cuenta estudiantes activos en la DB."""
    db = get_db()
    return db.execute(
        "SELECT COUNT(*) FROM estudiantes WHERE condicion='ACTIVO'"
    ).fetchone()[0]


# ── PORTAL ───────────────────────────────────────────────────────────────────

@suministros_bp.route("/suministros")
@login_required
@_sumi_required
def portal_suministros():
    u = get_usuario()
    return render_template("suministros.html",
        categorias=CATEGORIAS_SUMINISTRO,
        unidades=UNIDADES,
        raciones_personal=RACIONES_PERSONAL,
        current_user=u,
    )


# ── INVENTARIO ────────────────────────────────────────────────────────────────

@suministros_bp.route("/api/suministros/inventario")
@login_required
@_sumi_required
def listar_inventario():
    db = get_db()
    rows = db.execute("""
        SELECT s.id, s.nombre, s.descripcion, s.categoria, s.unidad,
               s.stock_actual, s.stock_minimo, s.ubicacion, s.fecha_creacion,
               u.nombre AS creado_por_nombre
        FROM inventario_suministros s
        LEFT JOIN usuarios u ON u.id = s.creado_por
        WHERE s.activo = 1
        ORDER BY s.categoria, s.nombre
    """).fetchall()

    resultado = []
    for r in rows:
        alerta = None
        if r["stock_minimo"] and r["stock_actual"] <= r["stock_minimo"]:
            alerta = "bajo"
        elif r["stock_actual"] == 0:
            alerta = "agotado"
        resultado.append({
            "id":           r["id"],
            "nombre":       r["nombre"],
            "descripcion":  r["descripcion"] or "",
            "categoria":    r["categoria"],
            "categoria_label": CATEGORIAS_SUMINISTRO.get(r["categoria"], r["categoria"]),
            "unidad":       r["unidad"],
            "stock_actual": r["stock_actual"],
            "stock_minimo": r["stock_minimo"] or 0,
            "ubicacion":    r["ubicacion"] or "",
            "alerta":       alerta,
            "creado_por":   r["creado_por_nombre"] or "—",
        })

    return jsonify({"inventario": resultado, "total": len(resultado)})


@suministros_bp.route("/api/suministros/inventario", methods=["POST"])
@login_required
@_sumi_required
def crear_suministro():
    d = request.get_json() or {}
    nombre = (d.get("nombre") or "").strip()[:200]
    if not nombre:
        return jsonify({"error": "Nombre requerido"}), 400

    categoria = d.get("categoria", "otro")
    if categoria not in CATEGORIAS_SUMINISTRO:
        categoria = "otro"
    unidad = (d.get("unidad") or "unidades").strip()[:50]

    db = get_db()
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur = db.execute("""
        INSERT INTO inventario_suministros
            (nombre, descripcion, categoria, unidad, stock_actual,
             stock_minimo, ubicacion, activo, fecha_creacion, creado_por)
        VALUES (?,?,?,?,?,?,?,1,?,?)
    """, (
        nombre,
        (d.get("descripcion") or "").strip()[:500],
        categoria, unidad,
        float(d.get("stock_actual", 0)),
        float(d.get("stock_minimo", 0)),
        (d.get("ubicacion") or "").strip()[:200],
        ahora, session["user_id"],
    ))
    db.commit()
    logger.info(f"[SUMINISTROS] Creado: {nombre} por user_id={session['user_id']}")
    return jsonify({"ok": True, "id": cur.lastrowid})


@suministros_bp.route("/api/suministros/inventario/<int:sid>", methods=["PUT"])
@login_required
@_sumi_required
def editar_suministro(sid):
    d = request.get_json() or {}
    db = get_db()
    row = db.execute("SELECT id FROM inventario_suministros WHERE id=? AND activo=1", (sid,)).fetchone()
    if not row:
        return jsonify({"error": "No encontrado"}), 404

    nombre = (d.get("nombre") or "").strip()[:200]
    if not nombre:
        return jsonify({"error": "Nombre requerido"}), 400

    categoria = d.get("categoria", "otro")
    if categoria not in CATEGORIAS_SUMINISTRO:
        categoria = "otro"

    db.execute("""
        UPDATE inventario_suministros
        SET nombre=?, descripcion=?, categoria=?, unidad=?,
            stock_minimo=?, ubicacion=?
        WHERE id=?
    """, (
        nombre,
        (d.get("descripcion") or "").strip()[:500],
        categoria,
        (d.get("unidad") or "unidades").strip()[:50],
        float(d.get("stock_minimo", 0)),
        (d.get("ubicacion") or "").strip()[:200],
        sid,
    ))
    db.commit()
    return jsonify({"ok": True})


@suministros_bp.route("/api/suministros/inventario/<int:sid>", methods=["DELETE"])
@login_required
@_sumi_required
def eliminar_suministro(sid):
    rol = _normalizar_rol(session.get("rol", ""))
    if rol not in ROLES_DIRECTORA | {"coordinador_general"}:
        return jsonify({"error": "Solo directora/coordinador puede eliminar"}), 403

    db = get_db()
    db.execute("UPDATE inventario_suministros SET activo=0 WHERE id=?", (sid,))
    db.commit()
    return jsonify({"ok": True})


# ── MOVIMIENTOS (entradas / salidas / ajustes) ────────────────────────────────

@suministros_bp.route("/api/suministros/movimientos")
@login_required
@_sumi_required
def listar_movimientos():
    sid = request.args.get("suministro_id", type=int)
    limit = min(int(request.args.get("limit", 50)), 200)

    db = get_db()
    cond = "WHERE 1=1"
    params = []
    if sid:
        cond += " AND m.suministro_id = ?"
        params.append(sid)

    rows = db.execute(f"""
        SELECT m.id, m.suministro_id, s.nombre AS suministro_nombre,
               m.tipo, m.cantidad, m.motivo, m.fecha,
               u.nombre AS registrado_por_nombre,
               m.referencia_mov_financiero
        FROM movimientos_suministros m
        JOIN inventario_suministros s ON s.id = m.suministro_id
        LEFT JOIN usuarios u ON u.id = m.registrado_por
        {cond}
        ORDER BY m.fecha DESC, m.id DESC
        LIMIT ?
    """, params + [limit]).fetchall()

    return jsonify({"movimientos": [dict(r) for r in rows]})


@suministros_bp.route("/api/suministros/movimientos", methods=["POST"])
@login_required
@_sumi_required
def registrar_movimiento():
    d = request.get_json() or {}
    sid = d.get("suministro_id")
    tipo = d.get("tipo", "")
    cantidad = d.get("cantidad")
    motivo = (d.get("motivo") or "").strip()[:300]
    fecha = d.get("fecha") or date.today().isoformat()
    vincular_finanzas = d.get("vincular_finanzas", False)
    monto_financiero = d.get("monto_financiero")
    concepto_financiero = (d.get("concepto_financiero") or "").strip()[:200]

    if not sid or tipo not in ("entrada", "salida", "ajuste"):
        return jsonify({"error": "Datos incompletos"}), 400
    try:
        cantidad = float(cantidad)
        if cantidad <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"error": "Cantidad debe ser un número positivo"}), 400

    db = get_db()
    row = db.execute(
        "SELECT id, nombre, stock_actual, unidad FROM inventario_suministros WHERE id=? AND activo=1",
        (sid,)
    ).fetchone()
    if not row:
        return jsonify({"error": "Suministro no encontrado"}), 404

    # Calcular nuevo stock
    stock = row["stock_actual"]
    if tipo == "entrada":
        nuevo_stock = stock + cantidad
    elif tipo == "salida":
        if cantidad > stock:
            return jsonify({"error": f"Stock insuficiente. Disponible: {stock} {row['unidad']}"}), 400
        nuevo_stock = stock - cantidad
    else:  # ajuste
        nuevo_stock = cantidad  # ajuste reemplaza el valor

    # Registrar movimiento en suministros
    cur = db.execute("""
        INSERT INTO movimientos_suministros
            (suministro_id, tipo, cantidad, motivo, fecha, registrado_por)
        VALUES (?,?,?,?,?,?)
    """, (sid, tipo, cantidad, motivo, fecha, session["user_id"]))
    mov_id = cur.lastrowid

    # Actualizar stock
    db.execute("UPDATE inventario_suministros SET stock_actual=? WHERE id=?", (nuevo_stock, sid))

    # Vincular a finanzas si se solicitó y hay monto
    ref_financiero = None
    if vincular_finanzas and monto_financiero:
        try:
            monto = float(monto_financiero)
            if monto > 0:
                # Buscar o crear categoría "Suministros" en categorías de gasto
                cat = db.execute(
                    "SELECT id FROM categorias_gasto WHERE LOWER(nombre) LIKE 'suministro%' AND activa=1 LIMIT 1"
                ).fetchone()
                if not cat:
                    db.execute(
                        "INSERT INTO categorias_gasto (nombre, tipo, activa) VALUES ('Suministros','gasto',1)"
                    )
                    cat_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
                else:
                    cat_id = cat["id"]

                concepto = concepto_financiero or f"Compra {row['nombre']} ({cantidad} {row['unidad']})"
                db.execute("""
                    INSERT INTO movimientos_financieros
                        (tipo, categoria_id, concepto, monto, fecha, registrado_por, observaciones)
                    VALUES ('gasto',?,?,?,?,?,?)
                """, (cat_id, concepto, monto, fecha, session["user_id"],
                      f"Vinculado mov_suministros id={mov_id}"))
                ref_financiero = db.execute("SELECT last_insert_rowid()").fetchone()[0]

                # Actualizar referencia en movimiento
                db.execute(
                    "UPDATE movimientos_suministros SET referencia_mov_financiero=? WHERE id=?",
                    (ref_financiero, mov_id)
                )
        except (TypeError, ValueError):
            pass  # monto inválido — movimiento se guarda igual sin vínculo

    db.commit()

    logger.info(
        f"[SUMINISTROS] Movimiento: {tipo} {cantidad} de '{row['nombre']}' "
        f"por user_id={session['user_id']} → stock={nuevo_stock}"
    )

    return jsonify({
        "ok": True, "id": mov_id,
        "nuevo_stock": nuevo_stock,
        "referencia_financiero": ref_financiero,
    })


# ── RACIONES DIARIAS ──────────────────────────────────────────────────────────

@suministros_bp.route("/api/suministros/raciones")
@login_required
@_sumi_required
def listar_raciones():
    mes = request.args.get("mes")  # YYYY-MM
    db = get_db()
    cond = ""
    params = []
    if mes:
        cond = "WHERE r.fecha LIKE ?"
        params = [f"{mes}%"]

    rows = db.execute(f"""
        SELECT r.id, r.fecha, r.tipo_racion, r.raciones_estudiantes,
               r.raciones_personal, r.total_raciones, r.notas,
               u.nombre AS registrado_por_nombre
        FROM raciones_diarias r
        LEFT JOIN usuarios u ON u.id = r.registrado_por
        {cond}
        ORDER BY r.fecha DESC, r.tipo_racion
        LIMIT 200
    """, params).fetchall()

    return jsonify({"raciones": [dict(r) for r in rows]})


@suministros_bp.route("/api/suministros/raciones", methods=["POST"])
@login_required
@_sumi_required
def registrar_racion():
    d = request.get_json() or {}
    fecha = (d.get("fecha") or date.today().isoformat()).strip()
    tipo = d.get("tipo_racion", "")
    if tipo not in ("desayuno", "almuerzo"):
        return jsonify({"error": "tipo_racion debe ser 'desayuno' o 'almuerzo'"}), 400

    # Calcular raciones de estudiantes (activos en DB)
    rac_estudiantes = _estudiantes_activos_hoy()
    total = rac_estudiantes + RACIONES_PERSONAL

    db = get_db()
    try:
        db.execute("""
            INSERT INTO raciones_diarias
                (fecha, tipo_racion, raciones_estudiantes, raciones_personal,
                 total_raciones, registrado_por, notas)
            VALUES (?,?,?,?,?,?,?)
        """, (fecha, tipo, rac_estudiantes, RACIONES_PERSONAL, total,
              session["user_id"], (d.get("notas") or "").strip()[:300]))
        db.commit()
    except sqlite3.IntegrityError:
        # UNIQUE(fecha, tipo_racion) — ya existe, actualizar
        db.execute("""
            UPDATE raciones_diarias
            SET raciones_estudiantes=?, raciones_personal=?, total_raciones=?,
                registrado_por=?, notas=?
            WHERE fecha=? AND tipo_racion=?
        """, (rac_estudiantes, RACIONES_PERSONAL, total,
              session["user_id"], (d.get("notas") or "").strip()[:300],
              fecha, tipo))
        db.commit()

    logger.info(f"[SUMINISTROS] Ración {tipo} {fecha}: {rac_estudiantes} est + {RACIONES_PERSONAL} pers = {total}")
    return jsonify({
        "ok": True,
        "fecha": fecha, "tipo_racion": tipo,
        "raciones_estudiantes": rac_estudiantes,
        "raciones_personal": RACIONES_PERSONAL,
        "total_raciones": total,
    })


@suministros_bp.route("/api/suministros/resumen")
@login_required
@_sumi_required
def resumen():
    """KPIs rápidos para el dashboard del portal."""
    db = get_db()

    total_items = db.execute(
        "SELECT COUNT(*) FROM inventario_suministros WHERE activo=1"
    ).fetchone()[0]

    bajos = db.execute("""
        SELECT COUNT(*) FROM inventario_suministros
        WHERE activo=1 AND stock_minimo > 0 AND stock_actual <= stock_minimo
    """).fetchone()[0]

    agotados = db.execute(
        "SELECT COUNT(*) FROM inventario_suministros WHERE activo=1 AND stock_actual = 0"
    ).fetchone()[0]

    hoy = date.today().isoformat()
    raciones_hoy = db.execute(
        "SELECT SUM(total_raciones) FROM raciones_diarias WHERE fecha=?", (hoy,)
    ).fetchone()[0] or 0

    movs_hoy = db.execute(
        "SELECT COUNT(*) FROM movimientos_suministros WHERE fecha=?", (hoy,)
    ).fetchone()[0]

    return jsonify({
        "total_items": total_items,
        "bajos": bajos,
        "agotados": agotados,
        "raciones_hoy": raciones_hoy,
        "movimientos_hoy": movs_hoy,
        "estudiantes_activos": _estudiantes_activos_hoy(),
        "personal_fijo": RACIONES_PERSONAL,
    })
