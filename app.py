# -*- coding: utf-8 -*-
"""
Axula — Sistema de Gestión Académica
Centro Educativo en Artes Benito Juárez, Santo Domingo, RD
~81100 estudiantes · 4 especializaciones · Nivel Secundario

App factory — punto de entrada principal.
"""

import os
import logging
import logging.handlers
import traceback
from datetime import timedelta

# ── Logging con rotación ──────────────────────────────────────────────────────
_LOG_DIR  = os.environ.get("LOG_DIR", "logs")
_LOG_FILE = os.path.join(_LOG_DIR, "axula.log")
os.makedirs(_LOG_DIR, exist_ok=True)

_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s — %(message)s")

# Consola
_console = logging.StreamHandler()
_console.setFormatter(_fmt)

# Archivo rotativo: 5 MB por archivo, máximo 7 archivos (~35 MB total)
_file_handler = logging.handlers.RotatingFileHandler(
    _LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=7, encoding="utf-8"
)
_file_handler.setFormatter(_fmt)

logging.basicConfig(level=logging.INFO, handlers=[_console, _file_handler])
logger = logging.getLogger("axula")

# ── Cargar .env antes de cualquier otra cosa ─────────────────────────────────
def _cargar_env(path=".env"):
    """Carga .env sobreescribiendo siempre — el .env es la fuente de verdad."""
    try:
        with open(path) as _f:
            for _line in _f:
                _line = _line.strip()
                if not _line or _line.startswith("#") or "=" not in _line:
                    continue
                _key, _val = _line.split("=", 1)
                _key = _key.strip()
                _val = _val.strip().strip('"').strip("'")
                if _key:
                    os.environ[_key] = _val  # siempre sobreescribe
        logger.info("[ENV] .env cargado correctamente")
    except FileNotFoundError:
        logger.warning("[ENV] Archivo .env no encontrado")
    except Exception as _e:
        logger.error(f"[ENV] Error cargando .env: {_e}")

_cargar_env()
try:
    from dotenv import load_dotenv as _ldenv
    _ldenv(override=True)   # también override=True para dotenv
except ImportError:
    pass

# ── Flask app ────────────────────────────────────────────────────────────────
from flask import Flask, request, jsonify, session, redirect, url_for, render_template
from flask_cors import CORS
from core.security.headers import init_security_headers

app = Flask(__name__)

# Base de datos
from core.constants import DATABASE
FOTOS_DIR = os.path.join("static", "fotos")
os.makedirs(FOTOS_DIR, exist_ok=True)

# Secret key — nunca usar valor fijo predecible
import secrets as _secrets_mod
_PLACEHOLDERS = {"", "cambia_esto_con_el_comando_de_arriba", "change_me", "secret", "dev"}
_secret = os.environ.get("SECRET_KEY", "").strip()
if _secret in _PLACEHOLDERS or len(_secret) < 32:
    _secret = _secrets_mod.token_hex(32)
    logger.warning("  ⚠ SECRET_KEY ausente o débil en .env — generando clave aleatoria temporal.")
    logger.warning("    Las sesiones expirarán al reiniciar. Agrega SECRET_KEY al .env.")
    logger.warning("    Genera una con: python3 -c \"import secrets; print(secrets.token_hex(32))\"")
app.secret_key = _secret

# Configuración de sesión y uploads
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20 MB
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=10)
app.config["SESSION_COOKIE_SAMESITE"] = "Strict"
app.config["SESSION_COOKIE_HTTPONLY"] = True
# SESSION_COOKIE_SECURE=True requiere HTTPS — activar en producción via .env
app.config["SESSION_COOKIE_SECURE"]   = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"
app.config["SESSION_COOKIE_PATH"]     = "/"
app.config["SESSION_COOKIE_NAME"] = "axula_session"


# ── Registrar Blueprints ─────────────────────────────────────────────────────
from routes import ALL_BLUEPRINTS

for bp in ALL_BLUEPRINTS:
    app.register_blueprint(bp)
    logger.info(f"  ✓ Blueprint registrado: {bp.name}")

# ── CORS — solo rutas /api/*, orígenes autorizados ──────────────────────────
CORS(app,
     resources={r"/api/*": {"origins": [
         "http://localhost:5000",
         "https://axula.tudominio.com",
     ]}},
     methods=["GET", "POST", "PUT", "DELETE"],
     allow_headers=["Content-Type", "X-CSRF-Token"],
     supports_credentials=True,
)

# ── Compatibilidad backward de endpoints ─────────────────────────────────────
# Los templates existentes usan url_for("login_page") sin prefijo de blueprint.
# Este wrapper intenta con el nombre desnudo y si falla busca en todos los blueprints.
from werkzeug.routing import BuildError as _BuildError
_original_url_for = url_for

def _compat_url_for(endpoint, **values):
    """url_for compatible: acepta 'login_page' además de 'auth_bp.login_page'."""
    try:
        return _original_url_for(endpoint, **values)
    except _BuildError:
        # Intentar con cada blueprint como prefijo
        for bp_name in app.blueprints:
            try:
                return _original_url_for(f"{bp_name}.{endpoint}", **values)
            except _BuildError:
                continue
        raise

# Inyectar en Jinja y hacer disponible globalmente
app.jinja_env.globals['url_for'] = _compat_url_for


# ── Hooks globales ───────────────────────────────────────────────────────────
from core.auth import _csrf_check, _csrf_token, get_usuario

@app.after_request
def security_headers(response):
    """Agrega security headers en todas las respuestas."""
    # Content Security Policy
    # unsafe-inline requerido por templates con <script> y <style> inline
    # Ajustar cuando se implemente nonces en el futuro
    csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
        "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com data:; "
        "img-src 'self' data: blob: https://ssl.gstatic.com https://*.googleusercontent.com; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self';"
    )
    response.headers["Content-Security-Policy"]       = csp
    response.headers["X-Content-Type-Options"]        = "nosniff"
    response.headers["X-Frame-Options"]               = "DENY"
    response.headers["Referrer-Policy"]               = "strict-origin-when-cross-origin"
    response.headers["X-XSS-Protection"]              = "1; mode=block"
    response.headers["Permissions-Policy"]            = "camera=(), microphone=(), geolocation=()"
    response.headers["Cross-Origin-Resource-Policy"]  = "same-origin"
    response.headers["Cross-Origin-Opener-Policy"]    = "same-origin"
    # HSTS: activar solo cuando haya HTTPS (SESSION_COOKIE_SECURE=true en .env)
    if app.config.get("SESSION_COOKIE_SECURE"):
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    # Ocultar fingerprint del servidor
    response.headers.pop("Server", None)

    # Cache para archivos estáticos
    if request.path.startswith('/static/') and request.method == 'GET':
        ext = request.path.rsplit('.', 1)[-1].lower()
        if ext in ('js', 'css'):
            response.cache_control.max_age = 604800
            response.cache_control.public = True
        elif ext in ('png', 'jpg', 'jpeg', 'gif', 'ico', 'svg', 'webp'):
            response.cache_control.max_age = 2592000
            response.cache_control.public = True
    return response

@app.before_request
def respaldo_diario():
    """Dispara respaldo automático de la DB una vez por día (primer request del día)."""
    # Solo en GET para no bloquear escrituras; en hilo propio para no agregar latencia
    if request.method == "GET" and not request.path.startswith("/static/"):
        import threading
        from core.backup import hacer_respaldo
        threading.Thread(target=hacer_respaldo, daemon=True).start()

@app.before_request
def aislar_roles_operativos():
    """
    Bloquea roles puramente operativos (suministros) de rutas académicas.
    Estos roles solo pueden acceder a su propio portal y rutas de soporte.
    """
    if not session.get("user_id"):
        return
    from core.auth import _normalizar_rol as _nr
    rol = _nr(session.get("rol", ""))

    # Roles con acceso solo a su portal propio
    ROLES_AISLADOS = {"suministros"}
    if rol not in ROLES_AISLADOS:
        return

    path = request.path

    # Rutas permitidas para suministros
    PERMITIDAS = (
        "/suministros", "/api/suministros",  # su portal
        "/archivos", "/api/archivos",         # biblioteca institucional
        "/static/", "/logout", "/login",
        "/api/session-check",
        "/api/cambiar-password",
    )
    if any(path.startswith(p) for p in PERMITIDAS):
        return
    # /perfil exacto (sin ID) = perfil propio del usuario
    if path == "/perfil":
        return

    # Redirigir a su portal en GETs, 403 en APIs
    if path.startswith("/api/"):
        return jsonify({"error": "Sin permisos para esta sección"}), 403
    return redirect("/suministros")


@app.before_request
def csrf_global():
    """Valida CSRF en todas las rutas POST/PATCH/DELETE con sesión activa."""
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return
    RUTAS_EXENTAS = {
        "/login", "/api/recovery/request", "/api/recovery/reset",
    }
    if request.path in RUTAS_EXENTAS:
        return
    if not session.get("user_id"):
        return
    if not _csrf_check():
        if request.is_json or "application/json" in request.headers.get("Accept", ""):
            return jsonify({"error": "Token CSRF inválido. Recarga la página e intenta de nuevo."}), 403
        return redirect(url_for("auth_bp.login_page"))

@app.context_processor
def inject_usuario():
    """Inyecta current_user y csrf_token en todos los templates."""
    u = get_usuario()
    if u is None:
        u = {
            "id": None, "username": "", "nombre": "", "rol": "",
            "materia": "", "grado": "", "mencion": "",
            "es_admin": False, "es_coord": False, "es_psicologa": False,
            "es_directora": False, "ciclo_acceso": None,
            "es_padre": False, "es_profesor": False,
        }
    return {"current_user": u, "csrf_token": _csrf_token()}


# ── Error handlers ───────────────────────────────────────────────────────────

from core.helpers import _is_api_request

@app.errorhandler(404)
def error_404(e):
    if _is_api_request():
        return jsonify({"error": f"Ruta no encontrada: {request.path}"}), 404
    return render_template("login.html",
        error=f"Página no encontrada ({request.path}). Vuelve al inicio."), 404

@app.errorhandler(413)
def error_413(e):
    if _is_api_request():
        return jsonify({"error": "El archivo supera el límite de 20 MB permitido."}), 413
    return render_template("login.html",
        error="El archivo es demasiado grande (límite 20 MB)."), 413

@app.errorhandler(403)
def error_403(e):
    if _is_api_request():
        return jsonify({"error": "Sin permisos para esta acción."}), 403
    return render_template("login.html",
        error="No tienes permisos para acceder a esta sección."), 403

@app.errorhandler(500)
def error_500(e):
    logger.error(f"[500] {request.path}: {e}\n{traceback.format_exc()}")
    if _is_api_request():
        return jsonify({"error": "Error interno del servidor. Intenta de nuevo."}), 500
    return render_template("login.html",
        error="Ocurrió un error interno. Por favor recarga la página."), 500

@app.errorhandler(Exception)
def error_excepcion(e):
    logger.error(f"[EXCEPTION] {request.path}: {e}\n{traceback.format_exc()}")
    if _is_api_request():
        return jsonify({"error": "Error interno del servidor. Intenta de nuevo."}), 500
    return render_template("login.html",
        error="Ocurrió un error inesperado. Por favor recarga la página."), 500


# ── ARRANQUE ─────────────────────────────────────────────────────────────────
from core.database import migrar_bd, _seed_admin
from core.auth import _hash

migrar_bd()
_seed_admin(_hash)

init_security_headers(app)

if __name__ == "__main__":
    _debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(
        debug=_debug,
        port=int(os.environ.get("PORT", 5000)),
        use_reloader=_debug,
        threaded=True,
    )
