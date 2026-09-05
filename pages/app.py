import streamlit as st
import yfinance as yf
import google.generativeai as genai

# ============================================================
# CONFIGURAÇÃO
# ============================================================
# Cola aqui a tua chave gratuita gerada em https://aistudio.google.com/
GEMINI_API_KEY = "COLA_AQUI_A_TUA_CHAVE_GRATUITA"

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

st.set_page_config(page_title="Analisador Fundamental de Empresas", page_icon="📊", layout="centered")

# ============================================================
# PROMPT TEMPLATE (o teu prompt original, na íntegra)
# ============================================================
PROMPT_TEMPLATE = """Actua como um analista de negócios especializado, com a mentalidade combinada de Warren Buffett, Peter Lynch e Benjamin Graham.

O teu objetivo é ajudar-me a entender profundamente o negócio de uma empresa — sem análise financeira — de forma simples, clara e acessível a qualquer pessoa, mesmo sem conhecimentos de economia ou do setor.

A empresa a analisar é: {empresa}

Estrutura o relatório exatamente da seguinte forma:

---

1. O QUE FAZ ESTA EMPRESA?
Explica o negócio central em 3-5 frases, como se explicasses a um amigo sem qualquer conhecimento da área. Usa linguagem simples e evita jargão técnico. Se for inevitável usar termos técnicos do setor (ex: "hardware", "upstream", "SaaS", "refino"), explica o que significam logo a seguir entre parênteses ou numa nota curta.

---

2. COMO GANHA DINHEIRO?
Descreve as fontes de receita da empresa de forma clara. Como é que cada euro que entra chega até ela? Onde está o seu modelo de negócio? Se tiver múltiplas fontes, lista-as por ordem de importância.

---

3. PRINCIPAIS PRODUTOS OU SERVIÇOS
Lista os 3 a 5 produtos ou serviços mais importantes. Para cada um:
- Nome do produto/serviço
- O que é e para que serve (explicado de forma muito simples)
- Qual o peso ou importância no negócio total

---

4. PRINCIPAIS CONCORRENTES E VANTAGEM COMPETITIVA
- Quem são os 3 a 5 maiores concorrentes diretos?
- O que torna esta empresa diferente ou melhor (o famoso "moat" de Buffett — explica o conceito brevemente)?
- Onde é que a empresa é mais vulnerável face à concorrência?

---

5. FORNECEDORES E DEPENDÊNCIAS CRÍTICAS
- De quem ou do quê depende esta empresa para funcionar? (matérias-primas, tecnologia, parceiros, reguladores, etc.)
- Existe alguma dependência excessiva que possa ser um risco?

---

6. PRINCIPAIS RISCOS DO NEGÓCIO
Lista os 4 a 6 maiores riscos reais para este negócio (não financeiros). Pensa como Peter Lynch: o que poderia fazer esta empresa perder relevância ou falhar nos próximos anos? Inclui riscos de mercado, tecnológicos, regulatórios, de concorrência ou de mudança de hábitos dos consumidores.

---

7. POTENCIAL DE CRESCIMENTO
- Qual é o espaço de crescimento desta empresa? Porquê?
- Quais são os principais motores de crescimento futuro?
- Existem mercados ou segmentos ainda por explorar?

---

ESTILO E TOM:
- Escreve como se fosses um analista a explicar a um investidor inteligente mas não especialista no setor
- Sê direto, usa frases curtas, evita repetições
- Não uses tabelas nem listas excessivas — prefere parágrafos curtos e fluidos
- No final de cada secção, inclui uma frase de síntese em negrito com a ideia-chave
- O relatório deve ter no máximo 800 palavras no total
"""


# ============================================================
# FUNÇÕES AUXILIARES (com cache para poupar pedidos à API)
# ============================================================
@st.cache_data(show_spinner=False, ttl=60 * 60 * 24)  # cache de 24h
def obter_nome_empresa(ticker_ou_nome: str) -> str:
    """Tenta resolver o ticker para o nome oficial da empresa via yfinance."""
    try:
        info = yf.Ticker(ticker_ou_nome).info
        nome = info.get("longName") or info.get("shortName")
        if nome:
            return f"{nome} ({ticker_ou_nome.upper()})"
    except Exception:
        pass
    return ticker_ou_nome


@st.cache_data(show_spinner=False, ttl=60 * 60 * 24)  # cache de 24h por empresa
def gerar_relatorio(empresa: str) -> str:
    prompt = PROMPT_TEMPLATE.format(empresa=empresa)
    response = model.generate_content(prompt)
    return response.text


# ============================================================
# INTERFACE
# ============================================================
st.title("📊 Analisador Fundamental de Empresas")
st.caption("Introduz um ticker (ex: AAPL, NKE, GALP.LS) ou o nome de uma empresa para gerar um relatório de negócio.")

entrada = st.text_input("Ticker ou nome da empresa", placeholder="Ex: MSFT, Apple, Galp")

gerar = st.button("Gerar relatório", type="primary")

if gerar:
    if not entrada.strip():
        st.warning("Introduz um ticker ou nome de empresa antes de gerar o relatório.")
    elif "COLA_AQUI" in GEMINI_API_KEY:
        st.error("Ainda não configuraste a tua chave da Gemini API no topo do ficheiro app.py.")
    else:
        with st.spinner("A identificar a empresa..."):
            empresa_resolvida = obter_nome_empresa(entrada.strip())

        st.info(f"A gerar relatório para: **{empresa_resolvida}**")

        with st.spinner("A analisar o negócio... (pode demorar alguns segundos)"):
            try:
                texto = gerar_relatorio(empresa_resolvida)
                st.markdown("---")
                st.markdown(texto)
            except Exception as e:
                st.error(f"Ocorreu um erro ao contactar a API do Gemini: {e}")

st.markdown("---")
st.caption(
    "⚠️ Este relatório é gerado por IA com base em conhecimento geral do modelo, "
    "sem pesquisa web em tempo real. Pode conter imprecisões ou informação desatualizada — "
    "confirma sempre factos importantes noutras fontes antes de tomar decisões de investimento."
)
