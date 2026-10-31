← [Documentation](index.md)

# Déploiement sur Hugging Face Spaces

Techniquement possible sans modification du code : l'application lit `GRADIO_SERVER_NAME` / `GRADIO_SERVER_PORT` (fournis par l'environnement d'un Space) et résout le token via les mécanismes standards de `huggingface_hub`.

## Limite importante : abonnement PRO

À la date de rédaction, héberger un Space Gradio (non statique) sur le matériel gratuit **CPU Basic** nécessite un abonnement PRO, malgré ce qu'affiche `hf spaces hardware`. Seul **ZeroGPU** reste accessible sans abonnement, mais il exige au moins une fonction décorée `@spaces.GPU`, que Huggor n'a pas et n'a pas besoin d'avoir. Sans PRO, Spaces n'est donc **pas** une option gratuite viable : voir [Render](deployment-render.md), qui a été retenu pour la démo en ligne.

## En-tête YAML requis

Un Space lit sa configuration dans un bloc YAML en tête du `README.md`. Il n'est plus dans le README du dépôt (il s'affichait comme un tableau sur GitHub) ; pour recréer un Space, l'ajouter en tête du fichier :

```yaml
---
title: HF Explorer
emoji: 🤗
colorFrom: indigo
colorTo: blue
sdk: gradio
sdk_version: 6.26.0
app_file: app.py
pinned: false
---
```

## Étapes

1. Créer un Space sur <https://huggingface.co/new-space> avec le SDK **Gradio**.
2. Ajouter son dépôt Git comme remote puis pousser `main` :
   ```bash
   git remote add space https://huggingface.co/spaces/<votre-compte>/<nom-du-space>
   git push space main
   ```
3. Renseigner `HF_TOKEN` dans **Settings → Repository secrets** du Space si des ressources privées ou protégées doivent être accessibles (jamais dans le code ni dans le dépôt).
4. Le Space installe `requirements.txt`, lance `python app.py` et expose l'interface sur son URL publique.

## Réserves

- **Stockage éphémère** : `data/cache/`, `data/analytics/` et `data/favorites.json` sont réinitialisés à chaque redémarrage du conteneur, sauf stockage persistant payant.
- **PWA** : Gradio l'active automatiquement sur un Space (aucun paramètre `pwa=` dans `app.py`).
