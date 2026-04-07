import streamlit as st
import base64
from fpdf import FPDF
import tempfile
import os
from pathlib import Path
from datetime import datetime

# --- CONTENIDO MANUAL DE USUARIO (Hardcoded + Images) ---
MANUAL_SECTIONS = [
    {
        "type": "text",
        "title": "Introducción",
        "content": """
El **Transformador XML JATS** es una herramienta especializada diseñada para optimizar y automatizar el flujo de trabajo editorial de la **Universidad de Valparaíso**. 

Esta solución permite la conversión de manuscritos originales en formato Microsoft Word (`.docx`) al estándar **JATS XML (Journal Archiving and Interchange Tag Suite)**, asegurando el cumplimiento con los requisitos de indexación y preservación digital de alto nivel.

Características principales:
- Extracción automática de metadatos (título, autores, DOI, fechas).
- Conversión de tablas a formato JATS con estructura completa.
- Generación de HTML con DOIs clickeables y referencias bien formateadas.
- Validación contra el estándar JATS 1.4 (ANSI/NISO Z39.96-2024).
"""
    },
    {
        "type": "step",
        "title": "Configuración Inicial",
        "content": """
Antes de comenzar, diríjase a la pestaña **"⚙️ Configuración"** en el menú izquierdo para preparar su entorno:

**1. Clave de API Gemini:**
- **Primera vez**: Pegue su clave y presione **"💾 Guardar"**. Se almacenará de forma segura y persistente.
- **Sesiones posteriores**: La clave se carga automáticamente (ej. `AIza••••••xY4Z`).

**2. Metadatos de Publicación y Estándar:**
- Debajo del panel de cuotas encontrará los **Metadatos Persistentes de la Revista**.
- Rellene aquí el **Título de Revista**, la **Editorial**, el **ISSN**, y seleccione qué **Versión DTD JATS** utilizará (1.3 o 1.4).
- Estos datos se autocompletarán de forma transparente en cada validación que realice en la herramienta, ahorrando trabajo repetitivo.

**3. Panel de Consumo:**
- Encontrará una barra de progreso que ilustra las Requests usadas hoy vs. el límite diario, junto al historial y advertencias preventivas si se acerca al tope de su cuota gratuita.
"""
    },
    {
        "type": "step",
        "title": "1. Carga de Archivos",
        "content": """
- Navegue a la sección **"Transformador"** en el menú lateral.
- Encontrará un área designada para la carga de archivos.
- Puede subir documentos en formato **WORD (`.docx`)** o **PDF (`.pdf`)**.

Una vez cargado el archivo, el sistema desplegará el panel de **Revisión de Metadatos**:

- **Verifique los datos**: Título, Revista, Fecha, DOI, autores, etc.
- **Complete lo faltante**: Si faltan datos clave (el DOI y la fecha son obligatorios), un **Chatbot Asistente** aparecerá para pedírselos. Puede escribirlos en el chat o en los campos editables.
- Revise también la vista previa del texto extraído, incluyendo las tablas detectadas.
""",
        "image": "resources/manual_images/01.png",
        "caption": "Figura 2: Área de carga de documentos y extracción de metadatos."
    },
    {
        "type": "step",
        "title": "2. Generación de XML JATS",
        "content": """
Una vez confirmados los metadatos y el contenido, en la pestaña **"Generación"**:

- Presione el botón **"Generar XML JATS"**.
- El sistema procesará el contenido aplicando las reglas del último estándar **JATS 1.4 (ANSI/NISO Z39.96-2024)**.
- Se utilizarán los metadatos validados para construir un encabezado (`<front>`) preciso, incluyendo DOI y fechas.
- Las tablas del documento se convertirán automáticamente a `<table-wrap>` con encabezados y cuerpo.
- Cada sección del artículo (Introducción, Métodos, Resultados, etc.) se mapeará a su etiqueta `<sec>` correspondiente.
""",
        "image": "resources/manual_images/02.png",
        "caption": "Figura 3: Generación exitosa de XML JATS."
    },
    {
        "type": "step",
        "title": "3. Validación y Corrección",
        "content": """
- Presione el botón **"Ejecutar Validación DTD"**.
- Se ejecutará una validación automática estricta contra el DTD oficial **JATS 1.4**.

***Importante***
- Si el sistema encuentra errores, se mostrará un informe con los errores encontrados y se habilitarán un botón de corrección que permitirá corregir los errores encontrados asistido por la IA de Gemini.
- Si el sistema no encuentra errores, se mostrará un mensaje de éxito y se habilitarán el botón de Resultados.
""",
        "image": "resources/manual_images/03.png",
        "caption": "Figura 4: Validación de DTD ejecutada sin errores."
    },
    {
        "type": "step",
        "title": "4. Resultados",
        "content": """
Si la validación es exitosa, se habilitarán los botones de descarga:

- Descargar XML: Archivo listo para publicación/preservación.
- Descargar HTML: Vista previa para lectura web con DOIs clickeables.
- **Vista previa HTML**: Haga clic en el botón **"Ver vista previa en nueva pestaña"** para abrir el HTML en una pestaña independiente del navegador. Los enlaces internos (citas, tabla de contenidos) y los DOIs en las referencias funcionan correctamente en esta vista.
""",
        "image": "resources/manual_images/04.png",
        "caption": "Figura 5: Resultados y enlaces de descarga/vista previa."
    }
]

FAQ_CONTENT = """
**¿Qué formatos soporta?**
Soporta archivos Microsoft Word (`.docx`) y documentos Portables (`.pdf`).

**¿Qué hago si falla la validación?**
Revise el mensaje de error. Generalmente se debe a caracteres especiales no soportados o estructuras de documento inusuales (ej. tablas anidadas complejas). Puede usar el botón **"Intentar Solucionar con IA"** para que Gemini corrija automáticamente los errores, o editar el XML manualmente.

**¿Las tablas del documento se incluyen en el XML?**
Sí. Las tablas se extraen automáticamente y se convierten a formato JATS (`<table-wrap>`) con encabezados (`<thead>`) y cuerpo (`<tbody>`) correctamente estructurados, preservando todas las filas y columnas del documento original.

**¿Se incluye el DOI y la fecha de publicación?**
Sí. El DOI y la fecha de publicación son campos obligatorios que se extraen automáticamente de los metadatos. Si el sistema no los detecta, le pedirá que los ingrese antes de generar el XML.

**¿Los enlaces del HTML funcionan correctamente?**
Sí. Los enlaces de citas (ej. [1], [2]) y la tabla de contenidos navegan correctamente dentro de la página. Los DOIs en las referencias bibliográficas son clickeables y enlazan directamente a doi.org. Use siempre el botón "Ver vista previa en nueva pestaña" para la mejor experiencia.

**¿Los caracteres acentuados se ven bien?**
Sí. El sistema decodifica correctamente todos los caracteres UTF-8 (á, é, í, ó, ú, ñ, etc.) tanto en la vista previa como en el archivo descargado.

**¿Es seguro subir mis archivos?**
Sí, los archivos se procesan temporalmente en la memoria para su transformación y no se guardan en el servidor de forma permanente.

**¿Mi API Key está segura?**
Sí. La clave se almacena localmente en una base de datos SQLite (carpeta `data/`) con ofuscación Base64. Una vez guardada, desaparece de la interfaz y solo se muestra enmascarada. La carpeta `data/` está excluida del control de versiones.

**¿Qué pasa si alcanzo el límite de tokens gratuitos?**
El panel de consumo en la pestaña **"⚙️ Configuración"** muestra su consumo actual vs. los límites del tier gratuito de cada modelo. Al alcanzar el 80%% se muestra una advertencia; al 100%% las solicitudes podrían fallar. Puede esperar al día siguiente (los límites diarios se renuevan) o cambiar a un modelo con mayor cuota.
"""

def get_documentation_content():
    """Lee README y CONTRIBUTING."""
    docs = []
    
    # README
    readme_path = Path("README.md")
    if readme_path.exists():
        docs.append({"title": "Documentación General (README)", "content": readme_path.read_text(encoding='utf-8')})
    
    # CONTRIBUTING
    contrib_path = Path("CONTRIBUTING.md")
    if contrib_path.exists():
        docs.append({"title": "Guía de Contribución", "content": contrib_path.read_text(encoding='utf-8')})
        
    return docs

def get_credits_content():
    """Retorna contenido de créditos como texto."""
    return """
Esta herramienta ha sido desarrollada para optimizar el flujo de trabajo editorial de las Revistas UV, automatizando la conversión de manuscritos a XML JATS validado.

Desarrollador Principal:
Cristian Carreño León (cristian.carreno@uv.cl)
Escuela de Obstetricia y Puericultura
Facultad de Medicina
Universidad de Valparaíso, Chile

Tecnologías Utilizadas:
- Python 3.9+: Lenguaje base.
- Streamlit: Framework de interfaz de usuario web.
- Google Gemini 2.5 Flash: Modelo de lenguaje (LLM) para etiquetado inteligente.
- lxml: Procesamiento, validación y parsing de XML/HTML.
- python-docx: Extracción de contenido desde archivos Word.
- FPDF2: Generación de manuales en PDF.
- JATS 1.4 (ANSI/NISO Z39.96-2024): Estándar de etiquetado XML.

Privacidad y Tratamiento de Datos:
1. Procesamiento Volátil: Los archivos no se almacenan permanentemente en el servidor.
2. API de Inteligencia Artificial: Se utiliza Google Gemini bajo sus términos de servicio. El texto enviado a la API se procesa bajo las políticas de privacidad de Google.

Licencia:
Software de uso exclusivo para la Universidad de Valparaíso. Todos los derechos reservados.
El código fuente y la documentación son propiedad intelectual de la Universidad de Valparaíso y su autor.

Versión: 0.68
"""

class ProfessionalPDF(FPDF):
    def header(self):
        # Logo
        logo_path = "resources/UV_color.png"
        if os.path.exists(logo_path):
            self.image(logo_path, 10, 8, 33)
        
        self.set_font('Arial', 'B', 10)
        self.cell(80) # Move to right
        self.cell(100, 10, 'Manual de Usuario - Transformador XML JATS', 0, 0, 'R')
        self.ln(20)
        # Line break
        self.line(10, 25, 200, 25)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Generado el {datetime.now().strftime("%d/%m/%Y")} | Página ' + str(self.page_no()) + '/{nb}', 0, 0, 'C')

def clean_text_for_pdf(text):
    """Limpia caracteres markdown básicos y elimina caracteres no soportados por latin-1 (emojis)."""
    # Remove bold/italic markers only if they are not part of a header structure we parse later?
    # Actually for simple FPDF text, we want to strip them usually.
    # But let's leave proper headers (#) alone here so we can detect them in the loop.
    text = text.replace('**', '').replace('__', '').replace('`', '').strip()
    return text.encode('latin-1', 'ignore').decode('latin-1')

def add_markdown_section_to_pdf(pdf, text):
    """Parsea texto markdown simple y lo agrega al PDF formateado."""
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            pdf.ln(5)
            continue
            
        # Headers
        if line.startswith('# '):
            pdf.ln(5)
            pdf.set_font('Arial', 'B', 16)
            pdf.set_text_color(0, 51, 102) # Dark Blue
            pdf.cell(0, 10, clean_text_for_pdf(line.replace('# ', '')), 0, 1, 'L')
            pdf.set_text_color(0)
            pdf.set_font('Arial', '', 11)
        
        elif line.startswith('## '):
            pdf.ln(4)
            pdf.set_font('Arial', 'B', 14)
            pdf.set_text_color(0, 51, 102)
            pdf.cell(0, 10, clean_text_for_pdf(line.replace('## ', '')), 0, 1, 'L')
            pdf.set_text_color(0)
            pdf.set_font('Arial', '', 11)
            
        elif line.startswith('### '):
            pdf.ln(2)
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(0, 10, clean_text_for_pdf(line.replace('### ', '')), 0, 1, 'L')
            pdf.set_font('Arial', '', 11)
            
        # Lists
        elif line.startswith('- ') or line.startswith('* '):
            pdf.set_font('Arial', '', 11)
            pdf.cell(5) # Indent
            # chr(149) is bullet for latin-1
            content = clean_text_for_pdf(line[2:])
            pdf.multi_cell(0, 6, chr(149) + ' ' + content)
            
        # Numbered Lists (Simple detection "1. ")
        elif len(line) > 2 and line[0].isdigit() and line[1] == '.' and line[2] == ' ':
            pdf.set_font('Arial', '', 11)
            pdf.cell(5) # Indent
            content = clean_text_for_pdf(line)
            pdf.multi_cell(0, 6, content)
            
        # Code blocks (simple detection)
        elif line.startswith('```'):
            continue # Skip the marker
            
        # Normal text
        else:
            pdf.set_font('Arial', '', 11)
            pdf.multi_cell(0, 6, clean_text_for_pdf(line))

def create_professional_pdf():
    pdf = ProfessionalPDF()
    pdf.alias_nb_pages()
    
    # --- PORTADA ---
    pdf.add_page()
    
    # Logo Grande
    logo_path = "resources/UV_color.png"
    if os.path.exists(logo_path):
        pdf.image(logo_path, x=65, y=60, w=80)
    
    pdf.set_y(100)
    pdf.set_font('Arial', 'B', 24)
    pdf.cell(0, 10, 'Manual de Usuario', 0, 1, 'C')
    pdf.ln(5)
    pdf.set_font('Arial', '', 16)
    pdf.set_text_color(100)
    pdf.cell(0, 10, 'Transformador XML-JATS', 0, 1, 'C')
    
    pdf.set_y(130)
    pdf.set_font('Arial', '', 12)
    pdf.set_text_color(0)
    pdf.cell(0, 10, 'Universidad de Valparaíso', 0, 1, 'C')
    pdf.cell(0, 10, 'Facultad de Medicina', 0, 1, 'C')
    
    pdf.set_y(180)
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 10, 'Autor: Cristian Carreño León', 0, 1, 'C')
    pdf.cell(0, 10, 'Fecha: 15-03-2026', 0, 1, 'C')
    pdf.cell(0, 10, 'Versión: 0.68', 0, 1, 'C')
    pdf.cell(0, 10, 'Contacto: cristian.carreno@uv.cl', 0, 1, 'C')
    
    # --- SECCIÓN 1: DOCUMENTACIÓN ---
    docs = get_documentation_content()
    for doc in docs:
        pdf.add_page()
        # Title of the section (e.g. "Documentación General")
        pdf.set_font('Arial', 'B', 16)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(0, 10, doc["title"], 0, 1, 'L', 1)
        pdf.ln(5)
        
        # Render Markdown content properly
        add_markdown_section_to_pdf(pdf, doc["content"])
            
    # --- SECCIÓN 2: MANUAL DE USUARIO ---
    pdf.add_page()
    
    # Intro
    pdf.set_font('Arial', 'B', 16)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, 'Manual de Usuario', 0, 1, 'L', 1)
    pdf.ln(5)
    
    pdf.set_font('Arial', '', 11)
    intro_text = clean_text_for_pdf(MANUAL_SECTIONS[0]["content"])
    pdf.multi_cell(0, 6, intro_text)
    pdf.ln(10)
    
    # Pasos
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, 'Flujo de Trabajo', 0, 1, 'L')
    pdf.ln(5)
    
    for section in MANUAL_SECTIONS:
        if section["type"] == "step":
            # Title
            pdf.set_font('Arial', 'B', 13)
            pdf.set_text_color(0, 51, 102) # Dark Blue
            pdf.cell(0, 10, section["title"], 0, 1, 'L')
            pdf.set_text_color(0)
            
            # Content (using markdown parser logic slightly adapted or reuse)
            # The manual sections are simple, mostly lines. Let's use clean_text_for_pdf logic directly
            # but allow bullet points if any exist in the manual content.
            # Actually, let's use the new parser for consistency!
            add_markdown_section_to_pdf(pdf, section["content"])
            pdf.ln(2)
            
            # Image
            if "image" in section and os.path.exists(section["image"]):
                pdf.image(section["image"], w=140, x=35) 
                if "caption" in section:
                    pdf.set_font('Arial', 'I', 9)
                    pdf.cell(0, 8, section["caption"], 0, 1, 'C')
            
            pdf.ln(10)
            
    # FAQ
    pdf.add_page()
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, 'Preguntas Frecuentes', 0, 1, 'L')
    pdf.ln(5)
    
    # Use parser for FAQ too to handle bold headers if they were properly markdown 
    # (Currently FAQ_CONTENT uses ** for bold which clean_text strips, 
    # but we can improve FAQ_CONTENT to use ## if we want headers, or just rely on the existing logic there).
    # Since FAQ_CONTENT uses simple **Question?** format, the previous logic was fine. 
    # Let's clean it up to use standard markdown ## for questions if possible, 
    # or just stick to the manual parsing for FAQ which was working okay. 
    # The previous code handled "?" detection. Let's keep a simple loop for FAQ or adapt it.
    
    faq_lines = FAQ_CONTENT.strip().split('\n')
    for line in faq_lines:
        line = clean_text_for_pdf(line)
        if not line:
            pdf.ln(5)
            continue
        if "?" in line and line.endswith("?"): 
            pdf.set_font('Arial', 'B', 11)
            pdf.multi_cell(0, 6, line)
            pdf.set_font('Arial', '', 11)
        else:
            pdf.multi_cell(0, 6, line)
            
    # --- SECCIÓN 3: CRÉDITOS Y LICENCIAS ---
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, 'Créditos y Licencias', 0, 1, 'L', 1)
    pdf.ln(10)
    
    pdf.set_font('Arial', '', 11)
    # Using parser for credits? Credits is simple text.
    credits_text = get_credits_content()
    add_markdown_section_to_pdf(pdf, credits_text)

    return pdf

@st.cache_data(show_spinner="Generando PDF...")
def generate_pdf_bytes():
    """Genera el PDF y devuelve los bytes, cacheado para optimizar."""
    try:
        pdf = create_professional_pdf()
        # Use temp file to get bytes safely across platforms/versions
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            pdf.output(tmp_file.name)
            tmp_path = tmp_file.name
        
        with open(tmp_path, "rb") as f:
            pdf_bytes = f.read()
            
        os.unlink(tmp_path)
        return pdf_bytes
    except Exception as e:
        st.error(f"Error generando PDF: {e}")
        return None

def main():
    st.title("📖 Manual de Usuario")
    st.markdown("---")

    # Layout: Intro wide
    st.markdown(MANUAL_SECTIONS[0]["content"])
    
    st.subheader("📍 Flujo de Trabajo")
    
    st.graphviz_chart('''
        digraph Flujo {
            rankdir=LR;
            node [shape=rect, style=filled, color="#2e7bcf", fontcolor=white, fontname="Helvetica", margin="0.2,0.1"];
            edge [color="#666666", fontname="Helvetica", fontsize=10];
            
            Carga [label="1. Carga de Archivo\\n(.docx o .pdf)"];
            Extraccion [label="2. Extracción de\\nMetadatos"];
            Revision [label="3. Revisión / Chatbot"];
            Generacion [label="4. Generación\\nXML JATS"];
            Validacion [label="5. Validación DTD\\nJATS"];
            Resultados [label="6. Exportación\\n(XML / HTML)"];
            
            Carga -> Extraccion;
            Extraccion -> Revision;
            Revision -> Generacion [label=" Confirmar"];
            Generacion -> Validacion [label=" Validar"];
            Validacion -> Resultados [label=" Éxito", color="green", fontcolor="green"];
            Validacion -> Revision [label=" Error", color="red", fontcolor="red"];
        }
    ''')
    
    st.markdown("<br>", unsafe_allow_html=True)

    # Zig-zag layout using loop
    for i, section in enumerate(MANUAL_SECTIONS):
        if section["type"] == "step":
            with st.container():
                col_text, col_img = st.columns([1, 1], gap="large")
                
                
                if section.get("image"):
                    # Alternating layout
                    if i % 2 != 0:
                        col_text, col_img = col_img, col_text
                    
                    with col_text:
                        st.markdown(f"### {section['title']}")
                        st.markdown(section["content"])
                    
                    with col_img:
                        if os.path.exists(section["image"]):
                            st.image(section["image"], caption=section.get("caption", ""), width=400)
                        else:
                            st.warning("Imagen no encontrada")
                else:
                    # No image — full width text
                    st.markdown(f"### {section['title']}")
                    st.markdown(section["content"])
                
                st.divider()

    with st.expander("❓ Preguntas Frecuentes", expanded=False):
        st.markdown(FAQ_CONTENT)
    
    st.markdown("---")
    
    col_center = st.columns([1, 2, 1])
    with col_center[1]:
        st.info("Obtenga el manual completo en PDF, incluyendo documentación y créditos.")
        
        # Pre-generate or get from cache
        pdf_bytes = generate_pdf_bytes()
        
        if pdf_bytes:
            st.download_button(
                label="� Descargar Manual Completo PDF",
                data=pdf_bytes,
                file_name="Manual_Usuario_Completo_UV.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True
            )

    # Sidebar Footer (Igual que en la app principal para consistencia)
    with st.sidebar:
        st.markdown("---")
        st.markdown(
            """
            <div class='branding'>
                <b>Universidad de Valparaíso</b><br>
                <small>Transformador XML JATS v0.7.0</small>
            </div>
            """, 
            unsafe_allow_html=True
        )

if __name__ == "__main__":
    main()
