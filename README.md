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
- [Connecter WhatsApp](#connecter-whatsapp)
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
| F2 | Réception d'images (captures d'écran) avec OCR | 🚧 En cours |
| F3 | Base de connaissances de vérification | 🚧 En cours |
| F4 | Moteur de correspondance (fuzzy matching) | 🚧 En cours |
| F5 | Formatage standardisé des réponses | 🚧 En cours |
| F6 | Interface et réponses en français | 🚧 En cours |

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
- **Compte développeur Meta** (gratuit) — uniquement pour tester avec le vrai WhatsApp, voir [Connecter WhatsApp](#connecter-whatsapp). Le développement local fonctionne sans, via simulation.

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
# WhatsApp Business Platform / API Cloud (Meta)
WHATSAPP_VERIFY_TOKEN=change-me-verify-token   # à inventer, à saisir aussi chez Meta
WHATSAPP_ACCESS_TOKEN=change-me-access-token
WHATSAPP_PHONE_NUMBER_ID=change-me-phone-number-id
WHATSAPP_APP_SECRET=change-me-app-secret       # vérifie la signature des requêtes de Meta
WHATSAPP_API_VERSION=v25.0

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

Le fichier JSON contient une liste de vérifications (voir
[`data/verifications.example.json`](data/verifications.example.json) pour le format). Contrôlez-le
d'abord : la commande applique exactement les règles de l'import et affiche **toutes** les erreurs
d'un coup (champ manquant, verdict inconnu, date invalide, même affirmation avec deux verdicts).

```bash
python scripts/validate_data.py data/verifications.json    # contrôle, n'importe rien
python scripts/import_verifications.py data/verifications.json
```

L'import est répétable : les affirmations déjà présentes sont ignorées, et une entrée invalide
annule tout l'import avec un message précis. `data/verifications.json` est la **vraie** base (des
vérifications réelles, chacune avec sa source) : elle n'existe pas encore dans le dépôt.

### Données de test (fictives)

Pour tester sans vraie base, deux fichiers fictifs sont fournis : `data/verifications.example.json`
(2 entrées) et `data/verifications.mock.json` (110 affirmations générées par
`python scripts/generate_mock_data.py`).

> ⚠️ Ces entrées sont **inventées** : verdicts tirés au hasard, source « fictive », adresses
> `example.org`. Ne leur attribuez jamais le nom d'une vraie organisation de fact-checking.
> Avec `APP_ENV=production`, l'import les **refuse**, et un test empêche de les commiter sous
> le nom `data/verifications.json`.

## Connecter WhatsApp

### Faut-il WhatsApp Business ?

- **Les utilisateurs** qui transfèrent un message au robot gardent leur WhatsApp habituel
  (WhatsApp Messenger) : rien à installer ni à changer de leur côté.
- **Le numéro du robot**, lui, doit être enregistré sur la **plateforme WhatsApp Business de Meta
  (API Cloud)**. Ce n'est pas l'application « WhatsApp Business » du téléphone : c'est le service
  pour développeurs, qui permet à un programme d'envoyer et de recevoir des messages.
- Un numéro enregistré sur l'API ne peut plus servir dans l'application WhatsApp, et un numéro
  déjà utilisé sur WhatsApp doit d'abord y être supprimé. **N'utilisez jamais votre numéro personnel**.

### Étape 1 : tester avec le numéro de test de Meta (gratuit)

Meta fournit un numéro de test qui peut écrire à 5 numéros que vous déclarez (le vôtre, par
exemple). Vous discutez alors avec le robot depuis votre WhatsApp habituel.

1. Sur [developers.facebook.com](https://developers.facebook.com), créez une application de type
   *Business* et ajoutez-y le produit **WhatsApp**.
2. Dans la page de configuration de l'API WhatsApp, relevez l'**identifiant du numéro de
   téléphone** (`WHATSAPP_PHONE_NUMBER_ID`) et le **jeton d'accès** temporaire
   (`WHATSAPP_ACCESS_TOKEN`, il expire vite en mode test), puis ajoutez votre numéro dans la
   liste des destinataires.
3. Dans les paramètres de base de l'application, relevez la **clé secrète**
   (`WHATSAPP_APP_SECRET`).
4. Inventez un `WHATSAPP_VERIFY_TOKEN` (une chaîne secrète quelconque).
5. Exposez votre serveur en HTTPS (par exemple avec `ngrok http 8000` ou `cloudflared`), puis
   enregistrez chez Meta l'URL de rappel `https://<votre-adresse>/webhook` avec votre jeton de
   vérification, et abonnez-vous au champ **messages**.
6. Écrivez au numéro de test depuis votre WhatsApp.

> Les intitulés exacts de l'interface Meta évoluent : suivez la documentation officielle
> « WhatsApp Business Platform > Get started » si un libellé a changé.

### Étape 2 : production

- Un **numéro dédié** au robot, non enregistré sur WhatsApp.
- La **vérification de l'entreprise** dans Meta Business Manager, nécessaire pour écrire à
  n'importe quel numéro (le numéro de test est limité à 5 destinataires).
- Un **jeton d'accès permanent** (utilisateur système), à la place du jeton temporaire.
- `APP_ENV=production` : le webhook refuse alors toutes les notifications si `WHATSAPP_APP_SECRET` est vide.

### Tester sans compte Meta (simulation)

Sans `WHATSAPP_ACCESS_TOKEN` (et hors production), le robot écrit ses réponses dans les logs du
serveur au lieu de les envoyer. Le simulateur envoie un message signé comme le ferait Meta :

```bash
python scripts/import_verifications.py data/verifications.mock.json    # ou ...example.json
make run                                  # dans un premier terminal
python scripts/simulate_webhook.py "EXEMPLE FICTIF : une rumeur inventée pour tester le robot de vérification WhatsApp"
```

La réponse apparaît dans le terminal du serveur (`[simulation] réponse pour ***0000 : ...`).
Si `WHATSAPP_APP_SECRET` est défini dans `.env`, le simulateur signe ses requêtes avec.

### Sécurité et confidentialité

- Chaque requête est authentifiée par la signature `X-Hub-Signature-256` (clé secrète de
  l'application) : sans elle, n'importe qui pourrait faire répondre le robot.
- Le contenu des messages et les numéros complets ne sont **jamais écrits dans les logs** et rien
  n'est conservé après la réponse, sauf l'identifiant du message, gardé en mémoire pour ignorer
  les renvois de Meta.

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

Les fichiers marqués 🚧 restent à écrire (voir la [feuille de route](#feuille-de-route)).

```
portotype_verif-whatsapp/
├── .github/
│   └── workflows/
│       └── ci.yml                  # Intégration continue
├── app/
│   ├── main.py                     # Point d'entrée FastAPI (démarrage, routes)
│   ├── config.py                   # Variables d'environnement
│   ├── security.py                 # Signature des requêtes de Meta, comparaison de jetons
│   ├── api/
│   │   └── webhook.py              # GET (vérification Meta) et POST (messages)
│   ├── schemas/
│   │   └── whatsapp.py             # Format des notifications de Meta
│   ├── services/
│   │   ├── bot.py                  # Traitement d'un message : vérification et réponse
│   │   ├── whatsapp.py             # Client de l'API Meta (envoi, lecture, médias)
│   │   ├── matching.py             # Moteur de correspondance
│   │   ├── ocr.py                  # Extraction de texte des images
│   │   ├── formatting.py           # Formatage des réponses
│   │   └── importer.py             # Import de la base de connaissances
│   ├── models/
│   │   └── verification.py         # Modèles SQLAlchemy
│   └── db/
│       ├── base.py                 # Base déclarative
│       └── session.py              # Connexion base de données
├── data/
│   ├── verifications.example.json  # Exemple FICTIF du format (2 entrées)
│   ├── verifications.mock.json     # Données de test FICTIVES (110 affirmations)
│   └── verifications.json          # 🚧 Vraie base de connaissances (500 cas visés)
├── scripts/
│   ├── import_verifications.py     # Import des données
│   ├── validate_data.py            # Contrôle d'un fichier sans l'importer
│   ├── generate_mock_data.py       # Génère des données de test fictives
│   └── simulate_webhook.py         # Simule un message WhatsApp (sans compte Meta)
├── tests/                          # Tests unitaires et d'intégration
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
- [x] Configuration (`config.py`) et point d'entrée (`main.py`, endpoint `/health`)
- [x] Modèles de données (table `verifications`, session SQLAlchemy)
- [x] Moteur de correspondance + tests
- [x] Formatage des réponses + tests
- [x] Webhook WhatsApp (vérification Meta, signature, réception)
- [x] Envoi de messages via l'API Meta
- [x] OCR des captures d'écran (Tesseract)
- [ ] Test avec le numéro de test de Meta (conditions réelles)
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
