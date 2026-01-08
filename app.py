import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

st.set_page_config(page_title="SMC 6-Month Backtest", layout="wide")
st.title("🏦 Sniper SMC : Historique Profond (6 Mois)")

pairs_dict = {"EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "GOLD": "GC=F", "BTC/USD": "BTC-USD"}
selection = st.sidebar.selectbox("Choisir l'actif :", list(pairs_dict.keys()))

@st.cache_data(ttl=3600)
def load_full_history(symbol):
    # On télécharge 1 an pour être sûr d'avoir 6 mois de signaux après calculs
    df = yf.download(symbol, period="1y", interval="1h")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

data = load_full_history(pairs_dict[selection])

def get_deep_smc_signals(df):
    signals = []
    # On commence le scan 200 heures après le début des données
    for i in range(200, len(df)):
        # Fenêtre de structure (Lookback de 50h)
        window = df.iloc[i-50:i]
        hi, lo = window['High'].max(), window['Low'].min()
        
        # Fibonacci Golden Pocket
        fib_618 = lo + (0.618 * (hi - lo))
        fib_786 = lo + (0.786 * (hi - lo))
        
        curr = df.iloc[i]
        prev = df.iloc[i-1]
        
        # 1. LIQUIDITY SWEEP (Le piège des Stop Loss)
        # On cherche un bas local dans les 10 dernières heures
        local_low = window['Low'].tail(10).min()
        is_sweep = prev['Low'] < local_low and curr['Close'] > local_low
        
        # 2. CONFLUENCE FIBONACCI
        in_zone = fib_786 <= curr['Low'] <= fib_618
        
        # 3. MSS (Changement de structure)
        is_bullish = curr['Close'] > prev['High']

        if is_sweep and in_zone and is_bullish:
            # Simulation : TP au sommet / SL sous la mèche du sweep
            sl = curr['Low'] - 0.0010 # Marge de sécurité
            tp = hi
            
            # On regarde les 5 jours suivants (120h)
            future = df.iloc[i+1 : i+120]
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
                "Type": "SMC Liquidity Grab",
                "Résultat": res
            })
    return signals

tab1, tab2 = st.tabs(["🚀 Radar Temps Réel", "📜 Historique Complet (6 mois)"])

with tab2:
    st.subheader(f"Analyse des 180 derniers jours sur {selection}")
    all_results = get_deep_smc_signals(data)
    
    if all_results:
        df_res = pd.DataFrame(all_results)
        # On ne garde que les 6 derniers mois
        df_res['Date_dt'] = pd.to_datetime(df_res['Date'], format='%d/%m/%Y %H:%M')
        six_months_ago = pd.Timestamp.now() - pd.Timedelta(days=180)
        df_final = df_res[df_res['Date_dt'] > six_months_ago]
        
        finished = df_final[df_final['Résultat'] != "En cours"]
        if not finished.empty:
            wr = (finished['Résultat'] == "✅ GAGNÉ").sum() / len(finished) * 100
            st.metric("Taux de Réussite SMC (6 mois)", f"{wr:.1f}%")
        
        st.dataframe(df_final.drop(columns=['Date_dt']).sort_values(by="Date", ascending=False), use_container_width=True)
    else:
        st.warning("Aucun signal trouvé. Essayez de changer d'actif (ex: GOLD) pour voir plus de volatilité.")
