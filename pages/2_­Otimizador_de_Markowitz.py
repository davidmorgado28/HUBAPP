# ==============================================================================
# 📈 OTIMIZADOR DE MARKOWITZ — Aplicação Streamlit
# Convertido a partir do notebook original (Colab, ipywidgets) para uma página
# do hub Streamlit, com adição/remoção dinâmica de tickers através de uma
# tabela editável (st.data_editor).
# ==============================================================================

import warnings
warnings.filterwarnings("ignore")

import base64
import io

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf
import matplotlib.pyplot as plt
from scipy.optimize import minimize

st.set_page_config(
    page_title="Otimizador de Markowitz",
    page_icon="📈",
    layout="wide",
)

st.title("📈 Otimizador de Markowitz")
st.caption(
    "Otimiza os pesos de um portefólio pela Fronteira de Eficiência de Markowitz "
    "(maximização do Índice de Sharpe), com adição/remoção dinâmica de ativos."
)

TICKERS_INICIAIS = pd.DataFrame(
    [
        {"Ticker": "AAPL", "Peso": 0.20},
        {"Ticker": "MSFT", "Peso": 0.20},
        {"Ticker": "NVDA", "Peso": 0.20},
        {"Ticker": "JPM", "Peso": 0.15},
        {"Ticker": "GOOGL", "Peso": 0.15},
        {"Ticker": "AMZN", "Peso": 0.10},
    ]
)

# ------------------------------------------------------------------------------
# 1. INTERFACE — CONFIGURAÇÃO
# ------------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Configuração")
    periodo_analisado = st.selectbox("Período de Análise", ["1y", "2y", "3y", "5y", "10y"], index=3)
    min_weight_val = st.number_input(
        "Peso Mínimo por Ativo", min_value=0.0, max_value=1.0, value=0.02, step=0.01, format="%.2f"
    )
    max_weight_val = st.number_input(
        "Peso Máximo por Ativo", min_value=0.0, max_value=1.0, value=0.40, step=0.05, format="%.2f"
    )
    run_button = st.button("🚀 Calcular & Gerar Portefólio", type="primary", use_container_width=True)

st.subheader("Ativos e Pesos Desejados (Inicial)")
st.caption("Podes adicionar linhas (canto inferior da tabela) ou remover selecionando a linha e apagando.")
tickers_df = st.data_editor(
    TICKERS_INICIAIS,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Ticker": st.column_config.TextColumn("Ticker", required=True),
        "Peso": st.column_config.NumberColumn("Peso", min_value=0.0, step=0.01, format="%.2f", required=True),
    },
    key="tickers_editor",
)

# ------------------------------------------------------------------------------
# 2. LÓGICA DE PROCESSAMENTO
# ------------------------------------------------------------------------------
@st.cache_data(show_spinner=False, ttl=3600)
def fetch_close_prices(tickers_list, period):
    df = yf.download(tickers_list, period=period, progress=False, auto_adjust=True)
    if isinstance(df.columns, pd.MultiIndex):
        return df["Close"]
    elif "Close" in df.columns:
        return df["Close"]
    return df


@st.cache_data(show_spinner=False, ttl=3600)
def get_risk_free_rate():
    try:
        tnx_prices = fetch_close_prices("^TNX", "5d")
        tnx_last = (
            tnx_prices.iloc[:, 0].dropna().iloc[-1]
            if isinstance(tnx_prices, pd.DataFrame)
            else tnx_prices.dropna().iloc[-1]
        )
        tnx_val = float(tnx_last)
        return tnx_val / 1000.0 if tnx_val > 10 else (tnx_val / 100.0 if tnx_val > 1 else tnx_val)
    except Exception:
        return 0.045


@st.cache_data(show_spinner=False, ttl=3600)
def get_clean_dividend_yield(ticker):
    try:
        info = yf.Ticker(ticker).info
        dy = info.get("dividendYield")
        if dy is not None and dy > 0:
            return dy / 100.0 if dy > 0.15 else dy
        div_rate = info.get("trailingAnnualDividendRate", 0.0)
        price = info.get("currentPrice") or info.get("previousClose", 0.0)
        if div_rate and price and price > 0:
            return float(div_rate) / float(price)
    except Exception:
        pass
    return 0.0


def run_optimization(portfolio_config, periodo_analisado, min_weight_val, max_weight_val):
    num_assets = len(portfolio_config)
    if num_assets < 2:
        st.error("⚠️ Precisas de introduzir pelo menos 2 tickers válidos com peso maior que 0.")
        return

    if min_weight_val >= max_weight_val:
        st.error(f"⚠️ O peso mínimo ({min_weight_val:.1%}) não pode ser maior ou igual ao peso máximo ({max_weight_val:.1%}).")
        return
    if min_weight_val * num_assets > 1.0:
        st.error(f"⚠️ O peso mínimo de {min_weight_val:.1%} por ativo é muito elevado para {num_assets} ativos.")
        return
    if max_weight_val * num_assets < 1.0:
        st.error(f"⚠️ O peso máximo de {max_weight_val:.1%} por ativo é muito reduzido para {num_assets} ativos.")
        return

    benchmark_ticker = "^GSPC"

    with st.spinner("⚡ A descarregar dados de mercado e a calcular..."):
        risk_free_rate = get_risk_free_rate()

        tickers = list(portfolio_config.keys())
        raw_weights = np.array(list(portfolio_config.values()))
        initial_weights = raw_weights / np.sum(raw_weights)

        data = fetch_close_prices(tickers + [benchmark_ticker], periodo_analisado).dropna()

        missing_tickers = [t for t in tickers if t not in data.columns]
        if missing_tickers:
            st.error(f"⚠️ Não foi possível obter dados para os seguintes tickers: {', '.join(missing_tickers)}")
            return

        asset_prices = data[tickers]
        benchmark_prices = data[benchmark_ticker]

        asset_returns = asset_prices.pct_change().dropna()
        benchmark_returns = benchmark_prices.pct_change().dropna()

        dividend_yields_annual = np.array([get_clean_dividend_yield(t) for t in tickers])

        mean_daily_returns = asset_returns.mean()
        cov_matrix = asset_returns.cov()

        def portfolio_performance(w):
            ret_annual = np.sum(mean_daily_returns * w) * 252
            vol_annual = np.sqrt(np.dot(w.T, np.dot(cov_matrix * 252, w)))
            sharpe = (ret_annual - risk_free_rate) / vol_annual if vol_annual > 0 else 0
            return ret_annual, vol_annual, sharpe

        def negative_sharpe(w):
            return -portfolio_performance(w)[2]

        constraints = ({"type": "eq", "fun": lambda w: np.sum(w) - 1},)
        bounds = tuple((min_weight_val, max_weight_val) for _ in range(num_assets))

        adj_initial_weights = np.clip(initial_weights, min_weight_val, max_weight_val)
        adj_initial_weights /= np.sum(adj_initial_weights)

        opt_res = minimize(negative_sharpe, adj_initial_weights, method="SLSQP", bounds=bounds, constraints=constraints)
        opt_weights = opt_res.x

        def calculate_metrics(weights):
            ret_annual, vol_annual, sharpe = portfolio_performance(weights)
            port_daily_ret = (asset_returns * weights).sum(axis=1)
            ret_period = (1 + port_daily_ret).prod() - 1

            covariance = np.cov(port_daily_ret, benchmark_returns)[0][1]
            beta = covariance / np.var(benchmark_returns)
            weighted_dy_annual = np.sum(weights * dividend_yields_annual)

            return {
                "Retorno Anualizado": f"{ret_annual:.2%}",
                f"Retorno Acumulado ({periodo_analisado})": f"{ret_period:.2%}",
                "Desvio Padrão / Risco (Anualizado)": f"{vol_annual:.2%}",
                "Índice de Sharpe": f"{sharpe:.2f}",
                "Beta (vs S&P 500)": f"{beta:.2f}",
                "Dividend Yield (Anualizado)": f"{weighted_dy_annual:.2%}",
            }

        df_comparison = pd.DataFrame(
            [calculate_metrics(initial_weights), calculate_metrics(opt_weights)],
            index=["Portefólio Inicial", "Portefólio Otimizado (Max Sharpe)"],
        ).T

        sp500_ret_annual = benchmark_returns.mean() * 252
        sp500_vol_annual = benchmark_returns.std() * np.sqrt(252)

        num_portfolios = 10000
        results = np.zeros((3, num_portfolios))
        for i in range(num_portfolios):
            w = np.random.uniform(min_weight_val, max_weight_val, num_assets)
            w /= np.sum(w)
            r_ann, v_ann, s_ratio = portfolio_performance(w)
            results[0, i] = v_ann
            results[1, i] = r_ann
            results[2, i] = s_ratio

        init_ret, init_vol, _ = portfolio_performance(initial_weights)
        opt_ret, opt_vol, _ = portfolio_performance(opt_weights)

        fig, ax = plt.subplots(figsize=(10, 6))
        scatter = ax.scatter(results[0, :], results[1, :], c=results[2, :], cmap="viridis", marker="o", s=10, alpha=0.3, label="Portefólios Simulados")
        fig.colorbar(scatter, label="Sharpe Ratio")
        ax.scatter(init_vol, init_ret, color="red", marker="D", s=120, edgecolors="black", label="Portefólio Inicial")
        ax.scatter(opt_vol, opt_ret, color="gold", marker="*", s=250, edgecolors="black", label="Portefólio Otimizado (Max Sharpe)")
        ax.scatter(sp500_vol_annual, sp500_ret_annual, color="blue", marker="^", s=150, edgecolors="black", label="S&P 500 Benchmark")
        ax.set_title("Fronteira de Eficiência de Markowitz", fontsize=14, fontweight="bold")
        ax.set_xlabel("Volatilidade Anualizada / Desvio Padrão (Risco)", fontsize=12)
        ax.set_ylabel("Retorno Anualizado Esperado", fontsize=12)
        ax.legend(loc="upper left", frameon=True)
        ax.grid(True, linestyle="--", alpha=0.5)

        img_buf = io.BytesIO()
        fig.savefig(img_buf, format="png", bbox_inches="tight", dpi=150)
        img_buf.seek(0)
        img_base64 = base64.b64encode(img_buf.read()).decode("utf-8")

        correlation_matrix = asset_returns.corr().round(2)
        weights_df = pd.DataFrame(
            {
                "Ativo": tickers,
                "Peso Inicial": [f"{w:.2%}" for w in initial_weights],
                "Peso Otimizado": [f"{w:.2%}" for w in opt_weights],
            }
        )

        html_content = f"""
        <!DOCTYPE html>
        <html lang="pt">
        <head>
            <meta charset="UTF-8">
            <title>Relatório de Otimização de Portefólio</title>
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 30px; background-color: #f8f9fa; color: #212529; }}
                h1, h2 {{ color: #1a252f; border-bottom: 2px solid #34495e; padding-bottom: 8px; }}
                .container {{ max-width: 1000px; margin: auto; background: white; padding: 25px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 15px; }}
                th, td {{ padding: 12px 15px; text-align: center; border: 1px solid #dee2e6; }}
                th {{ background-color: #2c3e50; color: white; }}
                tr:nth-child(even) {{ background-color: #f2f2f2; }}
                .img-container {{ text-align: center; margin: 30px 0; }}
                .img-container img {{ max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.15); }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📊 Relatório de Otimização de Portefólio (Markowitz)</h1>
                <p><b>Período Analisado:</b> {periodo_analisado} | <b>Limites de Peso:</b> {min_weight_val:.1%} a {max_weight_val:.1%} | <b>Taxa Livre de Risco (US 10Y):</b> {risk_free_rate:.2%}</p>

                <h2>1. Distribuição de Pesos</h2>
                {weights_df.to_html(index=False, classes='table')}

                <h2>2. Comparação de Métricas de Desempenho</h2>
                {df_comparison.to_html(classes='table')}

                <h2>3. Fronteira de Eficiência</h2>
                <div class="img-container">
                    <img src="data:image/png;base64,{img_base64}" alt="Fronteira de Eficiencia">
                </div>

                <h2>4. Matriz de Correlação entre Ativos</h2>
                {correlation_matrix.to_html(classes='table')}
            </div>
        </body>
        </html>
        """

    st.success(f"✓ Taxa Livre de Risco (US 10Y): {risk_free_rate:.2%}")

    st.subheader("1. Distribuição de Pesos")
    st.dataframe(weights_df, use_container_width=True, hide_index=True)

    st.subheader("2. Comparação de Métricas de Desempenho")
    st.dataframe(df_comparison, use_container_width=True)

    st.subheader("3. Fronteira de Eficiência")
    st.pyplot(fig, use_container_width=True)

    st.subheader("4. Matriz de Correlação entre Ativos")
    st.dataframe(correlation_matrix, use_container_width=True)

    st.download_button(
        label="⬇️ Descarregar Relatório Completo em HTML",
        data=html_content,
        file_name="Relatorio_Markowitz.html",
        mime="text/html",
        use_container_width=True,
    )


# ------------------------------------------------------------------------------
# 3. EXECUÇÃO
# ------------------------------------------------------------------------------
if run_button:
    portfolio_config = {}
    for _, row in tickers_df.iterrows():
        t_val = str(row.get("Ticker", "")).strip().upper()
        try:
            p_val = float(row.get("Peso", 0.0))
        except (TypeError, ValueError):
            p_val = 0.0
        if t_val and p_val > 0:
            portfolio_config[t_val] = p_val

    run_optimization(portfolio_config, periodo_analisado, min_weight_val, max_weight_val)
else:
    st.info("👈 Ajusta os parâmetros e a tabela de ativos, depois clica em **Calcular & Gerar Portefólio**.")
