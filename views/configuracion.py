"""Vista de Configuración de API y uso de tokens.

Gestiona las claves de API de Gemini, muestra cuotas por tipo de cuenta
y proporciona un panel detallado de consumo de tokens con gráficos.
"""

import streamlit as st
import os
import pandas as pd
from modules import config_store


def main() -> None:
    st.title("⚙️ Configuración de API")
    st.markdown("Gestiona tus claves de Gemini, consulta cuotas y revisa el consumo detallado de tokens.")

    # ════════════════════════════════════════════════════════════
    # SECCIÓN 1: Gestión de API Keys
    # ════════════════════════════════════════════════════════════
    st.header("🔑 Claves de API")

    saved_key = config_store.load_api_key()

    col_free, col_info = st.columns(2, gap="large")

    with col_free:
        st.subheader("API Key Gratuita")
        if saved_key:
            masked = saved_key[:4] + "•" * 16 + saved_key[-4:]
            st.text_input("Key actual:", value=masked, disabled=True, key="_cfg_masked_free")
            st.success("✅ Configurada", icon="🟢")
            
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✏️ Cambiar", key="cfg_change_free"):
                    st.session_state["_cfg_edit_free"] = True
                    st.rerun()
            with c2:
                if st.button("🗑️ Borrar", key="cfg_delete_free"):
                    config_store.delete_api_key()
                    st.session_state.pop("_active_api_key", None)
                    st.rerun()
        else:
            st.warning("❌ No configurada")

        if not saved_key or st.session_state.get("_cfg_edit_free"):
            new_key = st.text_input(
                "Ingresa tu API Key gratuita:",
                type="password",
                key="_cfg_input_free",
                placeholder="AIza...",
                help="Crea una sin facturación en Google AI Studio."
            )
            bcol1, bcol2 = st.columns(2)
            with bcol1:
                if new_key and st.button("💾 Guardar", key="cfg_save_free", type="primary"):
                    config_store.save_api_key(new_key.strip())
                    st.session_state["_active_api_key"] = new_key.strip()
                    st.session_state.pop("_cfg_edit_free", None)
                    st.success("✅ Guardada")
                    st.rerun()
            with bcol2:
                if saved_key and st.button("Cancelar", key="cfg_cancel_free"):
                    st.session_state.pop("_cfg_edit_free", None)
                    st.rerun()

        st.markdown("[🔗 Obtener Key en Google AI Studio](https://aistudio.google.com/app/apikey)")

    with col_info:
        st.subheader("💡 Una sola clave para todo")
        st.info(
            "La misma API Key que guardas aquí sirve tanto para el **tier gratuito** "
            "como para el **tier de pago**.\n\n"
            "Cuando tu cuota gratuita diaria se agote, Google continuará usando la "
            "misma clave si tu cuenta tiene **facturación habilitada** en Google Cloud. "
            "Si no, las solicitudes quedarán bloqueadas hasta el día siguiente.\n\n"
            "No es necesario configurar una segunda clave.",
        )
        st.markdown(
            "[\U0001f4b3 Activar facturación en Google Cloud]("
            "https://console.cloud.google.com/billing)"
        )

    st.markdown("---")
    st.caption(
        "🔒 La clave se almacena localmente en `data/config.db` con ofuscación Base64. "
        "No se envía a ningún servidor externo excepto a la API de Google."
    )

    # ════════════════════════════════════════════════════════════
    # SECCIÓN 2: Cuotas de Gemini por tipo de cuenta
    # ════════════════════════════════════════════════════════════
    st.header("📋 Cuotas de Gemini por Modelo y Cuenta")

    st.markdown("""
El sistema utiliza la **API de Google Generative AI** para interactuar con los modelos Gemini.
Las cuentas gratuitas tienen límites diarios y por minuto. Cuando se agota la cuota libre,
Google continúa usando la misma clave si la cuenta tiene **facturación habilitada**.
""")

    # Tabla de cuotas
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
    st.dataframe(df_quotas, use_container_width=True, hide_index=True)

    with st.expander("ℹ️ Notas sobre cuentas y cuotas", expanded=False):
        st.markdown("""
**Cuenta Gratuita (sin facturación):**
- Ideal para pruebas y uso moderado.
- Límites diarios reinician a las 00:00 UTC.
- Al alcanzar el límite, se recibe error HTTP 429.

**Con facturación habilitada (Google Cloud Billing):**
- La misma API key continúa funcionando tras agotar la cuota libre.
- Se cobra sólo por tokens usados por encima del tier gratuito.
- Facturación pay-as-you-go sin límites artificiales.

**Modelos recomendados:**
| Modelo | Uso ideal |
|--------|-----------|
| `gemini-2.5-flash` | ✅ **Recomendado** — Balance óptimo de velocidad, costo y calidad |
| `gemini-2.5-flash-lite` | Tareas simples, máxima economía |
| `gemini-2.5-pro` | Máxima calidad, menor cuota gratuita |
| `gemini-2.0-flash` | Mayor cuota diaria (1500 req), buena calidad |

*\\* Consulta [Google AI pricing](https://ai.google.dev/pricing) para tarifas actuales.*
""")

    # ════════════════════════════════════════════════════════════
    # SECCIÓN 3: Panel de consumo de tokens detallado
    # ════════════════════════════════════════════════════════════
    st.header("📊 Consumo de Tokens")

    token_summary = config_store.get_token_summary()
    selected_model = st.session_state.get("selected_model", "gemini-2.5-flash")
    limits = config_store.get_free_tier_limits(selected_model)

    # ── Métricas principales ──
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

    # ── Barra de progreso grande ──
    rpd_pct = min(rpd_used / max(rpd_max, 1), 1.0)
    st.markdown(f"**Uso de cuota diaria ({selected_model}):**")
    st.progress(rpd_pct)
    if rpd_pct >= 1.0:
        st.error("🚫 Cuota gratuita diaria agotada. Si tu cuenta tiene facturación habilitada, las llamadas continuarán en tier de pago.")
    elif rpd_pct >= 0.8:
        st.warning(f"⚠️ Has usado {rpd_pct:.0%} de tu cuota diaria gratuita.")
    else:
        st.success(f"✅ Cuota diaria al {rpd_pct:.0%}.")

    # ── Gráfico de uso diario ──
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

    # ── Historial de operaciones recientes ──
    st.subheader("📝 Operaciones recientes")
    history = config_store.get_token_history(20)

    if history:
        df_hist = pd.DataFrame(history)
        df_hist.columns = ["Fecha/Hora", "Operación", "Modelo", "Prompt", "Respuesta", "Total"]
        # Formatear timestamp
        df_hist["Fecha/Hora"] = df_hist["Fecha/Hora"].apply(lambda x: x[:19].replace("T", " ") if x else "")
        st.dataframe(df_hist, use_container_width=True, hide_index=True)
    else:
        st.info("No hay operaciones registradas aún.")

    # ── Info adicional ──
    if token_summary['last_used']:
        st.caption(f"Última operación: {token_summary['last_used'][:19].replace('T', ' ')}")


main()
