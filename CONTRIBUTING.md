# Contribuer à HF Explorer (Huggor)

Merci de votre intérêt. Le projet est petit et maintenu par une seule personne : les propositions les plus faciles à traiter sont courtes, ciblées et testées.

## Signaler un problème ou proposer une idée

Ouvrez une [issue](https://github.com/nouhailler/huggor/issues/new) en précisant : version (écran « ℹ️ À propos »), mode d'accès (local, Debian, Render), navigateur, message d'erreur exact et étapes pour reproduire. Voir aussi [Dépannage](docs/troubleshooting.md) et [FAQ](docs/faq.md). Pour une faille de sécurité, suivez plutôt [SECURITY.md](SECURITY.md).

## Proposer une modification

1. Forkez le dépôt et créez une branche à partir de `main`.
2. Installez l'environnement de développement (voir [Démarrage rapide](README.md#démarrage-rapide)).
3. Faites votre modification, en suivant le style du code voisin (docstrings en français, noms existants).
4. Lancez les tests, qui doivent tous passer :
   ```bash
   python -m unittest discover -s tests -v
   ```
5. Mettez à jour la documentation concernée dans [`docs/`](docs/index.md) (fonctionnalité, paramètre, donnée, erreur, mode hors connexion) et, si besoin, [`docs/versions.md`](docs/versions.md). Une modification fonctionnelle n'est considérée comme terminée qu'avec sa documentation.
6. Ouvrez une [pull request](https://github.com/nouhailler/huggor/pulls) décrivant le changement et son motif.

## Règles à respecter

- **Aucun secret dans Git** : jamais de `.env`, de token ni de clé. `data/favorites.json` doit rester vide (`[]`) dans les commits : c'est une donnée utilisateur.
- **Tests isolés du réseau**, avec la bibliothèque standard uniquement (`unittest`).
- **Pas de comportement inventé** dans la documentation : ce qui n'est pas vérifiable dans le code est marqué `À vérifier`.
- Les textes légaux ne se modifient que dans [`src/legal_notice.py`](src/legal_notice.py), la visite guidée que dans [`src/onboarding.py`](src/onboarding.py).

Conventions détaillées : [`CLAUDE.md`](CLAUDE.md).
