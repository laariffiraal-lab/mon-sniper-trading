import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

st.set_page_config(page_title="SMC Precision Unlock", layout="wide")
st.title("🏦 Sniper SMC : Détection de Liquidité & Order Blocks")

pairs_dict = {"EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "GOLD": "GC=F", "BTC/USD": "BTC-USD"}
selection = st.sidebar.selectbox("Actif :", list(pairs_dict.keys()))

@st.cache_data(ttl=3600)
def load_data(symbol):
    # On prend 1 an pour être sûr d'avoir assez de recul
    df = yf.download(symbol, period="1y", interval="1h")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

data = load_data(pairs_dict[selection])

def get_unlocked_signals(df):
    signals = []
    # Paramètres assouplis pour capturer la réalité du marché
    for i in range(100, len(df)):
        # 1. Identifier la structure (Haut/Bas des 40 dernières heures)
        window = df.iloc[i-40:i]
        hi, lo = window['High'].max(), window['Low'].min()
        
        curr = df.iloc[i]
        prev = df.iloc[i-1]
        
        # 2. DETECTION DU SWEEP (Mèche qui dépasse le bas récent)
        # On regarde si la mèche basse est descendue sous le bas des 20 dernières heures
        recent_low = window['Low'].tail(20).min()
        is_sweep = curr['Low'] < recent_low and curr['Close'] > recent_low
        
        # 3. FILTRE DE TENDANCE LOURDE (EMA 200)
        ema200 = ta.ema(df['Close'], length=200).iloc[i]
        trend_up = curr['Close'] > ema200

        # 4. SIGNAL : Sweep + Bougie de retournement (Bougie verte dépassant le milieu de la précédente)
        rejection = curr['Close'] > (prev['Open'] + prev['Close']) / 2
        
        if is_sweep and trend_up and rejection:
            # Gestion du risque SMC : SL sous la mèche, TP au prochain sommet
            sl = curr['Low'] - (curr['Close'] * 0.001) # Petit buffer
            tp = hi
            
            # Ratio minimum de 1:2 pour valider le trade
            if (tp - curr['Close']) > (curr['Close'] - sl) * 1.5:
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
                    "Type": "SMC Liquidity Sweep",
                    "Résultat": res
                })
    return signals

tab1, tab2 = st.tabs(["🚀 Radar", "📜 Historique 6 Mois"])

with tab2:
    results = get_unlocked_signals(data)
    if results:
        df_res = pd.DataFrame(results).drop_duplicates(subset=['Date'])
        # Filtrage sur les 180 derniers jours
        df_res['dt'] = pd.to_datetime(df_res['Date'], format='%d/%m/%Y %H:%M')
        limit = pd.Timestamp.now() - pd.Timedelta(days=180)
        df_final = df_res[df_res['dt'] > limit]
        
        finished = df_final[df_final['Résultat'] != "En cours"]
        if not finished.empty:
            wr = (finished['Résultat'] == "✅ GAGNÉ").sum() / len(finished) * 100
            st.metric("Taux de Réussite SMC", f"{wr:.1f}%")
        
        st.dataframe(df_final.drop(columns=['dt']).sort_values(by="Date", ascending=False), use_container_width=True)
    else:
        st.warning("Aucun signal trouvé. Le marché a été trop directionnel ou sans chasses à la liquidité claires.")
