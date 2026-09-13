# ==============================================================================
# 📑 PEER BENCHMARK & VALUATION COMPARATIVO — Aplicação Streamlit
# Versão focada exclusivamente na comparação de rácios com pares (peers)
# escolhidos manualmente, seguida da análise textual. Todas as restantes
# secções (valuation histórico, crescimento, rentabilidade, alavancagem,
# liquidez, mercado) foram removidas a pedido.
#
# CORREÇÃO IMPORTANTE face à versão anterior:
# Os rácios anteriores misturavam dados ANUAIS (último ano fiscal, que pode
# ter 6-18 meses face à data de hoje) com o preço de mercado em TEMPO REAL
# (P/E, EV/EBITDA vindos do campo `info` da Yahoo, que é TTM). Isso produzia
# valores desalinhados face a sites que usam sempre TTM (últimos 4 trimestres).
# Agora todos os rácios são calculados em base TTM (trailing twelve months)
# a partir dos dados trimestrais mais recentes, com fallback explícito e
# visível para dados anuais quando não há trimestres suficientes.
# ==============================================================================

import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from theme import inject_theme, page_header

st.set_page_config(
    page_title="Peer Benchmark & Valuation",
    page_icon="📑",
    layout="wide",
)

inject_theme()

# ------------------------------------------------------------------------------
# ESTILO CSS — paleta OAK & VALUE (branco quente + verde carvalho)
# ------------------------------------------------------------------------------
STYLE_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    .report-container {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        background-color: #F1EEE4;
        color: #1C2420;
        padding: 30px;
        border-radius: 16px;
        box-shadow: 0 10px 25px -5px rgba(30,46,34,0.08), 0 8px 10px -6px rgba(30,46,34,0.02);
        max-width: 1200px;
        margin: 0 auto;
    }

    .header-card {
        background: linear-gradient(135deg, #1E2E22 0%, #2F4A38 100%);
        color: #F1EEE4;
        padding: 28px 32px;
        border-radius: 14px;
        margin-bottom: 30px;
        box-shadow: 0 10px 20px rgba(30, 46, 34, 0.18);
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 15px;
    }

    .header-card h1 { margin: 0; font-size: 26px; font-weight: 700; letter-spacing: -0.5px; color: #F1EEE4; }
    .header-card .subtitle { color: #B7CCBB; font-size: 13px; margin-top: 6px; font-weight: 400; }

    .badge-sector {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(8px);
        border: 1px solid rgba(255, 255, 255, 0.15);
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 500;
        color: #DCE6DE;
    }

    .section-title {
        font-size: 16px; font-weight: 600; color: #1E2E22; margin-top: 32px; margin-bottom: 14px;
        display: flex; align-items: center; gap: 8px; letter-spacing: -0.2px;
    }
    .section-title::before { content: ''; display: inline-block; width: 4px; height: 18px; background: #2E7D4C; border-radius: 2px; }

    .freshness-note {
        font-size: 12px; color: #4F7058; margin-top: -6px; margin-bottom: 18px;
    }

    .table-wrapper {
        background: #FFFFFF; border-radius: 12px; border: 1px solid rgba(47,74,56,0.15); overflow: hidden;
        margin-bottom: 24px; box-shadow: 0 1px 3px rgba(30,46,34,0.04);
    }

    .finance-table { border-collapse: collapse; width: 100%; font-size: 13px; margin: 0; }
    .finance-table th {
        background-color: #DCE6DE; color: #4F7058; text-align: right; padding: 12px 16px;
        font-weight: 600; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px;
        border-bottom: 1px solid rgba(47,74,56,0.15);
    }
    .finance-table th:first-child { text-align: left; }
    .finance-table td {
        border-bottom: 1px solid rgba(47,74,56,0.08); padding: 11px 16px; text-align: right; color: #1C2420;
        font-variant-numeric: tabular-nums;
    }
    .finance-table td:first-child {
        font-weight: 600; text-align: left; color: #1E2E22; background-color: #F2F5F0; width: 250px;
    }
    .finance-table tr:last-child td { border-bottom: none; }
    .finance-table tr:hover td { background-color: rgba(47,74,56,0.05); }
    .finance-table tr:hover td:first-child { background-color: #DCE6DE; }

    .analysis-card {
        background: #FFFFFF; border: 1px solid rgba(47,74,56,0.15); border-left: 5px solid #2E7D4C; border-radius: 12px;
        padding: 24px; margin-top: 25px; font-size: 14px; line-height: 1.7; color: #1C2420;
        box-shadow: 0 4px 6px -1px rgba(30,46,34,0.05);
    }
    .analysis-card h3 { margin-top: 0; color: #1E2E22; font-size: 16px; font-weight: 600; margin-bottom: 12px; }
    .analysis-card p { margin: 0 0 12px 0; }
    .analysis-card p:last-child { margin-bottom: 0; }

    .badge {
        display: inline-block; padding: 4px 10px; border-radius: 9999px;
        font-size: 11px; font-weight: 600; letter-spacing: 0.02em;
    }
    .badge-success { background: #dcfce7; color: #166534; }
    .badge-warning { background: #fef3c7; color: #92400e; }
    .badge-danger { background: #fee2e2; color: #991b1b; }
    .badge-info { background: #dbeafe; color: #1e40af; }
    .badge-neutral { background: #DCE6DE; color: #4F7058; }
</style>
"""

MAX_PEERS = 6
FRESHNESS_ROW = "Dados de Referência"

# ------------------------------------------------------------------------------
# LÓGICA DE CÁLCULO
# ------------------------------------------------------------------------------
def safe_div(num, denom):
    if denom is None or num is None:
        return np.nan
    try:
        if denom == 0 or np.isnan(denom) or np.isnan(num):
            return np.nan
    except TypeError:
        return np.nan
    return num / denom


def _fmt_period_label(col):
    """Converte a coluna de um DataFrame trimestral/anual do yfinance
    (Timestamp) numa etiqueta legível AAAA-MM."""
    try:
        return pd.to_datetime(col).strftime("%Y-%m")
    except Exception:
        return str(col)[:7]


def compute_ttm_metrics(ticker_symbol):
    """Calcula os rácios de um ticker em base TTM (últimos 4 trimestres),
    com fallback explícito para o último ano fiscal disponível quando não
    há pelo menos 4 trimestres de dados. Nunca mistura silenciosamente
    dados de datas diferentes sem assinalar a origem na linha
    'Dados de Referência'."""
    t = yf.Ticker(ticker_symbol)
    inf = t.info

    price = inf.get("currentPrice") or inf.get("regularMarketPrice")
    shares = inf.get("sharesOutstanding")

    if not inf or price is None:
        raise ValueError(f"Sem dados de mercado disponíveis para '{ticker_symbol}'.")

    q_inc = t.quarterly_financials
    q_bs = t.quarterly_balance_sheet
    a_inc = t.financials
    a_bs = t.balance_sheet

    has_ttm = (
        q_inc is not None and not q_inc.empty and q_inc.shape[1] >= 4
        and "Total Revenue" in q_inc.index
        and q_bs is not None and not q_bs.empty
    )

    if has_ttm:
        source_label = f"TTM (4 trimestres até {_fmt_period_label(q_inc.columns[0])})"

        def q_sum(row_name, n=4):
            if row_name not in q_inc.index:
                return np.nan
            return q_inc.loc[row_name].iloc[:n].sum()

        ttm_revenue = q_sum("Total Revenue")
        ttm_net_income = q_sum("Net Income")

        if "EBITDA" in q_inc.index:
            ttm_ebitda = q_sum("EBITDA")
        elif "EBIT" in q_inc.index and "Reconciled Depreciation" in q_inc.index:
            ttm_ebitda = q_sum("EBIT") + q_sum("Reconciled Depreciation")
        else:
            ttm_ebitda = np.nan

        latest_equity = q_bs.loc["Stockholders Equity"].iloc[0] if "Stockholders Equity" in q_bs.index else np.nan
        latest_debt = q_bs.loc["Total Debt"].iloc[0] if "Total Debt" in q_bs.index else np.nan
        latest_cash = q_bs.loc["Cash And Cash Equivalents"].iloc[0] if "Cash And Cash Equivalents" in q_bs.index else 0
        latest_curr_assets = q_bs.loc["Current Assets"].iloc[0] if "Current Assets" in q_bs.index else np.nan
        latest_curr_liab = q_bs.loc["Current Liabilities"].iloc[0] if "Current Liabilities" in q_bs.index else np.nan

        # Crescimento de receita YoY: trimestre mais recente vs. o mesmo trimestre há 1 ano
        if q_inc.shape[1] >= 5:
            rev_now = q_inc.loc["Total Revenue"].iloc[0]
            rev_year_ago = q_inc.loc["Total Revenue"].iloc[4]
            rev_growth = safe_div(rev_now - rev_year_ago, abs(rev_year_ago) if pd.notna(rev_year_ago) else np.nan)
        else:
            rev_growth = inf.get("revenueGrowth", np.nan)
    else:
        # Fallback: último ano fiscal completo disponível (assinalado como tal)
        if a_inc is None or a_inc.empty or a_bs is None or a_bs.empty:
            raise ValueError(f"Dados financeiros insuficientes (trimestrais e anuais) para '{ticker_symbol}'.")

        fiscal_year = _fmt_period_label(a_inc.columns[0])
        source_label = f"Anual — dados trimestrais insuficientes (ano fiscal {fiscal_year})"

        ttm_revenue = a_inc.loc["Total Revenue"].iloc[0] if "Total Revenue" in a_inc.index else np.nan
        ttm_net_income = a_inc.loc["Net Income"].iloc[0] if "Net Income" in a_inc.index else np.nan
        ttm_ebitda = a_inc.loc["EBITDA"].iloc[0] if "EBITDA" in a_inc.index else np.nan

        latest_equity = a_bs.loc["Stockholders Equity"].iloc[0] if "Stockholders Equity" in a_bs.index else np.nan
        latest_debt = a_bs.loc["Total Debt"].iloc[0] if "Total Debt" in a_bs.index else np.nan
        latest_cash = a_bs.loc["Cash And Cash Equivalents"].iloc[0] if "Cash And Cash Equivalents" in a_bs.index else 0
        latest_curr_assets = a_bs.loc["Current Assets"].iloc[0] if "Current Assets" in a_bs.index else np.nan
        latest_curr_liab = a_bs.loc["Current Liabilities"].iloc[0] if "Current Liabilities" in a_bs.index else np.nan

        rev_growth = inf.get("revenueGrowth", np.nan)

    market_cap = (price * shares) if (price and shares) else inf.get("marketCap", np.nan)
    enterprise_value = (
        market_cap + latest_debt - latest_cash
        if pd.notna(market_cap) and pd.notna(latest_debt)
        else np.nan
    )

    pe = safe_div(market_cap, ttm_net_income)
    if pd.isna(pe):
        pe = inf.get("trailingPE", np.nan)

    ev_ebitda = safe_div(enterprise_value, ttm_ebitda)
    if pd.isna(ev_ebitda):
        ev_ebitda = inf.get("enterpriseToEbitda", np.nan)

    ev_rev = safe_div(enterprise_value, ttm_revenue)
    if pd.isna(ev_rev):
        ev_rev = inf.get("enterpriseToRevenue", np.nan)

    metrics = {
        FRESHNESS_ROW: source_label,
        "P/E": pe,
        "Forward P/E": inf.get("forwardPE", np.nan),
        "EV/EBITDA": ev_ebitda,
        "P/S (EV/Rev)": ev_rev,
        "Revenue Growth (YoY)": rev_growth,
        "ROE": safe_div(ttm_net_income, latest_equity),
        "EBITDA Margin": safe_div(ttm_ebitda, ttm_revenue),
        "Net Margin": safe_div(ttm_net_income, ttm_revenue),
        "Debt/Equity": safe_div(latest_debt, latest_equity),
        "Current Ratio": safe_div(latest_curr_assets, latest_curr_liab),
    }
    return metrics, inf


def parse_peer_tickers(raw_text, main_ticker):
    """Converte o texto livre de peers numa lista limpa, sem duplicados
    e sem o próprio ticker principal. Não faz nenhuma seleção automática:
    apenas normaliza o que o utilizador escreveu."""
    if not raw_text or not raw_text.strip():
        return [], []

    candidates = [p.strip().upper() for p in raw_text.split(",") if p.strip()]

    seen = set()
    cleaned = []
    dropped_self = []
    for c in candidates:
        if c == main_ticker:
            dropped_self.append(c)
            continue
        if c not in seen:
            seen.add(c)
            cleaned.append(c)

    return cleaned, dropped_self


@st.cache_data(show_spinner=False, ttl=3600)
def fetch_peer_benchmark(ticker_symbol, peers_list):
    """Vai buscar os rácios TTM apenas para os tickers explicitamente
    fornecidos pelo utilizador. Nenhum peer é sugerido, adivinhado ou
    preenchido automaticamente — se um ticker falhar, é simplesmente
    ignorado e reportado, nunca substituído silenciosamente."""
    all_tickers = [ticker_symbol] + peers_list
    comp_data = {}
    failed_tickers = []
    main_info = {}

    for tk in all_tickers:
        try:
            metrics, inf = compute_ttm_metrics(tk)
            comp_data[tk] = metrics
            if tk == ticker_symbol:
                main_info = inf
        except Exception:
            if tk != ticker_symbol:
                failed_tickers.append(tk)
            else:
                raise

    return pd.DataFrame(comp_data), failed_tickers, main_info


def generate_peer_appreciation(ticker_symbol, df_comp):
    if ticker_symbol not in df_comp.columns:
        return "Dados insuficientes para gerar a análise comparativa automatizada."

    peers_only = df_comp.drop(columns=[ticker_symbol])
    if peers_only.empty:
        return "Sem concorrentes válidos para comparação."

    numeric_rows = [r for r in df_comp.index if r != FRESHNESS_ROW]
    target = df_comp.loc[numeric_rows, ticker_symbol]
    peers_median = peers_only.loc[numeric_rows].median(axis=1)

    pe_rel = safe_div(target["P/E"], peers_median["P/E"])
    pe_rel = pe_rel - 1 if pd.notna(pe_rel) else np.nan

    roe_target, roe_peers = target.get("ROE"), peers_median.get("ROE")
    margin_target, margin_peers = target.get("EBITDA Margin"), peers_median.get("EBITDA Margin")
    debt_target, debt_peers = target.get("Debt/Equity"), peers_median.get("Debt/Equity")

    # --- Valuation (P/E vs. mediana dos pares) ---
    if pd.notna(pe_rel):
        if pe_rel < -0.05:
            val_badge = "<span class='badge badge-success'>Desconto vs. Pares</span>"
        elif pe_rel > 0.05:
            val_badge = "<span class='badge badge-warning'>Prémio vs. Pares</span>"
        else:
            val_badge = "<span class='badge badge-info'>Em Linha com os Pares</span>"
        val_txt = f"negoceia a um múltiplo <b>P/E de {target['P/E']:.2f}x</b>, uma variação de <b>{pe_rel*100:+.1f}%</b> face à mediana dos concorrentes ({peers_median['P/E']:.2f}x)"
    else:
        val_badge, val_txt = "<span class='badge badge-neutral'>N/A</span>", "não tem dados suficientes para comparar o múltiplo P/E com os concorrentes"

    # --- Rentabilidade (ROE e Margem EBITDA vs. mediana dos pares) ---
    if pd.notna(roe_target) and pd.notna(roe_peers) and pd.notna(margin_target) and pd.notna(margin_peers):
        if roe_target > roe_peers and margin_target > margin_peers:
            rent_badge = "<span class='badge badge-success'>Acima da Média</span>"
        elif roe_target < roe_peers and margin_target < margin_peers:
            rent_badge = "<span class='badge badge-danger'>Abaixo da Média</span>"
        else:
            rent_badge = "<span class='badge badge-warning'>Mista</span>"
        rent_txt = f"o ROE (TTM) de <b>{roe_target*100:.2f}%</b> compara com uma mediana de <b>{roe_peers*100:.2f}%</b>, e a margem EBITDA (TTM) de <b>{margin_target*100:.2f}%</b> compara com <b>{margin_peers*100:.2f}%</b> no grupo de pares"
    else:
        rent_badge, rent_txt = "<span class='badge badge-neutral'>N/A</span>", "dados de rentabilidade insuficientes para comparação"

    # --- Alavancagem (Debt/Equity vs. mediana dos pares) ---
    if pd.notna(debt_target) and pd.notna(debt_peers):
        debt_badge = "<span class='badge badge-success'>Menos Alavancado</span>" if debt_target < debt_peers else "<span class='badge badge-warning'>Mais Alavancado</span>"
        debt_txt = f"o rácio Debt/Equity de <b>{debt_target:.2f}x</b> compara com a mediana de <b>{debt_peers:.2f}x</b> dos concorrentes diretos"
    else:
        debt_badge, debt_txt = "<span class='badge badge-neutral'>N/A</span>", "Debt/Equity indisponível para comparação"

    text = f"""
    <p>Em termos de valuation, a <b>{ticker_symbol}</b> {val_badge} — {val_txt}.</p>
    <p>Ao nível da rentabilidade, {rent_badge} face aos pares diretos — {rent_txt}.</p>
    <p>Quanto à estrutura de capital, {debt_badge} — {debt_txt}.</p>
    """
    return text


def format_df_to_html(df):
    df_formatted = df.astype(object)
    for col in df_formatted.columns:
        for idx in df_formatted.index:
            val = df_formatted.loc[idx, col]

            if idx == FRESHNESS_ROW:
                df_formatted.loc[idx, col] = f"<span style='color:#4F7058; font-size:12px;'>{val}</span>"
                continue

            if pd.isna(val) or val is None:
                df_formatted.loc[idx, col] = "<span style='color:#8FA096;'>—</span>"
            elif "Growth" in idx or "ROE" in idx or "Margin" in idx:
                color = "#059669" if val > 0 else ("#dc2626" if val < 0 else "#1C2420")
                df_formatted.loc[idx, col] = f"<span style='color:{color}; font-weight:500;'>{val * 100:.2f}%</span>"
            elif "Ratio" in idx:
                df_formatted.loc[idx, col] = f"{val:.2f}"
            else:
                df_formatted.loc[idx, col] = f"{val:.2f}x"

    table_html = df_formatted.to_html(classes="finance-table", escape=False)
    return f"<div class='table-wrapper'>{table_html}</div>"


# ------------------------------------------------------------------------------
# INTERFACE
# ------------------------------------------------------------------------------
page_header(
    "📑",
    "Peer Benchmark & Valuation Comparativo",
    "Comparação de rácios (base TTM) entre a empresa e os concorrentes diretos escolhidos manualmente.",
)

with st.sidebar:
    st.header("⚙️ Empresa")
    ticker_input = st.text_input("Ticker a analisar", value="AAPL")

    st.markdown("---")
    st.header("🏁 Peers para comparação")
    peers_input = st.text_input(
        "Tickers dos concorrentes (separados por vírgula)",
        value="",
        placeholder="Ex.: MSFT, GOOGL, AMZN",
        help=f"Máximo de {MAX_PEERS} tickers. Escolhe tu próprio os concorrentes diretos — a aplicação não sugere peers automaticamente.",
    )

    main_ticker_upper = ticker_input.strip().upper()
    peers_list, dropped_self = parse_peer_tickers(peers_input, main_ticker_upper)

    if dropped_self:
        st.warning(f"⚠️ Removi {', '.join(dropped_self)} da lista de peers, porque coincide com o ticker principal.")

    if len(peers_list) > MAX_PEERS:
        st.warning(f"⚠️ Indicaste {len(peers_list)} peers; apenas os primeiros {MAX_PEERS} serão usados: {', '.join(peers_list[:MAX_PEERS])}")
        peers_list = peers_list[:MAX_PEERS]

    if not peers_input.strip():
        st.info("ℹ️ Indica pelo menos um peer para gerar a comparação.")
    elif peers_list:
        st.caption(f"Peers a usar: {', '.join(peers_list)}")
    else:
        st.error("❌ Nenhum peer válido foi reconhecido nesse texto. Verifica os tickers introduzidos.")

    analyze_button = st.button("📊 Gerar Comparação", type="primary", use_container_width=True, disabled=not peers_list)

if analyze_button and peers_list:
    symbol = main_ticker_upper
    with st.spinner(f"⚡ A extrair dados trimestrais (TTM) para {symbol} e {len(peers_list)} peer(s)..."):
        try:
            df_peers, failed_tickers, main_info = fetch_peer_benchmark(symbol, peers_list)

            if failed_tickers:
                st.warning(f"⚠️ Não foi possível obter dados para: {', '.join(failed_tickers)}. Foram excluídos da comparação.")

            if df_peers.shape[1] <= 1:
                st.error("❌ Nenhum dos peers indicados devolveu dados válidos. Não é possível gerar a comparação.")
            else:
                sector = main_info.get("sector", "—")
                company_name = main_info.get("longName", symbol)
                appreciation_html = generate_peer_appreciation(symbol, df_peers)

                html_body = f"""
                <div class='report-container'>
                    <div class='header-card'>
                        <div>
                            <h1>{company_name} ({symbol})</h1>
                            <div class='subtitle'>Peer Benchmark & Valuation Comparativo (base TTM)</div>
                        </div>
                        <div>
                            <span class='badge-sector'>{sector}</span>
                            <div style='color: #B7CCBB; font-size: 11px; margin-top: 6px; text-align: right;'>{datetime.now().strftime('%d/%m/%Y')}</div>
                        </div>
                    </div>

                    <div class='section-title'>Peer Benchmark & Análise Setorial Direta (peers escolhidos manualmente)</div>
                    <div class='freshness-note'>Rácios calculados em base TTM (últimos 4 trimestres) quando disponível — ver linha "Dados de Referência" para a origem exata por ticker.</div>
                    {format_df_to_html(df_peers)}

                    <div class='section-title'>Conclusão & Síntese do Analista</div>
                    <div class='analysis-card'>
                        {appreciation_html}
                    </div>
                </div>
                """

                full_html = f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>Peer Benchmark {symbol}</title>{STYLE_CSS}</head><body style='background:#F1EEE4; padding:20px;'>{html_body}</body></html>"

                num_rows = len(df_peers.index)
                estimated_height = 900 + num_rows * 42
                components.html(full_html, height=estimated_height, scrolling=True)

                st.download_button(
                    label="⬇️ Descarregar Comparação em HTML",
                    data=full_html,
                    file_name=f"Peer_Benchmark_{symbol}_{datetime.now().strftime('%Y%m%d')}.html",
                    mime="text/html",
                    use_container_width=True,
                )

        except Exception as e:
            st.error(f"❌ Erro ao gerar comparação para {symbol}: {e}")
else:
    st.info("👈 Introduz o ticker principal e pelo menos um peer na barra lateral e clica em **Gerar Comparação** para começar.")
