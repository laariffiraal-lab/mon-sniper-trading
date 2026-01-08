import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

st.set_page_config(page_title="EUR/USD 70% Sniper", layout="wide")
st.title("🇪🇺 Sniper EUR/USD : EMA & MACD")

@st.cache_data(ttl=3600)
def load_data():
    # Téléchargement d'un an pour stabiliser les calculs
    df = yf.download("EURUSD=X", period="1y", interval="1h")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.index = pd.to_datetime(df.index, utc=True)
    return df

data = load_data()

def apply_strategy(df):
    # --- INDICATEURS ---
    df['EMA21'] = ta.ema(df['Close'], length=21)
    df['EMA200'] = ta.ema(df['Close'], length=200)
    
    # MACD (Utilisation de noms de colonnes fixes)
    macd = ta.macd(df['Close'])
    df['M_L'] = macd.iloc[:, 0] # MACD Line
    df['M_S'] = macd.iloc[:, 2] # Signal Line
    
    df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)

    signals = []
    for i in range(200, len(df)):
        curr = df.iloc[i]
        prev = df.iloc[i-1]
        
        # 1. Filtre Horaire (Londres/NY)
        is_active = 8 <= df.index[i].hour <= 17
        
        # 2. Tendance & Momentum
        uptrend = curr['Close'] > curr['EMA200']
        momentum = curr['M_L'] > curr['M_S']
        
        # 3. Trigger (Rebond sur EMA 21)
        # On entre si la mèche basse touche l'EMA 21 et clôture au-dessus
        trigger = curr['Low'] <= curr['EMA21'] and curr['Close'] > curr['EMA21']

        if is_active and uptrend and momentum and trigger:
            # Gestion du risque
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

# --- AFFICHAGE ---
tab1, tab2 = st.tabs(["🚀 Radar", "📜 Historique 6 Mois"])

with tab2:
    trades = apply_strategy(data)
    if trades:
        df_res = pd.DataFrame(trades)
        # On filtre les 180 derniers jours
        limit = pd.Timestamp.now(tz='UTC') - pd.Timedelta(days=180)
        df_final = df_res[df_res['Date'] > limit].copy()
        
        if not df_final.empty:
            # Calcul du taux de réussite
            finished = df_final[df_final['Résultat'] != "En cours"]
            if not finished.empty:
                wr = (finished['Résultat'] == "✅ GAGNÉ").sum() / len(finished) * 100
                st.metric("Taux de Réussite (EUR/USD)", f"{wr:.1f}%")
            
            # Table des résultats
            df_final['Date'] = df_final['Date'].dt.strftime('%d/%m/%Y %H:%M')
            st.dataframe(df_final.sort_values(by="Date", ascending=False), use_container_width=True)
        else:
            st.warning("Aucun trade trouvé sur les 180 derniers jours.")
    else:
        st.info("Recherche de signaux en cours...")
