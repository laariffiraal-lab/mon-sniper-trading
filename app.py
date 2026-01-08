import streamlit as st
import yfinance as yf
import pandas_ta as ta

# Configuration de l'affichage sur mobile
st.set_page_config(page_title="Sniper SMC Pro", layout="centered")

st.title("🎯 Mon Sniper SMC & Fibonacci")
st.write("Analyse Institutionnelle en Temps Réel")

# 1. Sélection de la paire (Tu peux en ajouter d'autres ici)
symbole = st.sidebar.selectbox("Choisir une paire :", ["EURUSD=X", "GBPUSD=X", "BTC-USD", "ETH-USD"])

# 2. Récupération des données sur Internet (Intervalle 15 minutes)
data = yf.download(symbole, period="5d", interval="15m")

if not data.empty:
    # --- CALCULS TECHNIQUES ---
    # EMA 200 pour la tendance globale
    # Calcul Ichimoku
ichimoku = data.ta.ichimoku()[0]
# Utilisation de noms de colonnes plus simples pour éviter l'erreur
span_a = ichimoku.iloc[:, 0] # Senkou Span A
span_b = ichimoku.iloc[:, 1] # Senkou Span B
    # Fibonacci OTE (Optimal Trade Entry) sur les 30 dernières bougies
    haut_recent = data['High'].rolling(window=30).max().iloc[-1]
    bas_recent = data['Low'].rolling(window=30).min().iloc[-1]
    diff = haut_recent - bas_recent
    zone_ote_haute = haut_recent - (0.705 * diff)
    zone_ote_basse = haut_recent - (0.79 * diff)

    prix_actuel = data['Close'].iloc[-1]

    # --- INTERFACE VISUELLE ---
    st.metric("PRIX ACTUEL", f"{prix_actuel:.5f}")

    # Vérification des conditions de la stratégie
    tendance_hausse = prix_actuel > data['EMA200'].iloc[-1]
    dans_zone_fibo = zone_ote_basse <= prix_actuel <= zone_ote_haute
    au_dessus_nuage = prix_actuel > ss_a.iloc[-1]

    st.divider()

    # --- DÉCISION DE L'ALGORITHME ---
    if tendance_hausse and au_dessus_nuage and dans_zone_fibo:
        st.success("🔥 SIGNAL D'ACHAT (BUY) : Zone Fibonacci OTE détectée !")
        st.write(f"🚩 **Stop Loss :** {bas_recent:.5f}")
        st.write(f"🎯 **Objectif (TP) :** {prix_actuel + (prix_actuel - bas_recent) * 2:.5f}")
    # --- AFFICHAGE DES RÉSULTATS ---
st.header(f"Analyse pour {ticker}")

if buy_signal:
    st.success("🚀 SIGNAL D'ACHAT : Le prix est dans la zone de rechargement Fibonacci !")
elif sell_signal:
    st.warning("📉 SIGNAL DE VENTE : Le prix est dans la zone d'extension Fibonacci !")
else:
    st.info("⌛ ANALYSE : Le marché n'est pas encore dans une zone de haute probabilité.")

st.line_chart(data['Close'].tail(50))
st.write(f"Dernière mise à jour : {data.index[-1]}")
