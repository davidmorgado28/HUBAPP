import streamlit as st

st.set_page_config(
    page_title="Hub de Aplicações",
    page_icon="🧰",
    layout="wide",
)

st.title("🧰 Hub de Aplicações")
st.write(
    "Usa o menu na barra lateral (esquerda) para navegar entre as diferentes "
    "aplicações. Cada uma corre de forma independente."
)

st.markdown("### Aplicações disponíveis")
st.markdown(
    """
- 📊 **Simulador de Portefólio vs S&P 500**
- 📈 **Otimizador de Markowitz**
- 🧮 **App 3** *(substituir por título real)*
- 🧮 **App 4** *(substituir por título real)*
"""
)

st.info("👈 Escolhe uma aplicação na barra lateral para começar.")
