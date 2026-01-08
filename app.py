import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

st.set_page_config(page_title="Sniper Master 80%", layout="wide")
st.title("🏛️ Algorithme Master Trend : Haute Probabilité")

pairs_dict = {"EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "GOLD": "GC=F", "NASDAQ": "NQ=F", "BTC/USD": "BTC-USD"}
selection = st.sidebar.selectbox("Choisir l'actif :", list(pairs_dict.keys()))

@st.cache_data(ttl=3600)
def load_data(symbol):
    df = yf.download(symbol, period="1y", interval="1h")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

data = load_data(pairs_dict[selection])

def apply_master_strategy(df):
    # 1. STRUCTURE DE TENDANCE
    df['EMA8'] = ta.ema(df['Close'], length=8)
    df['EMA21'] = ta.ema(df['Close'], length=21)
    df['EMA200'] = ta.ema(df['Close'], length=200)
    
    # 2. VOLATILITÉ (Canaux de Keltner)
    # Le prix doit sortir du canal supérieur pour confirmer l'impulsion
    kc = ta.kc(df['High'], df['Low'], df['Close'], length=20, scalar=2)
    df['KCU'] = kc['KCU_20_2.0']
    
    # 3. FILTRE DE MOMENTUM
    df['RSI'] = ta.rsi(df['Close'], length=14)

    signals = []
    for i in range(50, len(df)):
        curr = df.iloc[i]
        prev = df.iloc[i-1]
        
        # --- LOGIQUE MASTER 80% ---
        # A. Tendance Lourde : On est au-dessus de l'EMA 200
        tendance_haute = curr['Close'] > curr['EMA200']
        
        # B. Alignement : EMA8 > EMA21 (Tendance propre)
        alignement = curr['EMA8'] > curr['EMA21']
        
        # C. TRIGGER : Le prix clôture AU-DESSUS du canal de Keltner (Explosion)
        explosion = curr['Close'] > curr['KCU'] and prev['Close'] <= prev['KCU']
        
        # D. FILTRE ANTI-FATIGUE : RSI < 70 (On n'est pas encore en surachat)
        pas_trop_haut = curr['RSI'] < 70

        if tendance_haute and alignement and explosion and pas_trop_haut:
            # Gestion du risque : Stop Loss sous l'EMA 21 / TP Ratio 1:2
            sl = curr['EMA21']
            tp = curr['Close'] + (curr['Close'] - sl) * 2
            
            # Vérification historique
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
                "Date": df.index[i].strftime('%d/%m/%Y %H:%M'),
                "Prix": round(curr['Close'], 5),
                "Résultat": res
            })
    return signals

tab1, tab2 = st.tabs(["🚀 Radar", "📊 Backtest (Historique 6-12 mois)"])

with tab2:
    results = apply_master_strategy(data)
    if results:
        df_res = pd.DataFrame(results).drop_duplicates()
        finished = df_res[df_res['Résultat'] != "En cours"]
        if not finished.empty:
            wr = (finished['Résultat'] == "✅ GAGNÉ").sum() / len(finished) * 100
            st.metric("Taux de Réussite Réel", f"{wr:.1f}%")
        st.dataframe(df_res.sort_values(by="Date", ascending=False), use_container_width=True)
    else:
        st.warning("Aucune impulsion majeure détectée sur cet actif.")
