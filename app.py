import streamlit as st
import yfinance as yf
import pandas_ta as ta

st.set_page_config(page_title="Mon Sniper SMC", layout="wide")
st.title("🎯 Mon Sniper SMC & Fibonacci")

# Choix de la paire
ticker = st.sidebar.selectbox("Choisir une paire :", ["EURUSD=X", "BTC-USD", "ETH-USD", "GC=F"])

# 1. Récupération des données
data = yf.download(ticker, period="2d", interval="15m")

if not data.empty:
    # --- RÉPARATION DU MULTI-INDEX (L'erreur venait de là) ---
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    
    # 2. Calcul Ichimoku
    # On s'assure que les colonnes sont bien nommées pour pandas_ta
    ichimoku, _ = ta.ichimoku(data['High'], data['Low'], data['Close'])
    
    # 3. Calcul Fibonacci (Haut/Bas du jour)
    high_price = float(data['High'].max())
    low_price = float(data['Low'].min())
    current_price = float(data['Close'].iloc[-1])
    
    diff = high_price - low_price
    zone_rechargement = low_price + (0.618 * diff)

    # 4. Affichage
    st.header(f"Analyse pour {ticker}")
    
    if current_price <= zone_rechargement:
        st.success(f"🚀 SIGNAL D'ACHAT : Prix actuel ({current_price:.4f}) dans la zone Fibonacci !")
    else:
        st.info(f"⌛ ATTENTE : Prix actuel ({current_price:.4f}). Zone d'achat à {zone_rechargement:.4f}")

    # Graphique
    st.line_chart(data['Close'].tail(50))
else:
    st.error("Données indisponibles. Vérifie le symbole.")
