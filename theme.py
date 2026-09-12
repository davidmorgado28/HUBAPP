# ==============================================================================
# 🌳 THEME.PY — Identidade visual partilhada "OAK & VALUE"
# Importado por Home.py e por todas as páginas em /pages para garantir uma
# aparência consistente (branco quente + verde carvalho) em toda a app.
# ==============================================================================

import streamlit as st

# ------------------------------------------------------------------------------
# Identidade da aplicação
# ------------------------------------------------------------------------------
APP_NAME = "OAK Research App"     # nome da aplicação (usado em títulos/rodapés)
PAGE_TITLE = "OAK & VALUE"        # nome da página (browser tab / cabeçalho)

# ------------------------------------------------------------------------------
# Paleta de cores — branco quente (base) > verde carvalho (dominante, todos os tons)
# ------------------------------------------------------------------------------
WHITE = "#F1EEE4"          # branco quente e um pouco mais escuro (fundo principal)
CREAM = "#E8E4D6"          # painéis/cartões, ligeiramente mais escuro que o fundo
MIST = "#E1E7DC"           # branco com traço de verde, para a sidebar

OAK_900 = "#1E2E22"        # verde carvalho profundo — texto de destaque, títulos
OAK_700 = "#2F4A38"        # verde carvalho principal — botões, ícones, ênfase
OAK_600 = "#3E6249"        # verde médio-escuro — bordas de destaque, divisores
OAK_500 = "#4F7058"        # verde médio — texto secundário
OAK_400 = "#6B8F73"        # verde médio-claro — realces, badges
OAK_300 = "#8FAB93"        # verde claro — bordas, linhas subtis
OAK_100 = "#DCE6DE"        # verde muito claro — fundos subtis, hover

INK = "#1C2420"            # quase-preto esverdeado — texto de corpo


# ------------------------------------------------------------------------------
# CSS global da app (sidebar, tabelas, inputs, botões, tabs, alerts, etc.)
# ------------------------------------------------------------------------------
def inject_theme():
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@500;600;700&family=Cormorant+Garamond:ital,wght@0,500;0,600;1,500&family=Inter:wght@300;400;500;600&display=swap');

            :root {
                --white: #F1EEE4;
                --cream: #E8E4D6;
                --mist: #E1E7DC;
                --oak-900: #1E2E22;
                --oak-700: #2F4A38;
                --oak-600: #3E6249;
                --oak-500: #4F7058;
                --oak-400: #6B8F73;
                --oak-300: #8FAB93;
                --oak-100: #DCE6DE;
                --ink: #1C2420;
            }

            .stApp {
                background: linear-gradient(180deg, var(--white) 0%, var(--cream) 100%);
            }
            header[data-testid="stHeader"] { background: transparent; }

            html, body, [class*="css"] { font-family: 'Inter', sans-serif; color: var(--ink); }
            .block-container { padding-top: 2rem; max-width: 1200px; }

            /* ---------------- SIDEBAR ---------------- */
            section[data-testid="stSidebar"] {
                background: linear-gradient(180deg, var(--mist) 0%, var(--white) 100%);
                border-right: 1px solid rgba(47, 74, 56, 0.2);
            }
            /* Texto normal da sidebar (labels, parágrafos, legendas, markdown) — NÃO usar
               seletor universal aqui: isso também apanharia o texto dos botões e forçaria
               texto escuro sobre botões de fundo verde escuro, tornando-os ilegíveis. */
            section[data-testid="stSidebar"] label,
            section[data-testid="stSidebar"] p,
            section[data-testid="stSidebar"] span,
            section[data-testid="stSidebar"] .stMarkdown,
            section[data-testid="stSidebar"] .stCaptionContainer,
            section[data-testid="stSidebar"] div[data-testid="stCaptionContainer"],
            section[data-testid="stSidebar"] div[data-testid="stWidgetLabel"] {
                color: var(--ink) !important;
            }
            section[data-testid="stSidebar"] h1,
            section[data-testid="stSidebar"] h2,
            section[data-testid="stSidebar"] h3 {
                font-family: 'Playfair Display', serif;
                color: var(--oak-700) !important;
            }
            /* Botões dentro da sidebar mantêm texto branco sobre o fundo verde escuro.
               IMPORTANTE: inclui também os elementos filhos (button *) com o mesmo
               prefixo da sidebar, para ter mais especificidade do que a regra
               "section[...] p/span" acima — sem isto, o texto do botão (que o
               Streamlit envolve num <p> ou <div> interno) ficava escuro na mesma. */
            section[data-testid="stSidebar"] .stButton button,
            section[data-testid="stSidebar"] .stButton button *,
            section[data-testid="stSidebar"] .stDownloadButton button,
            section[data-testid="stSidebar"] .stDownloadButton button * {
                color: var(--white) !important;
            }
            /* Ícone/botão de calendário do date_input — mesmo tratamento, caso o
               Streamlit o renderize como botão clicável em vez de simples ícone. */
            section[data-testid="stSidebar"] .stDateInput button,
            section[data-testid="stSidebar"] .stDateInput button *,
            .stDateInput button,
            .stDateInput button * {
                color: var(--white) !important;
            }
            .stDateInput svg {
                fill: var(--oak-700) !important;
            }

            /* Texto geral (fora da sidebar) */
            h1, h2, h3 { color: var(--oak-900); font-family: 'Playfair Display', serif; }
            p, span, label, .stMarkdown { color: var(--ink); }

            /* ---------------- INPUTS ---------------- */
            .stTextInput input, .stNumberInput input, .stDateInput input,
            div[data-baseweb="select"] > div, div[data-baseweb="base-input"] {
                background-color: var(--white) !important;
                color: var(--ink) !important;
                border: 1px solid rgba(47, 74, 56, 0.35) !important;
            }
            .stTextInput label, .stNumberInput label, .stDateInput label,
            .stSelectbox label, .stSlider label { color: var(--oak-700) !important; }

            /* Texto das opções dentro do dropdown do selectbox/multiselect */
            div[data-baseweb="popover"] li,
            div[data-baseweb="menu"] li {
                color: var(--ink) !important;
                background-color: var(--white) !important;
            }

            /* Botões de incremento/decremento (+/-) do st.number_input — sem isto,
               os ícones herdavam uma cor clara pensada para fundo escuro e ficavam
               invisíveis sobre o novo fundo claro. */
            button[data-testid="stNumberInputStepUp"],
            button[data-testid="stNumberInputStepDown"] {
                background-color: var(--white) !important;
                border: 1px solid rgba(47, 74, 56, 0.35) !important;
            }
            button[data-testid="stNumberInputStepUp"] svg,
            button[data-testid="stNumberInputStepDown"] svg {
                fill: var(--oak-700) !important;
                color: var(--oak-700) !important;
            }

            /* Botão "x" de limpar texto nos campos de texto/select */
            div[data-baseweb="select"] svg {
                fill: var(--oak-700) !important;
            }

            /* ---------------- BOTÕES ---------------- */
            .stButton button, .stDownloadButton button {
                background: linear-gradient(135deg, var(--oak-900) 0%, var(--oak-700) 55%, var(--oak-500) 100%);
                color: var(--white) !important;
                border: 1px solid var(--oak-600);
                font-weight: 600;
                letter-spacing: 0.02em;
                transition: transform 0.15s ease, box-shadow 0.15s ease;
            }
            .stButton button:hover, .stDownloadButton button:hover {
                transform: translateY(-1px);
                box-shadow: 0 6px 16px rgba(47, 74, 56, 0.3);
                color: var(--white) !important;
            }
            .stButton button *, .stDownloadButton button * {
                color: var(--white) !important;
            }

            /* ---------------- CARTÕES DE MÉTRICAS ---------------- */
            div[data-testid="stMetric"] {
                background: linear-gradient(155deg, var(--white) 0%, var(--cream) 100%);
                border: 1px solid var(--oak-300);
                border-left: 3px solid var(--oak-600);
                border-radius: 12px;
                padding: 0.9rem 1rem;
            }
            div[data-testid="stMetricValue"] { color: var(--oak-900); }
            div[data-testid="stMetricLabel"] { color: var(--oak-500); }

            /* ---------------- TABELAS / DATAFRAMES ---------------- */
            div[data-testid="stDataFrame"], div[data-testid="stTable"] {
                border: 1px solid var(--oak-300);
                border-radius: 10px;
                overflow: hidden;
            }

            /* ---------------- EXPANDERS ---------------- */
            div[data-testid="stExpander"] {
                background: var(--mist);
                border: 1px solid var(--oak-300);
                border-radius: 10px;
            }
            /* Cabeçalho do expander (seta + texto) — o Streamlit assume por vezes
               um tema base escuro nestes componentes nativos e pinta-os a branco;
               força-se aqui a cor certa para o novo fundo claro. */
            div[data-testid="stExpander"] summary,
            div[data-testid="stExpander"] summary p,
            div[data-testid="stExpander"] summary span {
                color: var(--oak-700) !important;
            }
            div[data-testid="stExpander"] summary svg {
                fill: var(--oak-700) !important;
            }

            /* ---------------- RADIO / CHECKBOX / TOGGLE ---------------- */
            div[data-testid="stRadio"] label p,
            div[data-testid="stRadio"] label span,
            div[data-testid="stCheckbox"] label p,
            div[data-testid="stCheckbox"] label span,
            div[data-testid="stToggle"] label p,
            div[data-testid="stToggle"] label span {
                color: var(--ink) !important;
            }
            /* Contorno do círculo/caixa não selecionada do radio e checkbox */
            div[data-testid="stRadio"] label div:first-child,
            div[data-testid="stCheckbox"] label span:first-child {
                border-color: var(--oak-600) !important;
            }
            /* Texto dentro do "pill" selecionado do radio horizontal, quando o
               fundo fica colorido (verde) — garante contraste em ambos os casos */
            div[data-testid="stRadio"] label[data-checked="true"] p,
            div[data-testid="stRadio"] label[aria-checked="true"] p {
                color: var(--white) !important;
            }

            /* ---------------- SLIDER ---------------- */
            div[data-testid="stSlider"] div[data-testid="stTickBarMin"],
            div[data-testid="stSlider"] div[data-testid="stTickBarMax"],
            div[data-testid="stSlider"] label {
                color: var(--ink) !important;
            }
            div[data-testid="stSlider"] div[role="slider"] {
                background-color: var(--oak-700) !important;
            }

            /* ---------------- SELECTBOX / MULTISELECT ---------------- */
            div[data-baseweb="select"] svg {
                fill: var(--oak-700) !important;
            }
            /* Tags de itens selecionados no multiselect */
            div[data-baseweb="tag"] {
                background-color: var(--oak-700) !important;
            }
            div[data-baseweb="tag"] span,
            div[data-baseweb="tag"] svg {
                color: var(--white) !important;
                fill: var(--white) !important;
            }

            /* ---------------- ÍCONES DE AJUDA (tooltip "?") ---------------- */
            [data-testid="stTooltipIcon"] svg,
            [data-testid="stTooltipHoverTarget"] svg {
                fill: var(--oak-500) !important;
            }

            /* ---------------- TABS ---------------- */
            button[data-baseweb="tab"] { color: var(--oak-500); }
            button[data-baseweb="tab"][aria-selected="true"] { color: var(--oak-900); border-bottom-color: var(--oak-600); }

            /* ---------------- ALERTS (info / success / warning / error) ---------------- */
            div[data-testid="stAlert"] {
                background: var(--oak-100);
                border: 1px solid var(--oak-300);
                border-radius: 10px;
                color: var(--ink);
            }

            /* ---------------- PAGE HEADER (usado nas páginas internas) ---------------- */
            .page-header {
                display: flex;
                align-items: center;
                gap: 0.9rem;
                padding: 0.4rem 0 1rem 0;
                margin-bottom: 0.6rem;
                border-bottom: 1px solid var(--oak-300);
            }
            .page-header-icon {
                font-size: 2.1rem;
                filter: drop-shadow(0 0 6px rgba(47, 74, 56, 0.35));
            }
            .page-header-title {
                font-family: 'Playfair Display', serif;
                font-weight: 700;
                font-size: 1.9rem;
                background: linear-gradient(90deg, var(--oak-900) 0%, var(--oak-700) 55%, var(--oak-400) 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                line-height: 1.1;
            }
            .page-header-subtitle {
                font-family: 'Cormorant Garamond', serif;
                font-style: italic;
                color: var(--oak-500);
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
# Plotly — layout claro consistente com a marca
# ------------------------------------------------------------------------------
PLOTLY_COLORWAY = [OAK_700, OAK_400, OAK_300, "#6E8C9C", OAK_900, OAK_600]

PLOTLY_LAYOUT = dict(
    template="plotly_white",
    paper_bgcolor=WHITE,
    plot_bgcolor=CREAM,
    font=dict(color=INK, family="Inter, sans-serif"),
    colorway=PLOTLY_COLORWAY,
    xaxis=dict(
        gridcolor="rgba(47,74,56,0.14)", zerolinecolor="rgba(47,74,56,0.28)", linecolor="rgba(47,74,56,0.32)",
        title=dict(font=dict(color=OAK_900)), tickfont=dict(color=INK),
    ),
    yaxis=dict(
        gridcolor="rgba(47,74,56,0.14)", zerolinecolor="rgba(47,74,56,0.28)", linecolor="rgba(47,74,56,0.32)",
        title=dict(font=dict(color=OAK_900)), tickfont=dict(color=INK),
    ),
    legend=dict(
        bgcolor="rgba(241,238,228,0.9)", bordercolor="rgba(47,74,56,0.3)", borderwidth=1,
        font=dict(color=INK, family="Inter, sans-serif"),
    ),
    title=dict(font=dict(color=OAK_900)),
    hoverlabel=dict(bgcolor=WHITE, bordercolor=OAK_700, font=dict(color=INK, family="Inter, sans-serif")),
)


def style_plotly(fig):
    """Aplica o tema OAK & VALUE (branco quente + verde carvalho) a uma figura Plotly, sem alterar os dados."""
    fig.update_layout(**PLOTLY_LAYOUT)
    return fig


# ------------------------------------------------------------------------------
# Matplotlib — estilo claro consistente com a marca
# ------------------------------------------------------------------------------
def apply_mpl_dark_style():
    import matplotlib.pyplot as plt

    plt.rcParams.update(
        {
            "figure.facecolor": WHITE,
            "axes.facecolor": CREAM,
            "savefig.facecolor": WHITE,
            "axes.edgecolor": OAK_700,
            "axes.labelcolor": INK,
            "axes.titlecolor": OAK_900,
            "text.color": INK,
            "xtick.color": INK,
            "ytick.color": INK,
            "grid.color": OAK_100,
            "grid.alpha": 0.8,
            "legend.facecolor": WHITE,
            "legend.edgecolor": OAK_300,
            "legend.labelcolor": INK,
            "font.family": "sans-serif",
        }
    )
