# -*- coding: utf-8 -*-

"""Vista de Configuración de Prompts.

Permite visualizar, editar y restablecer los prompts de extracción de metadatos
y de generación de XML utilizados por el modelo LLM.
"""

import streamlit as st

from modules import config_store, prompts
from modules.theme import render_sidebar_footer


def main() -> None:
    st.title("📝 Configuración de Prompts")
    st.markdown(
        "Ajusta las instrucciones que se envían a la Inteligencia Artificial "
        "para la extracción de metadatos y la transformación JATS XML."
    )

    tab_extract, tab_transform = st.tabs(["Extracción de Metadatos", "Transformación XML"])

    # ════════════════════════════════════════════════════════════
    # PESTAÑA 1: Extracción de Metadatos
    # ════════════════════════════════════════════════════════════
    with tab_extract:
        st.header("Prompt de Extracción")
        st.markdown(
            "Este prompt se utiliza en el **Paso 1** para extraer información estructurada (JSON) "
            "a partir del texto original."
        )
        st.info("⚠️ **Comodín obligatorio**: No elimines la variable `{text_snippet}` ya que aquí se inyectará el texto del artículo.")

        current_ext_prompt = config_store.get_custom_extraction_prompt()
        if not current_ext_prompt:
            current_ext_prompt = prompts.DEFAULT_EXTRACTION_PROMPT_TEMPLATE.strip()

        new_ext_prompt = st.text_area(
            "Edita el prompt de extracción:",
            value=current_ext_prompt,
            height=400,
            key="ext_prompt_area"
        )

        col_ext1, col_ext2 = st.columns(2)
        with col_ext1:
            if st.button("💾 Guardar Prompt (Extracción)", type="primary", use_container_width=True):
                config_store.save_custom_extraction_prompt(new_ext_prompt)
                st.success("✅ Prompt de extracción guardado correctamente.")
        with col_ext2:
            if st.button("🔄 Restablecer al Original (Extracción)", use_container_width=True):
                config_store.delete_custom_extraction_prompt()
                st.success("✅ Prompt de extracción restablecido.")
                st.rerun()

    # ════════════════════════════════════════════════════════════
    # PESTAÑA 2: Transformación XML
    # ════════════════════════════════════════════════════════════
    with tab_transform:
        st.header("Prompt de Transformación XML")
        st.markdown(
            "Este es el prompt **principal** utilizado en el **Paso 2** para generar todo el marcado JATS."
        )
        st.info(
            "⚠️ **Comodines obligatorios**: Mantén las variables:\n"
            "- `{version}` (Versión de JATS)\n"
            "- `{metadata_instructions}` (Instrucciones de metadatos obligatorios)\n"
            "- `{texto_articulo}` (El contenido completo del artículo)"
        )

        current_gen_prompt = config_store.get_custom_generation_prompt()
        if not current_gen_prompt:
            current_gen_prompt = prompts.DEFAULT_GENERATION_PROMPT_TEMPLATE.strip()

        new_gen_prompt = st.text_area(
            "Edita el prompt de generación:",
            value=current_gen_prompt,
            height=600,
            key="gen_prompt_area"
        )

        col_gen1, col_gen2 = st.columns(2)
        with col_gen1:
            if st.button("💾 Guardar Prompt (Transformación)", type="primary", use_container_width=True):
                config_store.save_custom_generation_prompt(new_gen_prompt)
                st.success("✅ Prompt de transformación guardado correctamente.")
        with col_gen2:
            if st.button("🔄 Restablecer al Original (Transformación)", use_container_width=True):
                config_store.delete_custom_generation_prompt()
                st.success("✅ Prompt de transformación restablecido.")
                st.rerun()

    st.markdown("---")
    st.caption("🔒 Los prompts personalizados se almacenan localmente en la base de datos.")

    with st.sidebar:
        render_sidebar_footer()


main()
