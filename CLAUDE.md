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

## Mentions légales / avertissement de premier lancement

Système ajouté via la commande `/mentions-legales`. Contenu centralisé dans [`src/legal_notice.py`](src/legal_notice.py), affiché à deux endroits dans [`app.py`](app.py) : un bandeau au premier lancement et un lien permanent « ⚖️ Mentions légales » en pied de page. Détails complets : [`docs/legal.md`](docs/legal.md).

- **Stockage** : `localStorage` du navigateur, clé `legal_notice_acknowledged` (+ `legal_notice_acknowledged_version`). 100 % côté client, rien envoyé au serveur ni journalisé.
- **Modifier le texte** : éditer [`src/legal_notice.py`](src/legal_notice.py) uniquement — jamais dupliquer un paragraphe ailleurs, il est rendu aux deux endroits depuis ce seul fichier.
- **Changer la version** : incrémenter `LEGAL_NOTICE_VERSION` dans `src/legal_notice.py` et `LEGAL_NOTICE_VERSION` (chaîne JS) dans `_LEGAL_ACCEPT_JS` (`app.py`). Ne pas déclencher automatiquement une réapparition de l'avertissement pour un changement mineur — c'est un choix délibéré, pas fait par défaut ; si un changement le justifie un jour, comparer `legal_notice_acknowledged_version` au stockage côté JS avant de considérer l'avertissement comme acquis.
- **Tester le premier lancement** : ouvrir l'app dans une fenêtre de navigation privée, ou effacer `localStorage` pour `localhost:7860` (console navigateur : `localStorage.removeItem('legal_notice_acknowledged')` puis recharger).
- **Tests Python** : [`tests/test_legal_notice.py`](tests/test_legal_notice.py) vérifie la structure du contenu (8 sections, non vides, pas de section GPS puisque Huggor n'en a pas besoin). Le parcours interactif (bandeau → détails → acceptation → persistance) a été vérifié manuellement au navigateur, pas par un test automatisé : le projet n'a pas d'outillage e2e JS et il n'était pas justifié d'en ajouter un pour cette seule fonctionnalité.

## Git

Dépôt GitHub : `nouhailler/huggor`. Ne jamais commit de secret (`.env`, tokens). `data/cache/` et `data/analytics/` sont ignorés par git ; `data/favorites.json` est versionné mais doit rester vide (`[]`) dans les commits — c'est un fichier de données utilisateur, pas un exemple.
