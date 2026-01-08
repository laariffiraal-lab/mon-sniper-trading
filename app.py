import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from datetime import datetime, timedelta
import pytz

st.set_page_config(page_title="SMC Sniper Pro", layout="wide")
st.title("🏦 SMC Sniper : Historique & Signal Direct")

# --- 1. CONFIGURATION ET CHARGEMENT ---
pairs = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "JPY=X"
}
selection = st.sidebar.selectbox("Choisir l'actif :", list(pairs.keys()))

@st.cache_data(ttl=300) # Mise à jour auto toutes les 5 min
def load_data(symbol):
    # On prend 1 an pour garantir d'avoir les 6 derniers mois propres
    df = yf.download(symbol, period="1y", interval="1h")
    
    # Nettoyage des colonnes (MultiIndex)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # Gestion des fuseaux horaires (UTC -> Paris pour la cohérence)
    df.index = pd.to_datetime(df.index, utc=True)
    try:
        df.index = df.index.tz_convert('Europe/Paris')
    except:
        pass
        
    return df

data = load_data(pairs[selection])

# --- 2. INDICATEURS TECHNIQUES ---
def add_indicators(df):
    # EMA 50 : Notre juge de paix pour la tendance
    df['EMA50'] = ta.ema(df['Close'], length=50)
    return df

data = add_indicators(data)

# --- 3. BACKTEST (HISTORIQUE 6 MOIS) ---
def get_backtest_signals(df):
    signals = []
    # On recule de 180 jours depuis la dernière date disponible
    start_date = df.index[-1] - timedelta(days=180)
    # On filtre les données
    df_history = df[df.index >= start_date].copy()
    
    df_history['Date_Only'] = df_history.index.date
    unique_days = df_history['Date_Only'].unique()

    for day in unique_days:
        day_data = df_history[df_history['Date_Only'] == day]
        if len(day_data) < 10: continue

        # Définition du Range Asie (00h - 08h)
        asia = day_data[(day_data.index.hour >= 0) & (day_data.index.hour < 8)]
        if asia.empty: continue
        
        asia_high = asia['High'].max()
        asia_low = asia['Low'].min()

        # Session de Londres (08h - 12h) : La zone de chasse
        london = day_data[(day_data.index.hour >= 8) & (day_data.index.hour <= 12)]
        
        taken = False
        for idx, row in london.iterrows():
            if taken: break
            
            # SCÉNARIO ACHAT (LONG) : Tendance Haussière + Manipulation du Bas
            if row['Close'] > row['EMA50']:
                # Le prix casse le bas d'Asie puis clôture au-dessus
                if row['Low'] < asia_low and row['Close'] > asia_low:
                    sl = row['Low'] - 0.0005
                    tp = asia_high
                    res = "En cours"
                    
                    # Vérification du résultat
                    future = df_history[df_history.index > idx]
                    for _, f in future.iterrows():
                        if f['High'] >= tp:
                            res = "✅ GAGNÉ"
                            break
                        if f['Low'] <= sl:
                            res = "❌ PERDU"
                            break
                    
                    signals.append({
                        "Date": idx.strftime('%d/%m %H:%M'),
                        "Type": "LONG (Achat)",
                        "Entrée": round(row['Close'], 5),
                        "SL": round(sl, 5),
                        "TP": round(tp, 5),
                        "Résultat": res
                    })
                    taken = True

            # SCÉNARIO VENTE (SHORT) : Tendance Baissière + Manipulation du Haut
            elif row['Close'] < row['EMA50']:
                # Le prix casse le haut d'Asie puis clôture en dessous
                if row['High'] > asia_high and row['Close'] < asia_high:
                    sl = row['High'] + 0.0005
                    tp = asia_low
                    res = "En cours"
                    
                    future = df_history[df_history.index > idx]
                    for _, f in future.iterrows():
                        if f['Low'] <= tp:
                            res = "✅ GAGNÉ"
                            break
                        if f['High'] >= sl:
                            res = "❌ PERDU"
                            break
                    
                    signals.append({
                        "Date": idx.strftime('%d/%m %H:%M'),
                        "Type": "SHORT (Vente)",
                        "Entrée": round(row['Close'], 5),
                        "SL": round(sl, 5),
                        "TP": round(tp, 5),
                        "Résultat": res
                    })
                    taken = True
                    
    return pd.DataFrame(signals)

# --- 4. SIGNAL EN DIRECT (LIVE) ---
def get_current_setup(df):
    last_row = df.iloc[-1]
    
    # Récupérer les données d'aujourd'hui
    current_day = last_row.name.date()
    day_data = df[df.index.date == current_day]
    
    # Calculer le range Asie d'aujourd'hui
    asia = day_data[(day_data.index.hour >= 0) & (day_data.index.hour < 8)]
    
    if asia.empty:
        return None, "En attente de la fin de la session Asie (08h00)..."
        
    asia_high = asia['High'].max()
    asia_low = asia['Low'].min()
    
    # Déterminer la tendance actuelle
    is_bullish = last_row['Close'] > last_row['EMA50']
    trend_str = "HAUSSIÈRE 🟢 (Chercher Achat)" if is_bullish else "BAISSIÈRE 🔴 (Chercher Vente)"
    
    setup_info = {
        "Prix Actuel": round(last_row['Close'], 5),
        "Tendance EMA50": trend_str,
        "Haut Asie": round(asia_high, 5),
        "Bas Asie": round(asia_low, 5),
        "Conseil": "ATTENTE ⏳",
        "ENTRY": None, "SL": None, "TP": None
    }

    # LOGIQUE DE DÉCISION LIVE
    if is_bullish:
        # On attend que le prix passe SOUS le bas d'Asie puis remonte
        if last_row['Low'] < asia_low and last_row['Close'] > asia_low:
            setup_info["Conseil"] = "🚀 ACHAT (LONG) VALIDÉ MAINTENANT"
            setup_info["ENTRY"] = round(last_row['Close'], 5)
            setup_info["SL"] = round(last_row['Low'] - 0.0005, 5)
            setup_info["TP"] = round(asia_high, 5)
        elif last_row['Close'] < asia_low:
            setup_info["Conseil"] = "⚠️ ATTENTION : Le prix coule sous le Range Asie. Attendre la remontée (Clôture > Bas Asie)."
        else:
            setup_info["Conseil"] = f"⏳ SCÉNARIO : Attendre que le prix descende sous {round(asia_low, 5)} puis remonte."

    else: # Tendance Baissière
        # On attend que le prix passe AU-DESSUS du haut d'Asie puis redescende
        if last_row['High'] > asia_high and last_row['Close'] < asia_high:
            setup_info["Conseil"] = "🔻 VENTE (SHORT) VALIDÉ MAINTENANT"
            setup_info["ENTRY"] = round(last_row['Close'], 5)
            setup_info["SL"] = round(last_row['High'] + 0.0005, 5)
            setup_info["TP"] = round(asia_low, 5)
        elif last_row['Close'] > asia_high:
            setup_info["Conseil"] = "⚠️ ATTENTION : Le prix explose au-dessus du Range. Attendre la réintégration."
        else:
            setup_info["Conseil"] = f"⏳ SCÉNARIO : Attendre que le prix monte au-dessus de {round(asia_high, 5)} puis redescende."

    return setup_info, None

# --- 5. AFFICHAGE STREAMLIT ---
tab1, tab2 = st.tabs(["⚡ SIGNAL DIRECT", "📜 Historique (6 Mois)"])

with tab1:
    st.subheader(f"Analyse Temps Réel : {selection}")
    setup, error = get_current_setup(data)
    
    if error:
        st.warning(error)
    elif setup:
        # Affichage principal
        c1, c2, c3 = st.columns(3)
        c1.metric("Prix Actuel", setup["Prix Actuel"])
        c2.metric("Tendance", setup["Tendance EMA50"])
        c3.metric("Action", setup["Conseil"])
        
        st.divider()
        
        # Si un signal est actif, on affiche les détails en gros
        if setup["ENTRY"]:
            st.success(f"🎯 SIGNAL ACTIF : {setup['Conseil']}")
            col1, col2, col3 = st.columns(3)
            col1.metric("PRIX D'ENTRÉE", setup["ENTRY"])
            col2.metric("STOP LOSS", setup["SL"], delta="- Risque")
            col3.metric("TAKE PROFIT", setup["TP"], delta="+ Cible")
        else:
            st.info("Aucun signal de manipulation validé pour le moment. Surveillez les niveaux Asie.")
            st.write(f"**Niveau à surveiller (Haut)** : {setup['Haut Asie']}")
            st.write(f"**Niveau à surveiller (Bas)** : {setup['Bas Asie']}")

with tab2:
    st.subheader("Backtest : Stratégie SMC Trend + Sweep")
    with st.spinner("Calcul de l'historique sur 6 mois..."):
        df_history = get_backtest_signals(data)
    
    if not df_history.empty:
        finished = df_history[df_history['Résultat'] != "En cours"]
        if not finished.empty:
            wins = (finished['Résultat'] == "✅ GAGNÉ").sum()
            total = len(finished)
            wr = (wins / total) * 100
            
            k1, k2, k3 = st.columns(3)
            k1.metric("Taux de Réussite", f"{wr:.1f}%")
            k2.metric("Total Trades", total)
            k3.metric("Trades Gagnants", wins)
        
        st.dataframe(df_history.sort_values(by="Date", ascending=False), use_container_width=True)
    else:
        st.warning("Aucun trade SMC trouvé sur les 6 derniers mois. Le marché n'a pas offert de configurations propres.")
