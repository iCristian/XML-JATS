# XML-JATS — Resumen Técnico del Proyecto

## Propósito

**XML-JATS-Transformer** es una herramienta especializada para la **conversión automática de documentos académicos** (Word/PDF) al formato **JATS XML** (Journal Article Tag Suite), el estándar internacional utilizado por revistas científicas para indexación, preservación digital e interoperabilidad con plataformas como OJS, PubMed Central y SciELO.

Desarrollado para automatizar el flujo editorial de la Universidad de Valparaíso, el sistema emplea una arquitectura Multi-Agente con soporte para múltiples proveedores de LLM (Google Gemini, OpenAI, Anthropic, DeepSeek, Mistral, Groq, Ollama local).

---

## Arquitectura

```text
streamlit_app.py (Punto de Entrada)
       │
       ├── views/transformador.py ─────────────────────┐
       │         │                                      │
       │         ├── Extracción DOCX/PDF                │
       │         ├── Revisión de Metadatos + Chatbot    │
       │         ├── Generación XML (Multi-Agente)      │
       │         ├── Leaderboard + Puntuación DTD       │
       │         ├── Corrección Asistida por IA         │
       │         └── Conversión XML → HTML              │
       │                                                │
       ├── views/configuracion.py ───────────────────── │
       │         ├── Gestión Multi-Proveedor API Keys   │
       │         ├── Panel de Cuotas por Modelo         │
       │         └── Datos Persistentes de Revista      │
       │                                                │
       ├── views/manual_usuario.py                      │
       ├── views/documentacion.py                       │
       └── views/creditos.py                            │
                                                        │
              ┌─────────────────────────────────────────┘
              │
              ▼
       modules/                     (Backend — sin dependencias de UI)
       ├── transformer.py           (Núcleo: DOCX/PDF → XML JATS)
       ├── metadata_processor.py    (Extracción metadatos con IA)
       ├── correction.py            (Corrección XML asistida por IA)
       ├── prompts.py               (Repositorio centralizado de prompts)
       ├── xml_html.py              (XML JATS → HTML5 responsivo)
       ├── config_store.py          (Persistencia SQLite — API keys + métricas)
       └── llm_provider.py          (Abstracción Multi-Proveedor)
              │
              ▼
       modules/dtd/                 (Validación offline)
       └── JATS-Publishing-1-3-MathML3-DTD/
```

---

## Tecnologías

| Tecnología | Versión | Propósito |
| ---------- | ------- | --------- |
| **Python** | 3.9+ | Lenguaje base |
| **Streamlit** | 1.51.0 | Framework de interfaz web multi-página |
| **Google Gemini** | 2.5-flash | Modelo LLM principal para etiquetado inteligente |
| **OpenAI** | ≥1.30 | Proveedor alternativo (GPT-4o, etc.) |
| **Anthropic** | ≥0.28 | Proveedor alternativo (Claude 3.5) |
| **lxml** | 6.0.2 | Parsing, validación DTD y transformación XML/HTML |
| **python-docx** | 1.2.0 | Extracción de contenido y tablas de documentos Word |
| **pdfplumber** | 0.10.4 | Extracción de texto desde PDFs |
| **tenacity** | 9.1.2 | Reintentos robustos con backoff exponencial (error 429) |
| **SQLite** | — | Persistencia de API keys (ofuscadas) y métricas de tokens |
| **FPDF2** | — | Generación del manual de usuario en PDF |

---

## Estructura de Directorios

```text
XML-JATS/
├── streamlit_app.py          # Punto de entrada principal
├── run_app.sh                # Script de ejecución
├── requirements.txt          # Dependencias Python (pinned)
├── README.md                 # Documentación principal
├── RESUME.md                 # Este archivo — resumen técnico
├── CONTRIBUTING.md           # Guía de contribución
│
├── modules/                  # Backend — Módulos Python
│   ├── transformer.py        # Núcleo de conversión (DOCX/PDF → XML JATS)
│   ├── metadata_processor.py # Extracción de metadatos con IA
│   ├── correction.py         # Corrección con IA (preserva texto original)
│   ├── prompts.py            # Prompts centralizados (Zero-Placeholder)
│   ├── xml_html.py           # Conversión XML JATS → HTML5
│   ├── config_store.py       # Persistencia SQLite (multi-proveedor)
│   ├── llm_provider.py       # Abstracción LLMProvider + PROVIDER_REGISTRY
│   ├── convert_images.py     # Utilidad de conversión de imágenes
│   └── dtd/                  # DTD JATS local para validación offline
│       └── JATS-Publishing-1-3-MathML3-DTD/
│
├── views/                    # Frontend — Vistas Streamlit
│   ├── transformador.py      # Vista principal de transformación
│   ├── configuracion.py      # Configuración API keys, cuotas y revista
│   ├── manual_usuario.py     # Manual de usuario interactivo
│   ├── documentacion.py      # Documentación técnica
│   └── creditos.py           # Créditos y política de privacidad
│
└── resources/                # Recursos estáticos
    ├── UV_blanco.png         # Logo UV (fondo blanco)
    ├── UV_color.png          # Logo UV (color, usado en PDF)
    ├── logo.png              # Logo principal
    ├── logo_transparent.png  # Logo con transparencia
    └── manual_images/        # Capturas de pantalla del manual
```

---

## Flujo de Datos

1. **Carga**: El usuario sube un DOCX o PDF vía la UI de Streamlit.
2. **Extracción**: `transformer.extraer_contenido_estructurado()` extrae texto plano, tablas (en formato markdown para el prompt) e imágenes usando `python-docx` o `pdfplumber`.
3. **Metadatos**: `metadata_processor.MetadataExtractor` invoca la IA para extraer título, autores, DOI, ORCID, afiliaciones y fechas en formato JSON estructurado. `_normalize_metadata()` corrige variaciones en las claves.
4. **Revisión Humana**: La UI muestra los metadatos extraídos en campos editables. Un chatbot asistente solicita información faltante (DOI y fecha son obligatorios).
5. **Generación Paralela (Leaderboard)**: `transformer.generar_xml_jats()` invoca `llm_provider.LLMProvider.generate()` con el prompt maestro de `prompts.py`. Si el usuario seleccionó múltiples modelos, la generación se ejecuta en paralelo y los resultados se ordenan por puntaje DTD.
6. **Auditoría de Completitud Semántica**: `verificar_completitud_xml()` detecta placeholders, secciones vacías y baja densidad de texto. El XML que no pasa la auditoría se descarta automáticamente.
7. **Validación DTD**: El XML candidato se valida contra el DTD JATS 1.3 o 1.4 usando `lxml.etree.DTD`. Los errores se presentan en la UI con sugerencias de corrección.
8. **Corrección (Agente Editorial)**: Si hay errores DTD o la auditoría marca inconsistencias, `correction.corregir_xml()` invoca la IA con el XML erróneo y el informe de errores para obtener una versión corregida, preservando el texto original.
9. **Generación HTML**: `xml_html.build_html()` convierte el XML final a HTML5 responsivo con logo incrustado, tabla de contenidos interactiva y DOIs clickeables.
10. **Exportación**: El usuario descarga el XML JATS validado y/o el HTML generado.

---

## Proveedores de IA Soportados

| Proveedor | ID Interno | Tier Gratuito | Modelos por Defecto |
| --------- | ---------- | ------------- | ------------------- |
| Google Gemini | `gemini` | ✅ Sí (RPD limitado) | gemini-2.5-flash, gemini-2.5-pro |
| OpenAI | `openai` | ❌ Pay-as-you-go | gpt-4o, gpt-4o-mini |
| Anthropic | `anthropic` | ❌ Pay-as-you-go | claude-3-5-sonnet, claude-3-haiku |
| DeepSeek | `deepseek` | ✅ Limitado | deepseek-chat |
| Mistral | `mistral` | ✅ Limitado | mistral-large, mistral-small |
| Groq | `groq` | ✅ Sí | llama3-70b, mixtral-8x7b |
| Ollama (local) | `ollama` | ✅ Sin límites | llama3, qwen2.5, etc. |
| LM Studio (local) | `lmstudio` | ✅ Sin límites | Cualquier modelo GGUF |

---

## Cuotas Gemini (Tier Gratuito)

| Modelo | Req/día (RPD) | Tokens/min (TPM) | Uso recomendado |
| ------ | ------------- | ---------------- | --------------- |
| gemini-2.5-flash | 500 | 250 000 | Recomendado — mejor balance calidad/cuota |
| gemini-2.5-pro | 25 | 32 000 | Máxima calidad para artículos complejos |
| gemini-2.0-flash | 1 500 | 1 000 000 | Alto volumen de procesamiento |

> Una vez agotada la cuota gratuita, la misma clave funciona en **Pay-as-you-go** si la cuenta tiene facturación habilitada en Google Cloud. No se requiere una segunda clave.

---

## Gestión de API Keys y Cuota

- **Multi-proveedor**: Cada proveedor tiene su propia API Key almacenada en `data/config.db` con cifrado Fernet.
- **Proveedor activo**: Se configura en la UI y se persiste en `config_store`. El transformador usa el proveedor activo automáticamente.
- **Cuota agotada**: `transformer.py` retorna `{'quota_exceeded': True}` ante un error 429 persistente. La UI muestra el banner `💳 Cuota gratuita agotada — usando tier de pago` en la barra lateral.
- **Seguridad**: Las claves se almacenan cifradas en `data/config.db` (excluido de Git) y solo se muestran enmascaradas en la UI (`AIza••••••xY4Z`).
- **Variables de entorno como fallback**: Si no hay clave en `config.db`, el sistema intenta cargar desde la variable de entorno correspondiente (ej. `GEMINI_API_KEY`).

---

## Privacidad y Seguridad

- **Procesamiento por demanda**: El contenido del artículo se procesa durante el flujo de transformación; la aplicación no implementa un repositorio persistente de artículos.
- **Custodia local de secretos**: Las API keys se cifran con Fernet y la clave criptográfica se guarda en `data/.fernet.key` con permisos restringidos (`0600`).
- **Ruta de datos controlada**: El texto se envía solo al proveedor IA activo definido por el usuario o se ejecuta de forma local con Ollama/LM Studio.
- **Defensa de configuración**: `data/` está excluida por `.gitignore`, evitando versionado accidental de credenciales y métricas.
- **Reporte responsable**: Vulnerabilidades de seguridad deben comunicarse por canal privado antes de divulgación pública.

---

## Variables de Entorno

| Variable | Proveedor | Descripción |
| -------- | --------- | ----------- |
| `GEMINI_API_KEY` | Google Gemini | API Key principal (única variable requerida para uso básico) |
| `OPENAI_API_KEY` | OpenAI | API Key de OpenAI |
| `ANTHROPIC_API_KEY` | Anthropic | API Key de Anthropic |
| `DEEPSEEK_API_KEY` | DeepSeek | API Key de DeepSeek |
| `MISTRAL_API_KEY` | Mistral | API Key de Mistral |
| `GROQ_API_KEY` | Groq | API Key de Groq |

---

## Comandos Útiles

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar aplicación web
streamlit run streamlit_app.py
# o
./run_app.sh

# Uso por CLI (transformación)
python -m modules.transformer entrada.docx salida.xml

# Uso por CLI (conversión XML → HTML)
python -m modules.xml_html entrada.xml salida.html

# Verificar modelos disponibles
python check_models.py

# Validar sintaxis de todos los módulos
for f in modules/*.py views/*.py; do python -m py_compile "$f" && echo "OK: $f"; done
```

---

## Estado del Proyecto

- **Versión actual:** 0.7.5
- **Framework UI:** Streamlit 1.51+ (multi-página)
- **Arquitectura LLM:** LLM-Agnostic (Gemini, OpenAI, Anthropic, DeepSeek, Mistral, Groq, Ollama, LM Studio)
- **Validación:** DTD JATS 1.3 / 1.4 con scoring automatizado y Auditoría de Integridad Semántica (Zero-Placeholder)
- **Max output tokens:** 65 536 (soporta artículos extensos sin truncamiento)

---

## Archivos de Configuración

| Archivo | Propósito |
| ------- | --------- |
| `data/config.db` | Base de datos SQLite local (API keys ofuscadas, proveedor activo, tokens, métricas) |
| `.gitignore` | Exclusiones de Git (`data/`, `.venv/`, `__pycache__/`, etc.) |
| `requirements.txt` | Dependencias Python con versiones pinned para reproducibilidad |
| `run_app.sh` | Script de lanzamiento con activación automática del entorno virtual |

