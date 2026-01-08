import streamlit as st
import yfinance as yf
import pandas_ta as ta

st.set_page_config(page_title="Mon Sniper SMC", layout="wide")
st.title("🎯 Mon Sniper SMC & Fibonacci")

# Choix de la paire
ticker = st.sidebar.selectbox("Choisir une paire :", ["EURUSD=X", "BTC-USD", "ETH-USD", "GC=F"])

# Récupération des données
data = yf.download(ticker, period="1d", interval="15m")

if not data.empty:
    # Calcul Ichimoku simplifié
    ichimoku = data.ta.ichimoku()[0]
    span_a = ichimoku.iloc[:, 0]
    span_b = ichimoku.iloc[:, 1]
    
    # Calcul Fibonacci (Haut/Bas du jour)
    high_price = data['High'].max()
    low_price = data['Low'].min()
    diff = high_price - low_price
    
    zone_rechargement = low_price + (0.618 * diff)
    current_price = data['Close'].iloc[-1]

    # Logique de Signal
    st.header(f"Analyse pour {ticker}")
    
    if current_price <= zone_rechargement:
        st.success("🚀 SIGNAL D'ACHAT : Le prix est dans la zone de rechargement Fibonacci !")
    else:
        st.info("⌛ ANALYSE : En attente d'une zone de haute probabilité.")

    # Affichage du graphique
    st.line_chart(data['Close'].tail(50))
    st.write(f"Dernier prix : {current_price:.4f}")
else:
    st.error("Impossible de récupérer les données. Vérifie ta connexion.")
