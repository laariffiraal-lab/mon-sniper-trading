import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from datetime import timedelta

st.set_page_config(page_title="Scalper Pro 80%", layout="wide")
st.title("⚡ Scalping Haute Fréquence : Retour à la Moyenne")

# Configuration
pairs = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "NZD/USD": "NZDUSD=X",
    "USD/CAD": "CAD=X"
}
selection = st.sidebar.selectbox("Actif :", list(pairs.keys()))

@st.cache_data(ttl=300)
def load_data(symbol):
    # On reste en H1 pour la fiabilité, mais la logique est de type scalping
    df = yf.download(symbol, period="1y", interval="1h")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.index = pd.to_datetime(df.index, utc=True)
    try:
        df.index = df.index.tz_convert('Europe/Paris')
    except:
        pass
    return df

data = load_data(pairs[selection])

def run_scalping_strategy(df):
    # --- INDICATEURS ---
    # 1. Bandes de Bollinger (20, 2) -> La mesure de l'excès
    bb = ta.bbands(df['Close'], length=20, std=2.0)
    df['BBL'] = bb.iloc[:, 0] # Bas
    df['BBM'] = bb.iloc[:, 1] # Milieu (Moyenne Mobile)
    df['BBU'] = bb.iloc[:, 2] # Haut
    
    # 2. RSI (Rapidité) -> Confirmation de l'épuisement
    df['RSI'] = ta.rsi(df['Close'], length=7) # RSI court pour être réactif

    signals = []
    # Backtest sur 6 mois
    start_date = df.index[-1] - timedelta(days=180)
    df_hist = df[df.index >= start_date].copy()
    
    for i in range(1, len(df_hist)):
        curr = df_hist.iloc[i]
        prev = df_hist.iloc[i-1]
        
        # --- LOGIQUE SCALPING (RETOUR A LA MOYENNE) ---
        
        # ACHAT : Le prix sort de la Bollinger Basse + RSI < 30 (Surchauffe Vendeuse)
        # TRIGGER : Le prix clôture à nouveau DANS les bandes (Réintégration)
        if prev['Close'] < prev['BBL'] and curr['Close'] > curr['BBL'] and prev['RSI'] < 30:
            
            entry = curr['Close']
            # OBJECTIF : Toucher la moyenne mobile (Le milieu) -> Taux de réussite énorme
            tp = curr['BBM'] 
            # STOP : Sous le plus bas récent
            sl = entry - (tp - entry) # Ratio 1:1 (nécessaire pour avoir 80% winrate)
            
            # Si le TP est trop proche (marché plat), on ignore
            if (tp - entry) < 0.0010: continue

            res = "En cours"
            # On laisse max 12h pour toucher la moyenne
            future = df_hist.iloc[i+1 : i+12]
            
            for _, f in future.iterrows():
                # Le TP est dynamique (la moyenne bouge), mais pour le backtest on fixe la cible initiale
                if f['High'] >= tp:
                    res = "✅ GAGNÉ"
                    break
                if f['Low'] <= sl:
                    res = "❌ PERDU"
                    break
            
            signals.append({
                "Date": curr.name.strftime('%d/%m %H:%M'),
                "Type": "SCALP LONG",
                "Prix": round(entry, 5),
                "TP (Moyenne)": round(tp, 5),
                "Résultat": res
            })

        # VENTE : Le prix sort de la Bollinger Haute + RSI > 70 (Surchauffe Acheteuse)
        elif prev['Close'] > prev['BBU'] and curr['Close'] < curr['BBU'] and prev['RSI'] > 70:
            
            entry = curr['Close']
            tp = curr['BBM'] # Retour au milieu
            sl = entry + (entry - tp)
            
            if (entry - tp) < 0.0010: continue

            res = "En cours"
            future = df_hist.iloc[i+1 : i+12]
            
            for _, f in future.iterrows():
                if f['Low'] <= tp:
                    res = "✅ GAGNÉ"
                    break
                if f['High'] >= sl:
                    res = "❌ PERDU"
                    break
            
            signals.append({
                "Date": curr.name.strftime('%d/%m %H:%M'),
                "Type": "SCALP SHORT",
                "Prix": round(entry, 5),
                "TP (Moyenne)": round(tp, 5),
                "Résultat": res
            })
            
    return pd.DataFrame(signals)

# --- LIVE SIGNAL ---
def get_live_scalp(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    # Indicateurs (déjà calculés dans load/run mais on réassure)
    bb = ta.bbands(df['Close'], length=20, std=2.0)
    last_bbl = bb.iloc[-1, 0]
    last_bbu = bb.iloc[-1, 2]
    last_bbm = bb.iloc[-1, 1]
    
    rsi = ta.rsi(df['Close'], length=7).iloc[-1]
    prev_rsi = ta.rsi(df['Close'], length=7).iloc[-2]
    
    info = {
        "Prix": round(last['Close'], 5),
        "RSI (7)": round(rsi, 1),
        "Moyenne (Cible)": round(last_bbm, 5),
        "Conseil": "⏳ PATIENCE",
        "ENTRY": None
    }
    
    # Logique Live
    # Setup Achat Potentiel
    if last['Close'] < last_bbl or (prev['Close'] < last_bbl and last['Close'] > last_bbl):
        if rsi < 35:
            info["Conseil"] = "⚠️ SURVEILLANCE ACHAT (Prix hors bandes)"
            if last['Close'] > last_bbl and prev['Close'] < last_bbl:
                info["Conseil"] = "🚀 SCALP ACHAT MAINTENANT"
                info["ENTRY"] = last['Close']
                info["TP"] = last_bbm
                info["SL"] = last['Close'] - (last_bbm - last['Close'])

    # Setup Vente Potentiel
    elif last['Close'] > last_bbu or (prev['Close'] > last_bbu and last['Close'] < last_bbu):
        if rsi > 65:
            info["Conseil"] = "⚠️ SURVEILLANCE VENTE (Prix hors bandes)"
            if last['Close'] < last_bbu and prev['Close'] > last_bbu:
                info["Conseil"] = "🔻 SCALP VENTE MAINTENANT"
                info["ENTRY"] = last['Close']
                info["TP"] = last_bbm
                info["SL"] = last['Close'] + (last['Close'] - last_bbm)
                
    return info

# --- AFFICHAGE ---
tab1, tab2 = st.tabs(["⚡ SIGNAL LIVE", "📊 BACKTEST 6 MOIS"])

with tab1:
    st.header(f"Scanner Scalping : {selection}")
    live = get_live_scalp(data)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Prix Actuel", live["Prix"])
    c2.metric("RSI (Court Terme)", live["RSI (7)"])
    c3.metric("Cible (Moyenne)", live["Moyenne (Cible)"])
    
    if live["ENTRY"]:
        st.success(f"SIGNAL : {live['Conseil']}")
        k1, k2, k3 = st.columns(3)
        k1.metric("ENTRÉE", round(live["ENTRY"], 5))
        k2.metric("STOP LOSS", round(live["SL"], 5))
        k3.metric("TAKE PROFIT", round(live["TP"], 5))
    else:
        st.info(live["Conseil"])
        st.caption("On attend que le prix sorte des bandes de Bollinger et revienne brutalement.")

with tab2:
    with st.spinner("Calcul des probabilités..."):
        df_res = run_scalping_strategy(data)
    
    if not df_res.empty:
        finished = df_res[df_res['Résultat'] != "En cours"]
        if not finished.empty:
            wins = (finished['Résultat'] == "✅ GAGNÉ").sum()
            total = len(finished)
            wr = (wins / total) * 100
            
            st.metric("TAUX DE RÉUSSITE (SCALPING)", f"{wr:.1f}%", delta=f"{total} Trades")
            
            st.dataframe(df_res.sort_values(by="Date", ascending=False), use_container_width=True)
        else:
            st.write("Pas assez de données finalisées.")
    else:
        st.warning("Marché trop calme, les bandes de Bollinger n'ont pas été brisées.")
