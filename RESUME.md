# XML-JATS-2 - Resumen del Proyecto

## Propósito

**XML-JATS-Transformer** es una herramienta especializada para la **conversión automática de documentos académicos** (Word/PDF) al formato **JATS XML** (Journal Article Tag Suite), el estándar utilizado por revistas científicas para indexación y preservación digital.

Desarrollado para automatizar el flujo editorial de la Universidad de Valparaíso.

---

## Arquitectura

```
streamlit_app.py (Entrada)
       │
       ├── views/transformador.py ────┐
       │         │                    │
       │         ├── Extracción DOCX  │
       │         ├── Metadatos IA      │
       │         ├── Generación XML    │
       │         ├── Validación DTD    │
       │         └── Conversión HTML   │
       │                              │
       ├── views/configuracion.py ────┤
       │         └── API Key & Tokens  │
       │                              │
       └── views/manual_usuario.py    │
                                      │
              ┌───────────────────────┘
              │
              ▼
       modules/
       ├── transformer.py      (Núcleo de conversión DOCX → XML)
       ├── metadata_processor.py (Extracción de metadatos con IA)
       ├── correction.py        (Corrección de errores XML con IA)
       ├── prompts.py           (Prompts centralizados para Gemini)
       ├── xml_html.py          (Conversión XML JATS → HTML5)
       └── config_store.py      (Persistencia SQLite de config — una sola API key)
              │
              ▼
       modules/dtd/JATS-Publishing-1-3-MathML3-DTD/ (Validación DTD)
```

---

## Tecnologías

| Tecnología | Versión | Propósito |
|------------|---------|-----------|
| **Python** | 3.9+ | Lenguaje base |
| **Streamlit** | 1.51.0 | Framework de interfaz web |
| **Google Gemini** | 2.5-flash | Modelo LLM para etiquetado inteligente |
| **lxml** | 6.0.2 | Parsing, validación y transformación XML/HTML |
| **python-docx** | 1.2.0 | Extracción de contenido de Word |
| **pdfplumber** | 0.10.4 | Extracción de texto de PDFs |
| **tenacity** | 9.1.2 | Reintentos robustos con backoff exponencial |
| **SQLite** | - | Persistencia de API key y tokens |

---

## Estructura de Directorios

```
XML-JATS-2/
├── streamlit_app.py          # Punto de entrada principal
├── run_app.sh                # Script de ejecución
├── requirements.txt          # Dependencias Python
├── README.md                 # Documentación principal (v0.67)
├── RESUME.md                 # Resumen técnico del proyecto
├── CONTRIBUTING.md           # Guía de contribución
├── Manual_Usuario_Completo_UV_v0-5.pdf  # Manual PDF
│
├── modules/                  # Backend - Módulos Python
│   ├── transformer.py        # Núcleo de conversión (DOCX → XML)
│   ├── metadata_processor.py # Extracción de metadatos
│   ├── correction.py         # Corrección con IA
│   ├── prompts.py            # Prompts centralizados
│   ├── xml_html.py           # Conversión XML→HTML
│   ├── config_store.py       # Persistencia SQLite (una API key)
│   ├── convert_images.py     # Utilidad de conversión
│   └── dtd/                  # DTD JATS local
│       └── JATS-Publishing-1-3-MathML3-DTD/
│
├── views/                    # Frontend - Vistas Streamlit
│   ├── transformador.py      # Vista principal
│   ├── configuracion.py      # Configuración API/tokens
│   ├── manual_usuario.py     # Manual de usuario
│   ├── documentacion.py      # Vista de documentación
│   └── creditos.py           # Créditos y licencias
│
└── resources/                # Recursos estáticos
    ├── UV_blanco.png         # Logo UV
    ├── UV_color.png          # Logo UV color
    ├── logo.png              # Logo principal
    ├── logo_transparent.png  # Logo transparente
    └── manual_images/        # Imágenes del manual
```

---

## Flujo de Datos

1. **Carga**: Usuario sube DOCX/PDF vía Streamlit UI
2. **Extracción**: `transformer.extraer_contenido_estructurado()` extrae texto, tablas e imágenes
3. **Metadatos**: `metadata_processor.MetadataExtractor` usa Gemini para extraer título, autores, DOI, etc.
4. **Generación**: `prompts.get_generation_prompt()` + `transformer.invocar_gemini_cli()` generan XML JATS
5. **Validación**: `transformer.validar_jats_xml()` valida contra DTD local
6. **Corrección**: Si hay errores, `correction.corregir_xml()` usa IA para sugerir correcciones
7. **HTML**: `xml_html.build_html()` convierte a HTML visualizable

---

## Modelos de Gemini Soportados

| Modelo | Cuota gratis/día | Uso recomendado |
|--------|------------------|-----------------|
| gemini-2.5-flash | 500 RPD | Recomendado (balance calidad/cuota) |
| gemini-2.5-pro | 25 RPD | Máxima calidad |
| gemini-2.0-flash | 1500 RPD | Alto volumen |

> Una vez agotada la cuota gratuita, la misma clave funciona en el **tier de pago** si la cuenta tiene facturación habilitada en Google Cloud. No se requiere una segunda clave.

---

## Gestión de API Key y Cuota

- **Una sola clave**: ingresada desde la pestaña **"⚙️ Configuración"** o mediante la variable de entorno `GEMINI_API_KEY`.
- **Cuota agotada**: `transformer.py` retorna `{'quota_exceeded': True}` ante un error 429 persistente. La UI muestra el banner `💳 Cuota gratuita agotada — usando tier de pago` en la barra lateral.
- **Seguridad**: la clave se almacena en `data/config.db` (excluido de Git) y solo se muestra enmascarada en la UI.

---

## Variables de Entorno

| Variable | Descripción |
|----------|-------------|
| `GEMINI_API_KEY` | API Key de Google Gemini (única variable requerida) |

---

## Comandos

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar aplicación
streamlit run streamlit_app.py
# o
./run_app.sh
```

---

## Estado del Proyecto

- **Versión actual:** 0.67
- **Framework:** Streamlit
- **LLM:** Google Gemini API (gemini-2.5-flash por defecto)
- **Validación:** JATS DTD 1.3/1.4

---

## Archivos de Configuración

| Archivo | Propósito |
|---------|-----------|
| `data/config.db` | Base de datos SQLite local (API key, tokens, métricas) |
| `.gitignore` | Exclusiones de Git (`data/`, `.venv/`, etc.) |
| `requirements.txt` | Dependencias Python |