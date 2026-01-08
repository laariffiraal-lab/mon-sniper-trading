import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from datetime import datetime, timedelta
import numpy as np

st.set_page_config(page_title="SMC Fibonacci Sniper", layout="wide")
st.title("🥇 SMC + Fibonacci : La Golden Zone (OTE)")

# --- 1. SÉLECTION MULTI-ASSETS ---
pairs = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "JPY=X",
    "NZD/USD": "NZDUSD=X",
    "AUD/USD": "AUDUSD=X",
    "XAU/USD (Or)": "GC=F"
}
selection = st.sidebar.selectbox("Actif Institutionnel :", list(pairs.keys()))

@st.cache_data(ttl=300)
def load_data(symbol):
    # On charge 1 an pour avoir une structure solide sur 6 mois
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

# --- 2. FONCTION INTELLIGENTE DE DÉTECTION FIBONACCI ---
def apply_fibonacci_smc(df):
    signals = []
    
    # Indicateur de Tendance de fond (EMA 200) - On ne trade que dans le sens du flux
    df['EMA200'] = ta.ema(df['Close'], length=200)
    
    # On utilise le Donchian Channel pour trouver les Hauts/Bas majeurs sur 48 bougies (2 jours)
    df['Swing_High'] = df['High'].rolling(window=48).max()
    df['Swing_Low'] = df['Low'].rolling(window=48).min()
    
    # On analyse les 6 derniers mois
    start_date = df.index[-1] - timedelta(days=180)
    df_hist = df[df.index >= start_date].copy()
    
    # Pour éviter les signaux multiples sur la même vague
    last_trade_index = None 

    for i in range(50, len(df_hist)):
        if last_trade_index and i - last_trade_index < 10: continue # Pause après un trade
        
        curr = df_hist.iloc[i]
        
        # --- LOGIQUE HAUSSIÈRE (ACHAT DANS LA GOLDEN ZONE) ---
        # 1. Tendance Haussière (Prix > EMA200)
        if curr['Close'] > curr['EMA200']:
            # 2. Calcul du range Fibonacci actuel (Du Bas vers le Haut récent)
            range_high = curr['Swing_High']
            range_low = curr['Swing_Low']
            range_size = range_high - range_low
            
            if range_size == 0: continue

            # Niveaux Fibonacci (Retracement)
            fib_50 = range_high - (0.5 * range_size)
            fib_618 = range_high - (0.618 * range_size) # Début Golden Zone
            fib_786 = range_high - (0.786 * range_size) # Fin Golden Zone
            
            # 3. TRIGGER : Le prix est-il entré dans la Golden Zone (entre 61.8% et 78.6%) ?
            # Et est-il en train de rebondir (Close > Low) ?
            in_golden_zone = curr['Low'] <= fib_618 and curr['Low'] >= fib_786
            
            if in_golden_zone:
                # Entrée précise
                entry = curr['Close']
                # Stop Loss : Sous le point bas du mouvement (Invalidation de la structure)
                sl = range_low - 0.0005 
                # Take Profit : Le point haut précédent (Liquidité externe) ou extension -0.27
                tp = range_high
                
                # Ratio minimum 1:2 pour valider
                if (tp - entry) > 2 * (entry - sl):
                    res = "En cours"
                    # Simulation futur
                    future = df_hist.iloc[i+1 : i+48] # 48h max
                    for _, f in future.iterrows():
                        if f['High'] >= tp:
                            res = "✅ GAGNÉ"
                            break
                        if f['Low'] <= sl:
                            res = "❌ PERDU"
                            break
                    
                    signals.append({
                        "Date": curr.name.strftime('%d/%m %H:%M'),
                        "Type": "BUY OTE (61.8%)",
                        "Prix": round(entry, 5),
                        "Zone Fib": f"{round(fib_618, 5)} - {round(fib_786, 5)}",
                        "Résultat": res
                    })
                    last_trade_index = i

        # --- LOGIQUE BAISSIÈRE (VENTE DANS LA GOLDEN ZONE) ---
        elif curr['Close'] < curr['EMA200']:
            range_high = curr['Swing_High']
            range_low = curr['Swing_Low']
            range_size = range_high - range_low
            
            if range_size == 0: continue

            # Pour la vente, on mesure du Haut vers le Bas
            # Retracement vers le haut
            fib_50 = range_low + (0.5 * range_size)
            fib_618 = range_low + (0.618 * range_size)
            fib_786 = range_low + (0.786 * range_size)
            
            in_golden_zone = curr['High'] >= fib_618 and curr['High'] <= fib_786
            
            if in_golden_zone:
                entry = curr['Close']
                sl = range_high + 0.0005 # Stop au-dessus du sommet
                tp = range_low # On vise le bas
                
                if (entry - tp) > 2 * (sl - entry):
                    res = "En cours"
                    future = df_hist.iloc[i+1 : i+48]
                    for _, f in future.iterrows():
                        if f['Low'] <= tp:
                            res = "✅ GAGNÉ"
                            break
                        if f['High'] >= sl:
                            res = "❌ PERDU"
                            break
                    
                    signals.append({
                        "Date": curr.name.strftime('%d/%m %H:%M'),
                        "Type": "SELL OTE (61.8%)",
                        "Prix": round(entry, 5),
                        "Zone Fib": f"{round(fib_618, 5)} - {round(fib_786, 5)}",
                        "Résultat": res
                    })
                    last_trade_index = i

    return pd.DataFrame(signals)

# --- 3. SCANNER TEMPS RÉEL (LIVE) ---
def get_live_fib_setup(df):
    last = df.iloc[-1]
    
    # Calcul dynamique des swings
    # On regarde les 48 dernières heures pour définir la structure majeure
    recent_high = df['High'].tail(48).max()
    recent_low = df['Low'].tail(48).min()
    diff = recent_high - recent_low
    
    if diff == 0: return None
    
    ema200 = ta.ema(df['Close'], length=200).iloc[-1]
    trend = "HAUSSIÈRE 🟢" if last['Close'] > ema200 else "BAISSIÈRE 🔴"
    
    info = {
        "Prix Actuel": round(last['Close'], 5),
        "Tendance EMA200": trend,
        "Swing High (Haut)": round(recent_high, 5),
        "Swing Low (Bas)": round(recent_low, 5),
        "Conseil": "ATTENTE",
        "ENTRY": None
    }
    
    # Analyse Live
    if "🟢" in trend:
        # On attend un repli vers 61.8% du mouvement
        buy_zone_top = recent_high - (0.618 * diff)
        buy_zone_bottom = recent_high - (0.786 * diff)
        
        info["Zone Achat Idéale"] = f"{round(buy_zone_top, 5)} - {round(buy_zone_bottom, 5)}"
        
        if last['Low'] <= buy_zone_top and last['Low'] >= buy_zone_bottom:
            info["Conseil"] = "🎯 PRIX DANS LA GOLDEN ZONE (ACHAT)"
            info["ENTRY"] = last['Close']
            info["SL"] = recent_low - 0.0005
            info["TP"] = recent_high
        elif last['Close'] > buy_zone_top:
            info["Conseil"] = "⏳ Trop cher. Attendre repli vers Golden Zone."
        elif last['Close'] < buy_zone_bottom:
            info["Conseil"] = "⚠️ Tendance menacée (Sous les 78.6%)."
            
    else: # Baissière
        sell_zone_bottom = recent_low + (0.618 * diff)
        sell_zone_top = recent_low + (0.786 * diff)
        
        info["Zone Vente Idéale"] = f"{round(sell_zone_bottom, 5)} - {round(sell_zone_top, 5)}"
        
        if last['High'] >= sell_zone_bottom and last['High'] <= sell_zone_top:
            info["Conseil"] = "🎯 PRIX DANS LA GOLDEN ZONE (VENTE)"
            info["ENTRY"] = last['Close']
            info["SL"] = recent_high + 0.0005
            info["TP"] = recent_low
        elif last['Close'] < sell_zone_bottom:
            info["Conseil"] = "⏳ Trop bas. Attendre remontée vers Golden Zone."

    return info

# --- AFFICHAGE ---
tab1, tab2 = st.tabs(["⚡ SCANNER LIVE (OTE)", "📜 BACKTEST 6 MOIS"])

with tab1:
    st.header(f"Radar Fibonacci : {selection}")
    st.markdown("La stratégie **OTE (Optimal Trade Entry)** attend que le prix retrace entre **61.8% et 78.6%** avant d'entrer.")
    
    live_data = get_live_fib_setup(data)
    
    if live_data:
        c1, c2 = st.columns(2)
        c1.metric("Prix Actuel", live_data["Prix Actuel"])
        c2.metric("Tendance", live_data["Tendance EMA200"])
        
        if live_data["ENTRY"]:
            st.success(f"🔥 SIGNAL DÉTECTÉ : {live_data['Conseil']}")
            k1, k2, k3 = st.columns(3)
            k1.metric("ENTRÉE", round(live_data["ENTRY"], 5))
            k2.metric("STOP LOSS", round(live_data["SL"], 5))
            k3.metric("TAKE PROFIT", round(live_data["TP"], 5))
        else:
            st.info(f"{live_data['Conseil']}")
            if "Zone Achat Idéale" in live_data:
                st.write(f"**Surveillez cette zone pour acheter :** {live_data['Zone Achat Idéale']}")
            if "Zone Vente Idéale" in live_data:
                st.write(f"**Surveillez cette zone pour vendre :** {live_data['Zone Vente Idéale']}")

with tab2:
    with st.spinner("Calcul des retracements Fibonacci sur 6 mois..."):
        df_res = apply_fibonacci_smc(data)
    
    if not df_res.empty:
        finished = df_res[df_res['Résultat'] != "En cours"]
        if not finished.empty:
            wins = (finished['Résultat'] == "✅ GAGNÉ").sum()
            total = len(finished)
            wr = (wins / total) * 100
            
            st.metric("Taux de Réussite (OTE Strategy)", f"{wr:.1f}%")
            st.dataframe(df_res.sort_values(by="Date", ascending=False), use_container_width=True)
            
            if wr > 70:
                st.success("✅ La combinaison Liquidité + Fib > 70% est validée !")
        else:
            st.warning("Trades en cours...")
    else:
        st.warning("Aucun setup parfait (Golden Zone) détecté récemment. Soyez patient, c'est une stratégie de sniper.")
