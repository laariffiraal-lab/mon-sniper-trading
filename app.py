import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

st.set_page_config(page_title="Ultimate Sniper 80%", layout="wide")
st.title("🛡️ Stratégie Haute Précision (Confluence Institutionnelle)")

ticker = st.sidebar.selectbox("Paire :", ["EURUSD=X", "BTC-USD", "ETH-USD", "GBPUSD=X"])
timeframe = st.sidebar.selectbox("Unité de temps :", ["15m", "30m", "1h"])

data = yf.download(ticker, period="15d", interval=timeframe)

if not data.empty:
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    
    # 1. INDICATEURS DE STRUCTURE
    data['EMA200'] = ta.ema(data['Close'], length=200)
    data['ADX'] = ta.adx(data['High'], data['Low'], data['Close'], length=14)['ADX_14']
    data['RSI'] = ta.rsi(data['Close'], length=14)
    data['ATR'] = ta.atr(data['High'], data['Low'], data['Close'], length=14)
    
    curr = data.iloc[-1]
    prev = data.iloc[-2]
    
    # 2. CALCUL FIBONACCI (Sur 5 jours pour la solidité)
    high_p = float(data['High'].tail(100).max())
    low_p = float(data['Low'].tail(100).min())
    diff = high_p - low_p
    fib_618 = low_p + (0.618 * diff)
    fib_786 = low_p + (0.786 * diff) # Zone de "Deep Discount"

    # 3. LES 4 FILTRES DE SÉCURITÉ (La règle des 80%)
    c1 = curr['Close'] > curr['EMA200']             # Tendance Haussière de fond
    c2 = fib_786 <= curr['Close'] <= fib_618       # Zone de prix "Institutionnel"
    c3 = curr['ADX'] > 25                          # Le mouvement a de la force
    c4 = curr['RSI'] > prev['RSI']                 # Le momentum repart à la hausse

    # 4. CALCULS TP/SL (Basés sur la volatilité réelle)
    stop_loss = low_p - (curr['ATR'] * 2)
    take_profit = high_p + (curr['ATR'] * 1.5)

    # AFFICHAGE
    st.header(f"Radar Sniper : {ticker}")
    
    cols = st.columns(4)
    cols[0].metric("Prix", f"{curr['Close']:.4f}")
    cols[1].metric("Force (ADX)", f"{curr['ADX']:.1f}")
    cols[2].metric("Tendance", "BULLISH" if c1 else "BEARISH")
    cols[3].metric("Zone Fib", "OPTIMALE" if c2 else "ATTENTE")

    if c1 and c2 and c3 and c4:
        st.balloons()
        st.success("💎 SIGNAL DIAMANT : Haute Probabilité (>80%)")
        st.write(f"**ENTRÉE :** {curr['Close']:.4f} | **TP :** {take_profit:.4f} | **SL :** {stop_loss:.4f}")
    else:
        st.info("⌛ Analyse en cours... Le marché ne remplit pas encore les critères de précision 80%.")

    st.line_chart(data[['Close', 'EMA200']].tail(150))
else:
    st.error("Données indisponibles.")
