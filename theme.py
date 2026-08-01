# ==============================================================================
# 🎨 THEME.PY — Identidade visual partilhada "Luminara Capital"
# Importado por Home.py e por todas as páginas em /pages para garantir uma
# aparência consistente (azul-marinho profundo + dourado) em toda a app.
# ==============================================================================

import streamlit as st

# ------------------------------------------------------------------------------
# Paleta de cores
# ------------------------------------------------------------------------------
NAVY_950 = "#05070f"
NAVY_900 = "#0a0e27"
NAVY_800 = "#0d1230"
NAVY_700 = "#131a3d"
GOLD_100 = "#f6e7c1"
GOLD_300 = "#e8c874"
GOLD_500 = "#d4af37"
GOLD_700 = "#b8912e"
IVORY = "#f5f5f0"


# ------------------------------------------------------------------------------
# CSS global da app (sidebar, tabelas, inputs, botões, tabs, alerts, etc.)
# ------------------------------------------------------------------------------
def inject_theme():
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@500;600;700&family=Cormorant+Garamond:ital,wght@0,500;0,600;1,500&family=Inter:wght@300;400;500;600&display=swap');

            :root {
                --navy-950: #05070f;
                --navy-900: #0a0e27;
                --navy-800: #0d1230;
                --navy-700: #131a3d;
                --gold-100: #f6e7c1;
                --gold-300: #e8c874;
                --gold-500: #d4af37;
                --gold-700: #b8912e;
                --ivory: #f5f5f0;
            }

            .stApp {
                background: radial-gradient(circle at 20% 0%, #0e1338 0%, var(--navy-900) 45%, var(--navy-950) 100%);
            }
            header[data-testid="stHeader"] { background: transparent; }

            html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
            .block-container { padding-top: 2rem; max-width: 1200px; }

            /* Sidebar */
            section[data-testid="stSidebar"] {
                background: linear-gradient(180deg, var(--navy-950) 0%, var(--navy-800) 100%);
                border-right: 1px solid rgba(212, 175, 55, 0.25);
            }
            section[data-testid="stSidebar"] * { color: var(--ivory) !important; }
            section[data-testid="stSidebar"] h1,
            section[data-testid="stSidebar"] h2,
            section[data-testid="stSidebar"] h3 {
                font-family: 'Playfair Display', serif;
                color: var(--gold-300) !important;
            }

            /* Texto geral */
            h1, h2, h3 { color: var(--ivory); font-family: 'Playfair Display', serif; }
            p, span, label, .stMarkdown { color: rgba(245, 245, 240, 0.88); }

            /* Inputs */
            .stTextInput input, .stNumberInput input, .stDateInput input,
            div[data-baseweb="select"] > div, div[data-baseweb="base-input"] {
                background-color: var(--navy-700) !important;
                color: var(--ivory) !important;
                border: 1px solid rgba(212, 175, 55, 0.3) !important;
            }
            .stTextInput label, .stNumberInput label, .stDateInput label,
            .stSelectbox label, .stSlider label { color: var(--gold-100) !important; }

            /* Botões */
            .stButton button, .stDownloadButton button {
                background: linear-gradient(135deg, var(--gold-700) 0%, var(--gold-500) 50%, var(--gold-300) 100%);
                color: var(--navy-950);
                border: none;
                font-weight: 600;
                letter-spacing: 0.02em;
                transition: transform 0.15s ease, box-shadow 0.15s ease;
            }
            .stButton button:hover, .stDownloadButton button:hover {
                transform: translateY(-1px);
                box-shadow: 0 6px 16px rgba(212, 175, 55, 0.35);
                color: var(--navy-950);
            }

            /* Cartões de métricas */
            div[data-testid="stMetric"] {
                background: linear-gradient(155deg, rgba(19, 26, 61, 0.85) 0%, rgba(10, 14, 39, 0.85) 100%);
                border: 1px solid rgba(212, 175, 55, 0.22);
                border-radius: 12px;
                padding: 0.9rem 1rem;
            }
            div[data-testid="stMetricValue"] { color: var(--gold-100); }
            div[data-testid="stMetricLabel"] { color: rgba(245, 245, 240, 0.65); }

            /* Tabelas / dataframes */
            div[data-testid="stDataFrame"], div[data-testid="stTable"] {
                border: 1px solid rgba(212, 175, 55, 0.22);
                border-radius: 10px;
                overflow: hidden;
            }

            /* Expanders */
            div[data-testid="stExpander"] {
                background: rgba(19, 26, 61, 0.5);
                border: 1px solid rgba(212, 175, 55, 0.2);
                border-radius: 10px;
            }

            /* Tabs */
            button[data-baseweb="tab"] { color: rgba(245, 245, 240, 0.6); }
            button[data-baseweb="tab"][aria-selected="true"] { color: var(--gold-300); border-bottom-color: var(--gold-500); }

            /* Alerts (info / success / warning / error) */
            div[data-testid="stAlert"] {
                background: rgba(212, 175, 55, 0.08);
                border: 1px solid rgba(212, 175, 55, 0.3);
                border-radius: 10px;
                color: var(--ivory);
            }

            /* ---------------- PAGE HEADER (usado nas páginas internas) ---------------- */
            .page-header {
                display: flex;
                align-items: center;
                gap: 0.9rem;
                padding: 0.4rem 0 1rem 0;
                margin-bottom: 0.6rem;
                border-bottom: 1px solid rgba(212, 175, 55, 0.22);
            }
            .page-header-icon {
                font-size: 2.1rem;
                filter: drop-shadow(0 0 10px rgba(212, 175, 55, 0.35));
            }
            .page-header-title {
                font-family: 'Playfair Display', serif;
                font-weight: 700;
                font-size: 1.9rem;
                background: linear-gradient(90deg, var(--gold-700) 0%, var(--gold-100) 45%, var(--gold-500) 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                line-height: 1.1;
            }
            .page-header-subtitle {
                font-family: 'Cormorant Garamond', serif;
                font-style: italic;
                color: rgba(245, 245, 240, 0.68);
                font-size: 1.02rem;
                margin-top: 0.15rem;
            }
            .page-header-text { display: flex; flex-direction: column; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(icon: str, title: str, subtitle: str = ""):
    """Cabeçalho estilizado a substituir st.title() + st.caption() nas páginas internas."""
    subtitle_html = f'<div class="page-header-subtitle">{subtitle}</div>' if subtitle else ""
    st.markdown(
        f"""
        <div class="page-header">
            <div class="page-header-icon">{icon}</div>
            <div class="page-header-text">
                <div class="page-header-title">{title}</div>
                {subtitle_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ------------------------------------------------------------------------------
# Plotly — layout escuro consistente com a marca
# ------------------------------------------------------------------------------
PLOTLY_COLORWAY = [GOLD_500, "#8FB3D9", "#7FD9A8", "#E8927C", GOLD_300, "#B79CE0"]

PLOTLY_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor=NAVY_800,
    plot_bgcolor=NAVY_800,
    font=dict(color=IVORY, family="Inter, sans-serif"),
    colorway=PLOTLY_COLORWAY,
    xaxis=dict(gridcolor="rgba(212,175,55,0.15)", zerolinecolor="rgba(212,175,55,0.25)", linecolor="rgba(212,175,55,0.3)"),
    yaxis=dict(gridcolor="rgba(212,175,55,0.15)", zerolinecolor="rgba(212,175,55,0.25)", linecolor="rgba(212,175,55,0.3)"),
    legend=dict(bgcolor="rgba(10,14,39,0.6)", bordercolor="rgba(212,175,55,0.3)", borderwidth=1),
    title=dict(font=dict(color=GOLD_100)),
)


def style_plotly(fig):
    """Aplica o tema Luminara (navy + dourado) a uma figura Plotly, sem alterar os dados."""
    fig.update_layout(**PLOTLY_LAYOUT)
    return fig


# ------------------------------------------------------------------------------
# Matplotlib — estilo escuro consistente com a marca
# ------------------------------------------------------------------------------
def apply_mpl_dark_style():
    import matplotlib.pyplot as plt

    plt.rcParams.update(
        {
            "figure.facecolor": NAVY_800,
            "axes.facecolor": NAVY_800,
            "savefig.facecolor": NAVY_800,
            "axes.edgecolor": GOLD_500,
            "axes.labelcolor": IVORY,
            "axes.titlecolor": GOLD_100,
            "text.color": IVORY,
            "xtick.color": IVORY,
            "ytick.color": IVORY,
            "grid.color": "#2a3158",
            "grid.alpha": 0.6,
            "legend.facecolor": NAVY_700,
            "legend.edgecolor": GOLD_500,
            "legend.labelcolor": IVORY,
            "font.family": "sans-serif",
        }
    )
