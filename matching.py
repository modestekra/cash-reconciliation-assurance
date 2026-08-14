"""
Moteur de rapprochement (cash reconciliation) — 3 niveaux successifs :

Niveau 1 — Match exact  : référence de police trouvée dans le libellé (regex)
Niveau 2 — Match fuzzy  : nom du souscripteur retrouvé dans le libellé (RapidFuzz)
                          + montant proche (± tolérance) + date proche (± jours)
Niveau 3 — Match ML     : score de confiance (RandomForest) sur les candidats
                          ambigus, basé sur des features numériques (écart montant,
                          écart date, score de similarité nom, etc.)

Sortie : releve_bancaire_matche.csv avec le police_id proposé + méthode + confiance.
"""

import re
import pandas as pd
import numpy as np
from rapidfuzz import fuzz
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

TOLERANCE_JOURS = 5
TOLERANCE_MONTANT_PCT = 0.02  # 2%


def load_data():
    contrats = pd.read_csv("contrats.csv", parse_dates=["date_echeance"], dtype={"police_id": str})
    virements = pd.read_csv("releve_bancaire.csv", parse_dates=["date_virement"])
    return contrats, virements


# ---------------------------------------------------------------------------
# Niveau 1 : match exact par référence de police dans le libellé
# ---------------------------------------------------------------------------
def match_exact_reference(virements, contrats):
    polices_valides = set(contrats["police_id"].astype(str))
    ref_pattern = re.compile(r"\d{6}")

    def find_ref(libelle):
        for candidat in ref_pattern.findall(libelle):
            if candidat in polices_valides:
                return candidat
        return None

    virements["police_id_match"] = virements["libelle_banque"].apply(find_ref)
    virements["methode_match"] = np.where(
        virements["police_id_match"].notna(), "exact_reference", None
    )
    return virements


# ---------------------------------------------------------------------------
# Niveau 2 : match fuzzy nom + montant + date, pour les virements restants
# ---------------------------------------------------------------------------
def match_fuzzy(virements, contrats):
    non_matches = virements[virements["police_id_match"].isna()].copy()
    if non_matches.empty:
        return virements

    contrats_idx = contrats.set_index("police_id")

    for i, row in non_matches.iterrows():
        libelle = row["libelle_banque"]
        montant = row["montant_fcfa"]
        date_v = row["date_virement"]

        # Fenêtre de candidats : montant proche + date proche (réduit le coût du fuzzy matching)
        mask_montant = (contrats["prime_annuelle_fcfa"] - montant).abs() <= (
            montant * TOLERANCE_MONTANT_PCT + 15_000
        )
        mask_date = (contrats["date_echeance"] - date_v).abs() <= pd.Timedelta(days=TOLERANCE_JOURS)
        candidats = contrats[mask_montant & mask_date]

        if candidats.empty:
            continue

        # Score de similarité nom vs libellé (token_set_ratio tolère l'ordre et les mots en trop)
        best_score, best_police = -1, None
        for _, c in candidats.iterrows():
            score = fuzz.token_set_ratio(c["nom_souscripteur"].upper(), libelle.upper())
            if score > best_score:
                best_score, best_police = score, c["police_id"]

        if best_score >= 60:  # seuil de confiance fuzzy
            virements.at[i, "police_id_match"] = best_police
            virements.at[i, "methode_match"] = "fuzzy_nom"
            virements.at[i, "score_fuzzy"] = best_score

    return virements


# ---------------------------------------------------------------------------
# Niveau 3 : ML — score de confiance pour arbitrer les cas ambigus restants
# (entraîné sur les matches niveau 1+2 déjà validés, features génériques)
# ---------------------------------------------------------------------------
def build_features(virements, contrats):
    # police_id sur 6 chiffres aléatoires -> collisions possibles (paradoxe des anniversaires).
    # On dédoublonne en gardant la première occurrence pour un lookup fiable.
    contrats_idx = contrats.drop_duplicates(subset="police_id", keep="first").set_index("police_id")
    feats = []
    for _, row in virements.iterrows():
        if pd.isna(row["police_id_match"]) or str(row["police_id_match"]) not in contrats_idx.index:
            feats.append([np.nan, np.nan, np.nan])
            continue
        c = contrats_idx.loc[str(row["police_id_match"])]
        ecart_montant = abs(row["montant_fcfa"] - c["prime_annuelle_fcfa"]) / c["prime_annuelle_fcfa"]
        ecart_jours = abs((row["date_virement"] - c["date_echeance"]).days)
        score_nom = fuzz.token_set_ratio(str(c["nom_souscripteur"]).upper(), str(row["libelle_banque"]).upper())
        feats.append([ecart_montant, ecart_jours, score_nom])
    return pd.DataFrame(feats, columns=["ecart_montant_pct", "ecart_jours", "score_nom"])


def score_confiance_ml(virements, contrats):
    features = build_features(virements, contrats)
    virements = pd.concat([virements.reset_index(drop=True), features], axis=1)

    matched = virements.dropna(subset=["ecart_montant_pct"]).copy()
    if len(matched) < 50:
        virements["confiance_ml"] = np.nan
        return virements

    # Label proxy : un match "fort" = déjà validé exact_reference (vérité quasi-certaine)
    matched["label"] = (matched["methode_match"] == "exact_reference").astype(int)

    X = matched[["ecart_montant_pct", "ecart_jours", "score_nom"]].fillna(999)
    y = matched["label"]

    if y.nunique() < 2:
        virements["confiance_ml"] = np.nan
        return virements

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    clf = RandomForestClassifier(n_estimators=150, max_depth=6, random_state=42)
    clf.fit(X_train, y_train)

    proba_all = clf.predict_proba(X.fillna(999))[:, 1]
    matched["confiance_ml"] = proba_all

    virements = virements.merge(
        matched[["virement_id", "confiance_ml"]], on="virement_id", how="left"
    )
    return virements, clf.score(X_test, y_test)


def main():
    contrats, virements = load_data()
    virements["police_id_match"] = pd.array([None] * len(virements), dtype="object")
    virements["methode_match"] = None
    virements["score_fuzzy"] = np.nan

    virements = match_exact_reference(virements, contrats)
    n_exact = (virements["methode_match"] == "exact_reference").sum()

    virements = match_fuzzy(virements, contrats)
    n_fuzzy = (virements["methode_match"] == "fuzzy_nom").sum()

    virements, ml_accuracy = score_confiance_ml(virements, contrats)

    total = len(virements)
    n_matched = virements["police_id_match"].notna().sum()
    n_non_matched = total - n_matched

    print("=" * 55)
    print("RÉSULTATS DU RAPPROCHEMENT")
    print("=" * 55)
    print(f"Total virements                 : {total:,}")
    print(f"  └─ Match exact (référence)     : {n_exact:,} ({n_exact/total*100:.1f}%)")
    print(f"  └─ Match fuzzy (nom+montant+date): {n_fuzzy:,} ({n_fuzzy/total*100:.1f}%)")
    print(f"  └─ TOTAL matché automatiquement : {n_matched:,} ({n_matched/total*100:.1f}%)")
    print(f"  └─ Non matché (à traiter manuel) : {n_non_matched:,} ({n_non_matched/total*100:.1f}%)")
    print(f"\nPrécision du scoring ML (validation) : {ml_accuracy*100:.1f}%")

    virements.to_csv("releve_bancaire_matche.csv", index=False)

    # Comparaison au montant retenu en "compte de suspens" (non alloué)
    montant_total = virements["montant_fcfa"].sum()
    montant_non_alloue = virements.loc[virements["police_id_match"].isna(), "montant_fcfa"].sum()
    print(f"\nMontant total viré        : {montant_total:,.0f} FCFA")
    print(f"Montant non alloué (avant): 15% (référence marché estimée)")
    print(f"Montant non alloué (après): {montant_non_alloue/montant_total*100:.1f}%")

    print("\n✅ Fichier détaillé exporté : releve_bancaire_matche.csv")


if __name__ == "__main__":
    main()
