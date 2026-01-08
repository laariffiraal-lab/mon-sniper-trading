import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Mon Sniper SMC", layout="wide")
st.title("🎯 Mon Sniper SMC & Fibonacci")

# Choix de la paire
ticker = st.sidebar.selectbox("Choisir une paire :", ["BTC-USD", "EURUSD=X", "ETH-USD", "GC=F"])

# 1. Récupération des données
data = yf.download(ticker, period="2d", interval="15m")

if not data.empty:
    # Réparation du format des données Yahoo Finance
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    
    # 2. Calcul Fibonacci (Haut/Bas du jour)
    high_price = float(data['High'].max())
    low_price = float(data['Low'].min())
    current_price = float(data['Close'].iloc[-1])
    
    diff = high_price - low_price
    # Zone de rechargement (Golden Pocket 61.8%)
    zone_achat = low_price + (0.618 * diff)

    # 3. Affichage des résultats
    st.header(f"Analyse pour {ticker}")
    
    col1, col2 = st.columns(2)
    col1.metric("Prix Actuel", f"{current_price:.4f}")
    col2.metric("Zone d'Achat (Fib)", f"{zone_achat:.4f}")

    if current_price <= zone_achat:
        st.success("🚀 SIGNAL D'ACHAT : Le prix est dans la zone de rechargement !")
    else:
        st.info("⌛ ATTENTE : Le prix est trop haut. Attend un retour en zone Fibonacci.")

    # 4. Graphique
    st.line_chart(data['Close'].tail(50))
else:
    st.error("Données indisponibles. Vérifie ta connexion.")
