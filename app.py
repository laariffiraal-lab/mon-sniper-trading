import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

st.set_page_config(page_title="Sniper Momentum 80%", layout="wide")
st.title("🎯 Stratégie Triple Confluence (Objectif 80%+) ")

pairs_dict = {
    "EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/JPY": "USDJPY=X",
    "USD/CAD": "USDCAD=X", "GOLD": "GC=F", "BTC/USD": "BTC-USD"
}

selection = st.sidebar.selectbox("Choisir l'actif :", list(pairs_dict.keys()))
ticker = pairs_dict[selection]

@st.cache_data(ttl=600)
def load_data(symbol):
    # On utilise l'unité 1H pour la stabilité des 80%
    df = yf.download(symbol, period="180d", interval="1h")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

data = load_data(ticker)

def apply_strategy(df):
    # 1. Moyennes Mobiles
    df['EMA5'] = ta.ema(df['Close'], length=5)
    df['EMA13'] = ta.ema(df['Close'], length=13)
    df['EMA200'] = ta.ema(df['Close'], length=200)
    
    # 2. ADX pour la force de la tendance
    df['ADX'] = ta.adx(df['High'], df['Low'], df['Close'])['ADX_14']
    
    # 3. RSI pour éviter d'entrer trop tard
    df['RSI'] = ta.rsi(df['Close'], length=14)
    
    # 4. ATR pour le Stop Loss dynamique
    df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)

    signals = []
    for i in range(1, len(df)):
        curr = df.iloc[i]
        prev = df.iloc[i-1]
        
        # --- LES 4 CONDITIONS DU SUCCÈS ---
        # A. Tendance de fond : Prix > EMA 200
        cond1 = curr['Close'] > curr['EMA200']
        
        # B. Croisement de validation (Golden Cross local)
        cond2 = prev['EMA5'] < prev['EMA13'] and curr['EMA5'] > curr['EMA13']
        
        # C. Force : ADX > 25 (Indique une tendance forte, pas un range)
        cond3 = curr['ADX'] > 25
        
        # D. Sécurité : RSI entre 50 et 65 (On a encore de la place avant d'être fatigué)
        cond4 = 50 < curr['RSI'] < 65

        if cond1 and cond2 and cond3 and cond4:
            # Backtest du signal
            future = df.iloc[i+1 : i+48]
            # TP à 1.5x l'ATR / SL à 1.5x l'ATR (Ratio 1:1 très haute probabilité)
            tp = curr['Close'] + (curr['ATR'] * 2)
            sl = curr['Close'] - (curr['ATR'] * 1.5)
            
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
                "Prix Entrée": round(curr['Close'], 5),
                "Résultat": res
            })
    return signals

# Affichage
tab1, tab2 = st.tabs(["📈 Radar", "📊 Backtest (Historique)"])

with tab2:
    sig_list = apply_strategy(data)
    if sig_list:
        df_res = pd.DataFrame(sig_list)
        finished = df_res[df_res['Résultat'] != "En cours"]
        if not finished.empty:
            wr = (finished['Résultat'] == "✅ GAGNÉ").sum() / len(finished) * 100
            st.metric("Taux de Réussite Réel", f"{wr:.1f}%")
        st.table(df_res.sort_values(by="Date", ascending=False))
    else:
        st.warning("Conditions trop strictes : aucun signal parfait détecté.")
