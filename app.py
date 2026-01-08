import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

st.set_page_config(page_title="SMC Liquidity + Fib", layout="wide")
st.title("🏦 Sniper SMC : Liquidity Grab & Golden Fib")

pairs_dict = {"EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "GOLD": "GC=F", "BTC/USD": "BTC-USD"}
selection = st.sidebar.selectbox("Actif :", list(pairs_dict.keys()))

@st.cache_data(ttl=600)
def load_data(symbol):
    df = yf.download(symbol, period="200d", interval="1h")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

data = load_data(pairs_dict[selection])

def get_smc_elite_signals(df):
    signals = []
    for i in range(50, len(df)):
        # 1. Définir le Range Majeur (50 bougies)
        window = df.iloc[i-50:i]
        hi, lo = window['High'].max(), window['Low'].min()
        
        # 2. Tracer Fibonacci
        fib_618 = lo + (0.618 * (hi - lo))
        fib_786 = lo + (0.786 * (hi - lo))
        
        curr = df.iloc[i]
        prev = df.iloc[i-1]
        
        # 3. DÉTECTION DU "STOP HUNT" (Liquidité)
        # Le prix doit passer sous un bas récent (old_low) et réintégrer vite
        old_low = window['Low'].tail(15).min()
        is_sweep = prev['Low'] < old_low and curr['Close'] > old_low
        
        # 4. CONFLUENCE ZONE D'ACHAT
        # Le sweep doit se passer dans la Golden Pocket (61.8 - 78.6)
        in_golden_zone = fib_786 <= curr['Low'] <= fib_618
        
        # 5. CONFIRMATION DE STRUCTURE (MSS)
        # On veut une bougie de retournement (verte et forte)
        is_mss = curr['Close'] > curr['Open'] and curr['Close'] > prev['High']

        if is_sweep and in_golden_zone and is_mss:
            # Sortie de Pro : On vise le haut du range (Ratio énorme)
            sl = curr['Low'] - (ta.atr(df['High'], df['Low'], df['Close']).iloc[i] * 0.5)
            tp = hi
            
            future = df.iloc[i+1 : i+100]
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
                "Setup": "Liquidity Grab + Fib 61.8%",
                "Résultat": res
            })
    return signals

tab1, tab2 = st.tabs(["🚀 Radar SMC", "📜 Backtest Institutionnel"])

with tab2:
    results = get_smc_elite_signals(data)
    if results:
        df_res = pd.DataFrame(results).drop_duplicates(subset=['Date'])
        finished = df_res[df_res['Résultat'] != "En cours"]
        if not finished.empty:
            wr = (finished['Résultat'] == "✅ GAGNÉ").sum() / len(finished) * 100
            st.metric("Taux de Réussite (SMC/Fib)", f"{wr:.1f}%")
        st.table(df_res.sort_values(by="Date", ascending=False))
