import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from datetime import datetime, timedelta
import pytz

st.set_page_config(page_title="SMC Elite Multi-Asset", layout="wide")
st.title("🌐 Sniper SMC Elite : Multi-Devises & ATR Dynamique")

# --- 1. CONFIGURATION MULTI-PAIRES ---
# Les tickers Yahoo Finance peuvent varier, voici les standards
pairs = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/CAD": "CAD=X",     # Attention: Yahoo note souvent USD/CAD comme CAD=X (inverse) ou CADUSD=X
    "NZD/USD": "NZDUSD=X",
    "AUD/USD": "AUDUSD=X",
    "USD/JPY": "JPY=X"
}

# Note pour l'utilisateur sur USD/CAD
st.sidebar.info("ℹ️ Note : Les paires XXX/USD suivent la logique standard. Pour USD/CAD (CAD=X), la logique est inversée sur Yahoo.")

selection = st.sidebar.selectbox("Choisir l'actif à sniper :", list(pairs.keys()))

@st.cache_data(ttl=300)
def load_data(symbol):
    # Intervalle 1h pour la fiabilité du signal
    df = yf.download(symbol, period="1y", interval="1h")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # Gestion Timezone
    df.index = pd.to_datetime(df.index, utc=True)
    try:
        df.index = df.index.tz_convert('Europe/Paris')
    except:
        pass
    return df

ticker = pairs[selection]
data = load_data(ticker)

# --- 2. INDICATEURS AVANCÉS ---
def add_elite_indicators(df):
    # Tendance de fond
    df['EMA50'] = ta.ema(df['Close'], length=50)
    
    # ATR pour le Stop Loss dynamique (s'adapte à la volatilité de NZD vs GBP)
    df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
    
    # RSI pour éviter d'acheter un marché déjà épuisé
    df['RSI'] = ta.rsi(df['Close'], length=14)
    return df

data = add_elite_indicators(data)

# --- 3. MOTEUR DE BACKTEST (6 MOIS) ---
def get_elite_signals(df, pair_name):
    signals = []
    start_date = df.index[-1] - timedelta(days=180)
    df_hist = df[df.index >= start_date].copy()
    
    df_hist['Date_Only'] = df_hist.index.date
    unique_days = df_hist['Date_Only'].unique()

    for day in unique_days:
        day_data = df_hist[df_hist['Date_Only'] == day]
        if len(day_data) < 10: continue

        # Range Asie (00h-08h)
        asia = day_data[(day_data.index.hour >= 0) & (day_data.index.hour < 8)]
        if asia.empty: continue
        asia_hi, asia_lo = asia['High'].max(), asia['Low'].min()

        # Killzone (08h-16h) : On couvre Londres ET l'ouverture New York (pour USD/CAD)
        killzone = day_data[(day_data.index.hour >= 8) & (day_data.index.hour <= 16)]
        
        taken = False
        for idx, row in killzone.iterrows():
            if taken: break
            
            # FILTRE 1 : Tendance (EMA 50)
            # FILTRE 2 : Force de la bougie (Le corps doit être significatif)
            body_size = abs(row['Close'] - row['Open'])
            min_body = row['ATR'] * 0.3 # Le corps doit faire au moins 30% de l'ATR (pas de Doji)

            # SCÉNARIO ACHAT (LONG)
            if row['Close'] > row['EMA50']:
                # Sweep du BAS + Clôture interne + RSI pas suracheté (<70)
                if row['Low'] < asia_lo and row['Close'] > asia_lo and row['RSI'] < 70 and body_size > min_body:
                    
                    # Stop Loss adapté à la volatilité (ATR)
                    sl = row['Low'] - (row['ATR'] * 0.5) 
                    # Take Profit : On vise le haut Asie ou Ratio 1:2 min
                    risk = row['Close'] - sl
                    tp = row['Close'] + (risk * 2.5) # On vise un gros ratio pour absorber les pertes
                    
                    # Vérif
                    res = "En cours"
                    future = df_hist[df_hist.index > idx]
                    for _, f in future.iterrows():
                        if f['High'] >= tp:
                            res = "✅ GAGNÉ"
                            break
                        if f['Low'] <= sl:
                            res = "❌ PERDU"
                            break
                    
                    signals.append({
                        "Date": idx.strftime('%d/%m %H:%M'),
                        "Type": "LONG 🟢",
                        "Prix": round(row['Close'], 5),
                        "Résultat": res
                    })
                    taken = True

            # SCÉNARIO VENTE (SHORT)
            elif row['Close'] < row['EMA50']:
                # Sweep du HAUT + Clôture interne + RSI pas survendu (>30)
                if row['High'] > asia_hi and row['Close'] < asia_hi and row['RSI'] > 30 and body_size > min_body:
                    
                    sl = row['High'] + (row['ATR'] * 0.5)
                    risk = sl - row['Close']
                    tp = row['Close'] - (risk * 2.5)
                    
                    res = "En cours"
                    future = df_hist[df_hist.index > idx]
                    for _, f in future.iterrows():
                        if f['Low'] <= tp:
                            res = "✅ GAGNÉ"
                            break
                        if f['High'] >= sl:
                            res = "❌ PERDU"
                            break
                    
                    signals.append({
                        "Date": idx.strftime('%d/%m %H:%M'),
                        "Type": "SHORT 🔴",
                        "Prix": round(row['Close'], 5),
                        "Résultat": res
                    })
                    taken = True
                    
    return pd.DataFrame(signals)

# --- 4. SIGNAL LIVE AVEC ATR ---
def get_live_setup(df):
    last = df.iloc[-1]
    day_data = df[df.index.date == last.name.date()]
    asia = day_data[(day_data.index.hour >= 0) & (day_data.index.hour < 8)]
    
    if asia.empty: return None, "Attente Range Asie..."
    
    asia_hi, asia_lo = asia['High'].max(), asia['Low'].min()
    trend = "HAUSSIÈRE 🟢" if last['Close'] > last['EMA50'] else "BAISSIÈRE 🔴"
    
    # Calcul ATR pour affichage
    atr_val = last['ATR']
    
    info = {
        "Prix": round(last['Close'], 5),
        "Tendance": trend,
        "Asie High": round(asia_hi, 5),
        "Asie Low": round(asia_lo, 5),
        "Conseil": "⏳ OBSERVATION",
        "ENTRY": None, "SL": None, "TP": None
    }
    
    # Logique Live
    if "🟢" in trend:
        if last['Low'] < asia_lo and last['Close'] > asia_lo:
             info["Conseil"] = "🚀 ACHAT (LONG) CONFIRMÉ"
             info["ENTRY"] = last['Close']
             info["SL"] = last['Low'] - (atr_val * 0.5)
             info["TP"] = last['Close'] + ((last['Close'] - info["SL"]) * 2.5)
        elif last['Close'] < asia_lo:
             info["Conseil"] = "⚠️ Prix sous le range. Attendre la remontée."
    else:
        if last['High'] > asia_hi and last['Close'] < asia_hi:
             info["Conseil"] = "🔻 VENTE (SHORT) CONFIRMÉ"
             info["ENTRY"] = last['Close']
             info["SL"] = last['High'] + (atr_val * 0.5)
             info["TP"] = last['Close'] - ((info["SL"] - last['Close']) * 2.5)
        elif last['Close'] > asia_hi:
             info["Conseil"] = "⚠️ Prix au-dessus du range. Attendre la chute."
             
    return info, None

# --- 5. AFFICHAGE ---
tab1, tab2 = st.tabs(["⚡ SIGNAL DIRECT", "📊 BACKTEST ELITE"])

with tab1:
    st.header(f"Radar : {selection}")
    live, err = get_live_setup(data)
    if err:
        st.warning(err)
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Prix", live["Prix"])
        c2.metric("Tendance", live["Tendance"])
        c3.metric("Action", live["Conseil"])
        
        if live["ENTRY"]:
            st.success(f"SETUP VALIDÉ ! Ratio 1:2.5")
            k1, k2, k3 = st.columns(3)
            k1.metric("ENTRÉE", round(live["ENTRY"], 5))
            k2.metric("STOP LOSS", round(live["SL"], 5))
            k3.metric("TAKE PROFIT", round(live["TP"], 5))
        else:
            st.info("En attente de manipulation des banques...")
            st.write(f"Surveiller cassure de : **{live['Asie High']}** (Haut) ou **{live['Asie Low']}** (Bas)")

with tab2:
    st.subheader(f"Performance 6 Mois : {selection}")
    with st.spinner("Analyse algorithmique en cours..."):
        df_res = get_elite_signals(data, selection)
    
    if not df_res.empty:
        finished = df_res[df_res['Résultat'] != "En cours"]
        if not finished.empty:
            win_count = (finished['Résultat'] == "✅ GAGNÉ").sum()
            total = len(finished)
            wr = (win_count / total) * 100
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Taux de Réussite", f"{wr:.1f}%")
            m2.metric("Total Signaux", total)
            m3.metric("Gagnants", win_count)
            
            st.dataframe(df_res.sort_values(by="Date", ascending=False), use_container_width=True)
            
            if wr > 70:
                st.balloons()
                st.success("🔥 STRATÉGIE VALIDÉE (>70%) SUR CETTE PAIRE !")
        else:
            st.write("Trades en cours, pas de résultat fini.")
    else:
        st.warning("Aucun signal détecté. Essayez une autre paire ou attendez plus de volatilité.")
