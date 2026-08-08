# ==============================================================================
# 📊 SIMULADOR DE PORTEFÓLIO vs S&P 500 — Aplicação Streamlit
# Convertido a partir do notebook original (Colab) para uma app de ambiente
# de trabalho, com interface web local.
#
# ATUALIZAÇÃO: adiciona Stress Test (piores quedas históricas), diversificação
# setorial e geográfica, e tabela cruzada Cap Size x Estilo (Value/Growth/Core).
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

# Paleta consistente com a identidade Luminara Capital (dourado / navy)
LUMINARA_PALETTE = [
    "#d4af37", "#8fb3d9", "#7fd9a8", "#f6e7c1", "#b8912e",
    "#4a5a8f", "#c9a876", "#5c6b8a", "#e8c874", "#6f8fae",
]

# ------------------------------------------------------------------------------
# EVENTOS MACRO CONHECIDOS (para contextualizar os piores drawdowns)
# Datas aproximadas com base em picos/vales de mercado amplamente reportados.
# ------------------------------------------------------------------------------
KNOWN_EVENTS = [
    ("2018-09-20", "2018-12-24", "Selloff Q4 2018 (subida de juros da Fed + receios de recessão)"),
    ("2020-02-19", "2020-03-23", "Crash COVID-19 (paragem económica global)"),
    ("2022-01-03", "2022-10-13", "Mercado Bear 2022 (inflação elevada + subida agressiva de juros)"),
    ("2023-03-08", "2023-03-13", "Crise bancária regional dos EUA (colapso do SVB / Credit Suisse)"),
    ("2024-08-01", "2024-08-08", "Correção de agosto 2024 (desmontagem do 'yen carry trade')"),
    ("2025-02-19", "2025-04-08", "Guerra tarifária de Trump / 'Liberation Day' (escalada de tarifas comerciais)"),
]


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


@st.cache_data(show_spinner=False, ttl=3600)
def get_ticker_fundamentals(tickers):
    """Obtém setor, país, tipo de instrumento, market cap, P/E e P/B por ticker."""
    fundamentals = {}
    for t in tickers:
        try:
            info = yf.Ticker(t).info
        except Exception:
            info = {}

        is_crypto = t.upper().endswith("-USD") or info.get("quoteType") == "CRYPTOCURRENCY"
        quote_type = info.get("quoteType", "N/D")

        fundamentals[t] = {
            "sector": "Criptomoeda" if is_crypto else (info.get("sector") or (
                "ETF / Fundo" if quote_type == "ETF" else "Outro / Não Classificado"
            )),
            "country": "Global / Descentralizado" if is_crypto else (info.get("country") or "Não Especificado"),
            "quote_type": quote_type,
            "market_cap": info.get("marketCap"),
            "trailing_pe": info.get("trailingPE"),
            "price_to_book": info.get("priceToBook"),
            "is_crypto": is_crypto,
        }
    return fundamentals


def classify_cap_size(market_cap):
    if market_cap is None:
        return "N/D"
    if market_cap >= 10_000_000_000:
        return "Large Cap"
    elif market_cap >= 2_000_000_000:
        return "Mid Cap"
    else:
        return "Small Cap"


def classify_style(pe, pb):
    """Heurística simplificada de estilo (Value / Growth / Core) com base em P/E e P/B.
    NOTA: aproximação didática — não corresponde à metodologia proprietária de
    classificação usada por fornecedores como Morningstar."""
    if pe is None or pe <= 0:
        return "Core"
    if pe < 15 and (pb is None or pb < 3):
        return "Value"
    elif pe > 25:
        return "Growth"
    else:
        return "Core"


def build_diversification_data(tickers, weights, fundamentals):
    weights = np.array(weights) / np.sum(weights)

    sector_weights, country_weights = {}, {}
    capstyle_rows = []
    excluded_from_capstyle = []

    for t, w in zip(tickers, weights):
        f = fundamentals.get(t, {})
        sector = f.get("sector", "Outro / Não Classificado")
        country = f.get("country", "Não Especificado")

        sector_weights[sector] = sector_weights.get(sector, 0) + w
        country_weights[country] = country_weights.get(country, 0) + w

        if f.get("is_crypto") or f.get("quote_type") == "ETF" or f.get("market_cap") is None:
            excluded_from_capstyle.append(t)
            continue

        cap = classify_cap_size(f.get("market_cap"))
        style = classify_style(f.get("trailing_pe"), f.get("price_to_book"))
        capstyle_rows.append({"ticker": t, "weight": w, "cap": cap, "style": style})

    sector_df = pd.Series(sector_weights).sort_values(ascending=False) * 100
    country_df = pd.Series(country_weights).sort_values(ascending=False) * 100

    cap_order = ["Large Cap", "Mid Cap", "Small Cap"]
    style_order = ["Value", "Core", "Growth"]
    capstyle_table = pd.DataFrame(0.0, index=cap_order, columns=style_order)
    for row in capstyle_rows:
        if row["cap"] in cap_order:
            capstyle_table.loc[row["cap"], row["style"]] += row["weight"] * 100

    return sector_df, country_df, capstyle_table, excluded_from_capstyle


def make_pie_chart(series, title):
    fig = go.Figure(data=[go.Pie(
        labels=series.index,
        values=series.values,
        hole=0.45,
        marker=dict(colors=LUMINARA_PALETTE, line=dict(color="#05070f", width=1.5)),
        textinfo="label+percent",
        hovertemplate="<b>%{label}</b><br>Peso: %{value:.1f}%<extra></extra>",
    )])
    fig.update_layout(title=f"<b>{title}</b>", height=430, margin=dict(l=20, r=20, t=60, b=20))
    return style_plotly(fig)


# ------------------------------------------------------------------------------
# STRESS TEST — deteção automática dos piores drawdowns + evento macro associado
# ------------------------------------------------------------------------------
def get_drawdown_episodes(series, top_n=5):
    cummax = series.cummax()
    episodes = []
    in_dd = False
    peak_date, peak_val = series.index[0], series.iloc[0]
    trough_date, trough_val = None, None

    for date, val in series.items():
        if val >= cummax.loc[date] * 0.999999:
            if in_dd and trough_date is not None:
                episodes.append({
                    "peak_date": peak_date, "peak_val": peak_val,
                    "trough_date": trough_date, "trough_val": trough_val,
                    "recovery_date": date,
                })
            peak_date, peak_val = date, val
            trough_date, trough_val = None, None
            in_dd = False
        else:
            in_dd = True
            if trough_val is None or val < trough_val:
                trough_val, trough_date = val, date

    if in_dd and trough_date is not None:
        episodes.append({
            "peak_date": peak_date, "peak_val": peak_val,
            "trough_date": trough_date, "trough_val": trough_val,
            "recovery_date": None,
        })

    for ep in episodes:
        ep["drawdown_pct"] = (ep["trough_val"] - ep["peak_val"]) / ep["peak_val"]

    # Ignorar micro-quedas irrelevantes (< 3%) e ordenar pela mais severa
    episodes = [e for e in episodes if e["drawdown_pct"] <= -0.03]
    episodes = sorted(episodes, key=lambda x: x["drawdown_pct"])[:top_n]
    return episodes


def match_known_event(trough_date):
    for start, end, label in KNOWN_EVENTS:
        start_ts, end_ts = pd.Timestamp(start), pd.Timestamp(end)
        if start_ts - pd.Timedelta(days=12) <= trough_date <= end_ts + pd.Timedelta(days=12):
            return label
    return "Correção de mercado (sem evento macro específico identificado)"


def build_stress_test_table(df_results, top_n=5):
    port_series = df_results["Portfolio"]
    bench_series = df_results["SP500"]

    episodes = get_drawdown_episodes(port_series, top_n=top_n)
    if not episodes:
        return None

    rows = []
    for ep in episodes:
        peak_date, trough_date = ep["peak_date"], ep["trough_date"]
        recovery_date = ep["recovery_date"]

        duration_days = (trough_date - peak_date).days
        if recovery_date is not None:
            recovery_str = f"{(recovery_date - trough_date).days} dias"
        else:
            recovery_str = "Ainda em recuperação"

        # Queda do S&P 500 na mesma janela, para comparação
        try:
            bench_window = bench_series.loc[peak_date:trough_date]
            bench_dd = (bench_window.min() - bench_window.iloc[0]) / bench_window.iloc[0]
        except Exception:
            bench_dd = np.nan

        rows.append({
            "Período (Pico → Vale)": f"{peak_date.strftime('%d/%m/%Y')} → {trough_date.strftime('%d/%m/%Y')}",
            "Duração da Queda": f"{duration_days} dias",
            "Queda Máxima — Portefólio": f"{ep['drawdown_pct'] * 100:.2f}%",
            "Queda Máxima — S&P 500": f"{bench_dd * 100:.2f}%" if not np.isnan(bench_dd) else "N/D",
            "Tempo até Recuperação": recovery_str,
            "Evento Provável": match_known_event(trough_date),
        })

    return pd.DataFrame(rows)


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

    # ---- Novas análises: stress test, diversificação, cap/estilo ----
    stress_df = build_stress_test_table(df_results, top_n=5)

    fundamentals = get_ticker_fundamentals(tickers)
    sector_series, country_series, capstyle_table, excluded_capstyle = build_diversification_data(
        tickers, weights, fundamentals
    )
    sector_fig = make_pie_chart(sector_series, "Diversificação Setorial")
    geo_fig = make_pie_chart(country_series, "Diversificação Geográfica")

    # ---- Relatório HTML ----
    table_html = metrics_df.to_html(classes="styled-table", border=0)
    stress_html = stress_df.to_html(classes="styled-table", border=0, index=False) if stress_df is not None else "<p>Sem quedas relevantes (&gt;3%) no período selecionado.</p>"
    capstyle_html = capstyle_table.round(2).to_html(classes="styled-table", border=0)

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Relatório de Desempenho, Risco e Diversificação</title>
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
            .caption {{ color: #a9b3c9; font-size: 0.85em; margin-top: -10px; margin-bottom: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Luminara Capital — Relatório de Portefólio, Risco e Diversificação</h1>
            <h2>Métricas de Performance, Risco e Dividendos</h2>
            {table_html}
            <h2>Gráfico Interativo de Desempenho</h2>
            {fig.to_html(full_html=False, include_plotlyjs='cdn')}
            <h2>Stress Test — Piores Quedas Históricas do Portefólio</h2>
            <p class="caption">Deteção automática dos maiores episódios de queda (pico → vale) no período selecionado, com o evento macro mais provável associado.</p>
            {stress_html}
            <h2>Diversificação Setorial</h2>
            {sector_fig.to_html(full_html=False, include_plotlyjs=False)}
            <h2>Diversificação Geográfica</h2>
            {geo_fig.to_html(full_html=False, include_plotlyjs=False)}
            <h2>Tabela Cruzada — Capitalização x Estilo (% do Portefólio)</h2>
            <p class="caption">Classificação aproximada com base em capitalização de mercado e rácios P/E e P/B. ETFs e criptomoedas não são incluídos (não têm estas métricas). Estilo é uma heurística simplificada, não uma classificação oficial.</p>
            {capstyle_html}
        </div>
    </body>
    </html>
    """

    return {
        "metrics_df": metrics_df,
        "fig": fig,
        "stress_df": stress_df,
        "sector_fig": sector_fig,
        "geo_fig": geo_fig,
        "sector_series": sector_series,
        "country_series": country_series,
        "capstyle_table": capstyle_table,
        "excluded_capstyle": excluded_capstyle,
        "html_content": html_content,
    }


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
            with st.spinner("A obter dados de mercado, fundamentais e a simular o portefólio..."):
                result = run_portfolio_analysis(
                    tickers, weights, start_date.strftime("%Y-%m-%d"), initial_inv, monthly_dca
                )

            if result is not None:
                metrics_df = result["metrics_df"]
                fig = result["fig"]

                st.subheader("📋 Tabela Comparativa de Desempenho, Risco e Dividendos")
                st.dataframe(metrics_df, use_container_width=True)

                st.subheader("📈 Gráfico Interativo de Desempenho")
                st.plotly_chart(fig, use_container_width=True)

                # ---- Stress Test ----
                st.subheader("🧨 Stress Test — Piores Quedas Históricas")
                st.caption(
                    "Deteção automática dos maiores episódios de queda (pico → vale) do portefólio "
                    "no período selecionado, comparados com o S&P 500 e associados ao evento macro mais provável."
                )
                if result["stress_df"] is not None:
                    st.dataframe(result["stress_df"], use_container_width=True, hide_index=True)
                else:
                    st.info("Não foram detetadas quedas relevantes (> 3%) no período selecionado.")

                # ---- Diversificação Setorial e Geográfica ----
                st.subheader("🌍 Diversificação Setorial e Geográfica")
                col1, col2 = st.columns(2)
                with col1:
                    st.plotly_chart(result["sector_fig"], use_container_width=True)
                with col2:
                    st.plotly_chart(result["geo_fig"], use_container_width=True)

                # ---- Tabela Cruzada Cap Size x Estilo ----
                st.subheader("🧮 Tabela Cruzada — Capitalização x Estilo")
                st.caption(
                    "Classificação aproximada com base em capitalização de mercado (Large/Mid/Small Cap) "
                    "e rácios P/E e P/B (Value/Core/Growth). Valores em % do portefólio. "
                    "ETFs e criptomoedas ficam de fora por não terem estas métricas disponíveis. "
                    "É uma heurística simplificada, não uma classificação oficial de mercado."
                )
                st.dataframe(
                    result["capstyle_table"].round(2).style.format("{:.2f}%"),
                    use_container_width=True,
                )
                if result["excluded_capstyle"]:
                    st.caption(f"⚠️ Excluídos da tabela cruzada: {', '.join(result['excluded_capstyle'])}")

                st.download_button(
                    label="⬇️ Descarregar Relatório HTML Interativo",
                    data=result["html_content"],
                    file_name="relatorio_portefolio_completo.html",
                    mime="text/html",
                    use_container_width=True,
                )
                st.success("✅ Simulação concluída!")
    except Exception as e:
        st.error(f"❌ Erro ao processar os dados: {e}")
else:
    st.info("👈 Preenche os parâmetros na barra lateral e clica em **Simular Portefólio** para começar.")
