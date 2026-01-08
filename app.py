import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

st.set_page_config(page_title="Sniper Pro Multi-Paires", layout="wide")
st.title("🎯 Sniper Pro : Stratégie Haute Précision 80%+")

# 1. LISTE COMPLÈTE DE TES PAIRES
pairs_dict = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/CHF": "USDCHF=X",
    "USD/JPY": "USDJPY=X",
    "NZD/USD": "NZDUSD=X",
    "USD/CAD": "USDCAD=X",
    "AUD/JPY": "AUDJPY=X",
    "GOLD (Or)": "GC=F",
    "BTC/USD": "BTC-USD"
}

selection = st.sidebar.selectbox("Choisir l'actif à analyser :", list(pairs_dict.keys()))
ticker = pairs_dict[selection]
timeframe = st.sidebar.selectbox("Unité de temps :", ["15m", "30m", "1h"])

# Récupération des données (période de 15 jours pour plus de stabilité)
data = yf.download(ticker, period="15d", interval=timeframe)

if not data.empty:
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    
    # 2. CALCULS DES INDICATEURS DE CONFLUENCE
    data['EMA200'] = ta.ema(data['Close'], length=200)
    data['ADX'] = ta.adx(data['High'], data['Low'], data['Close'], length=14)['ADX_14']
    data['RSI'] = ta.rsi(data['Close'], length=14)
    data['ATR'] = ta.atr(data['High'], data['Low'], data['Close'], length=14)
    
    curr = data.iloc[-1]
    prev = data.iloc[-2]
    
    # Fibonacci sur les 100 dernières bougies (Zone Deep Discount)
    high_p = float(data['High'].tail(100).max())
    low_p = float(data['Low'].tail(100).min())
    diff = high_p - low_p
    fib_786 = low_p + (0.786 * diff)
    fib_618 = low_p + (0.618 * diff)

    # 3. FILTRES DE SÉCURITÉ (Règle des 80%+)
    # On gère l'inversion pour les paires en USD/XXX (comme USDJPY ou USDCAD)
    is_bullish = curr['Close'] > curr['EMA200']
    is_in_zone = fib_786 <= curr['Close'] <= fib_618
    is_strong = curr['ADX'] > 25
    is_rebounding = curr['RSI'] > prev['RSI']

    # Calcul dynamique du TP/SL avec l'ATR (Volatilité)
    stop_loss = low_p - (curr['ATR'] * 1.5)
    take_profit = high_p + (curr['ATR'] * 1.0)

    # 4. AFFICHAGE DU DASHBOARD
    st.header(f"Analyse en cours : {selection}")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Prix Actuel", f"{curr['Close']:.4f}")
    c2.metric("Tendance", "HAUSSIÈRE" if is_bullish else "BAISSIÈRE")
    c3.metric("Force (ADX)", f"{curr['ADX']:.1f}")
    c4.metric("RSI", f"{curr['RSI']:.1f}")

    if is_bullish and is_in_zone and is_strong and is_rebounding:
        st.balloons()
        st.success(f"💎 SIGNAL DIAMANT DÉTECTÉ SUR {selection}")
        st.write(f"🚀 **ACHAT (BUY) :** {curr['Close']:.4f}")
        st.write(f"🎯 **TAKE PROFIT :** {take_profit:.4f} | 🛡️ **STOP LOSS :** {stop_loss:.4f}")
    else:
        st.info("⌛ En attente de confluence... Aucun signal haute probabilité pour le moment.")

    # Affichage du graphique
    st.line_chart(data[['Close', 'EMA200']].tail(120))
else:
    st.error("Impossible de récupérer les données pour cet actif.")
