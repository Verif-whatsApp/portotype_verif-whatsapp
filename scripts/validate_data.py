import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

VALID_VERDICTS = {"faux", "trompeur", "vrai", "non_verifie"}

def validate() -> None:
    data_file = Path("data/verifications.json")
    if not data_file.exists():
        logger.error(f"Fichier introuvable : {data_file}")
        return

    try:
        with open(data_file, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"❌ Erreur de syntaxe JSON à la ligne {e.lineno}, colonne {e.colno} : {e.msg}")
        return

    errors = 0
    for i, item in enumerate(data):
        # Vérification des champs obligatoires
        required_fields = ["claim_text", "verdict", "explanation", "source_name"]
        for field in required_fields:
            if field not in item or not str(item[field]).strip():
                logger.error(f"❌ Cas #{i+1} : champ '{field}' manquant ou vide.")
                errors += 1
                
        # Vérification du verdict
        if item.get("verdict") not in VALID_VERDICTS:
            logger.error(f"❌ Cas #{i+1} : verdict '{item.get('verdict')}' invalide. Doit être : {VALID_VERDICTS}")
            errors += 1

    if errors == 0:
        logger.info(f"✅ Super ! Les {len(data)} vérifications sont valides et prêtes à être importées.")
    else:
        logger.warning(f"⚠️ {errors} erreur(s) trouvée(s). Corrigez le fichier avant d'importer.")

if __name__ == "__main__":
    validate()