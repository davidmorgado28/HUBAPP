# ==============================================================================
# 📑 PEER BENCHMARK & VALUATION COMPARATIVO — Aplicação Streamlit
# Versão focada exclusivamente na comparação de rácios com pares (peers)
# escolhidos manualmente, seguida da análise textual. Todas as restantes
# secções (valuation histórico, crescimento, rentabilidade, alavancagem,
# liquidez, mercado) foram removidas a pedido.
#
# CORREÇÃO IMPORTANTE face à versão anterior:
# Os rácios já não são recalculados manualmente a partir das demonstrações
# financeiras (o que introduzia diferenças de metodologia face ao Yahoo
# Finance — ex.: definição de EBITDA, TTM vs. ano fiscal, ações diluídas vs.
# básicas). Agora os valores vêm diretamente do campo `info` do yfinance,
# que é o mesmo feed de dados usado no site finance.yahoo.com, pelo que
# devem bater certo com o que lá é mostrado. A linha "Dados de Referência"
# indica a que trimestre/ano os fundamentais dizem respeito em cada ticker.
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


def _fmt_unix_date(ts):
    """Converte um timestamp Unix (campo 'mostRecentQuarter' /
    'lastFiscalYearEnd' do yfinance) numa data legível AAAA-MM-DD."""
    if ts is None or pd.isna(ts):
        return None
    try:
        return pd.to_datetime(ts, unit="s").strftime("%Y-%m-%d")
    except Exception:
        return None


def compute_yahoo_metrics(ticker_symbol):
    """Vai buscar os rácios já pré-calculados pela própria Yahoo Finance
    (campo `info` do yfinance, que é o mesmo feed usado no site
    finance.yahoo.com), em vez de os recalcular a partir das demonstrações
    financeiras. Isto evita divergências de metodologia (definição de
    EBITDA, TTM vs. último trimestre, ações diluídas vs. básicas, etc.)
    entre a app e o valor mostrado no site. Se um campo não existir para
    um dado ticker, fica em falta (—) — nunca é estimado ou substituído
    silenciosamente por um cálculo próprio."""
    t = yf.Ticker(ticker_symbol)
    inf = t.info

    if not inf or (inf.get("currentPrice") is None and inf.get("regularMarketPrice") is None):
        raise ValueError(f"Sem dados de mercado disponíveis para '{ticker_symbol}'.")

    # Debt/Equity vem da Yahoo em percentagem (ex.: 154.3 = 1.543x) — só
    # se converte a unidade de leitura, o valor de origem não é recalculado.
    debt_equity_pct = inf.get("debtToEquity", np.nan)
    debt_equity = safe_div(debt_equity_pct, 100) if pd.notna(debt_equity_pct) else np.nan

    # Etiqueta de referência: mostra a que trimestre/ano os fundamentais
    # da Yahoo dizem respeito, para se poder cruzar diretamente com o site.
    quarter_date = _fmt_unix_date(inf.get("mostRecentQuarter"))
    fiscal_year_end = _fmt_unix_date(inf.get("lastFiscalYearEnd"))
    if quarter_date:
        source_label = f"Yahoo Finance — último trimestre reportado: {quarter_date}"
    elif fiscal_year_end:
        source_label = f"Yahoo Finance — último ano fiscal: {fiscal_year_end}"
    else:
        source_label = "Yahoo Finance — data de referência não disponível"

    metrics = {
        FRESHNESS_ROW: source_label,
        "P/E": inf.get("trailingPE", np.nan),
        "Forward P/E": inf.get("forwardPE", np.nan),
        "EV/EBITDA": inf.get("enterpriseToEbitda", np.nan),
        "P/S (EV/Rev)": inf.get("enterpriseToRevenue", np.nan),
        "Revenue Growth (YoY)": inf.get("revenueGrowth", np.nan),
        "ROE": inf.get("returnOnEquity", np.nan),
        "EBITDA Margin": inf.get("ebitdaMargins", np.nan),
        "Net Margin": inf.get("profitMargins", np.nan),
        "Debt/Equity": debt_equity,
        "Current Ratio": inf.get("currentRatio", np.nan),
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
            metrics, inf = compute_yahoo_metrics(tk)
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
                    <div class='freshness-note'>Rácios obtidos diretamente da Yahoo Finance (mesmo feed do site finance.yahoo.com) — ver linha "Dados de Referência" para o trimestre/ano a que dizem respeito em cada ticker.</div>
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
