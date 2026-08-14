"""
Dashboard Streamlit — Cash Reconciliation Assurance
Visualise la performance du moteur de rapprochement automatique.

Lancer avec : streamlit run app.py
"""

import os
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

import generate_data
import matching

st.set_page_config(page_title="Cash Reconciliation - Assurance", page_icon="💰", layout="wide")


@st.cache_resource
def ensure_data_exists():
    """
    Sur Streamlit Cloud, seuls les fichiers .py versionnés sur GitHub sont garantis
    présents — les CSV générés ne le sont pas forcément (taille, .gitignore, oubli).
    On régénère donc les données + le matching au premier lancement si besoin.
    Mis en cache pour ne le faire qu'une fois par session serveur.
    """
    if not os.path.exists("releve_bancaire_matche.csv"):
        with st.spinner("Première initialisation : génération des données simulées..."):
            generate_data.main()
            matching.main()
    return True


@st.cache_data
def load_data():
    ensure_data_exists()
    virements = pd.read_csv("releve_bancaire_matche.csv", parse_dates=["date_virement"])
    contrats = pd.read_csv("contrats.csv", dtype={"police_id": str})
    return virements, contrats


virements, contrats = load_data()

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("💰 Simulateur de Cash Reconciliation — Assurance")
st.caption(
    "Rapprochement automatique de virements bancaires non-identifiés avec les polices "
    "d'assurance correspondantes (règles + fuzzy matching + machine learning)."
)

# ---------------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------------
total = len(virements)
n_matched = virements["police_id_match"].notna().sum()
n_exact = (virements["methode_match"] == "exact_reference").sum()
n_fuzzy = (virements["methode_match"] == "fuzzy_nom").sum()
n_non_matched = total - n_matched

montant_total = virements["montant_fcfa"].sum()
montant_non_alloue = virements.loc[virements["police_id_match"].isna(), "montant_fcfa"].sum()
taux_avant = 0.15  # référence marché simulée
taux_apres = montant_non_alloue / montant_total

col1, col2, col3, col4 = st.columns(4)
col1.metric("Virements traités", f"{total:,}")
col2.metric("Taux de matching auto", f"{n_matched/total*100:.1f}%", delta=f"+{(n_matched/total-0.40)*100:.0f} pts vs règle simple")
col3.metric("Fonds non alloués — avant", f"{taux_avant*100:.0f}%")
col4.metric("Fonds non alloués — après", f"{taux_apres*100:.1f}%", delta=f"-{(taux_avant-taux_apres)*100:.1f} pts", delta_color="inverse")

montant_liberé = montant_total * (taux_avant - taux_apres)
st.success(f"💡 **{montant_liberé:,.0f} FCFA** de trésorerie libérée du compte de suspens grâce au rapprochement automatique.")

st.divider()

# ---------------------------------------------------------------------------
# Répartition des méthodes de matching
# ---------------------------------------------------------------------------
c1, c2 = st.columns([1, 1])

with c1:
    st.subheader("Répartition par méthode de matching")
    repartition = pd.DataFrame({
        "Méthode": ["Référence exacte", "Fuzzy matching (nom)", "Non matché"],
        "Nombre": [n_exact, n_fuzzy, n_non_matched],
    })
    fig1 = px.pie(repartition, names="Méthode", values="Nombre", hole=0.5,
                  color_discrete_sequence=["#2E7D32", "#FBC02D", "#C62828"])
    fig1.update_traces(textinfo="percent+label")
    st.plotly_chart(fig1, use_container_width=True)

with c2:
    st.subheader("Fonds non alloués : avant / après")
    fig2 = go.Figure(go.Bar(
        x=["Avant algo", "Après algo"],
        y=[taux_avant * 100, taux_apres * 100],
        marker_color=["#C62828", "#2E7D32"],
        text=[f"{taux_avant*100:.0f}%", f"{taux_apres*100:.1f}%"],
        textposition="outside",
    ))
    fig2.update_layout(yaxis_title="% des fonds en compte de suspens", yaxis_range=[0, 18])
    st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# Distribution du score de confiance ML
# ---------------------------------------------------------------------------
st.subheader("Distribution du score de confiance (ML)")
scored = virements.dropna(subset=["confiance_ml"])
if not scored.empty:
    fig3 = px.histogram(scored, x="confiance_ml", nbins=30,
                         labels={"confiance_ml": "Score de confiance du match"},
                         color_discrete_sequence=["#1565C0"])
    st.plotly_chart(fig3, use_container_width=True)
else:
    st.info("Pas assez de données scorées pour afficher la distribution.")

st.divider()

# ---------------------------------------------------------------------------
# Table des virements non matchés (à traiter manuellement)
# ---------------------------------------------------------------------------
st.subheader(f"⚠️ Virements non matchés à traiter manuellement ({n_non_matched:,})")
non_matches = virements[virements["police_id_match"].isna()][
    ["virement_id", "date_virement", "montant_fcfa", "libelle_banque", "banque_emettrice"]
].sort_values("montant_fcfa", ascending=False)
st.dataframe(non_matches, use_container_width=True, height=300)

st.caption("Projet de démonstration — données 100% simulées à des fins pédagogiques.")
