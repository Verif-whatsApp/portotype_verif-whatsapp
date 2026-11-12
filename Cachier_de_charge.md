
---

# Cahier des Charges — « Vérif'WhatsApp »
## Robot de fact-checking léger pour l'Afrique de l'Ouest

**Version** : 1.0 (MVP)
**Date** : Novembre 2026
**Confidentialité** : Interne / Partenaires

---

## 1. Contexte et Problématique

En Afrique de l'Ouest, la désinformation circule massivement via WhatsApp, souvent au sein de groupes privés où les outils de vérification traditionnels (sites web, applications) n'ont pas d'accès. Les utilisateurs reçoivent des messages suspects — fausses alertes sécuritaires, rumeurs sanitaires, faux communiqués — et n'ont aucun moyen simple de vérifier avant de transférer.

Les initiatives existantes (Vérif'All, BLOC Anti-Fake) proposent des applications ou des portails centralisés . Cependant, elles exigent un changement d'habitude : quitter WhatsApp, ouvrir une application, effectuer une recherche. **Le coût cognitif est trop élevé pour une adoption massive.**

**Notre proposition** : un robot qui vit *dans* WhatsApp. L'utilisateur transfère un message suspect à un numéro dédié. En quelques secondes, il reçoit une réponse claire, en français, avec un verdict et une source. Aucune application à installer.

---

## 2. Objectifs du Produit

### 2.1 Objectif principal
Réduire la propagation de la désinformation en Afrique de l'Ouest en offrant un point de vérification instantané, accessible depuis l'application que les utilisateurs utilisent déjà.

### 2.2 Objectifs mesurables (MVP, 6 premiers mois)
| Indicateur | Cible |
|---|---|
| Utilisateurs ayant transféré au moins 1 message | 2 000 |
| Taux de « transfert » (messages reçus / utilisateurs actifs) | > 3 |
| Taux d'action post-vérification (l'utilisateur ne partage pas le message après verdict « Faux ») | > 60% (mesuré par enquête) |
| Temps de réponse médian | < 10 secondes |
| Couverture des cas vérifiés (base de données initiale) | 500 cas |

---

## 3. Périmètre Fonctionnel

### 3.1 Fonctionnalités incluses (MVP)

**F1 — Réception de messages texte**
L'utilisateur transfère un message texte au numéro WhatsApp du robot. Le robot accuse réception, analyse le contenu, et renvoie un verdict structuré.

**F2 — Réception d'images (captures d'écran)**
L'utilisateur envoie une capture d'écran d'un message suspect. Le robot extrait le texte par OCR, puis applique la même logique que pour le texte.

**F3 — Base de connaissances de vérification**
Base de données structurée contenant des paires « affirmation / verdict / source / date ». Alimentée manuellement au démarrage à partir des publications d'Africa Check, FactSpace West Africa, IvoireCheck, et autres organisations signataires de l'IFCN .

**F4 — Moteur de correspondance**
Le message de l'utilisateur est comparé à la base de connaissances par similarité textuelle (fuzzy matching). Si une correspondance suffisamment proche est trouvée (seuil de confiance), le verdict correspondant est renvoyé. Sinon, le robot répond « Non vérifié pour l'instant » avec une invitation à consulter les sources officielles.

**F5 — Format de réponse standardisé**
Chaque réponse contient :
- Le verdict (Faux / Trompeur / Vrai / Non vérifié)
- Une explication courte (2-3 phrases maximum)
- La source (nom de l'organisation + lien si disponible)
- La date de la vérification

**F6 — Langue**
Interface et réponses en **français** pour le MVP. L'architecture doit permettre l'ajout ultérieur de langues locales (yoruba, haoussa, bambara, etc.) sans refonte majeure.

### 3.2 Fonctionnalités exclues du MVP (hors périmètre)
- Messages vocaux (reporté à la v2)
- Vérification en temps réel par recherche web (le MVP repose sur une base pré-construite)
- Interface d'administration web (gestion manuelle via fichiers au démarrage)
- Multilingue (hors français)
- Application mobile autonome

---

## 4. Architecture Technique

### 4.1 Vue d'ensemble

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
│  Service Backend  │  (Python / FastAPI ou Node.js)
│  - Réception      │
│  - OCR (images)   │
│  - Matching       │
│  - Formatage      │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  Base de          │  (SQLite pour MVP, PostgreSQL si scale)
│  Connaissances    │
└───────────────────┘
```

### 4.2 Choix techniques recommandés

| Composant | Technologie | Justification |
|---|---|---|
| **Passerelle WhatsApp** | API officielle Meta (WhatsApp Business Platform) | Seule option conforme aux conditions d'utilisation ; évite les risques de blocage. 1 000 messages de service gratuits/mois  |
| **Backend** | Python (FastAPI) ou Node.js (Express) | Écosystème riche pour OCR et traitement de texte ; déploiement simple |
| **OCR** | Tesseract (open source) | Gratuit, suffisant pour des captures d'écran de messages WhatsApp (texte relativement propre) |
| **Base de connaissances** | SQLite (MVP) → PostgreSQL (si volume > 10 000 cas) | SQLite ne nécessite aucun serveur dédié, idéal pour un démarrage léger |
| **Matching** | `fuzzywuzzy` ou `rapidfuzz` (Python) | Similarité textuelle simple, pas besoin d'IA pour le MVP |
| **Hébergement** | VPS basique (2 Go RAM) ou service cloud gratuit (Railway, Render) | Coût minimal au démarrage |

### 4.3 Contraintes techniques
- **Coût WhatsApp** : À partir d'octobre 2026, les réponses de bots sont facturées au-delà de 1 000 messages de service par mois . Prévoir un budget évolutif.
- **Délai de réponse** : Le traitement doit être asynchrone pour ne pas bloquer l'API WhatsApp. Utiliser une file d'attente simple (Redis ou file en mémoire) si le volume augmente.
- **Sécurité** : Les messages des utilisateurs ne doivent pas être stockés au-delà du temps nécessaire à la vérification (RGPD et bonnes pratiques).

---

## 5. Base de Connaissances : Stratégie d'Alimentation

### 5.1 Sources initiales (manuelles)
| Source | Type de contenu | Langue | Format |
|---|---|---|---|
| Africa Check (Afrique de l'Ouest) | Vérifications publiées | Français/Anglais | Articles web |
| FactSpace West Africa / GhanaFact | Vérifications Ghana, Nigeria, etc. | Anglais | Articles web  |
| IvoireCheck (Côte d'Ivoire) | Vérifications locales | Français | Articles web |
| NigerCheck, Capp Check (Bénin) | Vérifications locales | Français | Articles web  |

### 5.2 Structure de la base (table `verifications`)
| Champ | Type | Description |
|---|---|---|
| `id` | INTEGER | Identifiant unique |
| `claim_text` | TEXT | L'affirmation telle qu'elle circule |
| `claim_variants` | TEXT (JSON) | Variantes connues de la formulation |
| `verdict` | TEXT | `faux`, `trompeur`, `vrai`, `non_verifie` |
| `explanation` | TEXT | Explication courte (2-3 phrases) |
| `source_name` | TEXT | Organisation source |
| `source_url` | TEXT | Lien vers la vérification originale |
| `verified_at` | DATE | Date de la vérification |
| `language` | TEXT | `fr`, `en`, etc. |

### 5.3 Processus d'alimentation initial
1. **Semaine 1-2** : Collecte manuelle de 300 à 500 vérifications récentes (6 derniers mois) auprès des sources listées.
2. **Semaine 3** : Structuration dans la base, rédaction des explications courtes (vulgarisation).
3. **Semaine 4** : Test interne avec 50 messages types pour ajuster le seuil de similarité.

---

## 6. Expérience Utilisateur (UX)

### 6.1 Parcours utilisateur type

1. L'utilisateur reçoit dans un groupe WhatsApp : *« ALERTE : Attaque à Doropo, ne sortez pas »*
2. Il transfère ce message au numéro du robot.
3. Le robot répond en moins de 10 secondes :
   ```
   🚫 FAUX
   
   Aucune attaque n'a été signalée à Doropo à cette date.
   Les autorités locales ont démenti l'information.
   
   Source : IvoireCheck, 12/10/2026
   Lien : [lien vers la vérification]
   
   Ne partagez pas ce message.
   ```

### 6.2 Règles de réponse
- **Verdict « Faux »** : Message ferme, source citée, invitation explicite à ne pas partager.
- **Verdict « Trompeur »** : Nuancer (« Le message contient une part de vérité mais... »).
- **Verdict « Non vérifié »** : Ne pas inventer de réponse. Dire clairement que le message n'a pas encore été vérifié, et orienter vers les sources officielles.
- **Message non reconnu / hors sujet** : Réponse polie indiquant que le robot ne peut pas traiter cette demande.

---

## 7. Planning de Développement (MVP)

| Phase | Durée | Livrables |
|---|---|---|
| **Phase 1 : Setup** | Semaine 1 | Compte WhatsApp Business API créé ; backend vide déployé ; webhook fonctionnel |
| **Phase 2 : Base de connaissances** | Semaines 2-3 | 500 cas structurés et validés ; moteur de matching opérationnel |
| **Phase 3 : Traitement texte + images** | Semaine 4 | OCR intégré ; flux complet texte → verdict → réponse |
| **Phase 4 : Tests internes** | Semaine 5 | 100 messages testés ; ajustement du seuil de similarité ; corrections |
| **Phase 5 : Pilote fermé** | Semaine 6 | Déploiement auprès de 20-50 utilisateurs (groupes partenaires) ; collecte de feedback |

**Durée totale** : 6 semaines (à temps plein pour une personne, ou 8-10 semaines à temps partiel).

---

## 8. Budget Prévisionnel (MVP, 6 premiers mois)

| Poste | Coût estimé | Notes |
|---|---|---|
| **API WhatsApp Business** | 0 € (dans le quota gratuit) → ~50 €/mois si dépassement | 1 000 messages gratuits/mois  |
| **Hébergement backend** | 0-10 €/mois | Render/Railway tier gratuit ou VPS basique |
| **Nom de domaine** | ~15 €/an | Optionnel pour le MVP |
| **Temps de développement** | Interne / bénévolat | 6 semaines à temps plein |
| **Collecte et structuration des données** | Interne | 2-3 semaines |
| **Total cash (6 mois)** | **~100-200 €** | Hors valorisation du temps |

---

## 9. Risques et Mitigation

| Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|
| Coût WhatsApp explose si adoption forte | Moyenne | Élevé | Surveiller le compteur ; limiter les réponses à 1 message par requête ; prévoir un budget de scale |
| Base de connaissances insuffisante (trop de « non vérifié ») | Élevée au début | Moyen | Prioriser les 10 rumeurs les plus fréquentes dans les groupes pilotes ; enrichir en continu |
| Faible adoption (les utilisateurs ne connaissent pas le numéro) | Élevée | Élevé | Partenariats avec des administrateurs de groupes WhatsApp ; diffusion via des influenceurs locaux |
| Qualité OCR insuffisante sur captures d'écran | Moyenne | Faible | Tesseract est généralement fiable sur du texte WhatsApp ; fallback manuel si échec |
| Concurrence de Vérif'All / BLOC Anti-Fake | Moyenne | Moyen | Se différencier par l'intégration WhatsApp native (pas d'application à installer) |

---

## 10. Indicateurs de Succès et Évaluation

### 10.1 Métriques techniques
- Temps de réponse médian < 10 s
- Taux d'échec OCR < 5%
- Disponibilité du service > 95%

### 10.2 Métriques produit
- Nombre d'utilisateurs uniques ayant envoyé au moins 1 message
- Nombre moyen de messages par utilisateur actif
- Distribution des verdicts (faux / trompeur / vrai / non vérifié)
- Top 10 des rumeurs les plus fréquemment soumises (pour enrichir la base)

### 10.3 Méthode d'évaluation de l'impact
Enquête auprès des utilisateurs pilotes après 4 semaines :
- « Avez-vous cessé de partager un message après avoir reçu un verdict "Faux" ? »
- « Recommanderiez-vous ce service à un ami ? »

---

## 11. Évolutions Post-MVP (V2 et au-delà)

| Fonctionnalité | Priorité | Complexité |
|---|---|---|
| Support des messages vocaux (transcription) | Haute | Moyenne |
| Ajout du yoruba et du haoussa (interface et réponses) | Haute | Élevée (corpus limité) |
| Vérification par recherche web en temps réel (Perplexity API ou Tavily) | Moyenne | Moyenne |
| Interface d'administration pour l'équipe (ajout de cas sans toucher au code) | Moyenne | Faible |
| Tableau de bord des rumeurs émergentes (pour les partenaires) | Basse | Moyenne |
| Partenariat officiel avec une organisation de fact-checking (Africa Check, FactSpace) | Haute | Relationnel |

---

## 12. Annexes

### A. Références régionales
- **FactSpace West Africa** : organisation non-profit basée au Ghana, couvrant 5 pays, signataire de l'IFCN .
- **GhanaFact** : projet de FactSpace, première organisation de fact-checking du Ghana .
- **IvoireCheck** : plateforme de vérification ivoirienne, membre du consortium BLOC Anti-Fake .
- **BLOC Anti-Fake** : consortium de 5 organisations (Bénin, Mali, Niger, Sénégal, Côte d'Ivoire) financé par l'OIF .

### B. Contraintes légales et éthiques
- Le robot doit clairement indiquer qu'il s'agit d'un outil automatisé, pas d'un journaliste.
- Les verdicts doivent toujours citer une source humaine vérifiable.
- En cas de doute, le robot doit préférer « Non vérifié » à une réponse spéculative.
- Les données utilisateurs (numéros de téléphone, contenus des messages) ne doivent pas être conservées au-delà de la session de vérification, sauf consentement explicite.

---