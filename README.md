# Transformador XML JATS (JATS XML Transformer) - v0.66

Una herramienta avanzada impulsada por Inteligencia Artificial para convertir documentos de Word (`.docx`) a formato **JATS XML** validado, diseñada específicamente para el flujo editorial de revistas científicas.

Esta aplicación automatiza el proceso de etiquetado semántico, extracción de tablas e imágenes, y validación contra el estándar **NISO JATS Version 1.4 (ANSI/NISO Z39.96-2024)**.

## 🚀 Características Principales

- **Conversión Inteligente**: Utiliza LLMs (Google Gemini 2.5 Flash) para interpretar la estructura lógica del documento y generar etiquetas JATS precisas.
- **Soporte Multiformato**: Procesa documentos **Word (`.docx`)** y **PDF (`.pdf`)**.
- **Extracción de Metadatos**: Identifica y extrae automáticamente metadatos clave (título, autores, DOI, fechas de publicación, recepción y aceptación).
- **Extracción de Tablas**: Las tablas del documento se convierten automáticamente a `<table-wrap>` con `<thead>`/`<tbody>` correctamente estructurados.
- **Preservación de Texto**: El sistema etiqueta el texto original sin modificarlo — respetando el trabajo de los correctores humanos.
- **Revisión Interactiva**: Permite editar metadatos y dialogar con un chatbot para completar información faltante antes de la generación.
- **Validación JATS 1.4**: Valida contra el último estándar **NISO JATS Version 1.4 (ANSI/NISO Z39.96-2024)**.
- **Conversión a HTML**: Genera archivos HTML autocontenidos con logo incrustado (Base64), tema claro/oscuro, tabla de contenidos interactiva y enlaces funcionales. Las referencias bibliográficas se renderizan correctamente con DOIs clickeables.
- **Vista Previa en Nueva Pestaña**: La previsualización del HTML se abre en una pestaña del navegador con soporte completo de UTF-8 y navegación por anclas.
- **API Key Persistente**: La clave de API se guarda de forma segura en una base de datos SQLite local. No es necesario reingresarla en cada sesión.
- **Monitoreo de Tokens**: Panel integrado que muestra el consumo de tokens acumulado, requests diarias vs. límites del tier gratuito, y alertas automáticas al acercarse al límite.
- **Interfaz Dual**:
  - **Web UI (Streamlit)**: Interfaz gráfica amigable para arrastrar y soltar archivos, editar contenido extraído y previsualizar resultados.
  - **CLI (Línea de Comandos)**: Para automatización y procesamiento por lotes.

## 🛠️ Requisitos del Sistema

- Windows, macOS o Linux.
- [Python 3.9+](https://www.python.org/downloads/)
- Una clave de API de Google Gemini (Google AI Studio).

## 📦 Instalación

1. **Clonar el repositorio** (si aplica) o descargar el código fuente.

2. **Crear un entorno virtual** (recomendado):

    ```bash
    python -m venv .venv
    # Activar:
    # Windows: .venv\Scripts\activate
    # macOS/Linux: source .venv/bin/activate
    ```

3. **Instalar dependencias**:

    ```bash
    pip install -r requirements.txt
    ```

4. **Configurar la API Key de Gemini** (elige una opción):

    **Opción A — Desde la interfaz web (recomendado):**
    Al abrir la aplicación, dirígete a la pestaña **"⚙️ Configuración"** en el menú izquierdo, pega tu clave en el campo correspondiente y presiona **"💾 Guardar"**. La clave se almacena de forma persistente y se carga automáticamente en futuras sesiones.

    **Opción B — Variable de entorno (fallback):**

    ```bash
    export GEMINI_API_KEY="tu_clave_aqui"
    ```

## 📖 Uso

### Interfaz Web (Recomendado)

La interfaz gráfica es la forma más fácil de usar la herramienta.

1. Ejecuta la aplicación:

    ```bash
    streamlit run streamlit_app.py
    ```

2. Abre tu navegador en la URL mostrada (usualmente `http://localhost:8501`).
3. Sube tu archivo `.docx` o `.pdf`.
4. Revisa y completa los metadatos extraídos.
5. Genera el XML, valida y descarga los resultados.
6. Genera el HTML y haz clic en **"Ver vista previa en nueva pestaña"** para inspeccionar el resultado.

### Línea de Comandos (CLI)

Para usuarios avanzados que deseen integrar la herramienta en scripts.

**Transformación (Word -> XML):**

```bash
python -m modules.transformer entrada.docx salida.xml
```

**Conversión (XML -> HTML):**

```bash
python -m modules.xml_html entrada.xml salida.html
```

## 📂 Estructura del Proyecto

- `streamlit_app.py`: Punto de entrada de la aplicación web (Streamlit UI).
- `modules/`:
  - `transformer.py`: Núcleo de la lógica de conversión. Desacoplado de la interfaz de usuario. Usa `tenacity` para manejo robusto de reintentos (HTTP 429) y control de errores. Soporta generación de hasta 65K tokens de salida.
  - `metadata_processor.py`: Módulo para la extracción de metadatos mediante IA, agnóstico al entorno gráfico.
  - `correction.py`: Módulo para la corrección asistida por IA (preserva texto original), completamente separado del estado de Streamlit.
  - `prompts.py`: Repositorio centralizado de instrucciones maestras (prompts) de IA con plantillas detalladas para tablas, secciones, DOI y fechas.
  - `xml_html.py`: Convertidor de JATS XML a HTML5 responsivo con renderización completa de referencias bibliográficas (DOIs clickeables, nombres de autores, fuentes en itálica).
  - `config_store.py`: Almacenamiento persistente de configuración (API Key, uso de tokens) mediante SQLite.
- `views/`: Vistas de la interfaz gráfica (transformador, manual de usuario, documentación).
- `data/`: Base de datos SQLite local (`config.db`) — excluida de Git.
- `JATS-Publishing-1-3-MathML3-DTD/`: Archivos DTD locales para validación offline.
- `imagenes_extraidas/`: Directorio temporal donde se guardan las imágenes extraídas del documento Word.
- `resources/`: Logo de la revista y recursos gráficos.

## 🤝 Créditos

Desarrollado por **Cristian Carreño León**\
Escuela de Obstetricia y Puericultura\
Facultad de Medicina\
Universidad de Valparaíso, Chile.

Desarrollado para la **Universidad de Valparaíso** con el objetivo de optimizar los procesos de publicación científica.

### Tecnologías Utilizadas

| Tecnología | Uso |
| --- | --- |
| Python 3.9+ | Lenguaje base |
| Streamlit | Framework de interfaz web |
| Google Gemini | Modelo de lenguaje (LLM) para etiquetado inteligente |
| lxml | Procesamiento, validación y parsing de XML/HTML |
| python-docx | Extracción de contenido desde archivos Word |
| FPDF2 | Generación de manuales en PDF |
| JATS 1.4 (ANSI/NISO Z39.96-2024) | Estándar de etiquetado XML |

## 📄 Licencia

Este software es de uso exclusivo para la **Universidad de Valparaíso**. Todos los derechos reservados.

El código fuente y la documentación contenidos en este repositorio son propiedad intelectual de la Universidad de Valparaíso y su autor. Queda prohibida su reproducción, distribución o modificación sin autorización expresa.

Para consultas sobre licenciamiento o uso, contactar a: [cristian.carreno@uv.cl](mailto:cristian.carreno@uv.cl)

## 📅 Historial de Versiones (Changelog)

### v0.66 — Interfaz Minimalista, Validación de API y Configuración Dedicada

- **Página de Configuración Exclusiva**: Nueva pestaña "⚙️ Configuración" dedicada exclusivamente a visualizar y gestionar las API Keys y el modelo IA seleccionado, liberando espacio en el menú principal.
- **Validación Robusta de API Keys**: Se implementó una verificación exhaustiva de la API Key en el backend, la cual ahora detecta placeholders o claves inválidas antes de enviar peticiones a la API, evitando errores confusos y cierres inesperados.
- **Interfaz del Menú Lateral Minimalista**: Rediseño del panel lateral en el transformador principal. El estado de la API Key ahora se muestra de forma compacta (mini indicador) bajo el seleccionador de modelo. Las instrucciones pasaron de ocupar gran espacio a mostrarse en un práctico "popover" (ventana flotante).
- **Recuperación Automática de XML Crítico (Resilient Parsing)**: El parser XML ahora cuenta con capacidad de recuperación ante etiquetas malformadas menores (`recover=True`), lo cual permite generar un HTML de vista previa incluso si la IA cometió ligeros errores estructurales en el etiquetado JATS.
- **Mejores Mensajes de Error**: Si el XML está demasiado dañado para generar HTML seguro, la aplicación ahora detecta el fallo y sugiere amablemente al usuario utilizar la pestaña de "Validación y Corrección" asistida por IA para solucionarlo automáticamente.

### v0.65 — Auditoría Exhaustiva y Corrección de Bugs Críticos

- **🔧 15+ Bugs Críticos Corregidos**: Auditoría completa del código fuente de todos los módulos con corrección de errores funcionales que impedían el flujo correcto.
- **Extracción de Tablas Mejorada**: Instrucciones detalladas en el prompt para generar `<table-wrap>` con `<table>`, `<thead>`, `<tbody>`, `<tr>`, `<th>`, `<td>` completos. Las tablas ya no se omiten ni se generan vacías.
- **DOI y Fechas Obligatorios**: El DOI y la fecha de publicación son ahora campos obligatorios en la validación de metadatos. Instrucciones reforzadas para que el modelo siempre incluya `<pub-date>` y `<article-id pub-id-type="doi">`.
- **Secciones con Títulos**: Instrucciones mejoradas para que cada sección del artículo (Introducción, Métodos, Resultados, etc.) se mapee correctamente a `<sec><title>`.
- **Token Limit**: `max_output_tokens` aumentado de 8192 a 65536 — los artículos extensos ya no se truncan.
- **Corrección de Modelo**: Todos los módulos ahora usan `gemini-2.5-flash` de forma consistente.
- **Parsing de Metadatos Robusto**: Nuevo método `_normalize_metadata()` que corrige variaciones en las claves del JSON devuelto por la IA. Extracción de JSON mejorada para manejar respuestas con prefijos no-JSON.
- **Corrección de Chatbot**: El flujo de corrección por chatbot ahora detecta correctamente XML directo (sin backticks) en las respuestas de la IA, resolviendo el bug donde las correcciones nunca se aplicaban.
- **Renderización de Referencias HTML**: `xml_html.py` ahora maneja correctamente elementos JATS de bibliografía (`<name>`, `<surname>`, `<given-names>`, `<person-group>`, `<source>`, `<pub-id>`, etc.) con DOIs clickeables y fuentes en itálica.
- **Eliminación de Código Duplicado**: Removida la definición duplicada de `validar_jats_xml` y la llamada a `construir_prompt_avanzado` (función inexistente).

### v0.64 — Refactorización del Backend y Desacoplamiento de UI

- **Arquitectura Desacoplada**: Eliminada la dependencia de `streamlit` (`st.session_state`) en los módulos del backend (`metadata_processor.py`, `correction.py`, `transformer.py`). Ahora toda la configuración (API keys, versión de modelo) se pasa explícitamente, permitiendo ejecución pura por CLI o testing automatizado.
- **Centralización de Prompts**: Creación del nuevo módulo `modules/prompts.py` que almacena todas las plantillas de instrucciones complejas para la IA, limpiando el código funcional y facilitando la afinación del comportamiento del modelo.
- **Reintentos Robustos con Tenacity**: El bucle manual de reintentos en las llamadas a la API de Google Gemini ha sido reemplazado por la librería estándar `tenacity`. Ahora el sistema maneja automáticamente los errores de cuota (HTTP 429) usando retardos exponenciales, mientras preserva el fallo rápido para errores irrecuperables como bloqueos por *Recitation*/Copyright.

### v0.63 — API Key Persistente y Monitoreo de Tokens

- **Almacenamiento Persistente de API Key**: La clave de Gemini se guarda de forma segura en una base de datos SQLite local (`data/config.db`).
- **Seguridad de la Key**: Una vez guardada, la clave desaparece de la interfaz. Solo se muestra una versión enmascarada (`AIza••••••••xY4Z`). Botones para **cambiar** o **borrar** la key en cualquier momento.
- **Panel de Uso de Tokens**: Nuevo panel expandible en la barra lateral que muestra:
  - Requests usadas hoy vs. límite diario (RPD) con barra de progreso.
  - Tokens consumidos hoy.
  - Límites por minuto (TPM y RPM) del modelo seleccionado.
  - Historial acumulado total.
- **Advertencias de Límite**: Alertas automáticas al alcanzar el 80% y 100% del límite diario del tier gratuito.
- **Registro Automático**: Cada operación con IA (generación, corrección, chatbot) registra automáticamente los tokens consumidos.
- **Nuevo Módulo `config_store.py`**: Gestión centralizada de configuración y métricas mediante SQLite.

### v0.62 — Mejoras de HTML, Manejo de Recitación y Deduplicación de Referencias

- **Deduplicación de Referencias**: Corregido el problema donde los números de referencias bibliográficas aparecían triplicados en el HTML (por `<ol>`, `<label>` y texto de la cita). Nueva función `_strip_leading_ref_number()` limpia automáticamente los números duplicados.
- **Vista Previa en Nueva Pestaña**: La previsualización HTML ahora se abre en una pestaña nueva del navegador en lugar de un iframe incrustado, resolviendo problemas con enlaces y estilos.
- **Corrección UTF-8**: Implementación correcta de decodificación UTF-8 en la vista previa (`TextDecoder` en lugar de `atob`), solucionando caracteres acentuados corruptos (ej. "crÃticas" → "críticas").
- **Navegación por Anclas**: Script de interceptación de clicks en enlaces `#ancla` usando `scrollIntoView()`, corrigiendo la navegación interna en páginas abiertas con `document.write()`.
- **Preservación de Texto (Prompt)**: Prompt de generación JATS completamente reescrito para prohibir modificaciones al texto original — la IA solo etiqueta, nunca reescribe.
- **Manejo de Recitación**: Manejo robusto de errores `finish_reason=4` (recitación) de la API de Gemini con reintentos automáticos y temperatura progresiva.
- **Filtros de Seguridad Desactivados**: Todos los filtros de seguridad de Gemini configurados en `BLOCK_NONE` (apropiado para contenido académico publicado).
- **Instrucciones de Referencia en Prompt**: Las instrucciones JATS ahora especifican explícitamente que el número de referencia va SOLO en `<label>`, no en `<element-citation>`.

### v0.6 — Actualización JATS 1.4 + Metadatos

- **Estándar JATS 1.4**: Actualización completa del motor de validación y prompts al estándar ANSI/NISO Z39.96-2024.
- **Soporte PDF**: Ahora es posible cargar archivos `.pdf` para extracción de texto y metadatos.
- **Módulo de Metadatos**: Nueva lógica de extracción y validación de metadatos (título, autores, DOI, fecha).
- **UI de Revisión**: Nueva sección en la interfaz para editar metadatos y chatbot asistente para completar información faltante.

### v0.5 (Beta)

- **Mejoras de UI**: Navegación por pestañas con botones de avance automático.
- **Corrección Interactiva**: Nuevo chatbot que permite dialogar con la IA para resolver errores de validación. Implementación de una "Caja de Sugerencias" para revisar y aplicar cambios al XML de forma segura.
- **Logo Embedded**: El logo de la revista ahora se incrusta como Base64 en el HTML generado, eliminando la dependencia de carpetas locales.
- **Optimización**: Eliminación de animaciones intrusivas y mejora en la legibilidad del chat en modo oscuro.

### v0.1 — v0.4 (Alpha)

- Inicio del proyecto.
- Configuración de Gemini CLI.
- Extracción básica de DOCX.
- Primera implementación de transformación a XML JATS.
