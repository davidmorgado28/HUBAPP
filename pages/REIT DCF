"""
DCF para REITs — Valorização baseada em AFFO por Ação
Segue o padrão da Luminara Capital: theme.py, data_editor sem sync-back,
validação explícita de dados, transparência sobre limitações.

Renomear este ficheiro para seguir a tua convenção numerada+emoji
(ex: '7_🏢_DCF_REITs.py') antes de colocar em pages/.
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

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
# Input do ticker
# ---------------------------------------------------------------------------
ticker_input = st.text_input("Ticker do REIT", value="O").upper().strip()

if not ticker_input:
    st.stop()

if "reit_dcf_ticker" not in st.session_state or st.session_state["reit_dcf_ticker"] != ticker_input:
    st.session_state["reit_dcf_ticker"] = ticker_input
    st.session_state.pop("affo_editor_data", None)


# ---------------------------------------------------------------------------
# Fetch de dados históricos e cálculo aproximado de AFFO/ação
# ---------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def fetch_affo_inputs(ticker_symbol):
    """
    Vai buscar os inputs para calcular FFO/AFFO por ação dos últimos anos
    disponíveis via yfinance (tipicamente 4, por vezes 5 anos anuais).

    FFO = Resultado Líquido + Depreciação & Amortização
    AFFO = FFO - Capex (usado como proxy de capex recorrente/manutenção)

    Limitação assumida e explícita: o yfinance não expõe separadamente
    ganhos/perdas na venda de imóveis nem o ajuste de "straight-line rent",
    pelo que este é um AFFO aproximado. A tabela final é editável para
    correção manual.
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

    # Colunas mais recentes primeiro -> inverter para ordem cronológica
    years = list(net_income.index)[:N_HIST_YEARS]
    years = sorted(years)

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

        rows.append(
            {
                "Ano": pd.Timestamp(year).year,
                "AFFO/Ação (€)": round(float(affo_per_share), 4),
            }
        )

    if not rows:
        return None, "Não foi possível calcular AFFO/ação com os dados disponíveis."

    warning = None
    if len(rows) < N_HIST_YEARS:
        warning = (
            f"Apenas {len(rows)} de {N_HIST_YEARS} anos com dados completos "
            f"estão disponíveis via Yahoo Finance. Podes completar os restantes "
            f"manualmente na tabela abaixo."
        )

    return pd.DataFrame(rows), warning


affo_df, fetch_msg = fetch_affo_inputs(ticker_input)

st.markdown("### 1. AFFO por Ação — Histórico")
st.caption(
    "Cálculo aproximado (FFO = Resultado Líquido + D&A; AFFO = FFO − Capex). "
    "Não inclui ajustes de ganhos/perdas em vendas de imóveis nem straight-line "
    "rent, por limitação de dados. Revê e corrige os valores se necessário."
)

if affo_df is None:
    st.warning(fetch_msg + " Preenche a tabela manualmente.")
    affo_df = pd.DataFrame(
        {
            "Ano": list(range(pd.Timestamp.today().year - N_HIST_YEARS, pd.Timestamp.today().year)),
            "AFFO/Ação (€)": [np.nan] * N_HIST_YEARS,
        }
    )
elif fetch_msg:
    st.info(fetch_msg)

if "affo_editor_data" not in st.session_state:
    st.session_state["affo_editor_data"] = affo_df

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
# Tabela de taxas de crescimento histórico (derivada, apenas leitura)
# ---------------------------------------------------------------------------
st.markdown("### 2. Taxa de Crescimento Histórica do AFFO/Ação")

affo_series = affo_edited["AFFO/Ação (€)"].astype(object)
growth_rows = []
for i in range(1, len(affo_edited)):
    prev_val = affo_edited["AFFO/Ação (€)"].iloc[i - 1]
    curr_val = affo_edited["AFFO/Ação (€)"].iloc[i]
    if pd.isna(prev_val) or pd.isna(curr_val) or prev_val == 0:
        growth = None
    else:
        growth = (curr_val / prev_val - 1) * 100

    if growth is None:
        growth_display = "n/d"
    else:
        growth_display = f"{growth:.2f}%"

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
cagr_hist = float(np.mean(valid_growths)) if valid_growths else 0.0

# ---------------------------------------------------------------------------
# Tabela 3x5 de premissas de crescimento futuro
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
        **{
            f"Ano {y}": st.column_config.NumberColumn(f"Ano {y} (%)", format="%.2f")
            for y in proj_years
        },
    },
)

# ---------------------------------------------------------------------------
# CAPM automático
# ---------------------------------------------------------------------------
st.markdown("### 4. Custo de Capital Próprio (CAPM)")


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

    return float(beta), float(risk_free_rate), current_price


beta_val, rf_val, current_price = fetch_capm_inputs(ticker_input)

capm_col1, capm_col2, capm_col3, capm_col4 = st.columns(4)
with capm_col1:
    beta_input = st.number_input("Beta", value=round(beta_val, 3), step=0.05)
with capm_col2:
    rf_input = st.number_input(
        "Taxa Sem Risco (%) — 10Y Treasury", value=round(rf_val * 100, 2), step=0.05
    )
with capm_col3:
    erp_input = st.number_input(
        "Prémio de Risco de Mercado (%)",
        value=5.5,
        step=0.1,
        help="Estimativa editável — não é obtida automaticamente. Referência comum: 4.5%-6%.",
    )
with capm_col4:
    ke = rf_input + beta_input * erp_input
    st.metric("Custo de Capital Próprio (Ke)", f"{ke:.2f}%")

# ---------------------------------------------------------------------------
# Taxas de crescimento terminal por cenário
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
# Cálculo da valorização
# ---------------------------------------------------------------------------
st.markdown("### 6. Resultado da Valorização")

last_affo = affo_edited["AFFO/Ação (€)"].iloc[-1] if len(affo_edited) else None

if pd.isna(last_affo) or last_affo is None:
    st.error("Preenche o AFFO/Ação do último ano histórico para calcular a valorização.")
    st.stop()

discount_rate = ke / 100

results = []
for scenario in SCENARIOS:
    row = growth_proj_edited[growth_proj_edited["Cenário"] == scenario].iloc[0]
    tgr = tgr_map[scenario] / 100

    if discount_rate <= tgr:
        results.append(
            {
                "Cenário": scenario,
                "Valor Justo/Ação (€)": None,
                "Erro": "Ke deve ser superior à TGR para este cenário.",
            }
        )
        continue

    projected = []
    current_affo = float(last_affo)
    for y in proj_years:
        g = float(row[f"Ano {y}"]) / 100
        current_affo = current_affo * (1 + g)
        projected.append(current_affo)

    discounted = [
        cf / ((1 + discount_rate) ** (i + 1)) for i, cf in enumerate(projected)
    ]
    terminal_value = projected[-1] * (1 + tgr) / (discount_rate - tgr)
    discounted_tv = terminal_value / ((1 + discount_rate) ** N_PROJ_YEARS)

    fair_value = sum(discounted) + discounted_tv

    results.append(
        {
            "Cenário": scenario,
            "Valor Justo/Ação (€)": round(fair_value, 2),
            "Erro": None,
        }
    )

results_df = pd.DataFrame(results)

display_cols = ["Cenário", "Valor Justo/Ação (€)"]
display_df = results_df[display_cols].copy()
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
                st.metric(
                    scenario,
                    f"€{fair:.2f}",
                    delta=f"{upside:+.1f}% vs €{current_price:.2f} atual",
                )
else:
    st.caption("Preço de mercado atual não disponível para comparação.")
