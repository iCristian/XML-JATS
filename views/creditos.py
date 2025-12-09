import streamlit as st
import base64
from pathlib import Path

# Nota: st.set_page_config removido, se maneja en streamlit_app.py

def _get_logo_base64() -> str:
    """Lee el archivo de logo y lo convierte a Base64."""
    try:
        logo_path = Path("resources/UV_blanco.png")
        if logo_path.exists():
            encoded = base64.b64encode(logo_path.read_bytes()).decode("utf-8")
            return f"data:image/png;base64,{encoded}"
    except Exception:
        pass
    return ""

def main():
    st.title("ℹ️ Información del Proyecto")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        logo_src = _get_logo_base64()
        if logo_src:
            st.markdown(
                f"""
                <div style="text-align: left; margin-bottom: 20px;">
                    <img src="{logo_src}" style="max-width: 200px;">
                </div>
                """, 
                unsafe_allow_html=True
            )
        
        st.markdown("""
        ### Universidad de Valparaíso
        **Facultad de Medicina**  
        *Escuela de Obstetricia y Puericultura*
        """)

    with col2:
        st.header("Créditos y Desarrollo")
        st.markdown("""
        Esta herramienta ha sido desarrollada para optimizar el flujo de trabajo editorial de la **Revistas UV**, automatizando la conversión de manuscritos a XML JATS validado.

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
        - **Google Gemini Pro**: Modelo de lenguaje (LLM) para la interpretación semántica y corrección de XML.
        - **LXML**: Procesamiento y validación robusta de XML.
        - **JATS 1.3**: Estándar de etiquetado (Journal Archiving and Interchange Tag Suite).
        """)

    st.divider()

    st.header("🔒 Privacidad y Tratamiento de Datos")
    st.info("""
    **Importante:** Esta aplicación procesa documentos utilizando servicios de terceros.
    """)
    
    st.markdown("""
    1. **Procesamiento Volátil**: Los archivos cargados se procesan en la memoria del servidor (o localmente si se ejecuta en su máquina) y **no se almacenan permanentemente**.
    2. **API de Inteligencia Artificial**:
        - El texto extraído de los documentos se envía a la API de **Google Gemini** para su estructuración.
        - Google utiliza estos datos de acuerdo con sus [Términos de Servicio de API Generativa](https://ai.google.dev/terms).
        - **No suba documentos con datos personales sensibles** (nombres de pacientes, datos confidenciales no anonimizados) a menos que tenga autorización explícita.
    3. **Uso Local Recomendado**: Para máxima privacidad, ejecute esta herramienta en un entorno local seguro.
    """)

    st.divider()

    # Botón Volver (más claro)
    col_back, _ = st.columns([1, 2])
    with col_back:
        if st.button("⬅️ VOLVER AL INICIO", type="primary", use_container_width=True):
            st.switch_page("views/transformador.py")

    # Sidebar Footer (Igual que en la app principal)
    with st.sidebar:
        #st.markdown("---")
        st.markdown(
            """
            <div class='branding'>
                <b>Universidad de Valparaíso</b><br>
                <small>Transformador XML JATS v0.5 (Beta)</small>
            </div>
            """, 
            unsafe_allow_html=True
        )

    st.caption("Transformador XML JATS v0.5 (Beta) | Universidad de Valparaíso")

main()
