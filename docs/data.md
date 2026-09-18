← [Documentation](index.md)

# Données

## Données utilisées

| Donnée | Origine | Stockage | Transmission | Finalité |
|---|---|---|---|---|
| Métadonnées de modèles (auteur, licence, tags, téléchargements, likes, fichiers…) | API publique Hugging Face Hub | Cache local (`data/cache/`), en mémoire le temps de l'affichage | Reçue depuis le Hub, jamais renvoyée ailleurs | Afficher les résultats de recherche et les fiches détaillées |
| Model Card (README du dépôt) | Hugging Face Hub | Cache local (`data/cache/`) | Reçue depuis le Hub | Afficher la documentation du modèle |
| Favoris (collection, statut, note, tags, commentaire) | Saisie de l'utilisateur | `data/favorites.json`, en local, versionné vide (`[]`) dans le dépôt source | Aucune (jamais envoyée au Hub ni ailleurs) | Suivi personnel des modèles évalués |
| Observations Analytics (tendances, croissance) | Résultats de recherche déjà reçus du Hub, agrégés localement | `data/analytics/` | Aucune | Détecter des tendances dans le temps, localement |
| RAM/VRAM déclarées | Saisie de l'utilisateur | Non stockée (recalculée à chaque saisie) | Jamais transmise au Hub | Calculer un verdict de compatibilité matérielle |
| Token Hugging Face (`HF_TOKEN`) | Configuration de l'utilisateur/de l'administrateur du déploiement | Variable d'environnement, fichier `.env` local ou secret de la plateforme de déploiement | Envoyé au Hub uniquement pour authentifier les requêtes | Accéder aux ressources privées/protégées — voir [Permissions](permissions.md) |

Aucune donnée personnelle identifiante (nom, e-mail, adresse) n'est collectée par l'application elle-même. Elle ne dispose d'aucun compte utilisateur.

## Stockage local

| Répertoire | Contenu | Durée de vie / TTL | Suivi par Git |
|---|---|---|---|
| `data/cache/` — namespace `search` | Résultats de recherche | 15 minutes (900 s) par défaut, secours possible au-delà en cas de panne réseau (voir [Mode hors connexion](offline.md)) | Non (`.gitignore`) |
| `data/cache/` — namespace `model` | Détails de modèle | 30 minutes (1 800 s) | Non |
| `data/cache/` — namespace `card` | Model Card | 1 heure (3 600 s) | Non |
| `data/analytics/` — `observations` / `trend_observations` | Historique de tendances Analytics | 90 jours observés conservés, expiration après 1 an d'inactivité | Non |
| `data/favorites.json` | Collection de favoris | Permanent (pas d'expiration automatique) | Oui, mais doit rester vide (`[]`) dans les commits — c'est une donnée utilisateur, pas un exemple |

**Ce qui est conservé** : uniquement des métadonnées publiques du Hub et les données personnelles saisies volontairement (favoris). **Suppression** : voir [Gestion du cache](features.md#gestion-du-cache) pour vider le cache manuellement ; supprimer `data/favorites.json` (ou son contenu) efface les favoris. **À la désinstallation** (paquet Debian) : les données dans `${XDG_DATA_HOME:-~/.local/share}/hf-explorer/` sont conservées par défaut, pas supprimées automatiquement — voir [Bien démarrer](getting-started.md#mise-à-jour-et-désinstallation). **Export** : aucune fonction d'export n'existe dans l'interface. `data/favorites.json` reste un fichier JSON lisible et copiable directement en dehors de l'application.

Aucune base de données externe, aucun `localStorage`/`IndexedDB` navigateur n'est utilisé : tout le stockage se fait côté serveur, dans des fichiers JSON locaux (voir [`src/utils/cache.py`](../src/utils/cache.py) et [`src/utils/favorites.py`](../src/utils/favorites.py)).
