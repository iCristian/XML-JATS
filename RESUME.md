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
       │         └── API Keys & Tokens │
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
       └── config_store.py      (Persistencia SQLite de config)
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
| **SQLite** | - | Persistencia de API keys y tokens |

---

## Estructura de Directorios

```
XML-JATS-2/
├── streamlit_app.py          # Punto de entrada principal
├── run_app.sh                # Script de ejecución
├── requirements.txt          # Dependencias Python
├── README.md                 # Documentación principal (v0.66)
├── CONTRIBUTING.md           # Guía de contribución
├── Manual_Usuario_Completo_UV_v0-5.pdf  # Manual PDF
│
├── modules/                  # Backend - Módulos Python
│   ├── transformer.py        # Núcleo de conversión (694 líneas)
│   ├── metadata_processor.py # Extracción de metadatos (134 líneas)
│   ├── correction.py         # Corrección con IA (37 líneas)
│   ├── prompts.py            # Prompts centralizados (274 líneas)
│   ├── xml_html.py           # Conversión XML→HTML (1700+ líneas)
│   ├── config_store.py       # Persistencia SQLite (373 líneas)
│   ├── convert_images.py     # Utilidad de conversión
│   └── dtd/                  # DTD JATS local
│       └── JATS-Publishing-1-3-MathML3-DTD/
│
├── views/                    # Frontend - Vistas Streamlit
│   ├── transformador.py      # Vista principal (931 líneas)
│   ├── configuracion.py      # Configuración API/tokens (239 líneas)
│   ├── manual_usuario.py     # Manual de usuario (520+ líneas)
│   ├── documentacion.py     # Vista de documentación
│   └── creditos.py           # Créditos y licencias
│
└── resources/                # Recursos estáticos
    ├── UV_blanco.png         # Logo UV
    ├── UV_color.png          # Logo UV color
    ├── logo.png              # Logo principal
    ├── logo_transparent.png   # Logo transparente
    └── manual_images/         # Imágenes del manual
```

**Total de líneas de código Python:** ~5,365 líneas

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
| gemini-2.5-flash | 500 | Recomendado (balance) |
| gemini-2.5-pro | 25 | Máxima calidad |
| gemini-2.0-flash | 1500 | Alto volumen |
| gemini-3-flash-preview | 500 | Experimental |

---

## Variables de Entorno

- `GEMINI_API_KEY` - API Key gratuita de Gemini
- `GEMINI_API_KEY_PRO` - API Key de pago (opcional)

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

- **Versión actual:** 0.66
- **Framework:** Streamlit
- **LLM:** Google Gemini API
- **Validación:** JATS DTD 1.3/1.4

---

## Archivos de Configuración

| Archivo | Propósito |
|---------|-----------|
| `data/config.db` | Base de datos SQLite local (API keys, tokens, métricas) |
| `.gitignore` | Exclusiones de Git |
| `requirements.txt` | Dependencias Python |