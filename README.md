# 💰 Simulateur de Cash Reconciliation — Assurance

> J'ai simulé 12 000 virements non-identifiés d'une compagnie d'assurance et créé un algo qui en rapproche automatiquement **92,7%**. Voici comment.

---

## Business Problem

Dans le secteur de l'assurance en Afrique (zone CIMA notamment), une part significative des primes reçues — souvent **10 à 15%** — atterrit en **"compte de suspens"** : de l'argent bien reçu par la banque, mais qu'on ne sait pas rattacher à une police précise, faute de référence claire dans le virement.

Conséquences concrètes :
- **Trésorerie immobilisée** — l'argent est là mais inutilisable tant qu'il n'est pas alloué.
- **Risque réglementaire** — les régulateurs (CIMA) surveillent ce ratio de près.
- **Client mal servi** — un assuré dont le paiement n'est pas rapproché peut être relancé ou considéré en défaut à tort.

Le problème vient souvent d'un simple libellé bancaire mal renseigné : `"VIREMENT ABJ KOUASI"` au lieu du nom exact du client, sans numéro de police, parfois payé par un tiers (l'employeur, un proche).

## La simulation

Trois jeux de données générés avec du bruit réaliste :

| Fichier | Contenu | Bruit injecté |
|---|---|---|
| `clients.csv` | 10 000 clients (nom, IBAN, contact) | — |
| `contrats.csv` | 10 000 polices (n° police, prime, échéance, produit) | — |
| `releve_bancaire.csv` | 12 000 virements bancaires | 20% sans référence visible, 5% montant erroné, 3% payés par un tiers, libellés déformés |

## Approche technique

Le rapprochement se fait en 3 niveaux successifs, du plus fiable au plus incertain :

1. **Règle exacte** — extraction du numéro de police dans le libellé (regex). Rapide, fiable, mais limité par la qualité des libellés.
2. **Fuzzy matching** — quand pas de référence : comparaison du nom du souscripteur avec le libellé (`RapidFuzz`, `token_set_ratio`), filtré par une fenêtre montant ± tolérance et date ± 5 jours.
3. **Scoring ML** — un `RandomForestClassifier` (scikit-learn) attribue un score de confiance à chaque match, basé sur l'écart de montant, l'écart de date et le score de similarité du nom. Sert à prioriser les cas à vérifier manuellement.

### Stack

- **Python + Pandas** — génération des données, manipulation, règles de matching
- **RapidFuzz** — similarité de chaînes pour le matching de noms
- **scikit-learn** — RandomForest pour le score de confiance
- **Streamlit + Plotly** — dashboard interactif de visualisation des résultats

## Résultats

| Indicateur | Avant (règle simple) | Après (règles + fuzzy + ML) |
|---|---|---|
| Taux de matching automatique | ~40% | **92,7%** |
| Fonds en compte de suspens | 15% | **7,4%** |
| Précision du scoring ML (validation) | — | 87,4% |

Sur un portefeuille simulé de ~23,4 milliards FCFA de primes, cela représente environ **1,8 milliard FCFA** de trésorerie libérée du compte de suspens.

## Comment lancer le projet

```bash
pip install -r requirements.txt

# 1. Générer les données simulées
python generate_data.py

# 2. Lancer le moteur de rapprochement
python matching.py

# 3. Lancer le dashboard
streamlit run app.py
```

## Structure du repo

```
├── generate_data.py                    # génération des 3 datasets simulés
├── matching.py                         # moteur de rapprochement (règles + fuzzy + ML)
├── app.py                              # dashboard Streamlit
├── requirements.txt
├── clients.csv                         # généré
├── contrats.csv                        # généré
├── releve_bancaire.csv                 # généré (input du moteur)
├── releve_bancaire_matche.csv          # généré (output du moteur)
└── README.md
```

## Limites & prochaines étapes

- Données 100% simulées — à valider sur un vrai échantillon anonymisé avant tout déploiement.
- Le seuil de confiance fuzzy (60) et le seuil ML mériteraient un tuning plus poussé avec de vraies données étiquetées.
- Prochaine itération possible : détection de fraude aux sinistres (NetworkX) ou prédiction de résiliation (churn).

---

*Projet pédagogique de démonstration — aucune donnée réelle utilisée.*
