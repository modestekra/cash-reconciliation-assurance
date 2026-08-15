"""
Dashboard — Cash Reconciliation Assurance
Design : direction fintech/corporate sur mesure (pas de thème Streamlit par défaut).

Lancer avec : streamlit run app.py
"""

import os
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

import generate_data
import matching

st.set_page_config(page_title="Cash Reconciliation — Assurance", layout="wide")


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
@st.cache_resource
def ensure_data_exists():
    if not os.path.exists("releve_bancaire_matche.csv"):
        with st.spinner("Initialisation des données…"):
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
# Design tokens
# ---------------------------------------------------------------------------
BG = "#F5F6F8"
SURFACE = "#FFFFFF"
BORDER = "#E4E7EC"
INK = "#10182B"
INK_MUTED = "#5B6472"
ACCENT = "#0E6B5C"        # sarcelle — matché avec certitude (référence exacte)
ACCENT_SOFT = "#E3F2EE"
GOLD = "#B8863B"          # ocre — matché par déduction (fuzzy)
GOLD_SOFT = "#F7EFE1"
RISK = "#B3441E"          # rouille — non résolu / fonds bloqués
RISK_SOFT = "#FBEAE3"

FONT_STACK = "Inter, -apple-system, Segoe UI, sans-serif"
MONO_STACK = "'IBM Plex Mono', 'SFMono-Regular', Consolas, monospace"

# ---------------------------------------------------------------------------
# Icônes SVG (traits fins, style outline — pas d'emoji)
# ---------------------------------------------------------------------------
ICONS = {
    "layers": '<path d="M12 2 2 7l10 5 10-5-10-5Z"/><path d="m2 17 10 5 10-5"/><path d="m2 12 10 5 10-5"/>',
    "target": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
    "vault": '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="12" cy="12" r="4"/><path d="M12 10v4M10 12h4"/>',
    "alert": '<path d="M12 3 2 20h20L12 3Z"/><path d="M12 10v4"/><path d="M12 17h.01"/>',
}


def svg(name, size=18, color=INK):
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
        f'{ICONS[name]}</svg>'
    )


# ---------------------------------------------------------------------------
# CSS global
# ---------------------------------------------------------------------------
st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@500;600&display=swap');

    #MainMenu, footer, header {{visibility: hidden;}}
    .stApp {{ background: {BG}; }}
    .block-container {{ padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1180px; }}
    html, body, [class*="css"] {{ font-family: {FONT_STACK}; color: {INK}; }}

    .eyebrow {{
        font-family: {MONO_STACK}; font-size: 0.72rem; font-weight: 600;
        letter-spacing: 0.12em; text-transform: uppercase; color: {ACCENT};
        margin-bottom: 0.4rem;
    }}
    .page-title {{
        font-family: 'Space Grotesk', sans-serif; font-weight: 600;
        font-size: 2.05rem; line-height: 1.15; color: {INK}; margin: 0 0 0.5rem 0;
    }}
    .page-subtitle {{
        font-size: 0.98rem; color: {INK_MUTED}; max-width: 640px; line-height: 1.55;
    }}

    .kpi-card {{
        background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 10px;
        padding: 1.15rem 1.25rem; height: 100%;
    }}
    .kpi-icon-row {{ display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.9rem; }}
    .kpi-icon-box {{
        width: 30px; height: 30px; border-radius: 7px; background: {ACCENT_SOFT};
        display: flex; align-items: center; justify-content: center;
    }}
    .kpi-label {{ font-size: 0.78rem; color: {INK_MUTED}; font-weight: 500; }}
    .kpi-value {{
        font-family: {MONO_STACK}; font-size: 1.85rem; font-weight: 600; color: {INK};
        letter-spacing: -0.02em; line-height: 1;
    }}
    .kpi-delta {{ font-size: 0.78rem; font-weight: 600; margin-top: 0.5rem; }}
    .kpi-delta.up {{ color: {ACCENT}; }}
    .kpi-delta.down {{ color: {RISK}; }}

    /* Panneaux : on stylise directement le conteneur bordé natif de Streamlit
       (st.container(border=True)) plutôt que d'ouvrir/fermer un <div> dans deux
       st.markdown séparés — sinon Streamlit ne les imbrique pas et ça laisse
       des boîtes vides. */
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background: {SURFACE}; border: 1px solid {BORDER} !important; border-radius: 10px;
    }}
    div[data-testid="stVerticalBlockBorderWrapper"] > div {{ gap: 0 !important; }}
    div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stVerticalBlock"] {{
        padding: 1.4rem 1.5rem;
    }}
    div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stElementContainer"] {{
        margin-bottom: 0.15rem;
    }}
    .panel-title {{
        font-family: 'Space Grotesk', sans-serif; font-weight: 600; font-size: 1.02rem;
        color: {INK}; margin-bottom: 0.2rem;
    }}
    .panel-caption {{ font-size: 0.82rem; color: {INK_MUTED}; margin-bottom: 1.1rem; }}

    .callout {{
        border-left: 3px solid {ACCENT}; background: {ACCENT_SOFT};
        border-radius: 0 8px 8px 0; padding: 0.9rem 1.1rem; font-size: 0.92rem;
        color: {INK}; margin: 1.4rem 0 1.6rem 0;
    }}
    .callout b {{ font-family: {MONO_STACK}; }}

    .legend-row {{ display: flex; gap: 1.4rem; margin-top: 0.9rem; flex-wrap: wrap; }}
    .legend-item {{ display: flex; align-items: center; gap: 0.45rem; font-size: 0.8rem; color: {INK_MUTED}; }}
    .legend-dot {{ width: 8px; height: 8px; border-radius: 2px; }}

    table.custom {{ width: 100%; border-collapse: collapse; font-size: 0.84rem; }}
    table.custom th {{
        text-align: left; font-weight: 500; color: {INK_MUTED}; font-size: 0.74rem;
        text-transform: uppercase; letter-spacing: 0.04em; padding: 0.5rem 0.6rem;
        border-bottom: 1px solid {BORDER};
    }}
    table.custom td {{
        padding: 0.55rem 0.6rem; border-bottom: 1px solid {BORDER}; color: {INK};
    }}
    table.custom td.mono {{ font-family: {MONO_STACK}; font-size: 0.82rem; }}
    table.custom tr:last-child td {{ border-bottom: none; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Calculs
# ---------------------------------------------------------------------------
total = len(virements)
n_matched = virements["police_id_match"].notna().sum()
n_exact = (virements["methode_match"] == "exact_reference").sum()
n_fuzzy = (virements["methode_match"] == "fuzzy_nom").sum()
n_non_matched = total - n_matched

montant_total = virements["montant_fcfa"].sum()
montant_non_alloue = virements.loc[virements["police_id_match"].isna(), "montant_fcfa"].sum()
taux_avant = 0.15
taux_apres = montant_non_alloue / montant_total
montant_libere = montant_total * (taux_avant - taux_apres)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown('<div class="eyebrow">Simulation — Rapprochement bancaire</div>', unsafe_allow_html=True)
st.markdown('<div class="page-title">Cash Reconciliation, Assurance</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="page-subtitle">Rapprochement automatique de virements bancaires non identifiés '
    'avec les polices d\'assurance correspondantes, par règles métier, correspondance approximative '
    'de noms et scoring par apprentissage automatique.</div>',
    unsafe_allow_html=True,
)
st.write("")

# ---------------------------------------------------------------------------
# KPI cards
# ---------------------------------------------------------------------------
def kpi_card(icon, label, value, delta_text=None, delta_dir="up"):
    delta_html = (
        f'<div class="kpi-delta {delta_dir}">{delta_text}</div>' if delta_text else ""
    )
    return f"""
    <div class="kpi-card">
        <div class="kpi-icon-row">
            <div class="kpi-label">{label}</div>
            <div class="kpi-icon-box">{svg(icon, 15, ACCENT)}</div>
        </div>
        <div class="kpi-value">{value}</div>
        {delta_html}
    </div>
    """


c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(kpi_card("layers", "Virements traités", f"{total:,}".replace(",", " ")), unsafe_allow_html=True)
with c2:
    st.markdown(
        kpi_card("target", "Matching automatique", f"{n_matched/total*100:.1f}%",
                  "+52,7 pts vs règle simple", "up"),
        unsafe_allow_html=True,
    )
with c3:
    st.markdown(
        kpi_card("vault", "Fonds en suspens — avant", f"{taux_avant*100:.0f}%"),
        unsafe_allow_html=True,
    )
with c4:
    st.markdown(
        kpi_card("alert", "Fonds en suspens — après", f"{taux_apres*100:.1f}%",
                  f"-{(taux_avant-taux_apres)*100:.1f} pts", "up"),
        unsafe_allow_html=True,
    )

st.markdown(
    f'<div class="callout">Impact estimé : <b>{montant_libere:,.0f} FCFA</b>'.replace(",", " ")
    + " de trésorerie libérée du compte de suspens sur ce portefeuille simulé.</div>",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Chart config commun
# ---------------------------------------------------------------------------
def base_layout(height=260):
    return dict(
        height=height,
        margin=dict(l=0, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT_STACK, color=INK, size=12.5),
        showlegend=False,
    )


col_left, col_right = st.columns([1.05, 1])

# --- Composition avant / après (barre empilée horizontale) ---
with col_left:
    panel = st.container(border=True)
    panel.markdown('<div class="panel-title">Composition des fonds</div>', unsafe_allow_html=True)
    panel.markdown('<div class="panel-caption">Part allouée vs en compte de suspens</div>', unsafe_allow_html=True)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=["Après algorithme", "Avant (règle simple)"],
        x=[1 - taux_apres, 1 - taux_avant],
        orientation="h", marker_color=ACCENT, name="Alloué",
        text=[f"{(1-taux_apres)*100:.1f}%", f"{(1-taux_avant)*100:.0f}%"],
        textposition="inside", textfont=dict(color="white", size=13),
        hoverinfo="skip",
    ))
    fig.add_trace(go.Bar(
        y=["Après algorithme", "Avant (règle simple)"],
        x=[taux_apres, taux_avant],
        orientation="h", marker_color=RISK, name="Suspens",
        text=[f"{taux_apres*100:.1f}%", f"{taux_avant*100:.0f}%"],
        textposition="inside", textfont=dict(color="white", size=13),
        hoverinfo="skip",
    ))
    fig.update_layout(**base_layout(190), barmode="stack",
                       xaxis=dict(visible=False, range=[0, 1]),
                       yaxis=dict(tickfont=dict(size=12.5)))
    panel.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    panel.markdown(
        f"""<div class="legend-row">
        <div class="legend-item"><div class="legend-dot" style="background:{ACCENT}"></div>Fonds alloués</div>
        <div class="legend-item"><div class="legend-dot" style="background:{RISK}"></div>Compte de suspens</div>
        </div>""",
        unsafe_allow_html=True,
    )

# --- Répartition par méthode ---
with col_right:
    panel2 = st.container(border=True)
    panel2.markdown('<div class="panel-title">Méthode de résolution</div>', unsafe_allow_html=True)
    panel2.markdown('<div class="panel-caption">Comment chaque virement a été rapproché</div>', unsafe_allow_html=True)

    methodes = ["Référence exacte", "Correspondance de nom", "Non résolu"]
    valeurs = [n_exact, n_fuzzy, n_non_matched]
    couleurs = [ACCENT, GOLD, RISK]

    fig2 = go.Figure(go.Bar(
        x=valeurs, y=methodes, orientation="h", marker_color=couleurs,
        text=[f"{v:,}".replace(",", " ") + f"  ·  {v/total*100:.1f}%" for v in valeurs],
        textposition="outside", textfont=dict(size=12.5, family=MONO_STACK),
        cliponaxis=False,
        hoverinfo="skip",
    ))
    layout2 = base_layout(190)
    layout2["margin"] = dict(l=0, r=70, t=10, b=10)
    fig2.update_layout(
        **layout2,
        xaxis=dict(visible=False, range=[0, max(valeurs) * 1.28]),
        yaxis=dict(tickfont=dict(size=12.5)),
    )
    panel2.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

# ---------------------------------------------------------------------------
# Distribution du score de confiance
# ---------------------------------------------------------------------------
panel3 = st.container(border=True)
panel3.markdown('<div class="panel-title">Score de confiance du modèle</div>', unsafe_allow_html=True)
panel3.markdown(
    '<div class="panel-caption">Distribution des scores attribués par le modèle aux correspondances trouvées — '
    'plus le score est proche de 1, plus la correspondance est fiable</div>',
    unsafe_allow_html=True,
)

scored = virements.dropna(subset=["confiance_ml"])
if not scored.empty:
    fig3 = go.Figure(go.Histogram(
        x=scored["confiance_ml"], nbinsx=32, marker_color=ACCENT, marker_line_width=0,
        hoverinfo="skip",
    ))
    fig3.update_layout(
        **base_layout(200),
        xaxis=dict(title=None, gridcolor=BORDER, tickfont=dict(size=11.5), range=[0, 1]),
        yaxis=dict(title=None, gridcolor=BORDER, tickfont=dict(size=11.5)),
    )
    panel3.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})
else:
    panel3.caption("Pas assez de données scorées pour afficher la distribution.")

# ---------------------------------------------------------------------------
# Table — virements non résolus
# ---------------------------------------------------------------------------
panel4 = st.container(border=True)
panel4.markdown(f'<div class="panel-title">File de traitement manuel</div>', unsafe_allow_html=True)
panel4.markdown(
    f'<div class="panel-caption">{n_non_matched:,} virements sans correspondance automatique, triés par montant</div>'.replace(",", " "),
    unsafe_allow_html=True,
)

non_matches = (
    virements[virements["police_id_match"].isna()]
    [["virement_id", "date_virement", "montant_fcfa", "libelle_banque", "banque_emettrice"]]
    .sort_values("montant_fcfa", ascending=False)
    .head(12)
)

rows_html = "".join(
    f"""<tr>
        <td class="mono">{r.virement_id}</td>
        <td class="mono">{r.date_virement.strftime('%d/%m/%Y')}</td>
        <td class="mono">{r.montant_fcfa:,.0f}</td>
        <td>{r.libelle_banque}</td>
        <td>{r.banque_emettrice}</td>
    </tr>"""
    for r in non_matches.itertuples()
).replace(",", " ")

panel4.markdown(
    f"""
    <table class="custom">
        <thead><tr>
            <th>ID</th><th>Date</th><th>Montant (FCFA)</th><th>Libellé bancaire</th><th>Banque</th>
        </tr></thead>
        <tbody>{rows_html}</tbody>
    </table>
    """,
    unsafe_allow_html=True,
)
if n_non_matched > 12:
    panel4.caption(f"{n_non_matched - 12:,} lignes supplémentaires dans le fichier complet.".replace(",", " "))

st.caption("Projet de démonstration — données entièrement simulées, à usage pédagogique.")
