import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

st.set_page_config(page_title="EUR/USD Pro Sniper", layout="wide")
st.title("🇪🇺 Sniper EUR/USD : Précision 70%+")

@st.cache_data(ttl=3600)
def load_eur_data():
    # Chargement d'un an pour stabiliser les calculs
    df = yf.download("EURUSD=X", period="1y", interval="1h")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.index = pd.to_datetime(df.index, utc=True)
    return df

data = load_eur_data()

def apply_strategy(df):
    # Indicateurs Techniques
    df['EMA21'] = ta.ema(df['Close'], length=21)
    df['EMA200'] = ta.ema(df['Close'], length=200)
    
    # MACD pour la force du mouvement
    macd = ta.macd(df['Close'], fast=12, slow=26, signal=9)
    # Protection contre les erreurs de noms de colonnes
    df['MACD_LINE'] = macd.iloc[:, 0]
    df['MACD_SIG'] = macd.iloc[:, 2]
    
    df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)

    signals = []
    for i in range(200, len(df)):
        curr = df.iloc[i]
        prev = df.iloc[i-1]
        
        # 1. Filtre de Session (Londres + NY : 08h à 17h UTC)
        hour = df.index[i].hour
        is_active = 8 <= hour <= 17
        
        # 2. Tendance (Prix au-dessus de l'EMA 200)
        is_trending = curr['Close'] > curr['EMA200']
        
        # 3. Momentum (Ligne MACD au-dessus du Signal)
        is_momentum = curr['MACD_LINE'] > curr['MACD_SIG']
        
        # 4. Trigger de précision (Rebond sur l'EMA 21)
        # On entre quand la mèche touche l'EMA 21 mais clôture au-dessus
        is_rebound = curr['Low'] <= curr['EMA21'] and curr['Close'] > curr['EMA21']

        if is_active and is_trending and is_momentum and is_rebound:
            # Gestion du risque (Ratio 1:2)
            sl = curr['Close'] - (curr['ATR'] * 1.5)
            tp = curr['Close'] + (curr['ATR'] * 3.0)
            
            future = df.iloc[i+1 : i+50]
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

tab1, tab2 = st.tabs(["🚀 Radar Direct", "📜 Historique 6 Mois"])

with tab2:
    all_trades = apply_strategy(data)
    if all_trades:
        df_res = pd.DataFrame(all_trades)
        # On garde les 180 derniers jours
        limit_date = pd.Timestamp.now(tz='UTC') - pd.Timedelta(days=180)
        df_final = df_res[df_res['Date'] > limit_date].copy()
        
        if not df_final.empty:
            finished = df_final[df_final['Résultat'] != "En cours"]
            if not finished.empty:
                wr = (finished['Résultat'] == "✅ GAGNÉ").sum() / len(finished) * 100
                st.metric("Taux de Réussite (EUR/USD)", f"{wr:.1f}%")
            
            df_final['Date'] = df_final['Date'].dt.strftime('%d/%m/%Y %H:%M')
            st.dataframe(df_final.sort_values(by="Date", ascending=False), use_container_width=True)
        else:
            st.warning("Aucun trade trouvé sur les 6 derniers mois avec ces critères.")
    else:
