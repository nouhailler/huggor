← [Documentation](index.md)

# Architecture

Application Python monolithique : un serveur Gradio qui interroge l'API du Hugging Face Hub et stocke cache, favoris et observations dans des fichiers JSON locaux. Pas de base de données ni de service annexe.

## Technologies

| Rôle | Choix |
|---|---|
| Langage | Python 3.10+ (testé ici avec 3.13 ; Render : 3.11.9) |
| Interface | [Gradio](https://www.gradio.app/) 6.26.0, thème « Soft » personnalisé |
| Accès au Hub | `huggingface-hub` 1.30.0 (`HfApi`, `ModelCard`) |
| Tableaux / graphiques | `pandas` 2.3.3, `plotly` 7.0.0 |
| Configuration | `python-dotenv` 1.2.3 |
| Source de données | API du [Hugging Face Hub](https://huggingface.co/models) |
| Stockage | Fichiers JSON dans `data/` (cache avec TTL, favoris, observations) |
| Tests | `unittest` (bibliothèque standard), isolés du réseau |
| Déploiement | Local, paquet `.deb`, Render ; Hugging Face Spaces possible (PRO) |

Versions épinglées dans [`requirements.txt`](../requirements.txt).

## Arborescence

```text
huggor/
├── app.py              # Point d'entrée : assemblage Gradio, CSS, menu, écrans superposés
├── src/
│   ├── api_client.py       # Client du Hub (recherche, fiche, Model Card), cache, mode hors connexion
│   ├── model_analysis.py   # Analyse technique d'un dépôt, conseil de téléchargement
│   ├── hardware_advisor.py # Besoins mémoire et verdicts d'usage local
│   ├── resource_calculator.py  # Calculateur RAM/VRAM (onglet Hardware)
│   ├── huggor_score.py     # Score composite /100 et son détail
│   ├── comparison.py       # Comparaison de 2 à 4 modèles
│   ├── quantization_search.py  # Variantes quantifiées sur le Hub
│   ├── similar_models.py   # Modèles similaires
│   ├── use_case_search.py  # Recherche par usage (onglet Mon usage)
│   ├── analytics.py        # Statistiques et historique des observations
│   ├── cache_manager.py    # Gestion du cache par domaine
│   ├── app_info.py         # Version, commit, liens (écran « À propos »)
│   ├── legal_notice.py     # Texte légal centralisé
│   ├── onboarding.py       # Contenu de la visite guidée
│   ├── paths.py            # Répertoire de données
│   ├── ui/                 # Un module par onglet Gradio
│   └── utils/              # cache.py (JSON + TTL), favorites.py, formatters.py
├── tests/              # Tests unitaires (un fichier par module)
├── data/               # Cache, analytics (ignorés par Git), favorites.json (versionné vide)
├── docs/               # Documentation
├── packaging/          # Lanceur et entrée de menu du paquet Debian
├── scripts/build_deb.py    # Construction du paquet .deb
├── assets/             # Logo
├── render.yaml         # Blueprint Render
├── requirements.txt
└── .env.example
```

## Flux de données

1. Un onglet (`src/ui/*_tab.py`) appelle le client `HuggingFaceClient` ou un module métier.
2. Le client consulte d'abord le cache (`data/cache/`), sinon le Hub, puis met en cache.
3. Si le Hub est injoignable, le client sert l'entrée de cache même expirée (voir [Mode hors connexion](offline.md)).
4. Les modules métier (score, advisor, comparaison…) calculent à partir de métadonnées publiques ; l'interface affiche le résultat.

Le cache distingue accès anonyme et accès authentifié via une empreinte SHA-256 tronquée du token : le token lui-même n'est ni stocké ni journalisé.

Le contenu légal, la visite guidée et les métadonnées de build sont isolés dans leurs modules : `app.py` ne fait que câbler leur affichage. Conventions de développement : voir [`CLAUDE.md`](../CLAUDE.md).
