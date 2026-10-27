import html as _html
import re
from datetime import datetime
from io import StringIO

import numpy as np
import pandas as pd
import requests
import streamlit as st
import yfinance as yf

from theme import inject_theme, page_header

st.set_page_config(page_title="Modelo DDM | OAK & VALUE", page_icon="💰", layout="wide")
inject_theme()
try:
    page_header("Modelo DDM", "Dividend Discount Model — 3 cenários")
except TypeError:
    page_header("Modelo DDM")

SCEN = ["Base", "Otimista", "Pessimista"]
N = 5
ERP_FLOOR = 0.035


# ───────────────────────── Dados ─────────────────────────
def _row(df, names):
    for n in names:
        if n in df.index:
            s = df.loc[n].dropna()
            if len(s):
                return s
    return None


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_company(ticker):
    t = yf.Ticker(ticker)
    info = t.info or {}
    bs, fin = t.balance_sheet, t.financials
    eq = _row(bs, ["Stockholders Equity", "Common Stock Equity", "Total Equity Gross Minority Interest"])
    ni = _row(fin, ["Net Income Common Stockholders", "Net Income"])
    if eq is None or ni is None:
        raise ValueError("Não foi possível obter Equity e/ou Net Income históricos.")
    equity0, ni0 = float(eq.iloc[0]), float(ni.iloc[0])
    price = info.get("currentPrice") or info.get("regularMarketPrice")
    return {
        "ticker": ticker,
        "name": info.get("shortName", ticker),
        "currency": info.get("currency", ""),
        "price": float(price) if price else None,
        "shares": float(info.get("sharesOutstanding") or 0),
        "beta": info.get("beta"),
        "equity0": equity0,
        "ni0": ni0,
        "roe0": ni0 / equity0,
        "last_year": int(eq.index[0].year),
    }


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_rf():
    h = yf.Ticker("^TNX").history(period="10d")["Close"].dropna()
    return float(h.iloc[-1]) / 100 if len(h) else None


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_sp500_cagr():
    h = yf.Ticker("^GSPC").history(period="20y", auto_adjust=True)["Close"].dropna()
    yrs = (h.index[-1] - h.index[0]).days / 365.25
    return float((h.iloc[-1] / h.iloc[0]) ** (1 / yrs) - 1)


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_damodaran_erp():
    """ERP implícito (FCFE) mais recente do site do Prof. Damodaran. None se falhar."""
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


def parse_box(text, default, pct=False):
    """Caixa de texto: vazia → valor calculado; preenchida → override."""
    t = (text or "").strip().replace(",", ".").replace("%", "")
    if not t:
        return default, False
    try:
        v = float(t)
        return (v / 100 if pct else v), True
    except ValueError:
        st.warning(f"Valor inválido «{text}» — a usar o valor calculado.")
        return default, False


# ───────────────────────── Cálculo ─────────────────────────
def payout_table(d, roe_g, eq_g):
    out = pd.DataFrame(index=SCEN, columns=roe_g.columns, dtype=float)
    for s in SCEN:
        roe = d["roe0"]
        for i in range(N):
            roe = roe * (1 + roe_g.loc[s].iloc[i] / 100)
            g = eq_g.loc[s].iloc[i] / 100
            out.loc[s].iloc[i] = np.nan if roe == 0 else 1 - g / roe
    return out


def run_ddm(d, roe_g, eq_g, bb, ke, tgr):
    cols = roe_g.columns
    res = {k: pd.DataFrame(index=SCEN, columns=cols, dtype=float)
           for k in ["roe", "payout", "ni", "div", "shares", "dps", "pv"]}
    summary = []
    for s in SCEN:
        roe, eq, sh = d["roe0"], d["equity0"], d["shares"]
        pv_sum = 0.0
        for i in range(N):
            roe = roe * (1 + roe_g.loc[s].iloc[i] / 100)
            g = eq_g.loc[s].iloc[i] / 100
            payout = np.nan if roe == 0 else 1 - g / roe
            ni = roe * eq                      # ROE do ano × Equity do ano anterior
            div = payout * ni
            sh = sh * (1 - bb.loc[s].iloc[i] / 100)
            dps = div / sh
            pv = dps / (1 + ke) ** (i + 1)
            pv_sum += pv
            eq = eq * (1 + g)
            for k, v in zip(res, [roe, payout, ni, div, sh, dps, pv]):
                res[k].loc[s].iloc[i] = v
        gt = tgr[s] / 100
        tv_total = res["div"].loc[s].iloc[-1] * (1 + gt) / (ke - gt)
        tv_ps = tv_total / res["shares"].loc[s].iloc[-1]
        pv_tv = tv_ps / (1 + ke) ** N
        val = pv_sum + pv_tv
        summary.append({
            "Cenário": s, "TGR": gt, "Terminal Value (total)": tv_total,
            "Σ DPS atualizados": pv_sum, "TV atualizado / ação": pv_tv,
            "Valor intrínseco / ação": val,
            "Upside": (val / d["price"] - 1) if d["price"] else np.nan,
        })
    return res, pd.DataFrame(summary).set_index("Cenário")


def fmt_df(df, f):
    return df.astype(object).apply(lambda c: c.map(lambda x: "—" if pd.isna(x) else f(x)))


pct = lambda x: f"{x * 100:.2f}%"
mil = lambda x: f"{x / 1e6:,.1f}"
num = lambda x: f"{x:,.2f}"

# ───────────────────────── Sidebar ─────────────────────────
with st.sidebar:
    st.header("Empresa")
    ticker = st.text_input("Ticker", value="MCD").strip().upper()
    fetch_btn = st.button("Buscar dados", use_container_width=True)
    st.header("TGR por cenário (%)")
    tgr = {
        "Base": st.number_input("Base", value=2.0, max_value=2.5, step=0.1),
        "Otimista": st.number_input("Otimista", value=2.5, max_value=2.5, step=0.1),
        "Pessimista": st.number_input("Pessimista", value=1.5, max_value=2.5, step=0.1),
    }

if fetch_btn:
    with st.spinner("A obter dados…"):
        try:
            d = fetch_company(ticker)
            years = [f"{d['last_year'] + i}E" for i in range(1, N + 1)]
            zeros = lambda: pd.DataFrame(0.0, index=SCEN, columns=years)
            st.session_state["ddm"] = {"d": d, "roe_g": zeros(), "eq_g": zeros(), "bb": zeros()}
            st.session_state.pop("ddm_result", None)
        except Exception as e:
            st.error(f"Falha ao obter dados de {ticker}: {e}")

if "ddm" not in st.session_state:
    st.info("Escolhe o ticker na barra lateral e clica em «Buscar dados».")
    st.stop()

S = st.session_state["ddm"]
d = S["d"]
if d["shares"] <= 0:
    st.error(f"Sem número de ações para {d['ticker']} — não é possível calcular o valor por ação.")
    st.stop()

st.subheader(f"{d['name']} ({d['ticker']})")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Preço atual", f"{d['price']:,.2f} {d['currency']}" if d["price"] else "—")
c2.metric(f"Equity {d['last_year']} (M)", mil(d["equity0"]))
c3.metric(f"ROE {d['last_year']}", pct(d["roe0"]))
c4.metric("Ações (M)", mil(d["shares"]))
st.caption("ROE histórico = Net Income / Equity do último ano fiscal. Fonte: Yahoo Finance.")

# ───────────────────────── Custo do capital próprio ─────────────────────────
st.markdown("### Custo do Capital Próprio (CAPM)")
rf_calc = fetch_rf()
beta_calc = d["beta"]
dam = fetch_damodaran_erp()
if dam:
    mrp_calc, mrp_src = dam[0], f"Damodaran (ERP implícito, {dam[1]})"
else:
    try:
        mrp_calc = max(fetch_sp500_cagr() - (rf_calc or 0), ERP_FLOOR)
        mrp_src = "Fallback: CAGR 20 anos do S&P 500 − taxa livre de risco (mín. 3,5%)"
    except Exception:
        mrp_calc, mrp_src = None, "indisponível"

if rf_calc is None or beta_calc is None or mrp_calc is None:
    st.warning("Algum parâmetro do CAPM não foi obtido automaticamente — preenche as caixas abaixo.")

k1, k2, k3 = st.columns(3)
rf_txt = k1.text_input("Taxa livre de risco (%) — T-Bond 10y", placeholder=f"{rf_calc * 100:.2f}" if rf_calc else "preencher")
beta_txt = k2.text_input("Beta", placeholder=f"{beta_calc:.2f}" if beta_calc is not None else "preencher")
mrp_txt = k3.text_input("Market Risk Premium (%)", placeholder=f"{mrp_calc * 100:.2f}" if mrp_calc else "preencher")
rf, _ = parse_box(rf_txt, rf_calc, pct=True)
beta, _ = parse_box(beta_txt, beta_calc)
mrp, _ = parse_box(mrp_txt, mrp_calc, pct=True)
st.caption(f"Deixa vazio para usar o valor calculado. MRP: {mrp_src}.")
if None in (rf, beta, mrp):
    st.stop()
ke = rf + beta * mrp
st.metric("Ke = Rf + β × MRP", pct(ke))

# ───────────────────────── Grelhas ─────────────────────────
st.markdown("### Pressupostos (em %)")


def grid(title, df, key):
    st.markdown(f"**{title}**")
    cfg = {c: st.column_config.NumberColumn(c, format="%.2f", step=0.5) for c in df.columns}
    return st.data_editor(df, key=f"{key}_{d['ticker']}", column_config=cfg, use_container_width=True)


roe_g = grid("Taxa de crescimento do ROE (%)", S["roe_g"], "roe")
eq_g = grid("Taxa de crescimento do Equity (%)", S["eq_g"], "eq")
bb = grid("Buyback Yield (%)", S["bb"], "bb")

st.markdown("**Payout Ratio** = 1 − (crescimento do Equity / ROE)")
pt = payout_table(d, roe_g, eq_g)
st.dataframe(fmt_df(pt, pct), use_container_width=True)
if ((pt < 0) | (pt > 1)).any().any():
    st.warning("Há Payouts negativos ou acima de 100% — confirma os pressupostos de ROE e Equity.")

# ───────────────────────── Botão ─────────────────────────
if st.button("Calcular DDM", type="primary"):
    bad = [s for s in SCEN if ke <= tgr[s] / 100]
    if bad:
        st.error(f"Ke ({pct(ke)}) tem de ser superior ao TGR em: {', '.join(bad)}.")
    else:
        res, summ = run_ddm(d, roe_g, eq_g, bb, ke, tgr)
        st.session_state["ddm_result"] = (res, summ, ke, d["ticker"])

if "ddm_result" in st.session_state and st.session_state["ddm_result"][3] == d["ticker"]:
    res, summ, ke_used, _ = st.session_state["ddm_result"]
    st.markdown("### Resultados")
    show = pd.DataFrame({
        "TGR": summ["TGR"].map(pct),
        "Terminal Value (M)": summ["Terminal Value (total)"].map(mil),
        "Σ DPS atualizados": summ["Σ DPS atualizados"].map(num),
        "TV atualizado / ação": summ["TV atualizado / ação"].map(num),
        "Valor intrínseco / ação": summ["Valor intrínseco / ação"].map(num),
        "Upside vs preço": summ["Upside"].map(lambda x: "—" if pd.isna(x) else pct(x)),
    })
    st.dataframe(show, use_container_width=True)

    blocks = [
        ("ROE estimado", res["roe"], pct),
        ("Payout Ratio", res["payout"], pct),
        ("Net Income (M) = ROE × Equity do ano anterior", res["ni"], mil),
        ("Dividendos totais (M) = Payout × Net Income", res["div"], mil),
        ("Nº de ações (M) após buyback", res["shares"], mil),
        ("DPS (dividendo por ação)", res["dps"], num),
        (f"DPS atualizado ao Ke ({pct(ke_used)})", res["pv"], num),
    ]
    html_parts = [f"<h2>Modelo DDM — {_html.escape(d['name'])} ({d['ticker']})</h2>",
                  f"<p>Ke = {pct(ke_used)} · gerado em {datetime.now():%Y-%m-%d %H:%M}</p>",
                  show.to_html()]
    for title, df, f in blocks:
        f_df = fmt_df(df, f)
        st.markdown(f"**{title}**")
        st.dataframe(f_df, use_container_width=True)
        html_parts += [f"<h3>{_html.escape(title)}</h3>", f_df.to_html()]

    st.download_button(
        "Descarregar relatório (HTML)",
        data="<html><meta charset='utf-8'><body style='font-family:sans-serif'>" + "".join(html_parts) + "</body></html>",
        file_name=f"DDM_{d['ticker']}.html", mime="text/html",
    )
