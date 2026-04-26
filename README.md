# Transformador XML JATS

> **v0.7.5** · Python 3.9+ · Streamlit · JATS 1.3 / 1.4 (ANSI/NISO Z39.96-2024)

Una herramienta avanzada impulsada por **Inteligencia Artificial Multi-Agente** para convertir documentos de Word (`.docx`) y PDF (`.pdf`) al estándar **JATS XML** validado, diseñada específicamente para el flujo editorial de revistas científicas.

El sistema automatiza el etiquetado semántico completo del artículo, la extracción de metadatos, tablas e imágenes, y la validación contra el estándar **NISO JATS Version 1.4 (ANSI/NISO Z39.96-2024)**, con soporte para múltiples proveedores de IA (Gemini, OpenAI, Anthropic, DeepSeek, Mistral, Groq, Ollama local).

## 🚀 Características Principales

### Conversión y Etiquetado
- **Soporte Multiformato**: Procesa documentos **Word (`.docx`)** y **PDF (`.pdf`)** directamente.
- **Etiquetado Semántico Completo**: La IA aplica el esquema JATS completo — secciones, párrafos, listas, fórmulas, figuras, tablas y referencias — sin alterar el texto original.
- **Extracción de Metadatos con IA**: Identifica y extrae automáticamente título, autores (con afiliaciones), DOI, ORCID, fechas de recepción, aceptación y publicación.
- **Extracción de Tablas**: Las tablas se convierten automáticamente a `<table-wrap>` con `<thead>`/`<tbody>` correctamente estructurados, preservando todas las filas y columnas.
- **Preservación de Texto (Zero-Edit)**: El sistema etiqueta el texto original sin modificarlo, respetando el trabajo de los correctores humanos.

### Arquitectura Multi-Agente
- **Generación Paralela**: Permite generar múltiples versiones del XML simultáneamente usando distintos modelos (Gemini, OpenAI, Claude, etc.) y seleccionar el mejor resultado.
- **Leaderboard DTD**: Panel competitivo que evalúa en tiempo real la precisión estructural de cada XML generado contra el DTD JATS, asignando un porcentaje de exactitud y coronando al modelo ganador.
- **Agente Editorial Experto**: Agente de revisión con rol de editor experto que asiste didácticamente en la corrección de errores JATS antes de la exportación final.
- **Arquitectura LLM-Agnostic**: Soporta **Google Gemini, OpenAI (GPT-4o), Anthropic (Claude 3.5), DeepSeek, Mistral, Groq** y modelos locales offline con **Ollama** o **LM Studio** — sin modificar el código.

### Validación y Calidad
- **Validación JATS 1.3 / 1.4**: Valida contra los estándares **NISO JATS Version 1.3 y 1.4 (ANSI/NISO Z39.96-2024)** usando el DTD oficial empaquetado localmente.
- **Auditoría de Integridad Semántica (Semantic Check)**: Valida heurísticamente la densidad de texto real, bloqueando XMLs con placeholders (`<!-- ... -->`), secciones vacías o contenido insuficiente generados por modelos de baja capacidad o cuota limitada.
- **Corrección Automática Asistida por IA**: Si la validación falla, un agente experto sugiere y aplica correcciones directamente sobre el XML generado, con revisión humana antes de aceptar.
- **Parsing Resiliente**: Recuperación automática ante etiquetas ligeramente malformadas (`recover=True`), permitiendo generar la vista previa HTML incluso con XML imperfecto.

### Salida y Exportación
- **Conversión a HTML5 Responsivo**: Genera HTML autocontenidos con logo incrustado (Base64), modo claro/oscuro, tabla de contenidos interactiva y DOIs clickeables.
- **Vista Previa en Nueva Pestaña**: La previsualización se abre en el navegador con soporte UTF-8 completo y navegación por anclas internas.
- **Descarga Directa**: Botones para descargar el XML JATS final y el HTML generado.

### Gestión y Seguridad
- **Gestión Multi-Proveedor de API Keys**: Las claves se guardan localmente en SQLite con cifrado Fernet; nunca se envían a servidores externos no seleccionados por el usuario.
- **Monitoreo de Tokens**: Panel estadístico con historial de 30 días, alertas al 80 % y 100 % de la cuota gratuita, y métricas por proveedor.
- **Detección de Cuota Agotada**: Cuando se agota la cuota gratuita el sistema detecta el error 429 automáticamente y muestra un banner informativo en la barra lateral.
- **Metadatos de Revista Persistentes**: Título de revista, editorial e ISSN se configuran una sola vez y se inyectan en todas las transformaciones.
- **Interfaz Dual**:
  - **Web UI (Streamlit)**: Interfaz gráfica con arrastrar-y-soltar, revisión de metadatos, chatbot asistente y previsualización en tiempo real.
  - **CLI (Línea de Comandos)**: Para automatización, procesamiento por lotes e integración en pipelines editoriales.

### Privacidad y Seguridad Operativa
- **Cifrado Local de Credenciales**: Las API keys se almacenan en `data/config.db` cifradas con **Fernet** (criptografía simétrica autenticada). Las claves antiguas en Base64 se migran automáticamente a Fernet.
- **Clave Criptográfica Local**: El secreto de cifrado se guarda en `data/.fernet.key` con permisos restringidos (`0600`), y nunca se versiona en Git.
- **Procesamiento por Demanda**: El contenido del documento se procesa en memoria durante la operación; no existe un repositorio persistente de artículos en el proyecto.
- **Envío Controlado a Proveedor Activo**: El texto solo se envía al proveedor IA seleccionado por el usuario (Gemini, OpenAI, Anthropic, etc.) o se procesa localmente con Ollama/LM Studio.
- **Aislamiento Local Opcional**: Con modelos locales (Ollama/LM Studio), los datos no salen del entorno de ejecución.
- **Mínimo Privilegio Operativo**: La carpeta `data/` está excluida por `.gitignore`; no se deben subir bases de datos, logs ni capturas con datos sensibles.

## 🛠️ Requisitos del Sistema

| Requisito | Mínimo | Recomendado |
|-----------|--------|-------------|
| Sistema Operativo | Windows 10, macOS 11, Ubuntu 20.04 | macOS 13+ / Ubuntu 22.04 |
| Python | 3.9 | 3.11+ |
| RAM | 4 GB | 8 GB |
| Almacenamiento | 500 MB | 1 GB |
| Conexión a Internet | Requerida (para proveedores cloud) | — |

**API Key requerida** de al menos uno de los proveedores soportados (Gemini, OpenAI, Anthropic, DeepSeek, Mistral, Groq) o una instalación local de **[Ollama](https://ollama.com)** ejecutándose en `localhost:11434`.

## 📦 Instalación

### Instalación Estándar

1. **Clonar el repositorio**:

    ```bash
    git clone https://github.com/iCristian/XML-JATS.git
    cd XML-JATS
    ```

2. **Crear un entorno virtual** (recomendado para aislar dependencias):

    ```bash
    python -m venv .venv
    # Activar:
    # Windows PowerShell: .venv\Scripts\Activate.ps1
    # Windows CMD:        .venv\Scripts\activate.bat
    # macOS/Linux:        source .venv/bin/activate
    ```

3. **Instalar dependencias**:

    ```bash
    pip install -r requirements.txt
    ```

4. **Configurar la API Key** (elige una opción):

    **Opción A — Desde la interfaz web (recomendado):**
    Abre la aplicación y navega a **"⚙️ API y Tokens"** en el menú lateral. Selecciona tu proveedor de IA (Gemini, OpenAI, Anthropic, etc.), pega tu clave y presiona **"💾 Guardar"**. La clave se almacena en `data/config.db` (excluido de Git) con cifrado Fernet.

    **Opción B — Variable de entorno:**

    ```bash
    # Google Gemini
    export GEMINI_API_KEY="AIza..."

    # OpenAI
    export OPENAI_API_KEY="sk-..."

    # Anthropic
    export ANTHROPIC_API_KEY="sk-ant-..."
    ```

    > **Modelos locales con Ollama:** No requieren API Key. Instala [Ollama](https://ollama.com), descarga un modelo (`ollama pull llama3`) y asegúrate de que el servicio esté corriendo. El sistema lo detecta automáticamente en `http://localhost:11434`.

    > **Nota sobre cuota pagada (Gemini):** Si tu cuenta de Google AI tiene facturación habilitada en Google Cloud, la misma clave funciona automáticamente en el tier de pago una vez agotada la cuota gratuita. No se necesita ninguna clave adicional.

## 📖 Uso

### Interfaz Web (Recomendado)

```bash
streamlit run streamlit_app.py
# o usando el script helper:
./run_app.sh
```

Abre tu navegador en `http://localhost:8501`. El flujo de trabajo es:

1. **Configurar** tu API Key en **"⚙️ API y Tokens"**.
2. **Cargar** un archivo `.docx` o `.pdf` en el **Transformador**.
3. **Revisar** los metadatos extraídos por la IA (título, autores, DOI, etc.).
4. **Generar** el XML JATS — opcionalmente con múltiples modelos en paralelo.
5. **Validar** el XML contra el DTD JATS oficial y corregir si es necesario.
6. **Descargar** el XML validado y/o el HTML para publicación web.

### Línea de Comandos (CLI)

Para usuarios avanzados o integración en pipelines editoriales.

**Transformación (Word → XML JATS):**

```bash
python -m modules.transformer entrada.docx salida.xml
```

**Conversión (XML JATS → HTML5):**

```bash
python -m modules.xml_html entrada.xml salida.html
```

**Verificar modelos disponibles:**

```bash
python check_models.py
```

## 📂 Estructura del Proyecto

```text
XML-JATS/
├── streamlit_app.py          # Punto de entrada web (Streamlit multi-página)
├── run_app.sh                # Script helper para lanzar la app
├── requirements.txt          # Dependencias Python (pinned)
├── README.md                 # Este archivo
├── RESUME.md                 # Resumen técnico del proyecto
├── CONTRIBUTING.md           # Guía de contribución
│
├── modules/                  # Backend — independiente de la UI
│   ├── __init__.py
│   ├── transformer.py        # Núcleo de conversión DOCX/PDF → XML JATS
│   ├── metadata_processor.py # Extracción de metadatos con IA
│   ├── correction.py         # Corrección asistida por IA (preserva texto original)
│   ├── prompts.py            # Repositorio centralizado de prompts para la IA
│   ├── xml_html.py           # Conversión XML JATS → HTML5 responsivo
│   ├── config_store.py       # Persistencia SQLite (API keys, tokens, métricas)
│   ├── llm_provider.py       # Abstracción multi-proveedor (LLMProvider)
│   ├── convert_images.py     # Utilidad de extracción/conversión de imágenes
│   └── dtd/                  # DTDs JATS empaquetados para validación offline
│       ├── JATS-Publishing-1-3-MathML3-DTD/
│       ├── JATS-Publishing-1-4-MathML3-DTD/  # ← DTD por defecto
│       └── download_jats14.py  # Helper para descargar DTD 1.4 desde NCBI
│
├── views/                    # Frontend — vistas Streamlit
│   ├── transformador.py      # Vista principal: carga, metadatos, generación, validación
│   ├── configuracion.py      # Gestión de API keys, cuotas y datos de revista
│   ├── manual_usuario.py     # Manual de usuario interactivo con pasos y FAQ
│   ├── documentacion.py      # Documentación técnica (README, CONTRIBUTING, RESUME)
│   └── creditos.py           # Créditos, privacidad y licencias
│
├── resources/                # Recursos estáticos
│   ├── UV_blanco.png         # Logo UV (fondo blanco)
│   ├── UV_color.png          # Logo UV (color)
│   ├── logo.png              # Logo principal
│   ├── logo_transparent.png  # Logo transparente
│   └── manual_images/        # Capturas de pantalla del manual de usuario
│
└── data/                     # Datos locales — excluidos de Git
    └── config.db             # Base de datos SQLite (API keys, tokens, métricas)
```

### Descripción de Módulos Backend

| Módulo | Responsabilidad |
|--------|----------------|
| `transformer.py` | Orquesta el flujo completo: extrae texto/tablas/imágenes del DOCX, invoca la IA para generar XML JATS, verifica completitud semántica y retorna el resultado. Usa `tenacity` para reintentos con backoff exponencial ante errores 429. |
| `metadata_processor.py` | Extrae metadatos (título, autores, DOI, ORCID, afiliaciones, fechas) usando IA. Aplica `_normalize_metadata()` para corregir variaciones en las claves JSON devueltas por el modelo. |
| `correction.py` | Agente de corrección que recibe el XML con errores DTD y genera una versión corregida preservando el texto original. Desacoplado de Streamlit. |
| `prompts.py` | Repositorio centralizado de todos los prompts maestros. Ningún otro módulo hardcodea instrucciones para la IA. |
| `xml_html.py` | Convierte XML JATS a HTML5 responsivo con logo incrustado (Base64), modo oscuro/claro, tabla de contenidos, DOIs clickeables y referencias bibliográficas completas. |
| `config_store.py` | Gestión de persistencia mediante SQLite: guarda/carga API keys (ofuscadas), registra uso de tokens y métricas históricas. |
| `llm_provider.py` | Clase abstracta `LLMProvider` con implementaciones para Gemini, OpenAI, Anthropic, DeepSeek, Mistral, Groq, Ollama y LM Studio. Punto de extensión para nuevos proveedores. |

## 🔄 Flujo de Datos

```
Usuario sube DOCX/PDF
        │
        ▼
transformer.extraer_contenido_estructurado()
   ├── python-docx / pdfplumber  → texto plano + tablas + imágenes
   └── (tablas renderizadas como markdown para el prompt)
        │
        ▼
metadata_processor.MetadataExtractor
   └── LLMProvider.generate() → JSON con título, autores, DOI, fechas
        │
        ▼
[Revisión humana y chatbot asistente en UI]
        │
        ▼
transformer.generar_xml_jats()  [opcionalmente en paralelo con múltiples modelos]
   └── LLMProvider.generate() → XML JATS candidato
        │
        ▼
Auditoría de Completitud Semántica (verificar_completitud_xml)
   ├── Detecta placeholders (<!-- ... -->)
   ├── Valida densidad de texto vs. original
   └── Puntúa cada candidato
        │
        ▼
Leaderboard: selección del XML con mayor puntaje DTD
        │
        ├── [Si errores] correction.corregir_xml()
        │       └── LLMProvider.generate() → XML corregido
        │
        ▼
xml_html.build_html() → HTML5 autocontenido con DOIs clickeables
        │
        ▼
Descarga: XML + HTML
```

## 🤖 Proveedores de IA Soportados

| Proveedor | Modelos por Defecto | Tier Gratuito | Variable de Entorno |
|-----------|---------------------|---------------|---------------------|
| **Google Gemini** | gemini-2.5-flash, gemini-2.5-pro, gemini-2.0-flash | ✅ Sí (RPD limitado) | `GEMINI_API_KEY` |
| **OpenAI** | gpt-4o, gpt-4o-mini, gpt-4-turbo | ❌ Pay-as-you-go | `OPENAI_API_KEY` |
| **Anthropic** | claude-3-5-sonnet, claude-3-haiku | ❌ Pay-as-you-go | `ANTHROPIC_API_KEY` |
| **DeepSeek** | deepseek-chat, deepseek-coder | ✅ Limitado | `DEEPSEEK_API_KEY` |
| **Mistral** | mistral-large, mistral-small | ✅ Limitado | `MISTRAL_API_KEY` |
| **Groq** | llama3-70b, mixtral-8x7b | ✅ Sí | `GROQ_API_KEY` |
| **Ollama** (local) | llama3, qwen2.5, etc. | ✅ Sin límites | — (local) |
| **LM Studio** (local) | cualquier modelo GGUF | ✅ Sin límites | — (local) |

### Cuotas Gemini (Tier Gratuito)

| Modelo | Req/día | Tokens/min | Req/min |
|--------|---------|------------|---------|
| gemini-2.5-flash | 500 | 250 000 | 10 |
| gemini-2.5-pro | 25 | 32 000 | 5 |
| gemini-2.0-flash | 1 500 | 1 000 000 | 15 |

> Una vez agotada la cuota gratuita, la misma clave funciona en **Pay-as-you-go** si la cuenta tiene facturación habilitada en Google Cloud.

## ⚙️ Variables de Entorno

| Variable | Proveedor | Descripción |
|----------|-----------|-------------|
| `GEMINI_API_KEY` | Google | API Key de Google Gemini |
| `OPENAI_API_KEY` | OpenAI | API Key de OpenAI |
| `ANTHROPIC_API_KEY` | Anthropic | API Key de Anthropic |
| `DEEPSEEK_API_KEY` | DeepSeek | API Key de DeepSeek |
| `MISTRAL_API_KEY` | Mistral | API Key de Mistral |
| `GROQ_API_KEY` | Groq | API Key de Groq |

Las variables de entorno funcionan como **fallback** si no hay clave guardada en `data/config.db`. Si ambas existen, prevalece la guardada en la base de datos.

## 🔧 Solución de Problemas

### Error: `ModuleNotFoundError`
```bash
# Asegúrate de tener el entorno virtual activado
source .venv/bin/activate
pip install -r requirements.txt
```

### Error: `SSL: CERTIFICATE_VERIFY_FAILED` (macOS)
```bash
# Instala los certificados de Python
/Applications/Python\ 3.x/Install\ Certificates.command
```
El sistema también tiene un mecanismo de fallback que ignora errores SSL al descargar el DTD JATS.

### Error 429: Cuota Agotada
- Espera al día siguiente (los límites diarios se renuevan a las 00:00 UTC).
- Cambia a un modelo con más cuota (ej. `gemini-2.0-flash` tiene 1500 RPD).
- Configura otro proveedor (OpenAI, Anthropic, etc.) como alternativa.
- Activa facturación en Google Cloud para usar el tier Pay-as-you-go con la misma clave.

### El XML generado contiene placeholders `<!-- ... -->`
- El sistema detecta esto automáticamente en la Auditoría de Completitud.
- Si igual ocurre, usa el botón **"🔧 Intentar Solucionar con IA"** en la sección de Validación.
- Si persiste, prueba con un modelo de mayor capacidad (ej. `gemini-2.5-pro` en lugar de `flash`).

### Ollama no conecta
```bash
# Verificar que el servicio esté activo
ollama list
# Si no está corriendo, iniciarlo manualmente
ollama serve
```

### Las imágenes del PDF no se extraen
Los PDFs con imágenes vectoriales o con protección DRM pueden no permitir la extracción. Usa el archivo Word original si está disponible.

## 🔒 Protección de Privacidad

Este proyecto está diseñado para reducir exposición de datos en el flujo editorial:

1. **Persistencia mínima**: solo se almacenan configuración, métricas y claves cifradas en `data/config.db`; los artículos no se guardan como dataset interno.
2. **Custodia local de credenciales**: la API key se cifra con Fernet antes de persistirla y se muestra enmascarada en la interfaz.
3. **Control de destino de datos**: el procesamiento IA ocurre exclusivamente con el proveedor activo configurado por el usuario.
4. **Modo local recomendado para datos sensibles**: para documentos de alto riesgo, use Ollama/LM Studio y políticas institucionales de anonimización previa.

## 🛡️ Seguridad

- **Reporte responsable de vulnerabilidades**: contactar primero a [cristian.carreno@uv.cl](mailto:cristian.carreno@uv.cl) antes de abrir issues públicos.
- **Higiene de secretos**: prohibido subir API keys, `data/config.db`, `data/.fernet.key` o trazas con datos de documentos.
- **Dependencias**: toda nueva librería debe revisarse por CVEs y mantenerse fijada en `requirements.txt`.
- **Transporte**: las integraciones cloud se realizan sobre HTTPS provisto por los SDKs oficiales.

## 🤝 Créditos

Desarrollado por **Cristian Carreño León**\
Escuela de Obstetricia y Puericultura\
Facultad de Medicina\
Universidad de Valparaíso, Chile.\
✉️ [cristian.carreno@uv.cl](mailto:cristian.carreno@uv.cl)

Desarrollado para la **Universidad de Valparaíso** con el objetivo de optimizar los procesos de publicación científica.

### Tecnologías Utilizadas

| Tecnología | Versión | Uso |
| --- | --- | --- |
| Python | 3.9+ | Lenguaje base |
| Streamlit | 1.51+ | Framework de interfaz web |
| Google Gemini | 2.5-flash | LLM principal para etiquetado |
| lxml | 6.0+ | Procesamiento y validación XML/HTML |
| python-docx | 1.2+ | Extracción de contenido Word |
| pdfplumber | 0.10+ | Extracción de texto desde PDF |
| tenacity | 9.1+ | Reintentos robustos con backoff exponencial |
| FPDF2 | — | Generación del manual en PDF |
| SQLite | — | Persistencia de API keys y métricas |
| JATS | 1.3 / 1.4 | Estándar ANSI/NISO Z39.96-2024 |

## 📄 Licencia

Este software es de uso exclusivo para la **Universidad de Valparaíso**. Todos los derechos reservados.

El código fuente y la documentación contenidos en este repositorio son propiedad intelectual de la Universidad de Valparaíso y su autor. Queda prohibida su reproducción, distribución o modificación sin autorización expresa.

El uso de servicios de terceros (Google, OpenAI, Anthropic, DeepSeek, Mistral, Groq, Ollama o LM Studio) está sujeto adicionalmente a las condiciones de licenciamiento y privacidad de cada proveedor.

Para consultas sobre licenciamiento o uso, contactar a: [cristian.carreno@uv.cl](mailto:cristian.carreno@uv.cl)

## 📅 Historial de Versiones (Changelog)

### v0.7.5 — Auditoría Semántica y Robustez de Infraestructura

- **Verificación de Completitud Semántica**: Nueva capa de validación heurística que detecta omisiones de texto, placeholders de IA e insuficiencia de densidad de datos, garantizando la integridad de la investigación maquetada.
- **Auto-vuelo de Ollama (macOS)**: Implementación de auto-detección y lanzamiento del servicio local Ollama. Si el servicio no responde, el sistema intenta levantarlo automáticamente en entornos macOS para garantizar disponibilidad inmediata.
- **Etiquetado de Origen [LOCAL/CLOUD]**: Identificación clara de modelos en el selector, diferenciando entre inferencia local (Ollama) y proveedores cloud, con monitoreo de estado en tiempo real.
- **Refuerzo de Prompt "Zero-Placeholder"**: Instrucciones maestras rediseñadas para prohibir estrictamente el uso de comentarios XML como marcadores de posición, forzando la transcripción íntegra del cuerpo y referencias.

### v0.7.0 — Arquitectura Multi-Agente y Multi-Model (Vendor-Agnostic)

- **Generación Paralela Multi-Agente**: Permite generar múltiples versiones de XML simultáneamente utilizando modelos distintos (Gemini, OpenAI, Anthropic, etc.), evaluando su rendimiento en tiempo real.
- **Leaderboard y Puntuación DTD**: Implementación de un panel competitivo que evalúa automáticamente la precisión estructural de cada XML generado contra las estrictas reglas del DTD JATS. Genera un porcentaje de exactitud y corona a un modelo ganador.
- **Validador Editorial AI (Agente Experto)**: Incorpora un agente de revision con rol de Editor Experto que asiste con explicaciones didácticas para subsanar los posibles fallos JATS del XML final, de forma detallada antes de su exportación.
- **Soporte Multi-Proveedor (LLM-Agnostic)**: El Transformador XML abandona el confinamiento a Gemini e introduce una robusta arquitectura con soporte nativo para **OpenAI**, **Anthropic (Claude)**, **DeepSeek**, **Mistral**, **Groq** e inferencia local offline apoyada en **Ollama** (Llama3, Qwen, etc).
- **Abstracción Multi-Proveedor**: Un nuevo diseño estructural (`modules/llm_provider.py`) introduce la clase abstracta `LLMProvider` permitiendo la fácil y limpia integración de nuevos ecosistemas y API providers en el futuro.
- **Selectificador y Dashboard Híbrido**: El menú de *Configuración* fue reconstruido para permitir el ingreso de la API Key particular a cada servicio con enmascaramiento Base64, además de proveer atajos URL para expedir las Key gratuitas de todos los competidores en el mercado.
- **Cuotas Multi-Cuenta y Fallbacks**: Rebalanceo interno del monitoreo de peticiones e historial contable, el token-meter reportará fidedignamente según el proveedor utilizado.

### v0.68 — Metadatos de Revista Persistentes, Selectores DTD y Corrección SSL

- **Metadatos de Revista Persistentes**: Nueva sección en configuración para guardar datos estructurales de la publicación (título de la revista, editorial, ISSN), los cuales se inyectan automáticamente en cada nuevo flujo ahorrando escritura manual repetitiva.
- **Selector de Versión JATS Dinámico**: El usuario puede escoger la versión objetivo del estándar (1.3 o 1.4) en la misma página de configuración. El transformador inyectará condicionalmente la declaración `<!DOCTYPE>` y validará contra el DTD JATS oficial preciso usando rutas dependientes del contexto.
- **Validación SSL Opt-out Local**: Se resolvió un bug prevalente en macOS (`SSL: CERTIFICATE_VERIFY_FAILED`) ignorando programáticamente fallos SSL intermitentes al hacer el fetch oficial del DTD JATS a NLM. Esto asegura que la herramienta arranque exitosamente en cualquier estado de certificados Python.
- **UI Responsiva y Textos Justificados**: Mejorada radicalmente la integración HTML CSS para IFrames como OJS (`width: 100%`) y se aseguró uniformidad con justificación de texto automática en artículos.

### v0.67 — Unificación a Clave API Única y Detección de Cuota

- **Una sola API Key**: Eliminado el concepto de "Key Pro" separada. El sistema ahora usa una única clave de API. Google gestiona internamente el paso de tier gratuito a tier de pago cuando la cuenta tiene **facturación habilitada en Google Cloud**.
- **Detección de Cuota Agotada**: Cuando `transformer.py` o `correction.py` reciben un error 429 tras reintentos, retornan `{'quota_exceeded': True}` en lugar de intentar cambiar de clave. La UI muestra automáticamente un banner `💳 Cuota gratuita agotada — usando tier de pago` en la barra lateral.
- **Tabla de Cuotas Simplificada**: La sección **"⚙️ Configuración"** reemplaza las columnas "Pro" de la tabla por una única columna **"Tras cuota libre: Pay-as-you-go"**. Se añade un panel informativo explicando el modelo de una sola clave con enlace a [Google AI pricing](https://ai.google.dev/pricing).
- **Funciones Obsoletas Marcadas**: `save_api_key_pro`, `load_api_key_pro` y `delete_api_key_pro` en `config_store.py` emiten `DeprecationWarning` si se llaman. Se mantienen solo para compatibilidad con bases de datos antiguas.
- **Backend Limpio**: `transformer.py` y `correction.py` ya no aceptan el parámetro `api_key_pro` en sus firmas. Args residuales se absorben con `**_kwargs`.

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
