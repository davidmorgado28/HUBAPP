# ==============================================================================
# 🏢 ANÁLISE COMPREENSIVA DE REITs — Aplicação Streamlit
# Convertido a partir do notebook original (Colab, ipywidgets) para uma página
# do hub Streamlit. O visual "Executive Dashboard" (CSS customizado) foi
# mantido integralmente, renderizado via st.markdown(unsafe_allow_html=True).
# ==============================================================================

import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from theme import inject_theme, page_header

st.set_page_config(
    page_title="Análise de REITs",
    page_icon="🏢",
    layout="wide",
)

inject_theme()

# ------------------------------------------------------------------------------
# 1. CÁLCULO DE INDICADORES DE MERCADO (lógica inalterada)
# ------------------------------------------------------------------------------
@st.cache_data(show_spinner=False, ttl=3600)
def calcular_metricas_mercado(ticker_symbol, rf_rate=0.045, period="3y"):
    ticker = yf.Ticker(ticker_symbol)
    hist = ticker.history(period=period)["Close"]

    if hist.empty or len(hist) < 30:
        return {}

    sp500 = yf.Ticker("^GSPC").history(period=period)["Close"]
    returns = hist.pct_change().dropna()
    sp500_returns = sp500.pct_change().dropna()

    df_returns = pd.concat([returns, sp500_returns], axis=1, keys=["REIT", "SP500"]).dropna()

    volatility = df_returns["REIT"].std() * np.sqrt(252)
    total_return = (1 + df_returns["REIT"]).prod() - 1
    num_years = len(df_returns) / 252
    annualized_return = (1 + total_return) ** (1 / num_years) - 1 if num_years > 0 else 0

    sharpe_ratio = (annualized_return - rf_rate) / volatility if volatility != 0 else np.nan
    cov = np.cov(df_returns["REIT"], df_returns["SP500"])[0][1]
    var_sp500 = np.var(df_returns["SP500"])
    beta = cov / var_sp500 if var_sp500 != 0 else np.nan

    cumulative = (1 + df_returns["REIT"]).cumprod()
    peak = cumulative.cummax()
    drawdown = (cumulative - peak) / peak
    max_drawdown = drawdown.min()

    return {
        "Beta": beta,
        "Sharpe Ratio": sharpe_ratio,
        "Volatilidade Anualizada": volatility,
        "Max Drawdown": max_drawdown,
    }


# ------------------------------------------------------------------------------
# 2. EXTRAÇÃO E CÁLCULO HISTÓRICO DE REIT (4 ANOS) (lógica inalterada)
# ------------------------------------------------------------------------------
@st.cache_data(show_spinner=False, ttl=3600)
def extrair_historico_reit(ticker_symbol):
    reit = yf.Ticker(ticker_symbol)
    info = reit.info

    financials = reit.financials
    balance_sheet = reit.balance_sheet
    cashflow = reit.cashflow

    if financials.empty or balance_sheet.empty or cashflow.empty:
        return None, None, None

    anos = [pd.to_datetime(col).strftime("%Y") for col in financials.columns[:4]]
    num_anos = len(anos)

    price = info.get("currentPrice") or info.get("previousClose", 0)
    shares_outstanding = info.get("sharesOutstanding", 1)
    company_name = info.get("longName", ticker_symbol)
    sector = info.get("sector", "Real Estate")
    industry = info.get("industry", "REIT")

    historico = {
        "Valuation": {"Price / FFO": [], "Price / AFFO": []},
        "Rentabilidade": {"FFO Margin": [], "AFFO Margin": [], "NOI Margin (Est.)": [], "EBITDA Margin": []},
        "Dividendos": {"Dividend Yield": [], "Dividend Growth": [], "FFO Payout Ratio": [], "AFFO Payout Ratio": []},
        "Endividamento": {"Net Debt / EBITDA": [], "Debt / Equity": [], "Interest Coverage": []},
        "Crescimento": {"FFO Growth": [], "AFFO Growth": []},
    }

    ffo_list = []
    affo_list = []
    div_yield_list = []

    for i in range(num_anos):
        net_income = financials.loc["Net Income"].iloc[i] if "Net Income" in financials.index else 0
        ebitda = financials.loc["EBITDA"].iloc[i] if "EBITDA" in financials.index else (info.get("ebitda", 1))
        revenue = financials.loc["Total Revenue"].iloc[i] if "Total Revenue" in financials.index else 1

        depreciation = 0
        if "Reconciled Depreciations" in cashflow.index:
            depreciation = cashflow.loc["Reconciled Depreciations"].iloc[i]
        elif "Depreciation And Amortization" in cashflow.index:
            depreciation = cashflow.loc["Depreciation And Amortization"].iloc[i]

        capex = abs(cashflow.loc["Capital Expenditure"].iloc[i]) if "Capital Expenditure" in cashflow.index else 0
        gain_sale = financials.loc["Gain Loss On Sale Of Assets"].iloc[i] if "Gain Loss On Sale Of Assets" in financials.index else 0

        ffo = net_income + depreciation - gain_sale
        affo = ffo - capex
        ffo_per_share = ffo / shares_outstanding if shares_outstanding > 0 else 0
        affo_per_share = affo / shares_outstanding if shares_outstanding > 0 else 0

        ffo_list.append(ffo)
        affo_list.append(affo)

        op_income = financials.loc["Operating Income"].iloc[i] if "Operating Income" in financials.index else 0
        noi_est = op_income + depreciation

        total_debt = balance_sheet.loc["Total Debt"].iloc[i] if "Total Debt" in balance_sheet.index else 0
        cash = balance_sheet.loc["Cash Cash Equivalents And Short Term Investments"].iloc[i] if "Cash Cash Equivalents And Short Term Investments" in balance_sheet.index else 0
        net_debt = total_debt - cash
        total_equity = balance_sheet.loc["Stockholders Equity"].iloc[i] if "Stockholders Equity" in balance_sheet.index else 1
        interest = abs(financials.loc["Interest Expense"].iloc[i]) if "Interest Expense" in financials.index else 0

        div_paid = abs(cashflow.loc["Common Stock Dividend Paid"].iloc[i]) if "Common Stock Dividend Paid" in cashflow.index else 0
        div_y = (div_paid / shares_outstanding) / price if (price > 0 and shares_outstanding > 0) else info.get("dividendYield", 0)
        div_yield_list.append(div_y)

        historico["Valuation"]["Price / FFO"].append(price / ffo_per_share if ffo_per_share > 0 else np.nan)
        historico["Valuation"]["Price / AFFO"].append(price / affo_per_share if affo_per_share > 0 else np.nan)

        historico["Rentabilidade"]["FFO Margin"].append(ffo / revenue if revenue > 0 else np.nan)
        historico["Rentabilidade"]["AFFO Margin"].append(affo / revenue if revenue > 0 else np.nan)
        historico["Rentabilidade"]["NOI Margin (Est.)"].append(noi_est / revenue if revenue > 0 else np.nan)
        historico["Rentabilidade"]["EBITDA Margin"].append(ebitda / revenue if revenue > 0 else np.nan)

        historico["Dividendos"]["Dividend Yield"].append(div_y)
        historico["Dividendos"]["FFO Payout Ratio"].append(div_paid / ffo if ffo > 0 else np.nan)
        historico["Dividendos"]["AFFO Payout Ratio"].append(div_paid / affo if affo > 0 else np.nan)

        historico["Endividamento"]["Net Debt / EBITDA"].append(net_debt / ebitda if ebitda > 0 else np.nan)
        historico["Endividamento"]["Debt / Equity"].append(total_debt / total_equity if total_equity > 0 else np.nan)
        historico["Endividamento"]["Interest Coverage"].append(ebitda / interest if interest > 0 else np.nan)

    for i in range(num_anos):
        if i < num_anos - 1:
            ffo_g = (ffo_list[i] - ffo_list[i + 1]) / ffo_list[i + 1] if ffo_list[i + 1] > 0 else np.nan
            affo_g = (affo_list[i] - affo_list[i + 1]) / affo_list[i + 1] if affo_list[i + 1] > 0 else np.nan
            div_g = (div_yield_list[i] - div_yield_list[i + 1]) / div_yield_list[i + 1] if div_yield_list[i + 1] > 0 else np.nan
        else:
            ffo_g, affo_g, div_g = np.nan, np.nan, np.nan

        historico["Crescimento"]["FFO Growth"].append(ffo_g)
        historico["Crescimento"]["AFFO Growth"].append(affo_g)
        historico["Dividendos"]["Dividend Growth"].append(div_g)

    metricas_mercado = calcular_metricas_mercado(ticker_symbol)
    historico["Indicadores de Mercado"] = {k: [v] * num_anos for k, v in metricas_mercado.items()}

    meta = {"name": company_name, "price": price, "sector": sector, "industry": industry}

    return anos, historico, meta


# ------------------------------------------------------------------------------
# 3. COMPARATIVO DE CONCORRENTES (lógica inalterada)
# ------------------------------------------------------------------------------
def obter_resumo_concorrente(symbol):
    try:
        anos, hist, meta = extrair_historico_reit(symbol)
        if not hist:
            return None
        return {
            "Ticker": symbol,
            "Price / FFO": hist["Valuation"]["Price / FFO"][0],
            "Price / AFFO": hist["Valuation"]["Price / AFFO"][0],
            "Dividend Yield": hist["Dividendos"]["Dividend Yield"][0],
            "AFFO Payout": hist["Dividendos"]["AFFO Payout Ratio"][0],
            "Net Debt / EBITDA": hist["Endividamento"]["Net Debt / EBITDA"][0],
            "FFO Growth (YoY)": hist["Crescimento"]["FFO Growth"][0],
        }
    except Exception:
        return None


# ------------------------------------------------------------------------------
# 4. GERADOR DE PARECER (lógica inalterada)
# ------------------------------------------------------------------------------
def gerar_parecer(symbol, anos, hist):
    p_affo = hist["Valuation"]["Price / AFFO"][0]
    payout_affo = hist["Dividendos"]["AFFO Payout Ratio"][0]
    div_yield = hist["Dividendos"]["Dividend Yield"][0]
    net_debt_ebitda = hist["Endividamento"]["Net Debt / EBITDA"][0]

    parecer = "<div>"

    if pd.notna(p_affo):
        if p_affo < 15:
            val_status = "<span class='badge badge-success'>Atrativo</span>"
            val_txt = f"O REIT negoceia a um múltiplo <b>Price/AFFO bastante atrativo ({p_affo:.2f}x)</b>, abaixo das médias históricas do setor imobiliário."
        elif p_affo <= 20:
            val_status = "<span class='badge badge-info'>Fair Value</span>"
            val_txt = f"O múltiplo <b>Price/AFFO de {p_affo:.2f}x</b> reflete uma avaliação equilibrada dentro do valor justo de mercado."
        else:
            val_status = "<span class='badge badge-warning'>Prémio Elevado</span>"
            val_txt = f"O rácio <b>Price/AFFO elevado ({p_affo:.2f}x)</b> indica que o mercado exige um prémio substancial pela qualidade dos ativos ou perspetivas de crescimento."
    else:
        val_status, val_txt = "<span class='badge badge-neutral'>N/A</span>", "Múltiplo Price/AFFO indisponível."

    if pd.notna(payout_affo) and pd.notna(div_yield):
        if payout_affo < 0.85:
            div_status = "<span class='badge badge-success'>Sustentável</span>"
            div_txt = f"O rendimento por dividendo (<b>{div_yield*100:.2f}%</b>) está confortavelmente protegido por um <b>AFFO Payout Ratio de {payout_affo*100:.1f}%</b>."
        elif payout_affo <= 1.0:
            div_status = "<span class='badge badge-warning'>Acompanhar</span>"
            div_txt = f"A distribuição de dividendos (<b>{div_yield*100:.2f}%</b>) encontra-se num limite ajustado face ao caixa gerado (<b>AFFO Payout: {payout_affo*100:.1f}%</b>)."
        else:
            div_status = "<span class='badge badge-danger'>Risco Elevado</span>"
            div_txt = f"<b>Alerta de Cobertura:</b> O AFFO Payout Ratio de <b>{payout_affo*100:.1f}%</b> indica que os dividendos excedem a geração operacional orgânica de caixa."
    else:
        div_status, div_txt = "<span class='badge badge-neutral'>N/A</span>", "Métricas de dividendos indisponíveis."

    if pd.notna(net_debt_ebitda):
        if net_debt_ebitda < 6.0:
            debt_status = "<span class='badge badge-success'>Sólido</span>"
            debt_txt = f"Nível de alavancagem seguro e controlado com <b>Net Debt/EBITDA de {net_debt_ebitda:.2f}x</b>."
        else:
            debt_status = "<span class='badge badge-danger'>Alavancado</span>"
            debt_txt = f"Rácio de endividamento superior às recomendações conservadoras de mercado (<b>Net Debt/EBITDA de {net_debt_ebitda:.2f}x</b>)."
    else:
        debt_status, debt_txt = "<span class='badge badge-neutral'>N/A</span>", "Métrica de alavancagem indisponível."

    parecer += f"""
    <div class='insight-grid'>
        <div class='insight-card'>
            <div class='insight-header'>Valuation & Preço {val_status}</div>
            <p>{val_txt}</p>
        </div>
        <div class='insight-card'>
            <div class='insight-header'>Segurança dos Dividendos {div_status}</div>
            <p>{div_txt}</p>
        </div>
        <div class='insight-card'>
            <div class='insight-header'>Alavancagem & Risco {debt_status}</div>
            <p>{debt_txt}</p>
        </div>
    </div>
    </div>
    """
    return parecer


def gerar_apreciacao_peers(symbol, df_peers):
    """Gera um parágrafo de análise comparando o REIT alvo à mediana dos concorrentes."""
    if df_peers.empty or "Ticker" not in df_peers.columns or symbol not in df_peers["Ticker"].values:
        return ""

    peers_only = df_peers[df_peers["Ticker"] != symbol]
    if peers_only.empty:
        return ""

    target = df_peers[df_peers["Ticker"] == symbol].iloc[0]
    peers_median = peers_only.median(numeric_only=True)

    def safe_rel(a, b):
        if pd.isna(a) or pd.isna(b) or b == 0:
            return np.nan
        return (a / b) - 1

    p_affo_rel = safe_rel(target.get("Price / AFFO"), peers_median.get("Price / AFFO"))
    yield_target = target.get("Dividend Yield")
    yield_peers = peers_median.get("Dividend Yield")
    debt_target = target.get("Net Debt / EBITDA")
    debt_peers = peers_median.get("Net Debt / EBITDA")

    if pd.notna(p_affo_rel):
        if p_affo_rel < -0.05:
            val_badge = "<span class='badge badge-success'>Desconto vs. Pares</span>"
        elif p_affo_rel > 0.05:
            val_badge = "<span class='badge badge-warning'>Prémio vs. Pares</span>"
        else:
            val_badge = "<span class='badge badge-info'>Em Linha com os Pares</span>"
        val_txt = f"negoceia a um múltiplo <b>Price/AFFO de {target['Price / AFFO']:.2f}x</b>, uma variação de <b>{p_affo_rel*100:+.1f}%</b> face à mediana dos concorrentes ({peers_median['Price / AFFO']:.2f}x)"
    else:
        val_badge, val_txt = "<span class='badge badge-neutral'>N/A</span>", "não tem dados suficientes para comparar o múltiplo Price/AFFO com os concorrentes"

    if pd.notna(yield_target) and pd.notna(yield_peers):
        yield_diff = (yield_target - yield_peers) * 100
        yield_badge = "<span class='badge badge-success'>Acima da Média</span>" if yield_diff > 0 else "<span class='badge badge-warning'>Abaixo da Média</span>"
        yield_txt = f"O Dividend Yield de <b>{yield_target*100:.2f}%</b> compara com uma mediana de <b>{yield_peers*100:.2f}%</b> no grupo de pares ({yield_diff:+.2f} p.p.)"
    else:
        yield_badge, yield_txt = "<span class='badge badge-neutral'>N/A</span>", "Dividend Yield indisponível para comparação"

    if pd.notna(debt_target) and pd.notna(debt_peers):
        debt_badge = "<span class='badge badge-success'>Menos Alavancado</span>" if debt_target < debt_peers else "<span class='badge badge-warning'>Mais Alavancado</span>"
        debt_txt = f"O rácio Net Debt/EBITDA de <b>{debt_target:.2f}x</b> compara com a mediana de <b>{debt_peers:.2f}x</b> dos concorrentes diretos"
    else:
        debt_badge, debt_txt = "<span class='badge badge-neutral'>N/A</span>", "Net Debt/EBITDA indisponível para comparação"

    return f"""
    <p>Em termos de valuation, o <b>{symbol}</b> {val_badge} — {val_txt}.</p>
    <p>Ao nível dos dividendos, {yield_badge} — {yield_txt}.</p>
    <p>Quanto à estrutura de capital, {debt_badge} — {debt_txt}.</p>
    """


# ------------------------------------------------------------------------------
# 5. ESTILO CSS (idêntico ao original)
# ------------------------------------------------------------------------------
CSS_STYLES = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

    .reit-report-body {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        background-color: #f8fafc; color: #0f172a; margin: 0; padding: 20px;
    }
    .report-card {
        background: #ffffff; border-radius: 16px; box-shadow: 0 4px 20px -2px rgba(15,23,42,0.08);
        border: 1px solid #e2e8f0; padding: 28px; margin-bottom: 24px;
    }
    .hero-header {
        background: linear-gradient(135deg, #05070f 0%, #131a3d 100%); border-radius: 16px; padding: 28px;
        color: #ffffff; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center;
        box-shadow: 0 10px 25px -5px rgba(15,23,42,0.25);
    }
    .hero-title { font-size: 26px; font-weight: 700; margin: 0 0 4px 0; letter-spacing: -0.02em; }
    .hero-subtitle { color: #94a3b8; font-size: 13px; margin: 0; }
    .kpi-container { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 24px; }
    .kpi-card { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.02); }
    .kpi-label { font-size: 11px; font-weight: 600; text-transform: uppercase; color: #64748b; letter-spacing: 0.05em; margin-bottom: 6px; }
    .kpi-value { font-size: 22px; font-weight: 700; color: #0f172a; }
    .section-title { font-size: 17px; font-weight: 700; color: #0f172a; margin: 0 0 16px 0; display: flex; align-items: center; gap: 8px; }
    .section-title::before { content: ''; display: inline-block; width: 4px; height: 18px; background: #d4af37; border-radius: 2px; }
    .custom-table { width: 100%; border-collapse: separate; border-spacing: 0; margin-top: 12px; font-size: 13px; }
    .custom-table th { background-color: #f1f5f9; color: #334155; font-weight: 600; padding: 10px 14px; text-align: center; border-bottom: 2px solid #e2e8f0; }
    .custom-table th:first-child { text-align: left; border-top-left-radius: 8px; }
    .custom-table th:last-child { border-top-right-radius: 8px; }
    .custom-table tr.category-row th { background-color: #131a3d; color: #f6e7c1; text-align: left; font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em; padding: 8px 14px; }
    .custom-table td { padding: 10px 14px; border-bottom: 1px solid #f1f5f9; color: #334155; }
    .custom-table tr:hover td { background-color: #f8fafc; }
    .badge { display: inline-block; padding: 4px 10px; border-radius: 9999px; font-size: 11px; font-weight: 600; letter-spacing: 0.02em; }
    .badge-success { background: #dcfce7; color: #166534; }
    .badge-warning { background: #fef3c7; color: #92400e; }
    .badge-danger { background: #fee2e2; color: #991b1b; }
    .badge-info { background: #dbeafe; color: #1e40af; }
    .badge-neutral { background: #f1f5f9; color: #475569; }
    .insight-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; margin-top: 12px; }
    .insight-card { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 16px; }
    .insight-header { font-size: 13px; font-weight: 700; color: #1e293b; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; }
    .insight-card p { font-size: 12px; color: #475569; line-height: 1.5; margin: 0; }
</style>
"""


def formatar_kpis(hist):
    p_affo = hist["Valuation"]["Price / AFFO"][0]
    div_y = hist["Dividendos"]["Dividend Yield"][0]
    affo_payout = hist["Dividendos"]["AFFO Payout Ratio"][0]
    net_debt = hist["Endividamento"]["Net Debt / EBITDA"][0]

    return f"""
    <div class='kpi-container'>
        <div class='kpi-card'>
            <div class='kpi-label'>Price / AFFO</div>
            <div class='kpi-value'>{f"{p_affo:.2f}x" if pd.notna(p_affo) else "N/A"}</div>
        </div>
        <div class='kpi-card'>
            <div class='kpi-label'>Dividend Yield</div>
            <div class='kpi-value'>{f"{div_y*100:.2f}%" if pd.notna(div_y) else "N/A"}</div>
        </div>
        <div class='kpi-card'>
            <div class='kpi-label'>AFFO Payout Ratio</div>
            <div class='kpi-value'>{f"{affo_payout*100:.1f}%" if pd.notna(affo_payout) else "N/A"}</div>
        </div>
        <div class='kpi-card'>
            <div class='kpi-label'>Net Debt / EBITDA</div>
            <div class='kpi-value'>{f"{net_debt:.2f}x" if pd.notna(net_debt) else "N/A"}</div>
        </div>
    </div>
    """


def formatar_tabela_historica_pretty(anos, dados):
    headers = "".join([f"<th>{ano}</th>" for ano in anos])
    linhas = []

    for cat, metricas in dados.items():
        linhas.append(f"<tr class='category-row'><th colspan='{len(anos)+1}'>{cat}</th></tr>")
        for metrica, valores in metricas.items():
            cols = []
            for v in valores:
                if isinstance(v, float):
                    if any(kw in metrica for kw in ["Margin", "Yield", "Ratio", "Growth", "Drawdown", "Volatilidade"]):
                        cols.append(f"<td style='text-align: center;'><b>{v * 100:.2f}%</b></td>" if pd.notna(v) else "<td style='text-align: center; color: #94a3b8;'>—</td>")
                    elif any(kw in metrica for kw in ["Price", "Coverage", "Beta", "Sharpe", "Debt"]):
                        if pd.notna(v):
                            suffix = "x" if ("Price" in metrica or "Debt" in metrica or "Coverage" in metrica) else ""
                            cols.append(f"<td style='text-align: center;'>{v:.2f}{suffix}</td>")
                        else:
                            cols.append("<td style='text-align: center; color: #94a3b8;'>—</td>")
                    else:
                        cols.append(f"<td style='text-align: center;'>{v:.2f}</td>" if pd.notna(v) else "<td style='text-align: center; color: #94a3b8;'>—</td>")
                else:
                    cols.append(f"<td style='text-align: center;'>{v}</td>")

            linhas.append(f"<tr><td style='font-weight: 500;'>{metrica}</td>{''.join(cols)}</tr>")

    return f"""
    <div class='report-card'>
        <div class='section-title'>Evolução Histórica das Métricas (4 Anos Fiscais)</div>
        <table class='custom-table'>
            <thead><tr><th>Rácio / Indicador</th>{headers}</tr></thead>
            <tbody>{''.join(linhas)}</tbody>
        </table>
    </div>"""


def formatar_tabela_peers_pretty(df_peers):
    if df_peers.empty:
        return ""
    headers = "".join([f"<th>{col}</th>" for col in df_peers.columns])
    linhas = []
    for idx, row in df_peers.iterrows():
        cols = []
        for col, val in row.items():
            if col == "Ticker":
                cols.append(f"<td style='font-weight: 700; text-align: center; color: #1e293b;'>{val}</td>")
            elif "%" in col or "Yield" in col or "Payout" in col or "Growth" in col:
                cols.append(f"<td style='text-align: center;'>{val * 100:.2f}%</td>" if pd.notna(val) else "<td style='text-align: center; color: #94a3b8;'>—</td>")
            else:
                cols.append(f"<td style='text-align: center;'>{val:.2f}x</td>" if pd.notna(val) else "<td style='text-align: center; color: #94a3b8;'>—</td>")
        linhas.append(f"<tr>{''.join(cols)}</tr>")

    return f"""
    <div class='report-card'>
        <div class='section-title'>Análise Comparativa com Concorrentes</div>
        <table class='custom-table'>
            <thead><tr>{headers}</tr></thead>
            <tbody>{''.join(linhas)}</tbody>
        </table>
    </div>"""


# ------------------------------------------------------------------------------
# 6. INTERFACE
# ------------------------------------------------------------------------------
page_header(
    "🏢",
    "Análise Compreensiva de REITs",
    "Relatório executivo de REITs: FFO/AFFO, valuation, dividendos, alavancagem, risco de mercado e comparação com concorrentes.",
)

with st.sidebar:
    st.header("⚙️ Configuração")
    ticker_main = st.text_input("REIT Alvo", value="O", placeholder="ex: O")
    ticker_peers = st.text_input("Concorrentes (separados por vírgula)", value="NNN, ADC, MAIN", placeholder="ex: NNN, ADC")
    btn_executar = st.button("🚀 Gerar Relatório Executivo", type="primary", use_container_width=True)

if btn_executar:
    symbol = ticker_main.strip().upper()
    peers_list = [p.strip().upper() for p in ticker_peers.split(",") if p.strip()]

    with st.spinner(f"A obter dados e a construir o relatório para {symbol}..."):
        anos, hist, meta = extrair_historico_reit(symbol)

    if not hist:
        st.error("❌ Não foi possível carregar os dados do REIT principal.")
    else:
        kpi_html = formatar_kpis(hist)
        html_historico = formatar_tabela_historica_pretty(anos, hist)

        with st.spinner("A obter dados dos concorrentes..."):
            peers_data = []
            res_main = obter_resumo_concorrente(symbol)
            if res_main:
                peers_data.append(res_main)
            for p in peers_list:
                res_p = obter_resumo_concorrente(p)
                if res_p:
                    peers_data.append(res_p)

        df_peers = pd.DataFrame(peers_data)
        html_peers = formatar_tabela_peers_pretty(df_peers)
        html_parecer = gerar_parecer(symbol, anos, hist)
        html_apreciacao_peers = gerar_apreciacao_peers(symbol, df_peers)

        hero_html = f"""
        <div class='hero-header'>
            <div>
                <div class='hero-subtitle'>{meta['sector']} • {meta['industry']}</div>
                <div class='hero-title'>{meta['name']} ({symbol})</div>
            </div>
            <div style='text-align: right;'>
                <div style='font-size: 12px; color: #94a3b8;'>Cotação Atual</div>
                <div style='font-size: 24px; font-weight: 700;'>${meta['price']:.2f}</div>
            </div>
        </div>
        """

        parecer_card = f"""
        <div class='report-card'>
            <div class='section-title'>Apreciação Qualitativa Automatizada</div>
            {html_parecer}
        </div>
        """

        peer_appreciation_card = ""
        if html_apreciacao_peers:
            peer_appreciation_card = f"""
            <div class='report-card'>
                <div class='section-title'>Apreciação Relativa & Peer Benchmark</div>
                {html_apreciacao_peers}
            </div>
            """

        body_html = f"<div class='reit-report-body'>{hero_html}{kpi_html}{parecer_card}{html_historico}{html_peers}{peer_appreciation_card}</div>"

        doc_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Relatório Executivo REIT - {symbol}</title>
            {CSS_STYLES}
        </head>
        <body class="reit-report-body">
            {hero_html}
            {kpi_html}
            {parecer_card}
            {html_historico}
            {html_peers}
            {peer_appreciation_card}
        </body>
        </html>
        """

        # Número de linhas de tabela aproximado, para dimensionar o iframe sem cortar conteúdo
        num_rows = sum(len(m) for m in hist.values()) + len(df_peers.index)
        estimated_height = 1650 + num_rows * 42
        components.html(doc_html, height=estimated_height, scrolling=True)

        st.download_button(
            label="📥 Descarregar Relatório Executivo (HTML)",
            data=doc_html,
            file_name=f"Relatorio_Executivo_{symbol}.html",
            mime="text/html",
            use_container_width=True,
        )
else:
    st.info("👈 Introduz o ticker do REIT alvo e os concorrentes na barra lateral, depois clica em **Gerar Relatório Executivo**.")
