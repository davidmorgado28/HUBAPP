from datetime import datetime
import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# -----------------------------------------------------------------------------
# 1. Configuração da Página
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Relatório & Dashboard Financeiro",
    page_icon="📊",
    layout="wide",
)

# -----------------------------------------------------------------------------
# 2. Injeção de CSS no Streamlit (Para alinhar a interface aos cards do HTML)
# -----------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .stApp {
        background-color: #f8fafc;
    }
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        padding: 16px;
        border-radius: 10px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
    }
    </style>
""",
    unsafe_allow_html=True,
)


# -----------------------------------------------------------------------------
# 3. Funções Auxiliares: Gerador do HTML
# -----------------------------------------------------------------------------
def gerar_relatorio_html(empresa: str, retorno: float, sharpe: float, volatilidade: float, df_dados: pd.DataFrame) -> str:
    """Gera o código HTML estilizado com CSS responsivo para visualização e exportação."""
    data_hoje = datetime.now().strftime("%d/%m/%Y às %H:%M")

    # Transforma o DataFrame em linhas de tabela HTML
    linhas_tabela = ""
    for _, row in df_dados.iterrows():
        linhas_tabela += f"""
        <tr>
            <td style="padding: 10px; border-bottom: 1px solid #e2e8f0;">{row['Ativo']}</td>
            <td style="padding: 10px; border-bottom: 1px solid #e2e8f0; text-align: right;">{row['Peso']:.1f}%</td>
            <td style="padding: 10px; border-bottom: 1px solid #e2e8f0; text-align: right;">{row['Retorno Esperado']:.2f}%</td>
        </tr>
        """

    html_template = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                background-color: #f8fafc;
                color: #0f172a;
                margin: 0;
                padding: 24px;
            }}
            .container {{
                max-width: 900px;
                margin: 0 auto;
                background: #ffffff;
                padding: 32px;
                border-radius: 12px;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
                border: 1px solid #e2e8f0;
            }}
            .header {{
                border-bottom: 2px solid #3b82f6;
                padding-bottom: 16px;
                margin-bottom: 24px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            .title {{
                font-size: 24px;
                font-weight: 700;
                color: #1e293b;
                margin: 0;
            }}
            .subtitle {{
                font-size: 13px;
                color: #64748b;
                margin-top: 4px;
            }}
            .cards-grid {{
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 16px;
                margin-bottom: 24px;
            }}
            .card {{
                background: #f1f5f9;
                padding: 16px;
                border-radius: 8px;
                border-left: 4px solid #3b82f6;
            }}
            .card-label {{
                font-size: 12px;
                color: #475569;
                text-transform: uppercase;
                letter-spacing: 0.05em;
                font-weight: 600;
            }}
            .card-value {{
                font-size: 22px;
                font-weight: 700;
                color: #0f172a;
                margin-top: 6px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 16px;
                font-size: 14px;
            }}
            th {{
                background-color: #f8fafc;
                color: #475569;
                text-align: left;
                padding: 10px;
                border-bottom: 2px solid #cbd5e1;
                font-weight: 600;
            }}
            th.right, td.right {{
                text-align: right;
            }}
            .footer {{
                margin-top: 32px;
                padding-top: 16px;
                border-top: 1px solid #e2e8f0;
                font-size: 12px;
                color: #94a3b8;
                text-align: center;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div>
                    <h1 class="title">Relatório de Análise de Portfólio</h1>
                    <div class="subtitle">Análise Quantitativa | Empresa / Carteira: <strong>{empresa}</strong></div>
                </div>
                <div style="text-align: right; font-size: 12px; color: #64748b;">
                    Gerado em:<br><strong>{data_hoje}</strong>
                </div>
            </div>

            <div class="cards-grid">
                <div class="card">
                    <div class="card-label">Retorno Esperado</div>
                    <div class="card-value">{retorno:.2f}%</div>
                </div>
                <div class="card">
                    <div class="card-label">Volatilidade (Risco)</div>
                    <div class="card-value">{volatilidade:.2f}%</div>
                </div>
                <div class="card">
                    <div class="card-card-label" style="font-size: 12px; color: #475569; font-weight: 600;">Índice Sharpe</div>
                    <div class="card-value">{sharpe:.2f}</div>
                </div>
            </div>

            <h3 style="color: #334155; margin-bottom: 8px;">Composição do Portfólio</h3>
            <table>
                <thead>
                    <tr>
                        <th>Ativo</th>
                        <th class="right">Peso (%)</th>
                        <th class="right">Retorno Esperado (%)</th>
                    </tr>
                </thead>
                <tbody>
                    {linhas_tabela}
                </tbody>
            </table>

            <div class="footer">
                Relatório de Simulação Financeira • Gerado via Python & Streamlit
            </div>
        </div>
    </body>
    </html>
    """
    return html_template


# -----------------------------------------------------------------------------
# 4. Barra Lateral - Parâmetros
# -----------------------------------------------------------------------------
st.sidebar.header("⚙️ Parâmetros da Simulação")
nome_carteira = st.sidebar.text_input("Nome da Carteira / Empresa", "Carteira Modelo Alpha")
tx_retorno = st.sidebar.slider("Retorno Esperado (%)", 0.0, 30.0, 14.5, 0.5)
volatilidade = st.sidebar.slider("Volatilidade Anual (%)", 5.0, 40.0, 18.2, 0.5)
sharpe = st.sidebar.slider("Índice Sharpe", 0.0, 3.0, 1.35, 0.05)

# Dados mockados para simulação
dados_ativos = pd.DataFrame({
    "Ativo": ["PETR4.SA", "VALE3.SA", "ITUB4.SA", "WEGE3.SA"],
    "Peso": [30.0, 25.0, 25.0, 20.0],
    "Retorno Esperado": [16.2, 12.8, 14.0, 15.5]
})

# -----------------------------------------------------------------------------
# 5. Interface Principal
# -----------------------------------------------------------------------------
st.title("📊 Dashboard & Relatório de Performance")
st.caption("Esta aplicação exibe o relatório formatado exatamente como o arquivo HTML final baixado.")

# Gerar a String com o código HTML completo
relatorio_html_string = gerar_relatorio_html(
    empresa=nome_carteira,
    retorno=tx_retorno,
    sharpe=sharpe,
    volatilidade=volatilidade,
    df_dados=dados_ativos
)

# Painel de ações (Download)
st.download_button(
    label="📥 Baixar Relatório HTML",
    data=relatorio_html_string,
    file_name=f"Relatorio_{nome_carteira.replace(' ', '_')}.html",
    mime="text/html",
)

st.divider()

# RENDERIZAÇÃO DO RELATÓRIO HTML NO STREAMLIT
# O parâmetro height determina a altura do iframe e scrolling permite rolar se necessário.
components.html(relatorio_html_string, height=650, scrolling=True)
