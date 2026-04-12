# Guía de Contribución

¡Gracias por tu interés en mejorar el Transformador XML JATS! Este documento describe las normas y mejores prácticas para contribuir al código.

## Tabla de Contenidos

- [Configuración del Entorno de Desarrollo](#configuración-del-entorno-de-desarrollo)
- [Arquitectura del Proyecto](#arquitectura-del-proyecto)
- [Principios de Diseño](#principios-de-diseño)
- [Estilo de Código y Normas](#estilo-de-código-y-normas)
- [Cómo Añadir un Nuevo Proveedor de IA](#cómo-añadir-un-nuevo-proveedor-de-ia)
- [Flujo de Trabajo y Pull Requests](#flujo-de-trabajo-y-pull-requests)
- [Validación Local](#validación-local)
- [Errores Conocidos y Mitigaciones](#errores-conocidos-y-mitigaciones)
- [Política de Seguridad](#política-de-seguridad)
- [Contacto](#contacto)

---

## Configuración del Entorno de Desarrollo

1. **Clonar el repositorio**:

    ```bash
    git clone https://github.com/iCristian/XML-JATS.git
    cd XML-JATS
    ```

2. **Crear un entorno virtual** (Python 3.9+ recomendado):

    ```bash
    python -m venv .venv
    source .venv/bin/activate  # En Windows: .venv\Scripts\activate
    ```

3. **Instalar dependencias**:

    ```bash
    pip install -r requirements.txt
    ```

4. **Configurar la API Key**:
    Ingresa tu clave desde la pestaña **"⚙️ API y Tokens"** en la interfaz web, o exporta la variable de entorno antes de ejecutar:

    ```bash
    export GEMINI_API_KEY="tu_clave_aqui"
    streamlit run streamlit_app.py
    ```

5. **Verificar la instalación**:

    ```bash
    # Verificar sintaxis de todos los módulos
    python -m py_compile modules/transformer.py
    python -m py_compile modules/llm_provider.py
    python -m py_compile modules/metadata_processor.py

    # Verificar modelos disponibles
    python check_models.py
    ```

---

## Arquitectura del Proyecto

El proyecto sigue una arquitectura desacoplada donde el backend es independiente de la interfaz gráfica:

```text
streamlit_app.py              # Punto de entrada web
├── views/
│   ├── transformador.py      # UI principal (Streamlit)
│   ├── configuracion.py      # Configuración de API keys y tokens
│   ├── manual_usuario.py     # Manual de usuario interactivo
│   ├── documentacion.py      # Documentación técnica (README, CONTRIBUTING)
│   └── creditos.py           # Créditos y licencias
└── modules/
    ├── transformer.py         # Núcleo de conversión DOCX/PDF → XML JATS
    ├── prompts.py             # Plantillas de prompts centralizadas
    ├── metadata_processor.py  # Extracción de metadatos con IA
    ├── correction.py          # Corrección asistida por IA
    ├── xml_html.py            # Conversión XML JATS → HTML5
    ├── config_store.py        # Persistencia (SQLite) — API keys y métricas
    └── llm_provider.py        # Abstracción Multi-Proveedor y Multi-Agente
```

---

## Principios de Diseño

Cualquier contribución debe respetar estrictamente los siguientes principios:

### 1. Backend sin dependencia de UI

`transformer.py`, `metadata_processor.py`, `correction.py`, `llm_provider.py` y `prompts.py` **NO deben importar ni depender** de `streamlit` o `st.session_state`. La configuración se pasa como parámetros explícitos y se persiste usando `config_store.py`. Este desacoplamiento es esencial para permitir el uso por CLI y testing automatizado.

### 2. Arquitectura LLM-Agnostic

El proyecto utiliza la clase abstracta `LLMProvider` en `llm_provider.py` para comunicarse con cualquier proveedor de IA. **No introduzcas llamadas directas a `google.generativeai`, `openai.OpenAI()` u otras APIs** fuera de `llm_provider.py`. Toda llamada a la IA debe pasar por `LLMProvider.generate()`.

### 3. Prompts Centralizados

Todas las instrucciones para la IA están **exclusivamente** en `prompts.py`. Nunca hardcodees prompts en `transformer.py`, `correction.py` ni en ninguna vista. Si necesitas un nuevo prompt, agrégalo como función o constante en `prompts.py`.

### 4. Modelo y Versión Consistentes

El modelo por defecto es `gemini-2.5-flash` en toda la aplicación. Si añades un nuevo punto de llamada a la IA, respeta el modelo activo configurado por el usuario (no hardcodees un modelo diferente).

### 5. Una sola API Key por proveedor

**No añadas parámetros `api_key_pro` ni segundas claves.** El sistema ya gestiona el paso entre tier gratuito y pago automáticamente. Cuando la cuota gratuita se agota, `transformer.py` y `correction.py` retornan `{'quota_exceeded': True}` y la UI muestra el banner correspondiente.

### 6. Señalización de Cuota (No excepciones)

Si una función hace llamadas a la IA y puede recibir error 429, debe **retornar** un diccionario que incluya `'quota_exceeded': True` (no lanzar excepción), para que la UI detecte el estado y actualice el banner lateral. Usa `tenacity` con `stop_after_attempt(3)` y `wait_exponential()` para los reintentos.

### 7. Política de Integridad Semántica (Zero-Placeholder)

Queda estrictamente prohibido permitir que la IA entregue XMLs con marcadores de posición (`<!-- Contenido de... -->`). Cualquier cambio en los prompts o el transformador debe reforzar la transcripción íntegra del texto original. La función `verificar_completitud_xml()` en `transformer.py` es la última línea de defensa — no la elimines ni la debilites.

---

## Estilo de Código y Normas

### 1. Convenciones Generales

- Seguimos **PEP 8**.
- Longitud de línea máxima sugerida: **100 caracteres**.
- Usa **snake_case** para funciones y variables, y **PascalCase** para clases.
- No uses abreviaciones crípticas en nombres de variables.

### 2. Type Hints (Tipado Estático)

Todas las funciones y métodos **deben** tener anotaciones de tipo completas para argumentos y valores de retorno.

**Correcto:**

```python
def procesar_texto(entrada: str, opciones: Dict[str, bool]) -> List[str]:
    ...
```

**Incorrecto:**

```python
def procesar_texto(entrada, opciones):
    ...
```

### 3. Docstrings (Estilo Google)

Todas las funciones, clases y módulos públicos deben tener docstrings siguiendo el **Google Python Style Guide**.

```python
def funcion_ejemplo(arg1: int, arg2: str) -> bool:
    """Realiza una operación de ejemplo.

    Explica brevemente qué hace la función. Puede tener múltiples líneas
    si es complejo.

    Args:
        arg1 (int): El primer argumento, que representa X.
        arg2 (str): El segundo argumento, que representa Y.

    Returns:
        bool: True si la operación fue exitosa, False en caso contrario.

    Raises:
        ValueError: Si arg1 es negativo.
    """
    ...
```

### 4. Manejo de Respuestas de IA

Al procesar respuestas de la IA, sigue estas reglas:

- **Parsing de JSON**: Siempre busca el primer `{` y último `}` para extraer el JSON, ya que el modelo puede anteponer texto libre.
- **Parsing de XML**: Verifica si la respuesta comienza con `<` (XML directo) o contiene bloques ` ```xml ``` ` (markdown). `parse_model_response` en `llm_provider.py` ya limpia los backticks.
- **Normalización**: Usa `_normalize_metadata()` en `metadata_processor.py` para corregir variaciones en claves del JSON.
- **Cuota agotada**: Detecta el error 429 con `tenacity`; si se agotan los reintentos, retorna `{'error': ..., 'quota_exceeded': True}`.
- **Auditoría de Completitud**: Al modificar el flujo de generación, invoca `verificar_completitud_xml()` para asegurar que el output sea semánticamente denso.

### 5. Prompts para la IA

Al modificar o añadir prompts en `prompts.py`:

- Incluye instrucciones explícitas para DOI, fechas y secciones con títulos.
- Para tablas, incluye la estructura XML completa como ejemplo en el prompt.
- Usa negritas/mayúsculas para reglas **CRÍTICAS** que el modelo suele ignorar.
- Siempre incluye recordatorios sobre cierre correcto de etiquetas XML.
- Testea el prompt con al menos un artículo real antes de hacer el PR.

---

## Cómo Añadir un Nuevo Proveedor de IA

1. **Crear la clase en `llm_provider.py`**:

    ```python
    class MiProveedorProvider(LLMProvider):
        def generate(self, prompt: str, model: str, api_key: str,
                     max_tokens: int = 8192) -> str:
            # Implementar llamada a la API del nuevo proveedor
            ...

        def get_default_models(self) -> List[str]:
            return ["mi-modelo-1", "mi-modelo-2"]

        def get_api_key_url(self) -> str:
            return "https://mi-proveedor.com/api-keys"

        def get_api_key_env_var(self) -> str:
            return "MI_PROVEEDOR_API_KEY"
    ```

2. **Registrar el proveedor** en `PROVIDER_REGISTRY` dentro de `llm_provider.py`:

    ```python
    PROVIDER_REGISTRY["mi_proveedor"] = MiProveedorProvider()
    ```

3. **Añadir los límites de cuota** en `config_store.py` dentro de `FREE_TIER_LIMITS` (si tiene tier gratuito).

4. **Agregar la documentación** del proveedor en la sección correspondiente de `configuracion.py`.

---

## Flujo de Trabajo y Pull Requests

1. **Reportar Problemas**: Abre un Issue antes de comenzar trabajos grandes. Describe el problema con claridad y, si es posible, incluye un ejemplo de documento que falla.

2. **Ramas (Branches)**: Crea ramas descriptivas desde `main`:
    ```bash
    git checkout -b feature/nuevo-proveedor-mistral
    git checkout -b fix/error-parseo-metadatos
    git checkout -b docs/mejorar-manual-usuario
    ```

3. **Commits**: Usa mensajes descriptivos en español o inglés:
    ```bash
    git commit -m "feat: añadir soporte para proveedor Mistral"
    git commit -m "fix: corregir parsing de fechas en metadata_processor"
    git commit -m "docs: expandir manual de usuario con pasos de corrección"
    ```

4. **Pull Requests**:
    - Describe claramente los cambios realizados y el problema que resuelven.
    - Asegúrate de que el código no tenga errores de sintaxis:
        ```bash
        python -m py_compile modules/transformer.py
        ```
    - Adjunta capturas de pantalla si cambiaste la interfaz gráfica.
    - Referencia el Issue relacionado con `Closes #123`.

---

## Validación Local

Antes de hacer un PR, ejecuta estas validaciones mínimas:

```bash
# 1. Verificar sintaxis de todos los módulos Python
for f in modules/*.py views/*.py streamlit_app.py; do
    python -m py_compile "$f" && echo "OK: $f"
done

# 2. Verificar importaciones
python -c "from modules import transformer, metadata_processor, correction, llm_provider, config_store, prompts, xml_html; print('Imports OK')"

# 3. Lanzar la app y verificar manualmente el flujo básico
streamlit run streamlit_app.py
```

---

## Errores Conocidos y Mitigaciones

| Problema | Causa | Mitigación |
| --- | --- | --- |
| La IA antepone texto antes del JSON de metadatos | Comportamiento variable del modelo | Extracción por `{...}` en `metadata_processor.py` |
| La IA no cierra etiquetas XML correctamente | Límite de contexto / temperatura | Instrucciones reforzadas en `prompts.py` + sanitización en `transformer.py` |
| `max_output_tokens` insuficiente para artículos largos | Artículo muy extenso | Configurado a 65 536 tokens; considerar chunking para artículos >50 páginas |
| Backticks en la respuesta XML | Modelo responde en markdown | Detección dual de XML (directo o con backticks) vía `parse_model_response` |
| Cuota gratuita agotada (HTTP 429 persistente) | Límite diario alcanzado | `transformer.py` retorna `quota_exceeded: True`; la UI muestra el banner automáticamente |
| `SSL: CERTIFICATE_VERIFY_FAILED` en macOS | Certificados Python no instalados | Ignorado programáticamente con fallback; instalar con `Install Certificates.command` |
| Tablas anidadas no se convierten correctamente | Limitación del formato JATS | Aplanar la tabla manualmente en el Word original antes de cargar |
| Placeholders `<!-- Contenido... -->` en el XML | Modelo de baja capacidad o cuota baja | `verificar_completitud_xml()` detecta y rechaza; usar modelo de mayor capacidad |

---

## Política de Seguridad

- **No commitas API keys ni secretos** en el código fuente. Las claves se almacenan en `data/config.db` (excluido de Git mediante `.gitignore`).
- **No expongas `data/config.db`** en PRs o capturas de pantalla.
- Si descubres una vulnerabilidad de seguridad, repórtala directamente por correo a [cristian.carreno@uv.cl](mailto:cristian.carreno@uv.cl) antes de abrir un Issue público.
- Al añadir nuevas dependencias, verifica que no tengan vulnerabilidades conocidas (CVE) en la versión a utilizar.

---

## Contacto

Para dudas técnicas o de arquitectura, contacta a:\
**Cristian Carreño León** — [cristian.carreno@uv.cl](mailto:cristian.carreno@uv.cl)\
Universidad de Valparaíso, Facultad de Medicina.
