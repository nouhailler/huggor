← [Documentation](index.md)

# Déploiement sur Render

Render héberge un vrai processus Python persistant, avec un tier gratuit qui se met en veille après inactivité. C'est la cible de la [démo en ligne](https://huggor.onrender.com/).

Le fichier [`render.yaml`](../render.yaml) à la racine décrit le service (Blueprint Render). Aucune modification du code n'a été nécessaire. Render fournit le port à écouter via `$PORT` (pas via `GRADIO_SERVER_PORT`), donc la commande de démarrage fait le pont :

```yaml
startCommand: GRADIO_SERVER_NAME=0.0.0.0 GRADIO_SERVER_PORT=$PORT python app.py
```

## Étapes

1. Sur <https://dashboard.render.com> : **New → Blueprint**, puis connecter le dépôt GitHub `nouhailler/huggor`. Render détecte `render.yaml`.
2. Renseigner le secret `HF_TOKEN` dans les paramètres du service si des ressources privées ou protégées doivent être accessibles. Il est déclaré avec `sync: false` pour ne jamais figurer dans le dépôt.
3. Render installe `requirements.txt`, lance la commande de démarrage et expose l'interface sur `https://<nom-du-service>.onrender.com`.

## Variables d'environnement du service

| Variable | Rôle |
|---|---|
| `PYTHON_VERSION` | Version de Python utilisée par Render (`3.11.9` dans `render.yaml`) |
| `PYTHONUNBUFFERED` | `1` : sans elle, la sortie standard n'apparaît dans les logs Render qu'avec un retard imprévisible |
| `HF_TOKEN` | Secret facultatif, à saisir dans le tableau de bord (`sync: false`) |

Render injecte aussi `RENDER_GIT_COMMIT`, `RENDER_GIT_BRANCH` et `RENDER_GIT_REPO_SLUG`, utilisées par l'écran « ℹ️ À propos » pour afficher la version : Render déploie depuis un clone Git superficiel, sans tags ni remote `origin`, où `git describe` échoue.

## Réserves

- **Stockage éphémère** : `data/cache/`, `data/analytics/` et `data/favorites.json` sont réinitialisés à chaque redémarrage ou mise en veille, sauf disque persistant payant.
- **Mise en veille** après 15 minutes d'inactivité sur le tier gratuit : le premier visiteur suivant attend 30 à 50 secondes (voir [Dépannage](troubleshooting.md)).
- **PWA** : le mode PWA de Gradio n'est pas activé automatiquement ici (comportement propre à la détection d'un Space Hugging Face) ; il peut l'être avec `pwa=True` dans l'appel à `launch()`.
- **Secrets** : l'API REST de Render renvoie les valeurs des variables d'environnement **en clair**. Ne jamais les afficher ni les journaliser pour déboguer.

Alternative : [Hugging Face Spaces](deployment-huggingface.md) (déconseillé sans abonnement PRO).
