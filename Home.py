import base64
from pathlib import Path

import streamlit as st

from theme import inject_theme

st.set_page_config(
    page_title="Luminara Capital | Hub de Aplicações",
    page_icon="✨",
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
# Estilo — paleta Luminara Capital (azul-marinho profundo + dourado)
# ----------------------------------------------------------------------------
st.markdown(
    """
    <style>
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
            filter: drop-shadow(0 0 22px rgba(212, 175, 55, 0.35));
        }

        .hero-title {
            font-family: 'Playfair Display', serif;
            font-weight: 700;
            font-size: 3rem;
            letter-spacing: 0.12em;
            margin: 0.2rem 0 0 0;
            background: linear-gradient(90deg, var(--gold-700) 0%, var(--gold-100) 45%, var(--gold-500) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .hero-subtitle {
            font-family: 'Cormorant Garamond', serif;
            font-style: italic;
            font-weight: 500;
            font-size: 1.35rem;
            color: var(--gold-300);
            letter-spacing: 0.35em;
            margin-top: 0.3rem;
            text-transform: uppercase;
        }

        .hero-divider {
            width: 90px;
            height: 1px;
            margin: 1.1rem auto 1.3rem auto;
            background: linear-gradient(90deg, transparent, var(--gold-500), transparent);
        }

        .hero-tagline {
            color: rgba(245, 245, 240, 0.72);
            font-size: 1.02rem;
            font-weight: 300;
            max-width: 620px;
            line-height: 1.65;
        }

        /* ---------------- SECTION LABEL ---------------- */
        .section-label {
            font-family: 'Playfair Display', serif;
            color: var(--ivory);
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
            background: var(--gold-500);
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
            background: linear-gradient(155deg, rgba(19, 26, 61, 0.85) 0%, rgba(10, 14, 39, 0.85) 100%);
            border: 1px solid rgba(212, 175, 55, 0.22);
            border-radius: 14px;
            padding: 1.3rem 1.4rem;
            transition: border-color 0.25s ease, transform 0.25s ease, box-shadow 0.25s ease;
            position: relative;
            overflow: hidden;
        }
        .app-card:hover {
            border-color: rgba(212, 175, 55, 0.75);
            transform: translateY(-3px);
            box-shadow: 0 10px 28px rgba(0, 0, 0, 0.35), 0 0 18px rgba(212, 175, 55, 0.12);
        }
        .app-card .app-icon {
            font-size: 1.5rem;
            margin-bottom: 0.5rem;
            display: inline-block;
        }
        .app-card .app-name {
            font-family: 'Playfair Display', serif;
            color: var(--gold-100);
            font-size: 1.05rem;
            font-weight: 600;
            margin-bottom: 0.25rem;
        }
        .app-card .app-desc {
            color: rgba(245, 245, 240, 0.6);
            font-size: 0.86rem;
            font-weight: 300;
            line-height: 1.4;
        }
        .app-card .badge-soon {
            display: inline-block;
            margin-top: 0.55rem;
            font-size: 0.68rem;
            letter-spacing: 0.06em;
            color: var(--navy-950);
            background: var(--gold-300);
            padding: 0.15rem 0.55rem;
            border-radius: 20px;
            font-weight: 600;
            text-transform: uppercase;
        }

        /* ---------------- CTA / INFO BOX ---------------- */
        .cta-box {
            border: 1px solid rgba(212, 175, 55, 0.35);
            background: rgba(212, 175, 55, 0.06);
            border-radius: 12px;
            padding: 0.95rem 1.3rem;
            color: var(--gold-100);
            font-size: 0.92rem;
            text-align: center;
            margin-top: 0.5rem;
        }

        /* ---------------- FOOTER ---------------- */
        .lux-footer {
            text-align: center;
            margin-top: 3rem;
            padding-top: 1.2rem;
            border-top: 1px solid rgba(212, 175, 55, 0.18);
            color: rgba(245, 245, 240, 0.4);
            font-size: 0.78rem;
            letter-spacing: 0.08em;
        }
        .lux-footer span {
            color: var(--gold-500);
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
        <div class="hero-title">LUMINARA CAPITAL</div>
        <div class="hero-subtitle">Hub de Aplicações</div>
        <div class="hero-divider"></div>
        <div class="hero-tagline">
            Um espaço centralizado para as ferramentas de análise e simulação financeira
            da Luminara Capital. Usa o menu na barra lateral para navegar entre aplicações,
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
            <div class="app-name">Simulador de Portefólio vs S&amp;P 500</div>
            <div class="app-desc">Compara a performance do teu portefólio com o índice S&amp;P 500.</div>
        </div>
        <div class="app-card">
            <div class="app-icon">🧮</div>
            <div class="app-name">App 2</div>
            <div class="app-desc">Substituir por título e descrição reais.</div>
            <div class="badge-soon">Em breve</div>
        </div>
        <div class="app-card">
            <div class="app-icon">🧮</div>
            <div class="app-name">App 3</div>
            <div class="app-desc">Substituir por título e descrição reais.</div>
            <div class="badge-soon">Em breve</div>
        </div>
        <div class="app-card">
            <div class="app-icon">🧮</div>
            <div class="app-name">App 4</div>
            <div class="app-desc">Substituir por título e descrição reais.</div>
            <div class="badge-soon">Em breve</div>
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
    """
    <div class="lux-footer">
        LUMINARA <span>CAPITAL</span> — Hub interno de aplicações
    </div>
    """,
    unsafe_allow_html=True,
)
