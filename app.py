import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from datetime import datetime, timedelta

st.set_page_config(page_title="EUR/USD 70% Fix", layout="wide")
st.title("🇪🇺 Sniper EUR/USD : Historique & Précision")

@st.cache_data(ttl=3600)
def load_full_data():
    # On télécharge 1 an de données pour garantir 6 mois de signaux
    df = yf.download("EURUSD=X", period="1y", interval="1h")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    # On s'assure que l'index est en format datetime propre
    df.index = pd.to_datetime(df.index, utc=True)
    return df

data = load_full_data()

def get_signals(df):
    # Indicateurs
    df['EMA8'] = ta.ema(df['Close'], length=8)
    df['EMA21'] = ta.ema(df['Close'], length=21)
    df['EMA200'] = ta.ema(df['Close'], length=200)
    
    macd = ta.macd(df['Close'], fast=12, slow=26, signal=9)
    df['MACD'] = macd['MACD_12_26_9']
    df['MACD_S'] = macd['MACDs_12_26_9']
    df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)

    signals = []
    # On commence après la période de calcul de l'EMA200
    for i in range(200, len(df)):
        curr = df.iloc[i]
        prev = df.iloc[i-1]
        
        # 1. Filtre Horaire (Londres/NY)
        hour = df.index[i].hour
        is_active = 8 <= hour <= 17
        
        # 2. Tendance (EMA)
        uptrend = curr['Close'] > curr['EMA200'] and curr['EMA8'] > curr['EMA21']
        
        # 3. Momentum (MACD simple pour plus de signaux)
        momentum = curr['MACD'] > curr['MACD_S']
        
        # 4. Trigger (Rebond sur EMA 8 ou 21)
        trigger = curr['Low'] <= curr['EMA21'] and curr['Close'] > curr['EMA21']

        if is_active and uptrend and momentum and trigger:
            # Gestion du risque (Ratio 1:1.5)
            sl = curr['Close'] - (curr['ATR'] * 1.5)
            tp = curr['Close'] + (curr['ATR'] * 2.5)
            
            # Backtest sur les 48 heures suivantes
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
                "Date": df.index[i],
                "Prix": round(curr['Close'], 5),
                "Résultat": res
            })
    return signals

# --- AFFICHAGE ---
tab1, tab2 = st.tabs(["📊 Radar", "📜 Historique 6 Mois"])

with tab2:
    all_trades = get_signals(data)
    if all_trades:
        df_res = pd.DataFrame(all_trades)
        # Filtrer strictement les 180 derniers jours
        six_months_ago = pd.Timestamp.now(tz='UTC') - pd.Timedelta(days=180)
        df_final = df_res[df_res['Date'] > six_months_ago].copy()
        
        if not df_final.empty:
            finished = df_final[df_final['Résultat'] != "En cours"]
            if not finished.empty:
                wr = (finished['Résultat'] == "✅ GAGNÉ").sum() / len(finished) * 100
                st.metric("Taux de Réussite Réel (180j)", f"{wr:.1f}%")
            
            # Formater la date pour l'affichage
            df_final['Date'] = df_final['Date'].dt.strftime('%d/%m/%Y %H:%M')
            st.dataframe(df_final.sort_values(by="Date", ascending=False), use_container_width=True)
        else:
            st.warning("Aucun signal détecté sur les 6 derniers mois. Essayez d'élargir les critères.")
    else:
        st.error("L'algorithme n'a trouvé aucun trade
