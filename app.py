import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from datetime import datetime, timedelta
import pytz

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
    # On télécharge 1 an pour assurer 6 mois d'historique propre
    df = yf.download(symbol, period="1y", interval="1h")
    
    # Nettoyage des MultiIndex
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # Standardisation de l'index en UTC
    df.index = pd.to_datetime(df.index, utc=True)
    
    # Conversion en heure de Paris pour faciliter la lecture (GMT+1/GMT+2)
    try:
        df.index = df.index.tz_convert('Europe/Paris')
    except:
        pass # Si déjà converti
        
    return df

data = load_data(pairs[selection])

# --- 2. INDICATEURS ---
def add_indicators(df):
    # EMA 50 pour la tendance de fond
    df['EMA50'] = ta.ema(df['Close'], length=50)
    return df

data = add_indicators(data)

# --- 3. BACKTEST (HISTORIQUE 6 MOIS) ---
def get_backtest_signals(df):
    signals = []
    # On isole les 6 derniers mois
    start_date = df.index[-1] - timedelta(days=180)
    df_history = df[df.index >= start_date].copy()
    
    # Création d'une colonne date pour grouper par jour
    df_history['Date_Only'] = df_history.index.date
    unique_days = df_history['Date_Only'].unique()

    for day in unique_days:
        day_data = df_history[df_history['Date_Only'] == day]
        if len(day_data) < 10: continue

        # Range Asie (00h - 08h Paris)
        asia = day_data[(day_data.index.hour >= 0) & (day_data.index.
