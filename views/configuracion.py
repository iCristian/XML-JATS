"""Vista de Configuración de API y uso de tokens.

Gestiona las claves de API de múltiples proveedores de IA (Gemini, OpenAI,
Anthropic, DeepSeek, Mistral, Groq, Ollama), muestra cuotas y proporciona
un panel detallado de consumo de tokens con gráficos.
"""

import os

import pandas as pd
import streamlit as st

from modules import config_store
from modules.llm_provider import PROVIDER_REGISTRY, list_providers


def main() -> None:
    st.title("⚙️ Configuración de API")
    st.markdown("Gestiona tus claves de API para múltiples proveedores de IA, consulta cuotas y revisa el consumo de tokens.")

    # ════════════════════════════════════════════════════════════
    # SECCIÓN 1: Proveedor activo
    # ════════════════════════════════════════════════════════════
    st.header("🤖 Proveedor de IA Activo")

    providers = list_providers()
    provider_ids = [p["id"] for p in providers]
    provider_names = [p["name"] for p in providers]
    current_provider = config_store.load_active_provider()
    current_idx = provider_ids.index(current_provider) if current_provider in provider_ids else 0

    col_prov1, col_prov2 = st.columns([3, 1])
    with col_prov1:
        selected_provider = st.selectbox(
            "Proveedor principal a utilizar por defecto:",
            options=provider_ids,
            format_func=lambda pid: next((p["name"] for p in providers if p["id"] == pid), pid),
            index=current_idx,
            key="_cfg_provider_select",
        )
    with col_prov2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("💾 Guardar como Activo", width="stretch", type="primary"):
            if selected_provider != current_provider:
                config_store.save_active_provider(selected_provider)
                st.session_state["_active_provider"] = selected_provider
                st.success(f"Proveedor {selected_provider} configurado como principal.")
                st.rerun()
            else:
                st.info("Ya es el proveedor activo.")

    configured = config_store.get_configured_providers()
    st.caption(
        f"Proveedores con API Key configurada: **{', '.join(configured) if configured else 'Ninguno'}**"
    )

    st.markdown("---")

    # ════════════════════════════════════════════════════════════
    # SECCIÓN 2: Gestión de API Keys por proveedor
    # ════════════════════════════════════════════════════════════
    st.header("🔑 Claves de API")

    # Crear tabs por proveedor
    provider_tabs = st.tabs([p["name"] for p in providers])

    for tab, pinfo in zip(provider_tabs, providers):
        pid = pinfo["id"]
        pname = pinfo["name"]
        provider_obj = PROVIDER_REGISTRY[pid]

        with tab:
            saved_key = config_store.load_provider_key(pid)

            col_key, col_info = st.columns(2, gap="large")

            with col_key:
                if pid in ("ollama", "lmstudio"):
                    is_ollama = pid == "ollama"
                    name_prov = "Ollama" if is_ollama else "LM Studio"
                    default_port = "`localhost:11434`" if is_ollama else "`localhost:1234/v1`"
                    
                    st.info(
                        f"🏠 **{name_prov} es local** — no requiere API Key. "
                        f"Asegúrate de tener {name_prov} corriendo y el servidor local activado en {default_port}."
                    )
                    if st.button(f"🧪 Probar conexión", key=f"cfg_test_{pid}"):
                        try:
                            models = provider_obj.list_models(pid)
                            if models:
                                st.success(f"✅ {name_prov} conectado. Modelos: {', '.join(models[:5])}")
                            else:
                                st.warning(f"⚠️ {name_prov} conectado pero no se encontraron modelos descargados.")
                        except Exception as e:
                            st.error(f"❌ No se pudo conectar a {name_prov}: {e}")
                else:
                    if saved_key:
                        masked = saved_key[:4] + "•" * 16 + saved_key[-4:]
                        st.text_input(f"Key actual ({pname}):", value=masked, disabled=True, key=f"_cfg_masked_{pid}")
                        st.success("✅ Configurada", icon="🟢")

                        c1, c2 = st.columns(2)
                        with c1:
                            if st.button("✏️ Cambiar", key=f"cfg_change_{pid}"):
                                st.session_state[f"_cfg_edit_{pid}"] = True
                                st.rerun()
                        with c2:
                            if st.button("🗑️ Borrar", key=f"cfg_delete_{pid}"):
                                config_store.delete_provider_key(pid)
                                if pid == config_store.load_active_provider():
                                    st.session_state.pop("_active_api_key", None)
                                st.rerun()
                    else:
                        st.warning("❌ No configurada")

                    if not saved_key or st.session_state.get(f"_cfg_edit_{pid}"):
                        new_key = st.text_input(
                            f"Ingresa tu API Key de {pname}:",
                            type="password",
                            key=f"_cfg_input_{pid}",
                            placeholder="Pega tu API key aquí...",
                        )
                        bcol1, bcol2 = st.columns(2)
                        with bcol1:
                            if new_key and st.button("💾 Guardar", key=f"cfg_save_{pid}", type="primary"):
                                config_store.save_provider_key(pid, new_key.strip())
                                if pid == config_store.load_active_provider():
                                    st.session_state["_active_api_key"] = new_key.strip()
                                st.session_state.pop(f"_cfg_edit_{pid}", None)
                                st.success("✅ Guardada")
                                st.rerun()
                        with bcol2:
                            if saved_key and st.button("Cancelar", key=f"cfg_cancel_{pid}"):
                                st.session_state.pop(f"_cfg_edit_{pid}", None)
                                st.rerun()

                    api_url = provider_obj.get_api_key_url()
                    if api_url:
                        st.markdown(f"[🔗 Obtener API Key de {pname}]({api_url})")

            with col_info:
                st.subheader(f"💡 {pname}")
                
                if pid == "ollama":
                    st.markdown(
                        "**Ollama** es una herramienta que te permite ejecutar grandes modelos de lenguaje (LLMs) directamente en tu propia computadora, garantizando total privacidad y coste cero por consulta. "
                        "Es ideal para equipos con Apple Silicon (M1/M2/M3) o tarjetas gráficas dedicadas.\n\n"
                        "📚 [Visitar la página oficial de Ollama](https://ollama.com)\n\n"
                        "📖 [Explorar Modelos Disponibles](https://ollama.com/library)"
                    )
                elif pid == "lmstudio":
                    st.markdown(
                        "**LM Studio** es una aplicación de escritorio fácil de usar para descubrir, descargar y ejecutar modelos de lenguaje locales (GGUF, Llama, Qwen, etc.). "
                        "Ofrece un servidor local compatible con la API de OpenAI, lo que lo hace perfecto para integrarse con este sistema.\n\n"
                        "Para usarlo, descarga un modelo, ve a la pestaña **Local Server** y actívalo.\n\n"
                        "📚 [Descargar LM Studio](https://lmstudio.ai)\n\n"
                        "▶️ [Guía Rápida de LM Studio](https://lmstudio.ai/docs)"
                    )
                else:
                    default_models = provider_obj.get_default_models()
                    if default_models:
                        st.markdown("**Modelos disponibles:**")
                        for m in default_models[:6]:
                            st.markdown(f"- `{m}`")
                    env_var = provider_obj.get_api_key_env_var()
                    if env_var:
                        st.caption(f"Variable de entorno: `{env_var}`")

    st.markdown("---")
    st.caption(
        "🔒 Las claves se almacenan localmente en `data/config.db` con ofuscación Base64. "
        "No se envían a ningún servidor externo excepto a la API del proveedor seleccionado."
    )

    # ════════════════════════════════════════════════════════════
    # SECCIÓN 3: Configuración de la Revista y JATS
    # ════════════════════════════════════════════════════════════
    st.header("📄 Datos por Defecto y Estándar JATS")
    
    st.markdown("Establece los metadatos globales que se mantendrán fijos en todas las transformaciones y la versión JATS a exportar.")
    
    col_journal, col_jats = st.columns(2, gap="large")
    
    with col_journal:
        st.subheader("Datos de la Revista")
        journal_data = config_store.get_default_journal_data()
        
        new_title = st.text_input("Título de la Revista:", value=journal_data["title"])
        new_publisher = st.text_input("Nombre de la Editorial (Publisher):", value=journal_data["publisher"])
        new_issn = st.text_input("ISSN de la Revista:", value=journal_data["issn"])
        
        if st.button("💾 Guardar Datos", key="cfg_save_journal", type="primary"):
            config_store.save_default_journal_data(new_title, new_publisher, new_issn)
            st.success("✅ Datos de revista guardados")
            
    with col_jats:
        st.subheader("Estándar XML JATS")
        current_version = config_store.get_jats_version()
        
        st.info("**JATS 1.4** añade mejoras en accesibilidad, matemáticas y afiliaciones estructuradas. Selecciona **1.3** solo si tu publicador (ej. OJS legacy) lo restringe.")
        
        new_version = st.selectbox(
            "Versión a generar:",
            options=["1.3", "1.4"],
            index=0 if current_version == "1.3" else 1,
            key="cfg_jats_version"
        )
        
        if new_version != current_version:
            config_store.save_jats_version(new_version)
            st.success(f"✅ Versión JATS cambiada a {new_version}")
            st.rerun()

    st.markdown("---")

    # ════════════════════════════════════════════════════════════
    # SECCIÓN 4: Cuotas de Gemini por tipo de cuenta
    # ════════════════════════════════════════════════════════════
    st.header("📋 Cuotas de Gemini por Modelo y Cuenta")

    st.markdown("""
**Tier Gratuito:** Las claves de Google AI Studio operan en capa gratuita con límites diarios y por minuto. 
Mantenerte bajo este umbral garantiza coste cero. 
⚠️ **Atención:** Si vinculaste tu clave a un proyecto de Google Cloud con facturación activa, al sobrepasar estos límites **pasarás automáticamente al modelo Pay-as-you-go** incurriendo en cargos. Sugerimos `gemini-2.5-flash` para mantener amplio margen de capa libre.
""")

    quota_data = []
    for model_name, limits in config_store.FREE_TIER_LIMITS.items():
        quota_data.append({
            "Modelo": model_name,
            "Req/día (Free)": f"{limits['rpd']:,}",
            "Tokens/min (Free)": f"{limits['tpm']:,}",
            "Req/min (Free)": limits['rpm'],
            "Tras cuota libre": "Pay-as-you-go*",
        })

    df_quotas = pd.DataFrame(quota_data)
    st.dataframe(df_quotas, width="stretch", hide_index=True)

    with st.expander("ℹ️ Notas sobre cuentas y cuotas", expanded=False):
        st.markdown("""
**Google Gemini — Cuenta Gratuita:**
- Ideal para pruebas y uso moderado.
- Límites diarios reinician a las 00:00 UTC.

**OpenAI:**
- Pay-as-you-go desde el inicio. Consulta [OpenAI Pricing](https://openai.com/pricing).

**Anthropic (Claude):**
- Pay-as-you-go. Consulta [Anthropic Pricing](https://www.anthropic.com/pricing).

**DeepSeek / Mistral / Groq:**
- Algunos ofrecen tiers gratuitos limitados. Consulta sus sitios respectivos.

**Ollama (Local):**
- Totalmente gratuito. Requiere hardware local con GPU recomendada.
""")

    # ════════════════════════════════════════════════════════════
    # SECCIÓN 5: Panel de consumo de tokens detallado
    # ════════════════════════════════════════════════════════════
    st.header("📊 Consumo de Tokens")

    token_summary = config_store.get_token_summary()
    selected_model = st.session_state.get("selected_model", "gemini-2.5-flash")
    limits = config_store.get_free_tier_limits(selected_model)

    m1, m2, m3, m4 = st.columns(4)
    rpd_used = token_summary['today_requests']
    rpd_max = limits['rpd']

    with m1:
        st.metric("Requests hoy", f"{rpd_used} / {rpd_max}", 
                  delta=f"{rpd_max - rpd_used} restantes" if rpd_used < rpd_max else "Agotado",
                  delta_color="normal" if rpd_used < rpd_max else "inverse")
    with m2:
        st.metric("Tokens hoy", f"{token_summary['today_tokens']:,}")
    with m3:
        st.metric("Total histórico", f"{token_summary['total_tokens']:,}")
    with m4:
        st.metric("Operaciones totales", f"{token_summary['total_requests']}")

    rpd_pct = min(rpd_used / max(rpd_max, 1), 1.0)
    st.markdown(f"**Uso de cuota diaria ({selected_model}):**")
    st.progress(rpd_pct)
    if rpd_pct >= 1.0:
        st.error(f"🚫 Cuota gratuita diaria de `{selected_model}` agotada.")
    elif rpd_pct >= 0.8:
        st.warning(f"⚠️ Has usado {rpd_pct:.0%} de tu cuota diaria gratuita de `{selected_model}`.")
    else:
        st.success(f"✅ Cuota diaria al {rpd_pct:.0%}.")

    st.subheader("📈 Uso diario (últimos 30 días)")
    daily_usage = config_store.get_daily_usage(30)

    if daily_usage:
        df_daily = pd.DataFrame(daily_usage)
        df_daily.columns = ["Fecha", "Tokens", "Requests"]
        df_daily["Fecha"] = pd.to_datetime(df_daily["Fecha"])
        df_daily = df_daily.sort_values("Fecha")

        tab_tokens, tab_requests = st.tabs(["Tokens", "Requests"])
        with tab_tokens:
            st.bar_chart(df_daily.set_index("Fecha")["Tokens"], color="#667eea")
        with tab_requests:
            st.bar_chart(df_daily.set_index("Fecha")["Requests"], color="#764ba2")
    else:
        st.info("Aún no hay datos de uso registrados. Procesa un documento para ver estadísticas.")

    st.subheader("📝 Operaciones recientes")
    history = config_store.get_token_history(20)

    if history:
        df_hist = pd.DataFrame(history)
        df_hist.columns = ["Fecha/Hora", "Operación", "Modelo", "Prompt", "Respuesta", "Total"]
        df_hist["Fecha/Hora"] = df_hist["Fecha/Hora"].apply(lambda x: x[:19].replace("T", " ") if x else "")
        st.dataframe(df_hist, width="stretch", hide_index=True)
    else:
        st.info("No hay operaciones registradas aún.")

    if token_summary['last_used']:
        st.caption(f"Última operación: {token_summary['last_used'][:19].replace('T', ' ')}")


main()
