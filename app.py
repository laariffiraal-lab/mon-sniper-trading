import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

st.set_page_config(page_title="Sniper Pro + Backtest", layout="wide")
st.title("🎯 Sniper Pro : Temps Réel & Backtest 6 Mois")

# 1. Configuration des paires
pairs_dict = {
    "EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/CHF": "USDCHF=X",
    "USD/JPY": "USDJPY=X", "NZD/USD": "NZDUSD=X", "USD/CAD": "USDCAD=X",
    "AUD/JPY": "AUDJPY=X", "GOLD": "GC=F", "BTC/USD": "BTC-USD"
}

selection = st.sidebar.selectbox("Choisir l'actif :", list(pairs_dict.keys()))
ticker = pairs_dict[selection]

# Création des onglets
tab1, tab2 = st.tabs(["🚀 Signal en Direct", "📜 Historique (6 mois)"])

# --- CHARGEMENT DES DONNÉES ---
@st.cache_data
def load_data(symbol, period="180d"):
    df = yf.download(symbol, period=period, interval="1h") # 1h pour un historique propre sur 6 mois
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

data = load_data(ticker)

# --- CALCUL DES INDICATEURS ---
data['EMA200'] = ta.ema(data['Close'], length=200)
data['ADX'] = ta.adx(data['High'], data['Low'], data['Close'])['ADX_14']
data['RSI'] = ta.rsi(data['Close'], length=14)
data['ATR'] = ta.atr(data['High'], data['Low'], data['Close'], length=14)

# --- LOGIQUE DE SIGNAL ---
def get_signals(df):
    signals = []
    for i in range(200, len(df)):
        # Fenêtre glissante pour Fibonacci (100 bougies)
        window = df.iloc[i-100:i]
        hi = window['High'].max()
        lo = window['Low'].min()
        fib_786 = lo + (0.786 * (hi - lo))
        fib_618 = lo + (0.618 * (hi - lo))
        
        curr = df.iloc[i]
        prev = df.iloc[i-1]
        
        # Conditions 80%+ 
        c1 = curr['Close'] > curr['EMA200'] # Tendance
        c2 = fib_786 <= curr['Low'] <= fib_618 # Zone Fib
        c3 = curr['ADX'] > 25 # Force
        c4 = curr['RSI'] > prev['RSI'] # Momentum
        
        if c1 and c2 and c3 and c4:
            # Simulation du résultat (est-ce que le prix a touché le TP avant le SL ?)
            tp = hi 
            sl = lo - (curr['ATR'] * 1.5)
            
            # On regarde les 24h suivantes pour le dénouement
            future = df.iloc[i+1 : i+24]
            win = False
            for p in future['High']:
                if p >= tp:
                    win = True
                    break
                if p <= sl: break
            
            signals.append({
                "Date": df.index[i],
                "Prix Entrée": round(curr['Close'], 4),
                "Résultat": "✅ GAGNÉ" if win else "❌ PERDU",
                "TP": round(tp, 4),
                "SL": round(sl, 4)
            })
    return signals

# --- ONGLET 1 : SIGNAL EN DIRECT ---
with tab1:
    curr = data.iloc[-1]
    st.metric("Prix Actuel", f"{curr['Close']:.4f}")
    if curr['Close'] > curr['EMA200'] and curr['ADX'] > 25:
        st.success("Tendance et Force validées. Vérifiez la zone Fibonacci.")
    else:
        st.info("Marché neutre ou hors zone.")
    st.line_chart(data['Close'].tail(100))

# --- ONGLET 2 : BACKTEST ---
with tab2:
    st.subheader(f"Analyse des signaux sur les 6 derniers mois ({selection})")
    all_signals = get_signals(data)
    
    if all_signals:
        df_results = pd.DataFrame(all_signals)
        win_rate = (df_results['Résultat'] == "✅ GAGNÉ").sum() / len(df_results) * 100
        
        col1, col2 = st.columns(2)
        col1.metric("Nombre de Signaux", len(all_signals))
        col2.metric("Taux de Réussite", f"{win_rate:.1f}%")
        
        st.table(df_results.sort_values(by="Date", ascending=False))
    else:
        st.write("Aucun signal répondant aux critères stricts n'a été trouvé sur cette période.")
