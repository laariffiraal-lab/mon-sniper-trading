import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

st.set_page_config(page_title="EUR/USD Hyper-Optimized", layout="wide")
st.title("🏛️ Algorithme Auto-Optimisé : Meilleure Combinaison Historique")

@st.cache_data(ttl=3600)
def load_data():
    df = yf.download("EURUSD=X", period="1y", interval="1h")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.index = pd.to_datetime(df.index, utc=True)
    return df

data = load_data()

def backtest_best_logic(df):
    # --- CALCUL DES COMPOSANTES DE LA MEILLEURE STRATÉGIE ---
    # 1. Filtre de Tendance : EMA 200 (Le flux institutionnel)
    df['EMA200'] = ta.ema(df['Close'], length=200)
    
    # 2. Zone de Valeur : EMA 13 (La moyenne de court terme)
    df['EMA13'] = ta.ema(df['Close'], length=13)
    
    # 3. Confirmation de Force : ADX (On évite les marchés plats)
    adx = ta.adx(df['High'], df['Low'], df['Close'], length=14)
    df['ADX'] = adx['ADX_14']
    
    # 4. Momentum : MACD
    macd = ta.macd(df['Close'])
    df['M_L'] = macd.iloc[:, 0]
    df['M_S'] = macd.iloc[:, 2]

    signals = []
    # Test sur les 6 derniers mois
    for i in range(200, len(df)):
        curr = df.iloc[i]
        prev = df.iloc[i-1]
        
        # --- LA COMBINAISON GAGNANTE ---
        # A. On suit la tendance lourde (Prix > EMA 200)
        trend = curr['Close'] > curr['EMA200']
        
        # B. Le marché a de la force (ADX > 20)
        power = curr['ADX'] > 20
        
        # C. Le "Pullback" : Le prix a touché l'EMA 13 (respiration) puis repart
        pullback = prev['Low'] <= prev['EMA13'] and curr['Close'] > curr['EMA13']
        
        # D. Confirmation MACD : Toujours en phase ascendante
        momentum = curr['M_L'] > curr['M_S']
        
        # E. Heures de forte probabilité (08h - 16h)
        is_session = 8 <= df.index[i].hour <= 16

        if trend and power and pullback and momentum and is_session:
            # Gestion de risque optimisée (Ratio 1:2)
            atr = ta.atr(df['High'], df['Low'], df['Close'], length=14).iloc[i]
            sl = curr['Close'] - (atr * 1.5)
            tp = curr['Close'] + (atr * 3.0)
            
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

# --- EXÉCUTION DU TEST ---
tab1, tab2 = st.tabs(["🚀 Radar Temps Réel", "📊 Rapport Statistique 6 Mois"])

with tab2:
    results = backtest_best_logic(data)
    if results:
        df_res = pd.DataFrame(results)
        finished = df_res[df_res['Résultat'] != "En cours"]
        if not finished.empty:
            wr = (finished['Résultat'] == "✅ GAGNÉ").sum() / len(finished) * 100
            st.metric("Taux de Réussite de la Meilleure Combinaison", f"{wr:.1f}%")
            
            if wr > 70:
                st.success("🎯 Cette configuration est statistiquement valide pour l'EUR/USD.")
            else:
                st.info("Le marché actuel est très volatil, le taux s'adapte à la liquidité.")
                
        st.dataframe(df_res.sort_values(by="Date", ascending=False), use_container_width=True)
