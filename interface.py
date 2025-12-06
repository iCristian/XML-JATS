import streamlit as st
import os
import tempfile
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List

import transformer
import xml_html
import streamlit.components.v1 as components

# Configuración de la página
st.set_page_config(
    page_title="Transformador XML JATS",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Personalizado para un look profesional
st.markdown("""
<style>
    .main {
        background-color: #f8f9fa;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #003366; /* Azul UV aproximado */
        color: white;
        border: none;
    }
    .stButton>button:hover {
        background-color: #002244;
    }
    .stTextArea>div>div>textarea {
        font-family: 'Courier New', Courier, monospace;
    }
    h1 {
        color: #003366;
    }
    h2, h3 {
        color: #34495e;
    }
    .branding {
        text-align: center;
        margin-top: 20px;
        color: #666;
        font-size: 0.9em;
    }
</style>
""", unsafe_allow_html=True)

def main() -> None:
    """Función principal de la aplicación Streamlit.

    Orquesta la interfaz de usuario, manejo de estados y llamadas
    a los módulos de transformación y validación.
    """
    st.title("📄 Transformador XML JATS")
    st.markdown("### Convierte documentos Word a XML JATS con IA")
    
    with st.sidebar:
        st.header("Instrucciones")
        st.info(
            "1. Sube un archivo .docx.\n"
            "2. Revisa y edita el texto extraído si es necesario.\n"
            "3. Genera el XML.\n"
            "4. Valida y Descarga.\n"
            "5. (Opcional) Convierte a HTML y visualiza."
        )
        st.markdown("---")
        st.markdown(
            "<div class='branding'>Universidad de Valparaíso</div>", 
            unsafe_allow_html=True
        )

    # Carga de Archivo
    uploaded_file = st.file_uploader("Selecciona un documento Word", type=['docx'])

    if uploaded_file is not None:
        # Guardar archivo temporalmente
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name

        st.success(f"Archivo '{uploaded_file.name}' cargado exitosamente!")

        # Inicializar estado de la sesión
        if 'extracted_text' not in st.session_state:
            st.session_state.extracted_text = ""
        if 'generated_xml' not in st.session_state:
            st.session_state.generated_xml = ""
        if 'generated_html' not in st.session_state:
            st.session_state.generated_html = ""

        # --- Paso 1: Extracción ---
        st.divider()
        st.header("1. Extracción de Contenido")
        
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("Extraer Contenido"):
                with st.spinner("Extrayendo texto e imágenes..."):
                    extracted = transformer.extraer_contenido_estructurado(tmp_path)
                    if extracted:
                        st.session_state.extracted_text = extracted
                        st.success("¡Extracción Completa!")
                    else:
                        st.error("Fallo al extraer el contenido.")
        
        with col2:
            if st.session_state.extracted_text:
                st.session_state.extracted_text = st.text_area(
                    "Contenido Extraído (Editable)", 
                    value=st.session_state.extracted_text, 
                    height=400
                )
                st.caption("Puedes editar el texto arriba antes de generar el XML.")

        # --- Paso 2: Transformación ---
        if st.session_state.extracted_text:
            st.divider()
            st.header("2. Generación XML")
            
            if st.button("Generar XML JATS", type="primary"):
                with st.spinner("Llamando a Gemini AI para generar XML... (Esto puede tardar un minuto)"):
                    prompt = transformer.construir_prompt_avanzado(st.session_state.extracted_text)
                    result = transformer.invocar_gemini_cli(prompt)
                    
                    if result.get('returncode') == 0 and result.get('stdout'):
                        xml_out = result.get('stdout', '')
                        # Limpiar bloques de código markdown
                        import re
                        match = re.search(r"```xml\s*(.*?)\s*```", xml_out, re.DOTALL)
                        if match:
                            xml_out = match.group(1)
                        
                        st.session_state.generated_xml = xml_out.strip()
                        st.success("¡XML Generado Exitosamente!")
                    else:
                        st.error("Fallo en la Generación XML.")
                        with st.expander("Ver Detalles del Error"):
                            st.code(result.get('stderr'))

        # --- Paso 3: Validación, Salida y HTML ---
        if st.session_state.generated_xml:
            st.divider()
            st.header("3. Validación y Salida")
            
            # Pestañas para organizar la vista
            tab_xml, tab_val, tab_html = st.tabs(["Ver XML", "Validación y Descarga", "Vista Previa HTML"])
            
            with tab_xml:
                st.subheader("XML Generado")
                st.code(st.session_state.generated_xml, language='xml')
            
            with tab_val:
                st.subheader("Estado de Validación")
                if st.button("Validar XML"):
                    is_valid, errors = transformer.validar_jats_xml(st.session_state.generated_xml)
                    if is_valid:
                        st.success("✅ El XML es Válido según el DTD JATS.")
                    else:
                        st.error("❌ Falló la Validación XML.")
                        for err in errors:
                            st.warning(f"- {err}")
                
                st.markdown("---")
                st.download_button(
                    label="Descargar Archivo XML",
                    data=st.session_state.generated_xml,
                    file_name=f"{Path(uploaded_file.name).stem}.xml",
                    mime="application/xml"
                )

            with tab_html:
                st.subheader("Conversión a HTML")
                if st.button("Convertir XML a HTML"):
                    with st.spinner("Convirtiendo a HTML..."):
                        try:
                            # Necesitamos guardar el XML en un archivo temporal para que xml_html lo lea
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".xml", mode='w', encoding='utf-8') as tmp_xml:
                                tmp_xml.write(st.session_state.generated_xml)
                                tmp_xml_path = tmp_xml.name
                            
                            # Usar las funciones de xml_html.py
                            data = xml_html.parse_jats(tmp_xml_path)
                            html_content = xml_html.build_html(data)
                            st.session_state.generated_html = html_content
                            st.success("¡HTML Generado!")
                            
                        except Exception as e:
                            st.error(f"Error al convertir a HTML: {e}")

                if st.session_state.generated_html:
                    st.markdown("---")
                    st.download_button(
                        label="Descargar HTML",
                        data=st.session_state.generated_html,
                        file_name=f"{Path(uploaded_file.name).stem}.html",
                        mime="text/html"
                    )
                    st.markdown("### Vista Previa")
                    # Usar components.html para renderizar el HTML en un iframe aislado
                    components.html(st.session_state.generated_html, height=800, scrolling=True)

if __name__ == "__main__":
    main()
