# -*- coding: utf-8 -*-
"""
core/security/headers.py
Seguridad HTTP — registra after_request con headers de seguridad estándar.
"""


def init_security_headers(app):
    """
    Registra un @app.after_request que agrega headers de seguridad a cada
    respuesta.  Llamar desde app.py después de crear la instancia Flask.

    Uso::

        from core.security.headers import init_security_headers
        init_security_headers(app)
    """

    @app.after_request
    def _security_headers(response):
        # ── Clickjacking — permite iframes del mismo origen (SAMEORIGIN)
        # El proyecto usa app.py que ya tiene DENY; este módulo usa SAMEORIGIN
        # para mantener compatibilidad con posibles iframes internos.
        response.headers["X-Frame-Options"] = "SAMEORIGIN"

        # ── MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # ── HSTS — solo en producción (cuando debug=False)
        if not app.debug:
            response.headers["Strict-Transport-Security"] = (
                "max-age=63072000; includeSubDomains; preload"
            )

        # ── Referrer
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # ── Permissions — bloquea APIs de hardware sensible
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )

        # ── Content Security Policy
        # • self + unsafe-inline requerido por templates con <script>/<style> inline
        # • Google Fonts: fonts.googleapis.com (CSS) + fonts.gstatic.com (fuentes)
        # • cdnjs: FontAwesome y otras librerías CDN usadas en los templates
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' "
            "https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
            "font-src 'self' https://fonts.gstatic.com "
            "https://cdnjs.cloudflare.com data:; "
            "img-src 'self' data: blob: "
            "https://ssl.gstatic.com https://*.googleusercontent.com; "
            "connect-src 'self'; "
            "frame-ancestors 'self'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )
        response.headers["Content-Security-Policy"] = csp

        return response
