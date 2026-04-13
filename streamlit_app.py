import streamlit as st

# Configuración global de la página
st.set_page_config(
    page_title="Transformador XML JATS",
    page_icon="resources/logos/logo.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inicializar modo oscuro por defecto si no existe
if "_theme_dark" not in st.session_state:
    st.session_state["_theme_dark"] = True

# Inyectar tema de marca global
from modules.theme import (inject_theme_css, render_sidebar_footer,
                           render_sidebar_header)

inject_theme_css()

# Logo en la parte superior del sidebar (encima de la navegación)
render_sidebar_header()

# Definición de las páginas
pages = {
    "Aplicación": [
        st.Page("views/transformador.py", title="Transformador", icon="📄"),
    ],
    "Configuración": [
        st.Page("views/configuracion.py", title="API y Tokens", icon="⚙️"),
    ],
    "Información": [
        st.Page("views/manual_usuario.py", title="Manual de Usuario", icon="📖"),
        st.Page("views/documentacion.py", title="Documentación", icon="📚"),
        st.Page("views/creditos.py", title="Créditos y Licencias", icon="⚖️"),
    ],
}

# Configuración de navegación
pg = st.navigation(pages)
pg.run()
