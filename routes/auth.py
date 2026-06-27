# -*- coding: utf-8 -*-
"""Blueprint: auth"""

import sqlite3
import logging
import json as _json
import os
import re
import time as _time
import secrets as _sec_mod
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
    _csrf_token, _csrf_check, csrf_protected, rate_limited, _rate_peek, _rate_check,
    get_usuario,
)
from core.helpers import *
from core.helpers import _delete_recovery_token, _get_recovery_token, _guardar_recovery_token, _send_recovery_email, _validar_email_institucional
from core.ia import _get_groq_client, groq_client, construir_prompt, construir_prompt_planificacion, construir_prompt_rubrica, construir_prompt_estrategia
from core.excel import _parsear_boletin_bj, _buscar_o_crear_estudiante, _detectar_mencion_listado, _limpiar_nota
from core.pdf import _generar_pdf_acuerdo

logger = logging.getLogger("axula")

auth_bp = Blueprint("auth_bp", __name__)

@auth_bp.route("/api/smtp/config", methods=["GET"])
@login_required
def smtp_config_get():
    """Devuelve la configuración de email actual (sin contraseñas)."""
    u = get_usuario()
    if _normalizar_rol(u.get("rol", "")) not in ROLES_COORD and not u.get("es_directora"):
        return jsonify({"error": "Sin permisos"}), 403
    _cargar_env()
    resend_key  = os.environ.get("RESEND_API_KEY", "")
    smtp_user   = os.environ.get("SMTP_USER", "")
    smtp_pass   = os.environ.get("SMTP_PASS", "")
    metodo      = "resend" if resend_key else ("smtp" if smtp_user and smtp_pass else "ninguno")
    return jsonify({
        "metodo":       metodo,
        "resend_key":   bool(resend_key),
        "resend_from":  os.environ.get("RESEND_FROM", ""),
        "smtp_user":    smtp_user,
        "smtp_host":    os.environ.get("SMTP_HOST", "smtp.gmail.com"),
        "smtp_port":    os.environ.get("SMTP_PORT", "587"),
        "configurado":  metodo != "ninguno",
    })


@auth_bp.route("/api/smtp/config", methods=["POST"])
@login_required
def smtp_config_save():
    """
    Guarda la configuración SMTP en el archivo .env.
    Actualiza las líneas SMTP_* existentes o las agrega al final.
    """
    u = get_usuario()
    if _normalizar_rol(u.get("rol", "")) not in ROLES_COORD and not u.get("es_directora"):
        return jsonify({"error": "Sin permisos"}), 403

    d = request.get_json(force=True) or {}

    # Detectar si es configuración Resend o SMTP
    resend_key = (d.get("resend_api_key") or "").strip()
    resend_from = (d.get("resend_from") or "Axula <onboarding@resend.dev>").strip()

    smtp_user = (d.get("smtp_user") or "").strip()
    smtp_pass = (d.get("smtp_pass") or "").strip()
    smtp_host = (d.get("smtp_host") or "smtp.gmail.com").strip()
    smtp_port = str(d.get("smtp_port") or "587").strip()

    if resend_key:
        if not resend_key.startswith("re_"):
            return jsonify({"ok": False, "error": "RESEND_API_KEY inválida — debe empezar con re_"}), 400
        nuevas = {"RESEND_API_KEY": resend_key, "RESEND_FROM": resend_from}
    elif smtp_user:
        if "@" not in smtp_user:
            return jsonify({"ok": False, "error": "SMTP_USER inválido"}), 400
        if not smtp_pass:
            return jsonify({"ok": False, "error": "SMTP_PASS es requerido"}), 400
        nuevas = {"SMTP_USER": smtp_user, "SMTP_PASS": smtp_pass,
                  "SMTP_HOST": smtp_host, "SMTP_PORT": smtp_port}
    else:
        return jsonify({"ok": False, "error": "Nada que guardar"}), 400

    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")

    # Leer .env existente o crear vacío
    try:
        with open(env_path, "r") as f:
            lineas = f.readlines()
    except FileNotFoundError:
        lineas = []

    # Actualizar líneas existentes y rastrear cuáles se agregaron
    actualizadas = set()
    nuevas_lineas = []
    for linea in lineas:
        stripped = linea.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            nuevas_lineas.append(linea)
            continue
        clave = stripped.split("=", 1)[0].strip()
        if clave in nuevas:
            nuevas_lineas.append(f"{clave}={nuevas[clave]}\n")
            actualizadas.add(clave)
        else:
            nuevas_lineas.append(linea)

    # Agregar las que no existían
    for clave, valor in nuevas.items():
        if clave not in actualizadas:
            nuevas_lineas.append(f"{clave}={valor}\n")

    try:
        with open(env_path, "w") as f:
            f.writelines(nuevas_lineas)
    except Exception as ex:
        return jsonify({"ok": False, "error": f"No se pudo escribir .env: {ex}"}), 500

    # Recargar en memoria inmediatamente
    for clave, valor in nuevas.items():
        os.environ[clave] = valor

    return jsonify({"ok": True, "mensaje": "Configuración SMTP guardada en .env"})


@auth_bp.route("/api/smtp/test", methods=["POST"])
@login_required
def smtp_test():
    """Prueba de envío — intenta Resend primero, luego SMTP."""
    u = get_usuario()
    if _normalizar_rol(u.get("rol", "")) not in ROLES_COORD and not u.get("es_directora"):
        return jsonify({"error": "Sin permisos"}), 403
    d = request.get_json(silent=True) or {}
    to_email = d.get("email", "").strip()
    if not to_email or "@" not in to_email:
        return jsonify({"error": "Email inválido"}), 400

    _cargar_env()

    resend_key = os.environ.get("RESEND_API_KEY", "").strip()
    smtp_user  = os.environ.get("SMTP_USER", "").strip()
    smtp_pass  = os.environ.get("SMTP_PASS", "").strip()

    # ── Sin ningún método configurado ────────────────────────────────────
    if not resend_key and (not smtp_user or not smtp_pass):
        return jsonify({
            "ok": False,
            "error": "Ningún método de envío configurado",
            "metodo": "ninguno",
            "ayuda": (
                "OPCIÓN A — Resend (recomendado, más simple):\n"
                "1. Ve a resend.com → crea cuenta gratis\n"
                "2. En API Keys → Create API Key\n"
                "3. Agrega en .env:\n"
                "RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxx\n"
                "RESEND_FROM=Axula <onboarding@resend.dev>\n\n"
                "OPCIÓN B — Gmail SMTP:\n"
                "SMTP_USER=tucorreo@gmail.com\n"
                "SMTP_PASS=xxxx xxxx xxxx xxxx\n"
                "SMTP_HOST=smtp.gmail.com\n"
                "SMTP_PORT=587"
            )
        })

    # ── Intentar Resend ──────────────────────────────────────────────────
    if resend_key:
        try:
            import urllib.request as _req, json as _json
            from_addr = os.environ.get("RESEND_FROM", "Axula <onboarding@resend.dev>").strip()
            payload = _json.dumps({
                "from":    from_addr,
                "to":      [to_email],
                "subject": "✅ Axula — Prueba de email (Resend)",
                "html":    f"<p>✅ Email de prueba enviado correctamente desde Axula usando <b>Resend</b>.</p>"
                           f"<p style='color:#888;font-size:12px;'>Destinatario: {to_email}</p>",
            }).encode()
            req = _req.Request(
                "https://api.resend.com/emails",
                data=payload,
                headers={
                    "Authorization": f"Bearer {resend_key}",
                    "Content-Type": "application/json",
                },
                method="POST"
            )
            with _req.urlopen(req, timeout=15) as resp:
                result = _json.loads(resp.read())
            if result.get("id"):
                return jsonify({
                    "ok": True,
                    "metodo": "resend",
                    "mensaje": f"Email enviado a {to_email} vía Resend",
                    "smtp_host": "api.resend.com",
                    "smtp_port": 443,
                })
            return jsonify({
                "ok": False,
                "metodo": "resend",
                "error": f"Resend respondió: {result}",
                "ayuda": "Verifica que RESEND_API_KEY sea válida en resend.com/api-keys"
            })
        except Exception as ex:
            if not smtp_user or not smtp_pass:
                return jsonify({
                    "ok": False,
                    "metodo": "resend",
                    "error": f"Error Resend: {str(ex)}",
                    "ayuda": "Verifica RESEND_API_KEY en .env o agrega SMTP_USER/SMTP_PASS como alternativa."
                })
            # Caer al SMTP

    # ── Intentar SMTP ────────────────────────────────────────────────────
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com").strip()
    smtp_port_raw = os.environ.get("SMTP_PORT", "587").strip()
    try:
        smtp_port = int(smtp_port_raw)
    except ValueError:
        smtp_port = 587

    faltantes = []
    if not smtp_user: faltantes.append("SMTP_USER")
    if not smtp_pass: faltantes.append("SMTP_PASS")
    if faltantes:
        return jsonify({
            "ok": False,
            "metodo": "smtp",
            "error": f"Variable(s) no configurada(s): {', '.join(faltantes)}",
            "ayuda": (
                "Opción más fácil: usa Resend (resend.com) — solo necesitas RESEND_API_KEY\n"
                "Para SMTP Gmail:\n"
                "SMTP_USER=tucorreo@gmail.com\n"
                "SMTP_PASS=xxxx xxxx xxxx xxxx\n"
                "(Contraseña de aplicación — myaccount.google.com → Seguridad → Contraseñas de app)"
            )
        })

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "✅ Axula — Prueba SMTP"
        msg["From"]    = f"Axula <{smtp_user}>"
        msg["To"]      = to_email
        msg.attach(MIMEText(
            f"<p>✅ SMTP configurado correctamente.</p>"
            f"<p style='color:#888;font-size:12px;'>Servidor: {smtp_host}:{smtp_port}</p>",
            "html"
        ))
        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as s:
            s.ehlo(); s.starttls(); s.ehlo()
            s.login(smtp_user, smtp_pass)
            s.sendmail(smtp_user, to_email, msg.as_string())
        return jsonify({
            "ok": True,
            "metodo": "smtp",
            "mensaje": f"Email enviado a {to_email}",
            "smtp_host": smtp_host,
            "smtp_port": smtp_port,
        })
    except smtplib.SMTPAuthenticationError:
        return jsonify({
            "ok": False,
            "metodo": "smtp",
            "error": "Autenticación fallida — contraseña incorrecta",
            "ayuda": (
                f"Usuario: {smtp_user}\n"
                "SMTP_PASS debe ser una 'Contraseña de aplicación' de Google, no tu contraseña normal.\n"
                "Ve a: myaccount.google.com → Seguridad → Verificación 2 pasos → Contraseñas de aplicaciones"
            )
        })
    except Exception as ex:
        return jsonify({
            "ok": False,
            "metodo": "smtp",
            "error": str(ex),
            "ayuda": f"Servidor: {smtp_host}:{smtp_port} · Usuario: {smtp_user}"
        })


@auth_bp.route("/api/recovery/request", methods=["POST"])
@rate_limited(max_calls=5, window=60)
def recovery_request():
    """Solicita recuperación de contraseña por email institucional."""
    d = request.get_json(silent=True) or {}
    email = d.get("email", "").strip().lower()

    if not email or "@" not in email:
        return jsonify({"error": "Correo inválido"}), 400

    ok, msg = _validar_email_institucional(email)
    if not ok:
        return jsonify({"error": msg}), 400

    _MSG_GENERICO = "Si el correo está registrado, recibirás un enlace en breve."

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        u = conn.execute(
            """SELECT id, nombre, username, email FROM usuarios
               WHERE (lower(email)=? OR lower(username)=?) AND activo=1
               LIMIT 1""",
            (email, email)
        ).fetchone()

    # Siempre responde igual — nunca revelar si el correo/usuario existe
    if not u:
        logger.info(f"[RECOVERY] Solicitud para email no encontrado: {email}")
        return jsonify({"ok": True, "msg": _MSG_GENERICO})

    token = _sec_mod.token_urlsafe(32)
    _guardar_recovery_token(token, u["id"], datetime.now() + timedelta(minutes=30))

    smtp_configured = bool(os.environ.get("SMTP_USER") and os.environ.get("SMTP_PASS"))

    if smtp_configured:
        ok_mail, err = _send_recovery_email(email, token, u["nombre"])
        if not ok_mail:
            logger.error(f"[RECOVERY] Error enviando email a {email}: {err}")
        return jsonify({"ok": True, "msg": _MSG_GENERICO})

    # Sin SMTP: devolver el enlace directo al cliente (sistema interno)
    reset_url = f"{request.host_url.rstrip('/')}/reset-password/{token}"
    logger.warning(
        f"[RECOVERY] SMTP no configurado. Reset link para '{u['username']}' (id={u['id']}): {reset_url}"
    )
    return jsonify({"ok": True, "msg": _MSG_GENERICO, "reset_url": reset_url})


@auth_bp.route("/reset-password/<token>", methods=["GET"])
def reset_password_page(token):
    """Página para restablecer la contraseña."""
    data = _get_recovery_token(token)
    if not data:
        return render_template("login.html", error="El enlace expiró o no es válido. Solicita uno nuevo.")
    return render_template("reset_password.html", token=token)


@auth_bp.route("/api/recovery/link/<int:uid>", methods=["POST"])
@login_required
@csrf_protected
def admin_get_reset_link(uid):
    """
    Genera un enlace de restablecimiento de contraseña para cualquier usuario.
    Solo directora y coordinador_general pueden usarlo.
    Útil cuando SMTP no está configurado.
    """
    u = get_usuario()
    rol_solicitante = _normalizar_rol(u.get("rol",""))
    if rol_solicitante not in {"directora", "coordinador_general"}:
        logger.warning(f"[SECURITY] recovery/link denegado — rol={rol_solicitante} uid={u.get('id')} intentó reset uid={uid}")
        return jsonify({"error": "Sin permisos"}), 403

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        target = conn.execute("SELECT id, nombre, username FROM usuarios WHERE id=? AND activo=1", (uid,)).fetchone()
    if not target:
        return jsonify({"error": "Usuario no encontrado"}), 404

    token = _sec_mod.token_urlsafe(32)
    from datetime import datetime, timedelta
    _guardar_recovery_token(token, uid, datetime.now() + timedelta(hours=24))
    reset_url = f"{request.host_url.rstrip('/')}/reset-password/{token}"

    return jsonify({
        "ok": True,
        "reset_url": reset_url,
        "nombre": target["nombre"],
        "username": target["username"],
        "expira": "24 horas"
    })


@auth_bp.route("/api/recovery/reset", methods=["POST"])
@rate_limited(max_calls=5, window=60)
def recovery_reset():
    """Aplica la nueva contraseña."""
    d = request.get_json(silent=True) or {}
    token    = d.get("token", "")
    password = d.get("password", "").strip()

    if not token or not password:
        return jsonify({"error": "Datos incompletos"}), 400
    if len(password) < 6:
        return jsonify({"error": "La contraseña debe tener al menos 6 caracteres"}), 400

    data = _get_recovery_token(token)
    if not data:
        return jsonify({"error": "El enlace expiró. Solicita uno nuevo."}), 400

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.execute("UPDATE usuarios SET password=? WHERE id=?",
                     (_hash(password), data["user_id"]))
        conn.commit()

    # Invalidar token
    _delete_recovery_token(token)
    return jsonify({"ok": True})


@auth_bp.route("/login", methods=["GET"])
def login_page():
    if session.get("user_id"):
        return redirect("/")
    error = request.args.get("error", "")
    return render_template("login.html", error=error)


@auth_bp.route("/login", methods=["POST"])
def login_post():
    # ── Rate limiting: solo cuenta intentos FALLIDOS ─────────────────────────
    ip  = request.remote_addr or "unknown"
    key = f"login_fail:{ip}"

    # Verificar si ya está bloqueado (sin consumir slot)
    if not _rate_peek(key, max_calls=5, window=300):
        return render_template("login.html",
            error="Demasiados intentos fallidos. Espera 5 minutos.")

    username = request.form.get("username","").strip()
    password = request.form.get("password","").strip()
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        u = conn.execute(
            "SELECT * FROM usuarios WHERE (username=? OR lower(email)=lower(?)) AND activo=1", (username, username)
        ).fetchone()
    if not u or not _check_password(u["password"], password, user_id=u["id"] if u else None):
        # Registrar fallo — consume un slot
        _rate_check(key, max_calls=5, window=300)
        logger.warning(f"[AUTH] Login fallido para '{username}' desde {ip}")
        return redirect("/login?error=Credenciales incorrectas")

    # Login exitoso
    session.permanent = True
    session["user_id"]  = u["id"]
    session["username"] = u["username"]
    session["nombre"]   = u["nombre"]
    session["rol"]      = u["rol"]
    session["materia"]       = u["materia"]       or ""
    session["grado"]         = u["grado"]         or ""
    session["mencion"]       = u["mencion"]       or ""
    session["tipo_docencia"] = u["tipo_docencia"] or ""
    # Redirigir según rol
    rol_norm = _normalizar_rol(u["rol"])
    session.modified = True
    # Use a page-based redirect instead of 302 to ensure cookie is committed
    if rol_norm == "superusuario":
        dest = "/"
    elif rol_norm == "profesor":
        dest = "/profesor"
    elif rol_norm == "padre":
        dest = "/portal-padres"
    elif rol_norm in ("secretaria", "secretaria_docente"):
        dest = "/secretaria"
    elif rol_norm == "digitador":
        dest = "/digitador"
    elif rol_norm == "auxiliar_contabilidad":
        dest = "/finanzas"
    elif rol_norm == "suministros":
        dest = "/suministros"
    elif rol_norm == "asistente_directora":
        dest = "/asistente"
    else:
        dest = "/"
    return f'''<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="0;url={dest}">
<script>window.location.replace("{dest}");</script>
</head><body>
<p>Redirigiendo...</p>
</body></html>'''


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@auth_bp.route("/api/cambiar-password", methods=["POST"])
@login_required
def cambiar_password_propio():
    """Permite al usuario cambiar su propia contraseña verificando la actual."""
    u = get_usuario()
    d = request.get_json(silent=True) or {}
    pwd_actual = (d.get("password_actual") or "").strip()
    pwd_nueva  = (d.get("password_nueva")  or "").strip()

    if not pwd_actual or not pwd_nueva:
        return jsonify({"error": "Ambas contraseñas son requeridas"}), 400
    if len(pwd_nueva) < 8:
        return jsonify({"error": "La nueva contraseña debe tener al menos 8 caracteres"}), 400

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT password FROM usuarios WHERE id=?", (u["id"],)).fetchone()
        if not row or not _check_password(row["password"], pwd_actual):
            return jsonify({"error": "La contraseña actual es incorrecta"}), 403
        from werkzeug.security import generate_password_hash
        nuevo_hash = generate_password_hash(pwd_nueva)
        conn.execute("UPDATE usuarios SET password=? WHERE id=?", (nuevo_hash, u["id"]))
        conn.commit()

    return jsonify({"ok": True})


# ══════════════════════════════════════════════════════════════════════════════
#  PORTAL DE PADRES / TUTORES
#  Acceso de solo lectura para padres, madres y tutores.
#  Rol: "padre" — ve únicamente los hijos vinculados a su cuenta.
# ══════════════════════════════════════════════════════════════════════════════


