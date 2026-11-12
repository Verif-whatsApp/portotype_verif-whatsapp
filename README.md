# Vérif'WhatsApp

> Robot de fact-checking WhatsApp pour l'Afrique de l'Ouest — vérifiez une rumeur sans quitter WhatsApp.

[![CI](https://github.com/Verif-whatsApp/portotype_verif-whatsapp/actions/workflows/ci.yml/badge.svg)](https://github.com/Verif-whatsApp/portotype_verif-whatsapp/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

---

## Table des matières

- [Contexte](#contexte)
- [Le problème](#le-problème)
- [La solution](#la-solution)
- [Fonctionnalités (MVP)](#fonctionnalités-mvp)
- [Architecture](#architecture)
- [Stack technique](#stack-technique)
- [Prérequis](#prérequis)
- [Installation](#installation)
- [Configuration](#configuration)
- [Utilisation](#utilisation)
- [Tests](#tests)
- [Structure du projet](#structure-du-projet)
- [Feuille de route](#feuille-de-route)
- [Contribution](#contribution)
- [Licence](#licence)
- [Contact](#contact)

---

## Contexte

En Afrique de l'Ouest, la désinformation circule massivement via **WhatsApp**, souvent au sein de groupes privés où les outils de vérification traditionnels (sites web, applications) n'ont pas d'accès. Les utilisateurs reçoivent des messages suspects — fausses alertes sécuritaires, rumeurs sanitaires, faux communiqués gouvernementaux — et n'ont aucun moyen simple de vérifier avant de transférer.

Les initiatives existantes proposent des applications ou des portails centralisés. Cependant, elles exigent un changement d'habitude : **quitter WhatsApp, ouvrir une application, effectuer une recherche**. Le coût cognitif est trop élevé pour une adoption massive.

## Le problème

- 📱 **80 % de l'information** circule via WhatsApp et les réseaux sociaux en Afrique de l'Ouest.
- 🚨 Les rumeurs (sécurité, santé, politique) se propagent en quelques heures dans des groupes de centaines de personnes.
- 🧩 Les outils de vérification existants sont **hors du canal** où circule l'information.
- 🌍 Les langues locales et les faibles bandes passantes limitent l'adoption des applications lourdes.

## La solution

**Vérif'WhatsApp** est un robot qui vit *dans* WhatsApp. L'utilisateur transfère un message suspect à un numéro dédié. En quelques secondes, il reçoit une réponse claire, en français, avec un verdict et une source. **Aucune application à installer.**

```
Utilisateur : [transfère] "ALERTE : Attaque à Doropo, ne sortez pas"

Vérif'WhatsApp :
🚫 FAUX

Aucune attaque n'a été signalée à Doropo à cette date.
Les autorités locales ont démenti l'information.

Source : IvoireCheck, 12/10/2026
Lien : https://...

Ne partagez pas ce message.
```

## Fonctionnalités (MVP)

| ID | Fonctionnalité | Statut |
|----|----------------|--------|
| F1 | Réception de messages texte | 🚧 En cours |
| F2 | Réception d'images (captures d'écran) avec OCR | ⏳ Planifié |
| F3 | Base de connaissances de vérification | ⏳ Planifié |
| F4 | Moteur de correspondance (fuzzy matching) | ⏳ Planifié |
| F5 | Formatage standardisé des réponses | ⏳ Planifié |
| F6 | Interface et réponses en français | ⏳ Planifié |

**Hors périmètre MVP** : messages vocaux, recherche web en temps réel, interface d'administration, multilingue, application mobile autonome.

## Architecture

```
Utilisateur WhatsApp
        │
        ▼
┌───────────────────┐
│  API WhatsApp     │  (Meta WhatsApp Business Platform)
│  Business         │
└────────┬──────────┘
         │ Webhook
         ▼
┌───────────────────┐
│  Service Backend  │  (FastAPI)
│  - Réception      │
│  - OCR (images)   │
│  - Matching       │
│  - Formatage      │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  Base de          │  (SQLite pour MVP)
│  Connaissances    │
└───────────────────┘
```

## Stack technique

| Composant | Technologie | Justification |
|-----------|-------------|---------------|
| Passerelle WhatsApp | API officielle Meta (WhatsApp Business Platform) | Seule option conforme aux conditions d'utilisation |
| Backend | Python 3.11+ / FastAPI | Écosystème riche, déploiement simple, performances suffisantes |
| Base de connaissances | SQLite (MVP) → PostgreSQL (scale) | Aucun serveur dédié au démarrage |
| OCR | Tesseract | Gratuit, fiable sur captures d'écran WhatsApp |
| Matching | RapidFuzz | Similarité textuelle rapide, pas d'IA nécessaire pour le MVP |
| Qualité | Ruff (lint + formatage), Mypy, Pytest, Pre-commit | Standards de l'écosystème Python |
| CI/CD | GitHub Actions | Intégration native au dépôt |

## Prérequis

- **Python 3.11 ou supérieur**
- **Git**
- **Tesseract OCR** (pour la fonctionnalité F2)
  - Linux : `sudo apt install tesseract-ocr tesseract-ocr-fra`
  - macOS : `brew install tesseract tesseract-lang`
  - Windows : [installateur officiel](https://github.com/UB-Mannheim/tesseract/wiki)
- **Compte WhatsApp Business API** (Meta) — pour tester le webhook en conditions réelles. Le développement local fonctionne sans, via simulation.

## Installation

```bash
# 1. Cloner le dépôt
git clone https://github.com/Verif-whatsApp/portotype_verif-whatsapp.git
cd portotype_verif-whatsapp

# 2. Créer un environnement virtuel
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
# ou
.venv\Scripts\activate           # Windows

# 3. Installer les dépendances (mode développement)
pip install -e ".[dev]"

# 4. Installer les hooks de qualité
pre-commit install

# 5. Copier le fichier d'environnement
cp .env.example .env
```

## Configuration

Éditez le fichier `.env` avec vos identifiants :

```bash
# WhatsApp Business API (Meta)
WHATSAPP_VERIFY_TOKEN=change-me-verify-token
WHATSAPP_ACCESS_TOKEN=change-me-access-token
WHATSAPP_PHONE_NUMBER_ID=change-me-phone-number-id
WHATSAPP_API_VERSION=v21.0

# Application
APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8000
LOG_LEVEL=INFO

# Base de données
DATABASE_URL=sqlite:///./verif.db

# Matching
MATCHING_THRESHOLD=85
```

> ⚠️ **Ne jamais committer le fichier `.env`.** Il est déjà exclu via `.gitignore`.

## Utilisation

### Lancer le serveur en développement

```bash
make run
# ou
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Le serveur est accessible sur `http://localhost:8000`.

### Vérifier que le service fonctionne

```bash
curl http://localhost:8000/health
# → {"status": "ok"}
```

### Documenter l'API

FastAPI génère automatiquement la documentation interactive :

- Swagger UI : `http://localhost:8000/docs`
- ReDoc : `http://localhost:8000/redoc`

### Importer la base de connaissances

> 🚧 Script à venir (voir la feuille de route).

```bash
python scripts/import_verifications.py
```

## Tests

```bash
# Lancer tous les tests avec couverture
make test
# ou
pytest
```

La couverture est rapportée dans le terminal et dans `htmlcov/index.html`.

### Qualité du code

```bash
# Lint
make lint

# Formatage automatique
make format
```

## Structure du projet

Structure cible : les modules sont ajoutés au fil de la [feuille de route](#feuille-de-route).

```
portotype_verif-whatsapp/
├── .github/
│   └── workflows/
│       └── ci.yml                  # Intégration continue
├── app/
│   ├── main.py                     # Point d'entrée FastAPI
│   ├── config.py                   # Variables d'environnement
│   ├── api/
│   │   └── webhook.py              # Réception des webhooks WhatsApp
│   ├── services/
│   │   ├── whatsapp.py             # Envoi de messages via l'API Meta
│   │   ├── matching.py             # Moteur de correspondance
│   │   ├── ocr.py                  # Extraction de texte des images
│   │   └── formatting.py           # Formatage des réponses
│   ├── models/
│   │   └── verification.py         # Modèles SQLAlchemy
│   └── db/
│       ├── session.py              # Connexion base de données
│       └── seed.py                 # Alimentation initiale
├── data/
│   └── verifications.json          # Base de connaissances initiale
├── scripts/
│   └── import_verifications.py     # Import des données
├── tests/
│   ├── test_matching.py
│   ├── test_formatting.py
│   └── test_webhook.py
├── .env.example
├── .gitignore
├── .pre-commit-config.yaml
├── Makefile
├── pyproject.toml
├── README.md
└── LICENSE
```

## Feuille de route

### MVP (6 semaines)

- [x] Initialisation du projet (structure, config, CI)
- [ ] Configuration (`config.py`) et point d'entrée (`main.py`)
- [ ] Modèles de données et base de connaissances
- [ ] Moteur de correspondance + tests
- [ ] Formatage des réponses + tests
- [ ] Webhook WhatsApp
- [ ] Envoi de messages via l'API Meta
- [ ] Base de connaissances initiale (500 cas)
- [ ] Tests internes et pilote fermé

### Post-MVP (V2)

- [ ] Support des messages vocaux (transcription)
- [ ] Ajout du yoruba et du haoussa
- [ ] Vérification par recherche web en temps réel
- [ ] Interface d'administration
- [ ] Tableau de bord des rumeurs émergentes
- [ ] Partenariat officiel avec une organisation de fact-checking

## Contribution

Les contributions sont bienvenues ! Pour contribuer :

1. Forkez le dépôt.
2. Créez une branche de fonctionnalité (`git checkout -b feature/ma-fonctionnalite`).
3. Committez vos changements (`git commit -m 'feat: ajout de ma fonctionnalité'`).
4. Poussez la branche (`git push origin feature/ma-fonctionnalite`).
5. Ouvrez une Pull Request.

### Conventions

- **Commits** : [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`).
- **Style** : Ruff, lint et formatage (configuré dans `pyproject.toml`).
- **Types** : Mypy en mode strict.
- **Tests** : Toute nouvelle fonctionnalité doit être accompagnée de tests.

### Signaler un bug

Ouvrez une [issue](https://github.com/Verif-whatsApp/portotype_verif-whatsapp/issues) en décrivant :
- Le comportement attendu
- Le comportement observé
- Les étapes pour reproduire
- L'environnement (OS, version Python)

## Licence

Ce projet est distribué sous licence **MIT**. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

## Contact

- **Organisation** : Shalom Digital Solutions
- **Dépôt** : [github.com/Verif-whatsApp/portotype_verif-whatsapp](https://github.com/Verif-whatsApp/portotype_verif-whatsapp)

---

<p align="center">
  Fait avec ❤️ pour l'Afrique de l'Ouest
</p>
