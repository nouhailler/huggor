# Contexte projet — Huggor (HF Explorer)

Application Python/Gradio pour rechercher, examiner, comparer et tester les modèles du Hugging Face Hub. Voir [README.md](README.md) pour l'installation, le lancement et le déploiement (Hugging Face Spaces, Render).

## Documentation

> Documentation : suivre [DOCUMENTATION_SPEC.md](DOCUMENTATION_SPEC.md). Une tâche n'est « done » que si la doc correspondante (dans [`/docs`](docs/index.md)) est à jour — voir §39 de la spec pour la check-list complète.

La documentation utilisateur/développeur vit dans [`/docs`](docs/index.md), en Markdown simple (pas de générateur de site : le projet n'en a pas besoin, voir §4 de la spec). Elle est versionnée avec le code.

Avant de considérer une tâche fonctionnelle comme terminée :
1. Le code est-il terminé et testé (`python -m unittest discover -s tests -v`) ?
2. La documentation dans `/docs` reflète-t-elle le nouveau comportement (fonctionnalité, paramètre, permission, donnée, erreur, mode hors connexion) ?
3. Le changelog (`docs/versions.md`) doit-il être mis à jour ?
4. La FAQ ou le dépannage (`docs/faq.md`, `docs/troubleshooting.md`) doivent-ils l'être aussi ?

Ne jamais inventer un comportement non vérifiable dans le code, la config ou les tests — écrire `À vérifier` et le signaler.

## Tests

```bash
python -m unittest discover -s tests -v
```

Isolés du réseau, bibliothèque standard uniquement (`unittest`).

## Git

Dépôt GitHub : `nouhailler/huggor`. Ne jamais commit de secret (`.env`, tokens). `data/cache/` et `data/analytics/` sont ignorés par git ; `data/favorites.json` est versionné mais doit rester vide (`[]`) dans les commits — c'est un fichier de données utilisateur, pas un exemple.
