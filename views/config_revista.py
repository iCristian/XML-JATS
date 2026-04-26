# -*- coding: utf-8 -*-

"""Vista de Configuración de Revista.

Gestiona los metadatos editoriales persistentes de la revista (journal-meta
JATS), la versión de estándar JATS y los logos para el renderizado HTML.
"""

import base64
from pathlib import Path

import streamlit as st

from modules import config_store
from modules.theme import render_sidebar_footer


def _img_preview(path: Path, max_height: int = 80) -> str:
    """Genera un tag <img> base64 para vista previa."""
    try:
        data = base64.b64encode(path.read_bytes()).decode("utf-8")
        suffix = path.suffix.lower().lstrip(".")
        mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                "svg": "image/svg+xml", "webp": "image/webp"}.get(suffix, "image/png")
        return (
            f'<img src="data:{mime};base64,{data}" '
            f'style="max-height: {max_height}px; border-radius: 8px; '
            f'border: 1px solid rgba(128,128,128,0.25); padding: 8px; '
            f'background: {"#fff" if "light" in path.stem else "#1a1a2e"};">'
        )
    except Exception:
        return ""


def _handle_logo_upload(mode: str) -> None:
    """Callback para procesar la subida del logo antes del renderizado."""
    upload_key = f"upload_logo_{mode}"
    uploaded = st.session_state.get(upload_key)
    if uploaded:
        img_bytes = uploaded.getvalue()
        if len(img_bytes) > 2 * 1024 * 1024:
            st.session_state[f"logo_error_{mode}"] = "El archivo supera 2 MB. Usa una imagen más ligera."
        else:
            config_store.save_journal_logo(mode, img_bytes, uploaded.name)
            st.session_state[f"logo_success_{mode}"] = True


def main() -> None:
    st.title("📰 Configuración de Revista")
    st.markdown(
        "Define los metadatos editoriales que se inyectarán automáticamente "
        "en `<journal-meta>` de cada XML JATS generado. Estos datos se "
        "mantienen fijos entre transformaciones."
    )

    # Cargar datos actuales
    cfg = config_store.get_journal_config()

    # ════════════════════════════════════════════════════════════
    # SECCIÓN 1: Identidad de la Revista
    # ════════════════════════════════════════════════════════════
    st.header("🏷️ Identidad de la Revista")

    col_id1, col_id2 = st.columns(2, gap="large")
    with col_id1:
        new_title = st.text_input(
            "Título de la Revista",
            value=cfg["title"],
            help="Nombre oficial completo → `<journal-title>`",
            key="jr_title",
        )
        new_publisher = st.text_input(
            "Editorial (Publisher)",
            value=cfg["publisher"],
            help="Entidad editora → `<publisher-name>`",
            key="jr_publisher",
        )
    with col_id2:
        new_abbrev = st.text_input(
            "Título Abreviado (ISO)",
            value=cfg["abbrev_title"],
            placeholder="Ej: Rev. Chil. Obstet. Ginecol.",
            help="Abreviatura ISO 4 → `<abbrev-journal-title>`",
            key="jr_abbrev",
        )
        new_journal_id = st.text_input(
            "ID de Revista",
            value=cfg["journal_id"],
            placeholder="Ej: rchog",
            help="Identificador corto del publisher → `<journal-id>`",
            key="jr_journal_id",
        )

    st.markdown("---")

    # ════════════════════════════════════════════════════════════
    # SECCIÓN 2: Identificadores
    # ════════════════════════════════════════════════════════════
    st.header("🔗 Identificadores")

    col_ids1, col_ids2, col_ids3 = st.columns(3, gap="large")
    with col_ids1:
        new_issn_print = st.text_input(
            "ISSN Impreso",
            value=cfg["issn_print"],
            placeholder="0000-0000",
            help='→ `<issn pub-type="ppub">`',
            key="jr_issn_print",
        )
    with col_ids2:
        new_issn_electronic = st.text_input(
            "ISSN Electrónico",
            value=cfg["issn_electronic"],
            placeholder="0000-0000",
            help='→ `<issn pub-type="epub">`',
            key="jr_issn_electronic",
        )
    with col_ids3:
        new_doi_base = st.text_input(
            "DOI Base (Prefijo)",
            value=cfg["doi_base"],
            placeholder="Ej: 10.4067/S0717-",
            help="Prefijo reutilizable. Solo cambia el sufijo por artículo.",
            key="jr_doi_base",
        )

    st.markdown("---")

    # ════════════════════════════════════════════════════════════
    # SECCIÓN 3: Publicación
    # ════════════════════════════════════════════════════════════
    st.header("📝 Publicación")

    col_pub1, col_pub2 = st.columns(2, gap="large")
    with col_pub1:
        new_subject = st.text_input(
            "Temática / Área de Conocimiento",
            value=cfg["subject"],
            placeholder="Ej: Ciencias de la Salud",
            help="→ `<subj-group><subject>`",
            key="jr_subject",
        )
        new_lang = st.selectbox(
            "Idioma por Defecto",
            options=["es", "en", "pt", "fr", "de", "it"],
            index=["es", "en", "pt", "fr", "de", "it"].index(cfg["default_lang"])
            if cfg["default_lang"] in ["es", "en", "pt", "fr", "de", "it"]
            else 0,
            help="Código ISO 639-1 → atributo `xml:lang`",
            key="jr_lang",
        )
    with col_pub2:
        new_license = st.text_input(
            "URL de Licencia de los Artículos",
            value=cfg["license_url"],
            placeholder="https://creativecommons.org/licenses/by-nc-sa/4.0/",
            help="→ `<license xlink:href=\"...\">`",
            key="jr_license",
        )

    st.markdown("---")

    # ════════════════════════════════════════════════════════════
    # SECCIÓN 4: Estándar JATS
    # ════════════════════════════════════════════════════════════
    st.header("📐 Estándar XML JATS")

    current_version = config_store.get_jats_version()

    col_jats1, col_jats2 = st.columns([1, 2], gap="large")
    with col_jats1:
        new_version = st.selectbox(
            "Versión JATS a generar:",
            options=["1.3", "1.4"],
            index=0 if current_version == "1.3" else 1,
            key="jr_jats_version",
        )
    with col_jats2:
        if new_version == "1.4":
            st.info(
                "**JATS 1.4** (ANSI/NISO Z39.96-2024) — Versión más reciente. "
                "Añade mejoras en accesibilidad, matemáticas y afiliaciones "
                "estructuradas. **Recomendada**."
            )
        else:
            st.warning(
                "**JATS 1.3** — Selecciona esta versión solo si tu publicador "
                "(ej. OJS legacy, SciELO antiguo) la requiere explícitamente."
            )

    st.markdown("---")

    # ════════════════════════════════════════════════════════════
    # BOTÓN GUARDAR TODO
    # ════════════════════════════════════════════════════════════
    if st.button("💾 Guardar Configuración de Revista", type="primary", use_container_width=True):
        journal_data = {
            "title": new_title,
            "abbrev_title": new_abbrev,
            "journal_id": new_journal_id,
            "publisher": new_publisher,
            "issn_print": new_issn_print,
            "issn_electronic": new_issn_electronic,
            "doi_base": new_doi_base,
            "subject": new_subject,
            "license_url": new_license,
            "default_lang": new_lang,
        }
        config_store.save_journal_config(journal_data)

        # Sincronizar versión JATS
        if new_version != current_version:
            config_store.save_jats_version(new_version)

        st.success("✅ Configuración de revista guardada correctamente.")
        st.toast("Datos editoriales actualizados", icon="📰")

    st.markdown("---")

    # ════════════════════════════════════════════════════════════
    # SECCIÓN 5: Logos de la Revista
    # ════════════════════════════════════════════════════════════
    st.header("🖼️ Logos de la Revista")
    st.markdown(
        "Sube el logo de tu revista para incluirlo en el HTML generado. "
        "Puedes configurar versiones separadas para **modo claro** (fondo blanco) "
        "y **modo oscuro** (fondo oscuro)."
    )

    with st.expander("📏 Recomendaciones de tamaño", expanded=False):
        st.markdown("""
- **Formato**: PNG con fondo transparente (preferido) o SVG.
- **Dimensiones**: Entre **400×120 px** y **800×240 px** (ratio ~3:1 horizontal).
- **Peso máximo**: < 500 KB para carga rápida del HTML.
- **Modo claro**: Logo con colores oscuros/originales (se verá sobre fondo blanco).
- **Modo oscuro**: Logo en blanco/claro o versión invertida (se verá sobre fondo oscuro).
        """)

    col_logo_l, col_logo_d = st.columns(2, gap="large")

    for mode, col, label, bg_hint in [
        ("light", col_logo_l, "☀️ Logo Modo Claro", "fondo blanco"),
        ("dark", col_logo_d, "🌙 Logo Modo Oscuro", "fondo oscuro"),
    ]:
        with col:
            st.subheader(label)

            existing = config_store.get_journal_logo_path(mode)
            if existing:
                preview = _img_preview(existing)
                if preview:
                    st.markdown(preview, unsafe_allow_html=True)
                st.caption(f"Archivo: `{existing.name}`")

                if st.button(f"🗑️ Eliminar logo ({mode})", key=f"del_logo_{mode}"):
                    config_store.delete_journal_logo(mode)
                    st.rerun()
            else:
                st.info(f"Sin logo para {bg_hint}.")

            st.file_uploader(
                f"Subir logo ({mode})",
                type=["png", "jpg", "jpeg", "svg", "webp"],
                key=f"upload_logo_{mode}",
                label_visibility="collapsed",
                on_change=_handle_logo_upload,
                args=(mode,)
            )
            
            if st.session_state.pop(f"logo_success_{mode}", False):
                st.success(f"✅ Logo {mode} guardado.")
            if err := st.session_state.pop(f"logo_error_{mode}", None):
                st.error(err)

    st.markdown("---")
    st.caption(
        "🔒 Todos los datos se almacenan localmente en `data/config.db`. "
        "Los logos se guardan en `data/logos/`. Nada sale de tu equipo."
    )

    with st.sidebar:
        render_sidebar_footer()


main()
