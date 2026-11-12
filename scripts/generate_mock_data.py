import json
import random
from pathlib import Path
from datetime import datetime, timedelta

# Listes de base pour générer des variations réalistes
LIEUX = ["Doropo", "Abidjan", "Dakar", "Cotonou", "Lomé", "Ouagadougou", "Bamako", "Niamey", "Kano", "Accra"]
SUJETS_SECURITE = ["attaque", "enlèvement", "manifestation", "coupure d'électricité", "fermeture de frontière"]
SUJETS_SANTE = ["vaccin contre la polio", "pilule contraceptive", "remède contre le paludisme", "test de dépistage", "traitement contre le COVID"]
SUJETS_POLITIQUE = ["nouvelle loi", "augmentation des impôts", "report des élections", "nomination ministérielle", "budget de l'État"]
SUJETS_ARNAQUES = ["billet de 10000 FCFA", "carte SIM gratuite", "subvention gouvernementale", "promotion Mobile Money", "tirage au sort"]
SOURCES = ["Africa Check", "IvoireCheck", "FactSpace West Africa", "NigerCheck", "Capp Check"]

def generate_mock_data(num_entries=500) -> list[dict]:
    data = []
    for i in range(num_entries):
        # Choix aléatoire d'une catégorie
        category = random.choice(["securite", "sante", "politique", "arnaques"])
        lieu = random.choice(LIEUX)
        
        if category == "securite":
            sujet = random.choice(SUJETS_SECURITE)
            claim = f"ALERTE : {sujet} à {lieu}, ne sortez pas"
            verdict = random.choice(["faux", "faux", "trompeur"])
            explanation = f"Aucune information officielle ne confirme une {sujet} à {lieu}. Les autorités ont démenti."
        elif category == "sante":
            sujet = random.choice(SUJETS_SANTE)
            claim = f"Le {sujet} rend stérile / est dangereux selon une étude"
            verdict = random.choice(["faux", "trompeur", "non_verifie"])
            explanation = f"Aucune étude scientifique sérieuse ne prouve cela concernant le {sujet}."
        elif category == "politique":
            sujet = random.choice(SUJETS_POLITIQUE)
            claim = f"Le gouvernement annonce {sujet} au {lieu}"
            verdict = random.choice(["faux", "trompeur"])
            explanation = f"Le communiqué officiel ne mentionne pas {sujet}. Il s'agit d'une fausse annonce."
        else:
            sujet = random.choice(SUJETS_ARNAQUES)
            claim = f"Gagnez de l'argent avec {sujet} en cliquant sur ce lien"
            verdict = "faux"
            explanation = f"Il s'agit d'une arnaque courante. Ne cliquez pas sur ce lien et ne partagez pas vos informations."

        # Création des variantes (pour tester le fuzzy matching)
        variants = [
            claim.lower(),
            claim.replace("ALERTE : ", ""),
            f"Info : {claim}"
        ]

        date_verif = (datetime.now() - timedelta(days=random.randint(1, 365))).strftime("%Y-%m-%d")
        
        data.append({
            "claim_text": claim,
            "claim_variants": variants,
            "verdict": verdict,
            "explanation": explanation,
            "source_name": random.choice(SOURCES),
            "source_url": f"https://example.org/verification-{i+1}",
            "verified_at": date_verif,
            "language": "fr"
        })
    
    return data

if __name__ == "__main__":
    mock_data = generate_mock_data(500)
    
    output_file = Path("data/verifications.json")
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(mock_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ {len(mock_data)} vérifications générées dans {output_file}")