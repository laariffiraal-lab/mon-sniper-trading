import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from datetime import datetime, timedelta

st.set_page_config(page_title="Sniper Pro Ultimate 80%", layout="wide")
st.title("🎯 Sniper Pro : Stratégie Institutionnelle & Backtest")

# 1. LISTE DES PAIRES
pairs_dict = {
    "EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/JPY": "USDJPY=X",
    "USD/CHF": "USDCHF=X", "AUD/JPY": "AUDJPY=X", "USD/CAD": "USDCAD=X",
    "NZD/USD": "NZDUSD=X", "GOLD": "GC=F", "BTC/USD": "BTC-USD"
}

selection = st.sidebar.selectbox("Choisir l'actif :", list(pairs_dict.keys()))
ticker = pairs_dict[selection]
tab1, tab2 = st.tabs(["🚀 Signal en Direct", "📜 Historique (6 mois)"])

# --- CHARGEMENT DES DONNÉES ---
@st.cache_data(ttl=3600)
def load_data(symbol):
    # On prend 200 jours pour avoir un historique de 6 mois propre
    df = yf.download(symbol, period="200d", interval="1h")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

data = load_data(ticker)

# --- CALCUL DES INDICATEURS ---
def add_indicators(df):
    df['EMA200'] = ta.ema(df['Close'], length=200)
    df['ADX'] = ta.adx(df['High'], df['Low'], df['Close'])['ADX_14']
    df['RSI'] = ta.rsi(df['Close'], length=14)
    df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
    return df

data = add_indicators(data)

# --- MOTEUR DE DÉTECTION DES SIGNAUX ---
def get_signals(df):
    signals = []
    # On commence après l'EMA 200
    for i in range(200, len(df)):
        # Fenêtre Fibonacci (50 dernières bougies)
        window = df.iloc[i-50:i]
        hi = window['High'].max()
        lo = window['Low'].min()
        
        # Zone de rechargement (61.8% - 78.6%)
        fib_786 = lo + (0.786 * (hi - lo))
        fib_618 = lo + (0.618 * (hi - lo))
        
        curr = df.iloc[i]
        prev = df.iloc[i-1]
        
        # CONDITIONS STRATÉGIQUES
        c1 = curr['Close'] > curr['EMA200']             # Tendance Haussière
        c2 = curr['Low'] <= fib_618 and curr['Close'] >= lo  # Prix dans la zone basse
        c3 = curr['ADX'] > 20                            # Début de force
        c4 = curr['RSI'] < 60                            # Pas encore sur-acheté
        
        if c1 and c2 and c3 and c4:
            # Simulation : On regarde les 72h suivantes
            future = df.iloc[i+1 : i+72]
            if future.empty: continue
            
            tp = hi 
            sl = lo - (curr['ATR'] * 1.5)
            
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
                "Prix Entrée": round(curr['Close'], 4),
                "Résultat": outcome,
                "TP Prévu": round(tp, 4),
                "SL Prévu": round(sl, 4)
            })
    
    # Nettoyage pour éviter les signaux trop proches (1 par 24h max)
    clean = []
    if signals:
        clean.append(signals[0])
        for s in signals[1:]:
            last_date = datetime.strptime(clean[-1]['Date'], '%d/%m/%Y %H:%M')
            curr_date = datetime.strptime(s['Date'], '%d/%m/%Y %H:%M')
            if curr_date > last_date + timedelta(hours=24):
                clean.append(s)
    return clean

# --- ONGLET 1 : SIGNAL EN DIRECT ---
with tab1:
    curr = data.iloc[-1]
    st.header(f"Analyse en temps réel : {selection}")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Prix Actuel", f"{curr['Close']:.4f}")
    col2.metric("Force (ADX)", f"{curr['ADX']:.1f}")
    col3.metric("RSI", f"{curr['RSI']:.1f}")

    # Vérification si un signal est actif maintenant
    hi_now = data['High'].tail(50).max()
    lo_now = data['Low'].tail(50).min()
    fib_618_now = lo_now + (0.618 * (hi_now - lo_now))

    if curr['Close'] > curr['EMA200'] and curr['Low'] <= fib_618_now and curr['ADX'] > 20:
        st.balloons()
        st.success("💎 SIGNAL DIAMANT ACTIF : Entrée en zone de rechargement détectée !")
    else:
        st.info("⌛ Le marché est hors zone ou la force est insuffisante. Patience.")

    st.line_chart(data[['Close', 'EMA200']].tail(150))

# --- ONGLET 2 : BACKTEST ---
with tab2:
    st.subheader(f"Historique des performances (6 derniers mois)")
    results = get_signals(data)
    
    if results:
        df_res = pd.DataFrame(results)
        # Calcul du taux de réussite (en ignorant les trades "En cours")
        finished_trades = df_res[df_res['Résultat'] != "En cours"]
        if not finished_trades.empty:
            wins = (finished_trades['Résultat'] == "✅ GAGNÉ").sum()
            wr = (wins / len(finished_trades)) * 100
            st.metric("Taux de Réussite Réel", f"{wr:.1f}%")
        
        st.dataframe(df_res.sort_values(by="Date", ascending=False), use_container_width=True)
    else:
        st.warning("Aucun signal trouvé avec ces critères. Le marché a été trop instable ou les conditions sont trop strictes.")
