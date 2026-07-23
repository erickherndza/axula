# -*- coding: utf-8 -*-
"""
Sistema de respaldos automáticos para Axula.

Respaldo diario de la base de datos SQLite usando el mecanismo
nativo de SQLite (backup API) que es seguro incluso con WAL mode.
El respaldo se dispara automáticamente en el primer request del día.
"""

import os
import sqlite3
import logging
import threading
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger("axula")

# ── Configuración ─────────────────────────────────────────────────────────────
_BACKUP_DIR      = os.environ.get("BACKUP_DIR", "/data/backups" if os.path.isdir("/data") else "backups")
_BACKUP_MAX_DIAS = int(os.environ.get("BACKUP_MAX_DIAS", "30"))  # retener 30 días
_DB_PATH         = os.environ.get("DATABASE_PATH", "/data/database.db" if os.path.isdir("/data") else "database.db")

_ultimo_respaldo: str | None = None   # fecha ISO del último respaldo en esta sesión
_ultimo_error: str | None   = None   # descripción del último error para exponer en /health
_lock = threading.Lock()


def estado_backup() -> dict:
    """Retorna el estado del sistema de respaldo para /health y dashboard."""
    return {
        "ultimo_respaldo": _ultimo_respaldo,
        "ultimo_error":    _ultimo_error,
        "ok":              _ultimo_error is None,
    }


def _hoy() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _nombre_archivo(fecha: str) -> str:
    return f"db_backup_{fecha}.db"


def _limpiar_antiguos(backup_dir: Path) -> None:
    """Elimina respaldos con más de _BACKUP_MAX_DIAS días."""
    corte = datetime.now() - timedelta(days=_BACKUP_MAX_DIAS)
    eliminados = 0
    for f in backup_dir.glob("db_backup_*.db"):
        try:
            # nombre: db_backup_YYYY-MM-DD.db
            fecha_str = f.stem.replace("db_backup_", "")
            fecha = datetime.strptime(fecha_str, "%Y-%m-%d")
            if fecha < corte:
                f.unlink()
                eliminados += 1
        except (ValueError, OSError):
            continue
    if eliminados:
        logger.info(f"[BACKUP] {eliminados} respaldo(s) antiguo(s) eliminado(s)")


def hacer_respaldo(forzar: bool = False) -> bool:
    """
    Realiza un respaldo de la base de datos si no se hizo hoy.
    Retorna True si se creó un nuevo respaldo, False si ya existía.

    Parámetros:
        forzar: si True, siempre hace respaldo ignorando si ya existe uno hoy.
    """
    global _ultimo_respaldo, _ultimo_error

    hoy = _hoy()

    with _lock:
        if not forzar and _ultimo_respaldo == hoy:
            return False  # ya se hizo hoy en esta sesión

        backup_dir = Path(_BACKUP_DIR)
        backup_dir.mkdir(parents=True, exist_ok=True)

        destino = backup_dir / _nombre_archivo(hoy)

        if not forzar and destino.exists():
            _ultimo_respaldo = hoy
            return False  # archivo ya existe en disco

        db_path = Path(_DB_PATH)
        if not db_path.exists():
            logger.warning("[BACKUP] Base de datos no encontrada, respaldo omitido")
            return False

        try:
            src  = sqlite3.connect(str(db_path), timeout=10)
            dest = sqlite3.connect(str(destino))
            with dest:
                src.backup(dest, pages=100)   # backup incremental seguro con WAL
            src.close()
            dest.close()

            tam = destino.stat().st_size / 1024  # KB
            logger.info(f"[BACKUP] Respaldo creado: {destino.name} ({tam:.1f} KB)")

            _limpiar_antiguos(backup_dir)
            _ultimo_respaldo = hoy
            _ultimo_error    = None  # limpiar error previo si el backup fue exitoso
            return True

        except Exception as e:
            _ultimo_error = f"{_hoy()} — {e}"
            logger.error(f"[BACKUP] Error al crear respaldo: {e}")
            # Si el archivo quedó parcial, eliminarlo
            if destino.exists():
                try:
                    destino.unlink()
                except OSError:
                    pass
            return False


def listar_respaldos() -> list[dict]:
    """Retorna lista de respaldos disponibles ordenados del más reciente al más antiguo."""
    backup_dir = Path(_BACKUP_DIR)
    if not backup_dir.exists():
        return []

    resultado = []
    for f in sorted(backup_dir.glob("db_backup_*.db"), reverse=True):
        try:
            fecha_str = f.stem.replace("db_backup_", "")
            fecha = datetime.strptime(fecha_str, "%Y-%m-%d")
            resultado.append({
                "archivo":  f.name,
                "fecha":    fecha_str,
                "fecha_dt": fecha,
                "tamano_kb": round(f.stat().st_size / 1024, 1),
            })
        except (ValueError, OSError):
            continue
    return resultado
