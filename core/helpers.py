# -*- coding: utf-8 -*-
"""Funciones auxiliares del sistema Axula."""

import os
import sqlite3
import logging
import re
import json as _json
import smtplib
import threading
from datetime import datetime, date, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import session, request, render_template

from .constants import DATABASE, DOMINIOS_INSTITUCIONALES, ROLES_COORD, DEFAULTS_CENTRO
from .auth import get_usuario, _normalizar_rol

logger = logging.getLogger("axula")

__all__ = [
    "_alerta_nuevo_reporte",
    "_anio_escolar_actual",
    "_anonimizar_estudiante",
    "_audit",
    "_buscar_estudiante_bd",
    "_calcular_bienestar_emocional",
    "_calcular_indice_conductual",
    "_calcular_nota_final_con_recuperacion",
    "_color_nota",
    "_construir_prompt_asignacion",
    "_crear_notificacion",
    "_delete_recovery_token",
    "_enviar_bienvenida",
    "_features_para_clustering",
    "_generar_ics",
    "_get_config_centro",
    "_get_hijos",
    "_get_periodos_estado",
    "_get_profesor",
    "_get_recovery_token",
    "_guardar_recovery_token",
    "_hook_asistencia_ausente",
    "_hook_nuevo_reporte",
    "_is_api_request",
    "_nota_estado",
    "_nota_requiere_recuperacion",
    "_enviar_email_raw",
    "_notificar",
    "_notificar_psicologa",
    "_notificar_reporte_nuevo",
    "_parse_ics_date",
    "_periodo_actual",
    "_periodo_bloqueado",
    "_prompt_sanitize",
    "_psicologa_del_ciclo",
    "_recalcular_indicadores",
    "_registrar_ausencia_semanal",
    "_render_perfil_staff",
    "_resolver_alcance_profesor",
    "_semana_iso",
    "_send_recovery_email",
    "_validar_email_institucional",
    "_validar_email_usuario",
    "_validar_materia_profesor",
    "_validar_magic_archivo",
    "_verificar_ausencias_semana",
    "analizar_perfil_maestro",
    "calcular_promedio_modulos",
    "calcular_proyeccion",
    "limpiar_v",
    "_normalizar_materia",
]

# Aliases de materias: normaliza variantes de casing/escritura a nombre canónico MINERD
_ALIAS_MATERIAS = {
    "lengua española":      "Lengua Española",
    "lengua espanola":      "Lengua Española",
    "español":              "Lengua Española",
    "espanol":              "Lengua Española",
    "lengua":               "Lengua Española",
    "matemática":           "Matemática",
    "matematica":           "Matemática",
    "matemáticas":          "Matemática",
    "matematicas":          "Matemática",
    "ciencias de la naturaleza": "Ciencias de la Naturaleza",
    "ciencias naturales":   "Ciencias de la Naturaleza",
    "ciencias sociales":    "Ciencias Sociales",
    "sociales":             "Ciencias Sociales",
    "educación artística":  "Educación Artística",
    "educacion artistica":  "Educación Artística",
    "ed. artística":        "Educación Artística",
    "ed artistica":         "Educación Artística",
    "educación física":     "Educación Física",
    "educacion fisica":     "Educación Física",
    "ed. física":           "Educación Física",
    "ed física":            "Educación Física",
    "idioma inglés":        "Idioma Inglés",
    "idioma ingles":        "Idioma Inglés",
    "inglés":               "Idioma Inglés",
    "ingles":               "Idioma Inglés",
    "idioma francés":       "Idioma Francés",
    "idioma frances":       "Idioma Francés",
    "francés":              "Idioma Francés",
    "frances":              "Idioma Francés",
    "formación integral":   "Formación Integral Humana y Religiosa",
    "formacion integral":   "Formación Integral Humana y Religiosa",
    "fihr":                 "Formación Integral Humana y Religiosa",
}


def get_ring_color(promedio, theme='light'):
    """Color del anillo de progreso — Axula v3. Sin verde fluorescente."""
    if theme == 'light':
        if promedio is None:    return '#D3D1C7'
        if promedio < 60:       return '#E24B4A'
        if promedio < 70:       return '#378ADD'
        if promedio < 80:       return '#378ADD'
        if promedio < 89:       return '#185FA5'
        return                         '#042C53'
    else:
        if promedio is None:    return '#143D6B'
        if promedio < 60:       return '#E8A0A0'
        if promedio < 70:       return '#7EB3D8'
        if promedio < 80:       return '#7EB3D8'
        if promedio < 89:       return '#A8CCEA'
        return                         '#9FD4C4'


def get_estado_class(promedio):
    """Clase CSS Axula según promedio (para ax-metric-*)."""
    if promedio is None:    return 'ax-metric-default'
    if promedio < 70:       return 'ax-metric-critico'
    if promedio < 80:       return 'ax-metric-obs'
    if promedio < 89:       return 'ax-metric-bueno'
    return                         'ax-metric-optimo'


def _normalizar_materia(nombre: str) -> str:
    """
    Normaliza el nombre de una materia a su forma canónica MINERD.
    Aplica alias conocidos primero; si no hay alias, usa Title Case limpio.
    Evita duplicados por diferencias de casing en materias_calificaciones.
    """
    if not nombre:
        return nombre
    norm = nombre.strip().lower().rstrip(".")
    if norm in _ALIAS_MATERIAS:
        return _ALIAS_MATERIAS[norm]
    # Sin alias: Title Case preservando acentos
    return " ".join(w.capitalize() for w in nombre.strip().split())


def _anonimizar_estudiante(est_id, nombre=None, apellido=None):
    """
    Retorna un código anónimo estable para usar en prompts de IA.
    El código es determinista para el mismo est_id (EST-XXXX),
    así que si la IA lo menciona se puede rastrear internamente.
    Nunca envía nombre ni apellido real a la API.
    """
    import hashlib as _hl
    h = _hl.md5(str(est_id).encode()).hexdigest()[:4].upper()
    return f"EST-{h}"


def _prompt_sanitize(texto):
    """
    Elimina patrones comunes de datos personales de un string
    antes de enviarlo a una IA externa.
    Solo aplica a campos de texto libre.
    """
    import re as _re
    # Cédulas dominicanas (XXX-XXXXXXX-X)
    texto = _re.sub(r'\b\d{3}-\d{7}-\d\b', '[CEDULA]', texto)
    # Teléfonos (809/829/849-XXX-XXXX)
    texto = _re.sub(r'\b(?:809|829|849)[\s.-]?\d{3}[\s.-]?\d{4}\b', '[TEL]', texto)
    return texto

# ── VALIDACIÓN DE ARCHIVOS ───────────────────────────────────────────────────

# Magic bytes de formatos permitidos
_MAGIC_IMAGEN = {
    "jpg":  (b"\xFF\xD8\xFF",),
    "jpeg": (b"\xFF\xD8\xFF",),
    "png":  (b"\x89PNG\r\n\x1a\n",),
    "webp": None,          # WEBP requiere check especial (ver abajo)
    "gif":  (b"GIF87a", b"GIF89a"),
}
_MAGIC_OFFICE = {
    "xlsx": (b"PK\x03\x04",),                       # ZIP (Office Open XML)
    "xls":  (b"\xD0\xCF\x11\xE0",),                 # OLE Compound Document
}
# Magic bytes para todos los tipos aceptados en la biblioteca de archivos
_MAGIC_ARCHIVOS = {
    "pdf":  (b"%PDF",),                              # PDF
    "docx": (b"PK\x03\x04",),                        # ZIP/Office Open XML
    "doc":  (b"\xD0\xCF\x11\xE0",),                 # OLE Compound Document
    "xlsx": (b"PK\x03\x04",),
    "xls":  (b"\xD0\xCF\x11\xE0",),
    "jpg":  (b"\xFF\xD8\xFF",),
    "jpeg": (b"\xFF\xD8\xFF",),
    "png":  (b"\x89PNG\r\n\x1a\n",),
}


def _validar_magic_imagen(datos: bytes, ext: str) -> bool:
    """Verifica que los bytes del archivo coincidan con la extensión declarada."""
    ext = ext.lower().lstrip(".")
    if ext == "webp":
        # RIFF????WEBP
        return datos[:4] == b"RIFF" and datos[8:12] == b"WEBP"
    firmas = _MAGIC_IMAGEN.get(ext)
    if firmas is None:
        return False
    return any(datos[:len(f)] == f for f in firmas)


def _validar_magic_excel(datos: bytes, ext: str) -> bool:
    """Verifica que el archivo sea realmente un Excel o CSV válido."""
    ext = ext.lower().lstrip(".")
    if ext == "csv":
        # CSV: debe ser texto decodificable
        try:
            datos[:512].decode("utf-8-sig", errors="strict")
            return True
        except UnicodeDecodeError:
            return False
    firmas = _MAGIC_OFFICE.get(ext)
    if firmas is None:
        return False
    return any(datos[:len(f)] == f for f in firmas)


def _validar_magic_archivo(datos: bytes, ext: str) -> bool:
    """
    Valida que los magic bytes del contenido real coincidan con la extensión.
    Úsalo en subidas de archivos para prevenir MIME-type spoofing.
    Retorna False si el contenido no corresponde al tipo declarado.
    """
    ext = ext.lower().lstrip(".")
    firmas = _MAGIC_ARCHIVOS.get(ext)
    if firmas is None:
        return False
    return any(datos[:len(f)] == f for f in firmas)


# ── RATE LIMITING EXTENDIDO ──────────────────────────────────────────────────


def _validar_email_institucional(email):
    """
    Valida que el email tenga un formato válido.
    Puedes agregar dominios permitidos aquí si quieres restringir
    solo a correos @educacion.edu.do u otros dominios institucionales.
    """
    import re
    pattern = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False, "El correo no tiene un formato válido."
    # Opcional: descomentar para restringir solo a dominios institucionales
    # DOMINIOS_PERMITIDOS = {"educacion.edu.do", "minerd.edu.do"}
    # dominio = email.split("@")[1].lower()
    # if dominio not in DOMINIOS_PERMITIDOS:
    #     return False, f"Solo se permiten correos institucionales (@educacion.edu.do)."
    return True, ""


# Tokens de recuperación — en BD para persistir reinicios del servidor


def _guardar_recovery_token(token, user_id, expires):
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.execute("""
            INSERT OR REPLACE INTO recovery_tokens (token, user_id, expires)
            VALUES (?, ?, ?)
        """, (token, user_id, expires.isoformat()))
        conn.commit()


def _get_recovery_token(token):
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM recovery_tokens WHERE token=?", (token,)
        ).fetchone()
    if not row:
        return None
    expires = datetime.fromisoformat(row["expires"])
    if expires < datetime.now():
        _delete_recovery_token(token)
        return None
    return {"user_id": row["user_id"], "expires": expires}


def _delete_recovery_token(token):
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.execute("DELETE FROM recovery_tokens WHERE token=?", (token,))
        conn.commit()


def _audit(accion, descripcion, entidad=None, entidad_id=None,
           valor_anterior=None, valor_nuevo=None):
    """
    Registra una acción en el audit_log.
    Se llama desde cualquier ruta que modifique datos críticos.
    No lanza excepción si falla — el audit nunca debe bloquear la operación principal.
    """
    import json as _json
    try:
        u = get_usuario()
        uid    = u.get("id") if u else None
        nombre = u.get("nombre", "sistema") if u else "sistema"
        ip     = request.remote_addr or "—"
        with sqlite3.connect(DATABASE, timeout=5) as conn:
            conn.execute(
                """INSERT INTO audit_log
                   (usuario_id, usuario_nombre, accion, entidad, entidad_id,
                    descripcion, valor_anterior, valor_nuevo, ip)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    uid, nombre, accion, entidad, entidad_id,
                    descripcion,
                    _json.dumps(valor_anterior, ensure_ascii=False) if valor_anterior is not None else None,
                    _json.dumps(valor_nuevo,    ensure_ascii=False) if valor_nuevo    is not None else None,
                    ip,
                )
            )
    except Exception as _ex:
        logger.warning(f"[AUDIT] No se pudo registrar: {_ex}")


def _enviar_email_raw(to_email: str, asunto: str, html: str) -> None:
    """
    Envía un email de alerta institucional (non-blocking — corre en thread propio).
    Prefiere Resend API; cae a SMTP si no. Silencia cualquier error.
    """
    if not to_email or "@" not in to_email:
        return

    def _send():
        resend_key = os.environ.get("RESEND_API_KEY", "").strip()
        smtp_user  = os.environ.get("SMTP_USER", "").strip()
        smtp_pass  = os.environ.get("SMTP_PASS", "").strip()

        if not resend_key and (not smtp_user or not smtp_pass):
            return  # sin método configurado → silencioso

        # ── Resend API ─────────────────────────────────────────────────────
        if resend_key:
            try:
                import urllib.request as _req
                from_addr = os.environ.get("RESEND_FROM", "Axula <noreply@resend.dev>").strip()
                payload = _json.dumps({
                    "from":    from_addr,
                    "to":      [to_email],
                    "subject": asunto,
                    "html":    html,
                }).encode()
                req = _req.Request(
                    "https://api.resend.com/emails", data=payload,
                    headers={"Authorization": f"Bearer {resend_key}",
                             "Content-Type": "application/json"},
                    method="POST"
                )
                with _req.urlopen(req, timeout=10) as resp:
                    result = _json.loads(resp.read())
                if result.get("id"):
                    logger.info(f"[EMAIL] Enviado a {to_email} (Resend id={result['id']})")
                    return
            except Exception as ex:
                logger.warning(f"[EMAIL] Resend error → fallback SMTP: {ex}")

        # ── SMTP ───────────────────────────────────────────────────────────
        if smtp_user and smtp_pass:
            try:
                smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com").strip()
                smtp_port = int(os.environ.get("SMTP_PORT", "587"))
                msg = MIMEMultipart("alternative")
                msg["Subject"] = asunto
                msg["From"]    = f"Axula BJ <{smtp_user}>"
                msg["To"]      = to_email
                msg.attach(MIMEText(html, "html"))
                try:
                    with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as s:
                        s.ehlo(); s.starttls(); s.ehlo()
                        s.login(smtp_user, smtp_pass)
                        s.sendmail(smtp_user, to_email, msg.as_string())
                except Exception:
                    with smtplib.SMTP_SSL(smtp_host, 465, timeout=15) as s:
                        s.login(smtp_user, smtp_pass)
                        s.sendmail(smtp_user, to_email, msg.as_string())
                logger.info(f"[EMAIL] Enviado a {to_email} (SMTP)")
            except Exception as ex:
                logger.error(f"[EMAIL] SMTP error a {to_email}: {ex}")

    threading.Thread(target=_send, daemon=True).start()


def _notificar(tipo, titulo, mensaje, url=None, destinatarios=None):
    """
    Crea una notificación para coordinadores y/o directora.
    destinatarios: lista de user_ids, o None para todos los coordinadores/directora activos.
    No bloquea si falla.
    """
    try:
        with sqlite3.connect(DATABASE, timeout=5) as conn:
            if destinatarios is None:
                rows = conn.execute(
                    """SELECT id, nombre, email FROM usuarios WHERE activo=1
                       AND (rol IN ('directora','coordinador_general',
                                    'coordinador_primer_ciclo','coordinador_segundo_ciclo'))"""
                ).fetchall()
                destinatarios_info = [(r[0], r[1], r[2]) for r in rows]
            else:
                rows = conn.execute(
                    f"SELECT id, nombre, email FROM usuarios WHERE id IN ({','.join('?'*len(destinatarios))})",
                    destinatarios
                ).fetchall() if destinatarios else []
                destinatarios_info = [(r[0], r[1], r[2]) for r in rows]

            for dest_id, dest_nombre, dest_email in destinatarios_info:
                conn.execute(
                    """INSERT INTO notificaciones
                       (destinatario_id, tipo, titulo, mensaje, url)
                       VALUES (?,?,?,?,?)""",
                    (dest_id, tipo, titulo, mensaje, url)
                )
                # Email opcional — no bloquea si falla o no está configurado
                if dest_email:
                    url_base = os.environ.get("APP_URL", "http://localhost:5000").rstrip("/")
                    enlace   = f"{url_base}{url}" if url else url_base
                    html = (
                        f"<div style='font-family:Arial,sans-serif;max-width:520px;margin:0 auto;"
                        f"padding:24px;background:#0d0d0d;color:#e0e0e0;border-radius:12px;'>"
                        f"<h3 style='color:#c8f060;margin-bottom:4px;'>Axula</h3>"
                        f"<p style='color:#888;font-size:11px;margin-bottom:16px;'>"
                        f"C.E. Benito Juárez — Modalidad Artes</p>"
                        f"<p>Hola <strong>{dest_nombre or 'usuario'}</strong>,</p>"
                        f"<p style='margin:12px 0;'>{mensaje}</p>"
                        f"<div style='text-align:center;margin:20px 0;'>"
                        f"<a href='{enlace}' style='background:#c8f060;color:#000;padding:10px 24px;"
                        f"border-radius:8px;text-decoration:none;font-weight:700;font-size:13px;'>"
                        f"Ver en Axula</a></div>"
                        f"<hr style='border-color:#222;margin:16px 0;'>"
                        f"<p style='font-size:10px;color:#555;'>Axula · C.E. Benito Juárez</p>"
                        f"</div>"
                    )
                    _enviar_email_raw(dest_email, titulo, html)
    except Exception as _ex:
        logger.warning(f"[NOTIF] No se pudo crear notificación: {_ex}")


def _enviar_bienvenida(nombre, username, password, email, rol):
    """
    Envía email de bienvenida con credenciales al nuevo usuario.
    No falla si el email no está configurado — solo registra en log.
    """
    rol_label = ROLES_DISPONIBLES.get(rol, rol)
    url_base  = os.environ.get("APP_URL", "http://localhost:5000").rstrip("/")

    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:520px;margin:0 auto;padding:32px;
                background:#0d0d0d;color:#e0e0e0;border-radius:12px;">
      <h2 style="color:#c8f060;margin-bottom:4px;">Axula</h2>
      <p style="color:#888;font-size:12px;margin-bottom:24px;">C.E. Benito Juárez — Modalidad Artes</p>

      <p>Hola <strong style="color:#fff;">{nombre}</strong>,</p>
      <p style="margin:12px 0;">Tu cuenta en Axula ha sido creada. Aquí están tus credenciales de acceso:</p>

      <div style="background:#1a1a1a;border:1px solid #333;border-radius:8px;padding:16px;margin:16px 0;">
        <div style="margin-bottom:8px;">
          <span style="color:#888;font-size:12px;">Usuario</span><br>
          <strong style="font-size:16px;color:#c8f060;font-family:monospace;">{username}</strong>
        </div>
        <div>
          <span style="color:#888;font-size:12px;">Contraseña temporal</span><br>
          <strong style="font-size:16px;color:#c8f060;font-family:monospace;">{password}</strong>
        </div>
      </div>

      <p style="font-size:12px;color:#888;">Rol asignado: <strong style="color:#fff;">{rol_label}</strong></p>

      <div style="text-align:center;margin:24px 0;">
        <a href="{url_base}/login" style="background:#c8f060;color:#000;padding:12px 28px;
           border-radius:8px;text-decoration:none;font-weight:700;font-size:14px;">
          Iniciar sesión
        </a>
      </div>

      <p style="font-size:11px;color:#555;margin-top:20px;">
        Por seguridad, cambia tu contraseña en tu primera sesión.<br>
        Si no esperabas este correo, contáctanos.
      </p>
      <hr style="border-color:#222;margin:20px 0;">
      <p style="font-size:10px;color:#444;">Axula · C.E. Benito Juárez · República Dominicana</p>
    </div>
    """

    resend_key = os.environ.get("RESEND_API_KEY", "").strip()
    smtp_user  = os.environ.get("SMTP_USER", "").strip()
    smtp_pass  = os.environ.get("SMTP_PASS", "").strip()

    # Si no hay ningún método configurado, solo registrar
    if not resend_key and (not smtp_user or not smtp_pass):
        logger.info(f"[BIENVENIDA] Sin método email — credenciales para {username}: usr={username} pwd={password}")
        return

    # Intentar Resend primero
    if resend_key:
        try:
            import urllib.request as _req, json as _json
            from_addr = os.environ.get("RESEND_FROM", "Axula <onboarding@resend.dev>").strip()
            payload = _json.dumps({
                "from":    from_addr,
                "to":      [email],
                "subject": f"Axula — Bienvenido/a, {nombre}",
                "html":    html,
            }).encode()
            req = _req.Request(
                "https://api.resend.com/emails", data=payload,
                headers={"Authorization": f"Bearer {resend_key}", "Content-Type": "application/json"},
                method="POST"
            )
            with _req.urlopen(req, timeout=10) as resp:
                result = _json.loads(resp.read())
            if result.get("id"):
                logger.info(f"[BIENVENIDA] Email enviado a {email} (Resend id={result['id']})")
                return
        except Exception as ex:
            logger.error(f"[BIENVENIDA] Resend error: {ex}")

    # Fallback SMTP
    if smtp_user and smtp_pass:
        try:
            smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
            smtp_port = int(os.environ.get("SMTP_PORT", "587"))
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"Axula — Bienvenido/a, {nombre}"
            msg["From"]    = f"Axula <{smtp_user}>"
            msg["To"]      = email
            msg.attach(MIMEText(html, "html"))
            with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as s:
                s.ehlo(); s.starttls(); s.ehlo(); s.login(smtp_user, smtp_pass)
                s.sendmail(smtp_user, email, msg.as_string())
            logger.info(f"[BIENVENIDA] Email enviado a {email} (SMTP)")
        except Exception as ex:
            logger.error(f"[BIENVENIDA] SMTP error: {ex}")


def _send_recovery_email(to_email, token, nombre):
    """
    Envía email de recuperación.
    Método preferido: Resend API (RESEND_API_KEY en .env) — sin configuración SMTP.
    Fallback: SMTP (SMTP_USER + SMTP_PASS en .env).
    """
    reset_url = f"{request.host_url.rstrip('/')}/reset-password/{token}"

    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:500px;margin:0 auto;padding:32px;
                background:#0d0d0d;color:#e0e0e0;border-radius:12px;">
        <h2 style="color:#c8f060;margin-bottom:8px;">Axula</h2>
        <p style="color:#888;font-size:13px;margin-bottom:24px;">C.E. Benito Juárez — Modalidad Artes</p>
        <p>Hola <strong style="color:#fff;">{nombre}</strong>,</p>
        <p>Recibimos una solicitud para restablecer tu contraseña.</p>
        <div style="text-align:center;margin:32px 0;">
            <a href="{reset_url}" style="background:#c8f060;color:#000;padding:12px 28px;
               border-radius:8px;text-decoration:none;font-weight:700;font-size:15px;">
               Restablecer contraseña
            </a>
        </div>
        <p style="font-size:12px;color:#666;">
            Enlace válido por <strong>30 minutos</strong>.
            Si no solicitaste esto, ignora este correo.
        </p>
        <hr style="border-color:#222;margin:24px 0;">
        <p style="font-size:11px;color:#555;">Axula · C.E. Benito Juárez · República Dominicana</p>
    </div>
    """

    # ── Método 1: Resend API ─────────────────────────────────────────────────
    resend_key = os.environ.get("RESEND_API_KEY", "").strip()
    if resend_key:
        try:
            import urllib.request as _req, json as _json
            from_addr = os.environ.get("RESEND_FROM", "Axula <noreply@resend.dev>").strip()
            payload = _json.dumps({
                "from":    from_addr,
                "to":      [to_email],
                "subject": "Axula — Recuperar contraseña",
                "html":    html,
            }).encode()
            req = _req.Request(
                "https://api.resend.com/emails",
                data=payload,
                headers={
                    "Authorization": f"Bearer {resend_key}",
                    "Content-Type":  "application/json",
                },
                method="POST"
            )
            with _req.urlopen(req, timeout=15) as resp:
                result = _json.loads(resp.read())
            if result.get("id"):
                return True, ""
            return False, f"Resend error: {result}"
        except Exception as e:
            logger.error(f"[Resend] Error: {e} — intentando SMTP...")

    # ── Método 2: SMTP ───────────────────────────────────────────────────────
    smtp_user = os.environ.get("SMTP_USER", "").strip()
    smtp_pass = os.environ.get("SMTP_PASS", "").strip()
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com").strip()
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))

    if not smtp_user or not smtp_pass:
        return False, (
            "No hay método de envío configurado. "
            "Opción A (recomendada): agrega RESEND_API_KEY en .env — "
            "obtén tu clave gratis en resend.com. "
            "Opción B: configura SMTP_USER y SMTP_PASS en .env."
        )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Axula — Recuperar contraseña"
    msg["From"]    = f"Axula BJ <{smtp_user}>"
    msg["To"]      = to_email
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
            server.ehlo(); server.starttls(); server.ehlo()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, to_email, msg.as_string())
        return True, ""
    except Exception as e1:
        try:
            with smtplib.SMTP_SSL(smtp_host, 465, timeout=15) as server:
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_user, to_email, msg.as_string())
            return True, ""
        except Exception as e2:
            return False, f"SMTP STARTTLS: {e1} | SSL: {e2}"


def _validar_email_usuario(email):
    """Valida que el email sea institucional si se provee."""
    if not email:
        return True, ""
    import re
    if not re.match(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', email):
        return False, "El correo no tiene un formato válido."
    dominio = email.split("@")[1].lower()
    if dominio not in DOMINIOS_INSTITUCIONALES:
        return False, f"Solo se permiten correos institucionales (@educacion.edu.do o @minerd.gob.do)."
    return True, ""


def limpiar_v(v):
    if v is None:
        return 0.0
    try:
        # Evitar importar pandas solo para isna
        import math
        if isinstance(v, float) and math.isnan(v):
            return 0.0
    except Exception:
        pass
    try:
        return round(float(str(v).replace('%', '').replace(',', '.').strip()), 1)
    except Exception:
        return 0.0


def calcular_proyeccion(actual, anterior):
    """Proyección optimista/pesimista basada en la tendencia entre períodos."""
    if anterior == 0:
        return actual
    tendencia = actual - anterior
    proyectado = actual + (tendencia * 1.2)
    return round(min(max(proyectado, 0), 100), 1)


def calcular_promedio_modulos(p_foto, p_lv, p_diseno):
    """
    Calcula el promedio real de los 3 módulos técnicos multimedia.
    Solo promedia los módulos que tienen datos (mayor a 0).
    """
    valores = [v for v in [p_foto, p_lv, p_diseno] if v > 0]
    if not valores:
        return 0.0
    return round(sum(valores) / len(valores), 1)


def analizar_perfil_maestro(d, historico=None):
    # Promedios principales — nombres exactos del Excel
    acad      = limpiar_v(d.get('Promedio_Academico', 0))
    cond      = limpiar_v(d.get('Promedio_Conductual', 0))
    emocional = limpiar_v(d.get('Promedio_Emocional', 0))
    auto      = limpiar_v(d.get('Autoestima', 0))

    # Módulos técnicos multimedia — nombres exactos del Excel
    p_foto  = limpiar_v(d.get('Promedio_Fotografia', 0))
    p_lv    = limpiar_v(d.get('Promedio_Lenguaje_Visual', 0))
    p_diseno= limpiar_v(d.get('Promedio_Diseño', 0))

    # Otros indicadores del Excel
    asistencia  = limpiar_v(d.get('Asistencia', 0))
    motivacion  = limpiar_v(d.get('Motivacion', 0))
    indice_riesgo = limpiar_v(d.get('Indice_Riesgo', 0))
    nivel_riesgo  = str(d.get('Nivel_Riesgo', '')).strip()

    # Promedio real de módulos técnicos
    prom_modulos = calcular_promedio_modulos(p_foto, p_lv, p_diseno)

    # Proyección basada en historial
    acad_anterior = historico['p_acad'] if historico else acad
    proyeccion = calcular_proyeccion(acad, acad_anterior)

    res = {
        "es_caso_silencioso": False,
        "nivel": "Estable",
        "color": "#28a745",
        "reporte": "",
        "proyeccion": proyeccion,
        "tendencia": "igual",
        "prom_modulos": prom_modulos
    }

    if proyeccion > acad:
        res["tendencia"] = "subiendo"
    elif proyeccion < acad:
        res["tendencia"] = "bajando"

    # Alerta por proyección
    if proyeccion < 70:
        res["nivel"] = "ALERTA DE REPROBACIÓN"
        res["color"] = "#fd7e14"
        modulo_bajo = ""
        if p_foto > 0 and p_foto < 70:
            modulo_bajo += "Fotografía"
        if p_lv > 0 and p_lv < 70:
            modulo_bajo += (", " if modulo_bajo else "") + "Lenguaje Visual"
        if p_diseno > 0 and p_diseno < 70:
            modulo_bajo += (", " if modulo_bajo else "") + "Diseño"
        detalle = f" Módulos críticos: {modulo_bajo}." if modulo_bajo else ""
        res["reporte"] = (
            f"PLANIFICACIÓN URGENTE: La tendencia indica un promedio final de {proyeccion}.{detalle} "
            "Se requiere intervención inmediata."
        )

    # Erick's Rule — alto rendimiento + bienestar emocional bajo
    if acad >= 80 and (auto < 70 or auto == 0):
        res["es_caso_silencioso"] = True
        res["nivel"] = "CASO SILENCIOSO"
        res["color"] = "#17a2b8"
        res["reporte"] = "Rendimiento alto con bienestar emocional crítico. Programar Entrevista de Bienestar."

    return res


def _is_api_request():
    """True si el request viene de fetch/AJAX (espera JSON), False si es navegador."""
    return (request.path.startswith("/api/") or
            "application/json" in request.headers.get("Accept", "") or
            request.headers.get("X-Requested-With") == "XMLHttpRequest")


def _features_para_clustering(conn):
    """Extrae features numéricas de estudiantes con datos suficientes."""
    rows = conn.execute("""
        SELECT id,
               COALESCE(p_acad,0)         as acad,
               COALESCE(p_cond,0)         as cond,
               COALESCE(p_auto,0)         as auto_e,
               COALESCE(p_emocional,0)    as emoc,
               COALESCE(motivacion,0)     as motiv,
               COALESCE(apoyo_familiar,0) as apoyo,
               COALESCE(indice_riesgo,0)  as riesgo,
               COALESCE(interrupciones,0) as interr,
               COALESCE(conflictos,0)     as conflic,
               COALESCE(falta_respeto,0)  as faltaR,
               COALESCE(distraccion,0)    as distr,
               COALESCE(prom_modulos,0)   as modulos
        FROM estudiantes
        WHERE (p_acad > 0 OR p_cond > 0 OR prom_modulos > 0
               OR motivacion > 0 OR indice_riesgo > 0)
    """).fetchall()
    return rows


def _buscar_estudiante_bd(conn, nombre, apellido, filtro_grado="", filtro_mencion=""):
    """
    Busca un estudiante por nombre/apellido con normalización unicode.
    Cuatro intentos en cascada: exacto → solo nombre → sin filtro grado → fuzzy.
    Retorna sqlite3.Row o None.
    NOTA: Solo selecciona columnas que siempre existen (sin cedula por compatibilidad).
    """
    import unicodedata

    def norm(s):
        if not s: return ""
        s = str(s).lower().strip()
        return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode("ascii")

    # Registrar función norm en esta conexión
    try:
        conn.create_function("norm", 1, norm)
    except Exception:
        pass

    nom1 = norm(nombre.split()[0] if nombre else "")
    ape1 = norm(apellido.split()[0] if apellido else "")

    # Detectar columnas disponibles (BD nueva puede no tener cedula aún)
    cols_disponibles = {row[1] for row in conn.execute("PRAGMA table_info(estudiantes)").fetchall()}
    safe_cols = "id, nombre, apellido, grado, curso"
    if "cedula" in cols_disponibles:
        safe_cols = "id, cedula, nombre, apellido, grado, curso"

    extra_cond   = ""
    extra_params = []
    if filtro_grado:
        extra_cond   += " AND upper(grado) LIKE upper(?)"
        extra_params.append(f"%{filtro_grado}%")
    if filtro_mencion:
        extra_cond   += " AND upper(curso) LIKE upper(?)"
        extra_params.append(f"%{filtro_mencion}%")

    # Intento 1: nombre + apellido + filtros
    est = conn.execute(
        f"SELECT {safe_cols} FROM estudiantes "
        f"WHERE norm(nombre) LIKE ? AND norm(apellido) LIKE ? {extra_cond} LIMIT 1",
        [f"%{nom1}%", f"%{ape1}%"] + extra_params
    ).fetchone()

    # Intento 2: solo nombre + filtros
    if not est and nom1:
        est = conn.execute(
            f"SELECT {safe_cols} FROM estudiantes "
            f"WHERE norm(nombre) LIKE ? {extra_cond} LIMIT 1",
            [f"%{nom1}%"] + extra_params
        ).fetchone()

    # Intento 3: nombre + apellido sin filtros
    if not est and ape1:
        est = conn.execute(
            f"SELECT {safe_cols} FROM estudiantes "
            "WHERE norm(nombre) LIKE ? AND norm(apellido) LIKE ? LIMIT 1",
            [f"%{nom1}%", f"%{ape1}%"]
        ).fetchone()

    # Intento 4: fuzzy con fuzzywuzzy
    if not est and nom1:
        try:
            from fuzzywuzzy import fuzz
            candidatos = conn.execute(
                f"SELECT {safe_cols} FROM estudiantes LIMIT 500"
            ).fetchall()
            full_buscado = f"{nom1} {ape1}".strip()
            mejor = None
            mejor_score = 0
            for c in candidatos:
                full_c = norm(f"{c['nombre']} {c['apellido']}")
                score = fuzz.token_sort_ratio(full_buscado, full_c)
                if score > mejor_score:
                    mejor_score = score
                    mejor = c
            if mejor_score >= 82:
                est = mejor
        except Exception:
            pass

    return est


# ══════════════════════════════════════════════════════════════════════════════
# CARGA DIRECTA — Registro de Calificaciones Oficial (formato MINERD)
# Lee múltiples hojas, detecta profesor, carga notas+asistencia
# ══════════════════════════════════════════════════════════════════════════════


def _get_profesor():
    """Retorna dict del usuario profesor autenticado o None."""
    uid = session.get("user_id")
    if not uid:
        return None
    try:
        with sqlite3.connect(DATABASE, timeout=10) as conn:
            conn.row_factory = sqlite3.Row
            u = conn.execute(
                "SELECT * FROM usuarios WHERE id=? AND activo=1", (uid,)
            ).fetchone()
        if not u:
            logger.info(f"[_get_profesor] uid={uid} not found or inactive in DB")
        return dict(u) if u else None
    except Exception as ex:
        logger.error(f"[_get_profesor] Error: {ex}")
        return None


def _resolver_alcance_profesor(profesor):
    """
    Resuelve el conjunto real de grados y menciones que cubre un profesor
    según las reglas del C.E. Benito Juárez:

    - Profesor de materia TÉCNICA (tipo_docencia='tecnica'):
        Cubre todos los grados de SU ciclo para SU(S) mención(es).
        Ej: prof. Teatro → 4to,5to,6to en mención TEATRO.

    - Profesor de materia BÁSICA/ACADÉMICA (tipo_docencia='basica'):
        Cubre todos los grados de su ciclo en TODAS las menciones.
        Ej: prof. Matemática segundo ciclo → 4to,5to,6to × MULTIMEDIA,TEATRO,MÚSICA,ARTES VISUALES,DANZA

    - Profesor de PRIMER CICLO (ciclo='primer_ciclo'):
        Cubre 1ro,2do,3ro en todas las secciones (mención irrelevante).

    - Tipo 'ambas': cubre como básica (todas las menciones de su ciclo).

    Retorna dict con:
      grados   : list[str]  — ej. ['4to','5to','6to']
      menciones: list[str]  — ej. ['MULTIMEDIA','TEATRO'] o [] (primer ciclo)
      filtro_mencion: bool  — si True hay que filtrar por mención al buscar estudiantes
    """
    ciclo        = (profesor.get("ciclo") or "").strip().lower()
    tipo_doc     = (profesor.get("tipo_docencia") or "basica").strip().lower()
    grado_raw    = (profesor.get("grado") or "").strip()
    mencion_raw  = (profesor.get("mencion") or "").strip().upper()

    # ── Grados según ciclo ───────────────────────────────────────────
    if ciclo == "primer_ciclo":
        grados = ["1ro", "2do", "3ro"]
    elif ciclo == "segundo_ciclo":
        grados = ["4to", "5to", "6to"]
    else:
        # Inferir del campo grado si no hay ciclo explícito
        grados_raw = [g.strip() for g in grado_raw.split(",") if g.strip()]
        if grados_raw:
            primer = {"1ro","2do","3ro","1ero","2do","3er"}
            segundo = {"4to","5to","6to"}
            if any(g.lower() in primer for g in grados_raw):
                grados = ["1ro","2do","3ro"]
            elif any(g.lower() in segundo for g in grados_raw):
                grados = ["4to","5to","6to"]
            else:
                grados = grados_raw
        else:
            grados = ["4to","5to","6to"]  # fallback segundo ciclo

    # ── Menciones según tipo de docencia ────────────────────────────
    MENCIONES_2DO = ["MULTIMEDIA","TEATRO","MÚSICA","ARTES VISUALES","DANZA"]
    if ciclo == "primer_ciclo":
        menciones       = []
        filtro_mencion  = False
    elif tipo_doc == "tecnica":
        # Solo las menciones asignadas al prof
        menciones = [m.strip().upper() for m in mencion_raw.split(",") if m.strip()]
        if not menciones:
            menciones = ["MULTIMEDIA"]  # fallback
        filtro_mencion = True
    else:
        # basica o ambas → todas las menciones del segundo ciclo
        menciones      = MENCIONES_2DO
        filtro_mencion = False   # no filtrar por mención en la query

    return {"grados": grados, "menciones": menciones, "filtro_mencion": filtro_mencion}


def _validar_materia_profesor(nombre_materia, nombre_curso, profesor):
    """
    Valida si una materia/curso corresponde al perfil asignado del profesor.
    Con la nueva lógica multi-grado, acepta cualquier grado del ciclo del profesor.
    Retorna (ok: bool, mensaje: str)
    """
    if not profesor or _normalizar_rol(profesor.get("rol", "")) in ROLES_COORD:
        return True, ""

    alcance      = _resolver_alcance_profesor(profesor)
    grados       = [g.lower() for g in alcance["grados"]]
    menciones    = [m.lower() for m in alcance["menciones"]]
    prof_asigs   = [a.strip().lower() for a in (profesor.get("asignaturas") or "").split(",") if a.strip()]
    curso_lower  = (nombre_curso or "").lower()
    materia_lower = (nombre_materia or "").lower()

    # Verificar grado — cualquiera de los grados del alcance
    if grados and not any(g in curso_lower for g in grados):
        return False, (
            f"Este archivo no corresponde a ningún grado de tu ciclo asignado "
            f"({', '.join(g.upper() for g in grados)}). "
            f"El archivo indica el curso '{nombre_curso}'."
        )

    # Verificar mención — solo si el profesor es de materia técnica
    if alcance["filtro_mencion"] and menciones:
        if not any(m in curso_lower for m in menciones):
            return False, (
                f"La mención del archivo ('{nombre_curso}') no corresponde a tu mención asignada "
                f"({', '.join(m.upper() for m in menciones)})."
            )

    # Verificar materia
    if prof_asigs:
        match = any(asig in materia_lower or materia_lower in asig for asig in prof_asigs)
        if not match:
            return False, (
                f"La materia '{nombre_materia}' no está en tu lista de asignaturas "
                f"({profesor.get('asignaturas')}). Contacta al coordinador si hay un error."
            )

    return True, ""


def _notificar_psicologa(conn, estudiante_id, origen_tipo, origen_id, titulo, cuerpo):
    """
    Envía una notificación a la psicóloga del ciclo correspondiente al estudiante.
    Si no hay psicóloga asignada, notifica al coordinador del ciclo.
    Siempre inserta en la tabla notificaciones.
    """
    # Determinar ciclo del estudiante
    est = conn.execute(
        "SELECT ciclo, grado FROM estudiantes WHERE id=?", (estudiante_id,)
    ).fetchone()
    ciclo = (est["ciclo"] if est else None) or "segundo_ciclo"

    # Buscar psicóloga del ciclo
    rol_psico = "psicologa_primer_ciclo" if ciclo == "primer_ciclo" else "psicologa_segundo_ciclo"
    rol_coord = "coordinador_primer_ciclo" if ciclo == "primer_ciclo" else "coordinador_segundo_ciclo"

    destinatarios = conn.execute(
        "SELECT id, nombre, email FROM usuarios WHERE rol IN (?,?,?) AND activo=1",
        (rol_psico, rol_coord, "coordinador_general")
    ).fetchall()

    for dest in destinatarios:
        conn.execute("""
            INSERT INTO notificaciones
                (destinatario_id, origen_tipo, origen_id, estudiante_id, titulo, cuerpo)
            VALUES (?,?,?,?,?,?)
        """, (dest["id"], origen_tipo, origen_id, estudiante_id, titulo, cuerpo))
        # Email opcional — no bloquea
        if dest["email"]:
            url_base = os.environ.get("APP_URL", "http://localhost:5000").rstrip("/")
            html = (
                f"<div style='font-family:Arial,sans-serif;max-width:520px;margin:0 auto;"
                f"padding:24px;background:#0d0d0d;color:#e0e0e0;border-radius:12px;'>"
                f"<h3 style='color:#c8f060;margin:0 0 4px;'>Axula</h3>"
                f"<p style='color:#888;font-size:11px;margin:0 0 16px;'>"
                f"C.E. Benito Juárez — Modalidad Artes</p>"
                f"<p>Hola <strong>{dest['nombre'] or 'usuario'}</strong>,</p>"
                f"<p style='margin:12px 0;background:#1a1a1a;padding:12px;border-radius:8px;"
                f"border-left:3px solid #c8f060;'>{cuerpo}</p>"
                f"<div style='text-align:center;margin:20px 0;'>"
                f"<a href='{url_base}/perfil/{estudiante_id}' style='background:#c8f060;color:#000;"
                f"padding:10px 24px;border-radius:8px;text-decoration:none;font-weight:700;"
                f"font-size:13px;'>Ver expediente</a></div>"
                f"<hr style='border-color:#222;margin:16px 0;'>"
                f"<p style='font-size:10px;color:#555;'>Axula · C.E. Benito Juárez</p>"
                f"</div>"
            )
            _enviar_email_raw(dest["email"], titulo, html)


def _verificar_ausencias_semana(conn, estudiante_id, fecha_str):
    """
    Verifica si un estudiante acumuló 3+ ausencias en la semana actual.
    Si es así y no se ha enviado alerta para esa semana, crea la notificación
    y registra en ausencias_semanales.
    """
    from datetime import datetime, timedelta
    try:
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d")
    except Exception:
        return

    # Calcular semana ISO (ej: "2026-W12")
    year, week, _ = fecha.isocalendar()
    semana_iso = f"{year}-W{week:02d}"

    # Inicio y fin de la semana
    inicio_semana = fecha - timedelta(days=fecha.weekday())
    fin_semana    = inicio_semana + timedelta(days=6)
    ini_str = inicio_semana.strftime("%Y-%m-%d")
    fin_str = fin_semana.strftime("%Y-%m-%d")

    # Contar ausencias en la semana (ausente + tardanza cuenta como 0.5)
    row = conn.execute("""
        SELECT
            SUM(CASE WHEN estado IN ('ausente','A') THEN 1 ELSE 0 END) as ausentes,
            SUM(CASE WHEN estado IN ('tardanza','T') THEN 0.5 ELSE 0 END) as tardanzas,
            GROUP_CONCAT(DISTINCT materia) as materias
        FROM asistencia
        WHERE estudiante_id=? AND fecha BETWEEN ? AND ?
    """, (estudiante_id, ini_str, fin_str)).fetchone()

    if not row:
        return

    total = (row["ausentes"] or 0) + (row["tardanzas"] or 0)

    # Verificar si ya existe registro para esta semana
    existente = conn.execute(
        "SELECT id, alerta_enviada, total_ausencias FROM ausencias_semanales WHERE estudiante_id=? AND semana=?",
        (estudiante_id, semana_iso)
    ).fetchone()

    # Actualizar o insertar el registro semanal
    if existente:
        conn.execute(
            "UPDATE ausencias_semanales SET total_ausencias=?, materias=?, actualizado_en=datetime('now') WHERE id=?",
            (total, row["materias"] or "", existente["id"])
        )
    else:
        conn.execute(
            "INSERT INTO ausencias_semanales (estudiante_id, semana, total_ausencias, materias) VALUES (?,?,?,?)",
            (estudiante_id, semana_iso, total, row["materias"] or "")
        )

    # Si tiene 3+ ausencias Y no se ha enviado alerta esta semana → alertar
    ya_alertado = existente and existente["alerta_enviada"]
    if total >= 3 and not ya_alertado:
        est = conn.execute(
            "SELECT nombre, apellido, grado, curso FROM estudiantes WHERE id=?",
            (estudiante_id,)
        ).fetchone()
        nombre_est = f"{est['nombre']} {est['apellido']}" if est else f"Estudiante #{estudiante_id}"
        grado_est  = f"{est['grado'] or ''} {est['curso'] or ''}".strip() if est else ""

        titulo = f"⚠️ Alerta de Asistencia — {nombre_est}"
        cuerpo = (
            f"{nombre_est} ({grado_est}) acumuló {int(total)} ausencia(s)/tardanza(s) "
            f"en la semana del {ini_str} al {fin_str}. "
            f"Materias afectadas: {row['materias'] or 'varias'}."
        )
        _notificar_psicologa(conn, estudiante_id, "asistencia", None, titulo, cuerpo)

        # Marcar alerta como enviada
        conn.execute(
            "UPDATE ausencias_semanales SET alerta_enviada=1 WHERE estudiante_id=? AND semana=?",
            (estudiante_id, semana_iso)
        )

        # Crear caso automáticamente si no existe uno abierto de asistencia esta semana
        caso_abierto = conn.execute("""
            SELECT id FROM casos
            WHERE estudiante_id=? AND tipo='asistencia' AND estado NOT IN ('Resuelto','Cerrado')
        """, (estudiante_id,)).fetchone()

        if not caso_abierto:
            conn.execute("""
                INSERT INTO casos
                    (estudiante_id, abierto_por, tipo, titulo, descripcion, origen_tipo)
                VALUES (?,1,'asistencia',?,?,'asistencia')
            """, (
                estudiante_id,
                f"Alerta automática — Ausencias semana {semana_iso}",
                cuerpo
            ))


def _notificar_directora_coordinador(conn, estudiante_id, origen_tipo, origen_id, titulo, cuerpo):
    """
    Notifica a directora y coordinador del ciclo (NO a psicóloga).
    Usado para reportes pedagógicos del profesor.
    """
    est = conn.execute(
        "SELECT ciclo FROM estudiantes WHERE id=?", (estudiante_id,)
    ).fetchone()
    ciclo = (est["ciclo"] if est else None) or "segundo_ciclo"
    rol_coord = "coordinador_primer_ciclo" if ciclo == "primer_ciclo" else "coordinador_segundo_ciclo"

    destinatarios = conn.execute(
        "SELECT id, nombre, email FROM usuarios WHERE rol IN (?,?,?) AND activo=1",
        (rol_coord, "coordinador_general", "directora")
    ).fetchall()

    for dest in destinatarios:
        conn.execute("""
            INSERT INTO notificaciones
                (destinatario_id, origen_tipo, origen_id, estudiante_id, titulo, cuerpo)
            VALUES (?,?,?,?,?,?)
        """, (dest["id"], origen_tipo, origen_id, estudiante_id, titulo, cuerpo))
        if dest["email"]:
            url_base = os.environ.get("APP_URL", "http://localhost:5000").rstrip("/")
            html = (
                f"<div style='font-family:Arial,sans-serif;max-width:520px;margin:0 auto;"
                f"padding:24px;background:#0d0d0d;color:#e0e0e0;border-radius:12px;'>"
                f"<h3 style='color:#378ADD;margin:0 0 4px;'>Axula</h3>"
                f"<p style='color:#888;font-size:11px;margin:0 0 16px;'>"
                f"C.E. Benito Juárez — Modalidad Artes</p>"
                f"<p>Hola <strong>{dest['nombre'] or 'usuario'}</strong>,</p>"
                f"<p style='margin:12px 0;background:#1a1a1a;padding:12px;border-radius:8px;"
                f"border-left:3px solid #378ADD;'>{cuerpo}</p>"
                f"<div style='text-align:center;margin:20px 0;'>"
                f"<a href='{url_base}/perfil/{estudiante_id}' style='background:#378ADD;color:#fff;"
                f"padding:10px 24px;border-radius:8px;text-decoration:none;font-weight:700;"
                f"font-size:13px;'>Ver expediente</a></div>"
                f"<hr style='border-color:#222;margin:16px 0;'>"
                f"<p style='font-size:10px;color:#555;'>Axula · C.E. Benito Juárez</p>"
                f"</div>"
            )
            _enviar_email_raw(dest["email"], titulo, html)


def _notificar_reporte_nuevo(conn, estudiante_id, reporte_id, tipo_reporte, severidad, titulo_rep, reportado_por, canal="pedagogico"):
    """
    Enruta notificaciones según el canal del reporte:
    - 'pedagogico' → directora + coordinador (el profesor maneja en su aula)
    - 'conductual'  → directora + coordinador + psicóloga (requiere orientación)
    """
    est = conn.execute(
        "SELECT nombre, apellido FROM estudiantes WHERE id=?", (estudiante_id,)
    ).fetchone()
    nombre_est = f"{est['nombre']} {est['apellido']}" if est else f"Estudiante #{estudiante_id}"

    if canal == "conductual":
        titulo = f"🚨 Reporte conductual — {nombre_est}"
        cuerpo = (
            f"El/la docente {reportado_por} registró un reporte de conducta "
            f"({tipo_reporte}, severidad {severidad}): \"{titulo_rep or 'Sin título'}\". "
            f"Requiere seguimiento de orientación."
        )
        _notificar_psicologa(conn, estudiante_id, "reporte", reporte_id, titulo, cuerpo)
    else:
        titulo = f"📋 Observación pedagógica — {nombre_est}"
        cuerpo = (
            f"El/la docente {reportado_por} registró una observación pedagógica "
            f"({tipo_reporte}, severidad {severidad}): \"{titulo_rep or 'Sin título'}\"."
        )
        _notificar_directora_coordinador(conn, estudiante_id, "reporte", reporte_id, titulo, cuerpo)


def _anio_escolar_actual():
    """Detecta automáticamente el año escolar según la fecha.
    El año escolar dominicano comienza en agosto.
    Si estamos en agosto-diciembre → 'YYYY-(YYY+1)'
    Si estamos en enero-julio  → '(YYYY-1)-YYYY'
    """
    from datetime import date
    hoy = date.today()
    if hoy.month >= 8:
        return f"{hoy.year}-{hoy.year + 1}"
    else:
        return f"{hoy.year - 1}-{hoy.year}"


def _periodo_actual():
    """Detecta el período activo por fecha.
    P1: agosto–octubre
    P2: noviembre–enero
    P3: febrero–abril
    P4: mayo–julio
    """
    from datetime import date
    m = date.today().month
    if m in (8, 9, 10):     return "P1"
    if m in (11, 12, 1):    return "P2"
    if m in (2, 3, 4):      return "P3"
    return "P4"  # 5, 6, 7


def _nota_estado(nota):
    """
    Clasifica la nota según Ordenanza 04-2023 MINERD (Art.28).
    D  89-100 Destacado
    S  80-88  Satisfactorio
    B  70-79  Básico         ← mínimo aprobatorio
    EP 60-69  En proceso     → Recuperación Pedagógica obligatoria
    I  0-59   Insuficiente   → Evaluación Completiva / Extraordinaria
    """
    if nota is None: return "sin_nota"
    if nota >= 89:   return "destacado"
    if nota >= 80:   return "satisfactorio"
    if nota >= 70:   return "basico"
    if nota >= 60:   return "en_proceso"
    return "insuficiente"


def _nota_requiere_recuperacion(nota):
    """True si la nota es menor que 70 — requiere Recuperación Pedagógica."""
    return nota is not None and nota < 70


def _calcular_nota_final_con_recuperacion(nota_base, recup):
    """
    Calcula la nota final ajustada tras recuperación pedagógica.
    Ord.04-2023: la evaluación completiva vale 50%, nota_final vale 50%.
    Para la recuperación pedagógica (primer nivel) el docente puede mejorar
    la nota directamente a partir de actividades complementarias.
    Si se ingresa nota_completiva: nota_final_ajustada = (nota_base*0.5 + nota_completiva*0.5).
    """
    if recup is None:
        return nota_base
    # Completiva: promedio ponderado 50/50
    return round(nota_base * 0.5 + recup * 0.5, 1)


def _color_nota(nota):
    if nota is None: return "#555"
    if nota >= 89:   return "#4dffb4"
    if nota >= 80:   return "#60b8f0"
    if nota >= 70:   return "#c8f060"
    if nota >= 60:   return "#f7b731"
    return "#ff4d4d"


# ═══════════════════════════════════════════════════════════════════════════════
#  ENDPOINTS CALIFICACIONES
# ═══════════════════════════════════════════════════════════════════════════════


def _semana_iso(fecha_str):
    """Devuelve la semana ISO de una fecha string 'YYYY-MM-DD'."""
    from datetime import datetime
    try:
        d = datetime.strptime(fecha_str, "%Y-%m-%d")
        return f"{d.isocalendar()[0]}-W{d.isocalendar()[1]:02d}"
    except Exception:
        from datetime import date
        return date.today().strftime("%G-W%V")


def _psicologa_del_ciclo(conn, ciclo):
    """Devuelve el usuario psicóloga asignado al ciclo del estudiante."""
    rol = "psicologa_segundo_ciclo" if ciclo == "segundo_ciclo" else "psicologa_primer_ciclo"
    row = conn.execute(
        "SELECT id FROM usuarios WHERE rol=? AND activo=1 LIMIT 1", (rol,)
    ).fetchone()
    return row["id"] if row else None


def _crear_notificacion(conn, destinatario_id, origen_tipo, origen_id,
                        estudiante_id, titulo, cuerpo=""):
    """Inserta una notificación en la BD."""
    if not destinatario_id:
        return None
    conn.execute("""
        INSERT INTO notificaciones
            (destinatario_id, origen_tipo, origen_id, estudiante_id, titulo, cuerpo)
        VALUES (?,?,?,?,?,?)
    """, (destinatario_id, origen_tipo, origen_id, estudiante_id, titulo, cuerpo))
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def _registrar_ausencia_semanal(conn, estudiante_id, fecha, materia):
    """
    Acumula la ausencia semanal del estudiante.
    Si llega a 3 en la misma semana, genera alerta automática a la psicóloga.
    """
    semana = _semana_iso(fecha)

    # Obtener o crear registro semanal
    row = conn.execute(
        "SELECT * FROM ausencias_semanales WHERE estudiante_id=? AND semana=?",
        (estudiante_id, semana)
    ).fetchone()

    if row:
        import json as _j
        materias = _j.loads(row["materias"] or "{}")
        materias[materia] = materias.get(materia, 0) + 1
        total = row["total_ausencias"] + 1
        conn.execute("""
            UPDATE ausencias_semanales
               SET total_ausencias=?, materias=?, actualizado_en=datetime('now')
             WHERE estudiante_id=? AND semana=?
        """, (total, _j.dumps(materias, ensure_ascii=False), estudiante_id, semana))

        # ── ALERTA: 3+ ausencias en la semana ───────────────────────────────
        if total >= 3 and not row["alerta_enviada"]:
            est = conn.execute(
                "SELECT nombre, apellido, ciclo FROM estudiantes WHERE id=?",
                (estudiante_id,)
            ).fetchone()
            if est:
                ciclo = est["ciclo"] or "segundo_ciclo"
                psic_id = _psicologa_del_ciclo(conn, ciclo)
                nombre_est = f"{est['nombre']} {est['apellido']}".strip()

                titulo_alerta = f"⚠ Alerta de Asistencia — {nombre_est}"
                cuerpo_alerta = (
                    f"El/la estudiante {nombre_est} acumula {total} ausencias "
                    f"durante la semana {semana}. "
                    f"Materias afectadas: {', '.join(f'{m}({n})' for m,n in materias.items())}. "
                    f"Se requiere seguimiento."
                )

                notif_id = _crear_notificacion(
                    conn, psic_id, "asistencia", None,
                    estudiante_id, titulo_alerta, cuerpo_alerta
                )

                # Crear caso automático si no hay uno abierto de asistencia esta semana
                caso_existente = conn.execute("""
                    SELECT id FROM casos
                    WHERE estudiante_id=? AND tipo='asistencia'
                      AND estado IN ('Abierto','En seguimiento')
                      AND creado_en >= date('now','-7 days')
                """, (estudiante_id,)).fetchone()

                if not caso_existente and psic_id:
                    conn.execute("""
                        INSERT INTO casos
                            (estudiante_id, abierto_por, tipo, titulo,
                             descripcion, origen_tipo, nivel_escala)
                        VALUES (?,?,?,?,?,?,1)
                    """, (
                        estudiante_id, psic_id, "asistencia",
                        f"Alerta de asistencia — semana {semana}",
                        cuerpo_alerta, "asistencia"
                    ))

                conn.execute("""
                    UPDATE ausencias_semanales
                       SET alerta_enviada=1, alerta_id=?
                     WHERE estudiante_id=? AND semana=?
                """, (notif_id, estudiante_id, semana))
    else:
        import json as _j
        conn.execute("""
            INSERT INTO ausencias_semanales (estudiante_id, semana, total_ausencias, materias)
            VALUES (?,?,1,?)
        """, (estudiante_id, semana, _j.dumps({materia: 1}, ensure_ascii=False)))


def _alerta_nuevo_reporte(conn, reporte_id, estudiante_id, tipo_reporte,
                          titulo_reporte, reportado_por):
    """Genera notificación a la psicóloga cuando se crea un reporte."""
    est = conn.execute(
        "SELECT nombre, apellido, ciclo FROM estudiantes WHERE id=?",
        (estudiante_id,)
    ).fetchone()
    if not est:
        return

    ciclo    = est["ciclo"] or "segundo_ciclo"
    psic_id  = _psicologa_del_ciclo(conn, ciclo)
    nombre   = f"{est['nombre']} {est['apellido']}".strip()
    emoji    = {"conducta": "🔴", "psicologico": "🟡", "academico": "🔵"}.get(tipo_reporte, "📋")

    _crear_notificacion(
        conn, psic_id, "reporte", reporte_id, estudiante_id,
        f"{emoji} Nuevo reporte — {nombre}",
        f"Se registró un reporte de tipo '{tipo_reporte}' para {nombre}. "
        f"Reportado por: {reportado_por}. Título: {titulo_reporte}."
    )


# ── NOTIFICACIONES ────────────────────────────────────────────────────────────


def _hook_nuevo_reporte(conn, reporte_id, estudiante_id, tipo, titulo, reportado_por):
    """Hook que se llama al crear un reporte para disparar notificación."""
    _alerta_nuevo_reporte(conn, reporte_id, estudiante_id, tipo, titulo, reportado_por)


# ── HOOK: interceptar registros de asistencia para contar ausencias ──────────


def _hook_asistencia_ausente(conn, estudiante_id, fecha, materia):
    """Hook que se llama cuando se registra una ausencia."""
    _registrar_ausencia_semanal(conn, estudiante_id, fecha, materia)


def _get_hijos(padre_id):
    """Devuelve lista de estudiantes vinculados al padre."""
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """SELECT e.*, v.parentesco
               FROM vinculos_padre_estudiante v
               JOIN estudiantes e ON e.id = v.estudiante_id
               WHERE v.padre_id = ? AND e.condicion != 'INACTIVO'
               ORDER BY e.apellido, e.nombre""",
            (padre_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def _render_perfil_staff(uid, viewer):
    """Renderiza el perfil de cualquier miembro del personal con su timeline."""
    try:
      with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        staff = conn.execute("SELECT * FROM usuarios WHERE id=?", (uid,)).fetchone()
        if not staff:
            return redirect("/")
        staff = dict(staff)

        rol_n = _normalizar_rol(staff["rol"])
        uid   = staff["id"]
        stats = {}

        # ── Estadísticas según el rol ─────────────────────────────────────
        if rol_n in ROLES_PSICOLOGA:
            ciclo = _ciclo_del_rol(rol_n)
            stats["casos_abiertos"] = conn.execute(
                "SELECT COUNT(*) FROM casos c JOIN estudiantes e ON e.id=c.estudiante_id "
                "WHERE c.estado NOT IN ('Resuelto','Cerrado') AND e.ciclo=?", (ciclo,)
            ).fetchone()[0]
            stats["acuerdos"] = conn.execute(
                "SELECT COUNT(*) FROM acuerdos_compromiso WHERE generado_por=?", (uid,)
            ).fetchone()[0]
            stats["notif_pendientes"] = conn.execute(
                "SELECT COUNT(*) FROM notificaciones WHERE destinatario_id=? AND leida=0", (uid,)
            ).fetchone()[0]
            stats["casos_cerrados"] = conn.execute(
                "SELECT COUNT(*) FROM casos WHERE estado IN ('Resuelto','Cerrado')"
            ).fetchone()[0]

        elif rol_n in ROLES_COORD or rol_n in ROLES_SUPER:
            try:
                stats["total_estudiantes"] = conn.execute(
                    "SELECT COUNT(*) FROM estudiantes"
                ).fetchone()[0]
            except Exception: stats["total_estudiantes"] = 0
            try:
                stats["casos_abiertos"] = conn.execute(
                    "SELECT COUNT(*) FROM casos WHERE estado NOT IN ('Resuelto','Cerrado')"
                ).fetchone()[0]
            except Exception: stats["casos_abiertos"] = 0
            try:
                stats["reportes_mes"] = conn.execute(
                    "SELECT COUNT(*) FROM reportes WHERE fecha >= date('now','-30 days')"
                ).fetchone()[0]
            except Exception: stats["reportes_mes"] = 0
            try:
                stats["usuarios_activos"] = conn.execute(
                    "SELECT COUNT(*) FROM usuarios WHERE activo=1"
                ).fetchone()[0]
            except Exception: stats["usuarios_activos"] = 0

        elif rol_n == "profesor":
            grado_prof = staff.get("grado", "")
            try:
                if grado_prof:
                    grados = [g.strip().upper() for g in grado_prof.split(",") if g.strip()]
                    placeholders = ",".join("?" * len(grados))
                    stats["mis_estudiantes"] = conn.execute(
                        f"SELECT COUNT(*) FROM estudiantes WHERE upper(grado) IN ({placeholders})",
                        grados
                    ).fetchone()[0]
                else:
                    stats["mis_estudiantes"] = 0
            except Exception: stats["mis_estudiantes"] = 0
            try:
                stats["planificaciones"] = conn.execute(
                    "SELECT COUNT(*) FROM historial_planificaciones WHERE profesor_id=?", (uid,)
                ).fetchone()[0]
            except Exception: stats["planificaciones"] = 0
            try:
                stats["reportes_creados"] = conn.execute(
                    "SELECT COUNT(*) FROM reportes WHERE reportado_por=?", (uid,)
                ).fetchone()[0]
            except Exception: stats["reportes_creados"] = 0
            try:
                stats["asistencias_registradas"] = conn.execute(
                    "SELECT COUNT(DISTINCT fecha||estudiante_id) FROM asistencia WHERE profesor_id=?", (uid,)
                ).fetchone()[0]
            except Exception: stats["asistencias_registradas"] = 0
        else:
            try:
                stats["estudiantes_total"] = conn.execute(
                    "SELECT COUNT(*) FROM estudiantes"
                ).fetchone()[0]
            except Exception: pass

        # ── TIMELINE UNIFICADO ────────────────────────────────────────────
        # Reúne toda la actividad del usuario de múltiples tablas
        timeline = []

        # Reportes creados por el usuario
        try:
            rows = conn.execute("""
                SELECT 'reporte' as tipo,
                       r.fecha as fecha,
                       '📋 Reporte ' || r.tipo || ' — ' || e.nombre || ' ' || e.apellido as desc,
                       r.severidad as extra,
                       e.id as ref_id,
                       '/perfil/' || e.id as url
                FROM reportes r
                JOIN estudiantes e ON e.id = r.estudiante_id
                WHERE r.reportado_por = ?
                ORDER BY r.fecha DESC LIMIT 30
            """, (uid,)).fetchall()
            timeline.extend([dict(r) for r in rows])
        except Exception: pass

        # Casos abiertos por el usuario
        try:
            rows = conn.execute("""
                SELECT 'caso' as tipo,
                       c.creado_en as fecha,
                       '🗂️ Caso ' || c.tipo || ': ' || c.titulo as desc,
                       c.estado as extra,
                       c.id as ref_id,
                       '/casos' as url
                FROM casos c
                WHERE c.abierto_por = ?
                ORDER BY c.creado_en DESC LIMIT 20
            """, (uid,)).fetchall()
            timeline.extend([dict(r) for r in rows])
        except Exception: pass

        # Acciones en casos (notas, citas, reuniones)
        try:
            rows = conn.execute("""
                SELECT 'caso_accion' as tipo,
                       a.fecha_accion as fecha,
                       '💬 ' || a.tipo_accion || ' en caso #' || a.caso_id || ': ' || substr(a.descripcion,1,60) as desc,
                       c.titulo as extra,
                       c.id as ref_id,
                       '/casos' as url
                FROM caso_acciones a
                JOIN casos c ON c.id = a.caso_id
                WHERE a.actor_id = ?
                ORDER BY a.fecha_accion DESC LIMIT 20
            """, (uid,)).fetchall()
            timeline.extend([dict(r) for r in rows])
        except Exception: pass

        # Acuerdos-Compromiso redactados
        try:
            rows = conn.execute("""
                SELECT 'acuerdo' as tipo,
                       ac.creado_en as fecha,
                       '📝 Acuerdo-Compromiso para ' || e.nombre || ' ' || e.apellido as desc,
                       'Acuerdo formal' as extra,
                       e.id as ref_id,
                       '/perfil/' || e.id as url
                FROM acuerdos_compromiso ac
                JOIN estudiantes e ON e.id = ac.estudiante_id
                WHERE ac.generado_por = ?
                ORDER BY ac.creado_en DESC LIMIT 15
            """, (uid,)).fetchall()
            timeline.extend([dict(r) for r in rows])
        except Exception: pass

        # Planificaciones guardadas (profesores)
        try:
            rows = conn.execute("""
                SELECT 'planificacion' as tipo,
                       hp.fecha as fecha,
                       '📚 Planificación: ' || COALESCE(hp.tema, hp.materia, 'Sin título') as desc,
                       hp.materia as extra,
                       hp.id as ref_id,
                       '/planificacion' as url
                FROM historial_planificaciones hp
                WHERE hp.profesor_id = ?
                ORDER BY hp.fecha DESC LIMIT 20
            """, (uid,)).fetchall()
            timeline.extend([dict(r) for r in rows])
        except Exception: pass

        # Notificaciones recibidas (para psicólogas)
        try:
            rows = conn.execute("""
                SELECT 'notificacion' as tipo,
                       n.creado_en as fecha,
                       '🔔 ' || n.titulo as desc,
                       CASE WHEN n.leida THEN 'Leída' ELSE 'Sin leer' END as extra,
                       n.id as ref_id,
                       '/casos' as url
                FROM notificaciones n
                WHERE n.destinatario_id = ?
                ORDER BY n.creado_en DESC LIMIT 20
            """, (uid,)).fetchall()
            timeline.extend([dict(r) for r in rows])
        except Exception: pass

        # Ordenar todo por fecha descendente y tomar los 50 más recientes
        def _fecha_key(item):
            return (item.get("fecha") or "1900-01-01")
        timeline.sort(key=_fecha_key, reverse=True)
        timeline = timeline[:50]

      es_propio = (viewer["id"] == uid)
      return render_template(
          "mi_perfil.html",
          staff       = staff,
          stats       = stats,
          timeline    = timeline,
          current_user= viewer,
          es_propio   = es_propio,
          es_vista_admin = not es_propio,
      )
    except Exception as _e:
        import traceback as _tb
        logger.error(f"Error en mi_perfil para uid={uid}: {_e}\n{_tb.format_exc()}")
        # Render a minimal fallback instead of redirecting to login
        return render_template(
            "mi_perfil.html",
            staff       = {"nombre": viewer.get("nombre",""), "username": viewer.get("username",""),
                           "rol": viewer.get("rol",""), "id": uid},
            stats       = {},
            timeline    = [],
            current_user= viewer,
            es_propio   = True,
            es_vista_admin = False,
            error_msg   = f"Error cargando el perfil: {str(_e)}"
        )


def _calcular_indice_conductual(conn, est_id):
    """
    Índice conductual compuesto — alimentado de todo el ecosistema:
      40%  Indicadores directos del profesor (puntualidad, participacion, tareas, rendimiento, comprension)
      20%  Indicadores negativos invertidos   (interrupciones, conflictos, desafia_autoridad, distraccion, falta_respeto)
      25%  Penalización por reportes formales de conducta / incidentes
      15%  Penalización por cuaderno anecdótico conductual
    Baja asistencia aplica descuento adicional.
    Si no hay indicadores directos, los pesos se redistribuyen entre reportes y cuaderno.
    """
    components = []

    # ── 1. Indicadores directos del profesor ────────────────────────────────
    try:
        row = conn.execute(
            "SELECT puntualidad, participacion, tareas, rendimiento, comprension,"
            "       interrupciones, conflictos, desafia_autoridad, distraccion, falta_respeto,"
            "       asistencia"
            " FROM estudiantes WHERE id=?", (est_id,)
        ).fetchone()
    except Exception:
        row = None

    asistencia_est = 0.0
    if row:
        pos_vals = [float(row[i] or 0) for i in range(5) if float(row[i] or 0) > 0]
        if pos_vals:
            components.append((sum(pos_vals) / len(pos_vals), 0.40))

        neg_vals = [float(row[i] or 0) for i in range(5, 10) if float(row[i] or 0) > 0]
        if neg_vals:
            avg_neg = sum(neg_vals) / len(neg_vals)
            components.append((max(0.0, 100.0 - avg_neg), 0.20))

        asistencia_est = float(row[10] or 0)

    # ── 2. Asistencia mensual real (datos de profesores, más autoritativa) ──
    try:
        rows_asist = conn.execute(
            "SELECT porcentaje FROM asistencia_mensual"
            " WHERE estudiante_id=? AND porcentaje IS NOT NULL AND porcentaje > 0",
            (est_id,)
        ).fetchall()
        if rows_asist:
            pcts = [float(r[0]) for r in rows_asist if r[0]]
            if pcts:
                asistencia_est = sum(pcts) / len(pcts)
    except Exception:
        pass

    # ── 3. Reportes formales de conducta / incidentes ───────────────────────
    DESC_RPT = {'alta': 30, 'grave': 30, 'media': 20, 'baja': 10}
    rpt_score = 100.0
    try:
        for r in conn.execute(
            "SELECT tipo, severidad FROM reportes"
            " WHERE estudiante_id=? AND tipo IN ('conducta','incidente_grave')",
            (est_id,)
        ).fetchall():
            tipo = (r[0] or '').lower()
            sev  = (r[1] or '').lower()
            rpt_score -= 40 if tipo == 'incidente_grave' else DESC_RPT.get(sev, 20)
    except Exception:
        pass
    components.append((max(0.0, rpt_score), 0.25))

    # ── 4. Cuaderno anecdótico conductual ───────────────────────────────────
    DESC_CA = {'conducta': 10, 'incidente': 15, 'disciplina': 10}
    cuad_score = 100.0
    try:
        for row_ca in conn.execute(
            "SELECT tipo FROM cuaderno_anecdotico"
            " WHERE estudiante_id=? AND lower(tipo) IN ('conducta','incidente','disciplina')",
            (est_id,)
        ).fetchall():
            cuad_score -= DESC_CA.get((row_ca[0] or '').lower(), 5)
    except Exception:
        pass
    components.append((max(0.0, cuad_score), 0.15))

    # ── Combinar con pesos normalizados ─────────────────────────────────────
    total_w = sum(w for _, w in components)
    score = sum(v * w for v, w in components) / total_w if components else 100.0

    # ── Penalización por baja asistencia ────────────────────────────────────
    if asistencia_est > 0:
        if asistencia_est < 70:
            score = max(0.0, score - 8)
        elif asistencia_est < 80:
            score = max(0.0, score - 4)

    return round(max(0.0, min(100.0, score)), 1)


def _calcular_bienestar_emocional(conn, est_id):
    """
    Bienestar emocional compuesto — alimentado de todo el ecosistema:
      50%  Indicadores emocionales directos (motivacion, estado_emocional, interes_futuro, apoyo_familiar, p_emocional)
      35%  Penalización por reportes psicológicos formales
      15%  Penalización por cuaderno anecdótico emocional / psicológico / familiar
    Si no hay indicadores directos, los pesos se redistribuyen entre reportes y cuaderno.
    """
    components = []

    # ── 1. Indicadores emocionales directos (psicóloga / tutor) ─────────────
    try:
        row = conn.execute(
            "SELECT motivacion, estado_emocional, interes_futuro, apoyo_familiar, p_emocional"
            " FROM estudiantes WHERE id=?", (est_id,)
        ).fetchone()
    except Exception:
        row = None

    if row:
        emoc_vals = [float(row[i] or 0) for i in range(5) if float(row[i] or 0) > 0]
        if emoc_vals:
            components.append((sum(emoc_vals) / len(emoc_vals), 0.50))

    # ── 2. Reportes psicológicos formales ───────────────────────────────────
    DESC_RPT = {'alta': 25, 'grave': 25, 'media': 15, 'baja': 8}
    rpt_score = 100.0
    try:
        for r in conn.execute(
            "SELECT severidad FROM reportes WHERE estudiante_id=? AND tipo='psicologico'",
            (est_id,)
        ).fetchall():
            sev = (r[0] or '').lower()
            rpt_score -= DESC_RPT.get(sev, 15)
    except Exception:
        pass
    components.append((max(0.0, rpt_score), 0.35))

    # ── 3. Cuaderno anecdótico emocional / psicológico / familiar ───────────
    DESC_CA = {'psicologico': 12, 'emocional': 10, 'familiar': 8}
    cuad_score = 100.0
    try:
        for row_ca in conn.execute(
            "SELECT tipo FROM cuaderno_anecdotico"
            " WHERE estudiante_id=? AND lower(tipo) IN ('psicologico','emocional','familiar')",
            (est_id,)
        ).fetchall():
            cuad_score -= DESC_CA.get((row_ca[0] or '').lower(), 5)
    except Exception:
        pass
    components.append((max(0.0, cuad_score), 0.15))

    # ── Combinar con pesos normalizados ─────────────────────────────────────
    total_w = sum(w for _, w in components)
    score = sum(v * w for v, w in components) / total_w if components else 100.0

    return round(max(0.0, min(100.0, score)), 1)


def _recalcular_indicadores(conn, est_id):
    for col in ['ind_conducta','ind_psico','ind_academico','ind_logros']:
        try:
            conn.execute('ALTER TABLE estudiantes ADD COLUMN ' + col + ' TEXT DEFAULT neutro')
        except Exception:
            pass

    def score_to_nivel(s):
        if s <= 60: return 'critico'
        if s <= 75: return 'alerta'
        if s <= 89: return 'observacion'
        return 'neutro'

    ind_conducta  = score_to_nivel(_calcular_indice_conductual(conn, est_id))
    ind_psico     = score_to_nivel(_calcular_bienestar_emocional(conn, est_id))

    reportes_acad = conn.execute("SELECT severidad FROM reportes WHERE estudiante_id=? AND tipo='academico'", (est_id,)).fetchall()
    if any(r[0] in ('Alta','Grave') for r in reportes_acad):   ind_academico = 'critico'
    elif any(r[0] == 'Media' for r in reportes_acad):          ind_academico = 'alerta'
    elif reportes_acad:                                         ind_academico = 'observacion'
    else:                                                       ind_academico = 'neutro'

    try:
        logros = conn.execute("SELECT COUNT(*) FROM logros WHERE estudiante_id=?", (est_id,)).fetchone()[0]
    except Exception:
        logros = 0
    ind_logros = 'destacado' if logros >= 3 else 'activo' if logros >= 1 else 'neutro'

    conn.execute("UPDATE estudiantes SET ind_conducta=?,ind_psico=?,ind_academico=?,ind_logros=? WHERE id=?",
                 (ind_conducta, ind_psico, ind_academico, ind_logros, est_id))


# ══════════════════════════════════════════════════════════════════════════════
#  EXPEDIENTE ESTUDIANTIL — Endpoints
# ══════════════════════════════════════════════════════════════════════════════


def _parse_ics_date(val):
    """Convierte DTSTART/DTEND de formato iCal a 'YYYY-MM-DD'."""
    val = str(val).strip().replace("Z", "")
    # Puede venir como YYYYMMDD o YYYYMMDDTHHmmss
    if "T" in val:
        val = val.split("T")[0]
    val = val.strip()
    if len(val) == 8:
        return f"{val[:4]}-{val[4:6]}-{val[6:8]}"
    return val


def _generar_ics(eventos):
    """
    Genera contenido de archivo .ics a partir de lista de eventos.
    eventos: lista de dicts con keys: fecha, titulo, descripcion
    """
    from datetime import datetime as _dt
    now = _dt.utcnow().strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Axula//C.E.Benito Juarez//ES",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Calendario C.E. Benito Juárez",
        "X-WR-TIMEZONE:America/Santo_Domingo",
    ]
    for ev in eventos:
        fecha_ics = ev["fecha"].replace("-", "")
        uid = f"{ev['fecha']}-{ev.get('tipo','evento')}@axula.bj"
        titulo    = (ev.get("descripcion") or ev.get("tipo", "Evento")).strip()
        lines += [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now}",
            f"DTSTART;VALUE=DATE:{fecha_ics}",
            f"DTEND;VALUE=DATE:{fecha_ics}",
            f"SUMMARY:{titulo}",
            f"DESCRIPTION:{ev.get('tipo','').upper()} — Calendario C.E. Benito Juárez",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


# ══════════════════════════════════════════════════════════════════════════════
#  CONFIGURACIÓN DEL CENTRO — membrete, logo, contacto
# ══════════════════════════════════════════════════════════════════════════════


def _get_config_centro():
    """Devuelve la configuración del centro. Nunca falla — usa defaults."""
    try:
        with sqlite3.connect(DATABASE, timeout=5) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM configuracion_centro WHERE id=1").fetchone()
            if row:
                cfg = dict(DEFAULTS_CENTRO)
                cfg.update({k: row[k] for k in row.keys() if row[k] is not None})
                return cfg
    except Exception:
        pass
    return dict(DEFAULTS_CENTRO)


def _construir_prompt_asignacion(tipo, materia, grado, mencion):
    """
    Genera un prompt para que la IA devuelva criterios de evaluación
    diferenciados según el tipo de asignación, la materia y la mención.
    """
    curriculum = CURRICULUM_ARTES.get(materia, {})
    competencia  = curriculum.get("competencia", "")
    descripcion  = curriculum.get("descripcion", "")
    evidencias   = curriculum.get("evidencias", "")
    indicadores  = curriculum.get("indicadores", [])
    ind_str = "; ".join(indicadores[:3]) if indicadores else ""

    tipo_guia = {
        "tarea": (
            "una TAREA escrita o práctica individual. "
            "Los criterios deben evaluar comprensión conceptual, aplicación y presentación."
        ),
        "examen": (
            "un EXAMEN formal de conocimientos. "
            "Los criterios deben reflejar dominio conceptual, precisión técnica y argumentación."
            " Para materias técnicas artísticas (instrumento, actuación, fotografía, danza) "
            "el examen es una DEMOSTRACIÓN PRÁCTICA o audición grabada, no escrita."
        ),
        "proyecto": (
            "un PROYECTO creativo o de investigación. "
            "Los criterios deben evaluar proceso, creatividad, técnica, presentación y reflexión."
        ),
    }.get(tipo, "una actividad evaluativa")

    prompt = f"""Eres un experto en evaluación educativa del bachillerato dominicano (MINERD), especializado en la Modalidad en Artes del C.E. Benito Juárez.

Contexto de la asignación:
- Tipo: {tipo_guia}
- Materia: {materia}
- Grado: {grado} | Mención: {mencion}
- Competencia curricular: {competencia}
- Descripción de la materia: {descripcion}
- Evidencias de aprendizaje esperadas: {evidencias}
- Indicadores de logro relevantes: {ind_str}

Genera exactamente 4 criterios de evaluación apropiados para esta asignación.
Cada criterio debe ser específico para la naturaleza de "{materia}" — NO uses criterios genéricos válidos para cualquier materia.

Responde SOLO con un objeto JSON con esta estructura exacta, sin texto adicional ni backticks:
{{
  "titulo": "título breve y descriptivo de la asignación (ej: 'Portafolio fotográfico — Luz y sombra')",
  "descripcion": "descripción en 2-3 oraciones de qué debe hacer el estudiante, adaptada a la materia",
  "criterios": [
    {{"nombre": "nombre del criterio", "puntaje_max": 25, "descripcion": "qué se evalúa exactamente"}},
    {{"nombre": "nombre del criterio", "puntaje_max": 25, "descripcion": "qué se evalúa exactamente"}},
    {{"nombre": "nombre del criterio", "puntaje_max": 25, "descripcion": "qué se evalúa exactamente"}},
    {{"nombre": "nombre del criterio", "puntaje_max": 25, "descripcion": "qué se evalúa exactamente"}}
  ]
}}

Los puntajes deben sumar 100. Adapta los criterios al tipo "{tipo}" de forma que tenga sentido para "{materia}" en {mencion}.
"""
    return prompt


def _periodo_bloqueado(periodo: str, anio_escolar: str = None) -> bool:
    """Retorna True si el período está cerrado para edición de notas."""
    if not anio_escolar:
        anio_escolar = _anio_escolar_actual()
    try:
        with sqlite3.connect(DATABASE, timeout=5) as conn:
            row = conn.execute(
                "SELECT id FROM periodos_bloqueados WHERE periodo=? AND anio_escolar=?",
                (periodo, anio_escolar)
            ).fetchone()
            return row is not None
    except Exception:
        return False


def _get_periodos_estado(anio_escolar: str = None) -> dict:
    """Retorna dict {P1: bool, P2: bool, P3: bool, P4: bool} con estado de bloqueo."""
    if not anio_escolar:
        anio_escolar = _anio_escolar_actual()
    estado = {"P1": False, "P2": False, "P3": False, "P4": False}
    try:
        with sqlite3.connect(DATABASE, timeout=10) as conn:
            rows = conn.execute(
                "SELECT periodo FROM periodos_bloqueados WHERE anio_escolar=?",
                (anio_escolar,)
            ).fetchall()
            for r in rows:
                if r[0] in estado:
                    estado[r[0]] = True
    except Exception:
        pass
    return estado



# ══════════════════════════════════════════════════════════════════════════════
#  NORMALIZACIÓN DE MATERIAS — deduplicación y filtro por profesor
# ══════════════════════════════════════════════════════════════════════════════

_MATERIA_SINONIMOS = {
    # Abreviaciones y variantes conocidas del C.E. Benito Juárez
    "fihr":                                              "formacion integral humana y religiosa",
    "formacion integral humana y religiosa":             "formacion integral humana y religiosa",
    "lenguaje visual y artesanal":                       "lenguaje visual y principios del diseno artesanal",
    "lenguaje visual, dibujo y creacion de personajes":  "lenguaje visual y principios del diseno artesanal",
    "lenguaje musical":                                  "lenguaje musical teoria y entrenamiento",
    "lenguaje musical, teoria y entrenamiento":          "lenguaje musical teoria y entrenamiento",
    "lenguaje musical, teoria y entrenamineto":          "lenguaje musical teoria y entrenamiento",
    "intro. a la historia del arte universal y dom":     "introduccion a la historia del arte universal y dominicano",
    "historia del arte universal y dominicano":          "introduccion a la historia del arte universal y dominicano",
    "idioma ingles":                                     "ingles",
    "ingles":                                            "ingles",
}


def _normalizar_clave_materia(nombre):
    """Clave de comparación: sin acentos, minúsculas, sin puntuación final, con mapa de sinónimos."""
    import unicodedata
    s = unicodedata.normalize("NFD", (nombre or "").strip().lower().rstrip("."))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = " ".join(s.split())
    return _MATERIA_SINONIMOS.get(s, s)


def _dedup_materias(rows):
    """
    Deduplica materias con el mismo nombre en distinta capitalización, acentos distintos
    o con typos menores (fuzzy ≥ 0.88).
    Regla de merge: toma el entry con más períodos con nota y promedio mayor.
    Para el nombre de display, prefiere Proper Case sobre TODO MAYÚSCULAS.
    """
    from collections import OrderedDict
    from difflib import SequenceMatcher

    def _merge_entries(entradas):
        def score_datos(e):
            periodos_con_nota = sum(1 for p in ("p1","p2","p3","p4") if e.get(p) and e[p] > 0)
            return (periodos_con_nota, e.get("promedio") or 0)
        mejor = max(entradas, key=score_datos)
        for otra in entradas:
            if otra is mejor:
                continue
            for p in ("p1","p2","p3","p4"):
                if not (mejor.get(p) and mejor[p] > 0) and (otra.get(p) and otra[p] > 0):
                    mejor[p] = otra[p]
        periodos_vals = [mejor[p] for p in ("p1","p2","p3","p4") if mejor.get(p) and mejor[p] > 0]
        if periodos_vals:
            mejor["promedio"] = round(sum(periodos_vals) / len(periodos_vals), 2)
        nombre_display = mejor["materia"]
        for e in entradas:
            if e["materia"] != e["materia"].upper():
                nombre_display = e["materia"]
                break
            if len(e["materia"]) > len(nombre_display):
                nombre_display = e["materia"]
        mejor["materia"] = nombre_display
        return mejor

    grupos = OrderedDict()
    for r in rows:
        clave = _normalizar_clave_materia(r["materia"])
        grupos.setdefault(clave, []).append(r)

    candidatos = []
    for clave, entradas in grupos.items():
        merged = _merge_entries(entradas) if len(entradas) > 1 else entradas[0]
        candidatos.append((clave, merged))

    usados = [False] * len(candidatos)
    resultado = []
    for i, (clave_i, entry_i) in enumerate(candidatos):
        if usados[i]:
            continue
        grupo = [entry_i]
        for j, (clave_j, entry_j) in enumerate(candidatos):
            if j <= i or usados[j]:
                continue
            if SequenceMatcher(None, clave_i, clave_j).ratio() >= 0.88:
                grupo.append(entry_j)
                usados[j] = True
        resultado.append(_merge_entries(grupo) if len(grupo) > 1 else grupo[0])
        usados[i] = True

    return resultado


# ── ARRANQUE ─────────────────────────────────────────────────────────────────


