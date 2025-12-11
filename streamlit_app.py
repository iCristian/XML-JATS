import streamlit as st

# Configuración global de la página
st.set_page_config(
    page_title="Transformador XML JATS",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Definición de las páginas
pages = {
    "Aplicación": [
        st.Page("views/transformador.py", title="Transformador", icon="📄"),
    ],
    "Información": [
        st.Page("views/manual_usuario.py", title="Manual de Usuario", icon="📖"),
        st.Page("views/documentacion.py", title="Documentación", icon="📚"),
        st.Page("views/creditos.py", title="Créditos y Licencias", icon="⚖️"),
    ]
}

# Configuración de navegación
pg = st.navigation(pages)
pg.run()
