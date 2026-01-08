import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

st.set_page_config(page_title="SMC Liquidity Sniper", layout="wide")
st.title("🏦 Sniper SMC Elite : Order Blocks & Liquidity Sweeps")

# 1. LISTE DES PAIRES
pairs_dict = {"EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/JPY": "USDJPY=X", "GOLD": "GC=F"}
selection = st.sidebar.selectbox("Actif :", list(pairs_dict.keys()))
ticker = pairs_dict[selection]

@st.cache_data(ttl=3600)
def load_data(symbol):
    df = yf.download(symbol, period="120d", interval="1h")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

data = load_data(ticker)

def get_liquidity_signals(df):
    signals = []
    for i in range(30, len(df)):
        window = df.iloc[i-20:i]
        
        # Identification des points de liquidité (Anciens bas/hauts)
        old_low = window['Low'].min()
        old_high = window['High'].max()
        
        curr = df.iloc[i]
        prev = df.iloc[i-1]
        
        # --- LOGIQUE DE LIQUIDITÉ SMC ---
        
        # 1. LIQUIDITY SWEEP (La Chasse aux Stops)
        # Le prix doit passer sous l'ancien bas puis clôturer au-dessus
        sweep_low = prev['Low'] < old_low and curr['Close'] > old_low
        
        # 2. CHoCH (Change of Character)
        # Après le sweep, on veut voir une cassure de la structure locale
        is_choch = curr['Close'] > window['High'].iloc[-5:].max()
        
        # 3. FILTRE DE VOLUME (Impulsion)
        # On utilise l'ATR pour vérifier que le mouvement est explosif
        atr = ta.atr(df['High'], df['Low'], df['Close'], length=14).iloc[i]
        is_explosive = (curr['High'] - curr['Low']) > (1.5 * atr)

        if sweep_low and is_choch:
            # On cherche le test de l'Order Block créé par le sweep
            ob_zone = old_low
            
            # Simulation du résultat
            future = df.iloc[i+1 : i+60]
            if future.empty: continue
            
            tp = curr['Close'] + (curr['Close'] - old_low) * 3 # Ratio 1:3 minimum
            sl = old_low - (atr * 0.5)
            
            res = "En cours"
            for _, row in future.iterrows():
                if row['High'] >= tp:
                    res = "✅ GAGNÉ (LIQUIDITY)"
                    break
                if row['Low'] <= sl:
                    res = "❌ STOP OUT"
                    break
            
            signals.append({
                "Date": df.index[i].strftime('%d/%m %H:%M'),
                "Setup": "Bullish Sweep + CHoCH",
                "Prix": round(curr['Close'], 4),
                "Résultat": res
            })
            
    return signals

tab1, tab2 = st.tabs(["🚀 Radar de Liquidité", "📜 Historique SMC"])

with tab1:
    st.header(f"Recherche de Liquidité : {selection}")
    st.write("L'algorithme attend qu'un 'bas' soit balayé (Sweep) pour piéger les vendeurs avant d'acheter.")
    st.line_chart(data['Close'].tail(120))

with tab2:
    results = get_liquidity_signals(data)
    if results:
        df_res = pd.DataFrame(results)
        finished = df_res[df_res['Résultat'] != "En cours"]
        if not finished.empty:
            wr = (finished['Résultat'] == "✅ GAGNÉ (LIQUIDITY)").sum() / len(finished) * 100
            st.metric("Taux de Réussite (SMC Liquidity)", f"{wr:.1f}%")
        st.table(df_res.sort_values(by="Date", ascending=False))
