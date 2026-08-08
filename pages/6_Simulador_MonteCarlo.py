"""
Luminara Capital — Simulador de Monte Carlo
--------------------------------------------
Página adicional para o hub Streamlit. Permite ao utilizador definir uma
carteira (tickers + pesos), um plano de investimento (montante inicial +
aporte mensal) e um horizonte temporal, e correr uma simulação de Monte
Carlo (bootstrap histórico ou distribuição normal) para projetar a
evolução do valor da carteira.

Coloca este ficheiro na pasta `pages/` do teu projeto. Renomeia o prefixo
numérico (6_) conforme a ordem que quiseres no menu lateral.

NOTA sobre o theme.py: não tenho acesso ao teu módulo `theme.py` nesta
conversa, por isso o import abaixo tem um fallback seguro. Se as tuas
funções tiverem nomes diferentes (ex: `inject_css`, `render_header`),
ajusta o bloco de import para bater certo com o teu módulo real — cola-mo
aqui que eu alinho tudo.
"""

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go

# ----------------------------------------------------------------------
# Tema partilhado (com fallback caso os nomes não coincidam exatamente)
# ----------------------------------------------------------------------
try:
    from theme import (
        inject_theme, page_header, style_plotly,
        NAVY_950, NAVY_900, NAVY_800, NAVY_700,
        GOLD_100, GOLD_300, GOLD_500, GOLD_700, IVORY,
    )
except ImportError:
    def inject_theme():
        pass

    def page_header(icon, title, subtitle=""):
        st.title(f"{icon} {title}")
        if subtitle:
            st.caption(subtitle)

    def style_plotly(fig):
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter, sans-serif", color="#f6e7c1"),
            colorway=["#d4af37", "#f6e7c1", "#8c7024", "#e8d9a0"],
        )
        return fig

    NAVY_950, NAVY_900, NAVY_800, NAVY_700 = "#05070f", "#0a0e27", "#0d1230", "#131a3d"
    GOLD_100, GOLD_300, GOLD_500, GOLD_700 = "#f6e7c1", "#e8c874", "#d4af37", "#b8912e"
    IVORY = "#f5f5f0"

st.set_page_config(page_title="Simulador de Monte Carlo | Luminara Capital", page_icon="🎲", layout="wide")
inject_theme()
page_header("🎲", "Simulador de Monte Carlo", "Projeção probabilística da evolução da tua carteira")

GOLD = GOLD_500
GOLD_LIGHT = GOLD_100

# ----------------------------------------------------------------------
# Estado inicial
# ----------------------------------------------------------------------
if "mc_portfolio" not in st.session_state:
    st.session_state.mc_portfolio = pd.DataFrame(
        {"Ticker": ["AAPL", "MSFT", "SPY"], "Peso (%)": [40.0, 30.0, 30.0]}
    )

if "mc_results" not in st.session_state:
    st.session_state.mc_results = None


# ----------------------------------------------------------------------
# Funções auxiliares
# ----------------------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_monthly_returns(tickers: tuple, period: str = "10y") -> pd.DataFrame:
    """Descarrega preços mensais ajustados e devolve retornos mensais por ativo."""
    data = yf.download(list(tickers), period=period, interval="1mo", progress=False, auto_adjust=True)

    if data.empty:
        return pd.DataFrame()

    if len(tickers) == 1:
        prices = data["Close"].to_frame(name=tickers[0])
    else:
        prices = data["Close"]

    prices = prices.dropna(how="all")
    returns = prices.pct_change().dropna(how="all")
    return returns


def run_monte_carlo(
    portfolio_returns: np.ndarray,
    initial_investment: float,
    monthly_investment: float,
    n_months: int,
    n_simulations: int,
    method: str,
) -> np.ndarray:
    """Simula n_simulations trajetórias mensais do valor da carteira."""
    mean_r = portfolio_returns.mean()
    std_r = portfolio_returns.std()

    paths = np.zeros((n_simulations, n_months + 1))
    paths[:, 0] = initial_investment

    for t in range(1, n_months + 1):
        if method == "Histórico (Bootstrap)":
            sampled = np.random.choice(portfolio_returns, size=n_simulations, replace=True)
        else:
            sampled = np.random.normal(mean_r, std_r, size=n_simulations)
        paths[:, t] = paths[:, t - 1] * (1 + sampled) + monthly_investment

    return paths


def max_drawdown_per_path(paths: np.ndarray) -> np.ndarray:
    running_max = np.maximum.accumulate(paths, axis=1)
    drawdowns = (paths - running_max) / running_max
    return drawdowns.min(axis=1)


# ----------------------------------------------------------------------
# 1. Composição da carteira
# ----------------------------------------------------------------------
st.subheader("1. Composição da Carteira")

edited_df = st.data_editor(
    st.session_state.mc_portfolio,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Ticker": st.column_config.TextColumn("Ticker", help="Símbolo do ativo, ex: AAPL, VWCE.DE"),
        "Peso (%)": st.column_config.NumberColumn("Peso (%)", min_value=0.0, max_value=100.0, step=1.0, format="%.1f"),
    },
    key="mc_portfolio_editor",
)
st.session_state.mc_portfolio = edited_df

clean_df = edited_df.dropna(subset=["Ticker"])
clean_df = clean_df[clean_df["Ticker"].str.strip() != ""]
total_weight = clean_df["Peso (%)"].fillna(0).sum()

weight_col1, weight_col2 = st.columns([3, 1])
with weight_col1:
    if abs(total_weight - 100) > 0.01:
        st.warning(f"⚠️ A soma dos pesos é {total_weight:.1f}%. Idealmente deve somar 100% (será normalizado automaticamente).")
    else:
        st.success("✅ Pesos somam 100%.")

# ----------------------------------------------------------------------
# 2. Parâmetros do investimento
# ----------------------------------------------------------------------
st.subheader("2. Parâmetros do Investimento")

col1, col2, col3, col4 = st.columns(4)
with col1:
    initial_investment = st.number_input("Montante Inicial (€)", min_value=0.0, value=10000.0, step=500.0)
with col2:
    monthly_investment = st.number_input("Aporte Mensal (€)", min_value=0.0, value=250.0, step=50.0)
with col3:
    horizon_years = st.selectbox("Horizonte Temporal (anos)", [1, 5, 10, 15, 20], index=2)
with col4:
    n_simulations = st.number_input("Nº de Simulações", min_value=100, max_value=20000, value=3000, step=500)

method = st.radio(
    "Método de amostragem dos retornos",
    ["Histórico (Bootstrap)", "Distribuição Normal"],
    horizontal=True,
    help="Bootstrap reamostra retornos mensais reais (captura melhor caudas gordas). Normal assume retornos gaussianos.",
)

run_button = st.button("🚀 Executar Simulação", type="primary", use_container_width=True)

# ----------------------------------------------------------------------
# 3. Execução da simulação
# ----------------------------------------------------------------------
if run_button:
    tickers = tuple(clean_df["Ticker"].str.strip().str.upper().tolist())

    if len(tickers) == 0:
        st.error("Adiciona pelo menos um ativo à tabela.")
    elif total_weight == 0:
        st.error("Os pesos não podem ser todos zero.")
    else:
        weights = clean_df["Peso (%)"].fillna(0).to_numpy()
        weights = weights / weights.sum()  # normaliza para somar 1

        with st.spinner("A obter dados históricos..."):
            returns_df = fetch_monthly_returns(tickers)

        if returns_df.empty:
            st.error("Não foi possível obter dados para os tickers indicados. Verifica os símbolos.")
        else:
            missing = [t for t in tickers if t not in returns_df.columns]
            if missing:
                st.warning(f"Sem dados para: {', '.join(missing)}. Serão ignorados e os pesos redistribuídos.")

            valid_tickers = [t for t in tickers if t in returns_df.columns]
            valid_weights = np.array([w for t, w in zip(tickers, weights) if t in returns_df.columns])
            valid_weights = valid_weights / valid_weights.sum()

            returns_df = returns_df[valid_tickers].dropna()
            portfolio_returns = (returns_df * valid_weights).sum(axis=1).to_numpy()

            n_months = int(horizon_years * 12)

            with st.spinner(f"A correr {n_simulations:,} simulações..."):
                paths = run_monte_carlo(
                    portfolio_returns, initial_investment, monthly_investment,
                    n_months, int(n_simulations), method,
                )

            total_invested = initial_investment + monthly_investment * n_months
            final_values = paths[:, -1]
            drawdowns = max_drawdown_per_path(paths)

            st.session_state.mc_results = {
                "paths": paths,
                "final_values": final_values,
                "drawdowns": drawdowns,
                "total_invested": total_invested,
                "n_months": n_months,
                "horizon_years": horizon_years,
                "mean_r": portfolio_returns.mean(),
                "std_r": portfolio_returns.std(),
                "valid_tickers": valid_tickers,
                "valid_weights": valid_weights,
            }

# ----------------------------------------------------------------------
# Helpers de formatação e exportação HTML
# ----------------------------------------------------------------------
def fmt_eur(v: float) -> str:
    return f"€{v:,.0f}"


HOVERLABEL_STYLE = dict(
    bgcolor=NAVY_700,
    bordercolor=GOLD,
    font=dict(color=GOLD_LIGHT, family="Inter, sans-serif", size=13),
)


def build_html_report(res, metrics, params, figs) -> str:
    import datetime as _dt

    fan_div = figs["fan"].to_html(full_html=False, include_plotlyjs=False, config={"displayModeBar": False})
    hist_div = figs["hist"].to_html(full_html=False, include_plotlyjs=False, config={"displayModeBar": False})
    dd_div = figs["dd"].to_html(full_html=False, include_plotlyjs=False, config={"displayModeBar": False})
    pie_div = figs["pie"].to_html(full_html=False, include_plotlyjs=False, config={"displayModeBar": False})

    timestamp = _dt.datetime.now().strftime("%d/%m/%Y %H:%M")

    metric_cards = "".join(
        f"""<div class="metric">
                <div class="metric-label">{label}</div>
                <div class="metric-value">{value}</div>
            </div>"""
        for label, value in metrics
    )

    portfolio_rows = "".join(
        f"<tr><td>{t}</td><td>{w*100:.1f}%</td></tr>"
        for t, w in zip(res["valid_tickers"], res["valid_weights"])
    )

    return f"""<!DOCTYPE html>
<html lang="pt">
<head>
<meta charset="UTF-8">
<title>Relatório — Simulador de Monte Carlo | Luminara Capital</title>
<script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
<style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Inter:wght@400;500;600&display=swap');
    body {{
        margin: 0; padding: 2.5rem 1.5rem;
        background: radial-gradient(circle at 20% 0%, #0e1338 0%, {NAVY_900} 45%, {NAVY_950} 100%);
        font-family: 'Inter', sans-serif; color: {IVORY};
    }}
    .wrap {{ max-width: 1100px; margin: 0 auto; }}
    h1 {{
        font-family: 'Playfair Display', serif;
        background: linear-gradient(90deg, {GOLD_700} 0%, {GOLD_100} 45%, {GOLD_500} 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
        font-size: 2rem; margin-bottom: 0.1rem;
    }}
    h2 {{ font-family: 'Playfair Display', serif; color: {GOLD_100}; border-bottom: 1px solid rgba(212,175,55,0.25); padding-bottom: 0.4rem; margin-top: 2.2rem; }}
    .subtitle {{ color: rgba(245,245,240,0.65); margin-bottom: 1.8rem; }}
    .params {{ display: flex; flex-wrap: wrap; gap: 0.6rem; margin-bottom: 1rem; }}
    .params span {{
        background: rgba(212,175,55,0.08); border: 1px solid rgba(212,175,55,0.3);
        border-radius: 8px; padding: 0.35rem 0.7rem; font-size: 0.88rem; color: {GOLD_100};
    }}
    table {{ border-collapse: collapse; width: 100%; max-width: 420px; margin-bottom: 1rem; }}
    th, td {{ text-align: left; padding: 0.4rem 0.7rem; border-bottom: 1px solid rgba(212,175,55,0.18); font-size: 0.9rem; }}
    th {{ color: {GOLD_300}; font-weight: 600; }}
    .metrics-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.8rem; margin: 1rem 0 2rem 0; }}
    .metric {{
        background: linear-gradient(155deg, rgba(19,26,61,0.85) 0%, rgba(10,14,39,0.85) 100%);
        border: 1px solid rgba(212,175,55,0.22); border-radius: 12px; padding: 0.9rem 1rem;
    }}
    .metric-label {{ font-size: 0.78rem; color: rgba(245,245,240,0.6); margin-bottom: 0.3rem; }}
    .metric-value {{ font-size: 1.25rem; color: {GOLD_100}; font-weight: 600; }}
    .chart-box {{
        background: rgba(19,26,61,0.35); border: 1px solid rgba(212,175,55,0.18);
        border-radius: 12px; padding: 0.8rem; margin-bottom: 1.6rem;
    }}
    .notes {{ font-size: 0.88rem; color: rgba(245,245,240,0.75); line-height: 1.6; }}
    .notes li {{ margin-bottom: 0.35rem; }}
    footer {{ margin-top: 2.5rem; font-size: 0.78rem; color: rgba(245,245,240,0.45); text-align: center; }}
    @media (max-width: 700px) {{ .metrics-grid {{ grid-template-columns: repeat(2, 1fr); }} }}
</style>
</head>
<body>
<div class="wrap">
    <h1>🎲 Relatório — Simulador de Monte Carlo</h1>
    <div class="subtitle">Luminara Capital &middot; gerado em {timestamp}</div>

    <div class="params">
        <span>Montante inicial: {fmt_eur(params['initial_investment'])}</span>
        <span>Aporte mensal: {fmt_eur(params['monthly_investment'])}</span>
        <span>Horizonte: {params['horizon_years']} anos</span>
        <span>Simulações: {params['n_simulations']:,}</span>
        <span>Método: {params['method']}</span>
    </div>

    <table>
        <tr><th>Ticker</th><th>Peso</th></tr>
        {portfolio_rows}
    </table>

    <h2>Resultados</h2>
    <div class="metrics-grid">{metric_cards}</div>

    <h2>Evolução Projetada da Carteira</h2>
    <div class="chart-box">{fan_div}</div>

    <h2>Distribuição do Valor Final</h2>
    <div class="chart-box">{hist_div}</div>

    <h2>Distribuição do Máximo Drawdown</h2>
    <div class="chart-box">{dd_div}</div>

    <h2>Alocação da Carteira</h2>
    <div class="chart-box">{pie_div}</div>

    <h2>Notas Metodológicas</h2>
    <ul class="notes">
        <li>Retornos mensais históricos (até ~10 anos, ou período disponível) foram combinados pelos pesos da carteira.</li>
        <li>Método de amostragem: {params['method']}.</li>
        <li>Cada simulação aplica um retorno mensal amostrado, seguido do aporte mensal, ao longo de {params['n_months']} meses.</li>
        <li>O máximo drawdown é calculado por trajetória individual (pico a vale), depois agregado por média e percentil 5% (pior caso).</li>
        <li>Esta simulação é apenas educativa e não constitui aconselhamento de investimento. Rentabilidade passada não garante rentabilidade futura.</li>
    </ul>

    <footer>Luminara Capital — Relatório gerado automaticamente pelo Simulador de Monte Carlo</footer>
</div>
</body>
</html>"""


# ----------------------------------------------------------------------
# 4. Relatório e gráficos
# ----------------------------------------------------------------------
res = st.session_state.mc_results

if res is not None:
    st.divider()
    st.subheader("3. Relatório da Simulação")

    final_values = res["final_values"]
    total_invested = res["total_invested"]
    drawdowns = res["drawdowns"]
    n_months = res["n_months"]

    expected_value = np.mean(final_values)
    median_value = np.median(final_values)
    std_value = np.std(final_values)
    prob_loss = np.mean(final_values < total_invested) * 100
    annualized_return = (1 + res["mean_r"]) ** 12 - 1
    annualized_vol = res["std_r"] * np.sqrt(12)
    avg_max_dd = np.mean(drawdowns) * 100
    worst_max_dd = np.percentile(drawdowns, 5) * 100
    p5, p95 = np.percentile(final_values, [5, 95])

    k1, k2, k3, k4 = st.columns(4)
    k1.metric(
        "Valor Esperado Final", f"€{expected_value:,.0f}", f"vs €{total_invested:,.0f} investido",
        help="Média do valor final da carteira em todas as simulações. É o resultado 'típico' esperado, "
             "mas cada simulação individual pode terminar bem acima ou abaixo deste número.",
    )
    k2.metric(
        "Retorno Anualizado (histórico)", f"{annualized_return*100:.2f}%",
        help="Quanto a carteira rendeu, em média, por ano, com base no histórico de preços usado na simulação. "
             "Não garante retornos futuros iguais.",
    )
    k3.metric(
        "Volatilidade Anualizada", f"{annualized_vol*100:.2f}%",
        help="Mede o quanto o valor da carteira costuma oscilar (para cima e para baixo) ao longo de um ano. "
             "Quanto maior, mais 'aos saltos' costuma ser o percurso.",
    )
    k4.metric(
        "Probabilidade de Perda", f"{prob_loss:.1f}%",
        help="Percentagem das simulações em que, no final do horizonte definido, o valor da carteira ficou "
             "abaixo do total que investiste (inicial + todos os aportes mensais).",
    )

    k5, k6, k7, k8 = st.columns(4)
    k5.metric(
        "Mediana Valor Final", f"€{median_value:,.0f}",
        help="O valor 'do meio': metade das simulações terminou acima deste valor, metade abaixo. "
             "Costuma ser uma leitura mais realista do que a média quando há cenários muito extremos.",
    )
    k6.metric(
        "Desvio-Padrão (Valor Final)", f"€{std_value:,.0f}",
        help="Mede o quanto os resultados finais das várias simulações variam entre si. Quanto maior este "
             "número, mais incerto e imprevisível é o resultado final da carteira.",
    )
    k7.metric(
        "Máx. Drawdown Médio", f"{avg_max_dd:.1f}%",
        help="Em cada simulação, é a maior queda (do pico até ao vale) que a carteira sofreu a certo ponto do "
             "percurso, mesmo que depois tenha recuperado. Este valor é a média dessa queda em todas as simulações.",
    )
    k8.metric(
        "Máx. Drawdown (pior 5%)", f"{worst_max_dd:.1f}%",
        help="Olhando só para os 5% cenários mais dolorosos, esta foi a queda temporária mais profunda que a "
             "carteira sofreu. Dá uma ideia de 'quão mau pode ser o pior caso', não só o caso típico.",
    )

    st.caption(f"Intervalo de confiança 90% do valor final: €{p5:,.0f} — €{p95:,.0f}")

    # ======================================================================
    # Construção dos gráficos (feita antes de os mostrar, para poderem
    # também ser embutidos no relatório HTML exportável)
    # ======================================================================
    percentiles = [5, 25, 50, 75, 95]
    perc_paths = np.percentile(res["paths"], percentiles, axis=0)
    x_months = np.arange(0, n_months + 1)
    x_years = x_months / 12
    dtick = 1 if horizon_years <= 5 else (2 if horizon_years <= 10 else 5)
    total_invested_line = initial_investment + x_months * monthly_investment

    # ---- Fan chart (percentis ao longo do tempo) -------------------------
    fig_fan = go.Figure()

    fig_fan.add_trace(go.Scatter(
        x=x_years, y=perc_paths[4], name="P95 (otimista)",
        line=dict(width=0), hovertemplate="P95: €%{y:,.0f}<extra></extra>",
    ))
    fig_fan.add_trace(go.Scatter(
        x=x_years, y=perc_paths[3], name="P75",
        line=dict(width=0), fill="tonexty", fillcolor="rgba(212,175,55,0.12)",
        hovertemplate="P75: €%{y:,.0f}<extra></extra>",
    ))
    fig_fan.add_trace(go.Scatter(
        x=x_years, y=perc_paths[2], name="Mediana (P50)",
        line=dict(color=GOLD, width=3), fill="tonexty", fillcolor="rgba(212,175,55,0.22)",
        hovertemplate="Mediana: €%{y:,.0f}<extra></extra>",
    ))
    fig_fan.add_trace(go.Scatter(
        x=x_years, y=perc_paths[1], name="P25",
        line=dict(width=0), fill="tonexty", fillcolor="rgba(212,175,55,0.22)",
        hovertemplate="P25: €%{y:,.0f}<extra></extra>",
    ))
    fig_fan.add_trace(go.Scatter(
        x=x_years, y=perc_paths[0], name="P5 (pessimista)",
        line=dict(width=0), fill="tonexty", fillcolor="rgba(212,175,55,0.12)",
        hovertemplate="P5: €%{y:,.0f}<extra></extra>",
    ))
    fig_fan.add_trace(go.Scatter(
        x=x_years, y=total_invested_line, name="Capital investido (sem crescimento)",
        line=dict(color="rgba(245,245,240,0.55)", width=2, dash="dash"),
        hovertemplate="Capital investido: €%{y:,.0f}<extra></extra>",
    ))

    fig_fan.update_layout(
        hovermode="x unified",
        hoverlabel=HOVERLABEL_STYLE,
        height=460,
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    )
    fig_fan.update_xaxes(title="Horizonte (anos)", dtick=dtick)
    fig_fan.update_yaxes(title="Valor da Carteira (€)", tickprefix="€", tickformat=",.0f")
    fig_fan = style_plotly(fig_fan)

    # ---- Histograma dos valores finais ------------------------------------
    n_bins = int(np.clip(n_simulations // 40, 30, 80))

    fig_hist = go.Figure()
    fig_hist.add_trace(go.Histogram(
        x=final_values, nbinsx=n_bins, histnorm="percent",
        marker=dict(color=GOLD, line=dict(color=NAVY_800, width=0.5)),
        name="Valor Final",
        hovertemplate="≈ €%{x:,.0f}<br>%{y:.1f}% das simulações<extra></extra>",
    ))
    fig_hist.add_vline(x=total_invested, line_dash="dash", line_color=GOLD_LIGHT,
                        annotation_text="Capital investido", annotation_position="top right")
    fig_hist.add_vline(x=median_value, line_dash="dot", line_color="white",
                        annotation_text="Mediana", annotation_position="top left")
    fig_hist.add_vline(x=p5, line_dash="dot", line_color="#E8927C",
                        annotation_text="P5", annotation_position="bottom left")
    fig_hist.add_vline(x=p95, line_dash="dot", line_color="#7FD9A8",
                        annotation_text="P95", annotation_position="bottom right")
    fig_hist.update_layout(hoverlabel=HOVERLABEL_STYLE, height=420, margin=dict(l=10, r=10, t=10, b=10), bargap=0.03)
    fig_hist.update_xaxes(title="Valor Final (€)", tickprefix="€", tickformat=",.0f")
    fig_hist.update_yaxes(title="% das simulações")
    fig_hist = style_plotly(fig_hist)

    # ---- Histograma do máximo drawdown ------------------------------------
    fig_dd = go.Figure()
    fig_dd.add_trace(go.Histogram(
        x=drawdowns * 100, nbinsx=n_bins, histnorm="percent",
        marker=dict(color="#8c7024", line=dict(color=NAVY_800, width=0.5)),
        name="Máx. Drawdown",
        hovertemplate="≈ %{x:.1f}%<br>%{y:.1f}% das simulações<extra></extra>",
    ))
    fig_dd.add_vline(x=avg_max_dd, line_dash="dash", line_color=GOLD_LIGHT,
                      annotation_text="Média", annotation_position="top right")
    fig_dd.add_vline(x=worst_max_dd, line_dash="dot", line_color="#E8927C",
                      annotation_text="Pior 5%", annotation_position="top left")
    fig_dd.update_layout(hoverlabel=HOVERLABEL_STYLE, height=420, margin=dict(l=10, r=10, t=10, b=10), bargap=0.03)
    fig_dd.update_xaxes(title="Máximo Drawdown (%)", ticksuffix="%")
    fig_dd.update_yaxes(title="% das simulações")
    fig_dd = style_plotly(fig_dd)

    # ---- Alocação -----------------------------------------------------------
    fig_pie = go.Figure(data=[go.Pie(
        labels=res["valid_tickers"], values=res["valid_weights"],
        hole=0.5, marker=dict(colors=["#d4af37", "#f6e7c1", "#8c7024", "#e8d9a0", "#b8974a", "#c9a961"]),
        hovertemplate="%{label}<br>%{percent}<extra></extra>",
    )])
    fig_pie.update_layout(hoverlabel=HOVERLABEL_STYLE, height=380, margin=dict(l=10, r=10, t=10, b=10))
    fig_pie = style_plotly(fig_pie)

    # ======================================================================
    # Botão de download do relatório em HTML
    # ======================================================================
    html_metrics = [
        ("Valor Esperado Final", fmt_eur(expected_value)),
        ("Retorno Anualizado", f"{annualized_return*100:.2f}%"),
        ("Volatilidade Anualizada", f"{annualized_vol*100:.2f}%"),
        ("Probabilidade de Perda", f"{prob_loss:.1f}%"),
        ("Mediana Valor Final", fmt_eur(median_value)),
        ("Desvio-Padrão (Valor Final)", fmt_eur(std_value)),
        ("Máx. Drawdown Médio", f"{avg_max_dd:.1f}%"),
        ("Máx. Drawdown (pior 5%)", f"{worst_max_dd:.1f}%"),
    ]
    html_report = build_html_report(
        res=res,
        metrics=html_metrics,
        params={
            "initial_investment": initial_investment,
            "monthly_investment": monthly_investment,
            "horizon_years": horizon_years,
            "n_simulations": int(n_simulations),
            "method": method,
            "n_months": n_months,
        },
        figs={"fan": fig_fan, "hist": fig_hist, "dd": fig_dd, "pie": fig_pie},
    )

    st.download_button(
        "📥 Descarregar Relatório em HTML",
        data=html_report,
        file_name="relatorio_monte_carlo_luminara.html",
        mime="text/html",
        use_container_width=True,
    )

    # ======================================================================
    # Exibição dos gráficos
    # ======================================================================
    st.markdown("#### Evolução Projetada da Carteira")
    st.caption("Passa o cursor sobre o gráfico para ver os valores de cada percentil em qualquer ano.")
    st.plotly_chart(fig_fan, use_container_width=True)

    hist_col, dd_col = st.columns(2)
    with hist_col:
        st.markdown("#### Distribuição do Valor Final")
        st.caption("Cada barra mostra a % de simulações que terminaram naquele intervalo de valores.")
        st.plotly_chart(fig_hist, use_container_width=True)

    with dd_col:
        st.markdown("#### Distribuição do Máximo Drawdown")
        st.caption("A pior queda temporária (pico a vale) registada em cada simulação.")
        st.plotly_chart(fig_dd, use_container_width=True)

    st.markdown("#### Alocação da Carteira Simulada")
    st.plotly_chart(fig_pie, use_container_width=True)

    with st.expander("ℹ️ Notas metodológicas"):
        st.markdown(f"""
        - Retornos mensais históricos (últimos ~10 anos, ou período disponível) foram combinados
          pelos pesos da carteira para formar uma série de retornos mensais da carteira.
        - Método de amostragem: **{method}**.
        - Cada simulação aplica um retorno mensal amostrado, seguido do aporte mensal, ao longo de
          **{n_months} meses** ({res['horizon_years']} anos).
        - Máximo drawdown é calculado por trajetória (pico a vale do valor acumulado), depois
          agregado por média e percentil 5% (pior caso).
        - Esta simulação é apenas educativa e não constitui aconselhamento de investimento.
          Rentabilidade passada não garante rentabilidade futura.
        """)
else:
    st.info("Preenche a carteira e os parâmetros acima e clica em **Executar Simulação** para gerar o relatório.")
