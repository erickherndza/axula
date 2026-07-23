# -*- coding: utf-8 -*-
"""
Sistema de tareas en background para operaciones pesadas (carga de Excel,
generación de PDF masivo, etc.).

Uso:
    from core.tasks import encolar_tarea, obtener_tarea

    # En la ruta Flask (request context):
    task_id = encolar_tarea(mi_funcion, arg1, arg2, kwarg=val)
    return jsonify({"ok": True, "task_id": task_id})

    # En el endpoint de polling:
    tarea = obtener_tarea(task_id)
    return jsonify(tarea)

La función que se pasa a encolar_tarea NO debe usar get_db() / Flask g —
debe crear su propia conexión con sqlite3.connect().
"""

import logging
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

logger = logging.getLogger("axula")

# ── Estado de tareas ──────────────────────────────────────────────────────────
_TAREAS: dict[str, dict] = {}
_LOCK   = threading.Lock()

# Máximo 2 tareas pesadas en paralelo para no saturar el único worker de Render
_POOL = ThreadPoolExecutor(max_workers=2, thread_name_prefix="axula-bg")

# Tiempo de vida de una tarea completada (1 hora)
_TTL = 3600


# ── API pública ───────────────────────────────────────────────────────────────

def encolar_tarea(fn: Callable, *args: Any, **kwargs: Any) -> str:
    """
    Encola `fn(*args, **kwargs)` en el pool de background.
    Devuelve un task_id para hacer polling.

    La función `fn` debe retornar un dict con los resultados.
    Si lanza una excepción, el error queda en tarea["error"].
    """
    task_id = str(uuid.uuid4())
    ahora   = time.time()

    with _LOCK:
        _TAREAS[task_id] = {
            "status":     "pending",   # pending | running | done | error
            "progreso":   0,           # 0-100
            "resultado":  None,
            "error":      None,
            "creada_en":  ahora,
            "terminada_en": None,
        }

    def _wrapper():
        _actualizar(task_id, status="running", progreso=0)
        try:
            resultado = fn(*args, **kwargs)
            _actualizar(task_id, status="done", progreso=100, resultado=resultado)
        except Exception as exc:
            logger.exception("[TASKS] Error en tarea %s: %s", task_id, exc)
            _actualizar(task_id, status="error", error=str(exc))

    _POOL.submit(_wrapper)
    logger.info("[TASKS] Tarea %s encolada: %s", task_id, fn.__name__)
    return task_id


def actualizar_progreso(task_id: str, progreso: int) -> None:
    """Actualiza el % de progreso de una tarea en ejecución (0-100)."""
    with _LOCK:
        t = _TAREAS.get(task_id)
        if t and t["status"] == "running":
            t["progreso"] = max(0, min(100, progreso))


def obtener_tarea(task_id: str) -> dict | None:
    """Retorna el estado de una tarea, o None si no existe / expiró."""
    with _LOCK:
        return dict(_TAREAS[task_id]) if task_id in _TAREAS else None


def limpiar_tareas_viejas() -> int:
    """Elimina tareas completadas con más de _TTL segundos. Retorna el conteo."""
    ahora = time.time()
    with _LOCK:
        viejas = [
            k for k, v in _TAREAS.items()
            if v["terminada_en"] and (ahora - v["terminada_en"]) > _TTL
        ]
        for k in viejas:
            del _TAREAS[k]
    return len(viejas)


# ── Helpers internos ──────────────────────────────────────────────────────────

def _actualizar(task_id: str, **campos) -> None:
    with _LOCK:
        t = _TAREAS.get(task_id)
        if not t:
            return
        t.update(campos)
        if campos.get("status") in ("done", "error"):
            t["terminada_en"] = time.time()
