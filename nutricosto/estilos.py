"""Hoja de estilos CSS para la app Streamlit (estetica Claude).

Paleta:
  bg_warm     #FAF9F5  fondo principal (cream)
  bg_card     #FFFFFF  superficies elevadas
  bg_subtle   #F0EBE0  fondos secundarios (sidebar, tabs)
  border      #E5E0D5  bordes suaves
  text        #1F1E1B  tipografia primaria
  text_muted  #6B6862  tipografia secundaria
  accent      #C96442  coral Claude (acciones primarias)
  accent_hi   #B5563A  hover
"""

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,500;8..60,600&family=Inter:wght@400;500;600&display=swap');

:root {
    --bg-warm: #FAF9F5;
    --bg-card: #FFFFFF;
    --bg-subtle: #F0EBE0;
    --border: #E5E0D5;
    --text: #1F1E1B;
    --text-muted: #6B6862;
    --accent: #C96442;
    --accent-hi: #B5563A;
    --success: #5C8A52;
}

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, system-ui, sans-serif !important;
    color: var(--text);
}

h1, h2, h3, h4 {
    font-family: 'Source Serif 4', Georgia, serif !important;
    font-weight: 500 !important;
    letter-spacing: -0.01em;
    color: var(--text);
}

h1 { font-size: 2.4rem !important; }
h2 { font-size: 1.6rem !important; margin-top: 1.2rem !important; }
h3 { font-size: 1.2rem !important; }

.block-container {
    padding-top: 2.5rem !important;
    padding-bottom: 3rem !important;
    max-width: 1200px !important;
}

/* Tabs minimalistas */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    border-bottom: 1px solid var(--border);
    background: transparent;
}
.stTabs [data-baseweb="tab"] {
    height: 44px;
    padding: 0 18px;
    background: transparent;
    border-radius: 6px 6px 0 0;
    color: var(--text-muted);
    font-weight: 500;
}
.stTabs [aria-selected="true"] {
    background: transparent !important;
    color: var(--accent) !important;
    border-bottom: 2px solid var(--accent) !important;
}

/* Botones */
.stButton > button {
    border-radius: 8px !important;
    border: 1px solid var(--border) !important;
    font-weight: 500 !important;
    padding: 0.5rem 1.1rem !important;
    transition: all 0.15s ease;
}
.stButton > button[kind="primary"] {
    background: var(--accent) !important;
    color: #fff !important;
    border-color: var(--accent) !important;
}
.stButton > button[kind="primary"]:hover {
    background: var(--accent-hi) !important;
    border-color: var(--accent-hi) !important;
    box-shadow: 0 2px 8px rgba(201,100,66,0.18);
}

/* Metric cards */
[data-testid="stMetric"] {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px 18px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.02);
}
[data-testid="stMetricLabel"] {
    color: var(--text-muted) !important;
    font-size: 0.78rem !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: 500 !important;
}
[data-testid="stMetricValue"] {
    font-family: 'Source Serif 4', Georgia, serif !important;
    font-size: 1.7rem !important;
    font-weight: 500 !important;
    color: var(--text) !important;
}

/* Inputs numericos */
[data-testid="stNumberInput"] input {
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    background: var(--bg-card) !important;
}
[data-testid="stNumberInput"] input:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 2px rgba(201,100,66,0.12);
}

/* Sliders */
[data-baseweb="slider"] [role="slider"] {
    background: var(--accent) !important;
    border-color: var(--accent) !important;
}

/* DataFrames */
[data-testid="stDataFrame"] {
    border: 1px solid var(--border);
    border-radius: 10px;
    overflow: hidden;
}

/* Expander */
[data-testid="stExpander"] {
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    background: var(--bg-card);
}

/* Alertas */
[data-testid="stAlertContainer"] {
    border-radius: 10px;
    border: 1px solid var(--border);
}

/* Caption */
.stCaption, [data-testid="stCaptionContainer"] {
    color: var(--text-muted) !important;
    font-size: 0.85rem;
}

/* Divider mas sutil */
hr {
    border-color: var(--border) !important;
    margin: 1.8rem 0 !important;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: var(--bg-subtle);
    border-right: 1px solid var(--border);
}

/* Forms */
[data-testid="stForm"] {
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    background: var(--bg-card);
    padding: 1.2rem !important;
}

/* Card helper class via markdown */
.nc-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px 22px;
    margin-bottom: 14px;
}
.nc-card h4 {
    margin-top: 0 !important;
    color: var(--text) !important;
    font-size: 0.85rem !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-family: 'Inter', sans-serif !important;
    color: var(--text-muted) !important;
    font-weight: 600 !important;
    margin-bottom: 10px !important;
}

/* Hero header */
.nc-hero {
    padding: 8px 0 4px 0;
    margin-bottom: 8px;
}
.nc-hero-eyebrow {
    color: var(--accent);
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-bottom: 6px;
}
.nc-hero-sub {
    color: var(--text-muted);
    font-size: 1rem;
    max-width: 720px;
    line-height: 1.55;
}

/* Pill badge */
.nc-pill {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    background: var(--bg-subtle);
    color: var(--text-muted);
    border: 1px solid var(--border);
}
.nc-pill.ok { background: #EAF1E5; color: var(--success); border-color: #C9DCBF; }
.nc-pill.warn { background: #FBE9DF; color: var(--accent-hi); border-color: #F1CDB8; }

/* Section header */
.nc-section-title {
    font-family: 'Source Serif 4', Georgia, serif;
    font-size: 1.05rem;
    font-weight: 500;
    color: var(--text);
    margin: 8px 0 14px 0;
    display: flex;
    align-items: center;
    gap: 10px;
}
.nc-section-title::before {
    content: "";
    width: 3px;
    height: 18px;
    background: var(--accent);
    border-radius: 2px;
}

/* Hide Streamlit's default header chrome */
#MainMenu, footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; }
</style>
"""
