"""Gestión centralizada de tema visual, paleta de marca y sidebar footer.

Paleta de marca XML-JATS (Technical Brand Guide):
- Cyan  #00FFFF  (neon mark)
- Magenta #FF00FF (neon stop)
- Core white #FFFFFF
- Background #000000

Se derivan variantes suaves para que funcionen tanto en modo claro como oscuro.
"""

import base64
from pathlib import Path

import streamlit as st

# ─── Constantes de marca ────────────────────────────────────────────────
BRAND_CYAN = "#00FFFF"
BRAND_MAGENTA = "#FF00FF"
BRAND_DARK_BG = "#0a0e1a"
BRAND_VERSION = "v0.7.5"

LOGO_PATH = Path("resources/logos/logo.png")
LOGO_MARCA_PATH = Path("resources/logos/logo_marca.png")


def _logo_base64() -> str:
    """Devuelve el data-URI del logo en Base64 (cacheado en session)."""
    if "_logo_b64" not in st.session_state:
        try:
            if LOGO_PATH.exists():
                encoded = base64.b64encode(LOGO_PATH.read_bytes()).decode()
                st.session_state["_logo_b64"] = f"data:image/png;base64,{encoded}"
            else:
                st.session_state["_logo_b64"] = ""
        except Exception:
            st.session_state["_logo_b64"] = ""
    return st.session_state["_logo_b64"]


def is_dark_mode() -> bool:
    """Devuelve True si el usuario eligió modo oscuro."""
    return st.session_state.get("_theme_dark", True)


def inject_theme_css() -> None:
    """Inyecta el CSS global de marca adaptado al modo claro/oscuro.

    Debe llamarse una vez al principio de cada vista que necesite estilos,
    o centralizado en streamlit_app.py.
    """
    dark = is_dark_mode()

    if dark:
        bg_primary = "#0a0e1a"
        bg_secondary = "#111827"
        bg_card = "#1a1f35"
        text_primary = "#e8ecf1"
        text_secondary = "#94a3b8"
        accent = "#00e5ff"           # cyan ligeramente atenuado
        accent_hover = "#00bcd4"
        accent_secondary = "#e040fb" # magenta atenuado
        border_color = "#1e293b"
        btn_bg = "linear-gradient(135deg, #0891b2, #6d28d9)"
        btn_bg_hover = "linear-gradient(135deg, #06b6d4, #7c3aed)"
        btn_text = "#ffffff"
        sidebar_bg = "#0f1525"
        link_color = "#22d3ee"
        success_color = "#34d399"
        warning_color = "#fbbf24"
        error_color = "#e040fb"      # magenta brand en vez de rojo
        divider_color = "#1e293b"
        input_bg = "#1e293b"
        input_border = "#334155"
        tab_active_border = "#00e5ff"
        tab_text = "#94a3b8"
        tab_text_active = "#e8ecf1"
        progress_fill = "linear-gradient(90deg, #0891b2, #7c3aed)"
        glow_shadow = "0 0 15px rgba(0,229,255,0.15)"
    else:
        bg_primary = "#e8ecf1"       # gris claro (no blanco)
        bg_secondary = "#dfe3ea"
        bg_card = "#f0f2f7"
        text_primary = "#0f172a"     # casi negro para max contraste
        text_secondary = "#1e293b"   # gris muy oscuro
        accent = "#0e7490"           # cyan oscuro legible
        accent_hover = "#0891b2"
        accent_secondary = "#7e22ce" # magenta oscuro legible
        border_color = "#9ca3af"
        btn_bg = "linear-gradient(135deg, #0891b2, #7c3aed)"
        btn_bg_hover = "linear-gradient(135deg, #0e7490, #6d28d9)"
        btn_text = "#ffffff"
        sidebar_bg = "#d5dae3"       # gris sidebar más contraste
        link_color = "#0e7490"
        success_color = "#047857"
        warning_color = "#b45309"
        error_color = "#7e22ce"      # magenta brand en vez de rojo
        divider_color = "#9ca3af"
        input_bg = "#f0f2f7"
        input_border = "#6b7280"
        tab_active_border = "#0e7490"
        tab_text = "#374151"
        tab_text_active = "#0f172a"
        progress_fill = "linear-gradient(90deg, #0891b2, #7c3aed)"
        glow_shadow = "none"

    css = f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Share+Tech+Mono&display=swap');
    /* ═══════ XML-JATS Brand Theme ═══════ */

    /* --- Root & Body --- */
    .stApp {{
        background-color: {bg_primary} !important;
        color: {text_primary} !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
    }}

    /* --- Sidebar --- */
    section[data-testid="stSidebar"] {{
        background-color: {sidebar_bg} !important;
        border-right: 1px solid {border_color} !important;
    }}
    section[data-testid="stSidebar"] * {{
        color: {text_primary} !important;
    }}
    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] .stMarkdown span,
    section[data-testid="stSidebar"] .stCaption p,
    section[data-testid="stSidebar"] small {{
        color: {text_secondary} !important;
    }}
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {{
        color: {text_primary} !important;
    }}

    /* --- Sidebar nav items (brand typography & effects) --- */
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a,
    section[data-testid="stSidebar"] nav a,
    section[data-testid="stSidebar"] ul li a,
    section[data-testid="stSidebar"] a[data-testid="stSidebarNavLink"] {{
        font-family: 'Inter', sans-serif !important;
        font-size: 0.88rem !important;
        font-weight: 500 !important;
        letter-spacing: 0.01em !important;
        color: {text_secondary} !important;
        opacity: 1 !important;
        padding: 0.55rem 0.9rem !important;
        border-radius: 8px !important;
        margin: 2px 6px !important;
        transition: all 0.25s cubic-bezier(.4,0,.2,1) !important;
        position: relative !important;
        border: 1px solid transparent !important;
    }}
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a span,
    section[data-testid="stSidebar"] nav a span,
    section[data-testid="stSidebar"] ul li a span,
    section[data-testid="stSidebar"] a[data-testid="stSidebarNavLink"] span {{
        font-family: 'Inter', sans-serif !important;
        color: inherit !important;
        opacity: 1 !important;
    }}
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a:hover,
    section[data-testid="stSidebar"] nav a:hover,
    section[data-testid="stSidebar"] ul li a:hover,
    section[data-testid="stSidebar"] a[data-testid="stSidebarNavLink"]:hover {{
        color: {accent} !important;
        background: {'rgba(0,229,255,0.07)' if dark else 'rgba(14,116,144,0.08)'} !important;
        border-color: {'rgba(0,229,255,0.2)' if dark else 'rgba(14,116,144,0.15)'} !important;
        box-shadow: {'0 0 12px rgba(0,229,255,0.08)' if dark else 'none'} !important;
    }}
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"],
    section[data-testid="stSidebar"] nav a[aria-current="page"],
    section[data-testid="stSidebar"] a[data-testid="stSidebarNavLink"][aria-current="page"] {{
        color: {text_primary} !important;
        background: {'linear-gradient(135deg, rgba(0,229,255,0.12), rgba(224,64,251,0.08))' if dark else 'linear-gradient(135deg, rgba(14,116,144,0.1), rgba(126,34,206,0.06))'} !important;
        border-color: {'rgba(0,229,255,0.3)' if dark else 'rgba(14,116,144,0.25)'} !important;
        font-weight: 600 !important;
        box-shadow: {'inset 3px 0 0 ' + accent if dark else 'inset 3px 0 0 ' + accent} !important;
    }}
    /* Nav section separators */
    section[data-testid="stSidebar"] .st-emotion-cache-1rtdyuf,
    section[data-testid="stSidebar"] [data-testid="stSidebarNavItems"] p,
    section[data-testid="stSidebar"] [data-testid="stSidebarNavSeparator"] p,
    section[data-testid="stSidebar"] [data-testid="stSidebarNavSeparator"] span {{
        font-family: 'Share Tech Mono', monospace !important;
        font-size: 0.68rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.12em !important;
        color: {accent} !important;
        opacity: 0.7 !important;
        padding: 0.8rem 0.9rem 0.3rem 0.9rem !important;
    }}
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stRadio label,
    section[data-testid="stSidebar"] .stCheckbox label {{
        font-family: 'Inter', sans-serif !important;
        font-size: 0.78rem !important;
        font-weight: 500 !important;
        letter-spacing: 0.02em !important;
        color: {text_secondary} !important;
    }}
    /* Sidebar selectbox values → brand mono font */
    section[data-testid="stSidebar"] [data-baseweb="select"] span,
    section[data-testid="stSidebar"] [data-baseweb="select"] input {{
        font-family: 'Inter', sans-serif !important;
        font-size: 0.82rem !important;
        letter-spacing: normal !important;
    }}
    /* Sidebar text inputs */
    section[data-testid="stSidebar"] input,
    section[data-testid="stSidebar"] textarea {{
        font-family: 'Inter', sans-serif !important;
        font-size: 0.82rem !important;
    }}
    /* Sidebar checkbox text → brand mono */
    section[data-testid="stSidebar"] [data-testid="stCheckbox"] label span {{
        font-family: 'Inter', sans-serif !important;
        font-size: 0.8rem !important;
        letter-spacing: normal !important;
    }}
    /* Sidebar popover trigger → brand button */
    section[data-testid="stSidebar"] [data-testid="stPopoverButton"] button,
    section[data-testid="stSidebar"] .stPopover > button {{
        font-family: 'Inter', sans-serif !important;
        font-size: 0.82rem !important;
        font-weight: 500 !important;
        letter-spacing: 0.01em !important;
        border: 1.5px solid {'rgba(0,229,255,0.25)' if dark else 'rgba(14,116,144,0.22)'} !important;
        border-radius: 10px !important;
        background: {'rgba(0,229,255,0.04)' if dark else 'rgba(14,116,144,0.04)'} !important;
        color: {text_secondary} !important;
        padding: 0.45rem 1rem !important;
        transition: all 0.3s cubic-bezier(.4,0,.2,1) !important;
    }}
    section[data-testid="stSidebar"] [data-testid="stPopoverButton"] button:hover,
    section[data-testid="stSidebar"] .stPopover > button:hover {{
        border-color: {accent} !important;
        color: {accent} !important;
        background: {'rgba(0,229,255,0.08)' if dark else 'rgba(14,116,144,0.08)'} !important;
        box-shadow: {'0 0 12px rgba(0,229,255,0.1)' if dark else 'none'} !important;
    }}

    /* --- Labels (global) --- */
    .stApp label {{
        color: {text_primary} !important;
    }}
    .stApp p {{
        color: {text_primary} !important;
    }}

    /* --- Headings (brand typography) --- */
    @keyframes headingGlowPulse {{
        0%, 100% {{ text-shadow: 0 0 8px {'rgba(0,229,255,0.18)' if dark else 'rgba(14,116,144,0.10)'}; }}
        50% {{ text-shadow: 0 0 18px {'rgba(0,229,255,0.32)' if dark else 'rgba(14,116,144,0.18)'}; }}
    }}
    .stApp h1,
    .stApp h2,
    .stApp h3,
    .stApp h4,
    .stApp h5,
    .stApp h6 {{
        font-family: 'Share Tech Mono', monospace !important;
        letter-spacing: 0.04em !important;
        text-transform: uppercase !important;
    }}
    .stApp h1 {{
        color: {accent} !important;
        font-weight: 400 !important;
        font-size: clamp(1.25rem, 3.5vw, 1.75rem) !important;
        text-shadow: {glow_shadow};
        animation: headingGlowPulse 3s ease-in-out infinite;
        position: relative;
    }}
    .stApp h1::after {{
        content: '';
        display: block;
        margin-top: 0.4rem;
        height: 2px;
        border-radius: 2px;
        background: {'linear-gradient(90deg, ' + accent + ', ' + accent_secondary + ', transparent)' if dark else 'linear-gradient(90deg, ' + accent + ', ' + accent_secondary + ', transparent)'};
        opacity: 0.5;
    }}
    .stApp h2 {{
        color: {accent} !important;
        font-weight: 400 !important;
        font-size: clamp(1.05rem, 2.8vw, 1.35rem) !important;
        text-shadow: 0 0 6px {'rgba(0,229,255,0.12)' if dark else 'rgba(14,116,144,0.06)'};
    }}
    .stApp h3 {{
        color: {accent_secondary} !important;
        font-weight: 400 !important;
        font-size: clamp(0.95rem, 2.2vw, 1.15rem) !important;
    }}
    .stApp h4 {{
        color: {accent} !important;
        font-weight: 400 !important;
        font-size: 0.95rem !important;
        opacity: 0.85;
    }}

    /* --- Animated Buttons (shared) --- */
    @keyframes btnShimmer {{
        0% {{ background-position: 0% 50%; }}
        50% {{ background-position: 100% 50%; }}
        100% {{ background-position: 0% 50%; }}
    }}
    @keyframes btnPulseGlow {{
        0%, 100% {{ box-shadow: 0 0 8px rgba(8,145,178,0.3), 0 0 0 rgba(124,58,237,0); }}
        50% {{ box-shadow: 0 0 16px rgba(8,145,178,0.5), 0 0 30px rgba(124,58,237,0.2); }}
    }}

    /* --- Buttons (primary) --- */
    .stApp button[kind="primary"],
    .stApp .stButton > button[kind="primary"] {{
        background: linear-gradient(135deg, #0891b2, #6d28d9, #e040fb, #0891b2) !important;
        background-size: 300% 300% !important;
        animation: btnShimmer 4s ease infinite, btnPulseGlow 3s ease-in-out infinite !important;
        color: {btn_text} !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 700 !important;
        letter-spacing: 0.03em !important;
        padding: 0.55rem 1.4rem !important;
        transition: transform 0.2s cubic-bezier(0.34,1.56,0.64,1), filter 0.2s ease !important;
        position: relative !important;
        overflow: hidden !important;
    }}
    .stApp button[kind="primary"]:hover,
    .stApp .stButton > button[kind="primary"]:hover {{
        transform: translateY(-2px) scale(1.03) !important;
        filter: brightness(1.15) !important;
        box-shadow: 0 6px 24px rgba(8,145,178,0.45), 0 0 40px rgba(124,58,237,0.25) !important;
    }}
    .stApp button[kind="primary"]:active,
    .stApp .stButton > button[kind="primary"]:active {{
        transform: translateY(0px) scale(0.98) !important;
        filter: brightness(0.95) !important;
    }}

    /* --- Buttons (secondary) --- */
    .stApp button[kind="secondary"],
    .stApp .stButton > button:not([kind="primary"]) {{
        background: transparent !important;
        color: {accent} !important;
        border: 2px solid {accent} !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        letter-spacing: 0.02em !important;
        padding: 0.5rem 1.3rem !important;
        transition: all 0.3s cubic-bezier(0.34,1.56,0.64,1) !important;
        position: relative !important;
        background-image: linear-gradient({bg_card}, {bg_card}), linear-gradient(135deg, {accent}, {accent_secondary}) !important;
        background-origin: border-box !important;
        background-clip: padding-box, border-box !important;
    }}
    .stApp button[kind="secondary"]:hover,
    .stApp .stButton > button:not([kind="primary"]):hover {{
        background: linear-gradient(135deg, {accent}, {accent_secondary}) !important;
        background-image: none !important;
        color: #ffffff !important;
        border-color: transparent !important;
        transform: translateY(-2px) scale(1.03) !important;
        box-shadow: 0 4px 16px rgba(8,145,178,0.3), 0 0 20px rgba(124,58,237,0.15) !important;
    }}
    .stApp button[kind="secondary"]:active,
    .stApp .stButton > button:not([kind="primary"]):active {{
        transform: translateY(0px) scale(0.97) !important;
    }}

    /* --- Unified border-radius for ALL interactive elements --- */
    .stApp button {{
        border-radius: 10px !important;
    }}

    /* --- Tabs (brand step navigation) --- */
    @keyframes tabGlowSlide {{
        0% {{ background-position: 200% center; }}
        100% {{ background-position: -200% center; }}
    }}
    @keyframes tabIndicatorPulse {{
        0%, 100% {{ opacity: 0.7; }}
        50% {{ opacity: 1; }}
    }}
    .stTabs [data-baseweb="tab-list"] {{
        border-bottom: 1px solid {border_color} !important;
        gap: 0.25rem !important;
        padding-bottom: 0 !important;
        position: relative !important;
        align-items: flex-end !important;
    }}
    .stTabs [data-baseweb="tab"] {{
        font-family: 'Inter', sans-serif !important;
        color: {tab_text} !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        letter-spacing: 0.02em !important;
        text-transform: uppercase !important;
        padding: 0.9rem 1.2rem !important;
        border-radius: 10px 10px 0 0 !important;
        border: 1px solid transparent !important;
        border-bottom: 1px solid transparent !important;
        margin-bottom: -1px !important;
        background: transparent !important;
        transition: color 0.3s ease, background 0.3s ease, border-color 0.3s ease, text-shadow 0.3s ease !important;
        position: relative !important;
        overflow: hidden !important;
        box-sizing: border-box !important;
    }}
    .stTabs [data-baseweb="tab"]::before {{
        content: "" !important;
        position: absolute !important;
        inset: 0 !important;
        background: linear-gradient(90deg, transparent, rgba(0,229,255,0.06), transparent) !important;
        background-size: 200% 100% !important;
        opacity: 0 !important;
        transition: opacity 0.3s ease !important;
    }}
    .stTabs [data-baseweb="tab"]:hover {{
        color: {tab_text_active} !important;
        background: {bg_card} !important;
        border-color: {border_color} !important;
        border-bottom-color: {border_color} !important;
    }}
    .stTabs [data-baseweb="tab"]:hover::before {{
        opacity: 1 !important;
        animation: tabGlowSlide 2s linear infinite !important;
    }}
    .stTabs [aria-selected="true"] {{
        font-family: 'Inter', sans-serif !important;
        color: {accent} !important;
        font-weight: 700 !important;
        background: {bg_card} !important;
        border-color: {border_color} !important;
        border-bottom-color: {bg_card} !important;
        z-index: 1 !important;
        text-shadow: 0 0 12px rgba(0,229,255,0.3) !important;
    }}
    .stTabs [aria-selected="true"]::after {{
        content: "" !important;
        position: absolute !important;
        bottom: 0 !important;
        left: 10% !important;
        width: 80% !important;
        height: 2px !important;
        background: linear-gradient(90deg, {accent}, {accent_secondary}, {accent}) !important;
        background-size: 200% 100% !important;
        animation: tabGlowSlide 3s linear infinite, tabIndicatorPulse 2s ease-in-out infinite !important;
        border-radius: 2px !important;
    }}
    /* Override Streamlit default red/primary highlight on tabs */
    .stTabs [data-baseweb="tab-highlight"] {{
        background: linear-gradient(90deg, {accent}, {accent_secondary}) !important;
        height: 2px !important;
        border-radius: 2px !important;
    }}
    html body .stApp .stTabs [data-baseweb="tab-highlight"] {{
        background: linear-gradient(90deg, {accent}, {accent_secondary}) !important;
        height: 2px !important;
    }}
    .stTabs [data-baseweb="tab-border"] {{
        background-color: {border_color} !important;
        height: 1px !important;
    }}
    /* Tab panel smooth entrance */
    .stTabs [data-baseweb="tab-panel"] {{
        animation: fadeInTab 0.35s ease-out !important;
    }}
    @keyframes fadeInTab {{
        from {{ opacity: 0; transform: translateY(6px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}

    /* --- Inputs --- */
    .stApp input, .stApp textarea {{
        background-color: {input_bg} !important;
        border-color: {input_border} !important;
        color: {text_primary} !important;
        border-radius: 10px !important;
        transition: border-color 0.3s ease, box-shadow 0.3s ease !important;
    }}
    .stApp input:focus, .stApp textarea:focus {{
        border-color: {accent} !important;
        box-shadow: 0 0 0 2px rgba(8,145,178,0.25), 0 0 12px rgba(8,145,178,0.1) !important;
    }}

    /* --- Multiselect tags (selected items pills) --- */
    .stApp [data-baseweb="tag"] {{
        background-color: {'rgba(0,229,255,0.13)' if dark else 'rgba(14,116,144,0.12)'} !important;
        border: 1.5px solid {'rgba(0,229,255,0.45)' if dark else 'rgba(14,116,144,0.4)'} !important;
        border-radius: 6px !important;
        color: {'#67e8f9' if dark else '#0e7490'} !important;
    }}
    .stApp [data-baseweb="tag"] span {{
        color: {'#67e8f9' if dark else '#0e7490'} !important;
    }}
    .stApp [data-baseweb="tag"] svg {{
        fill: {'#67e8f9' if dark else '#0e7490'} !important;
    }}
    .stApp [data-baseweb="tag"]:hover {{
        background-color: {'rgba(0,229,255,0.22)' if dark else 'rgba(14,116,144,0.2)'} !important;
        border-color: {'rgba(0,229,255,0.65)' if dark else 'rgba(14,116,144,0.6)'} !important;
    }}

    /* --- Select boxes (animated brand style) --- */
    @keyframes selectFocusGlow {{
        0%, 100% {{ box-shadow: 0 0 0 2px rgba(8,145,178,0.3), 0 0 8px rgba(8,145,178,0.1); }}
        50% {{ box-shadow: 0 0 0 2px rgba(8,145,178,0.5), 0 0 16px rgba(124,58,237,0.15); }}
    }}
    .stApp [data-baseweb="select"] {{
        background-color: {input_bg} !important;
    }}
    .stApp [data-baseweb="select"] > div {{
        background-color: {input_bg} !important;
        color: {text_primary} !important;
        border: 1.5px solid {input_border} !important;
        border-radius: 10px !important;
        transition: border-color 0.3s ease, box-shadow 0.3s ease !important;
    }}
    .stApp [data-baseweb="select"] > div:hover {{
        border-color: {accent} !important;
    }}
    .stApp [data-baseweb="select"][aria-expanded="true"] > div,
    .stApp [data-baseweb="select"]:focus-within > div {{
        border-color: {accent} !important;
        animation: selectFocusGlow 2s ease-in-out infinite !important;
    }}
    .stApp [data-baseweb="select"] span {{
        color: {text_primary} !important;
    }}
    .stApp [data-baseweb="select"] svg {{
        fill: {accent} !important;
        transition: transform 0.3s ease !important;
    }}
    .stApp [data-baseweb="select"][aria-expanded="true"] svg {{
        transform: rotate(180deg) !important;
    }}
    section[data-testid="stSidebar"] [data-baseweb="select"] {{
        background-color: transparent !important;
    }}
    section[data-testid="stSidebar"] [data-baseweb="select"] > div {{
        background-color: {input_bg} !important;
        color: {text_primary} !important;
        border: 1.5px solid {'rgba(0,229,255,0.2)' if dark else 'rgba(14,116,144,0.18)'} !important;
        border-radius: 10px !important;
        transition: all 0.3s cubic-bezier(.4,0,.2,1) !important;
        box-shadow: {'0 1px 4px rgba(0,0,0,0.15)' if dark else '0 1px 3px rgba(0,0,0,0.06)'} !important;
    }}
    section[data-testid="stSidebar"] [data-baseweb="select"] > div:hover {{
        border-color: {accent} !important;
        box-shadow: {'0 0 10px rgba(0,229,255,0.12), 0 2px 6px rgba(0,0,0,0.15)' if dark else '0 0 8px rgba(14,116,144,0.1), 0 2px 5px rgba(0,0,0,0.08)'} !important;
    }}
    section[data-testid="stSidebar"] [data-baseweb="select"]:focus-within > div {{
        border-color: {accent} !important;
        animation: selectFocusGlow 2s ease-in-out infinite !important;
    }}
    section[data-testid="stSidebar"] [data-baseweb="select"] svg {{
        fill: {accent} !important;
        transition: transform 0.3s ease !important;
    }}
    section[data-testid="stSidebar"] [data-baseweb="select"][aria-expanded="true"] svg {{
        transform: rotate(180deg) !important;
    }}
    section[data-testid="stSidebar"] input,
    section[data-testid="stSidebar"] textarea {{
        background-color: {input_bg} !important;
        color: {text_primary} !important;
        border: 1.5px solid {'rgba(0,229,255,0.2)' if dark else 'rgba(14,116,144,0.18)'} !important;
        border-radius: 10px !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 0.82rem !important;
        transition: all 0.3s cubic-bezier(.4,0,.2,1) !important;
        box-shadow: {'0 1px 4px rgba(0,0,0,0.15)' if dark else '0 1px 3px rgba(0,0,0,0.06)'} !important;
    }}
    section[data-testid="stSidebar"] input:focus,
    section[data-testid="stSidebar"] textarea:focus {{
        border-color: {accent} !important;
        animation: selectFocusGlow 2s ease-in-out infinite !important;
    }}

    /* --- Toggle / Checkbox in sidebar --- */
    section[data-testid="stSidebar"] [data-testid="stCheckbox"] label span,
    section[data-testid="stSidebar"] .stToggle label span,
    .stApp [data-testid="stCheckbox"] label span,
    .stApp .stToggle label span {{
        color: {text_primary} !important;
        font-weight: 600 !important;
    }}
    /* Toggle track override for visibility */
    .stApp .stToggle [data-testid="stToggle"] > label > div[role="checkbox"] {{
        border: 2px solid {input_border} !important;
    }}
    .stApp .stToggle [data-testid="stToggle"] > label > div[role="checkbox"][aria-checked="false"] {{
        background-color: {border_color} !important;
    }}

    /* --- Expander / Popover / Status --- */
    .stApp details {{
        border-color: {border_color} !important;
        background-color: {bg_card} !important;
        border-radius: 10px !important;
    }}
    .stApp details summary {{
        color: {text_primary} !important;
        background-color: {bg_card} !important;
        border-radius: 10px !important;
    }}
    .stApp details[open] summary {{
        background-color: {bg_card} !important;
    }}
    .stApp details summary p,
    .stApp details summary span {{
        color: {text_primary} !important;
    }}
    .stApp [data-testid="stExpander"] details summary,
    .stApp [data-testid="stExpander"] details summary p,
    .stApp [data-testid="stExpander"] details summary span {{
        color: {text_primary} !important;
        background-color: {bg_card} !important;
    }}
    .stApp [data-testid="stExpander"] details[open] > summary {{
        background-color: {bg_card} !important;
    }}
    .stApp [data-testid="stStatusWidget"] summary,
    .stApp [data-testid="stStatusWidget"] summary p,
    .stApp [data-testid="stStatusWidget"] summary span {{
        color: {text_primary} !important;
    }}
    .stApp [data-testid="stStatusWidget"] details,
    .stApp [data-testid="stStatusWidget"] details summary {{
        background-color: {bg_card} !important;
    }}

    /* --- Dividers --- */
    .stApp hr {{
        border-color: {divider_color} !important;
    }}

    /* --- Progress bar --- */
    .stApp .stProgress > div > div > div {{
        background: {progress_fill} !important;
    }}

    /* --- Links --- */
    .stApp a {{
        color: {link_color} !important;
    }}

    /* --- Alert boxes --- */
    .stApp [data-testid="stAlert"] {{
        border-radius: 10px !important;
    }}

    /* --- Metric cards --- */
    .stApp [data-testid="stMetric"] {{
        background-color: {bg_card} !important;
        border: 1px solid {border_color} !important;
        border-radius: 10px !important;
        padding: 1rem !important;
    }}
    .stApp [data-testid="stMetricValue"] {{
        color: {accent} !important;
    }}

    /* --- File uploader --- */
    .stApp [data-testid="stFileUploader"] section {{
        border: 2px dashed {border_color} !important;
        border-radius: 10px !important;
        background-color: {bg_card} !important;
    }}
    .stApp [data-testid="stFileUploader"] section:hover {{
        border-color: {accent} !important;
    }}
    .stApp [data-testid="stFileUploader"] section span,
    .stApp [data-testid="stFileUploader"] section small {{
        color: {text_secondary} !important;
    }}
    /* Uploaded file name & info row */
    .stApp [data-testid="stFileUploader"] [data-testid="stFileUploaderFile"],
    .stApp [data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] span,
    .stApp [data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] small,
    .stApp [data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] div,
    .stApp [data-testid="stFileUploader"] [data-testid="stFileUploaderFileName"] {{
        color: {text_primary} !important;
    }}

    /* --- Sidebar brand footer --- */
    .sidebar-brand-footer {{
        text-align: center;
        padding: 0.5rem 0.8rem 0.6rem 0.8rem;
        border-top: 1px solid {'rgba(0,229,255,0.15)' if dark else 'rgba(14,116,144,0.15)'};
        margin-top: 1rem;
    }}
    .sidebar-brand-footer .brand-name {{
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        font-size: 0.72rem;
        letter-spacing: 0.05em;
        color: {text_secondary};
        margin-bottom: 2px;
    }}
    .sidebar-brand-footer .brand-version {{
        font-family: 'Inter', sans-serif;
        font-size: 0.66rem;
        letter-spacing: 0.04em;
        color: {accent};
        opacity: 0.7;
    }}

    /* --- Theme toggle switch (custom branded) --- */
    @keyframes toggleGlowPulse {{
        0%, 100% {{ box-shadow: 0 0 8px {'rgba(0,229,255,0.2)' if dark else 'rgba(14,116,144,0.12)'}; }}
        50% {{ box-shadow: 0 0 18px {'rgba(0,229,255,0.35)' if dark else 'rgba(14,116,144,0.22)'}; }}
    }}

    /* --- Sidebar logo header --- */
    .sidebar-logo-header {{
        text-align: center;
        padding: 0.5rem 0 0.75rem 0;
    }}
    .sidebar-logo-header img {{
        border-radius: 14px;
        box-shadow: {glow_shadow};
    }}
    .sidebar-logo-header .app-title {{
        font-weight: 800;
        font-size: 1.1rem;
        background: linear-gradient(135deg, {accent}, {accent_secondary});
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-top: 0.4rem;
    }}

    /* --- Sidebar theme pills toggle (brand restyle) --- */
    section[data-testid="stSidebar"] [data-testid="stPills"] {{
        display: flex !important;
        justify-content: center !important;
    }}
    section[data-testid="stSidebar"] [data-testid="stPills"] > div {{
        background: {'linear-gradient(135deg, rgba(15,21,37,0.95), rgba(26,31,53,0.9))' if dark else 'linear-gradient(135deg, rgba(240,242,247,0.95), rgba(213,218,227,0.9))'} !important;
        border: 1.5px solid {'rgba(0,229,255,0.3)' if dark else 'rgba(14,116,144,0.22)'} !important;
        border-radius: 26px !important;
        padding: 3px !important;
        gap: 0 !important;
        display: inline-flex !important;
        position: relative !important;
        overflow: hidden !important;
        animation: toggleGlowPulse 3s ease-in-out infinite !important;
        max-width: 240px !important;
    }}
    section[data-testid="stSidebar"] [data-testid="stPills"] > div::before {{
        content: '' !important;
        position: absolute !important;
        top: -1px !important; left: -1px !important; right: -1px !important; bottom: -1px !important;
        border-radius: 26px !important;
        background: {'linear-gradient(135deg, rgba(0,229,255,0.15), rgba(224,64,251,0.1))' if dark else 'linear-gradient(135deg, rgba(14,116,144,0.1), rgba(126,34,206,0.08))'} !important;
        z-index: 0 !important;
        pointer-events: none !important;
    }}
    section[data-testid="stSidebar"] [data-testid="stPills"] button {{
        position: relative !important;
        z-index: 1 !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 0.76rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.03em !important;
        padding: 7px 20px !important;
        border-radius: 22px !important;
        border: 1px solid transparent !important;
        box-shadow: none !important;
        background: transparent !important;
        background-color: transparent !important;
        color: {text_secondary} !important;
        transition: all 0.35s cubic-bezier(.4,0,.2,1) !important;
        min-height: unset !important;
        line-height: 1.4 !important;
        text-transform: uppercase !important;
        cursor: pointer !important;
    }}
    section[data-testid="stSidebar"] [data-testid="stPills"] button:hover {{
        color: {accent} !important;
        background: {'rgba(0,229,255,0.06)' if dark else 'rgba(14,116,144,0.06)'} !important;
    }}
    section[data-testid="stSidebar"] [data-testid="stPills"] button[aria-checked="true"],
    section[data-testid="stSidebar"] [data-testid="stPills"] button[aria-pressed="true"],
    section[data-testid="stSidebar"] [data-testid="stPills"] button[data-active="true"] {{
        background: {'linear-gradient(135deg, rgba(0,229,255,0.22), rgba(224,64,251,0.16))' if dark else 'linear-gradient(135deg, rgba(14,116,144,0.16), rgba(126,34,206,0.12))'} !important;
        color: {accent} !important;
        font-weight: 700 !important;
        box-shadow: {'0 0 14px rgba(0,229,255,0.2), inset 0 0 10px rgba(0,229,255,0.08)' if dark else '0 0 10px rgba(14,116,144,0.12), inset 0 0 8px rgba(14,116,144,0.06)'} !important;
        border: 1px solid {'rgba(0,229,255,0.35)' if dark else 'rgba(14,116,144,0.25)'} !important;
    }}
    section[data-testid="stSidebar"] [data-testid="stPills"] button[aria-checked="false"],
    section[data-testid="stSidebar"] [data-testid="stPills"] button[aria-pressed="false"] {{
        background: transparent !important;
        background-color: transparent !important;
        color: {text_secondary} !important;
        border: 1px solid transparent !important;
    }}
    /* Hide the empty pills label */
    section[data-testid="stSidebar"] [data-testid="stPills"] > label {{
        display: none !important;
    }}

    /* --- Caption & small text (global) --- */
    .stApp .stCaption, .stApp .stCaption p,
    .stApp [data-testid="stCaptionContainer"] p {{
        color: {text_secondary} !important;
    }}
    .stApp small {{
        color: {text_secondary} !important;
    }}

    /* --- Streamlit alert overrides (brand colors) --- */
    .stApp [data-testid="stAlert"][data-baseweb] div[role="alert"] {{
        color: {text_primary} !important;
    }}

    /* --- Select popover / dropdown (list items) --- */
    [data-baseweb="popover"] li,
    [data-baseweb="popover"] ul,
    [data-baseweb="menu"] li {{
        background-color: {bg_card} !important;
        color: {text_primary} !important;
    }}
    [data-baseweb="popover"] li:hover,
    [data-baseweb="menu"] li:hover {{
        background-color: {'rgba(0,229,255,0.15)' if dark else 'rgba(14,116,144,0.12)'} !important;
        color: {accent} !important;
    }}

    /* ═══ Override ALL Streamlit red/primary focus rings ═══ */
    /* Radio buttons */
    @keyframes radioSelectPulse {{
        0% {{ box-shadow: 0 0 0 0 rgba(8,145,178,0.4); }}
        70% {{ box-shadow: 0 0 0 6px rgba(8,145,178,0); }}
        100% {{ box-shadow: 0 0 0 0 rgba(8,145,178,0); }}
    }}
    .stApp .stRadio [role="radiogroup"] label > div:first-child {{
        border-color: {input_border} !important;
        transition: border-color 0.3s ease, box-shadow 0.3s ease !important;
    }}
    .stApp .stRadio [role="radiogroup"] label > div:first-child:hover {{
        border-color: {accent} !important;
    }}
    .stApp .stRadio [role="radiogroup"] [aria-checked="true"] > div:first-child,
    .stApp .stRadio [role="radiogroup"] input:checked + div {{
        border-color: {accent} !important;
        background-color: {accent} !important;
        animation: radioSelectPulse 0.5s ease-out !important;
    }}
    /* Radio/Toggle checked inner fill */
    .stApp [data-baseweb="radio"] [aria-checked="true"] div div {{
        background-color: {accent} !important;
    }}
    .stApp [data-baseweb="radio"] div {{
        border-color: {input_border} !important;
    }}
    .stApp [data-baseweb="radio"] [aria-checked="true"] div {{
        border-color: {accent} !important;
    }}

    /* Checkbox brand override */
    .stApp [data-testid="stCheckbox"] [role="checkbox"][aria-checked="true"] {{
        background-color: {accent} !important;
        border-color: {accent} !important;
    }}
    .stApp [data-testid="stCheckbox"] [role="checkbox"] {{
        border-color: {input_border} !important;
        transition: all 0.3s ease !important;
    }}
    .stApp [data-testid="stCheckbox"] [role="checkbox"]:hover {{
        border-color: {accent} !important;
    }}

    /* Toggle/Switch brand override */
    .stApp [data-testid="stToggle"] [role="checkbox"][aria-checked="true"],
    .stApp .stToggle [role="checkbox"][aria-checked="true"] {{
        background-color: {accent} !important;
        border-color: {accent} !important;
    }}

    /* Slider brand override */
    .stApp [data-testid="stSlider"] [role="slider"] {{
        background-color: {accent} !important;
        border-color: {accent} !important;
    }}
    .stApp [data-testid="stSlider"] [data-testid="stThumbValue"] {{
        color: {accent} !important;
    }}
    .stApp .stSlider > div > div > div > div {{
        background: linear-gradient(90deg, {accent}, {accent_secondary}) !important;
    }}

    /* Selectbox dropdown list brand styling */
    [data-baseweb="popover"] [data-baseweb="menu"],
    [data-baseweb="popover"] ul {{
        border: 1px solid {accent} !important;
        border-radius: 10px !important;
        overflow: hidden !important;
    }}
    [data-baseweb="popover"] li[aria-selected="true"] {{
        background: linear-gradient(135deg, {accent}, {accent_secondary}) !important;
        color: #ffffff !important;
    }}

    /* Generic focus-visible override to kill any remaining red */
    .stApp *:focus-visible {{
        outline-color: {accent} !important;
    }}
    .stApp [data-baseweb] *:focus {{
        border-color: {accent} !important;
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)  # safe: all values are internal constants


def render_sidebar_header() -> None:
    """Muestra el logo en la parte superior del sidebar vía st.logo."""
    if LOGO_PATH.exists():
        st.logo(LOGO_PATH, size="large")


def render_sidebar_footer() -> None:
    """Muestra el toggle de tema + branding en la parte inferior del sidebar."""
    # ── Toggle de tema integrado ──
    render_theme_toggle()

    # ── Branding ──
    st.markdown(
        f"""
        <div class="sidebar-brand-footer">
            <div class="brand-name">Universidad de Valparaíso</div>
            <div class="brand-version">Transformador XML JATS {BRAND_VERSION}</div>
        </div>
        """,
        unsafe_allow_html=True,  # safe: all values are internal constants
    )


def _logo_marca_base64() -> str:
    """Devuelve el data-URI del logo de marca en Base64 (cacheado en session)."""
    if "_logo_marca_b64" not in st.session_state:
        try:
            if LOGO_MARCA_PATH.exists():
                encoded = base64.b64encode(LOGO_MARCA_PATH.read_bytes()).decode()
                st.session_state["_logo_marca_b64"] = f"data:image/png;base64,{encoded}"
            else:
                st.session_state["_logo_marca_b64"] = ""
        except Exception:
            st.session_state["_logo_marca_b64"] = ""
    return st.session_state["_logo_marca_b64"]


def render_hero_header() -> None:
    """Renderiza la cabecera hero profesional animada con logo y tipografía de marca."""
    dark = is_dark_mode()
    logo_src = _logo_base64()

    # Colores adaptados al modo
    if dark:
        title_cyan = "#00e5ff"
        subtitle_color = "#e040fb"
        line_gradient = "linear-gradient(90deg, #00e5ff, #e040fb, #00e5ff)"
        glow = "0 0 30px rgba(0,229,255,0.3), 0 0 60px rgba(224,64,251,0.15)"
        text_muted = "#94a3b8"
        separator_color = "rgba(0,229,255,0.2)"
    else:
        title_cyan = "#0e7490"
        subtitle_color = "#7e22ce"
        line_gradient = "linear-gradient(90deg, #0e7490, #7e22ce, #0e7490)"
        glow = "0 4px 20px rgba(14,116,144,0.15)"
        text_muted = "#475569"
        separator_color = "rgba(14,116,144,0.2)"

    html = f"""
    <link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap" rel="stylesheet">
    <style>
    @keyframes heroFadeIn {{
        from {{ opacity: 0; transform: translateY(-18px); }}
        to   {{ opacity: 1; transform: translateY(0); }}
    }}
    @keyframes heroLogoIn {{
        from {{ opacity: 0; transform: scale(0.7) rotate(-8deg); }}
        to   {{ opacity: 1; transform: scale(1) rotate(0deg); }}
    }}
    @keyframes heroLineExpand {{
        from {{ width: 0; }}
        to   {{ width: 100%; }}
    }}
    @keyframes subtitleSlide {{
        from {{ opacity: 0; transform: translateX(-30px); }}
        to   {{ opacity: 1; transform: translateX(0); }}
    }}
    @keyframes glowPulse {{
        0%, 100% {{ box-shadow: {glow}; }}
        50% {{ box-shadow: {glow.replace('0.3', '0.5').replace('0.15', '0.3')}; }}
    }}
    .hero-header-container {{
        display: flex;
        align-items: center;
        gap: 1.5rem;
        padding: 1.2rem 1.5rem;
        margin-bottom: 1.2rem;
        border-radius: 16px;
        animation: heroFadeIn 0.8s ease-out;
        position: relative;
        overflow: hidden;
    }}
    .hero-logo {{
        flex-shrink: 0;
        animation: heroLogoIn 0.9s cubic-bezier(0.34, 1.56, 0.64, 1);
    }}
    .hero-logo img {{
        width: 100px;
        height: 100px;
        border-radius: 16px;
        object-fit: contain;
        filter: drop-shadow(0 2px 8px rgba(0,0,0,0.2));
        animation: glowPulse 3s ease-in-out infinite;
    }}
    .hero-text {{
        display: flex;
        flex-direction: column;
        gap: 0.15rem;
        min-width: 0;
    }}
    @keyframes bracketFlicker {{
        0%, 100% {{ opacity: 1; }}
        50% {{ opacity: 0.4; }}
    }}
    @keyframes tagReveal {{
        from {{ max-width: 0; opacity: 0; }}
        to   {{ max-width: 300px; opacity: 1; }}
    }}
    .hero-title,
    .hero-title * {{
        font-family: 'Share Tech Mono', monospace !important;
    }}
    .hero-title {{
        font-size: clamp(1.1rem, 4vw, 2rem);
        font-weight: 400;
        letter-spacing: 0.04em;
        color: {title_cyan};
        margin: 0;
        line-height: 1.15;
        white-space: nowrap;
        animation: heroFadeIn 1s ease-out 0.2s both;
    }}
    @media (max-width: 480px) {{
        .hero-logo img {{
            width: 60px;
            height: 60px;
        }}
        .hero-header-container {{
            gap: 0.8rem;
            padding: 0.8rem 1rem;
        }}
    }}
    .hero-title .hero-bracket {{
        color: {subtitle_color};
        font-weight: 400;
        animation: bracketFlicker 2.5s ease-in-out 1.2s 2;
    }}
    .hero-title .hero-tag {{
        display: inline-block;
        overflow: hidden;
        white-space: nowrap;
        animation: tagReveal 0.8s ease-out 0.6s both;
        vertical-align: bottom;
    }}
    .hero-title .hero-tag-inner {{
        color: {subtitle_color};
        font-weight: 400;
    }}
    .hero-subtitle {{
        font-family: 'Share Tech Mono', monospace;
        font-size: 0.92rem;
        color: {subtitle_color};
        margin: 0;
        letter-spacing: 0.06em;
        animation: subtitleSlide 0.8s ease-out 0.5s both;
    }}
    .hero-tagline {{
        font-size: 0.78rem;
        color: {text_muted};
        margin: 0.2rem 0 0 0;
        letter-spacing: 0.02em;
        animation: subtitleSlide 0.8s ease-out 0.7s both;
    }}
    .hero-line {{
        height: 2px;
        background: {line_gradient};
        border: none;
        margin-top: 0.6rem;
        border-radius: 2px;
        animation: heroLineExpand 1s ease-out 0.9s both;
    }}
    </style>
    <div class="hero-header-container">
        <div class="hero-logo">
            <img src="{logo_src}" alt="XML JATS Logo" />
        </div>
        <div class="hero-text">
            <h1 class="hero-title">Transformador <span class="hero-bracket">&lt;</span><span class="hero-tag"><span class="hero-tag-inner">XML-JATS</span></span><span class="hero-bracket">&gt;</span></h1>
            <p class="hero-subtitle">Convierte documentos Word a XML JATS con IA</p>
            <p class="hero-tagline">Sistema de marcado inteligente &bull; JATS Publishing 1.3</p>
            <div class="hero-line"></div>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)  # safe: all values are internal constants


def render_theme_toggle() -> None:
    """Dibuja un toggle de tema claro/oscuro con st.pills estilizado."""
    options = ["🌙 Oscuro", "☀️ Claro"]
    current = options[0] if is_dark_mode() else options[1]
    choice = st.pills("", options, default=current, key="_theme_pills")
    new_dark = choice == options[0]
    if new_dark != is_dark_mode():
        st.session_state["_theme_dark"] = new_dark
        st.rerun()
