import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

st.set_page_config(page_title="Sniper Forteresse SMC", layout="wide")
st.title("🛡️ Stratégie Sniper Forteresse (SMC & Volatilité)")

# Configuration
ticker = st.sidebar.selectbox("Paire :", ["BTC-USD", "EURUSD=X", "ETH-USD", "GC=F"])
timeframe = st.sidebar.selectbox("Unité de temps :", ["15m", "30m", "1h"])

# Récupération des données (plus large pour la stabilité)
data = yf.download(ticker, period="10d", interval=timeframe)

if not data.empty:
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    
    # --- CALCULS AVANCÉS ---
    data['EMA200'] = ta.ema(data['Close'], length=200)
    data['RSI'] = ta.rsi(data['Close'], length=14)
    data['ATR'] = ta.atr(data['High'], data['Low'], data['Close'], length=14)
    
    current_price = float(data['Close'].iloc[-1])
    ema_200 = float(data['EMA200'].iloc[-1])
    rsi_val = float(data['RSI'].iloc[-1])
    atr_val = float(data['ATR'].iloc[-1])
    
    # Fibonacci sur les 3 derniers jours (plus solide)
    recent_data = data.tail(100)
    high_p = float(recent_data['High'].max())
    low_p = float(recent_data['Low'].min())
    diff = high_p - low_p
    
    entry_zone = low_p + (0.618 * diff)
    
    # --- LOGIQUE DE SORTIE BASÉE SUR LA VOLATILITÉ ---
    # Stop Loss = Bas récent - (1.5 * volatilité ATR) pour éviter les mèches
    stop_loss = low_p - (atr_val * 1.5)
    # Take Profit = Sommet + (0.5 * volatilité ATR)
    take_profit = high_p + (atr_val * 1.0)

    # --- CONDITIONS DE CONFLUENCE ---
    trend_ok = current_price > ema_200
    fib_ok = current_price <= entry_zone
    momentum_ok = 30 < rsi_val < 60 # Évite d'acheter si déjà trop "cher"

    st.header(f"Analyse Stratégique : {ticker}")
    
    # Dashboard de Confluence
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Tendance", "HAUSSIÈRE" if trend_ok else "BAISSIÈRE", delta=None)
    m2.metric("Zone Fib", "OUI" if fib_ok else "NON")
    m3.metric("RSI", f"{rsi_val:.1f}")
    m4.metric("Volatilité (ATR)", f"{atr_val:.4f}")

    if trend_ok and fib_ok and momentum_ok:
        st.success("🎯 SIGNAL SNIPER : Haute Probabilité détectée !")
        st.write(f"**ORDRE D'ACHAT :** {current_price:.4f}")
        st.write(f"**🎯 TAKE PROFIT :** {take_profit:.4f}")
        st.write(f"**🛡️ STOP LOSS :** {stop_loss:.4f}")
    else:
        st.info("⌛ Le marché ne présente pas toutes les confluences nécessaires. Restez à l'écart.")

    # Graphique technique
    st.line_chart(data[['Close', 'EMA200']].tail(120))
else:
    st.error("Données indisponibles.")
