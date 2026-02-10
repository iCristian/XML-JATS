import streamlit as st
import os
import tempfile
import time
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List

from modules import transformer
from modules import xml_html
from modules import correction
from modules import metadata_processor
import streamlit.components.v1 as components

# Nota: st.set_page_config se ha movido a streamlit_app.py

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
    if 'extracted_metadata' not in st.session_state:
        st.session_state.extracted_metadata = {}
    if 'metadata_missing_fields' not in st.session_state:
        st.session_state.metadata_missing_fields = []
    if 'metadata_chat' not in st.session_state:
        st.session_state.metadata_chat = []
    if 'metadata_verified' not in st.session_state:
        st.session_state.metadata_verified = False

    if 'last_uploaded_filename' not in st.session_state:
        st.session_state.last_uploaded_filename = None

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
        uploaded_file = st.file_uploader("Selecciona un documento (.docx o .pdf)", type=['docx', 'pdf'])

        if uploaded_file is not None:
            # Detectar cambio de archivo usando el nombre original
            if st.session_state.last_uploaded_filename != uploaded_file.name:
                st.session_state.extracted_text = ""
                st.session_state.extracted_metadata = {}
                st.session_state.metadata_chat = []
                st.session_state.metadata_verified = False
                st.session_state.uploaded_file_path = None # Reiniciar path
                st.session_state.last_uploaded_filename = uploaded_file.name # Actualizar tracking

            # Guardar archivo temporal solo si no existe path o cambió
            if st.session_state.uploaded_file_path is None or not os.path.exists(st.session_state.uploaded_file_path):
                with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    st.session_state.uploaded_file_path = tmp_file.name

            col1, col2 = st.columns([1, 2], gap="medium")
            with col1:
                st.info(f"Archivo cargado: **{uploaded_file.name}**")
                
                # Mostrar botón solo si NO hay datos extraídos aún
                if not st.session_state.extracted_metadata and not st.session_state.extracted_text:
                    if st.button("🔍 Extraer Contenido y Metadatos", type="primary"):
                        # Uso de st.status para feedback detallado y profesional
                        with st.status("Iniciando proceso de extracción...", expanded=True) as status:
                            try:
                                # 1. Validación inicial
                                status.write("📂 Verificando archivo...")
                                fpath = st.session_state.uploaded_file_path
                                if not fpath or not os.path.exists(fpath):
                                    status.update(label="Error: Archivo no encontrado", state="error")
                                    st.error("El archivo temporal se ha perdido. Por favor, cárgualo nuevamente.")
                                    st.stop()

                                # 2. Extraer Texto Estructurado
                                status.write("📄 Extrayendo contenido del documento...")
                                if fpath.endswith('.docx'):
                                    extracted = transformer.extraer_contenido_estructurado(fpath)
                                    if not extracted:
                                        status.update(label="Error en extracción de texto", state="error")
                                        st.error("No se pudo extraer texto del DOCX. El archivo podría estar corrupto o vacío.")
                                        st.stop()
                                    st.session_state.extracted_text = extracted
                                else:
                                    # Placeholder PDF
                                    st.session_state.extracted_text = "Contenido PDF extraído (placeholder)."
                                
                                # 3. Extraer Metadatos con IA
                                status.write("🤖 Analizando metadatos con Gemini AI...")
                                extractor = metadata_processor.MetadataExtractor()
                                meta = extractor.extract_from_file(fpath)
                                
                                # Verificar errores explícitos de la IA
                                if "error" in meta:
                                    status.update(label="Error en análisis de IA", state="error")
                                    st.error(f"Fallo al conectar con Gemini: {meta['error']}")
                                    st.stop()
                                
                                st.session_state.extracted_metadata = meta
                                
                                # 4. Validar campos
                                status.write("✅ Validando información extraída...")
                                missing = extractor.validate_metadata(meta)
                                st.session_state.metadata_missing_fields = missing
                                
                                if missing:
                                    # FIX: state="warning" no existe, usamos "error" para destacar que faltan cosas, o "complete" con warning.
                                    # Usamos error para que quede rojo y llame la atención, ya que faltan datos obligatorios.
                                    status.update(label=f"⚠️ Faltan datos: {', '.join(missing)}", state="error", expanded=False)
                                    st.warning(f"La extracción fue exitosa, pero faltan campos obligatorios: {', '.join(missing)}")
                                    
                                    # Generar mensaje de ayuda inicial para el chatbot
                                    if not st.session_state.metadata_chat:
                                        st.session_state.metadata_chat.append({
                                            "role": "assistant",
                                            "content": f"⚠️ **Atención**: No he podido detectar los siguientes campos en el documento: **{', '.join(missing)}**. \n\nPor favor, completa el formulario de metadatos manualmente."
                                        })
                                else:
                                    status.update(label="¡Extracción Completada con Éxito!", state="complete", expanded=False)
                                    st.success("Todos los metadatos críticos han sido encontrados.")
                                    st.toast("Análisis completo", icon="✅")
                                    st.session_state.metadata_verified = True
                                
                                time.sleep(1) # Breve pausa para que el usuario vea el estado final
                                st.rerun()
                                
                            except Exception as e:
                                status.update(label="Error Crítico Inesperado", state="error")
                                st.error(f"Ocurrió un error no controlado durante el proceso: {str(e)}")
                                # Imprimir traceback detallado para depuración
                                import traceback
                                st.expander("Ver detalles técnicos").code(traceback.format_exc())
                                # No hacemos rerun aquí para que el usuario vea el error
                else:
                    st.info("✅ Contenido y metadatos extraídos.")
                    if st.button("🔄 Re-extraer (Borrará cambios actuales)"):
                         st.session_state.extracted_text = ""
                         st.session_state.extracted_metadata = {}
                         st.session_state.metadata_chat = []
                         st.session_state.metadata_verified = False
                         st.rerun()

            # --- Sección de Revisión de Metadatos (Layout Mejorado) ---
            if st.session_state.extracted_metadata:
                # Mostrar formulario destacado en el cuerpo principal
                st.divider()
                st.subheader("📝 Revisión de Metadatos Obligatorios")
                st.markdown("Por favor, verifica y completa la información antes de generar el XML.")

                valid_container = st.container()
                
                # Estilo para destacar el formulario
                valid_container.markdown("""
                <style>
                div[data-testid="stForm"] {
                    background-color: #f8f9fa;
                    padding: 20px;
                    border-radius: 10px;
                    border: 1px solid #ddd;
                }
                @media (prefers-color-scheme: dark) {
                    div[data-testid="stForm"] {
                        background-color: #262730;
                        border: 1px solid #444;
                    }
                }
                </style>
                """, unsafe_allow_html=True)
                
                with valid_container.form("metadata_form"):
                    meta = st.session_state.extracted_metadata
                    
                    # Preparar valor inicial para autores (lista de dicts -> string)
                    current_authors = meta.get('authors', [])
                    authors_str = ""
                    if isinstance(current_authors, list):
                        names = []
                        for a in current_authors:
                            if isinstance(a, dict):
                                full_name = f"{a.get('given_names', '')} {a.get('surname', '')}".strip()
                                if full_name:
                                    names.append(full_name)
                            elif isinstance(a, str):
                                names.append(a)
                        authors_str = ", ".join(names)

                    
                    # Callback para guardar y validar
                    def save_metadata_callback():
                        # Recuperar valores desde el estado del formulario
                        new_title = st.session_state.meta_title
                        new_date = st.session_state.meta_date
                        new_journal = st.session_state.meta_journal
                        new_doi = st.session_state.meta_doi
                        new_authors_str = st.session_state.meta_authors
                        
                        # Procesar autores
                        authors_list = []
                        if new_authors_str:
                            for name in new_authors_str.split(','):
                                n = name.strip()
                                if n:
                                    parts = n.split(' ')
                                    if len(parts) > 1:
                                        surname = parts[-1]
                                        given = " ".join(parts[:-1])
                                    else:
                                        surname = n
                                        given = ""
                                    authors_list.append({
                                        "given_names": given,
                                        "surname": surname,
                                        "aff_id": ""
                                    })

                        # Actualizar metadatos
                        st.session_state.extracted_metadata.update({
                            'article_title': new_title,
                            'journal_title': new_journal,
                            'publication_date': new_date,
                            'doi': new_doi,
                            'authors': authors_list
                        })
                        
                        # Validar
                        from modules import metadata_processor
                        extractor = metadata_processor.MetadataExtractor()
                        missing = extractor.validate_metadata(st.session_state.extracted_metadata)
                        st.session_state.metadata_missing_fields = missing
                        
                        if not missing:
                            st.session_state.metadata_verified = True
                            st.toast("✅ ¡Metadatos validados correctamente!", icon="🎉")
                        else:
                            # Permitimos avanzar pero con advertencia (estado verificado True para habilitar tabs, pero con missing fields)
                            # El usuario pidió: "ir al paso 2 lleve toda la información de jats más los faltantes" y "habilitarlo también"
                            st.session_state.metadata_verified = True 
                            st.toast(f"⚠️ Guardado con faltantes: {', '.join(missing)}", icon="⚠️")

                    # Layout en columnas con KEYS para el estado
                    mc1, mc2 = st.columns(2)
                    with mc1:
                        st.text_input("Título Artículo", value=meta.get('article_title', ''), key="meta_title")
                        st.text_input("Fecha (YYYY-MM-DD)", value=meta.get('publication_date', ''), key="meta_date")
                    with mc2:
                        st.text_input("Revista", value=meta.get('journal_title', ''), key="meta_journal")
                        st.text_input("DOI", value=meta.get('doi', ''), key="meta_doi")
                    
                    st.text_area("Autores (separados por coma)", value=authors_str, help="Ej: Juan Pérez, María González", key="meta_authors")

                    # Botón con callback
                    st.form_submit_button("💾 Guardar y Validar Metadatos", on_click=save_metadata_callback, type="primary")

                # Mostrar resumen de validación
                if st.session_state.get('metadata_missing_fields'):
                    st.warning(f"⚠️ Campos pendientes: **{', '.join(st.session_state.metadata_missing_fields)}**")
                elif st.session_state.get('metadata_verified'):
                    st.success("✅ Todos los metadatos obligatorios están completos.")

                # Botón de Navegación (Siempre visible si hay texto extraído)
                st.markdown("---")
                # Habilitar siempre si hay texto, pero advertir si faltan metadatos
                if st.button("➡️ Ir a Paso 2: Generación", type="secondary"):
                    js_switch_tab(1)

            with col2:
                # Vista previa colapsable para no ocupar tanto espacio si el form es importante
                if st.session_state.extracted_text:
                    with st.expander("📄 Vista Previa del Contenido (Texto)", expanded=False):
                        st.text_area("Texto Extraído", value=st.session_state.extracted_text, height=400, label_visibility="collapsed")
            
            # --- Sidebar: Asistente de Soporte ---
            with st.sidebar:
                if st.session_state.extracted_metadata:
                    st.divider()
                    st.header("🤖 Soporte Metadatos")
                    
                    # Mostrar estado actual en sidebar
                    if st.session_state.metadata_missing_fields:
                        st.error(f"Faltan: {len(st.session_state.metadata_missing_fields)} campos")
                    else:
                        st.success("Estado: Completo")

                    # Chat de Ayuda
                    meta_chat_container = st.container(height=400)
                    with meta_chat_container:
                        if not st.session_state.metadata_chat:
                            st.info("Aquí verás ayuda sobre los metadatos.")
                        
                        for msg in st.session_state.metadata_chat:
                            st.chat_message(msg["role"]).write(msg["content"])
                    
                    # Interacción de soporte y corrección manual
                    st.caption("¿Dudas o faltan datos? Escríbelo abajo.")
                    
                    # Chatbot Logic Tab 1
                    if prompt := st.chat_input("Ej: DOI: 10.1000/xyz o '¿Dónde está la fecha?'"):
                        st.session_state.metadata_chat.append({"role": "user", "content": prompt})
                        with meta_chat_container:
                            st.chat_message("user").write(prompt)
                            
                            # Lógica simple de parsing para actualizar metadatos
                            response = ""
                            prompt_lower = prompt.lower()
                            updated_field = None
                            
                            if "doi:" in prompt_lower:
                                new_doi = prompt.split("doi:")[-1].strip()
                                st.session_state.extracted_metadata['doi'] = new_doi
                                updated_field = "DOI"
                            elif "fecha:" in prompt_lower:
                                new_date = prompt.split("fecha:")[-1].strip()
                                st.session_state.extracted_metadata['publication_date'] = new_date
                                updated_field = "Fecha"
                            elif "título:" in prompt_lower or "titulo:" in prompt_lower:
                                new_title = prompt.split(":")[-1].strip()
                                st.session_state.extracted_metadata['article_title'] = new_title
                                updated_field = "Título"
                            elif "revista:" in prompt_lower:
                                new_journal = prompt.split("revista:")[-1].strip()
                                st.session_state.extracted_metadata['journal_title'] = new_journal
                                updated_field = "Revista"
                            
                            if updated_field:
                                response = f"✅ He actualizado el **{updated_field}** con: `{prompt.split(':')[-1].strip()}`. \n\n(Recuerda guardar los cambios en el formulario principal)."
                                # Re-validar
                                # Eliminamos import local que causa conflicto de scope
                                extractor = metadata_processor.MetadataExtractor()
                                missing = extractor.validate_metadata(st.session_state.extracted_metadata)
                                st.session_state.metadata_missing_fields = missing
                                st.rerun() # Recargar para reflejar cambios en formulario y sidebar
                            else:
                                # Respuesta genérica o ayuda
                                if "donde" in prompt_lower or "buscar" in prompt_lower:
                                    response = "🔍 El DOI suele estar en la primera página, cerca del título. La fecha a veces está en el pie de página."
                                else:
                                    response = "Entendido. Si quieres actualizar un dato, usa el formato `Campo: Valor` (ej: `DOI: 10.xxxx`)."

                            st.chat_message("assistant").write(response)
                            st.session_state.metadata_chat.append({"role": "assistant", "content": response})

    # --- Tab 2 ---
    with tab2:
        st.header("Generación XML con IA")
        if not st.session_state.extracted_text:
            st.info("⚠️ Carga un documento en el Paso 1 primero.")
        # Eliminamos bloqueo estricto, solo advertencia
        elif not st.session_state.get('metadata_verified', False):
             st.warning("⚠️ **Atención**: No has validado completamente los metadatos en el Paso 1. Esto podría generar un XML incompleto.")
        
        if st.button("Generar XML JATS", type="primary", disabled=not st.session_state.extracted_text):
                progress_bar = st.progress(0, text="Iniciando...")
                status_text = st.empty()
                status_text.text("Preparando datos...")
                progress_bar.progress(10)
                time.sleep(0.5)
                
                status_text.text("Enviando a Gemini AI...")
                
                # Pasar metadatos al prompt
                prompt = transformer.construir_prompt_avanzado(
                    st.session_state.extracted_text, 
                    st.session_state.extracted_metadata
                )
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
                    else:
                        st.session_state.validation_errors = errors
                        st.session_state.show_correction_chat = True 
                        st.error(f"❌ {len(errors)} errores encontrados")
                        
                        # Auto-explicación en chatbot
                        if not st.session_state.correction_chat:
                             explanation_msg = f"❌ **He detectado {len(errors)} errores de validación.**\n\nAquí tienes una explicación preliminar:\n"
                             for i, err in enumerate(errors[:3]): # Solo los primeros 3 para no saturar
                                 explanation_msg += f"- `{err}`\n"
                             if len(errors) > 3:
                                 explanation_msg += f"... y {len(errors)-3} más."
                             explanation_msg += "\n\nPuedes intentar solucionarlos automáticamente con IA o editar manualmente."
                             
                             st.session_state.correction_chat.append({"role": "assistant", "content": explanation_msg})

                # Mostrar botón de ir a Resultados SOLO si está válido
                if not st.session_state.validation_errors and st.session_state.generated_xml: 
                     pass 
                
                if st.session_state.validation_errors:
                    for e in st.session_state.validation_errors:
                        st.warning(f"• {e}")
                    
                    st.divider()
                    st.markdown("### 🛠️ Corrección Asistida")
                    st.warning("⚠️ **Advertencia**: El uso de IA para corregir XML puede introducir alucinaciones o cambios no deseados. Revisa siempre el resultado.")
                    
                    if st.button("Intentar Solucionar con IA", type="primary"):
                        st.session_state.show_correction_chat = True
                        # ... lógica existente de corrección ...
                        if not st.session_state.correction_chat or st.session_state.correction_chat[-1]["role"] != "assistant":
                             with st.spinner("Analizando errores y buscando soluciones..."):
                                res = correction.analizar_errores_inicial(
                                    st.session_state.generated_xml,
                                    st.session_state.validation_errors
                                )
                                response_text = res.get('stdout', '') if res.get('returncode') == 0 else f"Error: {res.get('stderr')}"
                                
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
                    # Si no hay errores y hay XML
                    if st.session_state.generated_xml and not st.session_state.validation_errors:
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
                        # ... (resto de lógica de chat) ...
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
                                # Limpiar chat para iniciar nueva validación limpia
                                st.session_state.correction_chat = []
                                st.session_state.show_correction_chat = False
                                
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

    # Sidebar Footer (Igual que en la app principal para consistencia)
    with st.sidebar:
        st.markdown("---")
        st.markdown(
            """
            <div class='branding'>
                <b>Universidad de Valparaíso</b><br>
                <small>Transformador XML JATS v0.6</small>
            </div>
            """, 
            unsafe_allow_html=True
        )

main()
