# ==============================================================================
# 📊 SIMULADOR DE PORTEFÓLIO vs S&P 500 — Aplicação Streamlit
# Convertido a partir do notebook original (Colab) para uma app de ambiente
# de trabalho, com interface web local.
# ==============================================================================

import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from theme import inject_theme, page_header, style_plotly

st.set_page_config(
    page_title="Simulador de Portefólio vs S&P 500",
    page_icon="📊",
    layout="wide",
)

inject_theme()

# ------------------------------------------------------------------------------
# MOTOR DE CÁLCULO (idêntico à lógica original, apenas adaptado a Streamlit)
# ------------------------------------------------------------------------------
@st.cache_data(show_spinner=False, ttl=3600)
def download_prices(all_tickers, start_date):
    raw_close = yf.download(all_tickers, start=start_date, progress=False, auto_adjust=False)["Close"]
    adj_close = yf.download(all_tickers, start=start_date, progress=False, auto_adjust=True)
    if "Close" in adj_close:
        adj_close = adj_close["Close"]

    # yfinance devolve Series se só houver 1 ticker — normalizar para DataFrame
    if isinstance(raw_close, pd.Series):
        raw_close = raw_close.to_frame(all_tickers[0])
    if isinstance(adj_close, pd.Series):
        adj_close = adj_close.to_frame(all_tickers[0])

    raw_close = raw_close.ffill().dropna()
    adj_close = adj_close.ffill().dropna()
    return raw_close, adj_close


def run_portfolio_analysis(tickers, weights, start_date, initial_inv, monthly_dca):
    benchmark_ticker = "^GSPC"
    all_tickers = list(dict.fromkeys(tickers + [benchmark_ticker]))

    raw_close, adj_close = download_prices(all_tickers, start_date)

    missing_tickers = [t for t in all_tickers if t not in raw_close.columns]
    if missing_tickers:
        st.error(f"❌ Não foram encontrados dados para o(s) ticker(s): {', '.join(missing_tickers)}")
        return None

    if raw_close.empty or len(raw_close) < 2:
        st.error("❌ Dados insuficientes para o período selecionado.")
        return None

    portfolio_prices = adj_close[tickers]
    benchmark_prices = adj_close[benchmark_ticker]
    raw_portfolio_prices = raw_close[tickers]
    raw_bench_prices = raw_close[benchmark_ticker]

    weights = np.array(weights) / np.sum(weights)
    dates = adj_close.index

    port_shares = np.zeros(len(tickers))
    port_values, bench_values, total_invested_series = [], [], []

    port_shares_raw = np.zeros(len(tickers))
    port_values_raw, bench_values_raw = [], []

    bench_shares = 0.0
    bench_shares_raw = 0.0
    current_invested = 0.0
    previous_month = None

    for date in dates:
        current_month = (date.year, date.month)

        if date == dates[0]:
            current_invested += initial_inv
            port_shares += (initial_inv * weights) / portfolio_prices.loc[date].values
            bench_shares += initial_inv / benchmark_prices.loc[date]

            port_shares_raw += (initial_inv * weights) / raw_portfolio_prices.loc[date].values
            bench_shares_raw += initial_inv / raw_bench_prices.loc[date]
            previous_month = current_month

        elif current_month != previous_month:
            current_invested += monthly_dca
            port_shares += (monthly_dca * weights) / portfolio_prices.loc[date].values
            bench_shares += monthly_dca / benchmark_prices.loc[date]

            port_shares_raw += (monthly_dca * weights) / raw_portfolio_prices.loc[date].values
            bench_shares_raw += monthly_dca / raw_bench_prices.loc[date]
            previous_month = current_month

        current_port_val = np.sum(port_shares * portfolio_prices.loc[date].values)
        current_bench_val = bench_shares * benchmark_prices.loc[date]
        current_port_raw_val = np.sum(port_shares_raw * raw_portfolio_prices.loc[date].values)
        current_bench_raw_val = bench_shares_raw * raw_bench_prices.loc[date]

        port_values.append(current_port_val)
        bench_values.append(current_bench_val)
        port_values_raw.append(current_port_raw_val)
        bench_values_raw.append(current_bench_raw_val)
        total_invested_series.append(current_invested)

    df_results = pd.DataFrame(
        {
            "Portfolio": port_values,
            "SP500": bench_values,
            "Portfolio_NoDiv": port_values_raw,
            "SP500_NoDiv": bench_values_raw,
            "Invested": total_invested_series,
        },
        index=dates,
    )

    div_est_port = max(0.0, df_results["Portfolio"].iloc[-1] - df_results["Portfolio_NoDiv"].iloc[-1])
    div_est_bench = max(0.0, df_results["SP500"].iloc[-1] - df_results["SP500_NoDiv"].iloc[-1])
    div_yield_port = (div_est_port / df_results["Invested"].iloc[-1]) * 100
    div_yield_bench = (div_est_bench / df_results["Invested"].iloc[-1]) * 100

    risk_free_rate = 0.04
    trading_days = 252

    port_daily_ret = df_results["Portfolio"].pct_change().dropna()
    bench_daily_ret = df_results["SP500"].pct_change().dropna()

    total_ret_port = (df_results["Portfolio"].iloc[-1] - df_results["Invested"].iloc[-1]) / df_results["Invested"].iloc[-1]
    total_ret_bench = (df_results["SP500"].iloc[-1] - df_results["Invested"].iloc[-1]) / df_results["Invested"].iloc[-1]

    n_years = (dates[-1] - dates[0]).days / 365.25
    cagr_port = (df_results["Portfolio"].iloc[-1] / df_results["Invested"].iloc[-1]) ** (1 / max(n_years, 0.1)) - 1
    cagr_bench = (df_results["SP500"].iloc[-1] / df_results["Invested"].iloc[-1]) ** (1 / max(n_years, 0.1)) - 1

    vol_port = port_daily_ret.std() * np.sqrt(trading_days)
    vol_bench = bench_daily_ret.std() * np.sqrt(trading_days)

    sharpe_port = (cagr_port - risk_free_rate) / vol_port if vol_port != 0 else 0
    sharpe_bench = (cagr_bench - risk_free_rate) / vol_bench if vol_bench != 0 else 0

    covariance = np.cov(port_daily_ret, bench_daily_ret)[0][1]
    bench_variance = np.var(bench_daily_ret)
    beta = covariance / bench_variance if bench_variance != 0 else 1.0

    def get_max_drawdown(series):
        peak = series.cummax()
        dd = (series - peak) / peak
        return dd.min()

    mdd_port = get_max_drawdown(df_results["Portfolio"])
    mdd_bench = get_max_drawdown(df_results["SP500"])

    metrics_df = pd.DataFrame(
        {
            "Métrica": [
                "Capital Total Investido",
                "Valor Final (Com Dividendos)",
                "💰 Dividendos Reinvestidos (Est.)",
                "📈 Yield Acumulado dos Dividendos",
                "Valor Final (Sem Dividendos)",
                "Retorno Total (%)",
                "Retorno Anualizado (CAGR)",
                "Volatilidade (Risco)",
                "Índice de Sharpe (Rf=4%)",
                "Beta (vs SP500)",
                "Max Drawdown",
            ],
            "Portefólio": [
                f"{df_results['Invested'].iloc[-1]:,.2f} €",
                f"{df_results['Portfolio'].iloc[-1]:,.2f} €",
                f"{div_est_port:,.2f} €",
                f"{div_yield_port:.2f}%",
                f"{df_results['Portfolio_NoDiv'].iloc[-1]:,.2f} €",
                f"{total_ret_port * 100:.2f}%",
                f"{cagr_port * 100:.2f}%",
                f"{vol_port * 100:.2f}%",
                f"{sharpe_port:.2f}",
                f"{beta:.2f}",
                f"{mdd_port * 100:.2f}%",
            ],
            "S&P 500 Benchmark": [
                f"{df_results['Invested'].iloc[-1]:,.2f} €",
                f"{df_results['SP500'].iloc[-1]:,.2f} €",
                f"{div_est_bench:,.2f} €",
                f"{div_yield_bench:.2f}%",
                f"{df_results['SP500_NoDiv'].iloc[-1]:,.2f} €",
                f"{total_ret_bench * 100:.2f}%",
                f"{cagr_bench * 100:.2f}%",
                f"{vol_bench * 100:.2f}%",
                f"{sharpe_bench:.2f}",
                "1.00",
                f"{mdd_bench * 100:.2f}%",
            ],
        }
    ).set_index("Métrica")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_results.index, y=df_results["Portfolio"],
        mode="lines", name="Portefólio (Com Dividendos)",
        line=dict(color="#d4af37", width=2.5),
        hovertemplate="<b>Data:</b> %{x|%d/%m/%Y}<br><b>Portefólio:</b> %{y:,.2f} €<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=df_results.index, y=df_results["SP500"],
        mode="lines", name="S&P 500 (Com Dividendos)",
        line=dict(color="#8fb3d9", width=2),
        hovertemplate="<b>Data:</b> %{x|%d/%m/%Y}<br><b>S&P 500:</b> %{y:,.2f} €<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=df_results.index, y=df_results["Invested"],
        mode="lines", name="Total Investido (Aportes + DCA)",
        line=dict(color="#7fd9a8", width=1.8, dash="dash"),
        hovertemplate="<b>Data:</b> %{x|%d/%m/%Y}<br><b>Investido:</b> %{y:,.2f} €<extra></extra>",
    ))
    fig.update_layout(
        title="<b>Evolução do Património vs S&P 500 (Com Reinvestimento de Dividendos)</b>",
        xaxis_title="Data", yaxis_title="Valor (€ / $)",
        hovermode="x unified",
        margin=dict(l=40, r=40, t=60, b=40),
        height=550,
    )
    fig = style_plotly(fig)

    table_html = metrics_df.to_html(classes="styled-table", border=0)
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Relatório de Desempenho e Dividendos</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Inter:wght@400;500;600&display=swap');
            body {{ font-family: 'Inter', Arial, sans-serif; margin: 30px; background-color: #05070f; color: #f5f5f0; }}
            h1 {{ font-family: 'Playfair Display', serif; color: #f6e7c1; text-align: center; margin-bottom: 20px; letter-spacing: 0.03em; }}
            h2 {{ color: #e8c874; }}
            .container {{ max-width: 1200px; margin: 0 auto; background: #0d1230; padding: 25px; border-radius: 12px; border: 1px solid rgba(212,175,55,0.25); box-shadow: 0 8px 24px rgba(0,0,0,0.4); }}
            .styled-table {{ border-collapse: collapse; margin: 25px 0; font-size: 0.95em; min-width: 100%; border-radius: 8px; overflow: hidden; box-shadow: 0 0 20px rgba(0,0,0,0.2); }}
            .styled-table thead tr {{ background: linear-gradient(135deg, #b8912e, #d4af37); color: #05070f; text-align: left; font-weight: bold; }}
            .styled-table th, .styled-table td {{ padding: 12px 15px; border-bottom: 1px solid rgba(212,175,55,0.15); color: #f5f5f0; }}
            .styled-table tbody tr:nth-of-type(even) {{ background-color: rgba(212,175,55,0.05); }}
            .styled-table tbody tr:last-of-type {{ border-bottom: 2px solid #d4af37; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Luminara Capital — Relatório de Portefólio e Dividendos vs S&P 500</h1>
            <h2>Métricas de Performance, Risco e Dividendos</h2>
            {table_html}
            <h2>Gráfico Interativo de Desempenho</h2>
            {fig.to_html(full_html=False, include_plotlyjs='cdn')}
        </div>
    </body>
    </html>
    """

    return metrics_df, fig, html_content


# ------------------------------------------------------------------------------
# INTERFACE (equivalente aos widgets do Colab)
# ------------------------------------------------------------------------------
page_header(
    "📊",
    "Simulador de Portefólio vs S&P 500",
    "Simula um portefólio com investimento inicial + DCA mensal, comparado com o S&P 500 (com dividendos reinvestidos).",
)

with st.sidebar:
    st.header("⚙️ Configuração do Portefólio")
    tickers_input = st.text_input("Tickers (separados por vírgula)", "AAPL, MSFT, NVDA, BTC-USD")
    weights_input = st.text_input("Pesos % (mesma ordem dos tickers)", "30, 30, 20, 20")
    start_date = st.date_input("Data Inicial", value=pd.to_datetime("2021-01-01"))
    initial_inv = st.number_input("Investimento Inicial (€)", min_value=0.0, value=10000.0, step=100.0)
    monthly_dca = st.number_input("Aporte Mensal / DCA (€)", min_value=0.0, value=100.0, step=10.0)
    run_button = st.button("🚀 Simular Portefólio", type="primary", use_container_width=True)

if run_button:
    try:
        tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
        weights = [float(w.strip()) for w in weights_input.split(",") if w.strip()]

        if len(tickers) != len(weights):
            st.error("❌ O número de tickers e o número de pesos devem ser iguais.")
        else:
            with st.spinner("A obter dados de mercado e a simular o portefólio..."):
                result = run_portfolio_analysis(
                    tickers, weights, start_date.strftime("%Y-%m-%d"), initial_inv, monthly_dca
                )

            if result is not None:
                metrics_df, fig, html_content = result

                st.subheader("📋 Tabela Comparativa de Desempenho, Risco e Dividendos")
                st.dataframe(metrics_df, use_container_width=True)

                st.subheader("📈 Gráfico Interativo de Desempenho")
                st.plotly_chart(fig, use_container_width=True)

                st.download_button(
                    label="⬇️ Descarregar Relatório HTML Interativo",
                    data=html_content,
                    file_name="relatorio_portefolio_dividendos.html",
                    mime="text/html",
                    use_container_width=True,
                )
                st.success("✅ Simulação concluída!")
    except Exception as e:
        st.error(f"❌ Erro ao processar os dados: {e}")
else:
    st.info("👈 Preenche os parâmetros na barra lateral e clica em **Simular Portefólio** para começar.")
