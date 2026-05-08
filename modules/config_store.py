"""Módulo de persistencia para configuración y métricas de uso.

Almacena la API Key de Gemini y el historial de tokens consumidos
en una base de datos SQLite local (``data/config.db``).

La API key se guarda cifrada con Fernet (cifrado simétrico autenticado)
para proteger contra exposición accidental en texto plano. Las claves
almacenadas en el formato Base64 anterior se migran automáticamente.

    - ``save_api_key`` / ``load_api_key``: persistencia de la API key.
    - ``save_setting`` / ``load_setting``: configuraciones genéricas.
    - ``log_token_usage``: registra tokens consumidos por operación.
    - ``get_token_summary``: resumen acumulado de tokens.
    - ``get_daily_usage``: uso agrupado por día.

.. note::
    Las funciones ``save_api_key_pro`` / ``load_api_key_pro`` /
    ``delete_api_key_pro`` están **obsoletas** y se mantienen solo
    para compatibilidad silenciosa con bases de datos antiguas.
    No deben usarse en código nuevo.

Typical usage::

    from modules.config_store import save_api_key, load_api_key, log_token_usage

    save_api_key("AIza...")
    key = load_api_key()  # retorna "AIza..."
    log_token_usage("generation", "gemini-2.5-flash", 1200, 3400, 4600)
"""

import base64
import os
import sqlite3
import warnings
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from cryptography.fernet import Fernet

# ─── Constantes ────────────────────────────────────────────────
_DB_DIR = Path("data")
_DB_PATH = _DB_DIR / "config.db"
_FERNET_KEY_PATH = _DB_DIR / ".fernet.key"

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

            CREATE TABLE IF NOT EXISTS provider_keys (
                provider_id TEXT PRIMARY KEY,
                api_key     TEXT NOT NULL
            );
        """)
        # Migración automática: si existe gemini_api_key en config pero no en provider_keys
        row = conn.execute(
            "SELECT value FROM config WHERE key = 'gemini_api_key'"
        ).fetchone()
        if row:
            existing = conn.execute(
                "SELECT 1 FROM provider_keys WHERE provider_id = 'gemini'"
            ).fetchone()
            if not existing:
                conn.execute(
                    "INSERT INTO provider_keys (provider_id, api_key) VALUES (?, ?)",
                    ("gemini", row["value"]),
                )
        conn.commit()
    finally:
        conn.close()


# Inicialización automática al importar
init_db()


# ─── Cifrado de API Keys ──────────────────────────────────────


def _get_or_create_fernet_key() -> bytes:
    """Obtiene o genera la clave Fernet para cifrado de API keys.

    La clave se almacena en ``data/.fernet.key`` y se genera
    automáticamente en la primera ejecución.
    """
    if _FERNET_KEY_PATH.exists():
        return _FERNET_KEY_PATH.read_bytes().strip()
    _DB_DIR.mkdir(parents=True, exist_ok=True)
    key = Fernet.generate_key()
    _FERNET_KEY_PATH.write_bytes(key)
    os.chmod(str(_FERNET_KEY_PATH), 0o600)
    return key


def _obfuscate(text: str) -> str:
    """Cifra un texto con Fernet (cifrado simétrico autenticado).

    Args:
        text: Texto plano a cifrar.

    Returns:
        str: Token Fernet cifrado.
    """
    f = Fernet(_get_or_create_fernet_key())
    return f.encrypt(text.encode("utf-8")).decode("utf-8")


def _deobfuscate(encoded: str) -> str:
    """Descifra un texto. Soporta Fernet y Base64 legacy (migración).

    Si el texto no es un token Fernet válido, intenta decodificarlo
    como Base64 (formato anterior) para compatibilidad con bases de
    datos existentes.

    Args:
        encoded: Texto cifrado (Fernet) o codificado (Base64 legacy).

    Returns:
        str: Texto plano original.
    """
    f = Fernet(_get_or_create_fernet_key())
    try:
        return f.decrypt(encoded.encode("utf-8")).decode("utf-8")
    except Exception:
        # Fallback: Base64 legacy
        return base64.b64decode(encoded.encode("utf-8")).decode("utf-8")


def _migrate_legacy_keys() -> None:
    """Re-cifra con Fernet cualquier API key almacenada en Base64 legacy."""
    conn = _get_connection()
    try:
        fernet = Fernet(_get_or_create_fernet_key())
        # Migrar tabla provider_keys
        rows = conn.execute("SELECT provider_id, api_key FROM provider_keys").fetchall()
        for row in rows:
            stored = row["api_key"]
            try:
                fernet.decrypt(stored.encode("utf-8"))
            except Exception:
                try:
                    plain = base64.b64decode(stored.encode("utf-8")).decode("utf-8")
                    conn.execute(
                        "UPDATE provider_keys SET api_key = ? WHERE provider_id = ?",
                        (_obfuscate(plain), row["provider_id"]),
                    )
                except Exception:
                    pass
        # Migrar tabla config (gemini_api_key legacy)
        legacy = conn.execute(
            "SELECT value FROM config WHERE key = 'gemini_api_key'"
        ).fetchone()
        if legacy:
            stored = legacy["value"]
            try:
                fernet.decrypt(stored.encode("utf-8"))
            except Exception:
                try:
                    plain = base64.b64decode(stored.encode("utf-8")).decode("utf-8")
                    conn.execute(
                        "UPDATE config SET value = ? WHERE key = 'gemini_api_key'",
                        (_obfuscate(plain),),
                    )
                except Exception:
                    pass
        conn.commit()
    except Exception:
        pass  # La migración no debe romper la importación del módulo
    finally:
        conn.close()


_migrate_legacy_keys()


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


def save_api_key_pro(api_key: str) -> None:  # noqa: D401
    """**OBSOLETO** — No usar en código nuevo.

    La misma clave gratuita funciona en el tier de pago cuando la
    cuenta tiene facturación habilitada en Google Cloud. Esta función
    se mantiene solo para migración silenciosa de bases de datos antiguas.
    """
    warnings.warn(
        "save_api_key_pro está obsoleta. Usa save_api_key() únicamente.",
        DeprecationWarning,
        stacklevel=2,
    )
    save_setting("gemini_api_key_pro", _obfuscate(api_key.strip()))


def load_api_key_pro() -> Optional[str]:  # noqa: D401
    """**OBSOLETO** — No usar en código nuevo.

    Returns:
        La API key Pro desofuscada guardada anteriormente, o ``None``.
    """
    warnings.warn(
        "load_api_key_pro está obsoleta. Usa load_api_key() únicamente.",
        DeprecationWarning,
        stacklevel=2,
    )
    encoded = load_setting("gemini_api_key_pro")
    if encoded:
        try:
            return _deobfuscate(encoded)
        except Exception:
            return None
    return None


def delete_api_key_pro() -> None:  # noqa: D401
    """**OBSOLETO** — No usar en código nuevo."""
    warnings.warn(
        "delete_api_key_pro está obsoleta.",
        DeprecationWarning,
        stacklevel=2,
    )
    delete_setting("gemini_api_key_pro")


# ─── Multi-proveedor API Keys ────────────────────────────────

def save_provider_key(provider_id: str, api_key: str) -> None:
    """Guarda la API Key ofuscada para un proveedor específico.

    Args:
        provider_id: Identificador del proveedor (ej: 'gemini', 'openai').
        api_key: Clave de API en texto plano.
    """
    conn = _get_connection()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO provider_keys (provider_id, api_key) VALUES (?, ?)",
            (provider_id, _obfuscate(api_key.strip())),
        )
        conn.commit()
    finally:
        conn.close()
    # Mantener sincronizada la tabla legacy para Gemini
    if provider_id == "gemini":
        save_api_key(api_key)


def load_provider_key(provider_id: str) -> Optional[str]:
    """Carga la API Key de un proveedor específico.

    Args:
        provider_id: Identificador del proveedor.

    Returns:
        La API key desofuscada, o ``None`` si no hay ninguna guardada.
    """
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT api_key FROM provider_keys WHERE provider_id = ?",
            (provider_id,),
        ).fetchone()
        if row:
            try:
                return _deobfuscate(row["api_key"])
            except Exception:
                return None
    finally:
        conn.close()
    # Fallback para Gemini: intentar la tabla legacy
    if provider_id == "gemini":
        return load_api_key()
    return None


def delete_provider_key(provider_id: str) -> None:
    """Elimina la API Key de un proveedor específico.

    Args:
        provider_id: Identificador del proveedor.
    """
    conn = _get_connection()
    try:
        conn.execute(
            "DELETE FROM provider_keys WHERE provider_id = ?",
            (provider_id,),
        )
        conn.commit()
    finally:
        conn.close()
    if provider_id == "gemini":
        delete_api_key()


def save_active_provider(provider_id: str) -> None:
    """Guarda el proveedor activo seleccionado por el usuario.

    Args:
        provider_id: Identificador del proveedor activo.
    """
    save_setting("active_provider", provider_id)


def load_active_provider() -> str:
    """Carga el proveedor activo. Por defecto 'gemini'.

    Returns:
        Identificador del proveedor activo.
    """
    return load_setting("active_provider") or "gemini"


def get_configured_providers() -> List[str]:
    """Devuelve la lista de provider_ids que tienen una API key guardada.

    Returns:
        Lista de identificadores de proveedores configurados.
    """
    conn = _get_connection()
    try:
        rows = conn.execute("SELECT provider_id FROM provider_keys").fetchall()
        return [row["provider_id"] for row in rows]
    finally:
        conn.close()


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


# ─── Prompts Personalizados ───────────────────────────────────

def get_custom_generation_prompt() -> Optional[str]:
    """Obtiene el prompt de generación XML personalizado si existe."""
    return load_setting("custom_generation_prompt")


def save_custom_generation_prompt(prompt_text: str) -> None:
    """Guarda un prompt de generación XML personalizado."""
    save_setting("custom_generation_prompt", prompt_text)


def delete_custom_generation_prompt() -> None:
    """Elimina el prompt de generación XML personalizado."""
    delete_setting("custom_generation_prompt")


def get_custom_extraction_prompt() -> Optional[str]:
    """Obtiene el prompt de extracción de metadatos personalizado si existe."""
    return load_setting("custom_extraction_prompt")


def save_custom_extraction_prompt(prompt_text: str) -> None:
    """Guarda un prompt de extracción de metadatos personalizado."""
    save_setting("custom_extraction_prompt", prompt_text)


def delete_custom_extraction_prompt() -> None:
    """Elimina el prompt de extracción de metadatos personalizado."""
    delete_setting("custom_extraction_prompt")


def get_default_journal_data() -> Dict[str, str]:
    """Obtiene los datos por defecto de la revista (legacy, 3 campos).

    .. deprecated::
        Usar :func:`get_journal_config` para acceso completo.
    """
    return {
        "title": load_setting("default_journal_title") or "",
        "publisher": load_setting("default_publisher_name") or "",
        "issn": load_setting("default_journal_issn") or "",
    }


def save_default_journal_data(title: str, publisher: str, issn: str) -> None:
    """Guarda los datos por defecto de la revista (legacy, 3 campos).

    .. deprecated::
        Usar :func:`save_journal_config` para persistencia completa.
    """
    save_setting("default_journal_title", title)
    save_setting("default_publisher_name", publisher)
    save_setting("default_journal_issn", issn)


# ─── Configuración completa de Revista ────────────────────────

# Claves de configuración para la revista (journal-meta JATS)
_JOURNAL_KEYS: Dict[str, str] = {
    "title":          "default_journal_title",
    "abbrev_title":   "journal_abbrev_title",
    "journal_id":     "journal_publisher_id",
    "publisher":      "default_publisher_name",
    "issn_print":     "default_journal_issn",
    "issn_electronic": "journal_issn_electronic",
    "doi_base":       "journal_doi_base",
    "subject":        "journal_subject",
    "license_url":    "journal_license_url",
    "license_text":   "journal_license_text",
    "default_lang":   "journal_default_lang",
}


def get_journal_config() -> Dict[str, str]:
    """Obtiene la configuración completa de la revista.

    Returns:
        Dict con todas las claves de configuración editorial.
        Los valores no configurados se retornan como cadena vacía.
    """
    return {key: load_setting(db_key) or "" for key, db_key in _JOURNAL_KEYS.items()}


def save_journal_config(data: Dict[str, str]) -> None:
    """Guarda la configuración completa de la revista.

    Args:
        data: Diccionario con las claves de :data:`_JOURNAL_KEYS`.
              Las claves no presentes se ignoran.
    """
    for key, db_key in _JOURNAL_KEYS.items():
        if key in data:
            save_setting(db_key, data[key].strip())


# ─── Logos de revista ─────────────────────────────────────────

_LOGOS_DIR = _DB_DIR / "logos"


def save_journal_logo(mode: str, image_bytes: bytes, filename: str) -> Path:
    """Guarda un logo de la revista (modo claro u oscuro).

    Args:
        mode: ``'light'`` o ``'dark'``.
        image_bytes: Bytes del archivo de imagen.
        filename: Nombre original del archivo (para extensión).

    Returns:
        Path al archivo guardado.
    """
    _LOGOS_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(filename).suffix.lower() or ".png"
    dest = _LOGOS_DIR / f"journal_logo_{mode}{ext}"
    # Eliminar logos previos del mismo modo con otra extensión
    for old in _LOGOS_DIR.glob(f"journal_logo_{mode}.*"):
        old.unlink(missing_ok=True)
    dest.write_bytes(image_bytes)
    return dest


def get_journal_logo_path(mode: str) -> Optional[Path]:
    """Retorna la ruta al logo de la revista para un modo dado.

    Args:
        mode: ``'light'`` o ``'dark'``.

    Returns:
        Path al archivo si existe, ``None`` en caso contrario.
    """
    for p in _LOGOS_DIR.glob(f"journal_logo_{mode}.*"):
        if p.is_file():
            return p
    return None


def delete_journal_logo(mode: str) -> None:
    """Elimina el logo de la revista para un modo dado.

    Args:
        mode: ``'light'`` o ``'dark'``.
    """
    for p in _LOGOS_DIR.glob(f"journal_logo_{mode}.*"):
        p.unlink(missing_ok=True)


def get_jats_version() -> str:
    """Obtiene la versión de JATS configurada (1.4 por defecto)."""
    return load_setting("jats_version") or "1.4"


def save_jats_version(version: str) -> None:
    """Guarda la versión de JATS preferida."""
    save_setting("jats_version", version)



def get_ollama_host() -> str:
    """Obtiene la URL configurada para el servidor Ollama."""
    return load_setting("ollama_host") or "http://localhost:11434"


def save_ollama_host(host_url: str) -> None:
    """Guarda la URL del servidor Ollama."""
    save_setting("ollama_host", host_url.strip())


def get_lmstudio_host() -> str:
    """Obtiene la URL configurada para el servidor LM Studio."""
    return load_setting("lmstudio_host") or "http://localhost:1234/v1"


def save_lmstudio_host(host_url: str) -> None:
    """Guarda la URL del servidor LM Studio."""
    save_setting("lmstudio_host", host_url.strip())


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
