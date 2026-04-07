# Propuesta: Soporte Multi-Proveedor de IA

> **Fecha:** 6 de abril de 2026  
> **Estado:** Borrador para revisión  
> **Rama actual:** `multimodel`  
> **Impacto:** Medio-Alto (refactor de capa de IA + UI de configuración)

---

## 1. Diagnóstico del Estado Actual

### 1.1 Acoplamiento con Google Gemini

El proyecto está **100% acoplado** al SDK de Google Generative AI. No existe capa de abstracción entre la lógica de negocio y el proveedor de IA.

| Archivo | Dependencia directa de Gemini |
|---|---|
| `modules/transformer.py` | `import google.generativeai as genai`, `genai.configure()`, `genai.GenerativeModel()`, `model.start_chat()`, `HarmCategory`, `HarmBlockThreshold` |
| `modules/correction.py` | Llama a `invocar_gemini_cli()` con modelo Gemini hardcoded como default |
| `modules/metadata_processor.py` | Llama a `invocar_gemini_cli()` con modelo Gemini hardcoded como default |
| `modules/config_store.py` | `FREE_TIER_LIMITS` solo para modelos Gemini, persistencia solo de `gemini_api_key` |
| `views/configuracion.py` | UI de configuración solo para Gemini, cuotas solo Gemini |
| `views/transformador.py` | `genai.list_models()` para descubrir modelos, selector solo Gemini |
| `requirements.txt` | Solo `google-generativeai>=0.8.3` |

### 1.2 Lo que SÍ está bien diseñado

- **`modules/prompts.py`** → Los prompts son **agnósticos al proveedor**. Son strings puros sin dependencia de ningún SDK. Esto es excelente y no necesita cambios.
- La función `parse_model_response()` en transformer.py es genérica (extrae bloques markdown XML/JSON).
- La función `sanitize_generated_xml()` es post-procesamiento puro, independiente del proveedor.
- El sistema de token tracking en `config_store.py` ya acepta `model_name` como parámetro genérico.

### 1.3 Funcionalidades clave que debe cumplir cualquier proveedor

1. **Generación de texto largo** — El XML JATS de un artículo puede exceder 30,000 tokens de salida.
2. **Continuación automática** — Si el modelo llega a `MAX_TOKENS`, se envía un prompt de continuación en la misma conversación (chat multi-turno).
3. **Manejo de contexto extenso** — Los prompts incluyen el texto completo del artículo (puede ser >50,000 tokens de entrada).
4. **Respuesta estructurada** — El modelo debe devolver XML bien formado dentro de bloques de código markdown.
5. **Configuración de temperatura baja** — Se usa `temperature=0.1` para máxima consistencia.
6. **Reintentos ante rate-limiting** — Manejo de HTTP 429 con backoff exponencial.
7. **Tracking de tokens** — Conteo de tokens de entrada/salida para métricas de uso.

---

## 2. Proveedores Propuestos

### 2.1 Criterios de Selección

| Criterio | Peso | Justificación |
|---|---|---|
| Popularidad y estabilidad del SDK | Alto | Soporte a largo plazo, comunidad activa |
| Ventana de contexto ≥ 128K tokens | Alto | Artículos científicos extensos |
| Calidad en generación de XML estructurado | Alto | Core del producto |
| Disponibilidad de tier gratuito o bajo costo | Medio | Accesibilidad para usuarios individuales |
| SDK Python oficial y mantenido | Alto | Mantenibilidad del código |
| Soporte de chat multi-turno | Alto | Necesario para auto-continuación |

### 2.2 Proveedores Seleccionados

#### ✅ 1. Google Gemini (actual — se mantiene)
- **SDK:** `google-generativeai`
- **Modelos sugeridos:** `gemini-2.5-flash` (recomendado), `gemini-2.5-pro`, `gemini-2.0-flash`
- **Contexto:** Hasta 1M tokens (Flash), 1M tokens (Pro)
- **Tier gratuito:** Sí (500-1500 req/día según modelo)
- **Estado:** Ya implementado, se refactoriza dentro de la nueva abstracción

#### ✅ 2. OpenAI
- **SDK:** `openai` (oficial)
- **Modelos sugeridos:** `gpt-4o` (recomendado), `gpt-4o-mini` (económico), `o3-mini` (razonamiento)
- **Contexto:** 128K tokens (4o), 128K tokens (4o-mini)
- **Max output:** 16,384 tokens (4o), 16,384 tokens (4o-mini) — requiere continuación automática
- **Tier gratuito:** No nativo, pero créditos iniciales $5-$18 según región
- **Justificación:** Proveedor más popular del mercado. SDK maduro y estable. Excelente cumplimiento de instrucciones para XML estructurado.

#### ✅ 3. Anthropic (Claude)
- **SDK:** `anthropic` (oficial)
- **Modelos sugeridos:** `claude-sonnet-4-20250514` (recomendado), `claude-3-5-haiku-20241022` (económico)
- **Contexto:** 200K tokens
- **Max output:** 8,192 tokens (estándar) — requiere continuación automática con extended thinking o concatenación
- **Tier gratuito:** No nativo, créditos iniciales $5
- **Justificación:** El mejor modelo para tareas de texto largo y seguimiento preciso de instrucciones complejas. Ventana de contexto de 200K ideal para artículos extensos. Muy buena adherencia a formatos XML.

#### ✅ 4. OpenAI-Compatible (DeepSeek, Mistral, Groq, local)
- **SDK:** `openai` (misma librería, distinto `base_url`)
- **Modelos sugeridos:**
  - **DeepSeek:** `deepseek-chat` (V3), `deepseek-reasoner` (R1) — Muy económico
  - **Mistral:** `mistral-large-latest`, `mistral-small-latest` — Europeo, buen rendimiento
  - **Groq:** `llama-3.3-70b-versatile` — Inferencia ultrarrápida
  - **Ollama local:** Cualquier modelo compatible — Sin costo, sin internet
- **Contexto:** Variable (32K-128K según modelo)
- **Tier gratuito:** DeepSeek sí, Groq sí (limitado), Mistral créditos iniciales, Ollama gratis (local)
- **Justificación:** Al usar el SDK de OpenAI con `base_url` configurable, se obtiene compatibilidad con docenas de proveedores sin código adicional. Ideal para usuarios que quieren economía o privacidad (modelos locales).

### 2.3 Proveedores Descartados (con justificación)

| Proveedor | Razón de exclusión |
|---|---|
| **AWS Bedrock** | Requiere cuenta AWS + IAM, excesivamente complejo para el público objetivo |
| **Azure OpenAI** | Requiere suscripción Azure + deployment propio, no self-service |
| **Cohere** | Menor calidad en XML estructurado, comunidad más pequeña |
| **AI21 Labs** | SDK menos maduro, ventana de contexto limitada |

---

## 3. Arquitectura Propuesta

### 3.1 Patrón: Provider Abstraction Layer

Se introduce una capa de abstracción con un protocolo (interfaz) que cada proveedor implementa. La lógica de negocio (transformer, correction, metadata) solo interactúa con la abstracción.

```
┌─────────────────────────────────────────────────┐
│                 Lógica de Negocio                │
│  transformer.py | correction.py | metadata.py   │
└──────────────────────┬──────────────────────────┘
                       │ usa
              ┌────────▼────────┐
              │  LLMProvider    │  (Protocolo/ABC)
              │  - generate()   │
              │  - chat()       │
              │  - list_models()│
              └────────┬────────┘
         ┌─────────────┼─────────────┬──────────────┐
         │             │             │              │
   ┌─────▼─────┐ ┌────▼─────┐ ┌────▼──────┐ ┌────▼──────────┐
   │  Gemini   │ │  OpenAI  │ │ Anthropic │ │ OpenAI-Compat │
   │ Provider  │ │ Provider │ │ Provider  │ │   Provider    │
   └───────────┘ └──────────┘ └───────────┘ └───────────────┘
```

### 3.2 Nuevo módulo: `modules/llm_provider.py`

```python
"""Capa de abstracción para proveedores de IA (LLM)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict, Any


@dataclass
class LLMResponse:
    """Respuesta estandarizada de cualquier proveedor."""
    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    finish_reason: str = "stop"          # "stop" | "max_tokens" | "error"
    raw_response: Any = None             # respuesta original del SDK


@dataclass  
class LLMConfig:
    """Configuración unificada de generación."""
    temperature: float = 0.1
    top_p: float = 0.95
    max_output_tokens: int = 65536
    # Cada provider mapea internamente los que soporte


class LLMProvider(ABC):
    """Interfaz que debe implementar cada proveedor de IA."""

    @abstractmethod
    def configure(self, api_key: str, **kwargs) -> None:
        """Inicializa el cliente con la API key."""
        ...

    @abstractmethod
    def generate(self, prompt: str, model: str, config: LLMConfig) -> LLMResponse:
        """Genera una respuesta a partir de un prompt (single-turn)."""
        ...

    @abstractmethod
    def chat_generate(self, messages: List[Dict[str, str]], model: str, 
                      config: LLMConfig) -> LLMResponse:
        """Genera respuesta en modo chat multi-turno (para continuación)."""
        ...

    @abstractmethod
    def list_models(self) -> List[str]:
        """Devuelve la lista de modelos disponibles para este proveedor."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Nombre legible del proveedor (e.g., 'Google Gemini')."""
        ...

    @property
    @abstractmethod
    def default_model(self) -> str:
        """Modelo recomendado por defecto."""
        ...
```

### 3.3 Implementaciones concretas (resumen)

#### GeminiProvider
```python
class GeminiProvider(LLMProvider):
    """Wrapper sobre google-generativeai."""
    provider_name = "Google Gemini"
    default_model = "gemini-2.5-flash"
    
    def configure(self, api_key, **kwargs):
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self._genai = genai
    
    def generate(self, prompt, model, config):
        m = self._genai.GenerativeModel(model)
        response = m.generate_content(prompt, generation_config={...})
        return LLMResponse(
            text=response.text,
            prompt_tokens=response.usage_metadata.prompt_token_count,
            completion_tokens=response.usage_metadata.candidates_token_count,
            ...
        )
    
    def chat_generate(self, messages, model, config):
        m = self._genai.GenerativeModel(model)
        chat = m.start_chat(history=[...])  # convertir messages
        response = chat.send_message(messages[-1]["content"], ...)
        return LLMResponse(...)
    
    def list_models(self):
        return [m.name.replace("models/", "") 
                for m in self._genai.list_models() 
                if 'generateContent' in m.supported_generation_methods]
```

#### OpenAIProvider
```python
class OpenAIProvider(LLMProvider):
    """Wrapper sobre openai SDK — funciona con OpenAI, DeepSeek, Mistral, Groq, etc."""
    provider_name = "OpenAI"
    default_model = "gpt-4o"
    
    def __init__(self, base_url: str = None, provider_label: str = None):
        """base_url permite reutilizar para DeepSeek, Mistral, Groq, Ollama."""
        self._base_url = base_url
        if provider_label:
            self.provider_name = provider_label
    
    def configure(self, api_key, **kwargs):
        from openai import OpenAI
        self._client = OpenAI(api_key=api_key, base_url=self._base_url)
    
    def generate(self, prompt, model, config):
        response = self._client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=config.temperature,
            max_tokens=config.max_output_tokens,
        )
        choice = response.choices[0]
        return LLMResponse(
            text=choice.message.content,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            finish_reason=choice.finish_reason,
            ...
        )
    
    def chat_generate(self, messages, model, config):
        response = self._client.chat.completions.create(
            model=model, messages=messages, ...
        )
        return LLMResponse(...)
    
    def list_models(self):
        models = self._client.models.list()
        return [m.id for m in models.data]
```

#### AnthropicProvider
```python
class AnthropicProvider(LLMProvider):
    """Wrapper sobre anthropic SDK."""
    provider_name = "Anthropic (Claude)"
    default_model = "claude-sonnet-4-20250514"
    
    def configure(self, api_key, **kwargs):
        from anthropic import Anthropic
        self._client = Anthropic(api_key=api_key)
    
    def generate(self, prompt, model, config):
        response = self._client.messages.create(
            model=model,
            max_tokens=config.max_output_tokens,
            temperature=config.temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        return LLMResponse(
            text=response.content[0].text,
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
            finish_reason="max_tokens" if response.stop_reason == "max_tokens" else "stop",
            ...
        )
    
    def chat_generate(self, messages, model, config):
        response = self._client.messages.create(
            model=model, messages=messages, ...
        )
        return LLMResponse(...)
    
    def list_models(self):
        return ["claude-sonnet-4-20250514", "claude-3-5-haiku-20241022"]
```

### 3.4 Registry / Factory

```python
# modules/llm_provider.py (al final del archivo)

PROVIDER_REGISTRY = {
    "gemini": {
        "class": GeminiProvider,
        "label": "Google Gemini",
        "key_placeholder": "AIza...",
        "key_url": "https://aistudio.google.com/app/apikey",
        "requires_package": "google-generativeai",
    },
    "openai": {
        "class": OpenAIProvider,
        "label": "OpenAI",
        "key_placeholder": "sk-...",
        "key_url": "https://platform.openai.com/api-keys",
        "requires_package": "openai",
    },
    "anthropic": {
        "class": AnthropicProvider,
        "label": "Anthropic (Claude)",
        "key_placeholder": "sk-ant-...",
        "key_url": "https://console.anthropic.com/settings/keys",
        "requires_package": "anthropic",
    },
    "deepseek": {
        "class": lambda: OpenAIProvider(
            base_url="https://api.deepseek.com/v1",
            provider_label="DeepSeek",
        ),
        "label": "DeepSeek",
        "key_placeholder": "sk-...",
        "key_url": "https://platform.deepseek.com/api_keys",
        "requires_package": "openai",
    },
    "mistral": {
        "class": lambda: OpenAIProvider(
            base_url="https://api.mistral.ai/v1",
            provider_label="Mistral AI",
        ),
        "label": "Mistral AI",
        "key_placeholder": "",
        "key_url": "https://console.mistral.ai/api-keys/",
        "requires_package": "openai",
    },
    "groq": {
        "class": lambda: OpenAIProvider(
            base_url="https://api.groq.com/openai/v1",
            provider_label="Groq",
        ),
        "label": "Groq",
        "key_placeholder": "gsk_...",
        "key_url": "https://console.groq.com/keys",
        "requires_package": "openai",
    },
    "ollama": {
        "class": lambda: OpenAIProvider(
            base_url="http://localhost:11434/v1",
            provider_label="Ollama (Local)",
        ),
        "label": "Ollama (Local)",
        "key_placeholder": "ollama",
        "key_url": "https://ollama.com/download",
        "requires_package": "openai",
    },
}


def get_provider(provider_id: str) -> LLMProvider:
    """Instancia y devuelve el proveedor solicitado."""
    entry = PROVIDER_REGISTRY.get(provider_id)
    if not entry:
        raise ValueError(f"Proveedor desconocido: {provider_id}")
    
    factory = entry["class"]
    return factory() if callable(factory) and not isinstance(factory, type) else factory()
```

---

## 4. Plan de Cambios por Archivo

### 4.1 Archivos nuevos

| Archivo | Descripción |
|---|---|
| `modules/llm_provider.py` | Protocolo `LLMProvider`, dataclasses `LLMResponse`/`LLMConfig`, implementaciones de los 4 proveedores, registry |

### 4.2 Archivos a modificar

| Archivo | Cambios necesarios |
|---|---|
| **`modules/transformer.py`** | Reemplazar `import google.generativeai` y uso directo por `LLMProvider`. La función `invocar_gemini_cli()` se renombra a `invocar_llm()` y recibe un `provider` en vez de usar Gemini directamente. Se mantiene `invocar_gemini_cli()` como alias de compatibilidad. La lógica de continuación (MAX_TOKENS) usa `chat_generate()` del provider. |
| **`modules/correction.py`** | Cambiar default `model_version` → delegar al provider activo. Agregar parámetro `provider_id`. |
| **`modules/metadata_processor.py`** | Igual que correction.py — agregar parámetro `provider_id`, delegar al provider activo. |
| **`modules/config_store.py`** | Agregar: (1) tabla `provider_keys` para almacenar API key por proveedor; (2) funciones `save_provider_key(provider_id, key)` / `load_provider_key(provider_id)`; (3) `save_active_provider(id)` / `load_active_provider()` para recordar el proveedor seleccionado. Se mantienen `save_api_key`/`load_api_key` como alias que operan sobre el proveedor `"gemini"`. |
| **`views/configuracion.py`** | Rediseñar UI: selector de proveedor con tabs o selectbox; campo de API key por proveedor; tabla de cuotas adaptada al proveedor seleccionado; enlace de obtención de key dinámico. |
| **`views/transformador.py`** | Selector de proveedor en sidebar; lista de modelos dinámica según proveedor activo; pasar `provider_id` a las funciones de transformer/correction/metadata. |
| **`requirements.txt`** | Agregar `openai>=1.30.0` y `anthropic>=0.28.0` como dependencias opcionales (o directas). |

### 4.3 Archivos SIN cambios

| Archivo | Razón |
|---|---|
| `modules/prompts.py` | Ya es agnóstico al proveedor ✅ |
| `modules/xml_html.py` | No interactúa con IA |
| `modules/convert_images.py` | No interactúa con IA |
| `modules/dtd/` | Recursos estáticos |
| `streamlit_app.py` | Solo routing de páginas |
| `views/creditos.py`, `views/documentacion.py`, `views/manual_usuario.py` | No interactúan con IA |

---

## 5. Cambios Detallados en `transformer.py`

Este es el archivo más crítico. El refactor se centra en:

### 5.1 Función principal refactorizada

```python
# ANTES (acoplado a Gemini):
def invocar_gemini_cli(prompt, ..., model_version="gemini-2.5-flash", api_key=None):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_version)
    chat = model.start_chat()
    response = _attempt_gemini_call(model, prompt, ...)
    ...

# DESPUÉS (abstracto):
def invocar_llm(prompt, ..., model_version=None, api_key=None, provider_id=None):
    provider_id = provider_id or config_store.load_active_provider() or "gemini"
    api_key = api_key or config_store.load_provider_key(provider_id)
    
    provider = get_provider(provider_id)
    provider.configure(api_key=api_key)
    
    model = model_version or provider.default_model
    config = LLMConfig(temperature=0.1, max_output_tokens=65536)
    
    # Primera llamada
    response = _attempt_with_retry(provider, prompt, model, config)
    
    # Continuación automática si MAX_TOKENS
    full_text = response.text
    messages = [
        {"role": "user", "content": prompt},
        {"role": "assistant", "content": response.text},
    ]
    loop = 0
    while response.finish_reason == "max_tokens" and loop < 3:
        messages.append({"role": "user", "content": "Continúa generando..."})
        response = _attempt_with_retry_chat(provider, messages, model, config)
        full_text += "\n" + response.text
        messages.append({"role": "assistant", "content": response.text})
        loop += 1
    
    return {'returncode': 0, 'stdout': parse_model_response(full_text), ...}


# Alias de compatibilidad
def invocar_gemini_cli(*args, **kwargs):
    """Alias retrocompatible — delega a invocar_llm()."""
    return invocar_llm(*args, **kwargs)
```

### 5.2 Lógica de reintentos (genérica)

```python
@retry(stop=stop_after_attempt(3), wait=wait_exponential(...), ...)
def _attempt_with_retry(provider: LLMProvider, prompt: str, 
                         model: str, config: LLMConfig) -> LLMResponse:
    try:
        return provider.generate(prompt, model, config)
    except Exception as e:
        if "429" in str(e) or "rate" in str(e).lower():
            raise RetryableError(str(e))
        raise
```

---

## 6. Cambios en la UI (Streamlit)

### 6.1 Sidebar del Transformador (`views/transformador.py`)

```
┌─────────────────────────┐
│ 🤖 Proveedor de IA      │
│ [▾ Google Gemini      ]  │  ← selectbox con proveedores
│                          │
│ 🔧 Modelo               │
│ [▾ gemini-2.5-flash   ]  │  ← se actualiza dinámicamente
│ □ Modelo personalizado   │
│                          │
│ 🔑 ✅ API Key configurada│
│ (←ir a Configuración)    │
└─────────────────────────┘
```

### 6.2 Configuración (`views/configuracion.py`)

```
┌─────────────────────────────────────────────┐
│ ⚙️ Configuración de API                      │
│                                              │
│ Proveedor activo: [▾ Google Gemini        ]  │
│                                              │
│ ┌─ Google Gemini ─┐ ┌─ OpenAI ─┐ ┌─ ... ─┐ │
│ │ Key: AIza•••••  │ │ Key: ❌  │ │       │ │
│ │ ✅ Configurada  │ │ Sin key  │ │       │ │
│ │ [Cambiar]       │ │ [Añadir] │ │       │ │
│ │ 🔗 Obtener key  │ │ 🔗 ...   │ │       │ │
│ └────────────────┘ └──────────┘ └────────┘ │
│                                              │
│ 📋 Cuotas del proveedor activo               │
│ (tabla dinámica según proveedor)             │
│                                              │
│ 📊 Consumo de Tokens (ya existente)          │
└─────────────────────────────────────────────┘
```

---

## 7. Cambios en `config_store.py`

### 7.1 Nuevo esquema de base de datos

```sql
-- Tabla existente 'config' se mantiene para compatibilidad
-- Nueva tabla para API keys por proveedor:
CREATE TABLE IF NOT EXISTS provider_keys (
    provider_id TEXT PRIMARY KEY,
    api_key     TEXT NOT NULL    -- ofuscada con Base64
);
```

### 7.2 Nuevas funciones

```python
def save_provider_key(provider_id: str, api_key: str) -> None: ...
def load_provider_key(provider_id: str) -> Optional[str]: ...
def delete_provider_key(provider_id: str) -> None: ...
def save_active_provider(provider_id: str) -> None: ...
def load_active_provider() -> str: ...  # default "gemini"
```

### 7.3 Migración automática

Al iniciar, si existe `gemini_api_key` en la tabla `config` pero no hay entrada en `provider_keys` para `"gemini"`, migrar automáticamente. Esto mantiene compatibilidad total con bases de datos existentes.

---

## 8. Dependencias

### 8.1 Nuevas dependencias en `requirements.txt`

```
# AI Providers
google-generativeai>=0.8.3          # ya existente
openai>=1.30.0                      # OpenAI + compatible (DeepSeek, Mistral, Groq, Ollama)
anthropic>=0.28.0                   # Anthropic Claude
```

### 8.2 Impacto en tamaño

| Paquete | Tamaño aprox. | Dependencias transitivas |
|---|---|---|
| `openai` | ~300 KB | `httpx`, `pydantic` (ya presentes o ligeros) |
| `anthropic` | ~200 KB | `httpx`, `tokenizers` |

**Impacto total: ~1-2 MB adicionales.** Aceptable.

### 8.3 Alternativa: dependencias opcionales

Si se prefiere no instalar todas las dependencias siempre:

```python
# En cada Provider.__init__:
try:
    import openai
except ImportError:
    raise ImportError(
        "Para usar OpenAI, instala: pip install openai"
    )
```

La UI mostraría solo los proveedores cuyo paquete esté instalado, con un mensaje de guía para instalar los que falten.

---

## 9. Consideraciones de Seguridad

| Aspecto | Tratamiento |
|---|---|
| **Almacenamiento de API keys** | Se mantiene ofuscación Base64 actual (ya documentada como no-encriptación). Se almacena una key por proveedor, todas con el mismo nivel de protección. |
| **Keys en memoria** | Se pasan como parámetro, no se guardan en variables globales. `st.session_state` es por sesión. |
| **Validación de input** | La función `_is_valid_key_format()` se generaliza por proveedor (cada uno tiene su patrón de key). |
| **Errores de API expuestos** | Los mensajes de error se sanitizan para no exponer la API key completa (ya implementado). |
| **Ollama local** | No requiere API key real, pero se valida que el servidor esté corriendo antes de intentar llamadas. |

---

## 10. Plan de Ejecución Incremental

Se propone implementar en **4 fases**, cada una entregando valor funcional:

### Fase 1: Capa de abstracción + refactor Gemini (sin cambios visibles al usuario)
- Crear `modules/llm_provider.py` con `LLMProvider`, `LLMResponse`, `LLMConfig`
- Implementar `GeminiProvider`
- Refactorizar `transformer.py` para usar la abstracción
- Mantener `invocar_gemini_cli()` como alias
- Actualizar `correction.py` y `metadata_processor.py`
- **Tests:** Verificar que todo funciona idéntico a antes

### Fase 2: Agregar OpenAI + Anthropic
- Implementar `OpenAIProvider` y `AnthropicProvider`
- Agregar dependencias a `requirements.txt`
- Actualizar `config_store.py` con tabla `provider_keys` y migración
- **Tests:** Verificar generación XML con cada proveedor

### Fase 3: UI multi-proveedor
- Rediseñar `views/configuracion.py` con selector de proveedor y API keys múltiples
- Actualizar `views/transformador.py` con selector de proveedor en sidebar
- Cuotas dinámicas por proveedor

### Fase 4: Proveedores OpenAI-compatibles + Ollama
- Agregar entries en `PROVIDER_REGISTRY` para DeepSeek, Mistral, Groq, Ollama
- Opción "Proveedor personalizado" con `base_url` configurable
- Documentación actualizada

---

## 11. Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| Calidad de XML varía entre proveedores | Alta | Medio | Validación DTD post-generación ya existe; la corrección automática compensa diferencias. Documentar qué modelos funcionan mejor. |
| Límite de output tokens más bajo en OpenAI/Anthropic | Alta | Alto | La lógica de continuación automática (MAX_TOKENS) ya existe y se porta al protocolo abstracto. Cada provider reporta `finish_reason` estandarizado. |
| API keys almacenadas con distinto formato | Baja | Bajo | Validación de formato por proveedor usando regex (OpenAI: `sk-*`, Anthropic: `sk-ant-*`, Gemini: `AIza*`). |
| Paquete de proveedor no instalado | Media | Bajo | Import dinámico con mensaje claro de error guiando la instalación. |
| Breaking change en SDK de terceros | Baja | Medio | Versiones pinneadas en requirements.txt. Cada provider está aislado. |

---

## 12. Resumen Ejecutivo

| Dimensión | Antes | Después |
|---|---|---|
| **Proveedores** | Solo Gemini | Gemini, OpenAI, Anthropic, DeepSeek, Mistral, Groq, Ollama |
| **Acoplamiento** | Directo a `google-generativeai` | Abstracción `LLMProvider` |
| **API Keys** | 1 (Gemini) | 1 por proveedor, almacenadas independientemente |
| **Selección de modelo** | Solo modelos Gemini | Modelos dinámicos por proveedor |
| **Dependencias nuevas** | — | `openai>=1.30.0`, `anthropic>=0.28.0` (~2 MB) |
| **Archivos nuevos** | — | 1 (`modules/llm_provider.py`) |
| **Archivos modificados** | — | 5 (`transformer`, `correction`, `metadata_processor`, `config_store`, `views/*`) |
| **Prompts** | Sin cambios | Sin cambios (ya agnósticos) ✅ |
| **Compatibilidad hacia atrás** | — | Total (alias `invocar_gemini_cli`, migración automática de DB) |
