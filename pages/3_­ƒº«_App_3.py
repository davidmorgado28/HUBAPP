import streamlit as st

st.set_page_config(page_title="App 3", page_icon="🧮", layout="wide")

st.title("🧮 App 3")
st.caption("Substitui este ficheiro pelo código da tua 3ª aplicação.")

st.markdown(
    """
    **Como converter a tua app original para aqui:**
    1. Copia o corpo do teu script (a lógica de cálculo + os widgets `st.sidebar`,
       `st.button`, `st.dataframe`, `st.plotly_chart`, etc.) para este ficheiro.
    2. Mantém o `st.set_page_config(...)` como a primeira instrução Streamlit do ficheiro.
    3. Renomeia o ficheiro para algo como `3_📈_Nome_Da_App.py` — o número controla
       a ordem no menu lateral e o texto após o emoji é o nome mostrado.
    4. Junta ao `requirements.txt` da raiz quaisquer bibliotecas extra que esta
       app precise (ex: `scikit-learn`, `statsmodels`, etc.).
    """
)
