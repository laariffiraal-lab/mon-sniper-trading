import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

st.set_page_config(page_title="EUR/USD 70% Strategy", layout="wide")
st.title("🇪🇺 Sniper EUR/USD : EMA + MACD + Session")

@st.cache_data(ttl=3600)
def load_data():
    # On prend 1 an de données en 1H pour l'historique
    df = yf.download("EURUSD=X", period="1y", interval="1h")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

data = load_data()

def apply_70pc_strategy(df):
    # 1. MOYENNES MOBILES (Le "Crossover" institutionnel)
    df['EMA8'] = ta.ema(df['Close'], length=8)
    df['EMA21'] = ta.ema(df['Close'], length=21)
    df['EMA200'] = ta.ema(df['Close'], length=200)
    
    # 2. MACD (Paramètres standards pour confirmer le momentum)
    macd = ta.macd(df['Close'], fast=12, slow=26, signal=9)
    df['MACD'] = macd['MACD_12_26_9']
    df['MACD_S'] = macd['MACDs_12_26_9']
    
    # 3. ATR pour le Stop Loss (1.5x ATR)
    df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)

    signals = []
    for i in range(50, len(df)):
        curr = df.iloc[i]
        prev = df.iloc[i-1]
        
        # --- CONDITIONS DE HAUTE PROBABILITÉ ---
        
        # A. SESSION : Uniquement Londres & New York (8h - 16h UTC)
        hour = df.index[i].hour
        is_active_session = 8 <= hour <= 16
        
        # B. TENDANCE : Prix au-dessus de l'EMA 200 et EMA8 > EMA21
        trend_ok = curr['Close'] > curr['EMA200'] and curr['EMA8'] > curr['EMA21']
        
        # C. MOMENTUM : MACD au-dessus de sa ligne de signal (Achat confirmé)
        momentum_ok = curr['MACD'] > curr['MACD_S']
        
        # D. LE TRIGGER : On entre quand le prix touche ou descend vers l'EMA 8 (Le Rebond)
        trigger = curr['Low'] <= curr['EMA8'] and curr['Close'] > curr['EMA8']

        if is_active_session and trend_ok and momentum_ok and trigger:
            # Gestion du risque (Ratio 1:1.5 pour sécuriser les 70%)
            sl = curr['Close'] - (curr['ATR'] * 1.5)
            tp = curr['Close'] + (curr['ATR'] * 2.2)
            
            future = df.iloc[i+1 : i+48]
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

tab1, tab2 = st.tabs(["🚀 Radar Direct", "📜 Historique 6 Mois"])

with tab2:
    results = apply_70pc_strategy(data)
    if results:
        df_res = pd.DataFrame(results).drop_duplicates()
        df_res['dt'] = pd.to_datetime(df_res['Date'], format='%d/%m %H:%M')
        # On affiche les 180 derniers jours
        limit = pd.Timestamp.now() - pd.Timedelta(days=180)
        df_final = df_res[df_res['dt'] > limit]
        
        finished = df_final[df_final['Résultat'] != "En cours"]
        if not finished.empty:
            wr = (finished['Résultat'] == "✅ GAGNÉ").sum() / len(finished) * 100
            st.metric("Taux de Réussite (Objectif 70%)", f"{wr:.1f}%")
        
        st.table(df_final.drop(columns=['dt']).sort_values(by="Date", ascending=False))
