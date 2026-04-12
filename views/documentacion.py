from pathlib import Path

import streamlit as st


def main():
    st.title("📚 Documentación del Proyecto")

    tab1, tab2, tab3 = st.tabs(["📖 README", "🗂️ Resumen Técnico", "🤝 CONTRIBUTING"])

    with tab1:
        readme_path = Path("README.md")
        if readme_path.exists():
            st.markdown(readme_path.read_text(encoding='utf-8'))
        else:
            st.warning("README.md no encontrado.")

    with tab2:
        resume_path = Path("RESUME.md")
        if resume_path.exists():
            st.markdown(resume_path.read_text(encoding='utf-8'))
        else:
            st.warning("RESUME.md no encontrado.")

    with tab3:
        contrib_path = Path("CONTRIBUTING.md")
        if contrib_path.exists():
            st.markdown(contrib_path.read_text(encoding='utf-8'))
        else:
            st.warning("CONTRIBUTING.md no encontrado.")

    # Sidebar Footer (Igual que en la app principal para consistencia)
    with st.sidebar:
        st.markdown("---")
        st.markdown(
            """
            <div class='branding'>
                <b>Universidad de Valparaíso</b><br>
                <small>Transformador XML JATS v0.7.5</small>
            </div>
            """, 
            unsafe_allow_html=True  # safe: static HTML
        )

main()
