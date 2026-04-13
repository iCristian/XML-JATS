import base64
from pathlib import Path

import streamlit as st

from modules.theme import render_sidebar_footer

# Nota: st.set_page_config removido, se maneja en streamlit_app.py

def _get_image_base64(path: str) -> str:
    """Lee un archivo de imagen y lo convierte a Base64 data URI."""
    try:
        p = Path(path)
        if p.exists():
            encoded = base64.b64encode(p.read_bytes()).decode("utf-8")
            return f"data:image/png;base64,{encoded}"
    except Exception:
        pass
    return ""

def main():
    st.title("ℹ️ Información del Proyecto")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # Logo de marca XML-JATS
        brand_src = _get_image_base64("resources/logos/logo.png")
        uv_src = _get_image_base64("resources/UV_blanco.png")
        if brand_src:
            st.markdown(
                f"""
                <div style="text-align: center; margin-bottom: 12px;">
                    <img src="{brand_src}" style="max-width: 140px; border-radius: 16px;">
                </div>
                """,
                unsafe_allow_html=True,  # safe: brand_src is an internal base64 data URI
            )
        if uv_src:
            st.markdown(
                f"""
                <div style="text-align: center; margin-bottom: 12px;">
                    <img src="{uv_src}" style="max-width: 160px;">
                </div>
                """,
                unsafe_allow_html=True,  # safe: uv_src is an internal base64 data URI
            )
        
        st.markdown("""
        ### Universidad de Valparaíso
        **Facultad de Medicina**  
        *Escuela de Obstetricia y Puericultura*
        """)

    with col2:
        st.header("Créditos y Desarrollo")
        st.markdown("""
        Esta herramienta ha sido desarrollada para optimizar el flujo editorial de las **Revistas UV**, automatizando la conversión de manuscritos a XML JATS validado.

        **Desarrollador Principal:**  
        Cristian Carreño León  
        [cristian.carreno@uv.cl](mailto:cristian.carreno@uv.cl)
        """)

        st.divider()

        st.header("Tecnología")
        st.markdown("""
        El sistema utiliza tecnologías de vanguardia para el procesamiento de texto e inteligencia artificial:

        - **Python 3.9+**: Lenguaje base.
        - **Streamlit**: Framework de interfaz de usuario.
        - **Inteligencia Artificial Multi-Model**: Soporte nativo para motores LLM de **Google Gemini**, **OpenAI**, **Anthropic (Claude)**, **DeepSeek**, **Mistral**, **Groq** y local/offline mediante **Ollama**; para interpretación semántica y corrección de XML.
        - **LXML**: Procesamiento y validación robusta de XML.
        - **SQLite + Fernet**: Persistencia local de configuración y credenciales cifradas, con migración automática desde formatos legacy.
        - **JATS 1.3 / 1.4**: Estándares oficiales de etiquetado (Journal Archiving and Interchange Tag Suite), intercambiable en tiempo real a gusto del publicador.
        """)

    st.divider()

    st.header("🔒 Privacidad y Tratamiento de Datos")
    st.info("""
    **Importante:** Esta aplicación procesa documentos utilizando servicios de terceros.
    """)
    
    st.markdown("""
    1. **Procesamiento por Demanda**: Los archivos cargados se procesan durante el flujo de transformación y no se incorporan a un repositorio persistente de artículos.
    2. **Custodia Local de Claves**: Las API keys se almacenan cifradas en `data/config.db` mediante Fernet; la clave criptográfica se guarda localmente en `data/.fernet.key` con permisos restringidos.
    3. **Ruta de Datos Controlada**: El texto extraído se envía únicamente al proveedor de IA activo configurado por el usuario.
    4. **Inferencia Local Opcional**: Con Ollama o LM Studio, el procesamiento puede ejecutarse completamente en entorno local.
    5. **Responsabilidad de Anonimización**: Para contenido sensible, se recomienda anonimizar previamente y aplicar políticas institucionales de tratamiento de datos.
    """)

    st.divider()
    st.header("🛡️ Seguridad Operativa")
    st.markdown("""
    - **Secreto y Configuración fuera de Git**: `data/` está excluido por `.gitignore` para evitar filtraciones de base de datos y claves.
    - **Reporte Responsable de Vulnerabilidades**: Comunicar incidentes primero por correo a [cristian.carreno@uv.cl](mailto:cristian.carreno@uv.cl).
    - **Dependencias y Riesgo**: Toda actualización de librerías debe considerar revisión de CVEs y compatibilidad.
    - **Buenas Prácticas en PRs**: No adjuntar capturas con datos reales ni registros que contengan fragmentos de manuscritos.
    """)

    st.divider()

    # Botón Volver (más claro)
    col_back, _ = st.columns([1, 2])
    with col_back:
        if st.button("⬅️ VOLVER AL INICIO", type="primary", width="stretch"):
            st.switch_page("views/transformador.py")

    # Sidebar Footer
    with st.sidebar:
        render_sidebar_footer()

main()
