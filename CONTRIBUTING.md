# Contribuir al Proyecto

¡Gracias por tu interés en mejorar el Transformador XML JATS! Este documento describe las normas y mejores prácticas para contribuir al código.

## Configuración del Entorno de Desarrollo

1. **Clonar el repositorio**:

    ```bash
    git clone <URL_DEL_REPOSITORIO>
    cd <NOMBRE_DEL_DIR>
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

4. **Configurar Variables de Entorno**:
    Asegúrate de tener configurada la variable `GEMINI_API_KEY` o ingresarla desde la interfaz web al ejecutar la aplicación.

## Arquitectura del Proyecto

El proyecto sigue una arquitectura desacoplada donde el backend es independiente de la interfaz gráfica:

```text
streamlit_app.py          # Punto de entrada web
├── views/
│   ├── transformador.py  # UI principal (Streamlit)
│   └── manual_usuario.py # Documentación y manual
└── modules/
    ├── transformer.py     # Lógica de conversión DOCX → XML
    ├── prompts.py         # Plantillas de prompts para la IA
    ├── metadata_processor.py  # Extracción de metadatos
    ├── correction.py      # Corrección asistida por IA
    ├── xml_html.py        # Conversión XML → HTML
    └── config_store.py    # Persistencia (SQLite)
```

### Principios de Diseño

- **Backend sin dependencia de UI**: `transformer.py`, `metadata_processor.py`, `correction.py` y `prompts.py` NO deben importar `streamlit`. Toda la configuración se pasa como parámetros.
- **Prompts Centralizados**: Todas las instrucciones para la IA están en `prompts.py`. Nunca hardcodees prompts en otros módulos.
- **Modelo Consistente**: El modelo default es `gemini-2.5-flash` en toda la aplicación. Si añades un nuevo punto de llamada a la IA, usa este modelo.

## Estilo de Código y Normas

Para mantener la calidad y legibilidad del código, exigimos el cumplimiento de las siguientes normas en todos los Pull Requests:

### 1. Convenciones Generales

- Seguimos **PEP 8**.
- Longitud de línea máxima sugerida: **100 caracteres**.
- Usa **snake_case** para funciones y variables, y **PascalCase** para clases.

### 2. Type Hints (Tipado Estático)

Todas las funciones y métodos **deben** tener anotaciones de tipo (Type Hints) completas para argumentos y valores de retorno.

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

**Ejemplo:**

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

Al procesar respuestas de la IA (Gemini), sigue estas reglas:

- **Parsing de JSON**: Siempre busca el primer `{` y último `}` para extraer el JSON, ya que el modelo puede anteponer texto.
- **Parsing de XML**: Verifica si la respuesta comienza con `<` (XML directo) o contiene bloques ` ```xml ``` ` (markdown). `invocar_gemini_cli` ya limpia backticks via `parse_model_response`.
- **Normalización**: Usa `_normalize_metadata()` para corregir variaciones en claves del JSON.

### 5. Prompts para la IA

Al modificar o añadir prompts en `prompts.py`:

- Incluye instrucciones explícitas para DOI, fechas y secciones con títulos.
- Para tablas, incluye la estructura XML completa como ejemplo.
- Usa negritas/mayúsculas para reglas CRÍTICAS que el modelo suele ignorar.
- Siempre incluye recordatorios sobre cierre correcto de etiquetas XML.

## Flujo de Trabajo

1. **Reportar Problemas**: Abre un Issue antes de comenzar trabajos grandes.
2. **Ramas (Branches)**: Crea ramas descriptivas, ej. `feature/validacion-xml` o `fix/error-parseo`.
3. **Pull Requests**:
    - Describe claramente tus cambios.
    - Asegúrate de que el código pase las validaciones locales (`python3 -c "import ast; ast.parse(open('archivo.py').read())"` como mínimo).
    - Adjunta capturas de pantalla si cambiaste la interfaz gráfica.

## Errores Conocidos y Mitigaciones

| Problema | Mitigación |
| --- | --- |
| La IA antepone texto antes del JSON de metadatos | Extracción por `{...}` en `metadata_processor.py` |
| La IA no cierra etiquetas XML correctamente | Instrucciones reforzadas en `prompts.py` + sanitización en `transformer.py` |
| `max_output_tokens` insuficiente para artículos largos | Configurado a 65536 tokens |
| Backticks eliminados por `parse_model_response` | Detección dual de XML (directo o con backticks) en `transformador.py` |

## Contacto

Para dudas técnicas, contacta a: [cristian.carreno@uv.cl](mailto:cristian.carreno@uv.cl)
Universidad de Valparaíso.
