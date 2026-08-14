"""
Génération de datasets simulés pour le projet Cash Reconciliation Assurance.

Simule 3 fichiers :
- clients.csv       : 10 000 clients (nom, IBAN, contact)
- contrats.csv      : 10 000 contrats/polices (n° police, prime annuelle, échéance)
- releve_bancaire.csv : 12 000 virements bancaires bruités (dates, montants, libellés)

Bruit injecté (réaliste secteur assurance Afrique / CIMA) :
- 20% des virements sans référence de police dans le libellé
- 5% avec un montant légèrement différent de la prime attendue (frais, arrondi, double paiement partiel)
- 3% payés par un tiers (le nom sur le virement ≠ nom du client)
- Libellés bancaires "sales" : abréviations, fautes, casse aléatoire, bruit ville/agence
"""

import pandas as pd
import numpy as np
import random
import string
from datetime import datetime, timedelta
from faker import Faker

fake = Faker("fr_FR")
Faker.seed(42)
random.seed(42)
np.random.seed(42)

N_CLIENTS = 10_000
N_VIREMENTS = 12_000

VILLES = ["ABJ", "ABIDJAN", "BOUAKE", "YAMOUSSOUKRO", "SAN PEDRO", "DALOA", "KORHOGO"]
AGENCES = ["SGCI", "NSIA", "ECOBANK", "BICICI", "UBA", "BOA", "SIB"]


def deform_name(name: str) -> str:
    """Introduit des fautes/variations réalistes dans un nom (façon libellé bancaire)."""
    name = name.upper()
    ops = random.choice(["ok", "swap_letter", "drop_vowel", "double_letter", "truncate"])
    chars = list(name)
    if ops == "swap_letter" and len(chars) > 3:
        i = random.randint(1, len(chars) - 2)
        chars[i], chars[i + 1] = chars[i + 1], chars[i]
    elif ops == "drop_vowel":
        for i, c in enumerate(chars):
            if c in "AEIOU" and random.random() < 0.3:
                chars[i] = ""
    elif ops == "double_letter" and len(chars) > 2:
        i = random.randint(0, len(chars) - 1)
        chars[i] = chars[i] * 2
    elif ops == "truncate":
        chars = chars[: max(3, len(chars) - random.randint(1, 3))]
    return "".join(chars)


def make_libelle(client_name: str, has_ref: bool, police_ref: str, is_tiers: bool, tiers_name: str) -> str:
    ville = random.choice(VILLES)
    agence = random.choice(AGENCES)
    display_name = tiers_name if is_tiers else client_name

    # Nom déformé une fois sur deux (bruit bancaire typique)
    if random.random() < 0.5:
        display_name = deform_name(display_name)
    else:
        display_name = display_name.upper()

    templates_with_ref = [
        f"VIR {ville} {display_name} POL{police_ref}",
        f"VIREMENT {agence} {display_name} REF{police_ref}",
        f"{display_name} PRIME {police_ref}",
        f"VRT {display_name} /POLICE {police_ref}",
    ]
    templates_no_ref = [
        f"VIREMENT {ville} {display_name}",
        f"VRT {agence} {display_name}",
        f"PAIEMENT {display_name}",
        f"VIR {display_name} {ville}",
        "VIREMENT RECU",
        f"VRT {agence}",
    ]

    if has_ref:
        return random.choice(templates_with_ref)
    else:
        return random.choice(templates_no_ref)


def main():
    # ---------- 1. clients.csv ----------
    clients = []
    for i in range(N_CLIENTS):
        client_id = f"CLI{i:06d}"
        nom = fake.name()
        clients.append({
            "client_id": client_id,
            "nom_complet": nom,
            "iban": fake.iban(),
            "telephone": fake.phone_number(),
            "email": fake.email(),
            "ville": random.choice(VILLES),
        })
    df_clients = pd.DataFrame(clients)

    # ---------- 2. contrats.csv ----------
    contrats = []
    for i in range(N_CLIENTS):
        client = df_clients.iloc[i]
        police_ref = f"{random.randint(100000, 999999)}"
        prime = round(random.choice([
            random.uniform(50_000, 300_000),      # auto / habitation
            random.uniform(300_000, 1_500_000),   # santé / vie
            random.uniform(1_500_000, 8_000_000), # entreprise
        ]), -3)
        echeance = fake.date_between(start_date="-60d", end_date="+30d")
        contrats.append({
            "police_id": police_ref,
            "client_id": client["client_id"],
            "nom_souscripteur": client["nom_complet"],
            "prime_annuelle_fcfa": prime,
            "date_echeance": echeance,
            "type_produit": random.choice(["Auto", "Habitation", "Santé", "Vie", "Entreprise"]),
        })
    df_contrats = pd.DataFrame(contrats)

    # ---------- 3. releve_bancaire.csv ----------
    virements = []
    # on tire N_VIREMENTS contrats (avec remise pour simuler doubles paiements / tiers payeurs)
    sample_idx = np.random.choice(df_contrats.index, size=N_VIREMENTS, replace=True)

    for vi, idx in enumerate(sample_idx):
        contrat = df_contrats.iloc[idx]
        client_nom = contrat["nom_souscripteur"]
        police_ref = contrat["police_id"]
        montant_attendu = contrat["prime_annuelle_fcfa"]

        has_ref = random.random() > 0.20          # 20% sans référence
        montant_correct = random.random() > 0.05  # 5% montant erroné
        is_tiers = random.random() < 0.03         # 3% payé par un tiers

        montant = montant_attendu
        if not montant_correct:
            delta = random.choice([-1, 1]) * random.uniform(500, 15_000)
            montant = round(montant_attendu + delta, -2)

        tiers_name = fake.name() if is_tiers else client_nom

        date_echeance = pd.to_datetime(contrat["date_echeance"])
        offset_days = random.randint(-5, 5)  # paiement autour de l'échéance, ±3-5j de bruit
        date_virement = date_echeance + timedelta(days=offset_days)

        libelle = make_libelle(client_nom, has_ref, police_ref, is_tiers, tiers_name)

        virements.append({
            "virement_id": f"VRT{vi:06d}",
            "date_virement": date_virement.date(),
            "montant_fcfa": montant,
            "libelle_banque": libelle,
            "banque_emettrice": random.choice(AGENCES),
            # colonnes "vérité terrain" gardées à part pour évaluer l'algo ensuite
            "_verite_police_id": police_ref,
            "_verite_a_ref_visible": has_ref,
        })

    df_virements = pd.DataFrame(virements)

    # Sauvegarde
    df_clients.to_csv("clients.csv", index=False)
    df_contrats.to_csv("contrats.csv", index=False)
    # Fichier "métier" (sans la vérité terrain) — c'est celui que l'algo doit rapprocher
    df_virements.drop(columns=["_verite_police_id", "_verite_a_ref_visible"]).to_csv(
        "releve_bancaire.csv", index=False
    )
    # Fichier de vérité terrain séparé, pour scorer la performance de l'algo (usage interne / démo)
    df_virements.to_csv("releve_bancaire_verite_terrain.csv", index=False)

    print(f"✅ clients.csv          : {len(df_clients):,} lignes")
    print(f"✅ contrats.csv         : {len(df_contrats):,} lignes")
    print(f"✅ releve_bancaire.csv  : {len(df_virements):,} lignes")
    print(f"   dont {(~df_virements['_verite_a_ref_visible']).mean()*100:.1f}% sans référence visible")


if __name__ == "__main__":
    main()
