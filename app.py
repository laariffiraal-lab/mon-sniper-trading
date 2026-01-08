import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Mon Sniper SMC", layout="wide")
st.title("🎯 Mon Sniper SMC : Fibonacci & Objectifs")

ticker = st.sidebar.selectbox("Choisir une paire :", ["BTC-USD", "EURUSD=X", "ETH-USD", "GC=F"])
data = yf.download(ticker, period="2d", interval="15m")

if not data.empty:
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    
    high_price = float(data['High'].max())
    low_price = float(data['Low'].min())
    current_price = float(data['Close'].iloc[-1])
    diff = high_price - low_price

    # Calcul des zones
    zone_achat = low_price + (0.618 * diff)
    
    # --- CALCUL DES OBJECTIFS ---
    # Stop Loss : Juste en dessous du plus bas du jour
    stop_loss = low_price - (diff * 0.05) 
    # Take Profit : Le sommet récent (0.0% Fib)
    take_profit = high_price

    st.header(f"Analyse pour {ticker}")
    
    # Affichage des métriques en colonnes
    c1, c2, c3 = st.columns(3)
    c1.metric("Prix Actuel", f"{current_price:.4f}")
    c2.metric("🎯 TAKE PROFIT", f"{take_profit:.4f}", delta_color="normal")
    c3.metric("🛡️ STOP LOSS", f"{stop_loss:.4f}", delta_color="inverse")

    if current_price <= zone_achat:
        st.success(f"🚀 SIGNAL D'ACHAT ! Entrée sous {zone_achat:.4f}")
        st.info(f"💡 Stratégie : Viser {take_profit:.4f} avec une sécurité à {stop_loss:.4f}")
    else:
        st.warning("⌛ ATTENTE : Le prix est trop haut pour le moment.")

    st.line_chart(data['Close'].tail(50))
else:
    st.error("Données indisponibles.")
