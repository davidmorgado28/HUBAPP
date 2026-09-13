# ==============================================================================
# 🏢 PEER BENCHMARK DE REITs — Aplicação Streamlit
# Versão focada exclusivamente na comparação de rácios com pares (peers)
# escolhidos manualmente, seguida da análise textual. As secções de KPIs
# individuais, parecer qualitativo isolado e evolução histórica a 4 anos
# foram removidas a pedido.
#
# NOTA IMPORTANTE SOBRE FONTES DE DADOS:
# A Yahoo Finance NÃO publica FFO/AFFO (são métricas específicas de REITs
# que não constam do feed padrão). Por isso:
#   - Dividend Yield, Total Debt, Total Cash e EBITDA são lidos DIRETAMENTE
#     do campo `info` do yfinance (mesmo feed do site finance.yahoo.com).
#   - Price/FFO, Price/AFFO, AFFO Payout Ratio e FFO Growth continuam a ser
#     CALCULADOS a partir das demonstrações financeiras anuais, porque não
#     há alternativa — mas o ano fiscal usado fica sempre visível na tabela
#     (coluna "Ano Fiscal (FFO/AFFO)"), para que se saiba exatamente o que
#     está a ser comparado e não se confunda com dados TTM de outro site.
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
    page_title="Peer Benchmark de REITs",
    page_icon="🏢",
    layout="wide",
)

inject_theme()

MAX_PEERS = 6

# ------------------------------------------------------------------------------
# HELPERS
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
    """Converte a coluna de um DataFrame anual do yfinance (Timestamp)
    numa etiqueta legível AAAA."""
    try:
        return pd.to_datetime(col).strftime("%Y")
    except Exception:
        return str(col)[:4]


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


# ------------------------------------------------------------------------------
# CÁLCULO DE MÉTRICAS POR TICKER
# ------------------------------------------------------------------------------
def obter_metricas_peer_reit(ticker_symbol):
    """Devolve os rácios de comparação para um REIT.

    Dividend Yield, EBITDA e Net Debt vêm diretamente do campo `info` da
    Yahoo (mesmo feed do site). Price/FFO, Price/AFFO, AFFO Payout e FFO
    Growth são calculados a partir das demonstrações financeiras anuais,
    já que a Yahoo não publica FFO/AFFO. Nunca substitui um componente em
    falta por uma estimativa silenciosa — regista o aviso e assume 0,
    devolvendo a lista de avisos ao chamador para ser mostrada ao utilizador.
    """
    t = yf.Ticker(ticker_symbol)
    info = t.info

    price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
    shares = info.get("sharesOutstanding")

    if not info or price is None:
        raise ValueError(f"Sem dados de mercado disponíveis para '{ticker_symbol}'.")

    financials = t.financials
    cashflow = t.cashflow

    if financials is None or financials.empty or cashflow is None or cashflow.empty or not shares:
        raise ValueError(f"Demonstrações financeiras insuficientes para calcular FFO/AFFO de '{ticker_symbol}'.")

    avisos = []

    def get_row(df, name, col_idx, default=0.0, warn_label=None):
        if name in df.index and col_idx < df.shape[1]:
            val = df.loc[name].iloc[col_idx]
            if pd.notna(val):
                return val
        if warn_label:
            avisos.append(f"{ticker_symbol}: {warn_label} em falta — assumido como 0 no cálculo de FFO/AFFO.")
        return default

    num_years = financials.shape[1]
    ffo_hist = []
    for i in range(min(2, num_years)):
        net_income = get_row(financials, "Net Income", i, warn_label="Net Income")
        if "Reconciled Depreciations" in cashflow.index:
            depreciation = get_row(cashflow, "Reconciled Depreciations", i)
        else:
            depreciation = get_row(cashflow, "Depreciation And Amortization", i, warn_label="Depreciação/Amortização")
        capex = abs(get_row(cashflow, "Capital Expenditure", i, warn_label="CapEx (proxy para manutenção)"))
        gain_sale = get_row(financials, "Gain Loss On Sale Of Assets", i)

        ffo = net_income + depreciation - gain_sale
        affo = ffo - capex
        ffo_hist.append((ffo, affo))

    ffo_atual, affo_atual = ffo_hist[0]

    ffo_growth = np.nan
    if len(ffo_hist) > 1:
        ffo_anterior = ffo_hist[1][0]
        if pd.notna(ffo_anterior) and ffo_anterior != 0:
            ffo_growth = (ffo_atual - ffo_anterior) / abs(ffo_anterior)

    ffo_per_share = safe_div(ffo_atual, shares)
    affo_per_share = safe_div(affo_atual, shares)
    price_ffo = safe_div(price, ffo_per_share) if ffo_per_share and ffo_per_share > 0 else np.nan
    price_affo = safe_div(price, affo_per_share) if affo_per_share and affo_per_share > 0 else np.nan

    # --- Métricas obtidas diretamente da Yahoo Finance (mesmo feed do site) ---
    dividend_yield = info.get("dividendYield", np.nan)
    if pd.notna(dividend_yield) and dividend_yield > 1:
        # Algumas versões do yfinance devolvem o yield já em percentagem (ex. 4.5);
        # normaliza-se apenas quando isso é detetado, sem alterar o valor de origem.
        dividend_yield = dividend_yield / 100

    ebitda_ttm = info.get("ebitda", np.nan)
    total_debt = info.get("totalDebt", np.nan)
    total_cash = info.get("totalCash", np.nan)
    net_debt = (total_debt - total_cash) if pd.notna(total_debt) and pd.notna(total_cash) else np.nan
    net_debt_ebitda = safe_div(net_debt, ebitda_ttm)

    # AFFO Payout Ratio: métrica calculada (a Yahoo não publica payout sobre AFFO,
    # só sobre EPS), por isso usa-se o dividendo em caixa efetivamente pago.
    div_paid = abs(get_row(cashflow, "Common Stock Dividend Paid", 0))
    affo_payout = safe_div(div_paid, affo_atual) if affo_atual and affo_atual > 0 else np.nan

    fiscal_year_label = _fmt_period_label(financials.columns[0])

    metrics = {
        "Ticker": ticker_symbol,
        "Price / FFO": price_ffo,
        "Price / AFFO": price_affo,
        "Dividend Yield": dividend_yield,
        "AFFO Payout": affo_payout,
        "Net Debt / EBITDA": net_debt_ebitda,
        "FFO Growth (YoY)": ffo_growth,
        "Ano Fiscal (FFO/AFFO)": fiscal_year_label,
    }
    return metrics, avisos, info


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
# ESTILO CSS — paleta OAK & VALUE (branco quente + verde carvalho)
# ------------------------------------------------------------------------------
CSS_STYLES = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

    .reit-report-body {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        background-color: #F1EEE4; color: #1C2420; margin: 0; padding: 20px;
    }
    .report-card {
        background: #ffffff; border-radius: 16px; box-shadow: 0 4px 20px -2px rgba(30,46,34,0.1);
        border: 1px solid rgba(47,74,56,0.15); padding: 28px; margin-bottom: 24px;
    }
    .hero-header {
        background: linear-gradient(135deg, #1E2E22 0%, #2F4A38 100%); border-radius: 16px; padding: 28px;
        color: #F1EEE4; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center;
        box-shadow: 0 10px 25px -5px rgba(30,46,34,0.25);
    }
    .hero-title { font-size: 26px; font-weight: 700; margin: 0 0 4px 0; letter-spacing: -0.02em; }
    .hero-subtitle { color: #B7CCBB; font-size: 13px; margin: 0; }
    .freshness-note { font-size: 12px; color: #4F7058; margin-top: -6px; margin-bottom: 18px; }
    .section-title { font-size: 17px; font-weight: 700; color: #1E2E22; margin: 0 0 16px 0; display: flex; align-items: center; gap: 8px; }
    .section-title::before { content: ''; display: inline-block; width: 4px; height: 18px; background: #2E7D4C; border-radius: 2px; }
    .custom-table { width: 100%; border-collapse: separate; border-spacing: 0; margin-top: 12px; font-size: 13px; }
    .custom-table th { background-color: #DCE6DE; color: #4F7058; font-weight: 600; padding: 10px 14px; text-align: center; border-bottom: 2px solid rgba(47,74,56,0.15); }
    .custom-table th:first-child { text-align: left; border-top-left-radius: 8px; }
    .custom-table th:last-child { border-top-right-radius: 8px; }
    .custom-table td { padding: 10px 14px; border-bottom: 1px solid rgba(47,74,56,0.08); color: #1C2420; }
    .custom-table tr:hover td { background-color: rgba(47,74,56,0.05); }
    .badge { display: inline-block; padding: 4px 10px; border-radius: 9999px; font-size: 11px; font-weight: 600; letter-spacing: 0.02em; }
    .badge-success { background: #dcfce7; color: #166534; }
    .badge-warning { background: #fef3c7; color: #92400e; }
    .badge-danger { background: #fee2e2; color: #991b1b; }
    .badge-info { background: #dbeafe; color: #1e40af; }
    .badge-neutral { background: #DCE6DE; color: #4F7058; }
</style>
"""


def formatar_tabela_peers_pretty(df_peers):
    if df_peers.empty:
        return ""
    headers = "".join([f"<th>{col}</th>" for col in df_peers.columns])
    linhas = []
    for idx, row in df_peers.iterrows():
        cols = []
        for col, val in row.items():
            if col in ("Ticker", "Ano Fiscal (FFO/AFFO)"):
                weight = "700" if col == "Ticker" else "400"
                color = "#1E2E22" if col == "Ticker" else "#4F7058"
                cols.append(f"<td style='text-align: center; font-weight: {weight}; color: {color};'>{val}</td>")
            elif "Yield" in col or "Payout" in col or "Growth" in col:
                cols.append(f"<td style='text-align: center;'>{val * 100:.2f}%</td>" if pd.notna(val) else "<td style='text-align: center; color: #8FA096;'>—</td>")
            else:
                cols.append(f"<td style='text-align: center;'>{val:.2f}x</td>" if pd.notna(val) else "<td style='text-align: center; color: #8FA096;'>—</td>")
        linhas.append(f"<tr>{''.join(cols)}</tr>")

    return f"""
    <div class='report-card'>
        <div class='section-title'>Análise Comparativa com Concorrentes</div>
        <div class='freshness-note'>Dividend Yield, EBITDA e Net Debt vêm diretamente da Yahoo Finance. Price/FFO, Price/AFFO, AFFO Payout e FFO Growth são calculados a partir do ano fiscal indicado na última coluna, porque a Yahoo não publica FFO/AFFO.</div>
        <table class='custom-table'>
            <thead><tr>{headers}</tr></thead>
            <tbody>{''.join(linhas)}</tbody>
        </table>
    </div>"""


# ------------------------------------------------------------------------------
# INTERFACE
# ------------------------------------------------------------------------------
page_header(
    "🏢",
    "Peer Benchmark de REITs",
    "Comparação de rácios entre o REIT alvo e os concorrentes diretos escolhidos manualmente.",
)

with st.sidebar:
    st.header("⚙️ Configuração")
    ticker_main = st.text_input("REIT Alvo", value="O", placeholder="ex: O")
    peers_input = st.text_input(
        "Concorrentes (separados por vírgula)",
        value="NNN, ADC, MAIN",
        placeholder="ex: NNN, ADC, MAIN",
        help=f"Máximo de {MAX_PEERS} tickers. Escolhe tu próprio os concorrentes diretos.",
    )

    main_ticker_upper = ticker_main.strip().upper()
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

    btn_executar = st.button("🚀 Gerar Comparação", type="primary", use_container_width=True, disabled=not peers_list)

if btn_executar and peers_list:
    symbol = main_ticker_upper

    with st.spinner(f"A obter dados para {symbol} e {len(peers_list)} peer(s)..."):
        peers_data = []
        failed_tickers = []
        todos_avisos = []
        main_info = {}

        try:
            metrics_main, avisos_main, main_info = obter_metricas_peer_reit(symbol)
            peers_data.append(metrics_main)
            todos_avisos.extend(avisos_main)
        except Exception as e:
            st.error(f"❌ Não foi possível carregar os dados do REIT principal ({symbol}): {e}")
            st.stop()

        for p in peers_list:
            try:
                metrics_p, avisos_p, _ = obter_metricas_peer_reit(p)
                peers_data.append(metrics_p)
                todos_avisos.extend(avisos_p)
            except Exception:
                failed_tickers.append(p)

    if failed_tickers:
        st.warning(f"⚠️ Não foi possível obter dados para: {', '.join(failed_tickers)}. Foram excluídos da comparação.")

    if todos_avisos:
        with st.expander("⚠️ Avisos sobre componentes em falta no cálculo de FFO/AFFO"):
            for a in dict.fromkeys(todos_avisos):  # remove duplicados mantendo ordem
                st.markdown(f"- {a}")

    df_peers = pd.DataFrame(peers_data)

    if df_peers.shape[0] <= 1:
        st.error("❌ Nenhum dos peers indicados devolveu dados válidos. Não é possível gerar a comparação.")
    else:
        html_peers = formatar_tabela_peers_pretty(df_peers)
        html_apreciacao_peers = gerar_apreciacao_peers(symbol, df_peers)

        company_name = main_info.get("longName", symbol)
        sector = main_info.get("sector", "Real Estate")
        industry = main_info.get("industry", "REIT")
        price = main_info.get("currentPrice") or main_info.get("regularMarketPrice") or main_info.get("previousClose") or 0

        hero_html = f"""
        <div class='hero-header'>
            <div>
                <div class='hero-subtitle'>{sector} • {industry}</div>
                <div class='hero-title'>{company_name} ({symbol})</div>
            </div>
            <div style='text-align: right;'>
                <div style='font-size: 12px; color: #B7CCBB;'>Cotação Atual</div>
                <div style='font-size: 24px; font-weight: 700;'>${price:.2f}</div>
            </div>
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

        doc_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Peer Benchmark REIT - {symbol}</title>
            {CSS_STYLES}
        </head>
        <body class="reit-report-body">
            {hero_html}
            {html_peers}
            {peer_appreciation_card}
        </body>
        </html>
        """

        estimated_height = 850 + len(df_peers.index) * 46
        components.html(doc_html, height=estimated_height, scrolling=True)

        st.download_button(
            label="📥 Descarregar Comparação (HTML)",
            data=doc_html,
            file_name=f"Peer_Benchmark_REIT_{symbol}.html",
            mime="text/html",
            use_container_width=True,
        )
else:
    st.info("👈 Introduz o ticker do REIT alvo e pelo menos um concorrente na barra lateral, depois clica em **Gerar Comparação**.")
