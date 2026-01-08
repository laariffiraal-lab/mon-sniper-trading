import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="SMC London Sniper", layout="wide")
st.title("🏦 Stratégie Institutionnelle : London Judas Swing")

@st.cache_data(ttl=3600)
def load_eurusd_data():
    # On utilise le 15 minutes (M15) car c'est l'unité de temps des banques pour l'exécution
    df = yf.download("EURUSD=X", period="60d", interval="15m")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

data = load_eurusd_data()

def apply_judas_strategy(df):
    df['Date'] = df.index.date
    unique_days = df['Date'].unique()
    signals = []

    for day in unique_days:
        day_data = df[df['Date'] == day]
        if len(day_data) < 40: continue

        # 1. RANGE D'ASIE (00:00 - 07:00 UTC)
        asia_session = day_data[(day_data.index.hour >= 0) & (day_data.index.hour < 7)]
        if asia_session.empty: continue
        asia_high = asia_session['High'].max()
        asia_low = asia_session['Low'].min()

        # 2. FENÊTRE DE MANIPULATION (08:00 - 10:00)
        london_open = day_data[(day_data.index.hour >= 8) & (day_data.index.hour <= 10)]
        
        executed_today = False
        for idx, row in london_open.iterrows():
            if executed_today: break

            # --- LE SETUP DE RÉUSSITE ---
            # A. Prise de Liquidité (Le prix dépasse le haut d'Asie)
            if row['High'] > asia_high and row['Close'] < asia_high:
                # B. Entrée Sell : On parie sur le retour vers le bas d'Asie
                sl = row['High'] + 0.0005 # Stop au-dessus de la mèche
                tp = asia_low             # Objectif : Bas d'Asie
                
                # Vérification du résultat
                future = day_data[day_data.index > idx]
                for _, f_row in future.iterrows():
                    if f_row['Low'] <= tp:
                        signals.append({"Date": idx, "Type": "SELL (Judas)", "Résultat": "✅ GAGNÉ"})
                        executed_today = True
                        break
                    if f_row['High'] >= sl:
                        signals.append({"Date": idx, "Type": "SELL (Judas)", "Résultat": "❌ STOP"})
                        executed_today = True
                        break
            
            # Cas inverse (Achat)
            elif row['Low'] < asia_low and row['Close'] > asia_low:
                sl = row['Low'] - 0.0005
                tp = asia_high
                
                future = day_data[day_data.index > idx]
                for _, f_row in future.iterrows():
                    if f_row['High'] >= tp:
                        signals.append({"Date": idx, "Type": "BUY (Judas)", "Résultat": "✅ GAGNÉ"})
                        executed_today = True
                        break
                    if f_row['Low'] <= sl:
                        signals.append({"Date": idx, "Type": "BUY (Judas)", "Résultat": "❌ STOP"})
                        executed_today = True
                        break

    return signals

# --- RÉSULTATS ---
trades = apply_judas_strategy(data)
if trades:
    df_res = pd.DataFrame(trades)
    wr = (df_res[df_res['Résultat'] == "✅ GAGNÉ"].shape[0] / len(df_res)) * 100
    st.metric("Taux de Réussite Réel (SMC)", f"{wr:.1f}%")
    st.table(df_res.sort_values(by="Date", ascending=False))
