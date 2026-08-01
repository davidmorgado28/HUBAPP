# ==============================================================================
# 💰 MODELO DCF & DASHBOARD — Aplicação Streamlit
# Convertido a partir do notebook original (Colab, ipywidgets) para uma página
# do hub Streamlit. As grelhas 5 (anos) x 3 (cenários) de pressupostos passam
# a ser tabelas editáveis (st.data_editor).
# ==============================================================================

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Modelo DCF",
    page_icon="💰",
    layout="wide",
)

st.title("💰 Modelo DCF & Gerador de Dashboard")
st.caption(
    "Valuação por Discounted Cash Flow em 3 cenários (Base / Otimista / Pessimista), "
    "com WACC calculado dinamicamente e relatório HTML estilizado para download."
)

SCENARIOS = ["Base", "Otimista", "Pessimista"]
YEAR_COLS = [f"Ano {i}" for i in range(1, 6)]

# ------------------------------------------------------------------------------
# 1. FUNÇÕES AUXILIARES DE FINANÇAS CORPORATIVAS (lógica inalterada)
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


def calculate_wacc(ticker_obj, rf_rate):
    sp500_return = get_sp500_historical_return(years=20)
    erp_dynamic = max(0.035, sp500_return - rf_rate)

    info = ticker_obj.info
    market_cap = info.get("marketCap", 1e10)
    total_debt = info.get("totalDebt", 0.0)
    total_value = market_cap + total_debt

    weight_equity = market_cap / total_value if total_value > 0 else 0.8
    weight_debt = total_debt / total_value if total_value > 0 else 0.2

    beta = info.get("beta", 1.0) or 1.0
    cost_of_equity = rf_rate + (beta * erp_dynamic)

    financials = ticker_obj.financials
    interest_expense = 0.0
    if financials is not None and not financials.empty:
        for idx in ["Interest Expense", "Interest Expense Non Operating"]:
            if idx in financials.index:
                interest_expense = abs(financials.loc[idx].iloc[0])
                break

    cost_of_debt = (interest_expense / total_debt) if total_debt > 0 and interest_expense > 0 else rf_rate + 0.015

    if financials is not None and not financials.empty and "Tax Provision" in financials.index and "Pretax Income" in financials.index:
        tax = financials.loc["Tax Provision"].iloc[0]
        pretax = financials.loc["Pretax Income"].iloc[0]
        tax_rate = max(0.15, min(0.35, tax / pretax)) if pretax > 0 else 0.21
    else:
        tax_rate = 0.21

    wacc_base = (weight_equity * cost_of_equity) + (weight_debt * cost_of_debt * (1 - tax_rate))
    return wacc_base, tax_rate


@st.cache_data(show_spinner=False, ttl=3600)
def extract_financial_data(ticker_symbol):
    ticker = yf.Ticker(ticker_symbol)
    fin = ticker.financials
    bs = ticker.balance_sheet
    cf = ticker.cashflow

    if fin is None or fin.empty or cf is None or cf.empty:
        raise ValueError("Não foi possível obter dados financeiros para este Ticker.")

    def safe_get(df, keys):
        for k in keys:
            if k in df.index:
                return df.loc[k].iloc[:5][::-1]
        return pd.Series([0] * 5)

    revenue = safe_get(fin, ["Total Revenue", "Revenue"])
    ebit = safe_get(fin, ["EBIT", "Operating Income"])
    depreciation = safe_get(cf, ["Depreciation And Amortization", "Depreciation Amortization Depletion"])
    capex = safe_get(cf, ["Capital Expenditure", "Capital Expenditures"]).abs()

    tax_provision = safe_get(fin, ["Tax Provision"])
    pretax_inc = safe_get(fin, ["Pretax Income"])
    tax_rates = (tax_provision / pretax_inc).apply(lambda x: max(0.10, min(0.40, x)) if not np.isnan(x) and x > 0 else 0.21)

    nwc_change = safe_get(cf, ["Change In Working Capital", "Changes In Cash"])

    historical_df = pd.DataFrame(
        {
            "Revenue ($B)": revenue / 1e9,
            "EBIT ($B)": ebit / 1e9,
            "Depr & Amort ($B)": depreciation / 1e9,
            "CapEx ($B)": capex / 1e9,
            "Change in NWC ($B)": nwc_change / 1e9,
        }
    ).fillna(0)

    rev_growth_hist = revenue.pct_change().fillna(0) * 100
    ebit_margin_hist = (ebit / revenue).fillna(0) * 100
    tax_rate_hist = tax_rates * 100
    depr_pct_hist = (depreciation / revenue).fillna(0) * 100
    capex_pct_hist = (capex / revenue).fillna(0) * 100
    nwc_pct_hist = (nwc_change / revenue).fillna(0) * 100

    historical_ratios_df = pd.DataFrame(
        {
            "Revenue Growth (%)": rev_growth_hist,
            "EBIT Margin (%)": ebit_margin_hist,
            "Tax Rate (%)": tax_rate_hist,
            "Depr (% Rev)": depr_pct_hist,
            "CapEx (% Rev)": capex_pct_hist,
            "Change in NWC (% Rev)": nwc_pct_hist,
        }
    ).fillna(0)

    rf_rate = get_risk_free_rate()
    wacc_base, current_tax_rate = calculate_wacc(ticker, rf_rate)
    current_price = ticker.info.get("currentPrice") or ticker.info.get("regularMarketPrice") or 0.0
    shares_outstanding = ticker.info.get("sharesOutstanding", 1)
    total_debt = ticker.info.get("totalDebt", 0)
    cash = ticker.info.get("totalCash", 0)
    company_name = ticker.info.get("longName", ticker_symbol.upper())

    return {
        "ticker": ticker_symbol.upper(),
        "company_name": company_name,
        "historical_df": historical_df,
        "historical_ratios_df": historical_ratios_df,
        "wacc_base": wacc_base,
        "current_price": current_price,
        "shares_outstanding": shares_outstanding,
        "total_debt": total_debt,
        "cash": cash,
        "last_revenue": revenue.iloc[-1] if not revenue.empty else 0,
        "last_ebit": ebit.iloc[-1] if not ebit.empty else 0,
        "last_ratios": historical_ratios_df.iloc[-1],
    }


# ------------------------------------------------------------------------------
# 2. GERADOR DO DASHBOARD HTML ESTETIZADO (lógica inalterada)
# ------------------------------------------------------------------------------
def generate_styled_html_report(data, results_summary, tables_dict):
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
                <div>WACC: <b>{r['WACC']}</b></div>
                <div>TGR: <b>{r['TGR']}</b></div>
                <div>EV: <b>{r['Enterprise Value ($B)']}</b></div>
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
                table_rows += f"<td>${val:,.2f}B</td>"
            table_rows += "</tr>"

        projections_tables_html += f"""
        <div class="section-card">
            <h3 class="section-subtitle">Projeções de Fluxo de Caixa ($B) — Cenário {scen}</h3>
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
    for idx, row in data["historical_df"].iterrows():
        hist_abs_rows += f"<tr><td class='row-label'>{idx}</td>" + "".join([f"<td>${v:,.2f}B</td>" for v in row]) + "</tr>"

    hist_pct_rows = ""
    for idx, row in data["historical_ratios_df"].iterrows():
        hist_pct_rows += f"<tr><td class='row-label'>{idx}</td>" + "".join([f"<td>{v:.2f}%</td>" for v in row]) + "</tr>"

    html_template = f"""
    <!DOCTYPE html>
    <html lang="pt">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>DCF Valuation — {company} ({ticker})</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap" rel="stylesheet">
        <style>
            :root {{
                --bg-primary: #0F172A; --bg-card: #1E293B; --text-main: #F8FAFC;
                --text-muted: #94A3B8; --accent-blue: #38BDF8; --accent-green: #10B981;
                --accent-red: #EF4444; --border-color: #334155;
            }}
            body {{ font-family: 'Inter', sans-serif; background-color: var(--bg-primary); color: var(--text-main);
                margin: 0; padding: 40px 20px; display: flex; justify-content: center; }}
            .container {{ max-width: 1200px; width: 100%; }}
            .header {{ display: flex; justify-content: space-between; align-items: center;
                border-bottom: 2px solid var(--border-color); padding-bottom: 20px; margin-bottom: 30px; }}
            .header h1 {{ font-size: 28px; font-weight: 800; margin: 0; color: #FFFFFF; }}
            .header .ticker-badge {{ background: rgba(56, 189, 248, 0.15); color: var(--accent-blue);
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
                    <div style="color: var(--text-muted); font-size: 13px; margin-top: 4px;">Relatório de Valuação por Discounted Cash Flow (DCF)</div>
                </div>
                <div class="price-tag">Preço Atual de Mercado: <b>${price:.2f}</b></div>
            </div>
            <div class="cards-grid">{cards_html}</div>
            <h2 class="section-title">Projeções Financeiras por Cenário (5 Anos)</h2>
            {projections_tables_html}
            <h2 class="section-title">Contextualização Histórica (Últimos 5 Anos)</h2>
            <div class="section-card">
                <h3 class="section-subtitle">Demonstrações Financeiras ($B)</h3>
                <table class="custom-table">
                    <thead><tr><th>Métrica</th>{''.join([f'<th>Ano -{5-i}</th>' for i in range(5)])}</tr></thead>
                    <tbody>{hist_abs_rows}</tbody>
                </table>
            </div>
            <div class="section-card">
                <h3 class="section-subtitle">Rácios & Margens Históricas (%)</h3>
                <table class="custom-table">
                    <thead><tr><th>Rácio / Margem</th>{''.join([f'<th>Ano -{5-i}</th>' for i in range(5)])}</tr></thead>
                    <tbody>{hist_pct_rows}</tbody>
                </table>
            </div>
            <div class="footer">Gerado por Modelo DCF Institucional • Dados via Yahoo Finance • Apresentação de Dados em $B</div>
        </div>
    </body>
    </html>
    """
    return html_template


# ------------------------------------------------------------------------------
# 3. MOTOR DE CÁLCULO DO DCF (lógica inalterada)
# ------------------------------------------------------------------------------
def run_dcf_model(app_data, grids, wacc_vals, tgr_vals):
    scenarios = SCENARIOS
    results_summary = []
    tables_dict = {}
    last_rev = app_data["last_revenue"]

    for scen in scenarios:
        rev_growth = [grids["Revenue Growth (%)"].loc[scen, YEAR_COLS[i]] / 100.0 for i in range(5)]
        ebit_margin = [grids["EBIT Margin (%)"].loc[scen, YEAR_COLS[i]] / 100.0 for i in range(5)]
        tax_rate = [grids["Tax Rate (%)"].loc[scen, YEAR_COLS[i]] / 100.0 for i in range(5)]
        depr_pct = [grids["Depr (% Rev)"].loc[scen, YEAR_COLS[i]] / 100.0 for i in range(5)]
        capex_pct = [grids["CapEx (% Rev)"].loc[scen, YEAR_COLS[i]] / 100.0 for i in range(5)]
        nwc_pct = [grids["NWC (% Rev)"].loc[scen, YEAR_COLS[i]] / 100.0 for i in range(5)]

        wacc = wacc_vals[scen] / 100.0
        tgr = tgr_vals[scen] / 100.0

        proj_rev, proj_ebit, proj_nopat, proj_fcff = [], [], [], []
        curr_r = last_rev
        for i in range(5):
            curr_r *= (1 + rev_growth[i])
            ebit = curr_r * ebit_margin[i]
            nopat = ebit * (1 - tax_rate[i])
            depr = curr_r * depr_pct[i]
            capex = curr_r * capex_pct[i]
            nwc = curr_r * nwc_pct[i]
            fcff = nopat + depr - capex - nwc

            proj_rev.append(curr_r / 1e9)
            proj_ebit.append(ebit / 1e9)
            proj_nopat.append(nopat / 1e9)
            proj_fcff.append(fcff / 1e9)

        discount_factors = [(1 + wacc) ** (i + 1) for i in range(5)]
        pv_fcff = [proj_fcff[i] / discount_factors[i] for i in range(5)]
        sum_pv_fcff = sum(pv_fcff)

        terminal_value = (proj_fcff[-1] * (1 + tgr)) / (wacc - tgr) if wacc > tgr else 0
        pv_terminal_value = terminal_value / ((1 + wacc) ** 5)

        enterprise_value = sum_pv_fcff + pv_terminal_value
        cash_b = app_data["cash"] / 1e9
        debt_b = app_data["total_debt"] / 1e9

        equity_value = enterprise_value + cash_b - debt_b
        implied_price = (equity_value * 1e9) / app_data["shares_outstanding"] if app_data["shares_outstanding"] > 0 else 0
        upside = ((implied_price / app_data["current_price"]) - 1) * 100 if app_data["current_price"] > 0 else 0

        results_summary.append({
            "Cenário": scen,
            "WACC": f"{wacc * 100:.2f}%",
            "TGR": f"{tgr * 100:.2f}%",
            "Enterprise Value ($B)": f"${enterprise_value:,.2f}B",
            "Equity Value ($B)": f"${equity_value:,.2f}B",
            "Implied Share Price ($)": f"${implied_price:.2f}",
            "Upside / Downside (%)": f"{upside:+.2f}%",
        })

        proj_df = pd.DataFrame(
            {YEAR_COLS[i]: [proj_rev[i], proj_ebit[i], proj_nopat[i], proj_fcff[i], pv_fcff[i]] for i in range(5)},
            index=["Receita ($B)", "EBIT ($B)", "NOPAT ($B)", "FCFF ($B)", "PV of FCFF ($B)"],
        )
        tables_dict[scen] = proj_df

    return results_summary, tables_dict


# ------------------------------------------------------------------------------
# 4. INTERFACE
# ------------------------------------------------------------------------------
def default_grid(default_val_pct):
    return pd.DataFrame(
        [[round(default_val_pct, 2)] * 5, [round(default_val_pct + 3, 2)] * 5, [round(default_val_pct - 3, 2)] * 5],
        index=SCENARIOS,
        columns=YEAR_COLS,
    )


with st.sidebar:
    st.header("⚙️ Empresa")
    ticker_input = st.text_input("Ticker", value="KO", placeholder="Ex: KO, AAPL, MSFT")
    fetch_button = st.button("📥 Carregar Dados (5 Anos)", type="primary", use_container_width=True)

if fetch_button:
    with st.spinner(f"A obter dados financeiros para {ticker_input.upper()}..."):
        try:
            st.session_state["dcf_data"] = extract_financial_data(ticker_input)
            # limpar grelhas antigas para recalcular defaults para a nova empresa
            for key in list(st.session_state.keys()):
                if key.startswith("grid_"):
                    del st.session_state[key]
        except Exception as e:
            st.session_state.pop("dcf_data", None)
            st.error(f"Erro ao processar o ticker {ticker_input}: {e}")

app_data = st.session_state.get("dcf_data")

if not app_data:
    st.info("👈 Introduz um ticker na barra lateral e clica em **Carregar Dados** para começar.")
else:
    st.subheader(f"{app_data['company_name']} ({app_data['ticker']}) — Preço Atual: ${app_data['current_price']:.2f}")

    with st.expander("Ver Histórico Completo dos Últimos 5 Anos (Valores em $B & Percentagens)"):
        st.markdown("**Demonstrações Financeiras Históricas ($B)**")
        st.dataframe(app_data["historical_df"].style.format("${:,.2f}B"), use_container_width=True)
        st.markdown("**Contextualização Histórica de Rácios & Crescimentos (%)**")
        st.dataframe(app_data["historical_ratios_df"].style.format("{:.2f}%"), use_container_width=True)

    last_ratios = app_data["last_ratios"]
    metrics_defaults = {
        "Revenue Growth (%)": max(2.0, last_ratios.get("Revenue Growth (%)", 8.0)),
        "EBIT Margin (%)": max(5.0, last_ratios.get("EBIT Margin (%)", 20.0)),
        "Tax Rate (%)": max(15.0, last_ratios.get("Tax Rate (%)", 21.0)),
        "Depr (% Rev)": max(1.0, last_ratios.get("Depr (% Rev)", 4.0)),
        "CapEx (% Rev)": max(1.0, last_ratios.get("CapEx (% Rev)", 5.0)),
        "NWC (% Rev)": last_ratios.get("Change in NWC (% Rev)", 1.0),
    }

    st.markdown("### 📊 Pressupostos de Projeção (editáveis por cenário e por ano)")
    grids = {}
    for metric, default_val in metrics_defaults.items():
        st.markdown(f"**{metric}**")
        grid_key = f"grid_{metric}_{app_data['ticker']}"
        base_df = default_grid(default_val)
        edited = st.data_editor(
            base_df,
            use_container_width=True,
            key=grid_key,
        )
        grids[metric] = edited

    st.markdown("### 💵 Taxas de Desconto (WACC — Calculado Dinamicamente)")
    w_base = app_data["wacc_base"] * 100
    col1, col2, col3 = st.columns(3)
    wacc_vals = {}
    with col1:
        wacc_vals["Base"] = st.number_input("WACC Base (%)", value=round(w_base, 2), step=0.1, key=f"wacc_base_{app_data['ticker']}")
    with col2:
        wacc_vals["Otimista"] = st.number_input("WACC Otimista (%)", value=round(w_base - 0.5, 2), step=0.1, key=f"wacc_opt_{app_data['ticker']}")
    with col3:
        wacc_vals["Pessimista"] = st.number_input("WACC Pessimista (%)", value=round(w_base + 0.5, 2), step=0.1, key=f"wacc_pess_{app_data['ticker']}")

    st.markdown("### 📈 Terminal Growth Rate (TGR)")
    col4, col5, col6 = st.columns(3)
    tgr_vals = {}
    with col4:
        tgr_vals["Base"] = st.number_input("TGR Base (%)", value=2.5, step=0.1, key=f"tgr_base_{app_data['ticker']}")
    with col5:
        tgr_vals["Otimista"] = st.number_input("TGR Otimista (%)", value=3.0, step=0.1, key=f"tgr_opt_{app_data['ticker']}")
    with col6:
        tgr_vals["Pessimista"] = st.number_input("TGR Pessimista (%)", value=2.0, step=0.1, key=f"tgr_pess_{app_data['ticker']}")

    calc_button = st.button("🧮 Gerar Análise & Relatório HTML", type="primary", use_container_width=True)

    if calc_button:
        results_summary, tables_dict = run_dcf_model(app_data, grids, wacc_vals, tgr_vals)
        html_report = generate_styled_html_report(app_data, results_summary, tables_dict)

        st.markdown(f"### ✅ Valuação Concluída para {app_data['company_name']}")
        st.dataframe(pd.DataFrame(results_summary), use_container_width=True, hide_index=True)

        for scen in SCENARIOS:
            with st.expander(f"Projeções de Fluxo de Caixa — Cenário {scen}"):
                st.dataframe(tables_dict[scen].style.format("${:,.2f}B"), use_container_width=True)

        st.download_button(
            label="⬇️ Descarregar Relatório HTML Estilizado",
            data=html_report,
            file_name=f"DCF_Dashboard_{app_data['ticker']}.html",
            mime="text/html",
            use_container_width=True,
        )
