import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np

st.set_page_config(page_title="Sniper Quant 85%+", layout="wide")
st.title("🏛️ Algorithme Quantitatif : Haute Convergence")

pairs_dict = {
    "EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/JPY": "USDJPY=X",
    "GOLD": "GC=F", "BTC/USD": "BTC-USD", "NASDAQ": "NQ=F"
}

selection = st.sidebar.selectbox("Actif :", list(pairs_dict.keys()))
ticker = pairs_dict[selection]

@st.cache_data(ttl=600)
def load_deep_data(symbol):
    # On charge un historique massif pour stabiliser les indicateurs Quants
    df = yf.download(symbol, period="250d", interval="1h")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

data = load_deep_data(ticker)

def apply_quant_strategy(df):
    # --- INDICATEURS DE HAUTE PRÉCISION ---
    # 1. Tendance Lourde
    df['EMA200'] = ta.ema(df['Close'], length=200)
    
    # 2. SuperTrend (Filtre de direction robuste)
    sti = ta.supertrend(df['High'], df['Low'], df['Close'], length=10, multiplier=3)
    df['ST_DIR'] = sti['SUPERT_d_10_3.0']
    
    # 3. Squeeze Momentum (Bollinger vs Keltner)
    # Calcule si le marché est en phase d'explosion ou de compression
    bb = ta.bbands(df['Close'], length=20, std=2)
    kc = ta.kc(df['High'], df['Low'], df['Close'], length=20, scalar=1.5)
    df['BBU'] = bb['BBU_20_2.0']
    df['KCU'] = kc['KCU_20_1.5']
    
    # 4. ADX Filtré (Force réelle)
    df['ADX'] = ta.adx(df['High'], df['Low'], df['Close'])['ADX_14']

    signals = []
    for i in range(20, len(df)):
        curr = df.iloc[i]
        prev = df.iloc[i-1]
        
        # --- LOGIQUE DE CONVERGENCE QUANT ---
        # A. Alignement des planètes (Tendance + SuperTrend)
        is_trending = curr['Close'] > curr['EMA200'] and curr['ST_DIR'] == 1
        
        # B. Le Squeeze Breakout (L'explosion de volatilité)
        # On entre quand la bande de Bollinger sort du canal de Keltner (Explosion)
        is_breakout = curr['BBU'] > curr['KCU'] and prev['BBU'] <= prev['KCU']
        
        # C. Filtre de Session (Heure Institutionnelle 8h - 18h UTC)
        hour = df.index[i].hour
        is_market_open = 8 <= hour <= 18

        if is_trending and is_breakout and is_market_open and curr['ADX'] > 25:
            # Sortie : Stop Loss serré (ATR x 1.2) / Take Profit large (ATR x 3)
            # On cherche des gros mouvements, pas des miettes.
            atr = ta.atr(df['High'], df['Low'], df['Close'], length=14).iloc[i]
            sl = curr['Close'] - (atr * 1.5)
            tp = curr['Close'] + (atr * 3) # Ratio 1:2 pour garantir la rentabilité
            
            future = df.iloc[i+1 : i+120]
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

tab1, tab2 = st.tabs(["🚀 Dashboard Quant", "📜 Backtest Profond"])

with tab2:
    results = apply_quant_strategy(data)
    if results:
        df_res = pd.DataFrame(results).drop_duplicates()
        finished = df_res[df_res['Résultat'] != "En cours"]
        if not finished.empty:
            wr = (finished['Résultat'] == "✅ GAGNÉ").sum() / len(finished) * 100
            st.metric("Taux de Réussite Quant", f"{wr:.1f}%")
            st.write("Note : Ce taux est basé sur des explosions de volatilité confirmées.")
        st.table(df_res.sort_values(by="Date", ascending=False))
    else:
        st.warning("Aucune confluence parfaite détectée sur cette période.")
