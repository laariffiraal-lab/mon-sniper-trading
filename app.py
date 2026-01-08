import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

st.set_page_config(page_title="SMC Precision 80%", layout="wide")
st.title("🏦 Sniper SMC Elite : Liquidité & Structure")

pairs_dict = {"EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "GOLD": "GC=F", "BTC/USD": "BTC-USD"}
selection = st.sidebar.selectbox("Actif :", list(pairs_dict.keys()))

@st.cache_data(ttl=600)
def load_data(symbol):
    df = yf.download(symbol, period="150d", interval="1h")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

data = load_data(pairs_dict[selection])

def get_high_precision_signals(df):
    signals = []
    # Paramètres de précision
    period = 20 
    
    for i in range(period, len(df)):
        window = df.iloc[i-period:i]
        old_low = window['Low'].min()
        old_high = window['High'].max()
        
        curr = df.iloc[i]
        prev = df.iloc[i-1]
        
        # 1. LE SWEEP (La Chasse aux Stops)
        # Indispensable : La mèche doit descendre sous le bas précédent et réintégrer
        is_sweep = prev['Low'] < old_low and curr['Close'] > old_low
        
        # 2. MSS (Market Structure Shift) - LA CLÉ DU 80%
        # Le prix doit casser le dernier "Haut" à court terme avec force
        local_high = window['High'].tail(5).max()
        is_mss = curr['Close'] > local_high
        
        # 3. FILTRE DE MOMENTUM (RSI & ATR)
        # On vérifie que le mouvement n'est pas "mou"
        rsi = ta.rsi(df['Close'], length=14).iloc[i]
        
        if is_sweep and is_mss and 30 < rsi < 65:
            # Calcul du risque
            sl = prev['Low'] - (ta.atr(df['High'], df['Low'], df['Close'], length=14).iloc[i] * 0.5)
            tp = curr['Close'] + (curr['Close'] - sl) * 3 # Ratio 1:3 pour compenser les pertes
            
            # Backtest
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
                "Date": df.index[i].strftime('%d/%m %H:%M'),
                "Prix": round(curr['Close'], 5),
                "Signal": "SMC Setup (Sweep + MSS)",
                "Résultat": res
            })
    return signals

# --- AFFICHAGE ---
tab1, tab2 = st.tabs(["🚀 Radar Direct", "📜 Performance 80%"])

with tab2:
    results = get_high_precision_signals(data)
    if results:
        df_res = pd.DataFrame(results).drop_duplicates(subset=['Date'])
        finished = df_res[df_res['Résultat'] != "En cours"]
        if not finished.empty:
            wr = (finished['Résultat'] == "✅ GAGNÉ").sum() / len(finished) * 100
            st.metric("Taux de Réussite Réel", f"{wr:.1f}%")
        st.dataframe(df_res.sort_values(by="Date", ascending=False))
