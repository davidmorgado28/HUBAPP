# ==============================================================================
# 💵 MODELO DDM — Dividend Discount Model (Aplicação Streamlit)
# Mesmo padrão da página do DCF: grelhas 5 (anos) x 3 (cenários) editáveis,
# custo do capital próprio calculado por CAPM (editável) e relatório HTML.
# ==============================================================================

import html as _html
import sys
import warnings
from io import StringIO
from pathlib import Path

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import requests
import streamlit as st
import yfinance as yf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from theme import inject_theme, page_header, APP_NAME

st.set_page_config(
    page_title="Modelo DDM",
    page_icon="💵",
    layout="wide",
)

inject_theme()

page_header(
    "💵",
    "Modelo DDM — Dividend Discount Model",
    "Valuação por dividendos em 3 cenários (Base / Otimista / Pessimista), com projeção de ROE, "
    "Equity, Payout e Buyback Yield, Ke calculado por CAPM e relatório HTML para download.",
)

SCENARIOS = ["Base", "Otimista", "Pessimista"]
YEAR_COLS = [f"Ano {i}" for i in range(1, 6)]
N = 5


# ------------------------------------------------------------------------------
# 1. FUNÇÕES AUXILIARES (CAPM igual ao DCF; MRP preferencialmente Damodaran)
# ------------------------------------------------------------------------------
@st.cache_data(show_spinner=False, ttl=3600)
def get_risk_free_rate():
    try:
        hist = yf.Ticker("^TNX").history(period="5d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1]) / 100.0
    except Exception:
        pass
    return 0.0425


@st.cache_data(show_spinner=False, ttl=3600)
def get_sp500_historical_return(years=20):
    try:
        hist = yf.Ticker("^GSPC").history(period=f"{years}y")
        if not hist.empty:
            start_price = hist["Close"].iloc[0]
            end_price = hist["Close"].iloc[-1]
            num_years = (hist.index[-1] - hist.index[0]).days / 365.25
            return (end_price / start_price) ** (1 / num_years) - 1.0
    except Exception:
        pass
    return 0.098


@st.cache_data(show_spinner=False, ttl=86400)
def get_damodaran_erp():
    """ERP implícito (FCFE) mais recente do site do Prof. Damodaran, ou None."""
    try:
        url = "https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/histimpl.html"
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        for tb in pd.read_html(StringIO(r.text)):
            tb.columns = [" ".join(map(str, c)) if isinstance(c, tuple) else str(c) for c in tb.columns]
            col = next((c for c in tb.columns if "implied premium" in c.lower() and "fcfe" in c.lower()), None)
            if col is None:
                continue
            vals = pd.to_numeric(tb[col].astype(str).str.replace("%", "", regex=False), errors="coerce")
            idx = vals.last_valid_index()
            if idx is None:
                continue
            v = float(vals.loc[idx])
            v = v / 100 if v > 1 else v
            if 0.02 <= v <= 0.10:
                return v, str(tb.iloc[idx, 0])
    except Exception:
        pass
    return None


def calculate_cost_of_equity(info, rf_rate):
    dam = get_damodaran_erp()
    if dam:
        erp, erp_src = dam[0], f"Damodaran (ERP implícito, {dam[1]})"
    else:
        sp500_return = get_sp500_historical_return(years=20)
        erp = max(0.035, sp500_return - rf_rate)
        erp_src = "Média histórica do S&P 500 (20 anos) − taxa livre de risco"
    beta = info.get("beta", 1.0) or 1.0
    return rf_rate + beta * erp, beta, erp, erp_src


def _series(df, keys):
    """Série cronológica (mais antigo → mais recente), indexada por ano."""
    if df is not None and not df.empty:
        for k in keys:
            if k in df.index:
                s = df.loc[k].dropna()
                if len(s):
                    s = s.iloc[:5][::-1]
                    s.index = [pd.Timestamp(i).year for i in s.index]
                    return s
    return pd.Series(dtype=float)


@st.cache_data(show_spinner=False, ttl=3600)
def extract_financial_data(ticker_symbol):
    ticker = yf.Ticker(ticker_symbol)
    fin, bs, cf = ticker.financials, ticker.balance_sheet, ticker.cashflow
    info = ticker.info or {}

    equity = _series(bs, ["Stockholders Equity", "Common Stock Equity"])
    net_income = _series(fin, ["Net Income Common Stockholders", "Net Income"])
    buyback_cash = _series(cf, ["Repurchase Of Capital Stock", "Common Stock Payments"]).abs()
    shares_hist = _series(bs, ["Ordinary Shares Number", "Share Issued"])

    if equity.empty or net_income.empty:
        raise ValueError("Não foi possível obter Equity e/ou Net Income históricos para este Ticker.")

    years = sorted(set(equity.index) & set(net_income.index))
    if len(years) < 2:
        raise ValueError("Histórico insuficiente (menos de 2 anos com Equity e Net Income).")
    equity, net_income = equity.loc[years], net_income.loc[years]

    # Market cap no fim de cada ano fiscal (preço de fecho × nº de ações) para o Buyback Yield
    mcap = pd.Series(np.nan, index=years)
    try:
        px = ticker.history(period="8y", auto_adjust=False)["Close"].dropna()
        px.index = px.index.tz_localize(None) if px.index.tz is not None else px.index
        bs_dates = {pd.Timestamp(c).year: pd.Timestamp(c) for c in bs.columns}
        for y in years:
            if y in shares_hist.index and y in bs_dates:
                p = px[:bs_dates[y]]
                if len(p):
                    mcap[y] = float(p.iloc[-1]) * float(shares_hist[y])
    except Exception:
        pass
    bb_yield = (buyback_cash.reindex(years).fillna(0) / mcap) * 100

    roe = (net_income / equity) * 100
    historical_df = pd.DataFrame({
        "Net Income ($B)": net_income / 1e9,
        "Equity ($B)": equity / 1e9,
        "ROE (%)": roe,
        "Buyback Yield (%)": bb_yield,
    })
    historical_df.index = [str(y) for y in years]

    historical_ratios_df = pd.DataFrame({
        "ROE Growth (%)": roe.pct_change() * 100,
        "Equity Growth (%)": equity.pct_change() * 100,
    })
    historical_ratios_df.index = [str(y) for y in years]

    rf_rate = get_risk_free_rate()
    ke, beta, erp, erp_src = calculate_cost_of_equity(info, rf_rate)

    return {
        "ticker": ticker_symbol.upper(),
        "company_name": info.get("longName", ticker_symbol.upper()),
        "historical_df": historical_df,
        "historical_ratios_df": historical_ratios_df,
        "ke_base": ke, "rf": rf_rate, "beta": beta, "erp": erp, "erp_src": erp_src,
        "current_price": info.get("currentPrice") or info.get("regularMarketPrice") or 0.0,
        "shares_outstanding": float(info.get("sharesOutstanding") or 0),
        "last_year": int(years[-1]),
        "last_equity": float(equity.iloc[-1]),
        "last_roe": float(roe.iloc[-1]),
        "last_ratios": historical_ratios_df.iloc[-1],
        "last_bb": float(bb_yield.iloc[-1]) if not np.isnan(bb_yield.iloc[-1]) else 0.0,
    }


# ------------------------------------------------------------------------------
# 2. MOTOR DE CÁLCULO DO DDM
# ------------------------------------------------------------------------------
def payout_table(app_data, roe_g, eq_g):
    out = pd.DataFrame(index=SCENARIOS, columns=YEAR_COLS, dtype=float)
    for scen in SCENARIOS:
        roe = app_data["last_roe"] / 100.0
        for y in YEAR_COLS:
            roe *= 1 + roe_g.loc[scen, y] / 100.0
            g = eq_g.loc[scen, y] / 100.0
            out.loc[scen, y] = np.nan if roe == 0 else 1 - g / roe
    return out


def run_ddm_model(app_data, grids, ke_vals, tgr_vals):
    keys = ["roe", "payout", "ni", "div", "shares", "dps", "pv"]
    tables = {s: pd.DataFrame(index=[
        "ROE estimado (%)", "Payout Ratio (%)", "Net Income ($B)", "Dividendos totais ($B)",
        "Nº de ações (M)", "DPS ($)", "DPS atualizado ($)"], columns=YEAR_COLS, dtype=float)
        for s in SCENARIOS}
    summary = []

    for scen in SCENARIOS:
        ke, tgr = ke_vals[scen] / 100.0, tgr_vals[scen] / 100.0
        roe = app_data["last_roe"] / 100.0
        equity = app_data["last_equity"]
        shares = app_data["shares_outstanding"]
        sum_pv = 0.0
        last_div = 0.0

        for i, y in enumerate(YEAR_COLS):
            roe *= 1 + grids["ROE"].loc[scen, y] / 100.0
            g_eq = grids["Equity"].loc[scen, y] / 100.0
            payout = np.nan if roe == 0 else 1 - g_eq / roe
            net_income = roe * equity                       # ROE × Equity do ano anterior
            dividend = payout * net_income
            shares *= 1 - grids["Buyback"].loc[scen, y] / 100.0
            dps = dividend / shares
            pv = dps / (1 + ke) ** (i + 1)
            sum_pv += pv
            equity *= 1 + g_eq
            last_div = dividend
            tables[scen][y] = [roe * 100, payout * 100, net_income / 1e9, dividend / 1e9,
                               shares / 1e6, dps, pv]

        tv_total = last_div * (1 + tgr) / (ke - tgr)
        tv_ps = tv_total / shares
        pv_tv = tv_ps / (1 + ke) ** N
        value = sum_pv + pv_tv
        price = app_data["current_price"]
        upside = (value / price - 1) * 100 if price > 0 else 0
        summary.append({
            "Cenário": scen,
            "Ke": f"{ke * 100:.2f}%",
            "TGR": f"{tgr * 100:.2f}%",
            "Terminal Value ($B)": f"${tv_total / 1e9:,.2f}B",
            "Σ DPS atualizados ($)": f"${sum_pv:.2f}",
            "TV atualizado / ação ($)": f"${pv_tv:.2f}",
            "Valor Intrínseco / ação ($)": f"${value:.2f}",
            "Upside / Downside (%)": f"{upside:+.2f}%",
        })
    return summary, tables


# ------------------------------------------------------------------------------
# 3. RELATÓRIO HTML
# ------------------------------------------------------------------------------
def _fmt_row(label, vals):
    return f"<tr><td class='row-label'>{_html.escape(label)}</td>" + "".join(f"<td>{v}</td>" for v in vals) + "</tr>"


def _fmt_cell(label, v):
    if pd.isna(v):
        return "—"
    if "(%)" in label:
        return f"{v:.2f}%"
    if "($B)" in label:
        return f"${v:,.2f}B"
    if "(M)" in label:
        return f"{v:,.1f}M"
    return f"${v:,.2f}"


def generate_styled_html_report(data, summary, tables):
    price = data["current_price"]
    cards = ""
    for r in summary:
        up = r["Upside / Downside (%)"]
        color = "#10B981" if float(up.replace("%", "").replace("+", "")) >= 0 else "#EF4444"
        cards += f"""
        <div class="card"><div class="card-tag">{r['Cenário'].upper()}</div>
        <div class="card-title">Valor Intrínseco / ação</div>
        <div class="card-value">{r['Valor Intrínseco / ação ($)']}</div>
        <div class="card-sub" style="color:{color};"><span>{up}</span> vs Preço Atual (${price:.2f})</div>
        <div class="card-details"><div>Ke: <b>{r['Ke']}</b></div><div>TGR: <b>{r['TGR']}</b></div>
        <div>TV: <b>{r['Terminal Value ($B)']}</b></div></div></div>"""

    proj = ""
    for scen in SCENARIOS:
        df = tables[scen]
        rows = "".join(_fmt_row(idx, [_fmt_cell(idx, v) for v in row]) for idx, row in df.iterrows())
        proj += f"""<div class="section-card"><h3 class="section-subtitle">Projeções — Cenário {scen}</h3>
        <table class="custom-table"><thead><tr><th>Métrica</th>{''.join(f'<th>{c}</th>' for c in df.columns)}</tr></thead>
        <tbody>{rows}</tbody></table></div>"""

    def hist_block(df, title):
        head = "".join(f"<th>{i}</th>" for i in df.index)
        body = "".join(_fmt_row(c, [_fmt_cell(c, v) for v in df[c]]) for c in df.columns)
        return f"""<div class="section-card"><h3 class="section-subtitle">{title}</h3>
        <table class="custom-table"><thead><tr><th>Métrica</th>{head}</tr></thead><tbody>{body}</tbody></table></div>"""

    return f"""<!DOCTYPE html><html lang="pt"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DDM Valuation — {_html.escape(data['company_name'])} ({data['ticker']})</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap" rel="stylesheet">
<style>
:root {{ --bg-primary:#F1EEE4; --bg-card:#E8E4D6; --text-main:#1C2420; --text-muted:#4F7058; --accent-primary:#2E7D4C; --border-color:rgba(47,74,56,0.2); }}
body {{ font-family:'Inter',sans-serif; background:var(--bg-primary); color:var(--text-main); margin:0; padding:40px 20px; display:flex; justify-content:center; }}
.container {{ max-width:1200px; width:100%; }}
.header {{ display:flex; justify-content:space-between; align-items:center; border-bottom:2px solid var(--border-color); padding-bottom:20px; margin-bottom:30px; }}
.header h1 {{ font-size:28px; font-weight:800; margin:0; color:#1E2E22; }}
.ticker-badge {{ background:rgba(47,74,56,0.12); color:var(--accent-primary); padding:4px 12px; border-radius:6px; font-size:14px; font-weight:700; }}
.price-tag {{ font-size:16px; color:var(--text-muted); }} .price-tag b {{ color:#1E2E22; font-size:20px; }}
.cards-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(320px,1fr)); gap:20px; margin-bottom:35px; }}
.card {{ background:var(--bg-card); border:1px solid var(--border-color); border-radius:12px; padding:24px; position:relative; }}
.card-tag {{ position:absolute; top:20px; right:20px; font-size:11px; font-weight:800; background:rgba(47,74,56,0.12); color:var(--accent-primary); padding:2px 8px; border-radius:4px; }}
.card-title {{ font-size:13px; color:var(--text-muted); text-transform:uppercase; margin-bottom:8px; }}
.card-value {{ font-size:34px; font-weight:800; color:#1E2E22; margin-bottom:6px; }}
.card-sub {{ font-size:13px; font-weight:600; margin-bottom:18px; }}
.card-details {{ border-top:1px solid var(--border-color); padding-top:12px; display:flex; justify-content:space-between; font-size:12px; color:var(--text-muted); }}
.card-details b {{ color:var(--text-main); }}
.section-card {{ background:var(--bg-card); border:1px solid var(--border-color); border-radius:12px; padding:24px; margin-bottom:25px; }}
.section-title {{ font-size:18px; font-weight:700; margin:0 0 15px; color:var(--accent-primary); }}
.section-subtitle {{ font-size:15px; font-weight:600; margin:0 0 15px; color:#1E2E22; }}
.custom-table {{ width:100%; border-collapse:collapse; text-align:right; font-size:13px; }}
.custom-table th {{ background:linear-gradient(135deg,#2F4A38,#4F7058); color:#F1EEE4; font-weight:600; padding:12px 16px; text-transform:uppercase; font-size:11px; }}
.custom-table th:first-child {{ text-align:left; }}
.custom-table td {{ padding:12px 16px; border-bottom:1px solid var(--border-color); }}
.row-label {{ text-align:left; font-weight:600; color:#1E2E22; }}
.footer {{ text-align:center; color:var(--text-muted); font-size:12px; margin-top:40px; padding-top:20px; border-top:1px solid var(--border-color); }}
</style></head><body><div class="container">
<div class="header"><div><h1>{_html.escape(data['company_name'])} <span class="ticker-badge">{data['ticker']}</span></h1>
<div style="color:var(--text-muted);font-size:13px;margin-top:4px;">Relatório de Valuação por Dividend Discount Model (DDM)</div></div>
<div class="price-tag">Preço Atual de Mercado: <b>${price:.2f}</b></div></div>
<div class="cards-grid">{cards}</div>
<h2 class="section-title">Projeções por Cenário (5 Anos)</h2>{proj}
<h2 class="section-title">Contextualização Histórica</h2>
{hist_block(data['historical_df'], 'ROE, Equity e Buyback Yield Históricos')}
{hist_block(data['historical_ratios_df'], 'Taxas de Crescimento Históricas (%)')}
<div class="footer">Gerado por {APP_NAME} • Modelo DDM • Dados via Yahoo Finance e Damodaran</div>
</div></body></html>"""


# ------------------------------------------------------------------------------
# 4. INTERFACE
# ------------------------------------------------------------------------------
def default_grid(base_val, step, floor=None):
    rows = [base_val, base_val + step, base_val - step]
    if floor is not None:
        rows = [max(floor, r) for r in rows]
    return pd.DataFrame([[round(r, 2)] * 5 for r in rows], index=SCENARIOS, columns=YEAR_COLS)


def fmt_pct(x):
    return "—" if pd.isna(x) else f"{x:.2f}%"


with st.sidebar:
    st.header("⚙️ Empresa")
    ticker_input = st.text_input("Ticker", value="KO", placeholder="Ex: KO, PG, JNJ")
    fetch_button = st.button("📥 Carregar Dados (Histórico)", type="primary", use_container_width=True)

if fetch_button:
    with st.spinner(f"A obter dados financeiros para {ticker_input.upper()}..."):
        try:
            st.session_state["ddm_data"] = extract_financial_data(ticker_input.strip())
            for key in list(st.session_state.keys()):
                if key.startswith("ddmgrid_"):
                    del st.session_state[key]
        except Exception as e:
            st.session_state.pop("ddm_data", None)
            st.error(f"Erro ao processar o ticker {ticker_input}: {e}")

app_data = st.session_state.get("ddm_data")

if not app_data:
    st.info("👈 Introduz um ticker na barra lateral e clica em **Carregar Dados** para começar.")
else:
    st.subheader(f"{app_data['company_name']} ({app_data['ticker']}) — Preço Atual: ${app_data['current_price']:.2f}")

    if app_data["last_equity"] <= 0 or app_data["last_roe"] <= 0:
        st.error("Equity ou ROE do último ano é ≤ 0 — o DDM baseado em ROE/Equity não é aplicável a esta empresa.")
        st.stop()
    if app_data["shares_outstanding"] <= 0:
        st.error("Sem número de ações em circulação no Yahoo Finance — não é possível calcular o valor por ação.")
        st.stop()

    with st.expander("Ver Histórico dos Últimos Anos (ROE, Equity, Buyback Yield e Crescimentos)"):
        st.markdown("**ROE, Equity e Buyback Yield Históricos**")
        st.dataframe(
            app_data["historical_df"].style.format(
                {"Net Income ($B)": "${:,.2f}B", "Equity ($B)": "${:,.2f}B", "ROE (%)": "{:.2f}%", "Buyback Yield (%)": "{:.2f}%"},
                na_rep="—"),
            use_container_width=True)
        st.markdown("**Taxas de Crescimento Históricas (%)**")
        st.dataframe(app_data["historical_ratios_df"].style.format("{:.2f}%", na_rep="—"), use_container_width=True)
        st.caption("ROE = Net Income / Equity do fim do ano. Buyback Yield = recompras de ações do ano / "
                   "capitalização bolsista no fim do ano fiscal. Fonte: Yahoo Finance.")

    lr = app_data["last_ratios"]
    nz = lambda v, d: d if pd.isna(v) else float(v)
    metrics_defaults = {
        "ROE": ("Taxa de Crescimento do ROE (%)", default_grid(0.0, 2.0)),
        "Equity": ("Taxa de Crescimento do Equity (%)", default_grid(nz(lr.get("Equity Growth (%)"), 3.0), 2.0)),
        "Buyback": ("Buyback Yield (%)", default_grid(max(0.0, app_data["last_bb"]), 0.5, floor=0.0)),
    }

    st.markdown("### 📊 Pressupostos de Projeção (editáveis por cenário e por ano)")
    grids = {}
    for key, (title, base_df) in metrics_defaults.items():
        st.markdown(f"**{title}**")
        grids[key] = st.data_editor(base_df, use_container_width=True, key=f"ddmgrid_{key}_{app_data['ticker']}")

    st.markdown("### 💵 Custo do Capital Próprio (Ke — Calculado por CAPM)")
    st.caption(
        f"Ke = Rf + β × MRP = {app_data['rf'] * 100:.2f}% (T-Bond 10Y) + {app_data['beta']:.2f} × "
        f"{app_data['erp'] * 100:.2f}% ({app_data['erp_src']}). Altera apenas se discordares."
    )
    k_base = app_data["ke_base"] * 100
    col1, col2, col3 = st.columns(3)
    ke_vals = {}
    t = app_data["ticker"]
    with col1:
        ke_vals["Base"] = st.number_input("Ke Base (%)", value=round(k_base, 2), step=0.1, key=f"ke_base_{t}")
    with col2:
        ke_vals["Otimista"] = st.number_input("Ke Otimista (%)", value=round(k_base - 0.5, 2), step=0.1, key=f"ke_opt_{t}")
    with col3:
        ke_vals["Pessimista"] = st.number_input("Ke Pessimista (%)", value=round(k_base + 0.5, 2), step=0.1, key=f"ke_pess_{t}")

    st.markdown("### 📈 Terminal Growth Rate (TGR)")
    col4, col5, col6 = st.columns(3)
    tgr_vals = {}
    with col4:
        tgr_vals["Base"] = st.number_input("TGR Base (%)", value=2.0, max_value=2.5, step=0.1, key=f"ddm_tgr_base_{t}")
    with col5:
        tgr_vals["Otimista"] = st.number_input("TGR Otimista (%)", value=2.5, max_value=2.5, step=0.1, key=f"ddm_tgr_opt_{t}")
    with col6:
        tgr_vals["Pessimista"] = st.number_input("TGR Pessimista (%)", value=1.5, max_value=2.5, step=0.1, key=f"ddm_tgr_pess_{t}")

    calc_button = st.button("🧮 Gerar Análise & Relatório HTML", type="primary", use_container_width=True)

    if calc_button:
        bad = [s for s in SCENARIOS if ke_vals[s] <= tgr_vals[s]]
        if bad:
            st.error(f"O Ke tem de ser superior ao TGR em: {', '.join(bad)}.")
        else:
            summary, tables = run_ddm_model(app_data, grids, ke_vals, tgr_vals)
            html_report = generate_styled_html_report(app_data, summary, tables)

            st.markdown(f"### ✅ Valuação Concluída para {app_data['company_name']}")
            st.dataframe(pd.DataFrame(summary), use_container_width=True, hide_index=True)

            payouts = pd.concat([tables[sc].loc["Payout Ratio (%)"] for sc in SCENARIOS])
            if ((payouts < 0) | (payouts > 100)).any():
                st.warning("Há Payouts negativos ou acima de 100% — confirma os pressupostos de ROE e Equity.")

            for scen in SCENARIOS:
                with st.expander(f"Projeções — Cenário {scen}"):
                    df = tables[scen]
                    show = df.astype(object)
                    for idx in show.index:
                        show.loc[idx] = [_fmt_cell(idx, v) for v in df.loc[idx]]
                    st.dataframe(show, use_container_width=True)

            st.download_button(
                label="⬇️ Descarregar Relatório HTML Estilizado",
                data=html_report,
                file_name=f"DDM_Dashboard_{app_data['ticker']}.html",
                mime="text/html",
                use_container_width=True,
            )
