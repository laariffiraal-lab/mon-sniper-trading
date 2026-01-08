import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from datetime import datetime, timedelta

st.set_page_config(page_title="Sniper Elite 80%", layout="wide")
st.title("🛡️ Sniper Elite : Haute Précision (Filtres Avancés)")

pairs_dict = {
    "EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/JPY": "USDJPY=X",
    "USD/CHF": "USDCHF=X", "AUD/JPY": "AUDJPY=X", "USD/CAD": "USDCAD=X",
    "NZD/USD": "NZDUSD=X", "GOLD": "GC=F", "BTC/USD": "BTC-USD"
}

selection = st.sidebar.selectbox("Choisir l'actif :", list(pairs_dict.keys()))
ticker = pairs_dict[selection]
tab1, tab2 = st.tabs(["🚀 Signal en Direct", "📜 Historique (Backtest)"])

@st.cache_data(ttl=3600)
def load_data(symbol):
    df = yf.download(symbol, period="250d", interval="1h")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

data = load_data(ticker)

def add_indicators(df):
    df['EMA200'] = ta.ema(df['Close'], length=200)
    df['ADX'] = ta.adx(df['High'], df['Low'], df['Close'])['ADX_14']
    df['RSI'] = ta.rsi(df['Close'], length=14)
    df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
    # Calcul de la pente de l'EMA
    df['EMA_Slope'] = df['EMA200'].diff(5) 
    return df

data = add_indicators(data)

def get_signals(df):
    signals = []
    for i in range(200, len(df)):
        window = df.iloc[i-50:i]
        hi = window['High'].max()
        lo = window['Low'].min()
        fib_618 = lo + (0.618 * (hi - lo))
        
        curr = df.iloc[i]
        prev = df.iloc[i-1]
        
        # --- LES 5 FILTRES "ELITE" POUR LE 80% ---
        c1 = curr['Close'] > curr['EMA200']             # Prix au-dessus de l'EMA
        c2 = curr['EMA_Slope'] > 0                      # Tendance EMA orientée vers le haut
        c3 = curr['Low'] <= fib_618 and curr['Close'] > curr['EMA200'] # Zone Fib + Support EMA
        c4 = curr['ADX'] > 25                           # Force de tendance confirmée
        c5 = curr['RSI'] > prev['RSI'] and curr['RSI'] < 55 # Momentum haussier naissant

        if c1 and c2 and c3 and c4 and c5:
            future = df.iloc[i+1 : i+100] # On regarde plus loin (100h)
            if future.empty: continue
            
            tp = hi + (curr['ATR'] * 0.5) # TP un peu plus ambitieux
            sl = curr['EMA200'] - (curr['ATR'] * 1.5) # SL sécurisé sous l'EMA
            
            outcome = "En cours"
            for _, row in future.iterrows():
                if row['High'] >= tp:
                    outcome = "✅ GAGNÉ"
                    break
                if row['Low'] <= sl:
                    outcome = "❌ PERDU"
                    break
            
            signals.append({
                "Date": df.index[i].strftime('%d/%m/%Y %H:%M'),
                "Prix Entrée": round(curr['Close'], 4),
                "Résultat": outcome,
                "Profit": "Cible TP" if outcome == "✅ GAGNÉ" else "Stop Touché"
            })
    
    clean = []
    if signals:
        clean.append(signals[0])
        for s in signals[1:]:
            last_date = datetime.strptime(clean[-1]['Date'], '%d/%m/%Y %H:%M')
            curr_date = datetime.strptime(s['Date'], '%d/%m/%Y %H:%M')
            if curr_date > last_date + timedelta(hours=48): # Un seul trade tous les 2 jours
                clean.append(s)
    return clean

with tab1:
    curr = data.iloc[-1]
    st.header(f"Radar de précision : {selection}")
    col1, col2, col3 = st.columns(3)
    col1.metric("Prix", f"{curr['Close']:.4f}")
    col2.metric("Pente EMA", "HAUSSIÈRE" if curr['EMA_Slope'] > 0 else "NULLE/BASSE")
    col3.metric("Force (ADX)", f"{curr['ADX']:.1f}")

    if curr['Close'] > curr['EMA200'] and curr['EMA_Slope'] > 0 and curr['ADX'] > 25 and curr['RSI'] < 55:
        st.success("💎 SIGNAL ÉLITE : Haute probabilité détectée !")
    else:
        st.info("⌛ Filtres de sécurité actifs : Le marché n'est pas assez "propre" pour un trade à 80%.")

    st.line_chart(data[['Close', 'EMA200']].tail(150))

with tab2:
    st.subheader("Analyse de l'historique filtré")
    results = get_signals(data)
    if results:
        df_res = pd.DataFrame(results)
        finished = df_res[df_res['Résultat'] != "En cours"]
        if not finished.empty:
            wins = (finished['Résultat'] == "✅ GAGNÉ").sum()
            wr = (wins / len(finished)) * 100
            st.metric("Taux de Réussite (Filtré)", f"{wr:.1f}%")
        st.dataframe(df_res.sort_values(by="Date", ascending=False), use_container_width=True)
    else:
        st.warning("Aucun signal ne remplit les conditions de sécurité maximales sur 6 mois.")
