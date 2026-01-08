import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

st.set_page_config(page_title="Sniper Pro Final", layout="wide")
st.title("🛡️ Algorithme Quantitatif : Correction & Précision")

pairs_dict = {
    "EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "GOLD": "GC=F", "BTC/USD": "BTC-USD"
}

selection = st.sidebar.selectbox("Choisir l'actif :", list(pairs_dict.keys()))
ticker = pairs_dict[selection]

@st.cache_data(ttl=600)
def load_data(symbol):
    df = yf.download(symbol, period="200d", interval="1h")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

data = load_data(ticker)

def apply_strategy(df):
    # 1. Filtre de Tendance Institutionnelle
    df['EMA200'] = ta.ema(df['Close'], length=200)
    
    # 2. Volatilité (Bandes de Bollinger)
    bbands = ta.bbands(df['Close'], length=20, std=2)
    df['BBU'] = bbands['BBU_20_2.0']
    
    # 3. Force Relative (RSI)
    df['RSI'] = ta.rsi(df['Close'], length=14)
    
    # 4. ATR pour la gestion du risque
    df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)

    signals = []
    for i in range(20, len(df)):
        curr = df.iloc[i]
        prev = df.iloc[i-1]
        
        # --- LOGIQUE DE CONVERGENCE (Objectif 80%) ---
        # A. On ne trade que dans le sens de la tendance lourde
        trend_up = curr['Close'] > curr['EMA200']
        
        # B. On attend une explosion de prix (Cassure Bollinger)
        breakout = prev['Close'] < prev['BBU'] and curr['Close'] > curr['BBU']
        
        # C. On vérifie que le RSI n'est pas encore "épuisé" (< 70)
        momentum = 50 < curr['RSI'] < 70
        
        # D. Filtre de session (Uniquement pendant que Londres/NY sont ouverts)
        hour = df.index[i].hour
        active_hours = 8 <= hour <= 18

        if trend_up and breakout and momentum and active_hours:
            # Gestion du risque Ratio 1:2
            tp = curr['Close'] + (curr['ATR'] * 2)
            sl = curr['Close'] - (curr['ATR'] * 1.5)
            
            future = df.iloc[i+1 : i+72]
            res = "En cours"
            for _, row in future.iterrows():
                if row['High'] >= tp:
                    res = "✅ GAGNÉ"
                    break
                if row['Low'] <= sl:
                    res = "❌ PERDU"
                    break
            
            signals.append({
                "Date": df.index[i].strftime('%d/%m %H:%M'),
                "Prix": round(curr['Close'], 5),
                "Résultat": res
            })
    return signals

tab1, tab2 = st.tabs(["🚀 Signal Direct", "📊 Backtest 80%"])

with tab1:
    st.info("Stratégie active : Tendance EMA 200 + Breakout Volatilité + Session Institutionnelle.")
    st.line_chart(data['Close'].tail(100))

with tab2:
    sig_results = apply_strategy(data)
    if sig_results:
        df_res = pd.DataFrame(sig_results).drop_duplicates()
        finished = df_res[df_res['Résultat'] != "En cours"]
        if not finished.empty:
            wr = (finished['Résultat'] == "✅ GAGNÉ").sum() / len(finished) * 100
            st.metric("Taux de Réussite Réel", f"{wr:.1f}%")
        st.table(df_res.sort_values(by="Date", ascending=False))
