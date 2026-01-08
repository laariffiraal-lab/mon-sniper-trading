import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import pytz
from datetime import datetime, timedelta

st.set_page_config(page_title="SMC Sniper Pro", layout="wide")
st.title("🏦 SMC Sniper : Historique & Signal Direct")

# --- 1. CONFIGURATION ---
pairs = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "JPY=X"
}
selection = st.sidebar.selectbox("Choisir l'actif :", list(pairs.keys()))

@st.cache_data(ttl=300) # Mise à jour toutes les 5 min
def load_data(symbol):
    # On télécharge 1 an (1y) pour être sûr d'avoir 6 mois de backtest propre
    # interval="1h" est le plus fiable pour l'historique gratuit
    df = yf.download(symbol, period="1y", interval="1h")
    
    # Nettoyage des MultiIndex si nécessaire
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # Gestion des Timezones (UTC vers Europe/Paris pour la lisibilité)
    df.index = pd.to_datetime(df.index, utc=True)
    try:
        df.index = df.index.tz_convert('Europe/Paris')
    except:
        pass
        
    return df

data = load_data(pairs[selection])

# --- 2. CALCUL DES INDICATEURS ---
def add_indicators(df):
    # EMA 50 pour la tendance de fond
    df['EMA50'] = ta.ema(df['Close'], length=50)
    return df

data = add_indicators(data)

# --- 3. ANALYSE HISTORIQUE (BACKTEST) ---
def get_backtest_signals(df):
    signals = []
    # On regarde les 6 derniers mois
    start_date = df.index[-1] - timedelta(days=180)
    df_history = df[df.index >= start_date].copy()
    
    # Groupement par jour pour identifier le Range Asie
    df_history['Date_Only'] = df_history.index.date
    unique_days = df_history['Date_Only'].unique()

    for day in unique_days:
        day_data = df_history[df_history['Date_Only'] == day]
        if len(day_data) < 10: continue

        # Range Asie (00h - 08h Paris)
        asia = day_data[(day_data.index.hour >= 0) & (day_data.index.hour < 8)]
        if asia.empty: continue
        
        asia_high = asia['High'].max()
        asia_low = asia['Low'].min()

        # Session Londres (08h - 12h Paris)
        london = day_data[(day_data.index.hour >= 8) & (day_data.index.hour <= 12)]
        
        taken = False
        for idx, row in london.iterrows():
            if taken: break
            
            # --- STRATÉGIE SMC ---
            # CAS 1 : Tendance HAUSSIÈRE (Prix > EMA50) -> On veut ACHETER après un balayage du BAS
            if row['Close'] > row['EMA50']:
                if row['Low'] < asia_low and row['Close'] > asia_low: # Sweep + Clôture interne
                    sl = row['Low'] - 0.0005
                    tp = asia_high
                    res = "En cours"
                    
                    # Vérification du résultat dans le futur
                    future = df_history[df
