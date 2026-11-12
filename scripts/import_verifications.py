import json
import logging
from pathlib import Path
from sqlalchemy.orm import Session
from app.db.session import engine, SessionLocal
from app.models.verification import Base, Verification

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def import_data():
    # Créer les tables si elles n'existent pas
    Base.metadata.create_all(bind=engine)
    
    data_file = Path("data/verifications.json")
    if not data_file.exists():
        logger.error(f"Fichier introuvable : {data_file}")
        return

    with open(data_file, "r", encoding="utf-8") as f:
        verifications = json.load(f)

    db: Session = SessionLocal()
    try:
        count = 0
        for item in verifications:
            # Vérifier si le cas existe déjà (basé sur claim_text)
            existing = db.query(Verification).filter(Verification.claim_text == item["claim_text"]).first()
            if not existing:
                verif = Verification(
                    claim_text=item["claim_text"],
                    verdict=item["verdict"],
                    explanation=item["explanation"],
                    source_name=item["source_name"],
                    source_url=item.get("source_url"),
                    language=item.get("language", "fr")
                )
                db.add(verif)
                count += 1
        db.commit()
        logger.info(f"✅ {count} vérifications importées avec succès.")
    except Exception as e:
        db.rollback()
        logger.error(f"Erreur lors de l'importation : {e}")
    finally:
        db.close()

if __name__ == "__main__":
    import_data()