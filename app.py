import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

st.set_page_config(page_title="SMC Pro 6 Mois", layout="wide")
st.title("🏦 Algorithme SMC : London Sweep + Tendance (6 Mois)")

# Sélection de l'actif (EUR ou GBP)
pairs = {"EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X"}
selection = st.sidebar.selectbox("Choisir l'actif :", list(pairs.keys()))

@st.cache_data(ttl=3600)
def load_data(symbol):
    # Pour avoir 6 mois, on est obligés d'utiliser l'intervalle 1h
    df = yf.download(symbol, period="6mo", interval="1h")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.index = pd.to_datetime(df.index, utc=True)
    return df

data = load_data(pairs[selection])

def apply_smc_trend_strategy(df):
    # --- 1. DÉFINITION DE LA TENDANCE ---
    # On utilise une EMA 50 pour filtrer les trades perdants
    df['EMA50'] = ta.ema(df['Close'], length=50)
    
    signals = []
    df['Date_Only'] = df.index.date
    unique_days = df['Date_Only'].unique()

    for day in unique_days:
        day_data = df[df['Date_Only'] == day]
        if len(day_data) < 15: continue # Pas assez de données

        # --- 2. RANGE D'ASIE (00:00 - 07:00 UTC) ---
        asia = day_data[(day_data.index.hour >= 0) & (day_data.index.hour < 7)]
        if asia.empty: continue
        
        asia_high = asia['High'].max()
        asia_low = asia['Low'].min()
        
        # --- 3. SESSION DE LONDRES (08:00 - 11:00 UTC) ---
        london = day_data[(day_data.index.hour >= 8) & (day_data.index.hour <= 11)]
        
        # On cherche un seul setup par jour
        trade_taken = False
        
        for idx, row in london.iterrows():
            if trade_taken: break
            
            # Condition de Tendance Haussière (Prix
