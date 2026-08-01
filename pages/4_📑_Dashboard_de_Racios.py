# ==============================================================================
# 📑 DASHBOARD DE RÁCIOS FINANCEIROS & VALUATION — Aplicação Streamlit
# Convertido a partir do notebook original (Colab, ipywidgets) para uma página
# do hub Streamlit. O visual "Wall Street" (CSS customizado) foi mantido
# integralmente, renderizado via st.markdown(unsafe_allow_html=True).
# ==============================================================================

import warnings
warnings.filterwarnings("ignore")

from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf

st.set_page_config(
    page_title="Dashboard de Rácios & Valuation",
    page_icon="📑",
    layout="wide",
)

# ------------------------------------------------------------------------------
# ESTILO CSS (idêntico ao original)
# ------------------------------------------------------------------------------
STYLE_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    .report-container {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        background-color: #f8fafc;
        color: #0f172a;
        padding: 30px;
        border-radius: 16px;
        box-shadow: 0 10px 25px -5px rgba(0,0,0,0.05), 0 8px 10px -6px rgba(0,0,0,0.01);
        max-width: 1200px;
        margin: 0 auto;
    }

    .header-card {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        color: #ffffff;
        padding: 28px 32px;
        border-radius: 14px;
        margin-bottom: 30px;
        box-shadow: 0 10px 20px rgba(15, 23, 42, 0.15);
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 15px;
    }

    .header-card h1 { margin: 0; font-size: 26px; font-weight: 700; letter-spacing: -0.5px; color: #ffffff; }
    .header-card .subtitle { color: #94a3b8; font-size: 13px; margin-top: 6px; font-weight: 400; }

    .badge-sector {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(8px);
        border: 1px solid rgba(255, 255, 255, 0.15);
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 500;
        color: #38bdf8;
    }

    .section-title {
        font-size: 16px; font-weight: 600; color: #1e293b; margin-top: 32px; margin-bottom: 14px;
        display: flex; align-items: center; gap: 8px; letter-spacing: -0.2px;
    }
    .section-title::before { content: ''; display: inline-block; width: 4px; height: 18px; background: #2563eb; border-radius: 2px; }

    .table-wrapper {
        background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden;
        margin-bottom: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }

    .finance-table { border-collapse: collapse; width: 100%; font-size: 13px; margin: 0; }
    .finance-table th {
        background-color: #f1f5f9; color: #475569; text-align: right; padding: 12px 16px;
        font-weight: 600; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px;
        border-bottom: 1px solid #e2e8f0;
    }
    .finance-table th:first-child { text-align: left; }
    .finance-table td {
        border-bottom: 1px solid #f1f5f9; padding: 11px 16px; text-align: right; color: #334155;
        font-variant-numeric: tabular-nums;
    }
    .finance-table td:first-child {
        font-weight: 600; text-align: left; color: #0f172a; background-color: #fafafa; width: 250px;
    }
    .finance-table tr:last-child td { border-bottom: none; }
    .finance-table tr:hover td { background-color: #f8fafc; }
    .finance-table tr:hover td:first-child { background-color: #f1f5f9; }

    .analysis-card {
        background: #ffffff; border: 1px solid #e2e8f0; border-left: 5px solid #2563eb; border-radius: 12px;
        padding: 24px; margin-top: 25px; font-size: 14px; line-height: 1.7; color: #334155;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.03);
    }
    .analysis-card h3 { margin-top: 0; color: #0f172a; font-size: 16px; font-weight: 600; margin-bottom: 12px; }
</style>
"""

# ------------------------------------------------------------------------------
# LÓGICA DE CÁLCULO (inalterada)
# ------------------------------------------------------------------------------
def safe_div(num, denom):
    if denom is None or num is None or denom == 0 or np.isnan(denom) or np.isnan(num):
        return np.nan
    return num / denom


@st.cache_data(show_spinner=False, ttl=3600)
def fetch_financial_data(ticker_symbol):
    ticker = yf.Ticker(ticker_symbol)

    bs = ticker.balance_sheet
    inc = ticker.financials
    cf = ticker.cashflow
    hist = ticker.history(period="5y")
    info = ticker.info

    if bs.empty or inc.empty:
        raise ValueError(f"Não foram encontrados dados suficientes para o ticker: {ticker_symbol}")

    years = sorted(list(set(inc.columns).intersection(bs.columns)), reverse=True)[:5]
    if len(years) < 2:
        raise ValueError("Histórico de dados financeiros insuficiente (mínimo 2 anos necessários).")

    data = {}
    for yr in years:
        yr_str = str(yr.year) if hasattr(yr, "year") else str(yr)[:4]

        tot_assets = bs.loc["Total Assets", yr] if "Total Assets" in bs.index else np.nan
        tot_equity = bs.loc["Stockholders Equity", yr] if "Stockholders Equity" in bs.index else (
            bs.loc["Total Equity Gross Minority Interest", yr] if "Total Equity Gross Minority Interest" in bs.index else np.nan
        )
        tot_debt = bs.loc["Total Debt", yr] if "Total Debt" in bs.index else np.nan
        curr_assets = bs.loc["Current Assets", yr] if "Current Assets" in bs.index else np.nan
        curr_liab = bs.loc["Current Liabilities", yr] if "Current Liabilities" in bs.index else np.nan
        inventory = bs.loc["Inventory", yr] if "Inventory" in bs.index else 0
        cash = bs.loc["Cash And Cash Equivalents", yr] if "Cash And Cash Equivalents" in bs.index else 0

        rev = inc.loc["Total Revenue", yr] if "Total Revenue" in inc.index else np.nan
        ebitda = inc.loc["EBITDA", yr] if "EBITDA" in inc.index else np.nan
        ebit = inc.loc["EBIT", yr] if "EBIT" in inc.index else (inc.loc["Operating Income", yr] if "Operating Income" in inc.index else np.nan)
        net_inc = inc.loc["Net Income", yr] if "Net Income" in inc.index else np.nan
        eps = inc.loc["Diluted EPS", yr] if "Diluted EPS" in inc.index else (inc.loc["Basic EPS", yr] if "Basic EPS" in inc.index else np.nan)
        interest_exp = abs(inc.loc["Interest Expense", yr]) if "Interest Expense" in inc.index else np.nan

        fcf = cf.loc["Free Cash Flow", yr] if "Free Cash Flow" in cf.index else np.nan
        div_paid = abs(cf.loc["Cash Dividends Paid", yr]) if "Cash Dividends Paid" in cf.index else 0

        data[yr_str] = {
            "Revenue": rev, "EBITDA": ebitda, "EBIT": ebit, "Net Income": net_inc, "EPS": eps, "FCF": fcf, "Dividends": div_paid,
            "Total Debt": tot_debt, "Equity": tot_equity, "Total Assets": tot_assets, "Cash": cash,
            "ROA": safe_div(net_inc, tot_assets),
            "ROE": safe_div(net_inc, tot_equity),
            "ROIC": safe_div(ebit * (1 - 0.21), (tot_equity + tot_debt - cash)),
            "EBITDA Margin": safe_div(ebitda, rev),
            "Operating Margin": safe_div(ebit, rev),
            "Net Margin": safe_div(net_inc, rev),
            "Current Ratio": safe_div(curr_assets, curr_liab),
            "Quick Ratio": safe_div(curr_assets - inventory, curr_liab),
            "Debt/Equity": safe_div(tot_debt, tot_equity),
            "Debt/EBITDA": safe_div(tot_debt, ebitda),
            "Interest Coverage": safe_div(ebit, interest_exp),
        }

    df_hist = pd.DataFrame(data)

    df_growth = pd.DataFrame(
        index=["Revenue Growth", "EBITDA Growth", "Net Income Growth", "EPS Growth", "FCF Growth", "Dividend Growth"],
        columns=df_hist.columns,
    )
    for metric, name in [
        ("Revenue", "Revenue Growth"), ("EBITDA", "EBITDA Growth"), ("Net Income", "Net Income Growth"),
        ("EPS", "EPS Growth"), ("FCF", "FCF Growth"), ("Dividends", "Dividend Growth"),
    ]:
        vals = df_hist.loc[metric].values
        growths = [safe_div(vals[i] - vals[i + 1], abs(vals[i + 1])) if i + 1 < len(vals) else np.nan for i in range(len(vals))]
        df_growth.loc[name] = growths

    shares_out = info.get("sharesOutstanding", np.nan)
    val_data = {}
    for yr_str in df_hist.columns:
        try:
            p = hist.loc[hist.index.year == int(yr_str)]["Close"].iloc[-1]
            mcap = p * shares_out if shares_out else np.nan
            ev = mcap + df_hist.loc["Total Debt", yr_str] - df_hist.loc["Cash", yr_str] if mcap else np.nan
        except Exception:
            p, mcap, ev = np.nan, np.nan, np.nan

        val_data[yr_str] = {
            "P/E": safe_div(mcap, df_hist.loc["Net Income", yr_str]),
            "Forward P/E": info.get("forwardPE", np.nan) if yr_str == df_hist.columns[0] else np.nan,
            "PEG": info.get("pegRatio", np.nan) if yr_str == df_hist.columns[0] else np.nan,
            "EV/EBITDA": safe_div(ev, df_hist.loc["EBITDA", yr_str]),
            "EV/EBIT": safe_div(ev, df_hist.loc["EBIT", yr_str]),
            "EV/Revenue": safe_div(ev, df_hist.loc["Revenue", yr_str]),
        }
    df_val = pd.DataFrame(val_data)

    daily_returns = hist["Close"].pct_change().dropna()
    beta = info.get("beta", np.nan)
    volatility = daily_returns.std() * np.sqrt(252)
    cumulative = (1 + daily_returns).cumprod()
    peak = cumulative.cummax()
    drawdown = (cumulative - peak) / peak
    max_drawdown = drawdown.min()

    rf = 0.04
    ann_return = daily_returns.mean() * 252
    sharpe = safe_div(ann_return - rf, volatility)

    df_market = pd.DataFrame(
        {
            df_hist.columns[0]: {
                "Beta": beta,
                "Volatilidade (Anual)": volatility,
                "Maximum Drawdown": max_drawdown,
                "Sharpe Ratio": sharpe,
            }
        }
    )

    return {
        "info": info,
        "val": df_val,
        "growth": df_growth,
        "profitability": df_hist.loc[["ROA", "ROE", "ROIC", "EBITDA Margin", "Operating Margin", "Net Margin"]],
        "leverage": df_hist.loc[["Debt/Equity", "Debt/EBITDA", "Interest Coverage"]],
        "liquidity": df_hist.loc[["Current Ratio", "Quick Ratio"]],
        "market": df_market,
    }


@st.cache_data(show_spinner=False, ttl=3600)
def fetch_peer_benchmark(ticker_symbol, sector):
    t = yf.Ticker(ticker_symbol)
    try:
        peers_list = t.info.get("recommendedSymbols", [])
    except Exception:
        peers_list = []

    if not peers_list:
        sector_peers = {
            "Technology": ["MSFT", "AAPL", "GOOGL", "NVDA"],
            "Healthcare": ["JNJ", "PFE", "UNH", "ABBV"],
            "Financial Services": ["JPM", "BAC", "WFC", "C"],
            "Consumer Cyclical": ["AMZN", "TSLA", "HD", "NKE"],
            "Communication Services": ["META", "DIS", "NFLX", "TMUS"],
        }
        peers_list = sector_peers.get(sector, ["AAPL", "MSFT", "GOOGL", "AMZN"])

    peers_list = [p for p in peers_list if p != ticker_symbol][:4]
    all_tickers = [ticker_symbol] + peers_list
    comp_data = {}

    for tk in all_tickers:
        t = yf.Ticker(tk)
        inf = t.info
        bs = t.balance_sheet
        inc = t.financials

        try:
            net_inc = inc.loc["Net Income"].iloc[0] if "Net Income" in inc.index else np.nan
            rev = inc.loc["Total Revenue"].iloc[0] if "Total Revenue" in inc.index else np.nan
            ebitda = inc.loc["EBITDA"].iloc[0] if "EBITDA" in inc.index else np.nan
            tot_equity = bs.loc["Stockholders Equity"].iloc[0] if "Stockholders Equity" in bs.index else np.nan
            tot_debt = bs.loc["Total Debt"].iloc[0] if "Total Debt" in bs.index else np.nan

            comp_data[tk] = {
                "P/E": inf.get("trailingPE", np.nan),
                "Forward P/E": inf.get("forwardPE", np.nan),
                "EV/EBITDA": inf.get("enterpriseToEbitda", np.nan),
                "P/S (EV/Rev)": inf.get("enterpriseToRevenue", np.nan),
                "Revenue Growth (YoY)": inf.get("revenueGrowth", np.nan),
                "ROE": safe_div(net_inc, tot_equity),
                "EBITDA Margin": safe_div(ebitda, rev),
                "Net Margin": inf.get("profitMargins", np.nan),
                "Debt/Equity": safe_div(tot_debt, tot_equity),
                "Current Ratio": inf.get("currentRatio", np.nan),
            }
        except Exception:
            continue

    return pd.DataFrame(comp_data)


def generate_peer_appreciation(ticker_symbol, df_comp):
    if ticker_symbol not in df_comp.columns:
        return "Dados insuficientes para gerar a análise comparativa automatizada."

    target = df_comp[ticker_symbol]
    peers_median = df_comp.drop(columns=[ticker_symbol]).median(axis=1)

    pe_rel = safe_div(target["P/E"], peers_median["P/E"]) - 1
    roe_diff = (target["ROE"] - peers_median["ROE"]) * 100
    margin_diff = (target["EBITDA Margin"] - peers_median["EBITDA Margin"]) * 100

    valuation_str = (
        "<span style='color:#059669; font-weight:600;'>Subvalorizada</span>" if pe_rel < -0.05 else
        ("<span style='color:#dc2626; font-weight:600;'>Sobrevalorizada</span>" if pe_rel > 0.05 else
         "<span style='color:#2563eb; font-weight:600;'>Em linha com o mercado</span>")
    )
    operational_str = (
        "<span style='color:#059669; font-weight:600;'>Superior</span>" if roe_diff > 0 and margin_diff > 0 else
        ("<span style='color:#dc2626; font-weight:600;'>Inferior</span>" if roe_diff < 0 and margin_diff < 0 else
         "<span style='color:#d97706; font-weight:600;'>Mista</span>")
    )

    text = f"""
    <h3>Apreciação Relativa & Valuation (Perspetiva de Quant/Hedge Fund)</h3>
    <p>A <strong>{ticker_symbol}</strong> demonstra uma eficiência operacional <strong>{operational_str}</strong> relativamente aos pares diretos do setor.
    O retorno sobre o capital próprio (ROE) fixa-se nos <strong>{target['ROE']*100:.2f}%</strong> (face à mediana dos concorrentes de {peers_median['ROE']*100:.2f}%), enquanto a margem EBITDA atinge <strong>{target['EBITDA Margin']*100:.2f}%</strong> (vs. {peers_median['EBITDA Margin']*100:.2f}% do grupo de referência).</p>

    <p>Em termos de avaliação de mercado, a ação é negociada a um múltiplo P/E de <strong>{target['P/E']:.2f}x</strong> e EV/EBITDA de <strong>{target['EV/EBITDA']:.2f}x</strong>.
    Frente à mediana dos seus concorrentes diretos, a empresa apresenta-se <strong>{valuation_str}</strong> (múltiplo P/E com variação de <strong>{pe_rel*100:+.2f}%</strong> face aos pares).
    A alavancagem financeira fixa-se num rácio Debt/Equity de <strong>{target['Debt/Equity']:.2f}x</strong> (comparado com {peers_median['Debt/Equity']:.2f}x dos concorrentes).</p>
    """
    return text


def format_df_to_html(df):
    df_formatted = df.astype(object)
    for col in df_formatted.columns:
        for idx in df_formatted.index:
            val = df_formatted.loc[idx, col]
            if pd.isna(val) or val is None:
                df_formatted.loc[idx, col] = "<span style='color:#94a3b8;'>—</span>"
            elif "Growth" in idx or "ROA" in idx or "ROE" in idx or "ROIC" in idx or "Margin" in idx or "Volatilidade" in idx or "Drawdown" in idx:
                color = "#059669" if val > 0 else ("#dc2626" if val < 0 else "#334155")
                df_formatted.loc[idx, col] = f"<span style='color:{color}; font-weight:500;'>{val * 100:.2f}%</span>"
            else:
                df_formatted.loc[idx, col] = f"{val:.2f}x" if "Ratio" not in idx and "Sharpe" not in idx and "Beta" not in idx else f"{val:.2f}"

    table_html = df_formatted.to_html(classes="finance-table", escape=False)
    return f"<div class='table-wrapper'>{table_html}</div>"


# ------------------------------------------------------------------------------
# INTERFACE
# ------------------------------------------------------------------------------
st.title("📑 Dashboard de Rácios Financeiros & Valuation")
st.caption("Relatório estilo Wall Street: valuation, crescimento, rentabilidade, alavancagem, liquidez, risco e benchmark de pares.")

with st.sidebar:
    st.header("⚙️ Empresa")
    ticker_input = st.text_input("Ticker", value="AAPL")
    analyze_button = st.button("📊 Gerar Relatório Premium", type="primary", use_container_width=True)

if analyze_button:
    symbol = ticker_input.strip().upper()
    with st.spinner(f"⚡ A extrair demonstrações financeiras e a recalcular indicadores para {symbol}..."):
        try:
            data = fetch_financial_data(symbol)
            sector = data["info"].get("sector", "Technology")
            company_name = data["info"].get("longName", symbol)
            df_peers = fetch_peer_benchmark(symbol, sector)
            appreciation_html = generate_peer_appreciation(symbol, df_peers)

            html_body = f"""
            <div class='report-container'>
                <div class='header-card'>
                    <div>
                        <h1>{company_name} ({symbol})</h1>
                        <div class='subtitle'>Relatório de Análise Financeira, Rácios e Valuation Comparativo</div>
                    </div>
                    <div>
                        <span class='badge-sector'>{sector}</span>
                        <div style='color: #94a3b8; font-size: 11px; margin-top: 6px; text-align: right;'>{datetime.now().strftime('%d/%m/%Y')}</div>
                    </div>
                </div>

                <div class='section-title'>1. Múltiplos de Valuation (Evolução Histórica)</div>
                {format_df_to_html(data['val'])}

                <div class='section-title'>2. Crescimento Histórico YoY</div>
                {format_df_to_html(data['growth'])}

                <div class='section-title'>3. Margens e Indicadores de Rentabilidade</div>
                {format_df_to_html(data['profitability'])}

                <div class='section-title'>4. Estrutura de Capital e Endividamento</div>
                {format_df_to_html(data['leverage'])}

                <div class='section-title'>5. Rácios de Liquidez</div>
                {format_df_to_html(data['liquidity'])}

                <div class='section-title'>6. Métricas de Mercado, Volatilidade e Risco (5 Anos)</div>
                {format_df_to_html(data['market'])}

                <div class='section-title'>7. Peer Benchmark & Análise Setorial Direta ({sector})</div>
                {format_df_to_html(df_peers)}

                <div class='section-title'>8. Conclusão & Síntese do Analista</div>
                <div class='analysis-card'>
                    {appreciation_html}
                </div>
            </div>
            """

            full_html = f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>Relatório {symbol}</title>{STYLE_CSS}</head><body style='background:#f1f5f9; padding:20px;'>{html_body}</body></html>"

            # Número de linhas de tabela aproximado, para dimensionar o iframe sem cortar conteúdo
            num_rows = sum(len(df.index) for df in [data['val'], data['growth'], data['profitability'], data['leverage'], data['liquidity'], data['market'], df_peers])
            estimated_height = 1400 + num_rows * 42
            components.html(full_html, height=estimated_height, scrolling=True)

            st.download_button(
                label="⬇️ Descarregar Relatório Completo em HTML",
                data=full_html,
                file_name=f"Relatorio_Valuation_{symbol}_{datetime.now().strftime('%Y%m%d')}.html",
                mime="text/html",
                use_container_width=True,
            )

        except Exception as e:
            st.error(f"❌ Erro ao gerar análise para {symbol}: {e}")
else:
    st.info("👈 Introduz um ticker na barra lateral e clica em **Gerar Relatório Premium** para começar.")
