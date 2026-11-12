
---

## Étape 0 : Préparation du dépôt GitHub

### 0.1 Créer le dépôt

Sur GitHub, créez un dépôt nommé par exemple `verif-whatsapp` (ou le nom que vous préférez). Recommandations :

- **Visibilité** : `Private` au démarrage (vous pourrez passer en public plus tard).
- **Ne pas initialiser** avec README, `.gitignore` ou licence — on va tout créer localement pour garder le contrôle.
- **Branche par défaut** : `main`.

### 0.2 Cloner localement

```bash
git clone https://github.com/Verif-whatsApp/portotype_verif-whatsapp.git
cd portotype_verif-whatsapp
```

---

## Étape 1 : Structure du projet

On adopte une structure claire, extensible, et conforme aux standards Python (puisque le cahier des charges recommande FastAPI).

```
verif-whatsapp/
├── .github/
│   └── workflows/
│       └── ci.yml                  # Intégration continue (tests + lint)
├── app/
│   ├── __init__.py
│   ├── main.py                     # Point d'entrée FastAPI
│   ├── config.py                   # Variables d'environnement
│   ├── api/
│   │   ├── __init__.py
│   │   └── webhook.py              # Réception des webhooks WhatsApp
│   ├── services/
│   │   ├── __init__.py
│   │   ├── whatsapp.py             # Envoi de messages via l'API Meta
│   │   ├── matching.py             # Moteur de correspondance
│   │   ├── ocr.py                  # Extraction de texte des images
│   │   └── formatting.py           # Formatage des réponses
│   ├── models/
│   │   ├── __init__.py
│   │   └── verification.py         # Modèles SQLAlchemy
│   └── db/
│       ├── __init__.py
│       ├── session.py              # Connexion base de données
│       └── seed.py                 # Script d'alimentation initiale
├── data/
│   └── verifications.json          # Base de connaissances initiale (MVP)
├── tests/
│   ├── __init__.py
│   ├── test_matching.py
│   ├── test_formatting.py
│   └── test_webhook.py
├── scripts/
│   └── import_verifications.py     # Import des données vers la base
├── .env.example                    # Modèle de variables d'environnement
├── .gitignore
├── .pre-commit-config.yaml         # Hooks de qualité (black, ruff, mypy)
├── pyproject.toml                  # Dépendances et configuration
├── README.md
├── LICENSE
└── Makefile                        # Commandes raccourcies
```

---

## Étape 2 : Fichiers de fondation à créer maintenant

Voici les fichiers exacts à créer dans le dépôt, avec leur contenu prêt à l'emploi.

### 2.1 `.gitignore`

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
dist/
*.egg-info/
.eggs/

# Environnements virtuels
.venv/
venv/
env/

# Variables d'environnement
.env
.env.local

# Base de données locale
*.db
*.sqlite3

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Tests
.pytest_cache/
.coverage
htmlcov/
```

### 2.2 `.env.example`

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

### 2.3 `pyproject.toml`

```toml
[project]
name = "verif-whatsapp"
version = "0.1.0"
description = "Robot de fact-checking WhatsApp pour l'Afrique de l'Ouest"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "httpx>=0.27.0",
    "sqlalchemy>=2.0.0",
    "pydantic>=2.9.0",
    "pydantic-settings>=2.5.0",
    "python-multipart>=0.0.9",
    "rapidfuzz>=3.9.0",
    "pytesseract>=0.3.13",
    "pillow>=10.4.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=5.0.0",
    "ruff>=0.6.0",
    "black>=24.8.0",
    "mypy>=1.11.0",
    "pre-commit>=3.8.0",
]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.black]
line-length = 100
target-version = ["py311"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --cov=app --cov-report=term-missing"

[tool.mypy]
python_version = "3.11"
strict = true
ignore_missing_imports = true
```

### 2.4 `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.9
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.11.2
    hooks:
      - id: mypy
        additional_dependencies: [pydantic, sqlalchemy]
```

### 2.5 `README.md` (squelette)

```markdown
# Vérif'WhatsApp

Robot de fact-checking WhatsApp pour l'Afrique de l'Ouest.

## Contexte

Ce projet vise à réduire la propagation de la désinformation en Afrique de l'Ouest
en offrant un point de vérification instantané, accessible directement depuis WhatsApp.

## Stack technique

- Python 3.11+
- FastAPI (backend)
- SQLite (base de connaissances, MVP)
- API WhatsApp Business (Meta)
- RapidFuzz (moteur de correspondance)
- Tesseract (OCR pour captures d'écran)

## Démarrage rapide

```bash
# 1. Cloner le dépôt
git clone https://github.com/Verif-whatsApp/portotype_verif-whatsapp.git
cd portotype_verif-whatsapp

# 2. Créer un environnement virtuel
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# ou .venv\Scripts\activate  # Windows

# 3. Installer les dépendances
pip install -e ".[dev]"

# 4. Configurer les variables d'environnement
cp .env.example .env
# Éditer .env avec vos identifiants WhatsApp Business

# 5. Lancer le serveur en développement
uvicorn app.main:app --reload
```

## Tests

```bash
pytest
```

## Structure du projet

Voir le cahier des charges (document séparé) pour la description détaillée.

## Licence

Voir fichier LICENSE.
```

### 2.6 `LICENSE`

Pour un projet open source, je recommande **MIT** (permissive, adaptée à un usage large en Afrique de l'Ouest) ou **Apache 2.0** (si vous prévoyez des partenariats institutionnels). Voici le contenu MIT :

```
MIT License

Copyright (c) 2026 Shalom Digital Solutions

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### 2.7 `Makefile`

```makefile
.PHONY: install run test lint format clean

install:
	pip install -e ".[dev]"
	pre-commit install

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest

lint:
	ruff check .
	mypy app

format:
	ruff format .
	black .

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage htmlcov
```

### 2.8 `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"

      - name: Install dependencies
        run: |
          pip install -e ".[dev]"

      - name: Lint (ruff)
        run: ruff check .

      - name: Type check (mypy)
        run: mypy app

      - name: Tests
        run: pytest
```

---

## Étape 3 : Premier commit

Une fois les fichiers ci-dessus créés, exécutez :

```bash
git add .
git commit -m "chore: initialisation du projet (structure, config, CI)"
git push origin main
```

---

## Étape 4 : Ce qu'on fera ensuite (dans l'ordre)

Une fois ce socle poussé sur GitHub, on enchaînera dans cet ordre :

1. **`app/config.py`** — Chargement des variables d'environnement (Pydantic Settings).
2. **`app/main.py`** — Point d'entrée FastAPI avec un endpoint `/health` minimal.
3. **`app/models/verification.py`** — Modèle SQLAlchemy pour la base de connaissances.
4. **`app/services/matching.py`** — Moteur de correspondance (le cœur du produit, on écrira les tests en même temps).
5. **`app/services/formatting.py`** — Formatage des réponses (verdicts, explications, sources).
6. **`app/api/webhook.py`** — Réception et traitement des webhooks WhatsApp.
7. **`app/services/whatsapp.py`** — Envoi de messages via l'API Meta.
8. **`data/verifications.json`** + **`scripts/import_verifications.py`** — Base de connaissances initiale.

---

## Question avant de continuer

Pour que je vous fournisse les fichiers suivants de façon parfaitement adaptée :

1. **Confirmez le nom du dépôt** (et l'organisation GitHub si vous en avez une).
2. **Avez-vous déjà un compte WhatsApp Business API** (Meta) configuré, ou faut-il que je vous guide aussi sur cette étape ? C'est un prérequis pour tester le webhook en conditions réelles, mais on peut développer et tester localement sans, en simulant les webhooks.
3. **Préférence de licence** : MIT (permissive) ou Apache 2.0 (plus formelle, adaptée aux partenariats institutionnels) ?