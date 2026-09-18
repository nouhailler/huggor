← [Documentation](index.md)

# Référence

## Table des paramètres

| Paramètre | Onglet | Type | Défaut | Valeurs |
|---|---|---|---|---|
| Mot-clé | Recherche | texte | `Gemma` | libre |
| Domaine | Recherche | liste | `Tous les domaines` | 8 domaines pédagogiques |
| Tâche précise | Recherche | liste | `Toutes les tâches` | dépend du domaine |
| Langue | Recherche | liste | `Toutes les langues` | déclarées par les dépôts |
| Licence | Recherche | liste | `Toutes les licences` | déclarées par les dépôts |
| Trier par | Recherche | liste | `Téléchargements` | téléchargements, likes, date, pertinence |
| Minimum / Maximum (milliards) | Recherche | slider | `0` / `0` | 0–200 |
| Nombre de résultats | Recherche | slider | `20` | 5–100 |
| Usages | Mon usage | sélection multiple | aucun | 8 objectifs |
| RAM (Go) | Mon usage, Hardware | nombre | `16` | 0–4096 |
| VRAM (Go) | Mon usage, Hardware | nombre | `0` | 0–1024 |
| Collection | Favoris | texte/liste | vide | libre |
| Statut | Favoris | liste | vide | `à tester`, `testé`, `recommandé`, `à écarter` |
| Note personnelle | Favoris | slider | `0` | 0–5 |
| Tags | Favoris | texte | vide | libre, séparés par virgules |
| Dernier test | Favoris | texte | vide | date JJ/MM/AAAA |

Détail complet par onglet : [Paramètres](settings.md).

## Codes et messages d'erreur

| Situation | Message affiché | Cause | Solution |
|---|---|---|---|
| Panne de connectivité (réseau, DNS, timeout) | « Impossible de contacter le Hugging Face Hub. Vérifiez votre connexion et réessayez. » | Le Hub est injoignable | Réessayer ; le [mode hors connexion](offline.md) sert le cache si disponible |
| Dépôt introuvable | « Le modèle « X » est introuvable ou inaccessible. » | Identifiant erroné, modèle supprimé/renommé | Vérifier l'identifiant sur le Hub |
| Dépôt protégé (« gated ») | « Ce modèle est protégé. Acceptez ses conditions sur le Hub et fournissez un token autorisé. » | Conditions d'accès non acceptées | Accepter les conditions sur le Hub, fournir un token autorisé |
| Authentification refusée (401/403) | « Authentification Hugging Face refusée. Vérifiez votre token. » | Token absent, invalide ou insuffisant | Configurer/renouveler `HF_TOKEN` |
| Limite de requêtes atteinte (429) | « Limite de requêtes Hugging Face atteinte. Réessayez dans quelques instants. » | Trop de requêtes envoyées au Hub | Patienter puis réessayer |
| Autre erreur HTTP du Hub | « Le Hugging Face Hub a renvoyé une erreur. Réessayez plus tard. » | Erreur côté Hub non catégorisée | Réessayer plus tard |
| Identifiant de modèle invalide | « Identifiant de modèle invalide (exemple : auteur/nom-du-modele). » | Format d'identifiant incorrect | Corriger le format |
| Comparateur : nombre de modèles hors bornes | « Sélectionnez de 2 à 4 modèles. » | Moins de 2 ou plus de 4 identifiants saisis | Ajuster le nombre de modèles |
| Comparateur : doublon | « Chaque modèle doit être différent. » | Le même identifiant saisi deux fois | Retirer le doublon |

Source : [`src/api_client.py`](../src/api_client.py) (méthode `_translate_error`) et [`src/comparison.py`](../src/comparison.py) (`validate_comparison_ids`).

## Glossaire

| Terme | Définition | Utilisation dans Huggor |
|---|---|---|
| Hub (Hugging Face Hub) | Plateforme publique hébergeant modèles, datasets et espaces | Source unique des données affichées par Huggor |
| Dépôt (repo) | Espace de stockage d'un modèle sur le Hub, identifié par `auteur/nom` | Unité de base manipulée par la Recherche, les Détails, le Comparateur |
| Gated | Dépôt dont l'accès nécessite d'accepter des conditions sur le Hub | Cause l'erreur « Ce modèle est protégé » |
| Quantification | Réduction de la précision numérique d'un modèle pour réduire sa taille (GGUF, GPTQ, AWQ, EXL2, MLX…) | Détectée automatiquement dans la fiche Détails |
| Huggor Score | Note composite /100 propre à Huggor, sur 9 composantes | Voir [Huggor Score](features.md#huggor-score) |
| Model Advisor | Verdict d'adéquation matérielle (RAM/VRAM nécessaire) | Affiché dans la fiche Détails |
| TTL (time to live) | Durée de vie d'une entrée de cache avant expiration | Voir [Données → Stockage local](data.md#stockage-local) |
| Mode hors connexion | Dégradation gracieuse quand le Hub devient injoignable | Voir [Mode hors connexion](offline.md) |

## Compatibilité

- **Navigateurs** : tout navigateur récent supportant JavaScript (desktop ou mobile). Aucune restriction connue à un navigateur en particulier — non testé exhaustivement par navigateur (À vérifier pour une matrice de compatibilité précise par nom/version).
- **Écrans** : responsive dès 375px de large (menu hamburger en dessous de 768px) jusqu'aux grands écrans desktop.
- **Python** (exécution locale/serveur) : 3.10 ou supérieur, requis par le code et documenté dans le [README](../README.md#prérequis).
- **Systèmes** : le paquet packagé est spécifique à Debian/Ubuntu (`.deb`) ; l'application elle-même, étant un serveur Python + une page web, peut tourner sur tout système supportant Python 3.10+ (Linux, macOS, Windows) sans paquet dédié.
- **PWA installable** : uniquement quand déployée sur un Hugging Face Space (activation automatique par Gradio). Pas d'installation PWA sur Render ou en local sans configuration explicite (`pwa=True`).

## Limites connues

- **Onglet 🧪 Test** : non implémenté. Aucune fonctionnalité de test d'inférence n'existe à ce jour.
- **Estimations Hardware/Model Advisor** : théoriques, fondées sur des repères génériques de bande passante mémoire — jamais une mesure réelle du GPU/CPU effectivement installé.
- **Radar du Comparateur** : n'est pas une mesure de qualité, seulement une visualisation des quantités communes déclarées.
- **Statistiques Analytics** : portent uniquement sur l'échantillon chargé (jusqu'à 50 résultats), jamais sur tout le Hub. L'historique de croissance commence au premier chargement, sans reconstruction rétroactive.
- **Pas de synchronisation multi-appareil** : chaque installation (locale, Space, Render) a son propre cache et ses propres favoris, indépendants les uns des autres.
- **Stockage éphémère sur Hugging Face Spaces et Render (tier gratuit)** : `data/cache/`, `data/analytics/` et `data/favorites.json` sont réinitialisés à chaque redémarrage du conteneur, sauf stockage persistant payant activé.
- **Mode PWA** : actif automatiquement uniquement sur Hugging Face Spaces, pas sur Render ni en local.
