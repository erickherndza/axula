# -*- coding: utf-8 -*-
"""Autenticación, autorización, CSRF y manejo de roles."""

import functools
import logging
import secrets as _secrets

from flask import session, redirect, url_for, jsonify, request

from .constants import ROLES_ADMIN, ROLES_COORD, ROLES_SUPER, ROLES_DIRECTORA, ROLES_PSICOLOGA

logger = logging.getLogger("axula")

__all__ = [
    "_check_password",
    "_ciclo_del_rol",
    "_csrf_check",
    "_csrf_token",
    "_hash",
    "_normalizar_rol",
    "_rate_check",
    "_rate_peek",
    "admin_required",
    "coord_required",
    "csrf_protected",
    "directora_required",
    "get_usuario",
    "login_required",
    "rate_limited",
]



# ── HASH DE CONTRASEÑAS ─────────────────────────────────────────────────────

def _hash(pw):
    """Hash de contraseña usando werkzeug (pbkdf2:sha256 con salt automático)."""
    from werkzeug.security import generate_password_hash
    return generate_password_hash(pw, method="pbkdf2:sha256")


def _check_password(stored_hash, pw, user_id=None):
    """
    Verifica contraseña soportando formato nuevo (werkzeug pbkdf2) y legacy (sha256 sin sal).
    Si user_id se proporciona y el hash es legacy, lo migra a pbkdf2:sha256 en el momento.
    """
    from werkzeug.security import check_password_hash
    import hashlib
    if stored_hash.startswith("pbkdf2:") or stored_hash.startswith("scrypt:"):
        return check_password_hash(stored_hash, pw)
    # Hash legacy: SHA-256 sin sal — vulnerable a rainbow tables
    if stored_hash == hashlib.sha256(pw.encode()).hexdigest():
        if user_id is not None:
            # Auto-migrar a pbkdf2:sha256 transparentemente
            try:
                from .database import get_db
                db = get_db()
                db.execute("UPDATE usuarios SET password=? WHERE id=?", (_hash(pw), user_id))
                db.commit()
                db.close()
                logger.info(f"[AUTH] Hash legacy migrado a pbkdf2 para user_id={user_id}")
            except Exception as _e:
                logger.warning(f"[AUTH] No se pudo migrar hash legacy para user_id={user_id}: {_e}")
        return True
    return False


# ── NORMALIZACIÓN DE ROLES ───────────────────────────────────────────────────

def _normalizar_rol(rol):
    if not rol:
        return "profesor"
    r = rol.strip()
    rl = r.lower()
    if rl == "coordinador":
        return "coordinador_general"
    if "psicolog" in rl:
        if "primer" in rl or "1" in rl:
            return "psicologa_primer_ciclo"
        if "segundo" in rl or "2" in rl:
            return "psicologa_segundo_ciclo"
        return "psicologa_segundo_ciclo"
    if "coordinador" in rl or "coordinadora" in rl:
        if "primer" in rl or "1" in rl:
            return "coordinador_primer_ciclo"
        if "segundo" in rl or "2" in rl:
            return "coordinador_segundo_ciclo"
        if "general" in rl:
            return "coordinador_general"
        return "coordinador_general"
    if "asistente" in rl:
        return "asistente_directora"
    if "director" in rl:
        return "directora"
    if "superusuario" in rl or rl == "superusuario":
        return "superusuario"
    # Roles administrativos
    if "secretaria" in rl:
        if "docente" in rl:
            return "secretaria_docente"
        return "secretaria"
    if "digitador" in rl:
        return "digitador"
    if "contabilidad" in rl or "auxiliar" in rl:
        return "auxiliar_contabilidad"
    if "suministro" in rl:
        return "suministros"
    return r.lower() or "profesor"


def _ciclo_del_rol(rol):
    """Retorna el ciclo al que tiene acceso un rol, o None si ve todo."""
    rol = _normalizar_rol(rol)
    if rol in ROLES_SUPER or rol == "directora":
        return None
    if "primer" in rol:
        return "primer_ciclo"
    if "segundo" in rol:
        return "segundo_ciclo"
    return None


# ── DECORADORES DE ACCESO ────────────────────────────────────────────────────

def login_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        uid = session.get("user_id")
        if not uid:
            logger.info(f"[AUTH] login_required: NO session for {request.path} | session keys: {list(session.keys())}")
            # Rutas /api/* → 401 JSON para que el frontend pueda manejarlo
            if request.path.startswith("/api/"):
                return jsonify({"error": "no autenticado", "redirect": "/login"}), 401
            return redirect(url_for("auth_bp.login_page"))
        return f(*args, **kwargs)
    return decorated


def coord_required(f):
    """Coordinadores, coordinador_general y directora."""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("auth_bp.login_page"))
        rol = _normalizar_rol(session.get("rol", ""))
        if rol not in ROLES_COORD:
            return jsonify({"error": "Sin permisos"}), 403
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Solo directora. Funciones exclusivas de dirección."""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("auth_bp.login_page"))
        rol = _normalizar_rol(session.get("rol", ""))
        if rol not in ROLES_DIRECTORA:
            return jsonify({"error": "Acceso exclusivo para la Dirección"}), 403
        return f(*args, **kwargs)
    return decorated


def directora_required(f):
    """Solo directora y superusuario."""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("auth_bp.login_page"))
        if _normalizar_rol(session.get("rol", "")) not in {"directora", "superusuario"}:
            return jsonify({"error": "Acceso exclusivo para la Dirección"}), 403
        return f(*args, **kwargs)
    return decorated


# ── PERMISOS CONFIGURABLES ───────────────────────────────────────────────────

def _tiene_permiso(usuario_id: int, permiso: str) -> bool:
    """
    Verifica si un usuario tiene un permiso configurable habilitado.
    Usado principalmente para asistente_directora.
    Directora y superusuario siempre retornan True.
    """
    from flask import session as _sess
    rol = _normalizar_rol(_sess.get("rol", ""))
    if rol in {"directora", "superusuario"}:
        return True
    try:
        from .database import get_db
        db = get_db()
        row = db.execute(
            "SELECT habilitado FROM permisos_configurables WHERE usuario_id=? AND permiso=?",
            (usuario_id, permiso)
        ).fetchone()
        return bool(row and row["habilitado"])
    except Exception:
        return False


# Catálogo de permisos configurables para asistente_directora
PERMISOS_CATALOGO = {
    "gestionar_documentos":       "Gestionar documentos de secretaría",
    "inscribir_estudiantes":      "Inscribir y editar estudiantes",
    "editar_notas":               "Digitar y editar calificaciones",
    "ver_finanzas":               "Ver movimientos financieros (solo lectura)",
    "gestionar_permisos_personal":"Gestionar permisos del personal",
    "ver_reportes_conducta":      "Ver reportes conductuales",
}


# ── CSRF ─────────────────────────────────────────────────────────────────────

def _csrf_token():
    """Genera o recupera el token CSRF de la sesión actual."""
    if "csrf_token" not in session:
        session["csrf_token"] = _secrets.token_hex(32)
    return session["csrf_token"]


def _csrf_check():
    """Valida el token CSRF en peticiones POST/PATCH/DELETE."""
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return True
    exempt = {"/login", "/api/recovery/request", "/api/recovery/reset"}
    if request.path in exempt:
        return True
    token_sesion = session.get("csrf_token", "")
    if not token_sesion:
        return False
    token_req = (
        request.headers.get("X-CSRF-Token") or
        request.form.get("csrf_token") or
        (request.get_json(silent=True) or {}).get("csrf_token", "")
    )
    return _secrets.compare_digest(token_sesion, token_req)


def csrf_protected(f):
    """Decorador que aplica validación CSRF."""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not _csrf_check():
            if request.is_json:
                return jsonify({"error": "Token CSRF inválido o ausente"}), 403
            return redirect(url_for("auth_bp.login_page"))
        return f(*args, **kwargs)
    return decorated


# ── RATE LIMITING ────────────────────────────────────────────────────────────
import time as _time
import sqlite3 as _sqlite3
import os as _os

_RATE_STORE: dict = {}          # caché en memoria (rápido)
_RATE_DB    = _os.path.join(_os.path.dirname(__file__), "..", "rate_limits.db")
_RATE_CLEANUP_EVERY = 200       # limpiar caché cada N llamadas
_rate_call_count    = 0


def _rate_db_conn():
    """Conexión SQLite para persistencia de rate limits."""
    conn = _sqlite3.connect(_RATE_DB, timeout=5)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS rate_limits "
        "(key TEXT NOT NULL, ts REAL NOT NULL)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_rl_key ON rate_limits(key)")
    conn.commit()
    return conn


def _rate_check(key: str, max_calls: int = 30, window: int = 60) -> bool:
    """
    Rate limiting híbrido: caché en memoria + persistencia SQLite.
    Retorna True si el request está dentro del límite.
    """
    global _rate_call_count
    now = _time.time()
    cutoff = now - window

    # ── 1. Caché en memoria ──────────────────────────────────────────────────
    bucket = _RATE_STORE.setdefault(key, [])
    bucket[:] = [t for t in bucket if t > cutoff]

    # ── 2. Cleanup periódico del dict (evita memory leak) ───────────────────
    _rate_call_count += 1
    if _rate_call_count >= _RATE_CLEANUP_EVERY:
        _rate_call_count = 0
        stale = [k for k, v in _RATE_STORE.items() if not v]
        for k in stale:
            del _RATE_STORE[k]

    # ── 3. Si ya superó en caché, rechazar sin tocar DB ─────────────────────
    if len(bucket) >= max_calls:
        return False

    # ── 4. Sincronizar con SQLite para persistencia entre reinicios ──────────
    try:
        conn = _rate_db_conn()
        rows = conn.execute(
            "SELECT ts FROM rate_limits WHERE key=? AND ts>?", (key, cutoff)
        ).fetchall()
        all_ts = sorted({r[0] for r in rows} | set(bucket))
        if len(all_ts) >= max_calls:
            conn.close()
            return False
        conn.execute("INSERT INTO rate_limits(key, ts) VALUES (?,?)", (key, now))
        # limpiar entradas viejas de esta key
        conn.execute("DELETE FROM rate_limits WHERE key=? AND ts<=?", (key, cutoff))
        conn.commit()
        conn.close()
    except Exception as _e:
        logger.warning(f"[RATE] SQLite no disponible, usando solo memoria: {_e}")

    bucket.append(now)
    return True


def _rate_peek(key: str, max_calls: int = 30, window: int = 60) -> bool:
    """
    Verifica si la clave está dentro del límite SIN consumir un slot.
    Retorna True si puede proceder, False si ya está bloqueada.
    """
    now    = _time.time()
    cutoff = now - window
    bucket = [t for t in _RATE_STORE.get(key, []) if t > cutoff]
    if len(bucket) >= max_calls:
        return False
    try:
        conn  = _rate_db_conn()
        count = conn.execute(
            "SELECT COUNT(*) FROM rate_limits WHERE key=? AND ts>?", (key, cutoff)
        ).fetchone()[0]
        conn.close()
        return count < max_calls
    except Exception:
        return True


def rate_limited(max_calls=30, window=60):
    """Decorador de rate-limiting por IP + ruta."""
    def decorator(f):
        @functools.wraps(f)
        def decorated(*args, **kwargs):
            key = f"rate:{request.remote_addr}:{request.path}"
            if not _rate_check(key, max_calls, window):
                return jsonify({"error": "Demasiadas solicitudes. Intenta en un minuto."}), 429
            return f(*args, **kwargs)
        return decorated
    return decorator


# ── USUARIO ACTUAL ───────────────────────────────────────────────────────────

def get_usuario():
    """Retorna dict del usuario logueado o None."""
    if not session.get("user_id"):
        return None
    rol = _normalizar_rol(session.get("rol", ""))
    return {
        "id":       session["user_id"],
        "username": session["username"],
        "nombre":   session["nombre"],
        "rol":      rol,
        "rol_raw":  session.get("rol", ""),
        "materia":  session.get("materia", ""),
        "grado":    session.get("grado", ""),
        "mencion":       session.get("mencion", ""),
        "tipo_docencia": session.get("tipo_docencia", ""),
        "ciclo_acceso": _ciclo_del_rol(rol),
        "es_admin":     rol in ROLES_DIRECTORA,   # solo directora tiene acceso admin
        "es_coord":     rol in ROLES_COORD,
        "es_psicologa": rol in ROLES_PSICOLOGA,
        "es_directora": rol == "directora",
        "es_padre":     rol == "padre",
        "es_profesor":  rol == "profesor",
    }
