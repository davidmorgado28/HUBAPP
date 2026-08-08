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
    from theme import inject_theme, page_header, style_plotly
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

st.set_page_config(page_title="Simulador de Monte Carlo | Luminara Capital", page_icon="🎲", layout="wide")
inject_theme()
page_header("🎲", "Simulador de Monte Carlo", "Projeção probabilística da evolução da tua carteira")

GOLD = "#d4af37"
GOLD_LIGHT = "#f6e7c1"

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

    # ---- Fan chart (percentis ao longo do tempo) ----
    st.markdown("#### Evolução Projetada da Carteira")
    percentiles = [5, 25, 50, 75, 95]
    perc_paths = np.percentile(res["paths"], percentiles, axis=0)
    x_months = np.arange(0, n_months + 1)
    x_years = x_months / 12

    fig_fan = go.Figure()
    fig_fan.add_trace(go.Scatter(x=x_years, y=perc_paths[4], line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig_fan.add_trace(go.Scatter(
        x=x_years, y=perc_paths[0], fill="tonexty", fillcolor="rgba(212,175,55,0.10)",
        line=dict(width=0), name="Percentil 5–95%",
    ))
    fig_fan.add_trace(go.Scatter(x=x_years, y=perc_paths[3], line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig_fan.add_trace(go.Scatter(
        x=x_years, y=perc_paths[1], fill="tonexty", fillcolor="rgba(212,175,55,0.25)",
        line=dict(width=0), name="Percentil 25–75%",
    ))
    fig_fan.add_trace(go.Scatter(
        x=x_years, y=perc_paths[2], line=dict(color=GOLD, width=3), name="Mediana",
    ))
    fig_fan.update_xaxes(title="Anos")
    fig_fan.update_yaxes(title="Valor da Carteira (€)")
    fig_fan = style_plotly(fig_fan)
    st.plotly_chart(fig_fan, use_container_width=True)

    # ---- Histograma dos valores finais ----
    hist_col, dd_col = st.columns(2)

    with hist_col:
        st.markdown("#### Distribuição do Valor Final")
        fig_hist = go.Figure()
        fig_hist.add_trace(go.Histogram(x=final_values, nbinsx=60, marker_color=GOLD, name="Valor Final"))
        fig_hist.add_vline(x=total_invested, line_dash="dash", line_color=GOLD_LIGHT,
                            annotation_text="Total Investido")
        fig_hist.add_vline(x=median_value, line_dash="dot", line_color="white",
                            annotation_text="Mediana")
        fig_hist.update_xaxes(title="Valor Final (€)")
        fig_hist.update_yaxes(title="Frequência")
        fig_hist = style_plotly(fig_hist)
        st.plotly_chart(fig_hist, use_container_width=True)

    with dd_col:
        st.markdown("#### Distribuição do Máximo Drawdown")
        fig_dd = go.Figure()
        fig_dd.add_trace(go.Histogram(x=drawdowns * 100, nbinsx=60, marker_color="#8c7024", name="Max Drawdown"))
        fig_dd.update_xaxes(title="Máximo Drawdown (%)")
        fig_dd.update_yaxes(title="Frequência")
        fig_dd = style_plotly(fig_dd)
        st.plotly_chart(fig_dd, use_container_width=True)

    # ---- Alocação ----
    st.markdown("#### Alocação da Carteira Simulada")
    fig_pie = go.Figure(data=[go.Pie(
        labels=res["valid_tickers"], values=res["valid_weights"],
        hole=0.5, marker=dict(colors=["#d4af37", "#f6e7c1", "#8c7024", "#e8d9a0", "#b8974a", "#c9a961"]),
    )])
    fig_pie = style_plotly(fig_pie)
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
