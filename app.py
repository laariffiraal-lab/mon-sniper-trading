import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

st.set_page_config(page_title="SMC Breaker 80%", layout="wide")
st.title("🏦 Sniper SMC : Breaker Blocks & Liquidité")

# Configuration des actifs
pairs = {"GOLD": "GC=F", "EUR/USD": "EURUSD=X", "NASDAQ": "NQ=F", "BTC/USD": "BTC-USD"}
selection = st.sidebar.selectbox("Actif", list(pairs.keys()))

@st.cache_data(ttl=3600)
def load_data(symbol):
    # On télécharge 1 an pour avoir un historique de 6 mois solide
    df = yf.download(symbol, period="1y", interval="1h")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

data = load_data(pairs[selection])

def apply_smc_breaker(df):
    # Calculs de base stables (sans dépendre de noms de colonnes variables)
    df['EMA200'] = ta.ema(df['Close'], length=200)
    df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
    
    signals = []
    # Scan sur les 6 derniers mois (environ 4300 bougies horaires)
    for i in range(100, len(df)):
        window = df.iloc[i-30:i]
        
        # 1. Identification d'un "Fail High" (Liquidité)
        high_recent = window['High'].max()
        low_recent = window['Low'].min()
        
        curr = df.iloc[i]
        prev = df.iloc[i-1]
        
        # --- LOGIQUE SMC BREAKER ---
        # A. Tendance de fond
        trend_up = curr['Close'] > curr['EMA200']
        
        # B. Le Breaker : Le prix a cassé un ancien sommet mais a réintégré (Manipulation)
        # Puis il casse la structure vers le haut
        manipulation = prev['High'] > high_recent and curr['Close'] < high_recent
        
        # C. Rebond sur "Order Block" : On entre quand le prix touche le milieu du range récent
        mid_point = (high_recent + low_recent) / 2
        retest_ok = curr['Low'] <= mid_point and curr['Close'] > mid_point
        
        if trend_up and retest_ok and curr['Close'] > prev['Close']:
            # Gestion du Risque : TP au sommet / SL sous le point bas du range
            sl = low_recent
            tp = high_recent + (high_recent - low_recent)
            
            # Calcul du résultat
            future = df.iloc[i+1 : i+100]
            res = "En cours"
            for _, row in future.iterrows():
                if row['High'] >= tp:
                    res = "✅ GAGNÉ"
                    break
                if row['Low'] <= sl:
                    res = "❌ STOP OUT"
                    break
            
            signals.append({
                "Date": df.index[i].strftime('%d/%m/%Y %H:%M'),
                "Prix": round(curr['Close'], 5),
                "Setup": "SMC Breaker Rebound",
                "Résultat": res
            })
    return signals

tab1, tab2 = st.tabs(["🚀 Radar Temps Réel", "📜 Historique 6 Mois"])

with tab2:
    results = apply_smc_breaker(data)
    if results:
        df_res = pd.DataFrame(results).drop_duplicates(subset=['Date'])
        # Filtrage 180 jours
        df_res['dt'] = pd.to_datetime(df_res['Date'], format='%d/%m/%Y %H:%M')
        limit = pd.Timestamp.now() - pd.Timedelta(days=180)
        df_final = df_res[df_res['dt'] > limit]
        
        finished = df_final[df_final['Résultat'] != "En cours"]
        if not finished.empty:
            wr = (finished['Résultat'] == "✅ GAGNÉ").sum() / len(finished) * 100
            st.metric("Taux de Réussite (SMC Elite)", f"{wr:.1f}%")
        
        st.dataframe(df_final.drop(columns=['dt']).sort_values(by="Date", ascending=False), use_container_width=True)
    else:
        st.warning("Aucun signal SMC validé trouvé sur 6 mois.")
