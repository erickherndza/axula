# -*- coding: utf-8 -*-
"""Dispatch unificado de currículo para las 4 menciones del Bachillerato en Artes."""

from core.curriculo_multimedia import (
    COMPETENCIAS_FUNDAMENTALES, FASES_ABP, ELEMENTOS_STEAM,
    get_asignatura as _get_multi,
    formatear_contexto_curriculo as _fmt_multi,
)
from core.curriculo_artes_visuales import (
    get_asignatura_artes_visuales as _get_av,
    formatear_contexto_artes_visuales as _fmt_av,
)
from core.curriculo_musica import (
    get_asignatura_musica as _get_mus,
    formatear_contexto_musica as _fmt_mus,
)
from core.curriculo_teatro import (
    get_asignatura_teatro as _get_teat,
    formatear_contexto_teatro as _fmt_teat,
)

_DISPATCH = {
    "MULTIMEDIA":     (_get_multi, _fmt_multi),
    "ARTES VISUALES": (_get_av,    _fmt_av),
    "MUSICA":         (_get_mus,   _fmt_mus),
    "TEATRO":         (_get_teat,  _fmt_teat),
}


def _norm(mencion: str) -> str:
    m = mencion.upper().replace("ARTE MULTIMEDIA", "MULTIMEDIA").strip()
    if "VISUAL" in m:                                          return "ARTES VISUALES"
    if "MUSIC" in m or "MÚSICA" in m:                         return "MUSICA"
    if "TEATRO" in m or "DRAMATICA" in m or "DRAMÁTICA" in m: return "TEATRO"
    return "MULTIMEDIA"


def get_asignatura(mencion: str, nombre: str) -> dict:
    key = _norm(mencion)
    getter, _ = _DISPATCH[key]
    result = getter(nombre)
    if not result and key != "MULTIMEDIA":
        result = _get_multi(nombre)
    return result or {}


def formatear_contexto(mencion: str, nombre: str) -> str:
    key = _norm(mencion)
    _, fmt = _DISPATCH[key]
    result = fmt(nombre)
    if not result and key != "MULTIMEDIA":
        result = _fmt_multi(nombre)
    return result or ""
