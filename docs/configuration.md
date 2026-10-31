← [Documentation](index.md)

# Configuration

Cette page liste les variables d'environnement lues par l'application. Les réglages de l'interface (filtres, sliders…) sont décrits dans [Paramètres](settings.md).

## Variables d'environnement

| Variable | Rôle | Obligatoire | Défaut | Exemple |
|---|---|---|---|---|
| `HF_TOKEN` | Token Hugging Face pour les dépôts privés ou protégés (lu par `huggingface_hub` et via `.env`) | Non | aucun (accès public) | `hf_xxx…` (ne jamais le publier) |
| `GRADIO_SERVER_NAME` | Adresse d'écoute du serveur | Non | `127.0.0.1` | `0.0.0.0` |
| `GRADIO_SERVER_PORT` | Port d'écoute (entier) ; une valeur non numérique lève une erreur au démarrage | Non | `7860` | `8080` |
| `HF_EXPLORER_DATA_DIR` | Répertoire des données (cache, analytics, favoris) | Non | `data/` à la racine du dépôt | `/var/lib/hf-explorer` |
| `GRADIO_ANALYTICS_ENABLED` | Variable propre à Gradio (non définie par Huggor) : `False` désactive la télémétrie anonyme de Gradio | Non | `True` (côté Gradio) | `False` |
| `RENDER_GIT_COMMIT`, `RENDER_GIT_BRANCH`, `RENDER_GIT_REPO_SLUG` | Injectées par Render ; utilisées uniquement par l'écran « ℹ️ À propos » | Non (ne pas les définir à la main) | — | — |

Dans le paquet Debian, le lanceur définit `HF_EXPLORER_DATA_DIR` (voir [Paquet Debian](packaging-debian.md)). Pour Render, voir [Déploiement sur Render](deployment-render.md) (`PYTHON_VERSION`, `PYTHONUNBUFFERED`).

## Fichier `.env`

`.env.example` ne contient que :

```bash
HF_TOKEN=votre_token_ici
```

Copier ce fichier en `.env` à la racine et remplacer la valeur. `.env` est dans `.gitignore` : ne jamais le versionner. `python-dotenv` le charge au démarrage du client API.

## Durées de cache

Le cache local utilise des durées par défaut non configurables par variable d'environnement : voir [Données → Stockage local](data.md#stockage-local).
