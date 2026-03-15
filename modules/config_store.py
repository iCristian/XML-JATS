"""Módulo de persistencia para configuración y métricas de uso.

Almacena la API Key de Gemini y el historial de tokens consumidos
en una base de datos SQLite local (``data/config.db``).

La API key se guarda ofuscada con Base64 para evitar exposición
accidental en texto plano, aunque no constituye encriptación fuerte.

    - ``save_api_key`` / ``load_api_key``: persistencia de API key gratuita.
    - ``save_api_key_pro`` / ``load_api_key_pro``: persistencia de API key Pro (pago).
    - ``save_setting`` / ``load_setting``: configuraciones genéricas.
    - ``log_token_usage``: registra tokens consumidos por operación.
    - ``get_token_summary``: resumen acumulado de tokens.
    - ``get_daily_usage``: uso agrupado por día.

Typical usage::

    from modules.config_store import save_api_key, load_api_key, log_token_usage

    save_api_key("AIza...")
    key = load_api_key()  # retorna "AIza..."
    log_token_usage("generation", "gemini-2.5-flash", 1200, 3400, 4600)
"""

import sqlite3
import base64
import os
from datetime import datetime, date
from pathlib import Path
from typing import Any, Dict, List, Optional


# ─── Constantes ────────────────────────────────────────────────
_DB_DIR = Path("data")
_DB_PATH = _DB_DIR / "config.db"

# Límites del tier gratuito de Gemini (por día / por minuto)
FREE_TIER_LIMITS: Dict[str, Dict[str, int]] = {
    "gemini-2.5-flash":       {"rpd": 500,   "tpm": 250_000,  "rpm": 10},
    "gemini-2.5-flash-lite":  {"rpd": 500,   "tpm": 250_000,  "rpm": 10},
    "gemini-2.5-pro":         {"rpd": 25,    "tpm": 250_000,  "rpm": 5},
    "gemini-3-flash-preview": {"rpd": 500,   "tpm": 250_000,  "rpm": 10},
    "gemini-3-pro-preview":   {"rpd": 25,    "tpm": 250_000,  "rpm": 5},
    "gemini-2.0-flash":       {"rpd": 1500,  "tpm": 1_000_000, "rpm": 15},
}

# Modelo por defecto si no se reconoce
_DEFAULT_LIMITS: Dict[str, int] = {"rpd": 500, "tpm": 250_000, "rpm": 10}


# ─── Conexión y esquema ───────────────────────────────────────

def _get_connection() -> sqlite3.Connection:
    """Abre (o crea) la base de datos y devuelve una conexión.

    Returns:
        sqlite3.Connection: Conexión activa a ``data/config.db``.
    """
    _DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Crea las tablas si no existen.

    Se invoca automáticamente la primera vez que se usa cualquier
    función del módulo, pero puede llamarse explícitamente al
    arrancar la aplicación.
    """
    conn = _get_connection()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS config (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS token_usage (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp         TEXT    NOT NULL,
                operation         TEXT    NOT NULL,
                model             TEXT    NOT NULL,
                prompt_tokens     INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                total_tokens      INTEGER DEFAULT 0
            );
        """)
        conn.commit()
    finally:
        conn.close()


# Inicialización automática al importar
init_db()


# ─── API Key ──────────────────────────────────────────────────

def _obfuscate(text: str) -> str:
    """Ofusca un texto con Base64 (no es encriptación).

    Args:
        text: Texto plano a ofuscar.

    Returns:
        str: Representación Base64 del texto.
    """
    return base64.b64encode(text.encode("utf-8")).decode("utf-8")


def _deobfuscate(encoded: str) -> str:
    """Revierte la ofuscación Base64.

    Args:
        encoded: Texto codificado en Base64.

    Returns:
        str: Texto plano original.
    """
    return base64.b64decode(encoded.encode("utf-8")).decode("utf-8")


def save_api_key(api_key: str) -> None:
    """Guarda la API Key ofuscada en la base de datos.

    Args:
        api_key: Clave de API de Gemini.
    """
    save_setting("gemini_api_key", _obfuscate(api_key.strip()))


def load_api_key() -> Optional[str]:
    """Carga la API Key desde la base de datos.

    Returns:
        La API key desofuscada, o ``None`` si no hay ninguna guardada.
    """
    encoded = load_setting("gemini_api_key")
    if encoded:
        try:
            return _deobfuscate(encoded)
        except Exception:
            return None
    return None


def delete_api_key() -> None:
    """Elimina la API Key guardada de la base de datos."""
    delete_setting("gemini_api_key")


def save_api_key_pro(api_key: str) -> None:
    """Guarda la API Key Pro ofuscada en la base de datos.

    Args:
        api_key: Clave de API Pro de Gemini.
    """
    save_setting("gemini_api_key_pro", _obfuscate(api_key.strip()))


def load_api_key_pro() -> Optional[str]:
    """Carga la API Key Pro desde la base de datos.

    Returns:
        La API key Pro desofuscada, o ``None`` si no hay ninguna guardada.
    """
    encoded = load_setting("gemini_api_key_pro")
    if encoded:
        try:
            return _deobfuscate(encoded)
        except Exception:
            return None
    return None


def delete_api_key_pro() -> None:
    """Elimina la API Key Pro guardada de la base de datos."""
    delete_setting("gemini_api_key_pro")


# ─── Settings genéricos ───────────────────────────────────────

def save_setting(key: str, value: str) -> None:
    """Guarda una configuración clave-valor.

    Args:
        key: Nombre de la configuración.
        value: Valor a almacenar.
    """
    conn = _get_connection()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
            (key, value)
        )
        conn.commit()
    finally:
        conn.close()


def load_setting(key: str) -> Optional[str]:
    """Carga una configuración por su clave.

    Args:
        key: Nombre de la configuración.

    Returns:
        El valor almacenado, o ``None`` si no existe.
    """
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT value FROM config WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else None
    finally:
        conn.close()


def delete_setting(key: str) -> None:
    """Elimina una configuración por su clave.

    Args:
        key: Nombre de la configuración a eliminar.
    """
    conn = _get_connection()
    try:
        conn.execute("DELETE FROM config WHERE key = ?", (key,))
        conn.commit()
    finally:
        conn.close()


# ─── Token Usage ──────────────────────────────────────────────

def log_token_usage(operation: str, model: str,
                    prompt_tokens: int = 0,
                    completion_tokens: int = 0,
                    total_tokens: int = 0) -> None:
    """Registra el uso de tokens de una operación.

    Args:
        operation: Tipo de operación ('generation', 'correction',
            'metadata', 'chatbot').
        model: Nombre del modelo utilizado.
        prompt_tokens: Tokens del prompt.
        completion_tokens: Tokens de la respuesta.
        total_tokens: Tokens totales.
    """
    conn = _get_connection()
    try:
        conn.execute(
            """INSERT INTO token_usage 
               (timestamp, operation, model, prompt_tokens, completion_tokens, total_tokens)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                datetime.now().isoformat(),
                operation,
                model,
                prompt_tokens,
                completion_tokens,
                total_tokens,
            )
        )
        conn.commit()
    finally:
        conn.close()


def get_token_summary() -> Dict[str, Any]:
    """Obtiene un resumen acumulado de uso de tokens.

    Returns:
        Dict con claves:
            - ``total_tokens``: suma total de tokens consumidos (histórico).
            - ``total_requests``: número total de operaciones.
            - ``today_tokens``: tokens consumidos hoy.
            - ``today_requests``: operaciones realizadas hoy.
            - ``last_used``: timestamp de la última operación (o None).
    """
    conn = _get_connection()
    try:
        # Totales globales
        row_all = conn.execute(
            "SELECT COALESCE(SUM(total_tokens), 0) as total, COUNT(*) as cnt FROM token_usage"
        ).fetchone()

        # Totales de hoy
        today_str = date.today().isoformat()
        row_today = conn.execute(
            """SELECT COALESCE(SUM(total_tokens), 0) as total, COUNT(*) as cnt 
               FROM token_usage WHERE timestamp LIKE ?""",
            (today_str + "%",)
        ).fetchone()

        # Última operación
        row_last = conn.execute(
            "SELECT timestamp FROM token_usage ORDER BY id DESC LIMIT 1"
        ).fetchone()

        return {
            "total_tokens": row_all["total"],
            "total_requests": row_all["cnt"],
            "today_tokens": row_today["total"],
            "today_requests": row_today["cnt"],
            "last_used": row_last["timestamp"] if row_last else None,
        }
    finally:
        conn.close()


def get_token_history(limit: int = 20) -> List[Dict[str, Any]]:
    """Obtiene las últimas N operaciones registradas.

    Args:
        limit: Número máximo de registros a retornar.

    Returns:
        Lista de diccionarios con los datos de cada operación.
    """
    conn = _get_connection()
    try:
        rows = conn.execute(
            """SELECT timestamp, operation, model, 
                      prompt_tokens, completion_tokens, total_tokens
               FROM token_usage ORDER BY id DESC LIMIT ?""",
            (limit,)
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_daily_usage(days: int = 30) -> List[Dict[str, Any]]:
    """Obtiene el uso de tokens agrupado por día.

    Args:
        days: Número de días hacia atrás a consultar.

    Returns:
        Lista de diccionarios con ``date``, ``total_tokens``, ``requests``.
    """
    conn = _get_connection()
    try:
        rows = conn.execute(
            """SELECT DATE(timestamp) as day, 
                      SUM(total_tokens) as total_tokens,
                      COUNT(*) as requests
               FROM token_usage 
               GROUP BY DATE(timestamp)
               ORDER BY day DESC
               LIMIT ?""",
            (days,)
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_free_tier_limits(model: str) -> Dict[str, int]:
    """Retorna los límites del tier gratuito para un modelo.

    Args:
        model: Nombre del modelo de Gemini.

    Returns:
        Dict con ``rpd`` (requests/día), ``tpm`` (tokens/minuto),
        ``rpm`` (requests/minuto).
    """
    return FREE_TIER_LIMITS.get(model, _DEFAULT_LIMITS)
