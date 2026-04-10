# -*- coding: utf-8 -*-

"""Capa de abstracción multi-proveedor para modelos de lenguaje.

Define la interfaz ``LLMProvider`` y las implementaciones concretas para
Google Gemini, OpenAI, Anthropic y proveedores compatibles con la API de OpenAI
(DeepSeek, Mistral, Groq, Ollama).

Uso típico::

    from modules.llm_provider import get_provider

    provider = get_provider("openai")
    response = provider.generate("Hola, ¿cómo estás?", model="gpt-4o", api_key="sk-...")
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# ─── Dataclasses ──────────────────────────────────────────────

@dataclass
class LLMResponse:
    """Respuesta normalizada de cualquier proveedor LLM."""

    text: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    finish_reason: str = ""
    raw: Any = None  # respuesta nativa del SDK


@dataclass
class LLMConfig:
    """Configuración de generación común a todos los proveedores."""

    temperature: float = 0.1
    top_p: float = 0.95
    max_output_tokens: int = 65536


# ─── Clase base ───────────────────────────────────────────────

class LLMProvider(ABC):
    """Interfaz abstracta que deben implementar todos los proveedores."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Identificador único del proveedor (ej: 'gemini', 'openai')."""
        ...

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Nombre legible para la UI."""
        ...

    @abstractmethod
    def generate(
        self,
        prompt: str,
        model: str,
        api_key: str,
        config: Optional[LLMConfig] = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> LLMResponse:
        """Genera una respuesta a partir de un prompt.

        Args:
            prompt: Texto del prompt.
            model: Nombre/ID del modelo.
            api_key: Clave de API.
            config: Configuración de generación (usa defaults si es None).
            chat_history: Historial previo para llamadas multi-turno.

        Returns:
            LLMResponse normalizada.
        """
        ...

    @abstractmethod
    def list_models(self, api_key: str) -> List[str]:
        """Devuelve los modelos disponibles para este proveedor.

        Args:
            api_key: Clave de API necesaria para consultar modelos.

        Returns:
            Lista de identificadores de modelos.
        """
        ...

    def get_default_models(self) -> List[str]:
        """Modelos por defecto si la API no está disponible."""
        return []

    def get_api_key_url(self) -> str:
        """URL donde el usuario puede obtener una API key."""
        return ""

    def get_api_key_env_var(self) -> str:
        """Nombre de la variable de entorno para la API key."""
        return ""

    def is_available(self) -> bool:
        """Indica si el proveedor está disponible actualmente (útil para servicios locales)."""
        return True


# ─── Implementación: Google Gemini ────────────────────────────

class GeminiProvider(LLMProvider):
    """Proveedor para Google Gemini (google-generativeai SDK)."""

    @property
    def provider_id(self) -> str:
        return "gemini"

    @property
    def display_name(self) -> str:
        return "Google Gemini"

    def get_api_key_url(self) -> str:
        return "https://aistudio.google.com/app/apikey"

    def get_api_key_env_var(self) -> str:
        return "GEMINI_API_KEY"

    def get_default_models(self) -> List[str]:
        return [
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-2.5-flash-lite",
            "gemini-3-flash-preview",
            "gemini-3-pro-preview",
            "gemini-2.0-flash",
        ]

    def generate(
        self,
        prompt: str,
        model: str,
        api_key: str,
        config: Optional[LLMConfig] = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> LLMResponse:
        import google.generativeai as genai
        from google.generativeai.types import HarmBlockThreshold, HarmCategory

        cfg = config or LLMConfig()
        genai.configure(api_key=api_key)
        genai_model = genai.GenerativeModel(model)

        generation_config = genai.types.GenerationConfig(
            temperature=cfg.temperature,
            top_p=cfg.top_p,
            top_k=40,
            max_output_tokens=cfg.max_output_tokens,
        )
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }

        chat = genai_model.start_chat()

        # Inyectar historial previo si lo hay
        if chat_history:
            for msg in chat_history:
                role = "user" if msg.get("role") == "user" else "model"
                chat.history.append({"role": role, "parts": [msg["content"]]})

        response = chat.send_message(
            prompt,
            generation_config=generation_config,
            safety_settings=safety_settings,
        )

        text = response.text if response and hasattr(response, "text") else ""
        tu = _extract_gemini_usage(response)

        return LLMResponse(
            text=text,
            prompt_tokens=tu.get("prompt_tokens", 0),
            completion_tokens=tu.get("completion_tokens", 0),
            total_tokens=tu.get("total_tokens", 0),
            finish_reason=_gemini_finish_reason(response),
            raw=response,
        )

    def list_models(self, api_key: str) -> List[str]:
        try:
            import google.generativeai as genai

            genai.configure(api_key=api_key)
            models = []
            for m in genai.list_models():
                if "generateContent" in m.supported_generation_methods:
                    name = m.name.replace("models/", "")
                    if name.startswith("gemini-") and "vision" not in name:
                        models.append(name)
            if models:
                models.sort(reverse=True)
                if "gemini-2.5-flash" in models:
                    models.remove("gemini-2.5-flash")
                    models.insert(0, "gemini-2.5-flash")
                return models
        except Exception:
            pass
        return self.get_default_models()


def _extract_gemini_usage(response: Any) -> Dict[str, int]:
    """Extrae métricas de uso de tokens de una respuesta Gemini."""
    if response and hasattr(response, "usage_metadata"):
        usage = response.usage_metadata
        return {
            "prompt_tokens": getattr(usage, "prompt_token_count", 0),
            "completion_tokens": getattr(usage, "candidates_token_count", 0),
            "total_tokens": getattr(usage, "total_token_count", 0),
        }
    return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


def _gemini_finish_reason(response: Any) -> str:
    """Devuelve el finish_reason como string normalizado."""
    try:
        if response and response.candidates:
            fr = getattr(response.candidates[0], "finish_reason", None)
            return str(fr) if fr else "STOP"
    except Exception:
        pass
    return "STOP"


# ─── Implementación: OpenAI ──────────────────────────────────

class OpenAIProvider(LLMProvider):
    """Proveedor para la API de OpenAI (y compatibles via base_url)."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        custom_provider_id: Optional[str] = None,
        custom_display_name: Optional[str] = None,
        custom_api_key_url: Optional[str] = None,
        custom_api_key_env_var: Optional[str] = None,
        custom_default_models: Optional[List[str]] = None,
    ):
        self._base_url = base_url
        self._custom_id = custom_provider_id
        self._custom_name = custom_display_name
        self._custom_api_key_url = custom_api_key_url
        self._custom_api_key_env_var = custom_api_key_env_var
        self._custom_default_models = custom_default_models

    @property
    def provider_id(self) -> str:
        return self._custom_id or "openai"

    @property
    def display_name(self) -> str:
        return self._custom_name or "OpenAI"

    def get_api_key_url(self) -> str:
        if self._custom_api_key_url is not None:
            return self._custom_api_key_url
        return "https://platform.openai.com/api-keys"

    def get_api_key_env_var(self) -> str:
        if self._custom_api_key_env_var is not None:
            return self._custom_api_key_env_var
        return "OPENAI_API_KEY"

    def get_default_models(self) -> List[str]:
        if self._custom_default_models:
            return self._custom_default_models
        return ["gpt-4o", "gpt-4o-mini", "gpt-4.1", "gpt-4.1-mini", "o3-mini"]

    def get_base_url(self) -> Optional[str]:
        if self._custom_id == "ollama":
            from modules.config_store import get_ollama_host
            host = get_ollama_host().rstrip("/")
            if not host.endswith("/v1"):
                host = f"{host}/v1"
            return host
        if self._custom_id == "lmstudio":
            from modules.config_store import get_lmstudio_host
            host = get_lmstudio_host().rstrip("/")
            if not host.endswith("/v1"):
                host = f"{host}/v1"
            return host
        return self._base_url

    def _ensure_local_ready(self) -> bool:
        """Verifica si el servicio local (Ollama o LM Studio) está respondiendo y, si no, intenta iniciarlo."""
        import requests
        
        host = self.get_base_url()
        if not host:
            return False
            
        # Solo intentar iniciar si es localhost
        is_local = "localhost" in host or "127.0.0.1" in host
        
        # 1. Verificar si ya responde (rápido)
        try:
            if self._custom_id == "ollama":
                # Quitamos /v1 si existe para llegar al endpoint /api/tags nativo de Ollama
                ping_url = host.replace("/v1", "").rstrip("/") + "/api/tags"
            else:
                # Para LM Studio y otros, usamos /models
                ping_url = host.rstrip("/") + "/models"
                
            resp = requests.get(ping_url, timeout=1.0)
            if resp.status_code == 200:
                return True
        except Exception:
            pass
            
        if not is_local:
            return False # No podemos iniciar un servicio remoto
            
        # 2. Intentar iniciarlo en macOS
        if sys.platform == "darwin":
            app_name = "Ollama" if self._custom_id == "ollama" else ("LM Studio" if self._custom_id == "lmstudio" else None)
            if app_name and os.path.exists(f"/Applications/{app_name}.app"):
                try:
                    subprocess.run(["open", "-a", app_name], check=False)
                    # Esperar un poco a que levante
                    for _ in range(5):
                        time.sleep(1)
                        try:
                            resp = requests.get(ping_url, timeout=1.0)
                            if resp.status_code == 200:
                                return True
                        except Exception:
                            continue
                except Exception:
                    pass
        return False

    def is_available(self) -> bool:
        if self._custom_id in ("ollama", "lmstudio"):
            return self._ensure_local_ready()
        return True

    def generate(
        self,
        prompt: str,
        model: str,
        api_key: str,
        config: Optional[LLMConfig] = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> LLMResponse:
        from openai import OpenAI

        if self._custom_id in ("ollama", "lmstudio"):
            self._ensure_local_ready()
            
        cfg = config or LLMConfig()
        
        # Para modelos locales, el SDK falla si la api_key es None/vacía
        _api_key = api_key
        if self._custom_id in ("ollama", "lmstudio") and not _api_key:
            _api_key = self._custom_id
            
        client_kwargs: Dict[str, Any] = {"api_key": _api_key}
        
        actual_base_url = self.get_base_url()
        if actual_base_url:
            client_kwargs["base_url"] = actual_base_url
            
        client = OpenAI(**client_kwargs)

        # Limpiar el nombre del modelo si viene con etiquetas entre corchetes, ej: [LOCAL] o [LOCAL - OFFLINE]
        actual_model = model
        if model.startswith("[") and "] " in model:
            actual_model = model.split("] ", 1)[1]

        messages: List[Dict[str, str]] = []
        if chat_history:
            messages.extend(chat_history)
        messages.append({"role": "user", "content": prompt})

        response = client.chat.completions.create(
            model=actual_model,
            messages=messages,
            temperature=cfg.temperature,
            top_p=cfg.top_p,
            max_tokens=cfg.max_output_tokens,
        )

        choice = response.choices[0] if response.choices else None
        text = choice.message.content if choice else ""
        finish = choice.finish_reason if choice else "stop"
        usage = response.usage

        return LLMResponse(
            text=text or "",
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
            total_tokens=usage.total_tokens if usage else 0,
            finish_reason=finish or "stop",
            raw=response,
        )

    def list_models(self, api_key: str) -> List[str]:
        try:
            from openai import OpenAI

            is_local_provider = self._custom_id in ("ollama", "lmstudio")
            actual_base_url = self.get_base_url()
            
            if is_local_provider:
                self._ensure_local_ready()

            _api_key = api_key
            if is_local_provider and not _api_key:
                _api_key = self._custom_id

            client_kwargs: Dict[str, Any] = {"api_key": _api_key}
            
            if actual_base_url:
                client_kwargs["base_url"] = actual_base_url
                
            client = OpenAI(**client_kwargs)
            models = [m.id for m in client.models.list().data]
            
            if not models:
                return self.get_default_models()
                
            # Solo filtrar por nombres GPT/o* para el proveedor OpenAI nativo
            if not self._custom_id:
                chat_models = [m for m in models if any(k in m for k in ("gpt", "o1", "o3", "o4"))]
                return sorted(chat_models, reverse=True) if chat_models else sorted(models)[:20]
                
            # Para proveedores compatibles (DeepSeek, Mistral, Groq, Ollama, LM Studio)
            if is_local_provider:
                # Etiquetar local vs remoto
                is_local = actual_base_url and ("localhost" in actual_base_url or "127.0.0.1" in actual_base_url)
                tag = "[LOCAL]" if is_local else "[CLOUD]"
                labeled_models = [f"{tag} {m}" for m in models]
                return sorted(labeled_models)
                
            return sorted(models) if len(models) <= 30 else sorted(models)[:30]
        except Exception:
            pass
        
        # Si falló la consulta local, devolvemos default con aviso
        if self._custom_id in ("ollama", "lmstudio"):
            actual_base_url = self.get_base_url()
            is_local = actual_base_url and ("localhost" in actual_base_url or "127.0.0.1" in actual_base_url)
            tag = "[LOCAL - OFFLINE]" if is_local else "[CLOUD - UNREACHABLE]"
            return [f"{tag} {m}" for m in self.get_default_models()]
            
        return self.get_default_models()


# ─── Implementación: Anthropic ────────────────────────────────

class AnthropicProvider(LLMProvider):
    """Proveedor para la API de Anthropic (Claude)."""

    @property
    def provider_id(self) -> str:
        return "anthropic"

    @property
    def display_name(self) -> str:
        return "Anthropic (Claude)"

    def get_api_key_url(self) -> str:
        return "https://console.anthropic.com/settings/keys"

    def get_api_key_env_var(self) -> str:
        return "ANTHROPIC_API_KEY"

    def get_default_models(self) -> List[str]:
        return [
            "claude-sonnet-4-20250514",
            "claude-opus-4-20250514",
            "claude-3-5-haiku-20241022",
        ]

    def generate(
        self,
        prompt: str,
        model: str,
        api_key: str,
        config: Optional[LLMConfig] = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> LLMResponse:
        import anthropic

        cfg = config or LLMConfig()
        client = anthropic.Anthropic(api_key=api_key)

        messages: List[Dict[str, str]] = []
        if chat_history:
            for msg in chat_history:
                role = msg.get("role", "user")
                # Anthropic solo acepta "user" y "assistant"
                if role not in ("user", "assistant"):
                    role = "user"
                messages.append({"role": role, "content": msg["content"]})
        messages.append({"role": "user", "content": prompt})

        response = client.messages.create(
            model=model,
            max_tokens=cfg.max_output_tokens,
            temperature=cfg.temperature,
            top_p=cfg.top_p,
            messages=messages,
        )

        text = ""
        if response.content:
            text = "".join(
                block.text for block in response.content if hasattr(block, "text")
            )

        return LLMResponse(
            text=text,
            prompt_tokens=response.usage.input_tokens if response.usage else 0,
            completion_tokens=response.usage.output_tokens if response.usage else 0,
            total_tokens=(
                (response.usage.input_tokens + response.usage.output_tokens)
                if response.usage
                else 0
            ),
            finish_reason=response.stop_reason or "end_turn",
            raw=response,
        )

    def list_models(self, api_key: str) -> List[str]:
        # Anthropic no tiene endpoint público de listado de modelos
        return self.get_default_models()


# ─── Registro de proveedores ──────────────────────────────────

PROVIDER_REGISTRY: Dict[str, LLMProvider] = {
    "gemini": GeminiProvider(),
    "openai": OpenAIProvider(),
    "anthropic": AnthropicProvider(),
    # Proveedores compatibles con la API de OpenAI
    "deepseek": OpenAIProvider(
        base_url="https://api.deepseek.com/v1",
        custom_provider_id="deepseek",
        custom_display_name="DeepSeek",
        custom_api_key_url="https://platform.deepseek.com/api_keys",
        custom_api_key_env_var="DEEPSEEK_API_KEY",
        custom_default_models=["deepseek-chat", "deepseek-reasoner"],
    ),
    "mistral": OpenAIProvider(
        base_url="https://api.mistral.ai/v1",
        custom_provider_id="mistral",
        custom_display_name="Mistral AI",
        custom_api_key_url="https://console.mistral.ai/api-keys",
        custom_api_key_env_var="MISTRAL_API_KEY",
        custom_default_models=["mistral-large-latest", "mistral-small-latest", "codestral-latest", "open-mistral-nemo"],
    ),
    "groq": OpenAIProvider(
        base_url="https://api.groq.com/openai/v1",
        custom_provider_id="groq",
        custom_display_name="Groq",
        custom_api_key_url="https://console.groq.com/keys",
        custom_api_key_env_var="GROQ_API_KEY",
        custom_default_models=["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768", "gemma2-9b-it"],
    ),
    "ollama": OpenAIProvider(
        base_url="http://localhost:11434/v1",
        custom_provider_id="ollama",
        custom_display_name="Ollama (Local)",
        custom_api_key_url="",
        custom_api_key_env_var="",
        custom_default_models=["llama3.1", "llama3.2", "qwen2.5", "mistral", "gemma2", "phi3"],
    ),
    "lmstudio": OpenAIProvider(
        base_url="http://localhost:1234/v1",
        custom_provider_id="lmstudio",
        custom_display_name="LM Studio (Local)",
        custom_api_key_url="",
        custom_api_key_env_var="",
        custom_default_models=["llama-3-8b-instruct", "qwen2.5-7b-instruct", "mistral-7b-instruct-v0.3", "phi-3-mini-4k-instruct"],
    ),
}


def get_provider(provider_id: str) -> LLMProvider:
    """Obtiene una instancia del proveedor dado su ID.

    Args:
        provider_id: Identificador del proveedor (clave de PROVIDER_REGISTRY).

    Returns:
        Instancia de LLMProvider.

    Raises:
        ValueError: Si el provider_id no existe en el registro.
    """
    provider = PROVIDER_REGISTRY.get(provider_id)
    if provider is None:
        available = ", ".join(PROVIDER_REGISTRY.keys())
        raise ValueError(
            f"Proveedor '{provider_id}' no reconocido. "
            f"Disponibles: {available}"
        )
    return provider


def list_providers(filter_unavailable: bool = False) -> List[Dict[str, str]]:
    """Devuelve la lista de proveedores registrados con su ID y nombre.

    Args:
        filter_unavailable: Si es True, omite servicios locales no disponibles.

    Returns:
        Lista de dicts con claves 'id' y 'name'.
    """
    providers = []
    for pid, p in PROVIDER_REGISTRY.items():
        if filter_unavailable and not p.is_available():
            continue
        providers.append({"id": pid, "name": p.display_name})
    return providers
