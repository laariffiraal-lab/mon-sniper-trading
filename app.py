import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from datetime import datetime

st.set_page_config(page_title="SMC Liquidity Radar", layout="wide")
st.title("🏦 Sniper SMC : Liquidité & Flux Institutionnel")

pairs_dict = {
    "EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", 
    "USD/JPY": "USDJPY=X", "GOLD": "GC=F", "BTC/USD": "BTC-USD"
}

selection = st.sidebar.selectbox("Actif à scanner :", list(pairs_dict.keys()))
ticker = pairs_dict[selection]

@st.cache_data(ttl=600)
def load_data(symbol):
    # On charge 180 jours pour avoir un historique solide
    df = yf.download(symbol, period="180d", interval="1h")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

data = load_data(ticker)

def get_signals(df):
    signals = []
    # Paramètres de structure
    lookback = 15 
    
    for i in range(lookback + 5, len(df)):
        # 1. Identifier la Liquidité (Point bas récent)
        window = df.iloc[i-lookback:i]
        recent_low = window['Low'].min()
        recent_high = window['High'].max()
        
        curr = df.iloc[i]
        prev = df.iloc[i-1]
        
        # 2. LE SWEEP (Balayage)
        # La mèche de la bougie précédente ou actuelle passe sous le bas récent
        # Mais le prix clôture au-dessus (Rejet de liquidité)
        is_sweep = (prev['Low'] < recent_low or curr['Low'] < recent_low) and curr['Close'] > recent_low
        
        # 3. LE CHoCH (Changement de caractère)
        # On veut voir une bougie de force juste après ou pendant le sweep
        is_bullish_engulfing = curr['Close'] > prev['High']
        
        if is_sweep and is_bullish_engulfing:
            # Calcul du TP/SL
            atr = ta.atr(df['High'], df['Low'], df['Close']).iloc[i]
            sl = min(curr['Low'], prev['Low']) - (atr * 0.5)
            tp = curr['Close'] + (curr['Close'] - sl) * 2 # Ratio 1:2
            
            # Vérifier le futur pour le backtest
            future = df.iloc[i+1 : i+50]
            outcome = "En cours"
            for _, row in future.iterrows():
                if row['High'] >= tp:
                    outcome = "✅ GAGNÉ"
                    break
                if row['Low'] <= sl:
                    outcome = "❌ PERDU"
                    break
            
            signals.append({
                "Date": df.index[i].strftime('%d/%m/%Y %H:%M'),
                "Prix": round(curr['Close'], 5),
                "Type": "Bullish Sweep (SMC)",
                "Résultat": outcome
            })
            
    return signals

tab1, tab2 = st.tabs(["🚀 Radar en Direct", "📜 Historique des Sweeps"])

with tab1:
    st.subheader(f"Analyse de structure sur {selection}")
    # On affiche les derniers chandeliers
    st.line_chart(data['Close'].tail(100))
    
    curr_data = data.iloc[-1]
    st.write(f"Prix actuel : **{curr_data['Close']:.5f}**")
    st.info("Le radar cherche actuellement un balayage des bas récents pour valider une entrée institutionnelle.")

with tab2:
    st.subheader("Signaux de Liquidité détectés (6 mois)")
    all_signals = get_signals(data)
    
    if all_signals:
        df_res = pd.DataFrame(all_signals)
        finished = df_res[df_res['Résultat'] != "En cours"]
        
        if not finished.empty:
            wr = (finished['Résultat'] == "✅ GAGNÉ").sum() / len(finished) * 100
            st.metric("Taux de Réussite SMC", f"{wr:.1f}%")
        
        st.dataframe(df_res.sort_values(by="Date", ascending=False), use_container_width=True)
    else:
        st.warning("Aucun balayage de liquidité (Sweep) n'a été validé avec ces critères. Essayez une autre paire ou attendez une plus forte volatilité.")
