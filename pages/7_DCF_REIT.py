# ==============================================================================
# 🏢 MODELO DCF PARA REITS (AFFO) — Aplicação Streamlit
# Segue o mesmo template do Modelo DCF (FCFF): sidebar de ticker, CAPM/ERP
# dinâmico calculado a partir do S&P500, pressupostos editáveis por cenário
# e relatório HTML estilizado (dark/cards) para download.
#
# Diferença principal face ao modelo FCFF: o motor de valorização desconta
# AFFO por ação (fluxo de caixa já ao nível do acionista) em vez de FCFF ao
# nível da empresa — por isso não há bridge Enterprise Value -> Equity Value
# via caixa/dívida, e o custo de desconto é o Ke (CAPM), não o WACC.
# ==============================================================================

import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from theme import inject_theme, page_header

st.set_page_config(
    page_title="DCF para REITs",
    page_icon="🏢",
    layout="wide",
)

inject_theme()

page_header(
    "🏢",
    "Modelo DCF para REITs (AFFO)",
    "Valuação por Adjusted Funds From Operations em 3 cenários (Base / Otimista / Pessimista), "
    "com Ke calculado dinamicamente via CAPM e relatório HTML estilizado para download.",
)

SCENARIOS = ["Base", "Otimista", "Pessimista"]
YEAR_COLS = [f"Ano {i}" for i in range(1, 6)]

# ------------------------------------------------------------------------------
# 1. CAPM DINÂMICO (idêntico ao Modelo DCF — mesmas funções, mesma lógica)
# ------------------------------------------------------------------------------
@st.cache_data(show_spinner=False, ttl=3600)
def get_risk_free_rate():
    try:
        tnx = yf.Ticker("^TNX")
        hist = tnx.history(period="5d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1]) / 100.0
    except Exception:
        pass
    return 0.0425


@st.cache_data(show_spinner=False, ttl=3600)
def get_sp500_historical_return(years=20):
    try:
        sp500 = yf.Ticker("^GSPC")
        hist = sp500.history(period=f"{years}y")
        if not hist.empty:
            start_price = hist["Close"].iloc[0]
            end_price = hist["Close"].iloc[-1]
            num_years = (hist.index[-1] - hist.index[0]).days / 365.25
            return (end_price / start_price) ** (1 / num_years) - 1.0
    except Exception:
        pass
    return 0.098


def calculate_capm_reit(ticker_obj, rf_rate):
    """
    Ke = Rf + Beta * ERP_dinamico, onde ERP_dinamico = max(3.5%, Rm_S&P500 - Rf).
    Não há componente de dívida — AFFO/ação é já um fluxo de caixa ao nível
    do acionista, por isso descontamos a Ke (custo de capital próprio), não
    ao WACC.
    """
    sp500_return = get_sp500_historical_return(years=20)
    erp_dynamic = max(0.035, sp500_return - rf_rate)

    info = ticker_obj.info
    beta = info.get("beta", 1.0) or 1.0
    ke = rf_rate + (beta * erp_dynamic)

    return ke, beta, erp_dynamic, sp500_return


# ------------------------------------------------------------------------------
# 2. FÓRMULA COMPLETA DE FFO / AFFO
# ------------------------------------------------------------------------------
def _get_row(df, candidates):
    for name in candidates:
        if name in df.index:
            return df.loc[name]
    return None


@st.cache_data(show_spinner=False, ttl=3600)
def extract_reit_financial_data(ticker_symbol):
    """
    FFO (definição NAREIT, aproximada com os dados disponíveis via yfinance):
        FFO = Resultado Líquido
            + Depreciação & Amortização
            + Imparidades de ativos depreciáveis
            +/- Ajuste de Ganhos/Perdas em vendas de investimentos/imóveis
              (a cashflow statement já traz este ajuste com o sinal correto
              para remover o efeito não-recorrente do resultado líquido)

    AFFO = FFO
            + Compensação em ações (não-cash)
            + Amortização de custos de financiamento diferidos (não-cash)
            - CapEx de manutenção (recorrente)
            - Ajuste de "straight-line rent" (não disponível via yfinance —
              assumido como 0, com aviso explícito ao utilizador)

    Sempre que uma linha não existe no yfinance para este ticker, o
    respetivo componente é tratado como 0 e assinalado na UI, em vez de
    a aplicação falhar silenciosamente.
    """
    ticker = yf.Ticker(ticker_symbol)
    fin = ticker.financials
    cf = ticker.cashflow
    info = ticker.info

    if fin is None or fin.empty or cf is None or cf.empty:
        raise ValueError("Não foi possível obter dados financeiros para este Ticker.")

    # Interseção de datas entre as duas demonstrações, para evitar KeyErrors
    common_dates = sorted(set(fin.columns) & set(cf.columns))[-5:]
    if len(common_dates) < 2:
        raise ValueError("Histórico financeiro insuficiente (menos de 2 anos em comum).")

    net_income_row = _get_row(fin, ["Net Income", "Net Income Common Stockholders"])
    da_row = _get_row(cf, ["Depreciation And Amortization", "Depreciation Amortization Depletion"])
    impairment_row = _get_row(cf, ["Impairment Of Capital Assets", "Asset Impairment Charge"])
    gain_loss_row = _get_row(
        cf, ["Gain Loss On Investment Securities", "Net Investment Purchase And Sale", "Gain On Sale Of Business"]
    )
    sbc_row = _get_row(cf, ["Stock Based Compensation"])
    financing_amort_row = _get_row(
        cf, ["Amortization Of Financing Costs", "Amortization Of Debt Discount Premium", "Other Amortization"]
    )
    maintenance_capex_row = _get_row(cf, ["Purchase Of PPE"])
    total_capex_row = _get_row(cf, ["Capital Expenditure", "Capital Expenditures"])
    diluted_shares_row = _get_row(fin, ["Diluted Average Shares", "Basic Average Shares"])

    if net_income_row is None or da_row is None or diluted_shares_row is None:
        raise ValueError(
            "Faltam campos essenciais (Resultado Líquido, D&A ou Ações Diluídas) "
            "para calcular o FFO/AFFO deste ticker."
        )

    capex_is_total_fallback = maintenance_capex_row is None and total_capex_row is not None
    capex_row = maintenance_capex_row if maintenance_capex_row is not None else total_capex_row

    rows_out = {
        "Resultado Líquido ($M)": [],
        "+ D&A ($M)": [],
        "+ Imparidades ($M)": [],
        "+/- Ganhos/Perdas em Vendas ($M)": [],
        "= FFO ($M)": [],
        "+ Comp. em Ações (SBC) ($M)": [],
        "+ Amort. Custos Financiamento ($M)": [],
        "- CapEx de Manutenção ($M)": [],
        "= AFFO ($M)": [],
    }
    shares_out = []
    affo_per_share_out = []
    years_used = []

    for date in common_dates:
        ni = net_income_row.get(date, np.nan)
        d_a = da_row.get(date, np.nan)
        shares = diluted_shares_row.get(date, np.nan)

        if pd.isna(ni) or pd.isna(d_a) or pd.isna(shares) or shares == 0:
            continue

        impairment = impairment_row.get(date, 0.0) if impairment_row is not None else 0.0
        impairment = 0.0 if pd.isna(impairment) else abs(impairment)

        gain_loss_adj = gain_loss_row.get(date, 0.0) if gain_loss_row is not None else 0.0
        gain_loss_adj = 0.0 if pd.isna(gain_loss_adj) else gain_loss_adj

        sbc = sbc_row.get(date, 0.0) if sbc_row is not None else 0.0
        sbc = 0.0 if pd.isna(sbc) else sbc

        fin_amort = financing_amort_row.get(date, 0.0) if financing_amort_row is not None else 0.0
        fin_amort = 0.0 if pd.isna(fin_amort) else fin_amort

        maint_capex = capex_row.get(date, 0.0) if capex_row is not None else 0.0
        maint_capex = 0.0 if pd.isna(maint_capex) else abs(maint_capex)

        ffo = ni + d_a + impairment + gain_loss_adj
        affo = ffo + sbc + fin_amort - maint_capex
        affo_per_share = affo / shares

        years_used.append(date)
        rows_out["Resultado Líquido ($M)"].append(ni / 1e6)
        rows_out["+ D&A ($M)"].append(d_a / 1e6)
        rows_out["+ Imparidades ($M)"].append(impairment / 1e6)
        rows_out["+/- Ganhos/Perdas em Vendas ($M)"].append(gain_loss_adj / 1e6)
        rows_out["= FFO ($M)"].append(ffo / 1e6)
        rows_out["+ Comp. em Ações (SBC) ($M)"].append(sbc / 1e6)
        rows_out["+ Amort. Custos Financiamento ($M)"].append(fin_amort / 1e6)
        rows_out["- CapEx de Manutenção ($M)"].append(-maint_capex / 1e6)
        rows_out["= AFFO ($M)"].append(affo / 1e6)
        shares_out.append(shares / 1e6)
        affo_per_share_out.append(affo_per_share)

    if len(years_used) < 2:
        raise ValueError("Dados insuficientes para calcular pelo menos 2 anos de AFFO/ação.")

    col_labels = [pd.Timestamp(d).year for d in years_used]
    breakdown_df = pd.DataFrame(rows_out, index=col_labels).T

    affo_per_share_series = pd.Series(affo_per_share_out, index=col_labels)
    growth_series = affo_per_share_series.pct_change().fillna(0) * 100

    affo_share_df = pd.DataFrame(
        {
            "AFFO / Ação ($)": affo_per_share_series,
            "Crescimento AFFO/Ação (%)": growth_series,
            "Ações Diluídas (M)": pd.Series(shares_out, index=col_labels),
        }
    ).T

    rf_rate = get_risk_free_rate()
    ke_base, beta, erp_dynamic, sp500_return = calculate_capm_reit(ticker, rf_rate)

    current_price = info.get("currentPrice") or info.get("regularMarketPrice") or 0.0
    company_name = info.get("longName", ticker_symbol.upper())

    last_growth = growth_series.iloc[-1] if len(growth_series) else 2.0

    return {
        "ticker": ticker_symbol.upper(),
        "company_name": company_name,
        "breakdown_df": breakdown_df,
        "affo_share_df": affo_share_df,
        "current_price": current_price,
        "last_affo_per_share": affo_per_share_series.iloc[-1],
        "last_growth_pct": max(-20.0, min(30.0, last_growth)),
        "capex_is_total_fallback": capex_is_total_fallback,
        "missing_components": {
            "Imparidades": impairment_row is None,
            "Ganhos/Perdas em Vendas": gain_loss_row is None,
            "SBC": sbc_row is None,
            "Amort. Custos Financiamento": financing_amort_row is None,
            "CapEx de Manutenção (separado do CapEx total)": maintenance_capex_row is None,
        },
        "rf_rate": rf_rate,
        "beta": beta,
        "erp_dynamic": erp_dynamic,
        "sp500_return": sp500_return,
        "ke_base": ke_base,
    }


# ------------------------------------------------------------------------------
# 3. GERADOR DO DASHBOARD HTML ESTILIZADO (mesmo layout dark/cards do modelo FCFF)
# ------------------------------------------------------------------------------
def generate_styled_html_report_reit(data, results_summary, tables_dict):
    ticker = data["ticker"]
    company = data["company_name"]
    price = data["current_price"]

    cards_html = ""
    for r in results_summary:
        scen = r["Cenário"]
        target_p = r["Implied Share Price ($)"]
        up = r["Upside / Downside (%)"]
        up_v = float(up.replace("%", "").replace("+", ""))
        color = "#10B981" if up_v >= 0 else "#EF4444"

        cards_html += f"""
        <div class="card">
            <div class="card-tag">{scen.upper()}</div>
            <div class="card-title">Implied Target Price</div>
            <div class="card-value">{target_p}</div>
            <div class="card-sub" style="color: {color};">
                <span>{up}</span> vs Preço Atual (${price:.2f})
            </div>
            <div class="card-details">
                <div>Ke: <b>{r['Ke']}</b></div>
                <div>TGR: <b>{r['TGR']}</b></div>
                <div>PV AFFO: <b>{r['PV AFFO Sum ($)']}</b></div>
            </div>
        </div>
        """

    projections_tables_html = ""
    for scen in SCENARIOS:
        df = tables_dict[scen]
        table_rows = ""
        for idx, row in df.iterrows():
            table_rows += f"<tr><td class='row-label'>{idx}</td>"
            for val in row:
                table_rows += f"<td>${val:,.2f}</td>"
            table_rows += "</tr>"

        projections_tables_html += f"""
        <div class="section-card">
            <h3 class="section-subtitle">Projeções de AFFO/Ação ($) — Cenário {scen}</h3>
            <table class="custom-table">
                <thead>
                    <tr>
                        <th>Métrica</th>
                        <th>Ano 1</th><th>Ano 2</th><th>Ano 3</th><th>Ano 4</th><th>Ano 5</th>
                    </tr>
                </thead>
                <tbody>{table_rows}</tbody>
            </table>
        </div>
        """

    hist_abs_rows = ""
    for idx, row in data["breakdown_df"].iterrows():
        hist_abs_rows += f"<tr><td class='row-label'>{idx}</td>" + "".join([f"<td>${v:,.2f}</td>" for v in row]) + "</tr>"
    hist_abs_years = list(data["breakdown_df"].columns)

    hist_share_rows = ""
    for idx, row in data["affo_share_df"].iterrows():
        if "%" in idx:
            hist_share_rows += f"<tr><td class='row-label'>{idx}</td>" + "".join([f"<td>{v:.2f}%</td>" for v in row]) + "</tr>"
        elif "Ações" in idx:
            hist_share_rows += f"<tr><td class='row-label'>{idx}</td>" + "".join([f"<td>{v:,.1f}M</td>" for v in row]) + "</tr>"
        else:
            hist_share_rows += f"<tr><td class='row-label'>{idx}</td>" + "".join([f"<td>${v:.4f}</td>" for v in row]) + "</tr>"
    hist_share_years = list(data["affo_share_df"].columns)

    html_template = f"""
    <!DOCTYPE html>
    <html lang="pt">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>DCF REIT (AFFO) — {company} ({ticker})</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap" rel="stylesheet">
        <style>
            :root {{
                --bg-primary: #05070F; --bg-card: #0D1230; --text-main: #F5F5F0;
                --text-muted: #A8A8B8; --accent-blue: #D4AF37; --accent-green: #10B981;
                --accent-red: #EF4444; --border-color: #2A2F52;
            }}
            body {{ font-family: 'Inter', sans-serif; background-color: var(--bg-primary); color: var(--text-main);
                margin: 0; padding: 40px 20px; display: flex; justify-content: center; }}
            .container {{ max-width: 1200px; width: 100%; }}
            .header {{ display: flex; justify-content: space-between; align-items: center;
                border-bottom: 2px solid var(--border-color); padding-bottom: 20px; margin-bottom: 30px; }}
            .header h1 {{ font-size: 28px; font-weight: 800; margin: 0; color: #FFFFFF; }}
            .header .ticker-badge {{ background: rgba(212, 175, 55, 0.15); color: var(--accent-blue);
                padding: 4px 12px; border-radius: 6px; font-size: 14px; font-weight: 700; }}
            .header .price-tag {{ font-size: 16px; color: var(--text-muted); }}
            .header .price-tag b {{ color: #FFFFFF; font-size: 20px; }}
            .cards-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
                gap: 20px; margin-bottom: 35px; }}
            .card {{ background-color: var(--bg-card); border: 1px solid var(--border-color); border-radius: 12px;
                padding: 24px; position: relative; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.3); }}
            .card-tag {{ position: absolute; top: 20px; right: 20px; font-size: 11px; font-weight: 800;
                background: #334155; color: var(--accent-blue); padding: 2px 8px; border-radius: 4px; letter-spacing: 0.5px; }}
            .card-title {{ font-size: 13px; color: var(--text-muted); text-transform: uppercase;
                letter-spacing: 0.5px; margin-bottom: 8px; }}
            .card-value {{ font-size: 34px; font-weight: 800; color: #FFFFFF; margin-bottom: 6px; }}
            .card-sub {{ font-size: 13px; font-weight: 600; margin-bottom: 18px; }}
            .card-details {{ border-top: 1px solid var(--border-color); padding-top: 12px; display: flex;
                justify-content: space-between; font-size: 12px; color: var(--text-muted); }}
            .card-details b {{ color: var(--text-main); }}
            .section-card {{ background-color: var(--bg-card); border: 1px solid var(--border-color);
                border-radius: 12px; padding: 24px; margin-bottom: 25px; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.2); }}
            .section-title {{ font-size: 18px; font-weight: 700; margin-top: 0; margin-bottom: 15px; color: var(--accent-blue); }}
            .section-subtitle {{ font-size: 15px; font-weight: 600; margin-top: 0; margin-bottom: 15px; color: #FFFFFF; }}
            .custom-table {{ width: 100%; border-collapse: collapse; text-align: right; font-size: 13px; }}
            .custom-table th {{ background-color: #0F172A; color: var(--text-muted); font-weight: 600;
                padding: 12px 16px; border-bottom: 2px solid var(--border-color); text-transform: uppercase;
                font-size: 11px; letter-spacing: 0.5px; }}
            .custom-table th:first-child {{ text-align: left; }}
            .custom-table td {{ padding: 12px 16px; border-bottom: 1px solid var(--border-color); color: var(--text-main); }}
            .custom-table tr:hover {{ background-color: rgba(255,255,255,0.03); }}
            .row-label {{ text-align: left; font-weight: 600; color: #FFFFFF; }}
            .footer {{ text-align: center; color: var(--text-muted); font-size: 12px; margin-top: 40px;
                padding-top: 20px; border-top: 1px solid var(--border-color); }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div>
                    <h1>{company} <span class="ticker-badge">{ticker}</span></h1>
                    <div style="color: var(--text-muted); font-size: 13px; margin-top: 4px;">Relatório de Valuação REIT por AFFO/Ação Descontado</div>
                </div>
                <div class="price-tag">Preço Atual de Mercado: <b>${price:.2f}</b></div>
            </div>
            <div class="cards-grid">{cards_html}</div>
            <h2 class="section-title">Projeções de AFFO/Ação por Cenário (5 Anos)</h2>
            {projections_tables_html}
            <h2 class="section-title">Contextualização Histórica</h2>
            <div class="section-card">
                <h3 class="section-subtitle">Waterfall FFO → AFFO ($M)</h3>
                <table class="custom-table">
                    <thead><tr><th>Componente</th>{''.join([f'<th>{y}</th>' for y in hist_abs_years])}</tr></thead>
                    <tbody>{hist_abs_rows}</tbody>
                </table>
            </div>
            <div class="section-card">
                <h3 class="section-subtitle">AFFO por Ação e Crescimento Histórico</h3>
                <table class="custom-table">
                    <thead><tr><th>Métrica</th>{''.join([f'<th>{y}</th>' for y in hist_share_years])}</tr></thead>
                    <tbody>{hist_share_rows}</tbody>
                </table>
            </div>
            <div class="footer">Gerado por Modelo DCF para REITs (AFFO) • Dados via Yahoo Finance • Apresentação de Dados em $M / $ por Ação</div>
        </div>
    </body>
    </html>
    """
    return html_template


# ------------------------------------------------------------------------------
# 4. MOTOR DE CÁLCULO DO DCF (AFFO/AÇÃO)
# ------------------------------------------------------------------------------
def run_reit_dcf_model(reit_data, growth_grid, ke_vals, tgr_vals):
    results_summary = []
    tables_dict = {}
    last_affo = reit_data["last_affo_per_share"]

    for scen in SCENARIOS:
        growth = [growth_grid.loc[scen, YEAR_COLS[i]] / 100.0 for i in range(5)]
        ke = ke_vals[scen] / 100.0
        tgr = tgr_vals[scen] / 100.0

        proj_affo = []
        curr_affo = last_affo
        for i in range(5):
            curr_affo *= (1 + growth[i])
            proj_affo.append(curr_affo)

        discount_factors = [(1 + ke) ** (i + 1) for i in range(5)]
        pv_affo = [proj_affo[i] / discount_factors[i] for i in range(5)]
        sum_pv_affo = sum(pv_affo)

        terminal_value = (proj_affo[-1] * (1 + tgr)) / (ke - tgr) if ke > tgr else 0
        pv_terminal_value = terminal_value / ((1 + ke) ** 5)

        implied_price = sum_pv_affo + pv_terminal_value
        upside = ((implied_price / reit_data["current_price"]) - 1) * 100 if reit_data["current_price"] > 0 else 0

        results_summary.append({
            "Cenário": scen,
            "Ke": f"{ke * 100:.2f}%",
            "TGR": f"{tgr * 100:.2f}%",
            "PV AFFO Sum ($)": f"${sum_pv_affo:,.2f}",
            "PV Terminal Value ($)": f"${pv_terminal_value:,.2f}",
            "Implied Share Price ($)": f"${implied_price:.2f}",
            "Upside / Downside (%)": f"{upside:+.2f}%",
        })

        proj_df = pd.DataFrame(
            {YEAR_COLS[i]: [proj_affo[i], pv_affo[i]] for i in range(5)},
            index=["AFFO/Ação Projetado ($)", "PV do AFFO/Ação ($)"],
        )
        tables_dict[scen] = proj_df

    return results_summary, tables_dict


# ------------------------------------------------------------------------------
# 5. INTERFACE
# ------------------------------------------------------------------------------
def default_grid(default_val_pct):
    return pd.DataFrame(
        [[round(default_val_pct, 2)] * 5, [round(default_val_pct + 3, 2)] * 5, [round(default_val_pct - 3, 2)] * 5],
        index=SCENARIOS,
        columns=YEAR_COLS,
    )


with st.sidebar:
    st.header("⚙️ REIT")
    ticker_input = st.text_input("Ticker", value="O", placeholder="Ex: O, VICI, SPG")
    fetch_button = st.button("📥 Carregar Dados (AFFO)", type="primary", use_container_width=True)

if fetch_button:
    with st.spinner(f"A obter dados financeiros para {ticker_input.upper()}..."):
        try:
            st.session_state["reit_dcf_data"] = extract_reit_financial_data(ticker_input)
            for key in list(st.session_state.keys()):
                if key.startswith("grid_") or key.startswith("ke_") or key.startswith("tgr_"):
                    del st.session_state[key]
        except Exception as e:
            st.session_state.pop("reit_dcf_data", None)
            st.error(f"Erro ao processar o ticker {ticker_input}: {e}")

reit_data = st.session_state.get("reit_dcf_data")

if not reit_data:
    st.info("👈 Introduz o ticker de um REIT na barra lateral e clica em **Carregar Dados** para começar.")
else:
    st.subheader(f"{reit_data['company_name']} ({reit_data['ticker']}) — Preço Atual: ${reit_data['current_price']:.2f}")

    missing = [k for k, v in reit_data["missing_components"].items() if v]
    if missing:
        st.warning(
            "Componentes não encontrados na Yahoo Finance para este ticker (assumidos como 0 ou "
            f"usando o CapEx total como proxy): {', '.join(missing)}. O AFFO calculado é uma "
            "aproximação — a linha de ajuste 'straight-line rent' também não está disponível via yfinance."
        )
    if reit_data["capex_is_total_fallback"]:
        st.caption(
            "⚠️ Este ticker não reporta CapEx de manutenção separado do CapEx total na Yahoo Finance — "
            "foi usado o CapEx total como proxy, o que pode subestimar o AFFO se incluir capex de crescimento."
        )

    with st.expander("Ver Fórmula Completa de FFO/AFFO e Histórico Detalhado"):
        st.markdown("**Waterfall FFO → AFFO ($M)**")
        st.dataframe(reit_data["breakdown_df"].style.format("${:,.2f}M"), use_container_width=True)
        st.markdown("**AFFO por Ação e Crescimento Histórico**")
        affo_share_display = reit_data["affo_share_df"].astype(object)
        affo_share_display.loc["AFFO / Ação ($)"] = affo_share_display.loc["AFFO / Ação ($)"].map(lambda v: f"${v:.4f}")
        affo_share_display.loc["Crescimento AFFO/Ação (%)"] = affo_share_display.loc["Crescimento AFFO/Ação (%)"].map(lambda v: f"{v:.2f}%")
        affo_share_display.loc["Ações Diluídas (M)"] = affo_share_display.loc["Ações Diluídas (M)"].map(lambda v: f"{v:,.1f}M")
        st.dataframe(affo_share_display, use_container_width=True)

    st.markdown("### 📊 Pressupostos de Crescimento do AFFO/Ação (editável por cenário e ano)")
    grid_key = f"grid_AFFO_Growth_{reit_data['ticker']}"
    base_growth_df = default_grid(reit_data["last_growth_pct"])
    growth_grid = st.data_editor(
        base_growth_df,
        use_container_width=True,
        key=grid_key,
        column_config={col: st.column_config.NumberColumn(f"{col} (%)", format="%.2f") for col in YEAR_COLS},
    )

    st.markdown("### 💵 Custo de Capital Próprio (Ke — CAPM Calculado Dinamicamente)")
    st.caption(
        f"Rf (10Y Treasury): {reit_data['rf_rate']*100:.2f}% · "
        f"Beta: {reit_data['beta']:.3f} · "
        f"Rm (CAGR S&P500, 20 anos): {reit_data['sp500_return']*100:.2f}% · "
        f"ERP dinâmico (Rm − Rf, mín. 3,5%): {reit_data['erp_dynamic']*100:.2f}%"
    )
    ke_base_pct = reit_data["ke_base"] * 100
    col1, col2, col3 = st.columns(3)
    ke_vals = {}
    with col1:
        ke_vals["Base"] = st.number_input("Ke Base (%)", value=round(ke_base_pct, 2), step=0.1, key=f"ke_base_{reit_data['ticker']}")
    with col2:
        ke_vals["Otimista"] = st.number_input("Ke Otimista (%)", value=round(ke_base_pct - 0.5, 2), step=0.1, key=f"ke_opt_{reit_data['ticker']}")
    with col3:
        ke_vals["Pessimista"] = st.number_input("Ke Pessimista (%)", value=round(ke_base_pct + 0.5, 2), step=0.1, key=f"ke_pess_{reit_data['ticker']}")

    st.markdown("### 📈 Terminal Growth Rate (TGR)")
    col4, col5, col6 = st.columns(3)
    tgr_vals = {}
    with col4:
        tgr_vals["Base"] = st.number_input("TGR Base (%)", value=2.5, step=0.1, key=f"tgr_base_{reit_data['ticker']}")
    with col5:
        tgr_vals["Otimista"] = st.number_input("TGR Otimista (%)", value=3.0, step=0.1, key=f"tgr_opt_{reit_data['ticker']}")
    with col6:
        tgr_vals["Pessimista"] = st.number_input("TGR Pessimista (%)", value=2.0, step=0.1, key=f"tgr_pess_{reit_data['ticker']}")

    calc_button = st.button("🧮 Gerar Análise & Relatório HTML", type="primary", use_container_width=True)

    if calc_button:
        results_summary, tables_dict = run_reit_dcf_model(reit_data, growth_grid, ke_vals, tgr_vals)
        html_report = generate_styled_html_report_reit(reit_data, results_summary, tables_dict)

        st.markdown(f"### ✅ Valuação Concluída para {reit_data['company_name']}")
        st.dataframe(pd.DataFrame(results_summary), use_container_width=True, hide_index=True)

        for scen in SCENARIOS:
            with st.expander(f"Projeções de AFFO/Ação — Cenário {scen}"):
                st.dataframe(tables_dict[scen].style.format("${:,.2f}"), use_container_width=True)

        st.download_button(
            label="⬇️ Descarregar Relatório HTML Estilizado",
            data=html_report,
            file_name=f"DCF_REIT_AFFO_{reit_data['ticker']}.html",
            mime="text/html",
            use_container_width=True,
        )
