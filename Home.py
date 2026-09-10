import base64
from pathlib import Path

import streamlit as st

from theme import inject_theme, APP_NAME, PAGE_TITLE

st.set_page_config(
    page_title=f"{APP_NAME} | Hub de Aplicações",
    page_icon="🌳",
    layout="wide",
)

inject_theme()

# ----------------------------------------------------------------------------
# Logótipo (assets/logo.png, na mesma pasta deste ficheiro)
# ----------------------------------------------------------------------------
LOGO_PATH = Path(__file__).parent / "assets" / "logo.png"


def get_logo_base64() -> str:
    if LOGO_PATH.exists():
        return base64.b64encode(LOGO_PATH.read_bytes()).decode()
    return ""


logo_b64 = get_logo_base64()

# ----------------------------------------------------------------------------
# Estilo — paleta OAK & VALUE (branco quente + verde carvalho)
# ----------------------------------------------------------------------------
st.markdown(
    """
    <style>
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

        /* ---------------- HERO ---------------- */
        .hero-wrap {
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            padding: 1.5rem 0 2.5rem 0;
        }

        .hero-logo {
            width: 150px;
            margin-bottom: 0.5rem;
            filter: drop-shadow(0 0 18px rgba(47, 74, 56, 0.3));
        }

        .hero-title {
            font-family: 'Playfair Display', serif;
            font-weight: 700;
            font-size: 3rem;
            letter-spacing: 0.12em;
            margin: 0.2rem 0 0 0;
            background: linear-gradient(90deg, var(--oak-900) 0%, var(--oak-700) 55%, var(--oak-400) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .hero-subtitle {
            font-family: 'Cormorant Garamond', serif;
            font-style: italic;
            font-weight: 500;
            font-size: 1.35rem;
            color: var(--oak-700);
            letter-spacing: 0.35em;
            margin-top: 0.3rem;
            text-transform: uppercase;
        }

        .hero-divider {
            width: 90px;
            height: 1px;
            margin: 1.1rem auto 1.3rem auto;
            background: linear-gradient(90deg, transparent, var(--oak-600), transparent);
        }

        .hero-tagline {
            color: rgba(28, 36, 32, 0.72);
            font-size: 1.02rem;
            font-weight: 300;
            max-width: 620px;
            line-height: 1.65;
        }

        /* ---------------- SECTION LABEL ---------------- */
        .section-label {
            font-family: 'Playfair Display', serif;
            color: var(--oak-900);
            font-size: 1.3rem;
            font-weight: 600;
            letter-spacing: 0.04em;
            margin: 0.5rem 0 1.2rem 0;
            display: flex;
            align-items: center;
            gap: 0.6rem;
        }
        .section-label::before {
            content: "";
            width: 26px;
            height: 2px;
            background: var(--oak-600);
            display: inline-block;
        }

        /* ---------------- APP CARDS ---------------- */
        .app-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
            gap: 1rem;
            margin-bottom: 1.8rem;
        }

        .app-card {
            background: linear-gradient(155deg, var(--white) 0%, var(--cream) 100%);
            border: 1px solid var(--oak-300);
            border-radius: 14px;
            padding: 1.3rem 1.4rem;
            transition: border-color 0.25s ease, transform 0.25s ease, box-shadow 0.25s ease;
            position: relative;
            overflow: hidden;
        }
        .app-card:hover {
            border-color: var(--oak-600);
            transform: translateY(-3px);
            box-shadow: 0 10px 24px rgba(30, 46, 34, 0.14), 0 0 14px rgba(47, 74, 56, 0.18);
        }
        .app-card .app-icon {
            font-size: 1.5rem;
            margin-bottom: 0.5rem;
            display: inline-block;
        }
        .app-card .app-name {
            font-family: 'Playfair Display', serif;
            color: var(--oak-900);
            font-size: 1.05rem;
            font-weight: 600;
            margin-bottom: 0.25rem;
        }
        .app-card .app-desc {
            color: rgba(28, 36, 32, 0.62);
            font-size: 0.86rem;
            font-weight: 300;
            line-height: 1.4;
        }
        .app-card .badge-soon {
            display: inline-block;
            margin-top: 0.55rem;
            font-size: 0.68rem;
            letter-spacing: 0.06em;
            color: var(--oak-900);
            background: var(--oak-100);
            padding: 0.15rem 0.55rem;
            border-radius: 20px;
            font-weight: 600;
            text-transform: uppercase;
        }

        /* ---------------- CTA / INFO BOX ---------------- */
        .cta-box {
            border: 1px solid var(--oak-300);
            background: var(--oak-100);
            border-radius: 12px;
            padding: 0.95rem 1.3rem;
            color: var(--oak-900);
            font-size: 0.92rem;
            text-align: center;
            margin-top: 0.5rem;
        }

        /* ---------------- FOOTER ---------------- */
        .lux-footer {
            text-align: center;
            margin-top: 3rem;
            padding-top: 1.2rem;
            border-top: 1px solid var(--oak-100);
            color: rgba(28, 36, 32, 0.45);
            font-size: 0.78rem;
            letter-spacing: 0.08em;
        }
        .lux-footer span {
            color: var(--oak-600);
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------------
# Hero
# ----------------------------------------------------------------------------
logo_html = (
    f'<img src="data:image/png;base64,{logo_b64}" class="hero-logo" />'
    if logo_b64
    else ""
)

st.markdown(
    f"""
    <div class="hero-wrap">
        {logo_html}
        <div class="hero-title">OAK & VALUE</div>
        <div class="hero-subtitle">{APP_NAME}</div>
        <div class="hero-divider"></div>
        <div class="hero-tagline">
            Um espaço centralizado de ferramentas de análise e simulação financeira. 
            Usa o menu na barra lateral para navegar entre aplicações,
            cada uma a correr de forma independente.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------------
# Aplicações disponíveis
# ----------------------------------------------------------------------------
st.markdown('<div class="section-label">Aplicações disponíveis</div>', unsafe_allow_html=True)

st.markdown(
    """
    <div class="app-grid">
        <div class="app-card">
            <div class="app-icon">📊</div>
            <div class="app-name">Simulador de Portefólio vs Benchmark</div>
            <div class="app-desc">Compara a performance do teu portefólio com um Indice de referência, com investimento inicial + DCA mensal.</div>
        </div>
        <div class="app-card">
            <div class="app-icon">📈</div>
            <div class="app-name">Otimizador de Markowitz</div>
            <div class="app-desc">Otimiza os pesos do portefólio pela Fronteira de Eficiência (maximização do Índice de Sharpe).</div>
        </div>
        <div class="app-card">
            <div class="app-icon">💰</div>
            <div class="app-name">Modelo DCF</div>
            <div class="app-desc">Valuação por Discounted Cash Flow em 3 cenários, com WACC calculado dinamicamente.</div>
        </div>
        <div class="app-card">
            <div class="app-icon">📑</div>
            <div class="app-name">Dashboard de Rácios & Valuation</div>
            <div class="app-desc">Relatório de rácios financeiros: valuation, rentabilidade, alavancagem, liquidez e benchmark de pares.</div>
        </div>
        <div class="app-card">
            <div class="app-icon">🏢</div>
            <div class="app-name">Análise de REITs</div>
            <div class="app-desc">Análise financeira de REITs: FFO/AFFO, dividendos, alavancagem e comparação com concorrentes.</div>
             </div>
        <div class="app-card">
            <div class="app-icon">🏗️</div>
            <div class="app-name">Modelo DCF de REIT</div>
            <div class="app-desc">Valuação por Discounted Cash Flow adaptada a REITs, com projeção de FFO/AFFO, taxa de capitalização terminal e 3 cenários.</div>
        </div>
        <div class="app-card">
            <div class="app-icon">🎲</div>
            <div class="app-name">Simulador de Monte Carlo</div>
            <div class="app-desc">Projeta milhares de cenários futuros do teu portefólio (com aportes mensais) e devolve retorno esperado, risco, probabilidade de perda e drawdown.</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="cta-box">👈 Escolhe uma aplicação na barra lateral para começar.</div>',
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <div class="lux-footer">
        OAK <span>&amp; VALUE</span> — {APP_NAME} · Hub interno de aplicações
    </div>
    """,
    unsafe_allow_html=True,
)
