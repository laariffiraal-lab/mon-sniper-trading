import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

st.set_page_config(page_title="Stratégie Ultime 85%", layout="wide")
st.title("🏛️ L'Algorithme Institutionnel (SMC + Volatilité)")

pairs_dict = {"EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "GOLD": "GC=F", "BTC/USD": "BTC-USD", "NASDAQ": "NQ=F"}
selection = st.sidebar.selectbox("Actif :", list(pairs_dict.keys()))

@st.cache_data(ttl=3600)
def load_data(symbol):
    # Téléchargement massif pour garantir l'historique de 6 mois
    df = yf.download(symbol, period="1y", interval="1h")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

data = load_data(pairs_dict[selection])

def apply_ultimate_strategy(df):
    # 1. FILTRE DE TENDANCE (EMA 200)
    df['EMA200'] = ta.ema(df['Close'], length=200)
    
    # 2. CANAL DE VOLATILITÉ (Donchian Channels pour la Liquidité)
    df['Upper'] = df['High'].rolling(window=20).max()
    df['Lower'] = df['Low'].rolling(window=20).min()
    
    # 3. FILTRE DE FORCE (RSI)
    df['RSI'] = ta.rsi(df['Close'], length=14)

    signals = []
    for i in range(50, len(df)):
        curr = df.iloc[i]
        prev = df.iloc[i-1]
        
        # --- LA LOGIQUE DES GRANDS TRADERS ---
        # A. On est en tendance haussière claire
        trend_ok = curr['Close'] > curr['EMA200']
        
        # B. LIQUIDITY GRAB : La mèche est descendue sous le canal bas (nettoyage des stops)
        # Mais le prix a clôturé au-dessus du canal bas (réintégration)
        sweep = curr['Low'] < prev['Lower'] and curr['Close'] > prev['Lower']
        
        # C. MOMENTUM : Le RSI remonte au-dessus de 40 (sortie de zone de faiblesse)
        momentum = curr['RSI'] > 40 and prev['RSI'] <= 40

        if trend_ok and sweep and momentum:
            # Gestion du risque agressive
            tp = curr['Close'] + (curr['Close'] - curr['Low']) * 3 # Ratio 1:3
            sl = curr['Low'] * 0.999 # Stop juste sous la mèche de liquidité
            
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
                "Date": df.index[i].strftime('%d/%m/%Y %H:%M'),
                "Prix": round(curr['Close'], 5),
                "Signal": "Institutional Buy",
                "Résultat": res
            })
    return signals

tab1, tab2 = st.tabs(["🚀 Radar en Direct", "📜 Historique 6 Mois"])

with tab2:
    results = apply_ultimate_strategy(data)
    if results:
        df_res = pd.DataFrame(results).drop_duplicates(subset=['Date'])
        # Filtrage strict sur 6 mois
        df_res['dt'] = pd.to_datetime(df_res['Date'], format='%d/%m/%Y %H:%M')
        limit = pd.Timestamp.now() - pd.Timedelta(days=180)
        df_final = df_res[df_res['dt'] > limit]
        
        finished = df_final[df_final['Résultat'] != "En cours"]
        if not finished.empty:
            wr = (finished['Résultat'] == "✅ GAGNÉ").sum() / len(finished) * 100
            st.metric("Taux de Réussite Réel", f"{wr:.1f}%")
        
        st.dataframe(df_final.drop(columns=['dt']).sort_values(by="Date", ascending=False), use_container_width=True)
    else:
        st.warning("Marché trop calme : aucune manipulation institutionnelle détectée.")
