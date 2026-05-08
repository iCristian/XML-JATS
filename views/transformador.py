import atexit
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from xml.sax.saxutils import escape as xml_escape

import streamlit as st
import streamlit.components.v1 as components

from modules import (config_store, correction, metadata_processor, prompts,
                     transformer, xml_html)
from modules.llm_provider import (PROVIDER_REGISTRY, get_model_tier,
                                  get_provider, list_providers)
from modules.theme import render_hero_header, render_sidebar_footer

# Nota: st.set_page_config se ha movido a streamlit_app.py

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


# --- Limpieza de archivos temporales ---
_MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB
_ALLOWED_SUFFIXES = {'.docx', '.pdf'}
_MAGIC_BYTES = {
    '.docx': b'PK\x03\x04',
    '.pdf': b'%PDF',
}


def _cleanup_temp_files() -> None:
    """Elimina archivos temporales registrados en session_state."""
    for path in getattr(st.session_state, '_temp_files', []):
        try:
            if os.path.exists(path):
                os.unlink(path)
        except OSError:
            pass


atexit.register(_cleanup_temp_files)


@st.cache_data(ttl=600)
def _get_available_models(provider_id: str, api_key: str, host: Optional[str] = None) -> List[str]:
    """Lista modelos disponibles para un proveedor.

    Args:
        provider_id: ID del proveedor.
        api_key: API key del proveedor.
        host: Host opcional para proveedores locales (invalida cache).

    Returns:
        Lista de nombres de modelo.
    """
    provider_obj = PROVIDER_REGISTRY.get(provider_id)
    if not provider_obj:
        return []
    default_models = provider_obj.get_default_models()
    if not api_key and provider_id not in ("ollama", "lmstudio"):
        return default_models
    try:
        live_models = provider_obj.list_models(api_key or "ollama")
        if live_models:
            return live_models
    except Exception:
        pass
    return default_models


def _determine_recommended_mode() -> str:
    """Sugiere 'pipeline' o 'monolitico' según modelo y tamaño del artículo.

    Por defecto recomienda monolítico. Solo sugiere pipeline cuando el modelo
    es claramente pequeño (local o 3B-7B) o el artículo es extremadamente largo.

    Returns:
        'pipeline' si el modelo es local/small o el artículo supera 6 000 palabras;
        'monolitico' en caso contrario.
    """
    selected_model = st.session_state.get("selected_model", "")
    provider_id = st.session_state.get("_active_provider", "")

    # Criterio 1: solo modelos locales o clasificados como "small" (3B-7B)
    if provider_id in ("ollama", "lmstudio"):
        return "pipeline"
    tier = get_model_tier(selected_model)
    if tier == "small":
        return "pipeline"

    # Criterio 2: artículos extremadamente largos (>6 000 palabras ≈ 12+ páginas)
    extracted_text = st.session_state.get("extracted_text", "")
    word_count = len(extracted_text.split())
    if word_count > 6000:
        return "pipeline"

    return "monolitico"


def main() -> None:
    """Función principal de la aplicación Streamlit."""
    render_hero_header()
    
    with st.sidebar:
        # ─── Selección de Proveedor IA ───
        providers = list_providers(filter_unavailable=True)
        provider_ids = [p["id"] for p in providers]
        provider_names = {p["id"]: p["name"] for p in providers}
        
        active_provider = config_store.load_active_provider()
        
        # Fallback al primer proveedor disponible si el activo no está disponible
        if active_provider not in provider_ids and provider_ids:
            active_provider = provider_ids[0]
            config_store.save_active_provider(active_provider)
            
        active_idx = provider_ids.index(active_provider) if active_provider in provider_ids else 0

        selected_provider = st.selectbox(
            "🤖 Proveedor IA:",
            options=provider_ids,
            format_func=lambda pid: provider_names.get(pid, pid),
            index=active_idx,
            key="sidebar_provider_select",
        )
        if selected_provider != active_provider:
            config_store.save_active_provider(selected_provider)
        st.session_state["_active_provider"] = selected_provider

        # ─── Cargar API Key del proveedor activo ───
        _saved_key = config_store.load_provider_key(selected_provider)
        if not _saved_key:
            env_var = PROVIDER_REGISTRY[selected_provider].get_api_key_env_var()
            _saved_key = os.environ.get(env_var, "") if env_var else ""
        st.session_state["_active_api_key"] = _saved_key

        has_api_key = bool(st.session_state["_active_api_key"]) or selected_provider in ("ollama", "lmstudio")

        if selected_provider in ("ollama", "lmstudio"):
            is_ollama = selected_provider == "ollama"
            current_host = config_store.get_ollama_host() if is_ollama else config_store.get_lmstudio_host()
            name = "Ollama" if is_ollama else "LM Studio"
            
            new_host = st.text_input(f"🌐 URL Servidor {name}:", value=current_host, key=f"sidebar_{selected_provider}_host", help=f"Ej: http://localhost:{'11434' if is_ollama else '1234/v1'} (local) o remoto")
            if new_host != current_host:
                if is_ollama:
                    config_store.save_ollama_host(new_host)
                else:
                    config_store.save_lmstudio_host(new_host)
                st.toast(f"URL de {name} actualizada", icon="✅")
                st.rerun()
            
            # Verificar estado en vivo
            provider_obj = PROVIDER_REGISTRY[selected_provider]
            with st.spinner(f"Revisando {name}..."):
                is_ready = provider_obj._ensure_local_ready()
                if is_ready:
                    st.success(f"✅ {name} en ejecución")
                else:
                    st.error(f"❌ {name} no responde")
                    if "localhost" in current_host or "127.0.0.1" in current_host:
                        st.info("💡 Intentando iniciar servicio automáticamente...")
                    else:
                        st.warning("⚠️ Verifica que la URL del servidor remoto sea correcta.")

        # ─── Instrucciones (Popover minimalista) ───
        with st.popover("📋 Instrucciones"):
            st.markdown(
                "1. **Carga**: Sube el DOCX y extrae el texto.\n"
                "2. **Generación**: Crea el XML.\n"
                "3. **Validación**: Verifica y corrige errores.\n"
                "4. **Resultados**: Descarga el XML/HTML."
            )

        st.markdown("<br>", unsafe_allow_html=True)  # safe: static HTML

        # ─── Estado de API Key ───
        if has_api_key:
            st.markdown(
                f"<div style='font-size: 0.8rem; color: {'#34d399' if st.session_state.get('_theme_dark', True) else '#047857'}; margin-bottom: 0.5rem;'>🔑 ✅ {provider_names.get(selected_provider, selected_provider)} configurado</div>",
                unsafe_allow_html=True,  # safe: provider_names is an internal dict, not user input
            )
        else:
            st.markdown(
                f"<div style='font-size: 0.8rem; color: {'#e040fb' if st.session_state.get('_theme_dark', True) else '#7e22ce'}; margin-bottom: 0.5rem;'>🔑 ❌ Sin API Key (Ir a Configuración)</div>",
                unsafe_allow_html=True,  # safe: static HTML
            )

        # ─── Banner de cuota de pago activa ───
        if st.session_state.get("_paid_quota_active"):
            _mdl = st.session_state.get("selected_model", "gemini-2.5-flash")
            st.warning(
                f"💳 **Cuota gratuita diaria agotada para el modelo `{_mdl}`.** Las próximas llamadas podrían ser incurrir en cobros o dar error en tiers estrictos.",
                icon="⚠️",
            )

        # ─── Selección de Modelo ───
        st.markdown("📦 **Modelo**")

        # Obtener host actual para invalidar cache si cambia
        current_local_host = None
        if selected_provider == "ollama":
            current_local_host = config_store.get_ollama_host()
        elif selected_provider == "lmstudio":
            current_local_host = config_store.get_lmstudio_host()

        model_options = _get_available_models(selected_provider, st.session_state["_active_api_key"], current_local_host)

        selected_model = st.selectbox(
            "Modelo:",
            options=model_options,
            index=0,
            key="selected_model_dropdown",
            help="Selecciona el modelo del proveedor activo."
        )

        use_custom_model = st.checkbox("Modelo personalizado", value=False)
        if use_custom_model:
            selected_model = st.text_input("Nombre del modelo:", value=selected_model)

        st.session_state.selected_model = selected_model

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
    if '_temp_files' not in st.session_state:
        st.session_state._temp_files = []
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
    if 'pipeline_mode' not in st.session_state:
        st.session_state.pipeline_mode = "monolitico"
    if 'pipeline_mode_user_selected' not in st.session_state:
        st.session_state.pipeline_mode_user_selected = False
    # Reset a monolítico si el usuario no eligió manualmente y la sesión es antigua
    if not st.session_state.pipeline_mode_user_selected and st.session_state.pipeline_mode == "pipeline":
        st.session_state.pipeline_mode = "monolitico"
    if 'pipeline_result' not in st.session_state:
        st.session_state.pipeline_result = None
    if 'pipeline_provider_id' not in st.session_state:
        st.session_state.pipeline_provider_id = st.session_state.get("_active_provider", "gemini")
    if 'pipeline_model_name' not in st.session_state:
        st.session_state.pipeline_model_name = st.session_state.get("selected_model", "gemini-2.5-flash")

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
                # Limpiar archivo temporal anterior
                old_path = st.session_state.uploaded_file_path
                if old_path and os.path.exists(old_path):
                    try:
                        os.unlink(old_path)
                    except OSError:
                        pass
                st.session_state.uploaded_file_path = None # Reiniciar path
                st.session_state.last_uploaded_filename = uploaded_file.name # Actualizar tracking

            # Guardar archivo temporal solo si no existe path o cambió
            if st.session_state.uploaded_file_path is None or not os.path.exists(st.session_state.uploaded_file_path):
                data = uploaded_file.getvalue()
                suffix = Path(uploaded_file.name).suffix.lower()

                # Validar tamaño
                if len(data) > _MAX_UPLOAD_SIZE:
                    st.error("El archivo excede el tamaño máximo permitido (50 MB).")
                    st.stop()

                # Validar extensión
                if suffix not in _ALLOWED_SUFFIXES:
                    st.error("Tipo de archivo no permitido. Solo se aceptan .docx y .pdf.")
                    st.stop()

                # Validar magic bytes
                expected_magic = _MAGIC_BYTES.get(suffix, b'')
                if not data[:len(expected_magic)] == expected_magic:
                    st.error("El contenido del archivo no coincide con su extensión.")
                    st.stop()

                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
                    tmp_file.write(data)
                    st.session_state.uploaded_file_path = tmp_file.name
                os.chmod(tmp_file.name, 0o600)
                st.session_state._temp_files.append(tmp_file.name)

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
                                _prov_name = provider_names.get(st.session_state.get('_active_provider', 'gemini'), 'IA')
                                status.update(label=f"⏳ Analizando metadatos con {_prov_name}...")
                                status.write(f"🤖 Extrayendo título, autores, fecha y DOI usando {_prov_name}...")
                                extractor = metadata_processor.MetadataExtractor()
                                api_key = st.session_state.get('_active_api_key', '')
                                selected_model = st.session_state.get("selected_model", "gemini-2.5-flash")
                                _pid = st.session_state.get('_active_provider', 'gemini')
                                meta = extractor.extract_from_file(fpath, model_version=selected_model, api_key=api_key, provider_id=_pid)
                                
                                # Verificar errores explícitos de la IA
                                if "error" in meta:
                                    status.update(label="❌ Error en análisis de IA", state="error")
                                    st.error(f"Error en análisis de IA: {meta['error']}")
                                    st.stop()
                                
                                # Inyectar datos por defecto de la revista si existen
                                journal_defaults = config_store.get_journal_config()
                                if journal_defaults.get("title"):
                                    meta["journal_title"] = journal_defaults["title"]
                                if journal_defaults.get("publisher"):
                                    meta["publisher_name"] = journal_defaults["publisher"]
                                if journal_defaults.get("issn_print"):
                                    meta["issn"] = journal_defaults["issn_print"]
                                if journal_defaults.get("issn_electronic"):
                                    meta["issn_electronic"] = journal_defaults["issn_electronic"]
                                if journal_defaults.get("doi_base"):
                                    meta["doi_base"] = journal_defaults["doi_base"]
                                if journal_defaults.get("abbrev_title"):
                                    meta["abbrev_journal_title"] = journal_defaults["abbrev_title"]
                                if journal_defaults.get("journal_id"):
                                    meta["journal_id"] = journal_defaults["journal_id"]
                                if journal_defaults.get("license_url"):
                                    meta["license_url"] = journal_defaults["license_url"]
                                if journal_defaults.get("license_text"):
                                    meta["license_text"] = journal_defaults["license_text"]
                                if journal_defaults.get("subject"):
                                    meta["subject"] = journal_defaults["subject"]
                                
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
                                import logging
                                logging.exception("Error no controlado en procesamiento")
                                st.error("Ocurrió un error no controlado. Si persiste, contacte al administrador.")
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
                    
                    meta = st.session_state.extracted_metadata
                    
                    with st.expander("📝 Revisión de Metadatos", expanded=True):
                        st.markdown("Revisa los metadatos extraídos por la IA. Corrige o completa antes de generar el XML.")
                        
                        valid_container = st.container()
                        with valid_container.form("metadata_unified_form", border=False):
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

                            # Callback unificado
                            def save_unified_metadata_callback():
                                # --- Básicos ---
                                new_title = st.session_state.meta_title
                                new_date = st.session_state.meta_date
                                new_journal = st.session_state.meta_journal
                                new_doi = st.session_state.meta_doi
                                new_authors_str = st.session_state.meta_authors
                                new_volume = st.session_state.get("meta_volume", "")
                                new_issue = st.session_state.get("meta_issue", "")
                                new_pages = st.session_state.get("meta_pages", "")
                                
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
                                
                                fpage, lpage = "", ""
                                if new_pages:
                                    pg_parts = new_pages.replace("–", "-").split("-")
                                    fpage = pg_parts[0].strip()
                                    lpage = pg_parts[1].strip() if len(pg_parts) > 1 else fpage

                                # --- Enriquecidos ---
                                enrichment_fields = {
                                    "has_version_description": "version_description",
                                    "has_related_resources": "related_resources",
                                    "has_volume_special_id": "volume_special_id",
                                    "has_volume_series": "volume_series",
                                    "has_issue_special_id": "issue_special_id",
                                    "has_issue_title": "issue_title",
                                    "has_issue_sponsor": "issue_sponsor",
                                    "has_article_section": "article_section",
                                    "has_isbn": "isbn",
                                    "has_external_links": "external_links",
                                    "has_supplementary_material": "supplementary_material",
                                    "has_funding": "funding_description",
                                    "has_acknowledgments": "acknowledgments",
                                    "has_conference": "conference_description",
                                    "has_publication_history": "publication_history",
                                }
                                enrichment_updates = {}
                                for has_key, val_key in enrichment_fields.items():
                                    has_val = st.session_state.get(f"enr_{has_key}", False)
                                    val = st.session_state.get(f"enr_{val_key}", "")
                                    enrichment_updates[has_key] = bool(has_val)
                                    enrichment_updates[val_key] = str(val).strip()
                                
                                enrichment_updates["is_supplement"] = bool(st.session_state.get("enr_is_supplement", False))
                                enrichment_updates["supplement_description"] = str(st.session_state.get("enr_supplement_description", "")).strip()
                                enrichment_updates["contact_email"] = str(st.session_state.get("enr_contact_email", "")).strip()

                                st.session_state.extracted_metadata.update({
                                    'article_title': new_title,
                                    'journal_title': new_journal,
                                    'publication_date': new_date,
                                    'doi': new_doi,
                                    'volume': new_volume,
                                    'issue': new_issue,
                                    'fpage': fpage,
                                    'lpage': lpage,
                                    'authors': authors_list,
                                    **enrichment_updates,
                                })
                                
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

                            st.markdown("**📋 Metadatos Básicos**")
                            mc1, mc2 = st.columns(2)
                            with mc1:
                                st.text_input("Título Artículo", value=meta.get('article_title', ''), key="meta_title")
                                st.text_input("Fecha (YYYY-MM-DD)", value=meta.get('publication_date', ''), key="meta_date")
                            with mc2:
                                st.text_input("Revista", value=meta.get('journal_title', ''), key="meta_journal")
                                st.text_input("DOI", value=meta.get('doi', ''), key="meta_doi")
                            
                            st.text_area("Autores (separados por coma)", value=authors_str, help="Ej: Juan Pérez, María González", key="meta_authors")

                            mv1, mv2, mv3 = st.columns(3)
                            with mv1:
                                st.text_input("Volumen", value=meta.get('volume', ''), placeholder="Ej: 5", key="meta_volume")
                            with mv2:
                                st.text_input("Número (Issue)", value=meta.get('issue', ''), placeholder="Ej: 2", key="meta_issue")
                            with mv3:
                                pages_val = f"{meta.get('fpage', '')}–{meta.get('lpage', '')}".replace("–", "-") if meta.get('fpage') else ""
                                st.text_input("Páginas (ej: 13-21)", value=pages_val, placeholder="Ej: 13-21", key="meta_pages")

                            st.markdown("---")
                            st.markdown("**🔍 Enriquecimiento (la IA intentó detectarlos desde el texto)**")
                            st.caption("Deja vacío lo que no aplica. Solo marca el checkbox y completa si aplica a tu artículo.")

                            st.markdown("*Identificación y Relaciones*")
                            c1, c2 = st.columns(2)
                            with c1:
                                st.checkbox("¿Es una versión específica? (preprint, revisada, etc.)", value=meta.get("has_version_description", False), key="enr_has_version_description")
                                st.text_input("Descripción de la versión", value=meta.get("version_description", ""), key="enr_version_description")
                            with c2:
                                st.checkbox("¿Hay recursos relacionados? (dataset, software, artículos)", value=meta.get("has_related_resources", False), key="enr_has_related_resources")
                                st.text_input("Recursos relacionados", value=meta.get("related_resources", ""), key="enr_related_resources")

                            st.markdown("*Revista — Volumen y Número*")
                            c1, c2 = st.columns(2)
                            with c1:
                                st.checkbox("¿Volumen con identificador especial?", value=meta.get("has_volume_special_id", False), key="enr_has_volume_special_id")
                                st.text_input("Identificador del volumen", value=meta.get("volume_special_id", ""), key="enr_volume_special_id")
                                st.checkbox("¿Pertenece a una serie?", value=meta.get("has_volume_series", False), key="enr_has_volume_series")
                                st.text_input("Serie del volumen", value=meta.get("volume_series", ""), key="enr_volume_series")
                            with c2:
                                st.checkbox("¿Número con identificador especial?", value=meta.get("has_issue_special_id", False), key="enr_has_issue_special_id")
                                st.text_input("Identificador del número", value=meta.get("issue_special_id", ""), key="enr_issue_special_id")
                                st.checkbox("¿Número con título específico?", value=meta.get("has_issue_title", False), key="enr_has_issue_title")
                                st.text_input("Título del número", value=meta.get("issue_title", ""), key="enr_issue_title")
                                st.checkbox("¿Patrocinador para este número?", value=meta.get("has_issue_sponsor", False), key="enr_has_issue_sponsor")
                                st.text_input("Patrocinador", value=meta.get("issue_sponsor", ""), key="enr_issue_sponsor")

                            st.markdown("*Artículo y Publicación*")
                            c1, c2 = st.columns(2)
                            with c1:
                                st.checkbox("¿Es parte de una sección específica?", value=meta.get("has_article_section", False), key="enr_has_article_section")
                                st.text_input("Sección / Parte", value=meta.get("article_section", ""), key="enr_article_section")
                                st.checkbox("¿Hay ISBN asociado?", value=meta.get("has_isbn", False), key="enr_has_isbn")
                                st.text_input("ISBN", value=meta.get("isbn", ""), key="enr_isbn")
                            with c2:
                                st.checkbox("¿Es parte de un suplemento?", value=meta.get("is_supplement", False), key="enr_is_supplement")
                                st.text_input("Descripción del suplemento", value=meta.get("supplement_description", ""), key="enr_supplement_description")
                                st.text_input("Email de contacto principal", value=meta.get("contact_email", ""), key="enr_contact_email")

                            st.markdown("*Enlaces y Material Adicional*")
                            st.checkbox("¿Enlaces externos importantes? (repositorio, web, código)", value=meta.get("has_external_links", False), key="enr_has_external_links")
                            st.text_area("Enlaces externos", value=meta.get("external_links", ""), key="enr_external_links")
                            st.checkbox("¿Material suplementario? (videos, datos, anexos)", value=meta.get("has_supplementary_material", False), key="enr_has_supplementary_material")
                            st.text_area("Material suplementario", value=meta.get("supplementary_material", ""), key="enr_supplementary_material")

                            st.markdown("*Financiamiento y Agradecimientos*")
                            c1, c2 = st.columns(2)
                            with c1:
                                st.checkbox("¿Recibió financiamiento?", value=meta.get("has_funding", False), key="enr_has_funding")
                                st.text_area("Descripción del financiamiento", value=meta.get("funding_description", ""), key="enr_funding_description")
                            with c2:
                                st.checkbox("¿Apoyo significativo adicional?", value=meta.get("has_acknowledgments", False), key="enr_has_acknowledgments")
                                st.text_area("Agradecimientos / Apoyo", value=meta.get("acknowledgments", ""), key="enr_acknowledgments")

                            st.markdown("*Conferencia e Historial*")
                            c1, c2 = st.columns(2)
                            with c1:
                                st.checkbox("¿Versión extendida de conferencia?", value=meta.get("has_conference", False), key="enr_has_conference")
                                st.text_input("Conferencia (nombre, fecha, lugar)", value=meta.get("conference_description", ""), key="enr_conference_description")
                            with c2:
                                st.checkbox("¿Historial de publicación relevante?", value=meta.get("has_publication_history", False), key="enr_has_publication_history")
                                st.text_input("Historial (recibido, aceptado, revisado)", value=meta.get("publication_history", ""), key="enr_publication_history")

                            st.markdown("<br>", unsafe_allow_html=True)
                            st.form_submit_button("💾 Guardar y validar metadatos", on_click=save_unified_metadata_callback, type="primary")

                        if st.session_state.get('metadata_missing_fields'):
                            st.warning(f"⚠️ Campos pendientes: **{', '.join(st.session_state.metadata_missing_fields)}**")
                        elif st.session_state.get('metadata_verified'):
                            st.success("✅ Todos los metadatos obligatorios están completos.")
                            st.divider()
                            if st.button("✅ Confirmar todo e ir al Paso 2", type="primary", use_container_width=True, key="btn_go_step2"):
                                st.session_state.go_to_step_2 = True
                                st.rerun()
                        else:
                            st.warning("⚠️ Completa y guarda los metadatos básicos antes de avanzar.")

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
        
        # ─── Selector de Modo de Procesamiento ────────────────────
        effective_mode = st.session_state.pipeline_mode
        if not st.session_state.get("pipeline_mode_user_selected"):
            effective_mode = _determine_recommended_mode()
            st.session_state.pipeline_mode = effective_mode

        st.markdown("#### 🎯 Estrategia de Transformación")

        mode_cols = st.columns(2, gap="medium")
        modes = [
            {
                "id": "monolitico",
                "icon": "🧠",
                "title": "Monolítico",
                "subtitle": "Un solo prompt, artículo completo.",
                "detail": "Envía el documento entero al modelo en una sola llamada. Ideal cuando el modelo tiene suficiente contexto.",
                "pros": ["Máxima coherencia global", "Una sola llamada a la API", "Mejor para modelos grandes (Gemini, GPT-4, Claude)"],
                "cons": ["Requiere modelo con gran ventana de contexto", "Puede truncar documentos largos (> 3.000 palabras)"],
                "ideal": "Modelos grandes + artículos cortos",
            },
            {
                "id": "pipeline",
                "icon": "⚡",
                "title": "Pipeline por Fases",
                "subtitle": "🧪 Experimental — Divide, transforma y ensambla.",
                "detail": "Separa el artículo en Front, Body por secciones y Back. Cada parte se transforma por separado y luego se ensambla vía DOM. **Esta estrategia está en fase experimental y puede tener limitaciones.**",
                "pros": ["Compatible con modelos pequeños (Ollama, LM Studio)", "Maneja artículos de cualquier longitud", "Sanitización DOM garantiza XML well-formed"],
                "cons": ["Múltiples llamadas a la API", "Requiere ensamblaje posterior", "Fase experimental — puede presentar errores estructurales"],
                "ideal": "Modelos locales o artículos extensos",
            },
        ]

        selected_mode = st.session_state.pipeline_mode
        for idx, mode in enumerate(modes):
            with mode_cols[idx]:
                is_selected = selected_mode == mode["id"]
                is_recommended = effective_mode == mode["id"]

                with st.container(border=True):
                    # Header
                    header = f"**{mode['icon']} {mode['title']}**"
                    if is_recommended and not st.session_state.get("pipeline_mode_user_selected"):
                        header += "  &nbsp;`:rainbow[✨ RECOMENDADO]`"
                    st.markdown(header)
                    st.caption(mode["subtitle"])

                    # Descripción
                    st.markdown(mode["detail"])

                    # Expandible con pros/cons (más compacto)
                    with st.expander("Ver detalles", expanded=False):
                        st.markdown("**Ventajas**")
                        for p in mode["pros"]:
                            st.markdown(f"- :green-badge[✓] {p}")
                        st.markdown("**Limitaciones**")
                        for c in mode["cons"]:
                            st.markdown(f"- :orange-badge[▲] {c}")
                        st.markdown(f"**Ideal para:** *{mode['ideal']}*")

                    # Botón de acción
                    btn_type = "primary" if is_selected else "secondary"
                    btn_label = "✓  Seleccionado" if is_selected else f"Usar {mode['title']}"
                    if st.button(btn_label, key=f"mode_btn_{mode['id']}", type=btn_type, use_container_width=True):
                        st.session_state.pipeline_mode = mode["id"]
                        st.session_state.pipeline_mode_user_selected = True
                        st.rerun()

        processing_mode = st.session_state.pipeline_mode
        
        # ─── Configuración Multi-Agente (solo Monolítico) ─────────
        if processing_mode == "monolitico":
            configured_pids = config_store.get_configured_providers()
            # Filtrar automáticamente proveedores locales si están disponibles
            if "ollama" not in configured_pids and "ollama" in provider_ids:
                configured_pids.append("ollama")
            if "lmstudio" not in configured_pids and "lmstudio" in provider_ids:
                configured_pids.append("lmstudio")
                
            # Solo mostrar como seleccionables en la batalla a los proveedores funcionales
            available_pids = [p for p in configured_pids if p in PROVIDER_REGISTRY and PROVIDER_REGISTRY[p].is_available()]
            provider_names_multi = {p: PROVIDER_REGISTRY[p].display_name for p in available_pids}
            
            st.subheader("Selección de Agentes y Modelos")
            st.markdown("Selecciona los proveedores y modelos de IA que participarán en la Batalla de Modelos:")
            
            selected_pids = st.multiselect(
                "1. Elige los Proveedores:",
                options=available_pids,
                format_func=lambda p: provider_names_multi[p],
                default=[available_pids[0]] if available_pids else []
            )
            
            battle_roster = []
            
            if selected_pids:
                cols = st.columns(len(selected_pids)) if len(selected_pids) <= 3 else st.columns(3)
                
                for i, pid in enumerate(selected_pids):
                    with cols[i % len(cols)]:
                        provider_obj = PROVIDER_REGISTRY[pid]
                        api_key = config_store.load_provider_key(pid) if pid not in ("ollama", "lmstudio") else pid
                        
                        _host = None
                        if pid == "ollama":
                            _host = config_store.get_ollama_host()
                        elif pid == "lmstudio":
                            _host = config_store.get_lmstudio_host()
                            
                        models = _get_available_models(pid, api_key, _host)
                        
                        selected_models = st.multiselect(
                            f"Modelos de {provider_names_multi[pid]}:",
                            options=models,
                            default=[models[0]] if models else [],
                            key=f"battle_models_{pid}"
                        )
                        
                        for mdl in selected_models:
                            battle_roster.append({
                                "label": f"{provider_names[pid]} ({mdl})",
                                "provider": pid,
                                "model": mdl,
                                "api_key": api_key
                            })
                            
            if battle_roster:
                st.info("🤖 **Participantes en la batalla:** " + ", ".join([f"`{r['label']}`" for r in battle_roster]))
                
            can_generate = bool(st.session_state.extracted_text and len(battle_roster) > 0)
            
            if st.button("Generar XML JATS", type="primary", disabled=not can_generate):
                st.session_state.generated_versions = []
                st.session_state.generated_xml = None
                st.session_state.validation_errors = []
                st.session_state._validation_ran = False
                
                st.session_state._validation_ran_batalla = False
                
                total_agents = len(battle_roster)
                
                prompt = prompts.get_generation_prompt(
                    st.session_state.extracted_text, 
                    st.session_state.extracted_metadata
                )
                
                # Contenedores para el estado de cada agente progresivo
                status_containers = {}
                for r in battle_roster:
                    agent_label = r["label"]
                    status_containers[agent_label] = st.empty()
                    status_containers[agent_label].info(f"⏳ {agent_label}: Esperando turno...")
                    
                for idx, r in enumerate(battle_roster):
                    agent_label = r["label"]
                    _pid = r["provider"]
                    _model = r["model"]
                    _key = r["api_key"]
                    status_containers[agent_label].warning(f"🔄 {agent_label}: Procesando XML [{idx+1}/{total_agents}]...")
                    
                    result = transformer.invocar_llm(
                        prompt, 
                        model_version=_model,
                        api_key=_key,
                        provider_id=_pid,
                    )
                    
                    if result.get('quota_exceeded'):
                        st.session_state["_paid_quota_active"] = True
                    
                    if result.get('returncode') == 0 and result.get('stdout'):
                        xml_out = result.get('stdout', '').strip()
                        st.session_state.generated_versions.append({
                            "label": agent_label,
                            "provider": _pid,
                            "model": _model,
                            "xml": xml_out,
                            "tokens": result.get('token_usage', {}).get('total_tokens', 0)
                        })
                        status_containers[agent_label].success(f"✅ {agent_label}: Generado correctamente.")
                        
                        tu = result.get('token_usage', {})
                        if tu.get('total_tokens', 0) > 0:
                            config_store.log_token_usage(
                                operation="generation",
                                model=_model,
                                prompt_tokens=tu.get('prompt_tokens', 0),
                                completion_tokens=tu.get('completion_tokens', 0),
                                total_tokens=tu.get('total_tokens', 0),
                            )
                    else:
                        status_containers[agent_label].error(f"❌ {agent_label}: Fallo al generar. {result.get('stderr')}")
                        
                # Evaluación Inmediata en Tab 2
                if st.session_state.generated_versions:
                    with st.spinner("Realizando evaluación experta inmediata (DTD JATS)..."):
                        for version in st.session_state.generated_versions:
                            is_valid, errors = transformer.validar_jats_xml(version['xml'])
                            is_complete, semantic_warnings = transformer.verificar_completitud_xml(version['xml'], st.session_state.extracted_text)
                            
                            score = max(0, 100 - (len(errors) * 5)) if not is_valid else 100
                            if not is_complete:
                                score = min(score, 20)  # Penalización severa por XML vacío
                                errors = semantic_warnings + errors # Agregar como errores para forzar corrección
                                
                            version['score'] = score
                            version['errors'] = errors
                        st.session_state._validation_ran_batalla = True
                        st.session_state.generated_versions.sort(key=lambda x: x.get('score', 0), reverse=True)
                
                st.session_state.show_correction_chat = False
                st.session_state.pending_correction_xml = None
                
                st.rerun()
        
        # ─── Modo Pipeline ────────────────────────────────────────
        else:
            st.subheader("⚡ Pipeline por Fases")
            
            # Configuración del chunk
            chunk_cfg = st.expander("Configuración avanzada del Pipeline")
            with chunk_cfg:
                # ─── Selector de proveedor y modelo para el Pipeline ───
                all_providers = list_providers(filter_unavailable=True)
                all_provider_ids = [p["id"] for p in all_providers]
                all_provider_names = {p["id"]: p["name"] for p in all_providers}

                pipe_provider = st.selectbox(
                    "🤖 Proveedor para el Pipeline:",
                    options=all_provider_ids,
                    format_func=lambda pid: all_provider_names.get(pid, pid),
                    index=all_provider_ids.index(st.session_state.pipeline_provider_id)
                    if st.session_state.pipeline_provider_id in all_provider_ids else 0,
                    key="pipeline_provider_select",
                    help="Proveedor de IA que ejecutará el Pipeline. Puede ser diferente del usado para metadatos."
                )
                if pipe_provider != st.session_state.pipeline_provider_id:
                    st.session_state.pipeline_provider_id = pipe_provider
                    # Resetear modelo al default del nuevo proveedor
                    default_models = PROVIDER_REGISTRY[pipe_provider].get_default_models()
                    st.session_state.pipeline_model_name = default_models[0] if default_models else ""
                    st.rerun()

                # API key del proveedor seleccionado para el pipeline
                _key_pipe = config_store.load_provider_key(pipe_provider) or ""
                if not _key_pipe and pipe_provider not in ("ollama", "lmstudio"):
                    env_var = PROVIDER_REGISTRY[pipe_provider].get_api_key_env_var()
                    _key_pipe = os.environ.get(env_var, "") if env_var else ""

                # Host para locales
                pipe_host = None
                if pipe_provider == "ollama":
                    pipe_host = config_store.get_ollama_host()
                elif pipe_provider == "lmstudio":
                    pipe_host = config_store.get_lmstudio_host()

                # Selector de modelo
                pipe_model_options = _get_available_models(pipe_provider, _key_pipe, pipe_host)
                pipe_model = st.selectbox(
                    "📦 Modelo para el Pipeline:",
                    options=pipe_model_options,
                    index=pipe_model_options.index(st.session_state.pipeline_model_name)
                    if st.session_state.pipeline_model_name in pipe_model_options else 0,
                    key="pipeline_model_select",
                    help="Modelo que ejecutará cada fase del Pipeline."
                )
                if pipe_model != st.session_state.pipeline_model_name:
                    st.session_state.pipeline_model_name = pipe_model
                    st.rerun()

                _pid_pipe = pipe_provider
                _mdl_pipe = pipe_model

                # Verificación de estado para locales
                if pipe_provider in ("ollama", "lmstudio"):
                    is_ready = PROVIDER_REGISTRY[pipe_provider]._ensure_local_ready()
                    if not is_ready:
                        st.warning(f"⚠️ {all_provider_names.get(pipe_provider)} no responde. Verifica que esté en ejecución.")

                # Autodetección de context window y tier
                from modules.llm_provider import estimate_context_window, get_model_tier
                detected_ctx = estimate_context_window(_pid_pipe, _mdl_pipe, _key_pipe)
                model_tier = get_model_tier(_mdl_pipe)

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Contexto detectado", f"{detected_ctx:,} tokens")
                with col2:
                    tier_emoji = {"small": "🐤", "medium": "🦅", "large": "🦖"}.get(model_tier, "❓")
                    st.metric("Tier del modelo", f"{tier_emoji} {model_tier.upper()}")
                with col3:
                    st.caption(f"{_pid_pipe} / {_mdl_pipe}")

                col_chunk, col_para = st.columns(2)
                with col_chunk:
                    max_input_tokens = st.selectbox(
                        "Ventana de contexto (tokens):",
                        options=[2048, 4096, 8192, 16384, 32768, 65536, 131072],
                        index=2,
                        help="Tamaño máximo del prompt. Reduce este valor si usas modelos locales pequeños (ej. 2048 para Ollama en celulares)."
                    )
                with col_para:
                    parallel_toggle = st.toggle(
                        "Procesar en paralelo",
                        value=False,
                        help="Activa el procesamiento paralelo de secciones (más rápido, pero consume más RAM/GPU). Desactívalo para móviles."
                    )

                use_light = st.toggle(
                    "Usar prompts ligeros",
                    value=(model_tier == "small"),
                    help="Reduce las instrucciones del prompt para modelos pequeños (3B-7B). Mejora estabilidad en Ollama móvil."
                )

                st.checkbox(
                    "Forzar verificación IA de integridad",
                    value=True,
                    key="pipeline_force_ai_verify",
                    help="Si está activado, se ejecutará un modelo LLM para comparar el texto original contra el XML generado y detectar omisiones o parafraseos."
                )
            
            can_generate_pipe = bool(st.session_state.extracted_text and st.session_state.get('uploaded_file_path'))
            
            if st.button("▶️ Ejecutar Pipeline por Fases", type="primary", disabled=not can_generate_pipe):
                from modules.pipeline_orchestrator import PipelineOrchestrator
                from modules import config_store as cs
                
                st.session_state.generated_versions = []
                st.session_state.generated_xml = None
                st.session_state.validation_errors = []
                st.session_state._validation_ran = False
                st.session_state.pipeline_result = None
                
                journal_cfg = cs.get_journal_config()
                
                with st.status("⚡ Ejecutando Pipeline por Fases...", expanded=True) as status:
                    orchestrator = PipelineOrchestrator(
                        provider_id=_pid_pipe,
                        model=_mdl_pipe,
                        api_key=_key_pipe,
                        max_input_tokens=max_input_tokens,
                        max_output_tokens=max_input_tokens,
                        parallel=parallel_toggle,
                        max_workers=4,
                        use_light_prompts=use_light,
                        enable_ai_verification=st.session_state.get("pipeline_force_ai_verify", True),
                    )
                    
                    status.write("🔄 Fase 0: Segmentación semántica del documento...")
                    result = orchestrator.run(
                        docx_path=st.session_state.uploaded_file_path,
                        metadata=st.session_state.extracted_metadata,
                        journal_config=journal_cfg,
                    )
                    
                    # Mostrar progreso por fase
                    for stage in result.stages:
                        icon = "✅" if stage.status == "success" else "⚠️" if stage.status == "warning" else "❌" if stage.status == "failed" else "⏳"
                        status.write(f"{icon} **{stage.name}**: {stage.status.upper()}{(' — ' + stage.message) if stage.message else ''}")
                    
                    if result.error:
                        status.update(label="❌ Pipeline falló", state="error", expanded=True)
                        st.error(f"Error en pipeline: {result.error}")
                    else:
                        status.update(label="✅ Pipeline completado", state="complete", expanded=False)
                        st.session_state.pipeline_result = result
                        st.session_state.generated_xml = result.xml_string
                        st.session_state.validation_errors = result.dtd_errors
                        st.session_state._validation_ran = True
                        
                        # Crear una única versión para compatibilidad con el leaderboard
                        st.session_state.generated_versions = [{
                            "label": f"Pipeline ({_pid_pipe} / {_mdl_pipe})",
                            "provider": _pid_pipe,
                            "model": _mdl_pipe,
                            "xml": result.xml_string,
                            "tokens": 0,
                            "score": 100 if result.is_valid_dtd and (result.integrity_report.is_complete if result.integrity_report else False) else max(0, 100 - len(result.dtd_errors) * 5),
                            "errors": result.dtd_errors,
                        }]
                        
                        # Log de tokens (estimado, ya que el pipeline hace múltiples llamadas)
                        config_store.log_token_usage(
                            operation="generation_pipeline",
                            model=_mdl_pipe,
                            prompt_tokens=0,
                            completion_tokens=0,
                            total_tokens=0,
                        )
                        
                        # Mostrar reporte de integridad
                        if result.integrity_report:
                            if result.integrity_report.is_complete:
                                st.success("🔒 **Integridad textual 100%**: Todas las secciones coinciden con el original.")
                            else:
                                st.warning("⚠️ **Problemas de integridad detectados**:")
                                for w in result.integrity_report.warnings[:5]:
                                    st.write(f"- {w}")
                                if len(result.integrity_report.warnings) > 5:
                                    st.write(f"- ... y {len(result.integrity_report.warnings) - 5} más.")
                        
                        # Mostrar reporte de verificación IA
                        if result.ai_verification:
                            any_problems = any(not r.is_complete for r in result.ai_verification.values())
                            if any_problems:
                                st.warning("🤖 **Verificación IA detectó discrepancias**:")
                                for sec_title, verify in result.ai_verification.items():
                                    if not verify.is_complete and verify.problems:
                                        st.write(f"- **{sec_title}**: {verify.problems[0].description}")
                            else:
                                st.success("🤖 **Verificación IA**: Sin discrepancias semánticas detectadas.")
                        
                        st.rerun()
            
            # Mostrar resultado previo del pipeline si existe
            if st.session_state.get('pipeline_result'):
                pipe_res = st.session_state.pipeline_result
                st.markdown("---")
                st.markdown("### 📊 Resultado del Pipeline")
                
                cols = st.columns(4)
                with cols[0]:
                    st.metric("DTD Válido", "✅ Sí" if pipe_res.is_valid_dtd else "❌ No")
                with cols[1]:
                    integrity_ok = pipe_res.integrity_report.is_complete if pipe_res.integrity_report else False
                    st.metric("Integridad", "✅ OK" if integrity_ok else "⚠️ Falla")
                with cols[2]:
                    ai_ok = not any(not r.is_complete for r in (pipe_res.ai_verification or {}).values())
                    st.metric("Verificación IA", "✅ OK" if ai_ok else "⚠️ Falla")
                with cols[3]:
                    st.metric("Errores DTD", len(pipe_res.dtd_errors))
                
                if pipe_res.dtd_errors:
                    with st.expander("Ver errores DTD"):
                        for err in pipe_res.dtd_errors[:10]:
                            st.code(err)
                
                if pipe_res.integrity_report and not pipe_res.integrity_report.is_complete:
                    with st.expander("Ver diff de integridad"):
                        for diff in pipe_res.integrity_report.section_diffs:
                            if not diff.match:
                                st.markdown(f"**{diff.title}**")
                                if diff.diff_html:
                                    st.markdown(diff.diff_html, unsafe_allow_html=True)
                                else:
                                    st.write("Sección modificada (hash no coincide).")

        if st.session_state.get('generated_versions'):
            st.success(f"✅ Se evaluaron {len(st.session_state.generated_versions)} versión(es).")
            
            st.markdown("### 🏆 Evaluación y Puntajes Rápidos")
            st.markdown("Hemos evaluado cada versión generada aplicando **descuentos del 5% por cada error de DTD**. ¡Elige tu favorita para enviarla al editor de corrección final (Tab 3)!")
            
            for idx, version in enumerate(st.session_state.generated_versions):
                 score_color = "🟢" if version['score'] >= 90 else "🟠" if version['score'] >= 60 else "🔴"
                 
                 with st.container(border=True):
                     st.markdown(f"#### #{idx+1} | {version['label']}")
                     st.markdown(f"Puntuación Calidad JATS: {score_color} **{version['score']}%**")
                     if version['score'] == 100:
                         st.success("✅ XML Limpio, estándar XML-JATS respetado.")
                     elif version['score'] >= 90:
                         st.info("⚠️ XML casi perfecto. Mínimas advertencias.")
                     else:
                         st.warning(f"⚠️ {len(version['errors'])} advertencias/errores estructurales detectados.")
                     
                     def make_winner_callback(w_xml, w_errs, w_score):
                         st.session_state.generated_xml = w_xml
                         st.session_state.validation_errors = w_errs
                         st.session_state.generated_score = w_score
                         st.session_state.correction_chat = []
                         st.session_state.show_correction_chat = False
                         st.session_state.pending_correction_xml = None
                         st.session_state._validation_ran = True # Skip re-validation later
                         st.session_state.go_to_step_3 = True # Advance automatically to Tab 3
                     
                     btn_text = f"Pasar a Validar ({version['label']})" if idx == 0 else f"Seleccionar opción alternativa ({version['label']})"
                     st.button(btn_text, key=f"btn_tab2_win_{idx}", type="primary" if idx == 0 else "secondary", on_click=make_winner_callback, args=(version['xml'], version['errors'], version['score']))
                     
                     with st.expander(f"Inspeccionar código generado por {version['label']}", expanded=False):
                         st.code(version['xml'][:1500] + "\n\n... (truncado por memoria visual)", language='xml')
            
        if st.session_state.get('generated_xml'):
            st.success("🏆 XML Ganador Establecido.")
            
            c_xml, c_form = st.columns(2, gap="large")
            
            with c_xml:
                st.subheader("XML Resultante")
                st.code(st.session_state.generated_xml, language='xml')
                
            with c_form:
                st.subheader("Edición Rápida de Nodos")
                st.markdown("Revisa los componentes principales detectados. Modifica los campos vacíos o incorrectos. Los cambios se inyectarán en el XML automáticamente.")
                
                import re

                _VALID_TAG_RE = re.compile(r'^[a-zA-Z][a-zA-Z0-9\-]*$')
                _TAGS_WITH_SUBTAGS = {'abstract', 'kwd-group'}

                def extract_tag(xml_data: str, tag: str) -> str:
                    if not _VALID_TAG_RE.match(tag):
                        return ""
                    safe_tag = re.escape(tag)
                    match = re.search(f"<{safe_tag}(?:>|\\s[^>]*>)(.*?)</{safe_tag}>", xml_data[:500_000], re.DOTALL | re.IGNORECASE)
                    return match.group(1).strip() if match else ""
                    
                def inyectar_tag(xml_data: str, tag: str, new_val: str) -> str:
                    if not _VALID_TAG_RE.match(tag):
                        return xml_data
                    safe_tag = re.escape(tag)
                    # Escapar contenido solo para tags simples (sin sub-etiquetas)
                    if tag not in _TAGS_WITH_SUBTAGS:
                        new_val = xml_escape(new_val)
                    pattern = f"(<{safe_tag}(?:>|\\s[^>]*>))(.*?)(</{safe_tag}>)"
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

                    st.markdown("<br>", unsafe_allow_html=True)  # safe: static HTML
                    st.form_submit_button("💾 Guardar y Validar", on_click=aplicar_cambios_xml, type="primary")

            if st.session_state.pop("go_to_step_3", False):
                js_switch_tab(2)

    # --- Tab 3 ---
    with tab3:
        st.header("Validación y Corrección")
        if not st.session_state.get('generated_xml'):
            st.info("⚠️ Por favor, ve al Paso 2 (Generación) y selecciona un Ganador XML primero.")
        else:
            st.subheader("Estado de Validación (XML Seleccionado)")
            
            if 'generated_score' in st.session_state:
                 score = st.session_state.generated_score
                 score_color = "🟢" if score >= 90 else "🟠" if score >= 60 else "🔴"
                 st.markdown(f"**Puntuación de Calidad JATS:** {score_color} **{score}%**")
            
            def explain_dtd_error(error_msg: str) -> str:
                import re
                match = re.search(r"Element ([\w\-]+) content does not follow the DTD, expecting (.*?), got (.*)", error_msg)
                if match:
                    return f"🚨 Etiqueta `<{match.group(1)}>` incompleta o en orden incorrecto. Faltan elementos como `{match.group(2)}`."
                match2 = re.search(r"No declaration for attribute ([\w\-]+) of element ([\w\-]+)", error_msg)
                if match2:
                    return f"⚠️ Atributo no válido. El atributo `{match2.group(1)}` no se permite en `<{match2.group(2)}>`."
                match3 = re.search(r"Element ([\w\-]+) is not declared in (.*?)(?:List of possible elements:(.*))?", error_msg)
                if match3:
                     return f"🚨 Etiqueta desconocida. `<{match3.group(1)}>` no está permitida en esta sección."
                part_split = error_msg.split(':', 4)
                if len(part_split) > 4:
                     return f"⚠️ Problema estructural JATS: {part_split[-1].strip()}"
                return f"⚠️ {error_msg}"
            
            # ======================================================
            # SECCIÓN 1: XML Corregido por IA (si hay pendiente)
            # ======================================================
            if st.session_state.get('pending_correction_xml'):
                st.info("🤖 **La IA ha ejecutado el plan y generado una versión corregida.** Revísala y aplícala para re-evaluar.")
                with st.expander("📄 Ver XML corregido propuesto", expanded=False):
                    st.code(st.session_state.pending_correction_xml, language='xml')
                
                col_apply, col_discard = st.columns(2)
                with col_apply:
                    if st.button("✅ Aplicar Corrección y Re-validar", type="primary", key="btn_apply_correction"):
                        corrected_xml = st.session_state.pending_correction_xml.strip()
                        st.session_state.generated_xml = corrected_xml
                        st.session_state.pending_correction_xml = None
                        
                        # Auto-validar el XML corregido
                        is_valid, errors = transformer.validar_jats_xml(corrected_xml)
                        is_complete, semantic_warns = transformer.verificar_completitud_xml(corrected_xml, st.session_state.extracted_text)
                        
                        st.session_state._validation_ran = True
                        if is_valid and is_complete:
                            st.session_state.validation_errors = []
                            st.session_state.proposed_correction_plan = None
                        else:
                            st.session_state.validation_errors = semantic_warns + errors
                            st.session_state.proposed_correction_plan = None  # Reset plan to force re-evaluation
                        
                        st.rerun()
                with col_discard:
                    if st.button("❌ Descartar", key="btn_discard_correction"):
                        st.session_state.pending_correction_xml = None
                        st.rerun()
                
                st.divider()
            
            # ======================================================
            # SECCIÓN 2: Botón de Validación XML-JATS
            # ======================================================
            if st.button("Ejecutar Validación XML-JATS", key="btn_validate_dtd"):
                st.session_state.pending_correction_xml = None
                st.session_state.proposed_correction_plan = None
                st.session_state._validation_ran = True
                
                is_valid, errors = transformer.validar_jats_xml(st.session_state.generated_xml)
                is_complete, semantic_warns = transformer.verificar_completitud_xml(st.session_state.generated_xml, st.session_state.extracted_text)
                
                if is_valid and is_complete:
                    st.session_state.validation_errors = []
                    st.session_state.generated_score = 100
                else:
                    st.session_state.validation_errors = semantic_warns + errors
                    base_score = max(0, 100 - (len(errors) * 5))
                    st.session_state.generated_score = min(base_score, 20) if not is_complete else base_score
                st.rerun()
            
            # ======================================================
            # SECCIÓN 3: Resultados y Plan de Cambios ASISTIDO
            # ======================================================
            if st.session_state.get("_validation_ran", False):
                if st.session_state.get('validation_errors'):
                    
                    # Detectar si es un error semántico (generado por verificación heurística)
                    has_semantic_error = any("peligrosamente corto" in e or "omisión de texto" in e for e in st.session_state.validation_errors)
                    
                    if has_semantic_error:
                        st.error("⚠️ **ALERTA CRÍTICA DE EDICIÓN**: El XML es técnicamente válido según JATS, pero parece estar [VACÍO / INCOMPLETO]. Faltan fragmentos clave del texto original o la IA usó delimitadores en lugar de transcribir los párrafos. Se recomienda descartar este XML y generar uno nuevo usando un modelo de mayor capacidad.")
                    else:
                        st.error(f"❌ {len(st.session_state.validation_errors)} errores encontrados en la validación.")
                        
                    with st.expander("📋 Ver lista de errores detallados y simplificados", expanded=True):
                        for e in st.session_state.validation_errors:
                            st.info(f"• {explain_dtd_error(e) if 'Faltan fragmentos' not in e and 'El cuerpo' not in e and 'omisión de texto' not in e else e}")
                    
                    st.divider()
                    st.markdown("### 🛠️ Corrección Inteligente Asistida")
                    
                    if not st.session_state.get('proposed_correction_plan'):
                        st.info("El asistente revisará los problemas y te hará preguntas sencillas en lenguaje natural sobre los datos que faltan. No necesitas saber nada de XML.")
                        if st.button("🔍 Analizar y preguntarme qué falta", type="primary", key="btn_ai_plan"):
                            with st.spinner("Analizando los errores y preparando preguntas..."):
                                api_key = st.session_state.get('_active_api_key', '')
                                selected_model = st.session_state.get("selected_model", "gemini-2.5-flash")
                                _pid = st.session_state.get('_active_provider', 'gemini')
                                res = correction.generar_plan_correccion(
                                    st.session_state.validation_errors,
                                    metadata=st.session_state.get("extracted_metadata"),
                                    model_version=selected_model,
                                    api_key=api_key,
                                    provider_id=_pid,
                                )
                                response_text = res.get('stdout', '') if res.get('returncode') == 0 else f"Error: {res.get('stderr')}"
                                
                                if res.get('quota_exceeded'):
                                    st.session_state["_paid_quota_active"] = True
                                    
                                # Registrar uso de tokens del plan
                                tu = res.get('token_usage', {})
                                if tu.get('total_tokens', 0) > 0:
                                    config_store.log_token_usage(
                                        operation="correction_plan",
                                        model=st.session_state.get("selected_model", "gemini-2.5-flash"),
                                        prompt_tokens=tu.get('prompt_tokens', 0),
                                        completion_tokens=tu.get('completion_tokens', 0),
                                        total_tokens=tu.get('total_tokens', 0),
                                    )
                                
                                st.session_state.proposed_correction_plan = response_text
                                st.rerun()
                    else:
                        # Mostrar el plan como preguntas amigables
                        st.markdown("#### 📋 Información requerida para completar tu artículo")
                        st.info("💬 **Responde las preguntas a continuación en tus propias palabras.** El asistente se encargará de toda la parte técnica del XML.")
                        st.markdown(st.session_state.proposed_correction_plan)
                        
                        st.markdown("#### ✍️ Tus respuestas")
                        user_feedback = st.text_area(
                            "Escribe aquí los datos que te solicitó el asistente (volumen, número de la revista, nombres de autores, correos, fechas, etc.):",
                            height=120,
                            placeholder="Ejemplo:\n- El artículo se publica en el Vol. 5, Núm. 2\n- El autor de correspondencia es Juan Pérez, correo jperez@universidad.cl\n- Fecha de recibido: 15/03/2025, aceptado: 20/06/2025"
                        )
                        
                        if st.button("🚀 Aplicar correcciones y generar XML", type="primary", key="btn_ai_execute"):
                            with st.spinner("Incorporando tus datos y corrigiendo el documento..."):
                                api_key = st.session_state.get('_active_api_key', '')
                                selected_model = st.session_state.get("selected_model", "gemini-2.5-flash")
                                _pid = st.session_state.get('_active_provider', 'gemini')
                                res = correction.corregir_xml(
                                    st.session_state.generated_xml,
                                    st.session_state.validation_errors,
                                    user_feedback,
                                    model_version=selected_model,
                                    api_key=api_key,
                                    provider_id=_pid,
                                )
                                response_text = ""
                                corrected_xml = None
                                if res.get('returncode') == 0 and res.get('stdout'):
                                    response_text = res.get('stdout', '')
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
                                    
                                if res.get('quota_exceeded'):
                                    st.session_state["_paid_quota_active"] = True
                                
                                # Registrar uso de tokens de la corrección
                                tu = res.get('token_usage', {})
                                if tu.get('total_tokens', 0) > 0:
                                    config_store.log_token_usage(
                                        operation="correction",
                                        model=st.session_state.get("selected_model", "gemini-2.5-flash"),
                                        prompt_tokens=tu.get('prompt_tokens', 0),
                                        completion_tokens=tu.get('completion_tokens', 0),
                                        total_tokens=tu.get('total_tokens', 0),
                                    )
                                
                                if corrected_xml:
                                    st.session_state.pending_correction_xml = corrected_xml
                                    st.rerun()
                                else:
                                    st.error("No se pudo extraer el XML corregido. Por favor intenta de nuevo.")
                                    with st.expander("Ver respuesta del modelo", expanded=True):
                                        st.write(response_text)
                else:
                    st.success("✅ ¡XML Válido! No se encontraron errores estructurales.")
                    st.markdown("---")
                    if st.button("➡️ Ir a Paso 4: Resultados", type="primary", key="btn_goto_step4"):
                        js_switch_tab(3)


    # --- Tab 4 ---
    with tab4:
        st.header("Descargas y HTML")
        if not st.session_state.generated_xml:
            st.info("⚠️ Genera el contenido primero.")
        else:
            c1, c2 = st.columns(2)
            with c1:
                st.download_button(
                    label="⬇️ Descargar XML",
                    data=st.session_state.generated_xml.encode("utf-8"),
                    file_name="articulo.xml",
                    mime="application/octet-stream"
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
                         st.error(f"**Error al generar HTML:** {e}")
                         st.info("⚠️ **El XML generado tiene etiquetas mal formadas (ej. no cerradas correctamente).**\n\nVe a la pestaña **'Validación y Corrección'** y haz clic en *Ejecutar Validación XML-JATS*. La IA detectará los errores y propondrá automáticamente la corrección de las etiquetas.")
                
                if st.session_state.generated_html:
                    st.download_button(
                        label="⬇️ Descargar HTML",
                        data=st.session_state.generated_html.encode("utf-8"),
                        file_name="articulo.html",
                        mime="application/octet-stream"
                    )
            
            # Advertencia de validación SciELO
            st.markdown("---")
            st.warning(
                "⚠️ **Validación obligatoria antes de enviar a SciELO**\n\n"
                "El XML generado debe pasar por el validador oficial de SciELO para asegurar el cumplimiento del estándar SPS. "
                "Incluso si la validación DTD local es exitosa, pueden existir reglas específicas de SciELO no cubiertas por esta herramienta.\n\n"
                "🔗 [Validador SciELO Style Checker](https://manager.scielo.org/tools/validators/stylechecker/)"
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
                    background: linear-gradient(135deg, #0891b2 0%, #6d28d9 100%);
                    color: white;
                    border: none;
                    padding: 12px 28px;
                    border-radius: 10px;
                    font-family: 'Inter', -apple-system, sans-serif;
                    font-size: 15px;
                    font-weight: 600;
                    letter-spacing: 0.01em;
                    cursor: pointer;
                    transition: transform 0.2s cubic-bezier(0.34,1.56,0.64,1), box-shadow 0.2s ease, filter 0.2s ease;
                    box-shadow: 0 4px 15px rgba(8, 145, 178, 0.4);
                " onmouseover="this.style.transform='translateY(-2px) scale(1.03)'; this.style.boxShadow='0 6px 24px rgba(8,145,178,0.45), 0 0 40px rgba(124,58,237,0.25)'; this.style.filter='brightness(1.15)';"
                   onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 15px rgba(8, 145, 178, 0.4)'; this.style.filter='brightness(1)';">
                    🔍 Ver vista previa en nueva pestaña
                </button>
                """
                components.html(open_tab_js, height=80)

    # Sidebar Footer: Mini-resumen de Tokens + Branding
    with st.sidebar:
        st.divider()
        # ── Mini Resumen de Tokens ──
        token_summary = config_store.get_token_summary()
        _model = st.session_state.get("selected_model", "gemini-2.5-flash")
        _limits = config_store.get_free_tier_limits(_model)
        _rpd_used = token_summary['today_requests']
        _rpd_max = _limits['rpd']
        _rpd_pct = min(_rpd_used / max(_rpd_max, 1), 1.0)
        
        st.caption(f"📊 **Hoy ({_model}):** {_rpd_used} / {_rpd_max} req · {token_summary['today_tokens']:,} tokens")
        st.progress(_rpd_pct)
        if _rpd_pct >= 1.0:
            st.error(f"🚫 Cuota diaria de `{_model}` agotada.")
        elif _rpd_pct >= 0.8:
            st.warning(f"⚠️ Cuota diaria de `{_model}` casi agotada.")
        
        render_sidebar_footer()

main()
