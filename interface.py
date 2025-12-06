import streamlit as st
import os
import tempfile
import time
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List

import transformer
import xml_html
import correction
import streamlit.components.v1 as components

# Configuración de la página
st.set_page_config(
    page_title="Transformador XML JATS",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Personalizado
st.markdown("""
<style>
    .main {
        /* Dejar fondo por defecto */
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #003366;
        color: white;
        border: none;
    }
    .stButton>button:hover {
        background-color: #002244;
    }
    h1 {
        color: #003366;
    }
    @media (prefers-color-scheme: dark) {
        h1 { color: #8ab4f8; }
    }
    .branding {
        text-align: center;
        margin-top: 20px;
        color: #666;
        font-size: 0.9em;
    }
    .success-nav {
        /* Ya no se usa para bloque estático, pero mantenemos por compat */
        padding: 15px;
        border-radius: 8px;
        background-color: #d4edda;
        color: #155724;
        margin-top: 10px;
        border: 1px solid #c3e6cb;
    }
</style>
""", unsafe_allow_html=True)

# Helper para cambiar Tabs via JS
def js_switch_tab(tab_index: int):
    js_code = f"""
        <script>
            var tabs = window.parent.document.querySelectorAll('button[data-baseweb="tab"]');
            if (tabs[{tab_index}]) {{
                tabs[{tab_index}].click();
            }}
        </script>
    """
    components.html(js_code, height=0, width=0)

def main() -> None:
    """Función principal de la aplicación Streamlit."""
    st.title("📄 Transformador XML JATS")
    st.markdown("### Convierte documentos Word a XML JATS con IA")
    
    with st.sidebar:
        st.header("Instrucciones")
        st.info(
            "1. **Carga**: Sube el DOCX y extrae el texto.\n"
            "2. **Generación**: Crea el XML.\n"
            "3. **Validación**: Verifica y corrige errores.\n"
            "4. **Resultados**: Descarga el XML/HTML."
        )
        st.markdown("---")
        st.markdown(
            """
            <div class='branding'>
                <b>Universidad de Valparaíso</b><br>
                <small>v0.5 (Beta)</small>
            </div>
            """, 
            unsafe_allow_html=True
        )

    if 'extracted_text' not in st.session_state:
        st.session_state.extracted_text = ""
    if 'generated_xml' not in st.session_state:
        st.session_state.generated_xml = ""
    if 'generated_html' not in st.session_state:
        st.session_state.generated_html = ""
    if 'validation_errors' not in st.session_state:
        st.session_state.validation_errors = []
    if 'correction_chat' not in st.session_state:
        st.session_state.correction_chat = [] 
    if 'show_correction_chat' not in st.session_state:
        st.session_state.show_correction_chat = False
    if 'pending_correction_xml' not in st.session_state:
        st.session_state.pending_correction_xml = None
    if 'uploaded_file_path' not in st.session_state:
        st.session_state.uploaded_file_path = None

    # Definimos Tabs
    # Tab 0: Carga
    # Tab 1: Generación
    # Tab 2: Validación
    # Tab 3: Resultados
    tab1, tab2, tab3, tab4 = st.tabs([
        "1. Carga y Extracción", 
        "2. Generación", 
        "3. Validación y Corrección", 
        "4. Resultados"
    ])

    # --- Tab 1 ---
    with tab1:
        st.header("Carga de Documento")
        uploaded_file = st.file_uploader("Selecciona un documento Word (.docx)", type=['docx'])

        if uploaded_file is not None:
            if st.session_state.uploaded_file_path is None:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    st.session_state.uploaded_file_path = tmp_file.name

            col1, col2 = st.columns([1, 2])
            with col1:
                st.success("Archivo cargado.")
                if st.button("Extraer Contenido", type="primary"):
                    with st.spinner("Procesando documento..."):
                        extracted = transformer.extraer_contenido_estructurado(st.session_state.uploaded_file_path)
                        if extracted:
                            st.session_state.extracted_text = extracted
                            st.toast("Extracción exitosa", icon="✅")
                        else:
                            st.error("Error en la extracción.")
                
                # Nav Button
                if st.session_state.extracted_text:
                    st.success("✅ Texto extraído correctamente.")
                    if st.button("➡️ Ir a Paso 2: Generación"):
                        js_switch_tab(1)
            
            with col2:
                if st.session_state.extracted_text:
                    st.text_area("Texto Extraído", value=st.session_state.extracted_text, height=400)

    # --- Tab 2 ---
    with tab2:
        st.header("Generación XML con IA")
        if not st.session_state.extracted_text:
            st.info("⚠️ Completa el Paso 1 primero.")
        else:
            if st.button("Generar XML JATS", type="primary"):
                progress_bar = st.progress(0, text="Iniciando...")
                status_text = st.empty()
                status_text.text("Preparando datos...")
                progress_bar.progress(10)
                time.sleep(0.5)
                
                status_text.text("Enviando a Gemini AI...")
                prompt = transformer.construir_prompt_avanzado(st.session_state.extracted_text)
                progress_bar.progress(30)
                
                result = transformer.invocar_gemini_cli(prompt)
                
                status_text.text("Procesando respuesta...")
                progress_bar.progress(80)
                
                if result.get('returncode') == 0 and result.get('stdout'):
                    xml_out = result.get('stdout', '')
                    import re
                    match = re.search(r"```xml\s*(.*?)\s*```", xml_out, re.DOTALL)
                    if match:
                        xml_out = match.group(1)
                    
                    st.session_state.generated_xml = xml_out.strip()
                    st.session_state.validation_errors = []
                    st.session_state.correction_chat = []
                    st.session_state.show_correction_chat = False
                    st.session_state.pending_correction_xml = None
                    
                    progress_bar.progress(100)
                    status_text.text("¡Completado!")
                else:
                    progress_bar.empty()
                    status_text.error("Falló la generación.")
                    st.error(result.get('stderr'))
            
            if st.session_state.generated_xml:
                st.success("✅ XML Generado.")
                st.code(st.session_state.generated_xml, language='xml')
                if st.button("➡️ Ir a Paso 3: Validación"):
                    js_switch_tab(2)

    # --- Tab 3 ---
    with tab3:
        st.header("Validación y Corrección")
        if not st.session_state.generated_xml:
            st.info("⚠️ Genera el XML en el Paso 2 primero.")
        else:
            col_val, col_chat = st.columns([1, 1], gap="large")
            
            with col_val:
                st.subheader("Estado de Validación")
                if st.button("Ejecutar Validación DTD"):
                    st.session_state.pending_correction_xml = None
                    
                    is_valid, errors = transformer.validar_jats_xml(st.session_state.generated_xml)
                    if is_valid:
                        st.session_state.validation_errors = []
                        st.session_state.show_correction_chat = False
                        st.success("✅ XML Válido")
                        # Botón dentro del IF para no confundir
                    else:
                        st.session_state.validation_errors = errors
                        st.session_state.show_correction_chat = True 
                        st.error(f"❌ {len(errors)} errores encontrados")

                # Mostrar botón de ir a Resultados SOLO si está válido
                if not st.session_state.validation_errors and st.session_state.generated_xml: 
                     # Checkeamos si ya se validó (errors vacio, pero generated_xml existe... 
                     # podría no haberse validado aún, pero asumimos flujo normal)
                     # Mejor usar una flag si 'is_validated'
                     pass 

                if st.session_state.validation_errors:
                    for e in st.session_state.validation_errors:
                        st.warning(f"• {e}")
                    
                    st.divider()
                    if st.button("🛠️ Solucionar con IA", type="primary"):
                        st.session_state.show_correction_chat = True
                        if not st.session_state.correction_chat:
                             st.session_state.correction_chat.append({
                                 "role": "assistant", 
                                 "content": "He analizado los errores. ¿Cómo deseas proceder?"
                             })
                else:
                    # Si no hay errores, mostramos el botón de avanzar
                    st.markdown("---")
                    if st.button("➡️ Ir a Paso 4: Resultados"):
                        js_switch_tab(3)


            with col_chat:
                if st.session_state.show_correction_chat:
                    st.subheader("🤖 Asistente de Corrección")
                    
                    chat_container = st.container(height=350)
                    with chat_container:
                        for msg in st.session_state.correction_chat:
                            with st.chat_message(msg["role"]):
                                content = msg["content"]
                                if "```xml" in content and msg["role"] == "assistant":
                                    text_part = content.split("```xml")[0]
                                    st.write(text_part.strip())
                                    st.info("📄 (He generado un XML corregido. Revisa abajo 👇)")
                                else:
                                    st.write(content)

                    prompt = st.chat_input("Escribe tu instrucción...")
                    if prompt:
                        st.session_state.correction_chat.append({"role": "user", "content": prompt})
                        with chat_container:
                            with st.chat_message("user"):
                                st.write(prompt)
                            
                            with st.chat_message("assistant"):
                                with st.spinner("Consultando a Gemini..."):
                                    res = correction.corregir_xml(
                                        st.session_state.generated_xml,
                                        st.session_state.validation_errors,
                                        prompt
                                    )
                                    
                                    response_text = ""
                                    if res.get('returncode') == 0 and res.get('stdout'):
                                        response_text = res.get('stdout', '')
                                    else:
                                        response_text = f"Error: {res.get('stderr')}"
                                    
                                    import re
                                    match = re.search(r"```xml\s*(.*?)\s*```", response_text, re.DOTALL)
                                    if match:
                                        new_xml = match.group(1)
                                        st.session_state.pending_correction_xml = new_xml
                                        st.session_state.correction_chat.append({
                                            "role": "assistant", 
                                            "content": response_text 
                                        })
                                        st.rerun()
                                    else:
                                        st.write(response_text)
                                        st.session_state.correction_chat.append({"role": "assistant", "content": response_text})

                    if st.session_state.pending_correction_xml:
                        st.divider()
                        st.success("✨ ¡Corrección Generada!")
                        st.markdown("**La IA ha propuesto una nueva versión del XML. Revísala y aplícala si estás de acuerdo.**")
                        
                        cols_btn = st.columns([1, 1])
                        with cols_btn[0]:
                            if st.button("🔄 Reemplazar XML Original", type="primary"):
                                st.session_state.generated_xml = st.session_state.pending_correction_xml.strip()
                                st.session_state.validation_errors = []
                                st.session_state.pending_correction_xml = None
                                st.toast("XML Actualizado. Ejecuta validación nuevamente.", icon="🔄")
                                time.sleep(1.5)
                                st.rerun()
                        
                        with st.expander("Ver Diferencias / Nuevo XML", expanded=False):
                            st.code(st.session_state.pending_correction_xml, language='xml')

    # --- Tab 4 ---
    with tab4:
        st.header("Descargas y HTML")
        if not st.session_state.generated_xml:
            st.info("⚠️ Genera el contenido primero.")
        else:
            c1, c2 = st.columns(2)
            with c1:
                st.download_button(
                    "⬇️ Descargar XML",
                    st.session_state.generated_xml,
                    file_name="articulo.xml",
                    mime="application/xml"
                )
            with c2:
                if st.button("Generar HTML"):
                     with tempfile.NamedTemporaryFile(delete=False, suffix=".xml", mode='w', encoding='utf-8') as tmp:
                         tmp.write(st.session_state.generated_xml)
                         tmp_path = tmp.name
                     try:
                         data = xml_html.parse_jats(tmp_path)
                         html = xml_html.build_html(data)
                         st.session_state.generated_html = html
                     except Exception as e:
                         st.error(f"Error HTML: {e}")
                
                if st.session_state.generated_html:
                    st.download_button(
                        "⬇️ Descargar HTML",
                        st.session_state.generated_html,
                        file_name="articulo.html",
                        mime="text/html"
                    )
            
            if st.session_state.generated_html:
                st.markdown("---")
                components.html(st.session_state.generated_html, height=800, scrolling=True)

if __name__ == "__main__":
    main()
