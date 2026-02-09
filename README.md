# Transformador XML JATS (JATS XML Transformer) - v0.6

Una herramienta avanzada impulsada por Inteligencia Artificial para convertir documentos de Word (`.docx`) a formato **JATS XML** validado, diseñada específicamente para el flujo editorial de revistas científicas.

Esta aplicación automatiza el proceso de etiquetado semántico, extracción de tablas e imágenes (en desarrollo), y validación contra el estándar **NISO JATS Version 1.4 (ANSI/NISO Z39.96-2024)**.

## 🚀 Características Principales

- **Conversión Inteligente**: Utiliza LLMs (Google Gemini) para interpretar la estructura lógica del documento.
- **Soporte Multiformato**: Procesa documentos **Word (`.docx`)** y **PDF (`.pdf`)**.
- **Extracción de Metadatos**: Identifica y extrae automáticamente metadatos clave (título, autores, DOI, fechas).
- **Revisión Interactiva**: Permite editar metadatos y dialogar con un chatbot para completar información faltante antes de la generación.
- **Validación JATS 1.4**: Valida contra el último estándar **NISO JATS Version 1.4 (ANSI/NISO Z39.96-2024)**.
- **HTML Autocontenido**: Genera archivos HTML con el logo incrustado (Base64), listos para publicar.

- **Conversión Inteligente**: Utiliza LLMs (Google Gemini) para interpretar la estructura lógica del documento y generar etiquetas JATS precisas.
- **Extracción de Contenido**: Detecta y extrae imágenes y tablas automáticamente desde el archivo Word.
- **Validación Integrada**: Valida el XML generado contra el DTD oficial JATS 1.4 con MathML3.
- **Interfaz Dual**:
  - **CLI (Línea de Comandos)**: Para automatización y procesamiento por lotes.
  - **Web UI (Streamlit)**: Interfaz gráfica amigable para arrastrar y soltar archivos, editar contenido extraído y previsualizar resultados.
- **Conversión a HTML**: Genera una vista previa en HTML del artículo para su revisión inmediata.

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

    *Nota: Si no tienes un `requirements.txt`, las dependencias principales son: `python-docx`, `lxml`, `streamlit`, `google-generativeai` (o la herramienta CLI correspondiente).*

4. **Configurar la API Key de Gemini**:
    Asegúrate de que la CLI de `gemini` esté configurada en tu PATH o system environment variables.

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
  - `transformer.py`: Núcleo de la lógica de conversión. Maneja la lectura del Word, construcción del prompt para IA y validación XML.
  - `correction.py`: Módulo para la corrección asistida por IA.
  - `xml_html.py`: Utilidad para convertir el XML JATS resultante a HTML visualizable.
- `views/`: Vistas de la interfaz gráfica.
- `JATS-Publishing-1-3-MathML3-DTD/`: Archivos DTD locales para validación offline (se descargan si no existen).
- `imagenes_extraidas/`: Directorio temporal donde se guardan las imágenes extraídas del documento Word.

## 🤝 Créditos

Desarrollado por **Cristian Carreño León**\
Escuela de Obstetricia y Puericultura\
Facultad de Medicina\
Universidad de Valparaíso, Chile.

Desarrollado para la **Universidad de Valparaíso** con el objetivo de optimizar los procesos de publicación científica.

## 📅 Historial de Versiones (Changelog)

### v0.6 - Actualización JATS 1.4 + Metadatos

- **Estándar JATS 1.4**: Actualización completa del motor de validación y prompts al estándar ANSI/NISO Z39.96-2024.
- **Soporte PDF**: Ahora es posible cargar archivos `.pdf` para extracción de texto y metadatos.
- **Módulo de Metadatos**: Nueva lógica de extracción y validación de metadatos (título, autores, DOI, fecha).
- **UI de Revisión**: Nueva sección en la interfaz para editar metadatos y chatbot asistente para completar información faltante.

### v0.5 (Beta)

- **Mejoras de UI**: Navegación por pestañas con botones de avance automático.
- **Corrección Interactiva**: Nuevo chatbot que permite dialogar con la IA para resolver errores de validación. Implementación de una "Caja de Sugerencias" para revisar y aplicar cambios al XML de forma segura.
- **Logo Embedded**: El logo de la revista ahora se incrusta como Base64 en el HTML generado, eliminando la dependencia de carpetas locales.
- **Optimización**: Eliminación de animaciones intrusivas y mejora en la legibilidad del chat en modo oscuro.

### v0.1 - v0.4 (Alpha)

- Inicio del proyecto.
- Configuración de Gemini CLI.
- Extracción básica de DOCX.
- Primera implementación de transformación a XML JATS.
