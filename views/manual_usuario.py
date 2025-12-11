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
"""
    },
    {
        "type": "step",
        "title": "1. Carga de Archivos",
        "content": """
- Navegue a la sección **"Transformador"** en el menú lateral.
- Encontrará un área designada para la carga de archivos.
- Puede arrastrar y soltar su archivo `.docx` o hacer clic en "Browse files" para seleccionarlo de su equipo.

Una vez cargado el archivo, el sistema realizará una extracción automática del texto:

- Revise que el texto extraído sea correcto.
- Si no es correcto, puede editar el texto manualmente.
- Agregue en esta sección información que puede estar ausente en el documento original (DOI, Fecha de publicación, etc).
- Revise que la información sea correcta.
""",
        "image": "resources/manual_images/01.png",
        "caption": "Figura 1: Área de carga de documentos."
    },
    {
        "type": "step",
        "title": "2. Generación de XML JATS",
        "content": """
Una vez cargado el archivo, en la pestaña **"Generación"**:

- Presione el botón **"Generar XML JATS"**.
- El sistema procesará el contenido aplicando las reglas del estándar **JATS 1.3**.
""",
        "image": "resources/manual_images/02.png",
        "caption": "Figura 2: Generación de XML JATS."
    },
    {
        "type": "step",
        "title": "3. Validación y Corrección",
        "content": """
- Presione el botón **"Ejecutar Validación DTD"**.
- El sistema procesará el contenido aplicando las reglas del estándar **JATS 1.3**.
- Se ejecutará una validación automática estricta contra el DTD oficial.

***Importante***
- Si el sistema encuentra errores, se mostrará un informe con los errores encontrados y se habilitarán un botón de corrección que permitirá corregir los errores encontrados asistido por la IA de Gemini.
- Si el sistema no encuentra errores, se mostrará un mensaje de éxito y se habilitarán el botón de Resultados.
""",
        "image": "resources/manual_images/03.png", # Reusing home as it shows the button usually
        "caption": "Figura 3: Validación de DTD."
    },
    {
        "type": "step",
        "title": "4. Resultados",
        "content": """
Si la validación es exitosa, se habilitarán los botones de descarga:

- Descargar XML: Archivo listo para publicación/preservación.
- Descargar HTML: Vista previa para lectura web.
""",
        "image": "resources/manual_images/04.png",
        "caption": "Figura 4: Resultados."
    }
]

FAQ_CONTENT = """
**¿Qué formatos soporta?**
Actualmente soporta archivos Microsoft Word (`.docx`). Asegúrese de que el documento no esté protegido con contraseña.

**¿Qué hago si falla la validación?**
Revise el mensaje de error. Generalmente se debe a caracteres especiales no soportados o estructuras de documento inusuales (ej. tablas anidadas complejas). Edite el contenido en el paso 2 y reintente.

**¿Es seguro subir mis archivos?**
Sí, los archivos se procesan temporalmente en la memoria para su transformación y no se guardan en el servidor de forma permanente.
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
Esta herramienta ha sido desarrollada para optimizar el flujo de trabajo editorial de la Revistas UV, automatizando la conversión de manuscritos a XML JATS validado.

Desarrollador Principal:
Cristian Carreño León (cristian.carreno@uv.cl)

Tecnología:
- Python 3.9+: Lenguaje base.
- Streamlit: Framework de interfaz de usuario.
- Google Gemini Pro: Modelo de lenguaje (LLM).
- LXML: Procesamiento y validación robusta de XML.
- JATS 1.3: Estándar de etiquetado.

Privacidad y Tratamiento de Datos:
1. Procesamiento Volátil: Los archivos no se almacenan permanentemente.
2. API de Inteligencia Artificial: Se utiliza Google Gemini bajo sus términos de servicio.
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
    pdf.cell(0, 10, 'Fecha: 11-12-2025', 0, 1, 'C')
    pdf.cell(0, 10, 'Versión: 0.5 (Beta)', 0, 1, 'C')
    pdf.cell(0, 10, 'Contacto: carreonleong@gmail.com', 0, 1, 'C')
    
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
    
    # Zig-zag layout using loop
    for i, section in enumerate(MANUAL_SECTIONS):
        if section["type"] == "step":
            with st.container():
                col_text, col_img = st.columns([1, 1], gap="large")
                
                # Alternating layout
                if i % 2 != 0:
                    col_text, col_img = col_img, col_text
                
                with col_text:
                    st.markdown(f"### {section['title']}")
                    # Use the parser for the web view too?
                    # The content is string with markdown, st.markdown handles it well.
                    # But section content might be cleaner if we use st.markdown directly.
                    st.markdown(section["content"])
                
                with col_img:
                    if os.path.exists(section["image"]):
                        st.image(section["image"], caption=section["caption"], width=400) # Fixed width for consistency or use_container_width
                    else:
                        st.warning("Imagen no encontrada")
                
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

if __name__ == "__main__":
    main()
