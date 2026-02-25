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
from modules import config_store
from modules import prompts
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
        
        st.divider()
        st.markdown("### ⚙️ Configuración Global")
        
        # 1. API Key — persistente via SQLite
        # Cargar key guardada (solo la primera vez) a session_state
        if "_api_key_loaded" not in st.session_state:
            saved_key = config_store.load_api_key()
            if saved_key:
                st.session_state["gemini_api_key_input"] = saved_key
            st.session_state["_api_key_loaded"] = True
            
        if "_show_key_input" not in st.session_state:
            st.session_state["_show_key_input"] = False
        
        # Obtener key actual
        current_api_key = st.session_state.get("gemini_api_key_input") or os.environ.get("GEMINI_API_KEY", "")
        saved_key = config_store.load_api_key()
        has_saved_key = bool(saved_key)
        
        # 2. Selección de Modelo (Dinámico si hay key)
        @st.cache_data(ttl=3600)
        def get_available_models(api_key: str):
            default_models = [
                "gemini-2.5-flash",
                "gemini-2.5-pro",
                "gemini-2.5-flash-lite",
                "gemini-3-flash-preview",
                "gemini-3-pro-preview",
                "gemini-2.0-flash",
            ]
            if not api_key:
                return default_models
            
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                models = []
                for m in genai.list_models():
                    if 'generateContent' in m.supported_generation_methods:
                        name = m.name.replace("models/", "")
                        if name.startswith("gemini-") and "vision" not in name:
                            models.append(name)
                
                if models:
                    models.sort(reverse=True) # Sort to put newer versions first
                    if "gemini-2.5-flash" in models:
                        models.remove("gemini-2.5-flash")
                        models.insert(0, "gemini-2.5-flash") # Keep default fallback at top
                    return models
            except Exception:
                pass
            return default_models

        model_options = get_available_models(current_api_key)
        
        selected_model = st.selectbox(
            "Modelo IA:", 
            options=model_options, 
            index=0,
            key="selected_model_dropdown",
            help="Selecciona un modelo. La lista se actualiza automáticamente según lo disponible en tu cuenta. '2.5-flash' recomendado."
        )
        
        # Permitir modelo personalizado si es necesario (avanzado)
        use_custom_model = st.checkbox("Usar modelo personalizado o versión específica", value=False)
        if use_custom_model:
            selected_model = st.text_input("Escribe el nombre del modelo:", value=selected_model)
        
        # Store in session state for consistency
        st.session_state.selected_model = selected_model
        
        # 3. Mostrar UI de API Key debajo
        if has_saved_key and not st.session_state["_show_key_input"]:
            # Key guardada → ocultar, mostrar solo estado
            masked = saved_key[:4] + "•" * 20 + saved_key[-4:]
            st.text_input("Gemini API Key:", value=masked, disabled=True, key="_masked_key_display")
            st.caption("🔒 Key guardada de forma segura")
            
            key_col1, key_col2 = st.columns([1, 1])
            with key_col1:
                if st.button("✏️ Cambiar", key="change_key_btn", help="Ingresar una nueva API Key"):
                    st.session_state["_show_key_input"] = True
                    st.rerun()
            with key_col2:
                if st.button("🗑️ Borrar", key="delete_key_btn", help="Eliminar la API Key guardada"):
                    config_store.delete_api_key()
                    st.session_state["gemini_api_key_input"] = ""
                    st.session_state["_show_key_input"] = False
                    # Limpiar caché de modelos
                    get_available_models.clear()
                    st.rerun()
        else:
            # Sin key o modo edición → mostrar input
            api_key_input = st.text_input(
                "Gemini API Key:", 
                type="password", 
                value="" if st.session_state.get("_show_key_input") else st.session_state.get("gemini_api_key_input", ""),
                key="gemini_api_key_input",
                help="Pasos: 1. Ve a Google AI Studio. 2. Crea API Key. 3. Pégala aquí.",
                placeholder="Pega tu API Key aquí..."
            )
            
            current_key = st.session_state.get("gemini_api_key_input", "").strip()
            
            col_save, col_cancel = st.columns([1, 1])
            with col_save:
                if current_key:
                    if st.button("💾 Guardar", key="save_key_btn", type="primary"):
                        config_store.save_api_key(current_key)
                        st.session_state["_show_key_input"] = False
                        st.success("✅ Key guardada")
                        st.rerun()
            with col_cancel:
                if st.session_state["_show_key_input"] and has_saved_key:
                    if st.button("Cancelar", key="cancel_key_btn"):
                        st.session_state["_show_key_input"] = False
                        st.rerun()
            
            if not current_key and not has_saved_key:
                st.warning("⚠️ Sin API Key, las funciones de IA fallarán.")
                st.markdown("[Obtener Key](https://aistudio.google.com/app/apikey)")
        
        # ─── Panel de Uso de Tokens ───
        st.divider()
        with st.expander("📊 Uso de Tokens", expanded=False):
            token_summary = config_store.get_token_summary()
            selected_model_for_limits = st.session_state.get("selected_model", "gemini-2.5-flash")
            limits = config_store.get_free_tier_limits(selected_model_for_limits)
            
            st.caption(f"Modelo: **{selected_model_for_limits}**")
            
            # ── Requests diarias ──
            rpd_used = token_summary['today_requests']
            rpd_max = limits['rpd']
            rpd_progress = min(rpd_used / max(rpd_max, 1), 1.0)
            st.markdown(f"**Requests hoy:** {rpd_used:,} / {rpd_max:,}")
            st.progress(rpd_progress)
            
            # ── Tokens usados hoy ──
            tpm_max = limits['tpm']
            tokens_today = token_summary['today_tokens']
            st.markdown(f"**Tokens hoy:** {tokens_today:,}")
            st.markdown(f"**Límite por minuto (TPM):** {tpm_max:,}")
            st.markdown(f"**Límite requests/min (RPM):** {limits['rpm']}")
            
            # ── Advertencias ──
            if rpd_progress >= 0.8:
                st.warning(f"⚠️ {rpd_used}/{rpd_max} requests usadas hoy ({rpd_progress:.0%})")
            if rpd_progress >= 1.0:
                st.error("🚫 Límite diario alcanzado.")
            
            st.divider()
            
            # ── Histórico ──
            st.markdown(f"**Total histórico:** {token_summary['total_tokens']:,} tokens en {token_summary['total_requests']} ops")
            if token_summary['last_used']:
                st.caption(f"Último uso: {token_summary['last_used'][:16].replace('T', ' ')}")

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
                        # Variable de control para saber si debemos hacer rerun fuera del bloque status
                        should_rerun = False
                        
                        # Uso de st.status para feedback detallado y profesional
                        with st.status("⏳ Iniciando proceso de extracción...", expanded=True) as status:
                            try:
                                # 1. Validación inicial
                                status.update(label="⏳ Verificando archivo...")
                                status.write("📂 Validando la existencia del archivo en el servidor...")
                                fpath = st.session_state.uploaded_file_path
                                if not fpath or not os.path.exists(fpath):
                                    status.update(label="❌ Error: Archivo no encontrado", state="error")
                                    st.error("El archivo temporal se ha perdido. Por favor, cárgualo nuevamente.")
                                    st.stop()

                                # 2. Extraer Texto Estructurado
                                status.update(label="⏳ Extrayendo texto del documento DOCX...")
                                status.write("📄 Procesando párrafos y estructura del documento...")
                                if fpath.endswith('.docx'):
                                    extracted = transformer.extraer_contenido_estructurado(fpath)
                                    if not extracted:
                                        status.update(label="❌ Error en extracción de texto", state="error")
                                        st.error("No se pudo extraer texto del DOCX. El archivo podría estar corrupto o vacío.")
                                        st.stop()
                                    st.session_state.extracted_text = extracted
                                else:
                                    # Placeholder PDF
                                    st.session_state.extracted_text = "Contenido PDF extraído (placeholder)."
                                
                                # 3. Extraer Metadatos con IA
                                status.update(label="⏳ Analizando metadatos con Gemini AI...")
                                status.write("🤖 Extrayendo título, autores, fecha y DOI usando Inteligencia Artificial...")
                                extractor = metadata_processor.MetadataExtractor()
                                api_key = st.session_state.get('gemini_api_key_input') or os.environ.get("GEMINI_API_KEY")
                                selected_model = st.session_state.get("selected_model", "gemini-2.5-flash")
                                meta = extractor.extract_from_file(fpath, model_version=selected_model, api_key=api_key)
                                
                                # Verificar errores explícitos de la IA
                                if "error" in meta:
                                    status.update(label="❌ Error en análisis de IA", state="error")
                                    st.error(f"Error en análisis de IA: {meta['error']}")
                                    st.stop()
                                
                                st.session_state.extracted_metadata = meta
                                
                                # 4. Validar campos
                                status.update(label="⏳ Validando información extraída...")
                                status.write("✅ Comprobando que los campos obligatorios estén completos...")
                                missing = extractor.validate_metadata(meta)
                                st.session_state.metadata_missing_fields = missing
                                
                                if missing:
                                    # Usamos error para que quede rojo y llame la atención, ya que faltan datos obligatorios.
                                    status.update(label=f"⚠️ Faltan datos críticos: {', '.join(missing)}", state="error", expanded=False)
                                    st.warning(f"La extracción fue exitosa, pero faltan campos obligatorios: {', '.join(missing)}")
                                    
                                    # Generar mensaje de ayuda inicial para el chatbot
                                    if not st.session_state.metadata_chat:
                                        st.session_state.metadata_chat.append({
                                            "role": "assistant",
                                            "content": f"⚠️ **Atención**: No he podido detectar los siguientes campos en el documento: **{', '.join(missing)}**. \n\nPor favor, completa el formulario de metadatos manualmente."
                                        })
                                else:
                                    status.update(label="✨ ¡Extracción Completada con Éxito!", state="complete", expanded=False)
                                    st.success("Todos los metadatos críticos han sido encontrados.")
                                    st.toast("Análisis completo", icon="✅")
                                    st.session_state.metadata_verified = True
                                
                                # Indicamos que se debe hacer un rerun pero fuera del contexto
                                should_rerun = True
                                
                            except Exception as e:
                                # Prevenir la captura de Excepciones críticas de Streamlit que causan cuelgues (StopException, RerunException)
                                if e.__class__.__name__ in ["StopException", "RerunException"]:
                                    raise e
                                status.update(label="❌ Error Crítico Inesperado", state="error")
                                st.error(f"Ocurrió un error no controlado durante el proceso: {str(e)}")
                                # Imprimir traceback detallado para depuración
                                import traceback
                                st.expander("Ver detalles técnicos").code(traceback.format_exc())
                                # No hacemos rerun aquí para que el usuario vea el error
                        
                        # Mover sleep y rerun FUERA del bloque status para evitar deadlocks de UI de Streamlit
                        if should_rerun:
                            time.sleep(0.5)
                            st.rerun()
                else:
                    st.info("✅ Contenido y metadatos extraídos.")
                    if st.button("🔄 Re-extraer (Borrará cambios actuales)"):
                         st.session_state.extracted_text = ""
                         st.session_state.extracted_metadata = {}
                         st.session_state.metadata_chat = []
                         st.session_state.metadata_verified = False
                         st.rerun()

            with col2:
                # Vista previa colapsable para no ocupar tanto espacio si el form es importante
                if st.session_state.extracted_text:
                    with st.expander("📄 Vista Previa del Contenido (Texto)", expanded=False):
                        st.text_area("Texto Extraído", value=st.session_state.extracted_text, height=400, label_visibility="collapsed")
                
                # --- Sección de Revisión de Metadatos (Layout Mejorado) ---
                if st.session_state.extracted_text:
                    if not st.session_state.extracted_metadata:
                        st.session_state.extracted_metadata = {}
                        
                    with st.expander("📝 Formulario de Metadatos Extraídos", expanded=True):
                        st.markdown("Revisa los metadatos extraídos. Puedes editarlos antes de ir al Paso 2.")
                        
                        valid_container = st.container()
                        with valid_container.form("metadata_form", border=False):
                            meta = st.session_state.extracted_metadata
                            
                            # Preparar valor inicial para autores
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

                            # Callback para guardar
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
                                    st.session_state.metadata_verified = True 
                                    st.toast(f"⚠️ Guardado con faltantes: {', '.join(missing)}", icon="⚠️")
                                
                                # Bandera para cambiar de tab luego de que termine el callback
                                st.session_state.go_to_step_2 = True

                            # Layout en columnas con KEYS para el estado
                            mc1, mc2 = st.columns(2)
                            with mc1:
                                st.text_input("Título Artículo", value=meta.get('article_title', ''), key="meta_title")
                                st.text_input("Fecha (YYYY-MM-DD)", value=meta.get('publication_date', ''), key="meta_date")
                            with mc2:
                                st.text_input("Revista", value=meta.get('journal_title', ''), key="meta_journal")
                                st.text_input("DOI", value=meta.get('doi', ''), key="meta_doi")
                            
                            st.text_area("Autores (separados por coma)", value=authors_str, help="Ej: Juan Pérez, María González", key="meta_authors")

                            st.markdown("<br>", unsafe_allow_html=True)
                            st.form_submit_button("💾 Guardar e ir al paso 2", on_click=save_metadata_callback, type="primary")

                        # Mostrar resumen de validación (fuera del form pero dentro del expander)
                        if st.session_state.get('metadata_missing_fields'):
                            st.warning(f"⚠️ Campos pendientes: **{', '.join(st.session_state.metadata_missing_fields)}**")
                        elif st.session_state.get('metadata_verified'):
                            st.success("✅ Todos los metadatos obligatorios están completos.")

            # Detectar la intención de navegar y avisar vía JS render
            if st.session_state.pop("go_to_step_2", False):
                js_switch_tab(1)
                
    # --- Tab 2 ---
    with tab2:
        st.header("Generación XML con IA")
        if not st.session_state.extracted_text:
            st.info("⚠️ Carga un documento en el Paso 1 primero.")
        # Eliminamos bloqueo estricto, solo advertencia
        elif not st.session_state.get('metadata_verified', False):
             st.warning("⚠️ **Atención**: No has validado completamente los metadatos en el Paso 1. Esto podría generar un XML incompleto.")
        
        # --- Configuración ahora está en Sidebar ---
        if not st.session_state.get("gemini_api_key_input"):
             st.error("❌ Por favor configura tu API Key en la barra lateral izquierda.")
        
        can_generate = bool(st.session_state.extracted_text and st.session_state.get("gemini_api_key_input"))
        
        if st.button("Generar XML JATS", type="primary", disabled=not can_generate):
                progress_bar = st.progress(0, text="Iniciando...")
                status_text = st.empty()
                status_text.text("Preparando datos...")
                progress_bar.progress(10)
                time.sleep(0.5)
                
                selected_model = st.session_state.get("selected_model", "gemini-1.5-flash")
                status_text.text(f"Enviando a Gemini AI ({selected_model})...")
                
                # Pasar metadatos al prompt
                prompt = prompts.get_generation_prompt(
                    st.session_state.extracted_text, 
                    st.session_state.extracted_metadata
                )
                progress_bar.progress(30)
                
                # Llamada actualizada con parámetros de config
                result = transformer.invocar_gemini_cli(
                    prompt, 
                    model_version=selected_model,
                    api_key=st.session_state.get("gemini_api_key_input")
                )
                
                status_text.text("Procesando respuesta...")
                progress_bar.progress(80)
                
                if result.get('returncode') == 0 and result.get('stdout'):
                    xml_out = result.get('stdout', '')
                    
                    st.session_state.generated_xml = xml_out.strip()
                    st.session_state.validation_errors = []
                    st.session_state.correction_chat = []
                    st.session_state.show_correction_chat = False
                    st.session_state.pending_correction_xml = None
                    
                    # Registrar uso de tokens
                    tu = result.get('token_usage', {})
                    if tu.get('total_tokens', 0) > 0:
                        config_store.log_token_usage(
                            operation="generation",
                            model=selected_model,
                            prompt_tokens=tu.get('prompt_tokens', 0),
                            completion_tokens=tu.get('completion_tokens', 0),
                            total_tokens=tu.get('total_tokens', 0),
                        )
                    
                    progress_bar.progress(100)
                    tokens_msg = f" ({tu.get('total_tokens', 0):,} tokens)" if tu.get('total_tokens') else ""
                    status_text.text(f"¡Completado!{tokens_msg}")
                else:
                    progress_bar.empty()
                    status_text.error("Falló la generación.")
                    st.error(result.get('stderr'))
            
        if st.session_state.generated_xml:
            st.success("✅ XML Generado.")
            
            c_xml, c_form = st.columns(2, gap="large")
            
            with c_xml:
                st.subheader("XML Generado")
                st.code(st.session_state.generated_xml, language='xml')
                
            with c_form:
                st.subheader("Edición Rápida de Nodos")
                st.markdown("Revisa los componentes principales detectados. Modifica los campos vacíos o incorrectos. Los cambios se inyectarán en el XML automáticamente.")
                
                import re
                def extract_tag(xml_data: str, tag: str) -> str:
                    # Match exact tag name, followed by either > or a space and attributes
                    match = re.search(f"<{tag}(?:>|\\s[^>]*>)(.*?)</{tag}>", xml_data, re.DOTALL | re.IGNORECASE)
                    return match.group(1).strip() if match else ""
                    
                def inyectar_tag(xml_data: str, tag: str, new_val: str) -> str:
                    pattern = f"(<{tag}(?:>|\\s[^>]*>))(.*?)(</{tag}>)"
                    if re.search(pattern, xml_data, re.DOTALL | re.IGNORECASE):
                        return re.sub(pattern, f"\\g<1>{new_val}\\3", xml_data, flags=re.DOTALL | re.IGNORECASE)
                    return xml_data
                    
                with st.form("xml_quick_edit_form"):
                    xml_actual = st.session_state.generated_xml
                    
                    st.text_area("article-title (Título Principal)", 
                                 value=extract_tag(xml_actual, "article-title"), 
                                 key="xml_edit_article_title")
                                 
                    st.text_area("trans-title (Título Traducido)", 
                                 value=extract_tag(xml_actual, "trans-title"), 
                                 key="xml_edit_trans_title")
                                 
                    st.text_area("abstract (Resumen - ¡Mantén las etiquetas <p>!)", 
                                 value=extract_tag(xml_actual, "abstract"), 
                                 key="xml_edit_abstract", height=150)
                                 
                    st.text_area("kwd-group (Palabras clave - ¡Mantén las etiquetas <kwd>!)", 
                                 value=extract_tag(xml_actual, "kwd-group"), 
                                 key="xml_edit_kwd_group", height=100)
                                 
                    st.text_input("journal-title (Nombre de la Revista)", 
                                  value=extract_tag(xml_actual, "journal-title"), 
                                  key="xml_edit_journal_title")
                                  
                    st.text_input("publisher-name (Editorial)", 
                                  value=extract_tag(xml_actual, "publisher-name"), 
                                  key="xml_edit_publisher_name")

                    col_met1, col_met2 = st.columns(2)
                    with col_met1:
                        st.text_input("issn", value=extract_tag(xml_actual, "issn"), key="xml_edit_issn")
                        st.text_input("volume", value=extract_tag(xml_actual, "volume"), key="xml_edit_volume")
                        st.text_input("year (Año)", value=extract_tag(xml_actual, "year"), key="xml_edit_year")
                    with col_met2:
                        st.text_input("fpage (Página Inicial)", value=extract_tag(xml_actual, "fpage"), key="xml_edit_fpage")
                        st.text_input("lpage (Página Final)", value=extract_tag(xml_actual, "lpage"), key="xml_edit_lpage")
                        st.text_input("issue (Número)", value=extract_tag(xml_actual, "issue"), key="xml_edit_issue")

                    def aplicar_cambios_xml():
                        xml_mod = st.session_state.generated_xml
                        xml_mod = inyectar_tag(xml_mod, "article-title", st.session_state.xml_edit_article_title)
                        xml_mod = inyectar_tag(xml_mod, "trans-title", st.session_state.xml_edit_trans_title)
                        xml_mod = inyectar_tag(xml_mod, "abstract", st.session_state.xml_edit_abstract)
                        xml_mod = inyectar_tag(xml_mod, "kwd-group", st.session_state.xml_edit_kwd_group)
                        xml_mod = inyectar_tag(xml_mod, "journal-title", st.session_state.xml_edit_journal_title)
                        xml_mod = inyectar_tag(xml_mod, "publisher-name", st.session_state.xml_edit_publisher_name)
                        xml_mod = inyectar_tag(xml_mod, "issn", st.session_state.xml_edit_issn)
                        xml_mod = inyectar_tag(xml_mod, "volume", st.session_state.xml_edit_volume)
                        xml_mod = inyectar_tag(xml_mod, "issue", st.session_state.xml_edit_issue)
                        xml_mod = inyectar_tag(xml_mod, "fpage", st.session_state.xml_edit_fpage)
                        xml_mod = inyectar_tag(xml_mod, "lpage", st.session_state.xml_edit_lpage)
                        xml_mod = inyectar_tag(xml_mod, "year", st.session_state.xml_edit_year)
                        
                        st.session_state.generated_xml = xml_mod
                        st.session_state.go_to_step_3 = True

                    st.markdown("<br>", unsafe_allow_html=True)
                    st.form_submit_button("💾 Guardar y Validar", on_click=aplicar_cambios_xml, type="primary")

            if st.session_state.pop("go_to_step_3", False):
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
                
                # ======================================================
                # SECCIÓN 1: XML Corregido por IA (si hay pendiente)
                # ======================================================
                if st.session_state.pending_correction_xml:
                    st.info("🤖 **La IA ha generado una versión corregida.** Revísala y aplícala para continuar.")
                    with st.expander("📄 Ver XML corregido propuesto", expanded=False):
                        st.code(st.session_state.pending_correction_xml, language='xml')
                    
                    col_apply, col_discard = st.columns(2)
                    with col_apply:
                        if st.button("✅ Aplicar Corrección", type="primary", key="btn_apply_correction"):
                            corrected_xml = st.session_state.pending_correction_xml.strip()
                            st.session_state.generated_xml = corrected_xml
                            st.session_state.pending_correction_xml = None
                            
                            # Auto-validar el XML corregido
                            is_valid, errors = transformer.validar_jats_xml(corrected_xml)
                            st.session_state._validation_ran = True
                            if is_valid:
                                st.session_state.validation_errors = []
                                st.session_state.correction_chat = []
                                st.session_state.show_correction_chat = False
                            else:
                                st.session_state.validation_errors = errors
                            
                            st.rerun()
                    with col_discard:
                        if st.button("❌ Descartar", key="btn_discard_correction"):
                            st.session_state.pending_correction_xml = None
                            st.rerun()
                    
                    st.divider()
                
                # ======================================================
                # SECCIÓN 2: Botón de Validación DTD
                # ======================================================
                if st.button("Ejecutar Validación DTD", key="btn_validate_dtd"):
                    st.session_state.pending_correction_xml = None
                    st.session_state._validation_ran = True
                    
                    is_valid, errors = transformer.validar_jats_xml(st.session_state.generated_xml)
                    if is_valid:
                        st.session_state.validation_errors = []
                        st.session_state.show_correction_chat = False
                        st.session_state.correction_chat = []
                    else:
                        st.session_state.validation_errors = errors
                        st.session_state.show_correction_chat = True 
                        
                        # Auto-explicación en chatbot
                        if not st.session_state.correction_chat:
                             explanation_msg = f"❌ **He detectado {len(errors)} errores de validación.**\n\nExplicación preliminar:\n"
                             for i, err in enumerate(errors[:3]):
                                 explanation_msg += f"- `{err}`\n"
                             if len(errors) > 3:
                                 explanation_msg += f"... y {len(errors)-3} más."
                             explanation_msg += "\n\nPuedes intentar solucionarlos automáticamente con IA o editar manualmente."
                             st.session_state.correction_chat.append({"role": "assistant", "content": explanation_msg})
                    st.rerun()
                
                # ======================================================
                # SECCIÓN 3: Resultados de Validación
                # ======================================================
                if st.session_state.get("_validation_ran", False):
                    if st.session_state.validation_errors:
                        st.error(f"❌ {len(st.session_state.validation_errors)} errores encontrados")
                        for e in st.session_state.validation_errors:
                            st.warning(f"• {e}")
                        
                        st.divider()
                        st.markdown("### 🛠️ Corrección Asistida")
                        st.warning("⚠️ **Advertencia**: El uso de IA para corregir XML puede introducir alucinaciones. Revisa siempre el resultado.")
                        
                        if st.button("Intentar Solucionar con IA", type="primary", key="btn_ai_fix"):
                            st.session_state.show_correction_chat = True
                            with st.spinner("Analizando errores y buscando soluciones con IA..."):
                                api_key = st.session_state.get('gemini_api_key_input') or os.environ.get("GEMINI_API_KEY")
                                selected_model = st.session_state.get("selected_model", "gemini-2.5-flash")
                                res = correction.analizar_errores_inicial(
                                    st.session_state.generated_xml,
                                    st.session_state.validation_errors,
                                    model_version=selected_model,
                                    api_key=api_key
                                )
                                response_text = res.get('stdout', '') if res.get('returncode') == 0 else f"Error: {res.get('stderr')}"
                                
                                # Registrar uso de tokens de corrección
                                tu = res.get('token_usage', {})
                                if tu.get('total_tokens', 0) > 0:
                                    config_store.log_token_usage(
                                        operation="correction",
                                        model=st.session_state.get("selected_model", "gemini-2.5-flash"),
                                        prompt_tokens=tu.get('prompt_tokens', 0),
                                        completion_tokens=tu.get('completion_tokens', 0),
                                        total_tokens=tu.get('total_tokens', 0),
                                    )
                                
                                # invocar_gemini_cli ya limpia backticks via parse_model_response.
                                # Detectar si el resultado es XML directo o texto con explicación.
                                import re as _re_fix
                                stripped_resp = response_text.strip()
                                corrected_xml_fix = None
                                if stripped_resp.startswith('<'):
                                    corrected_xml_fix = stripped_resp
                                else:
                                    match_fix = _re_fix.search(r"```xml\s*(.*?)(?:```|$)", response_text, _re_fix.DOTALL | _re_fix.IGNORECASE)
                                    if match_fix:
                                        corrected_xml_fix = match_fix.group(1).strip()
                                
                                if corrected_xml_fix:
                                    st.session_state.pending_correction_xml = corrected_xml_fix
                                else:
                                    # No se pudo extraer XML, mostrar como texto
                                    st.session_state.pending_correction_xml = None
                                
                                st.session_state.correction_chat.append({
                                    "role": "assistant", 
                                    "content": response_text
                                })
                                st.rerun()
                    else:
                        # ======================================================
                        # SECCIÓN 4: Éxito + Botón Ir a Paso 4
                        # ======================================================
                        st.success("✅ ¡XML Válido! No se encontraron errores.")
                        st.markdown("---")
                        if st.button("➡️ Ir a Paso 4: Resultados", type="primary", key="btn_goto_step4"):
                            js_switch_tab(3)

            # ==============================================================
            # COLUMNA DERECHA: Chat de corrección
            # ==============================================================
            with col_chat:
                if st.session_state.show_correction_chat:
                    st.subheader("🤖 Asistente de Corrección")
                    
                    chat_container = st.container(height=400)
                    with chat_container:
                        for msg in st.session_state.correction_chat:
                            with st.chat_message(msg["role"]):
                                content = msg["content"]
                                if msg["role"] == "assistant":
                                    # Mostrar una porción para el chat y un expander para el XML completo
                                    st.write("Generé una posible corrección del XML.")
                                    if msg == st.session_state.correction_chat[-1] and st.session_state.get('pending_correction_xml'):
                                        st.info("📄 XML corregido generado. Aplícalo desde el panel izquierdo ⬅️")
                                    else:
                                        with st.expander("Ver XML generado en este paso", expanded=False):
                                            st.code(content, language='xml')
                                else:
                                    st.write(content)

                    prompt = st.chat_input("Escribe tu instrucción...", key="correction_chat_input")
                    if prompt:
                        st.session_state.correction_chat.append({"role": "user", "content": prompt})
                        with chat_container:
                            with st.chat_message("user"):
                                st.write(prompt)
                            
                            with st.chat_message("assistant"):
                                with st.spinner("Consultando a Gemini..."):
                                    api_key = st.session_state.get('gemini_api_key_input') or os.environ.get("GEMINI_API_KEY")
                                    selected_model = st.session_state.get("selected_model", "gemini-2.5-flash")
                                    res = correction.corregir_xml(
                                        st.session_state.generated_xml,
                                        st.session_state.validation_errors,
                                        prompt,
                                        model_version=selected_model,
                                        api_key=api_key
                                    )
                                    
                                    response_text = ""
                                    corrected_xml = None
                                    if res.get('returncode') == 0 and res.get('stdout'):
                                        response_text = res.get('stdout', '')
                                        # invocar_gemini_cli ya limpia backticks via parse_model_response.
                                        # Si el resultado parece XML directo (empieza con < ), usarlo.
                                        # Si aún tiene backticks (raro), extraer.
                                        import re as _re
                                        stripped = response_text.strip()
                                        if stripped.startswith('<'):
                                            corrected_xml = stripped
                                        else:
                                            match = _re.search(r"```xml\s*(.*?)(?:```|$)", response_text, _re.DOTALL | _re.IGNORECASE)
                                            if match:
                                                corrected_xml = match.group(1).strip()
                                    else:
                                        response_text = f"Error: {res.get('stderr')}"
                                    
                                    # Registrar uso de tokens del chatbot
                                    tu = res.get('token_usage', {})
                                    if tu.get('total_tokens', 0) > 0:
                                        config_store.log_token_usage(
                                            operation="chatbot",
                                            model=st.session_state.get("selected_model", "gemini-2.5-flash"),
                                            prompt_tokens=tu.get('prompt_tokens', 0),
                                            completion_tokens=tu.get('completion_tokens', 0),
                                            total_tokens=tu.get('total_tokens', 0),
                                        )
                                    
                                    if corrected_xml:
                                        st.session_state.pending_correction_xml = corrected_xml
                                        st.session_state.correction_chat.append({
                                            "role": "assistant", 
                                            "content": response_text 
                                        })
                                        st.rerun()
                                    else:
                                        st.write(response_text)
                                        st.session_state.correction_chat.append({"role": "assistant", "content": response_text})


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
                st.info("💡 La vista previa se abre en una pestaña nueva del navegador para que los enlaces y estilos funcionen correctamente.")
                
                # Codificar el HTML en base64 para abrirlo en una pestaña nueva
                import base64
                html_b64 = base64.b64encode(
                    st.session_state.generated_html.encode("utf-8")
                ).decode("utf-8")
                
                open_tab_js = f"""
                <script>
                function openHtmlPreview() {{
                    // Decodificar base64 a bytes y luego a texto UTF-8 correctamente
                    var binaryStr = atob("{html_b64}");
                    var bytes = new Uint8Array(binaryStr.length);
                    for (var i = 0; i < binaryStr.length; i++) {{
                        bytes[i] = binaryStr.charCodeAt(i);
                    }}
                    var htmlContent = new TextDecoder("utf-8").decode(bytes);
                    
                    var newWindow = window.open("", "_blank");
                    if (newWindow) {{
                        newWindow.document.open();
                        newWindow.document.write(htmlContent);
                        newWindow.document.close();
                    }} else {{
                        alert("El navegador bloqueó la ventana emergente. Permite pop-ups para este sitio.");
                    }}
                }}
                </script>
                <button onclick="openHtmlPreview()" style="
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    border: none;
                    padding: 12px 28px;
                    border-radius: 8px;
                    font-size: 16px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: transform 0.2s, box-shadow 0.2s;
                    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
                " onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 20px rgba(102, 126, 234, 0.6)';"
                   onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 15px rgba(102, 126, 234, 0.4)';">
                    🔍 Ver vista previa en nueva pestaña
                </button>
                """
                components.html(open_tab_js, height=80)

    # Sidebar Footer (Igual que en la app principal para consistencia)
    with st.sidebar:
        st.markdown("---")
        st.markdown(
            """
            <div class='branding'>
                <b>Universidad de Valparaíso</b><br>
                <small>Transformador XML JATS v0.65</small>
            </div>
            """, 
            unsafe_allow_html=True
        )

main()
