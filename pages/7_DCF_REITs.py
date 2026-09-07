"""
DCF para REITs — Valorização baseada em AFFO por Ação
Fluxo: Pesquisar ticker -> tabelas históricas + inputs editáveis -> Simular -> resultados + download HTML

Segue o padrão do DCF Valuation Model existente no hub: fetch só ao clicar em
Pesquisar (sem refetch a cada interação), data_editor sem sync-back manual
para session_state, resultados só calculados ao clicar em Simular.

Renomear para a tua convenção numerada+emoji (ex: '7_🏢_DCF_REITs.py') antes
de colocar em pages/.
"""

import io
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

# ---------------------------------------------------------------------------
# Tema (com fallback, seguindo o padrão do hub)
# ---------------------------------------------------------------------------
try:
    from theme import inject_theme, page_header, NAVY_950, GOLD_500, IVORY
except ImportError:
    NAVY_950 = "#0A1128"
    GOLD_500 = "#D4AF37"
    IVORY = "#FFFFF0"

    def inject_theme():
        pass

    def page_header(title, subtitle=None):
        st.title(title)
        if subtitle:
            st.caption(subtitle)


st.set_page_config(page_title="DCF REITs · AFFO", page_icon="🏢", layout="wide")
inject_theme()
page_header(
    "DCF para REITs",
    "Valorização por Adjusted Funds From Operations (AFFO) por ação",
)

N_HIST_YEARS = 5
N_PROJ_YEARS = 5
SCENARIOS = ["Pessimista", "Base", "Otimista"]

# ---------------------------------------------------------------------------
# Funções de fetch (cacheadas — só correm quando chamadas explicitamente)
# ---------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def fetch_affo_inputs(ticker_symbol):
    """
    FFO = Resultado Líquido + Depreciação & Amortização
    AFFO = FFO - Capex (proxy de capex recorrente/manutenção)

    Limitação explícita: yfinance não expõe separadamente ganhos/perdas em
    vendas de imóveis nem o ajuste de straight-line rent -> AFFO aproximado.
    """
    tk = yf.Ticker(ticker_symbol)
    financials = tk.financials
    cashflow = tk.cashflow

    if financials is None or financials.empty or cashflow is None or cashflow.empty:
        return None, "Não foi possível obter dados financeiros para este ticker."

    def get_row(df, candidates):
        for name in candidates:
            if name in df.index:
                return df.loc[name]
        return None

    net_income = get_row(financials, ["Net Income", "Net Income Common Stockholders"])
    da = get_row(cashflow, ["Depreciation And Amortization", "Depreciation Amortization Depletion"])
    capex = get_row(cashflow, ["Capital Expenditure", "Purchase Of PPE"])
    diluted_shares = get_row(financials, ["Diluted Average Shares", "Basic Average Shares"])

    missing = []
    if net_income is None:
        missing.append("Resultado Líquido")
    if da is None:
        missing.append("Depreciação & Amortização")
    if diluted_shares is None:
        missing.append("Ações Diluídas")

    if missing:
        return None, f"Dados em falta na Yahoo Finance: {', '.join(missing)}."

    years = sorted(list(net_income.index)[:N_HIST_YEARS])

    rows = []
    for year in years:
        ni = net_income.get(year, np.nan)
        d_a = da.get(year, np.nan) if da is not None else np.nan
        cpx = capex.get(year, np.nan) if capex is not None else 0.0
        shares = diluted_shares.get(year, np.nan)

        if pd.isna(ni) or pd.isna(d_a) or pd.isna(shares) or shares == 0:
            continue

        cpx = 0.0 if pd.isna(cpx) else abs(cpx)
        ffo = ni + d_a
        affo = ffo - cpx
        affo_per_share = affo / shares

        rows.append({"Ano": pd.Timestamp(year).year, "AFFO/Ação (€)": round(float(affo_per_share), 4)})

    if not rows:
        return None, "Não foi possível calcular AFFO/ação com os dados disponíveis."

    warning = None
    if len(rows) < N_HIST_YEARS:
        warning = (
            f"Apenas {len(rows)} de {N_HIST_YEARS} anos com dados completos estão "
            f"disponíveis via Yahoo Finance. Completa os restantes manualmente."
        )

    return pd.DataFrame(rows), warning


@st.cache_data(ttl=3600)
def fetch_capm_inputs(ticker_symbol):
    tk = yf.Ticker(ticker_symbol)
    info = tk.info

    beta = info.get("beta", None)
    if beta is None:
        beta = 1.0

    try:
        rf_hist = yf.Ticker("^TNX").history(period="5d")
        risk_free_rate = float(rf_hist["Close"].iloc[-1]) / 100
    except Exception:
        risk_free_rate = 0.04

    current_price = info.get("currentPrice") or info.get("regularMarketPrice")
    company_name = info.get("longName") or info.get("shortName") or ticker_symbol

    return float(beta), float(risk_free_rate), current_price, company_name


def generate_html_report(ticker, company_name, affo_df, growth_hist_df, growth_proj_df,
                          capm, tgr_map, results_df, current_price):
    date_str = datetime.now().strftime("%d/%m/%Y %H:%M")

    def df_to_html_rows(df):
        return "".join(
            "<tr>" + "".join(f"<td>{v}</td>" for v in row) + "</tr>"
            for row in df.itertuples(index=False)
        )

    results_rows = ""
    for _, r in results_df.iterrows():
        value_display = r["Valor Justo/Ação (€)"]
        if value_display is None:
            value_display = r.get("Erro", "n/d")
        else:
            value_display = f"€{value_display:.2f}"
        upside_display = ""
        if current_price and isinstance(r["Valor Justo/Ação (€)"], (int, float)):
            upside = (r["Valor Justo/Ação (€)"] / current_price - 1) * 100
            upside_display = f"{upside:+.1f}%"
        results_rows += f"<tr><td>{r['Cenário']}</td><td>{value_display}</td><td>{upside_display}</td></tr>"

    html = f"""
<!DOCTYPE html>
<html lang="pt">
<head>
<meta charset="UTF-8">
<title>DCF REIT — {ticker}</title>
<style>
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background: {IVORY}; color: {NAVY_950}; margin: 0; padding: 40px; }}
  .container {{ max-width: 900px; margin: 0 auto; }}
  h1 {{ color: {NAVY_950}; border-bottom: 3px solid {GOLD_500}; padding-bottom: 12px; }}
  h2 {{ color: {NAVY_950}; margin-top: 36px; border-left: 4px solid {GOLD_500}; padding-left: 10px; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
  th {{ background: {NAVY_950}; color: {GOLD_500}; padding: 10px; text-align: left; }}
  td {{ padding: 8px 10px; border-bottom: 1px solid #ddd; }}
  .meta {{ color: #555; font-size: 0.9em; }}
  .footer {{ margin-top: 40px; font-size: 0.8em; color: #888; }}
</style>
</head>
<body>
<div class="container">
  <h1>Luminara Capital — DCF REIT: {ticker}</h1>
  <p class="meta">{company_name} · Relatório gerado em {date_str}</p>

  <h2>1. AFFO/Ação — Histórico</h2>
  <table><tr><th>Ano</th><th>AFFO/Ação (€)</th></tr>{df_to_html_rows(affo_df)}</table>

  <h2>2. Crescimento Histórico</h2>
  <table><tr><th>Período</th><th>Crescimento AFFO/Ação</th></tr>{df_to_html_rows(growth_hist_df)}</table>

  <h2>3. Premissas de Crescimento Projetado</h2>
  <table><tr>{"".join(f"<th>{c}</th>" for c in growth_proj_df.columns)}</tr>{df_to_html_rows(growth_proj_df)}</table>

  <h2>4. CAPM</h2>
  <table>
    <tr><th>Beta</th><td>{capm['beta']:.3f}</td></tr>
    <tr><th>Taxa Sem Risco</th><td>{capm['rf']:.2f}%</td></tr>
    <tr><th>Prémio de Risco de Mercado</th><td>{capm['erp']:.2f}%</td></tr>
    <tr><th>Custo de Capital Próprio (Ke)</th><td>{capm['ke']:.2f}%</td></tr>
  </table>

  <h2>5. Taxa de Crescimento Terminal (TGR)</h2>
  <table>
    <tr><th>Pessimista</th><td>{tgr_map['Pessimista']:.2f}%</td></tr>
    <tr><th>Base</th><td>{tgr_map['Base']:.2f}%</td></tr>
    <tr><th>Otimista</th><td>{tgr_map['Otimista']:.2f}%</td></tr>
  </table>

  <h2>6. Resultado da Valorização</h2>
  <table><tr><th>Cenário</th><th>Valor Justo/Ação</th><th>Upside vs. Preço Atual</th></tr>{results_rows}</table>
  <p class="meta">Preço de mercado no momento do fetch: {"€%.2f" % current_price if current_price else "n/d"}</p>

  <div class="footer">
    Relatório gerado pela ferramenta de DCF para REITs — Luminara Capital.<br>
    AFFO calculado de forma aproximada a partir de dados públicos (Yahoo Finance).
    Não constitui aconselhamento financeiro.
  </div>
</div>
</body>
</html>
"""
    return html


# ---------------------------------------------------------------------------
# 0. Input do ticker + botão Pesquisar
# ---------------------------------------------------------------------------
col_ticker, col_btn = st.columns([3, 1])
with col_ticker:
    ticker_input = st.text_input("Ticker do REIT", value="O", label_visibility="visible").upper().strip()
with col_btn:
    st.markdown("<div style='height: 28px'></div>", unsafe_allow_html=True)
    search_clicked = st.button("🔍 Pesquisar", type="primary", use_container_width=True)

if search_clicked and ticker_input:
    with st.spinner(f"A obter dados de {ticker_input}..."):
        affo_df, fetch_msg = fetch_affo_inputs(ticker_input)
        beta_val, rf_val, current_price, company_name = fetch_capm_inputs(ticker_input)

    if affo_df is None:
        st.warning(fetch_msg + " Podes preencher a tabela manualmente abaixo.")
        affo_df = pd.DataFrame(
            {
                "Ano": list(range(pd.Timestamp.today().year - N_HIST_YEARS, pd.Timestamp.today().year)),
                "AFFO/Ação (€)": [np.nan] * N_HIST_YEARS,
            }
        )
    elif fetch_msg:
        st.info(fetch_msg)

    st.session_state["reit_ticker"] = ticker_input
    st.session_state["company_name"] = company_name
    st.session_state["affo_editor_data"] = affo_df
    st.session_state["capm_defaults"] = {"beta": beta_val, "rf": rf_val * 100}
    st.session_state["current_price"] = current_price
    # Reset projeções e resultados ao pesquisar um novo ticker
    st.session_state.pop("growth_editor_data", None)
    st.session_state.pop("simulation_results", None)

if "reit_ticker" not in st.session_state:
    st.info("Insere um ticker e clica em **Pesquisar** para carregar os dados históricos.")
    st.stop()

st.caption(f"Dados carregados para **{st.session_state['reit_ticker']}** — {st.session_state.get('company_name', '')}")

# ---------------------------------------------------------------------------
# 1. AFFO histórico (editável)
# ---------------------------------------------------------------------------
st.markdown("### 1. AFFO por Ação — Histórico")
st.caption(
    "Cálculo aproximado (FFO = Resultado Líquido + D&A; AFFO = FFO − Capex). "
    "Revê e corrige os valores se necessário."
)

affo_edited = st.data_editor(
    st.session_state["affo_editor_data"],
    key="affo_editor",
    num_rows="fixed",
    use_container_width=True,
    column_config={
        "Ano": st.column_config.NumberColumn("Ano", disabled=True, format="%d"),
        "AFFO/Ação (€)": st.column_config.NumberColumn("AFFO/Ação (€)", format="%.4f"),
    },
)

# ---------------------------------------------------------------------------
# 2. Crescimento histórico (derivado, só leitura)
# ---------------------------------------------------------------------------
st.markdown("### 2. Taxa de Crescimento Histórica do AFFO/Ação")

growth_rows = []
for i in range(1, len(affo_edited)):
    prev_val = affo_edited["AFFO/Ação (€)"].iloc[i - 1]
    curr_val = affo_edited["AFFO/Ação (€)"].iloc[i]
    if pd.isna(prev_val) or pd.isna(curr_val) or prev_val == 0:
        growth_display = "n/d"
    else:
        growth_display = f"{(curr_val / prev_val - 1) * 100:.2f}%"
    growth_rows.append(
        {
            "Período": f"{affo_edited['Ano'].iloc[i - 1]} → {affo_edited['Ano'].iloc[i]}",
            "Crescimento AFFO/Ação": growth_display,
        }
    )

growth_hist_df = pd.DataFrame(growth_rows)
st.dataframe(growth_hist_df, use_container_width=True, hide_index=True)

valid_growths = [
    (affo_edited["AFFO/Ação (€)"].iloc[i] / affo_edited["AFFO/Ação (€)"].iloc[i - 1] - 1) * 100
    for i in range(1, len(affo_edited))
    if not pd.isna(affo_edited["AFFO/Ação (€)"].iloc[i - 1])
    and not pd.isna(affo_edited["AFFO/Ação (€)"].iloc[i])
    and affo_edited["AFFO/Ação (€)"].iloc[i - 1] != 0
]
cagr_hist = float(np.mean(valid_growths)) if valid_growths else 2.0

# ---------------------------------------------------------------------------
# 3. Premissas de crescimento projetado (editável, 3x5)
# ---------------------------------------------------------------------------
st.markdown("### 3. Premissas de Crescimento do AFFO/Ação — Próximos 5 Anos")
st.caption("Define a taxa de crescimento anual (%) para cada cenário.")

last_year = int(affo_edited["Ano"].iloc[-1]) if len(affo_edited) else pd.Timestamp.today().year
proj_years = [last_year + i for i in range(1, N_PROJ_YEARS + 1)]

if "growth_editor_data" not in st.session_state:
    st.session_state["growth_editor_data"] = pd.DataFrame(
        {
            "Cenário": SCENARIOS,
            **{f"Ano {y}": [round(cagr_hist, 2)] * 3 for y in proj_years},
        }
    )

growth_proj_edited = st.data_editor(
    st.session_state["growth_editor_data"],
    key="growth_editor",
    num_rows="fixed",
    use_container_width=True,
    column_config={
        "Cenário": st.column_config.TextColumn("Cenário", disabled=True),
        **{f"Ano {y}": st.column_config.NumberColumn(f"Ano {y} (%)", format="%.2f") for y in proj_years},
    },
)

# ---------------------------------------------------------------------------
# 4. CAPM
# ---------------------------------------------------------------------------
st.markdown("### 4. Custo de Capital Próprio (CAPM)")

capm_defaults = st.session_state["capm_defaults"]

capm_col1, capm_col2, capm_col3, capm_col4 = st.columns(4)
with capm_col1:
    beta_input = st.number_input("Beta", value=round(capm_defaults["beta"], 3), step=0.05, key="beta_input")
with capm_col2:
    rf_input = st.number_input(
        "Taxa Sem Risco (%) — 10Y Treasury", value=round(capm_defaults["rf"], 2), step=0.05, key="rf_input"
    )
with capm_col3:
    erp_input = st.number_input(
        "Prémio de Risco de Mercado (%)",
        value=5.5,
        step=0.1,
        key="erp_input",
        help="Estimativa editável, não obtida automaticamente. Referência comum: 4.5%-6%.",
    )
with capm_col4:
    ke = rf_input + beta_input * erp_input
    st.metric("Ke", f"{ke:.2f}%")

# ---------------------------------------------------------------------------
# 5. TGR por cenário
# ---------------------------------------------------------------------------
st.markdown("### 5. Taxa de Crescimento Terminal (TGR) por Cenário")

tgr_col1, tgr_col2, tgr_col3 = st.columns(3)
with tgr_col1:
    tgr_pessimista = st.number_input("TGR — Pessimista (%)", value=1.5, step=0.1, key="tgr_pess")
with tgr_col2:
    tgr_base = st.number_input("TGR — Base (%)", value=2.5, step=0.1, key="tgr_base")
with tgr_col3:
    tgr_otimista = st.number_input("TGR — Otimista (%)", value=3.5, step=0.1, key="tgr_otim")

tgr_map = {"Pessimista": tgr_pessimista, "Base": tgr_base, "Otimista": tgr_otimista}

# ---------------------------------------------------------------------------
# 6. Botão Simular
# ---------------------------------------------------------------------------
st.markdown("---")
simulate_clicked = st.button("🚀 Simular Valorização", type="primary", use_container_width=True)

if simulate_clicked:
    last_affo = affo_edited["AFFO/Ação (€)"].iloc[-1] if len(affo_edited) else None

    if pd.isna(last_affo) or last_affo is None:
        st.error("Preenche o AFFO/Ação do último ano histórico antes de simular.")
    else:
        discount_rate = ke / 100
        results = []
        for scenario in SCENARIOS:
            row = growth_proj_edited[growth_proj_edited["Cenário"] == scenario].iloc[0]
            tgr = tgr_map[scenario] / 100

            if discount_rate <= tgr:
                results.append({"Cenário": scenario, "Valor Justo/Ação (€)": None, "Erro": "Ke deve ser superior à TGR."})
                continue

            projected = []
            current_affo = float(last_affo)
            for y in proj_years:
                g = float(row[f"Ano {y}"]) / 100
                current_affo = current_affo * (1 + g)
                projected.append(current_affo)

            discounted = [cf / ((1 + discount_rate) ** (i + 1)) for i, cf in enumerate(projected)]
            terminal_value = projected[-1] * (1 + tgr) / (discount_rate - tgr)
            discounted_tv = terminal_value / ((1 + discount_rate) ** N_PROJ_YEARS)
            fair_value = sum(discounted) + discounted_tv

            results.append({"Cenário": scenario, "Valor Justo/Ação (€)": round(fair_value, 2), "Erro": None})

        st.session_state["simulation_results"] = {
            "results_df": pd.DataFrame(results),
            "affo_df": affo_edited.copy(),
            "growth_hist_df": growth_hist_df.copy(),
            "growth_proj_df": growth_proj_edited.copy(),
            "capm": {"beta": beta_input, "rf": rf_input, "erp": erp_input, "ke": ke},
            "tgr_map": tgr_map,
            "current_price": st.session_state.get("current_price"),
        }

# ---------------------------------------------------------------------------
# 7. Resultados + download HTML
# ---------------------------------------------------------------------------
if "simulation_results" in st.session_state:
    sim = st.session_state["simulation_results"]
    results_df = sim["results_df"]
    current_price = sim["current_price"]

    st.markdown("### 6. Resultado da Valorização")

    display_df = results_df[["Cenário", "Valor Justo/Ação (€)"]].copy()
    display_df["Valor Justo/Ação (€)"] = display_df["Valor Justo/Ação (€)"].astype(object)
    for i, r in results_df.iterrows():
        if r["Erro"]:
            display_df.at[i, "Valor Justo/Ação (€)"] = r["Erro"]

    st.dataframe(display_df, use_container_width=True, hide_index=True)

    if current_price:
        st.markdown("#### Comparação com Preço de Mercado")
        price_cols = st.columns(3)
        for idx, scenario in enumerate(SCENARIOS):
            fair = results_df[results_df["Cenário"] == scenario]["Valor Justo/Ação (€)"].iloc[0]
            with price_cols[idx]:
                if fair is None:
                    st.metric(scenario, "n/d")
                else:
                    upside = (fair / current_price - 1) * 100
                    st.metric(scenario, f"€{fair:.2f}", delta=f"{upside:+.1f}% vs €{current_price:.2f} atual")
    else:
        st.caption("Preço de mercado atual não disponível para comparação.")

    html_report = generate_html_report(
        ticker=st.session_state["reit_ticker"],
        company_name=st.session_state.get("company_name", ""),
        affo_df=sim["affo_df"],
        growth_hist_df=sim["growth_hist_df"],
        growth_proj_df=sim["growth_proj_df"],
        capm=sim["capm"],
        tgr_map=sim["tgr_map"],
        results_df=results_df,
        current_price=current_price,
    )

    st.download_button(
        label="⬇️ Download Relatório HTML",
        data=html_report,
        file_name=f"DCF_REIT_{st.session_state['reit_ticker']}_{datetime.now().strftime('%Y%m%d')}.html",
        mime="text/html",
        use_container_width=True,
    )
