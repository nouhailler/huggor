← [Documentation](index.md)

# Fonctionnalités

## Recherche par domaine et tâche

**Description** : rechercher des modèles sans connaître le vocabulaire technique du Hub, en passant par un domaine (🧠 LLM, 👁️ Vision, 🖼️ Image, 🎙️ Audio, 🗣️ Speech, 🔤 Embeddings, 🌐 Multimodal, 🧩 Reranking) puis une tâche précise réellement couverte.
**Objectif** : rendre la recherche pédagogique plutôt que de forcer l'utilisateur à connaître les `pipeline_tag` du Hub.
**Prérequis** : aucun (fonctionne sans token pour les modèles publics).
**Comment l'utiliser** : voir [Guide → 🔍 Recherche](guide.md#-recherche).
**Options** : mot-clé, domaine, tâche précise, langue, licence, tri, plage de paramètres (milliards), nombre de résultats (5 à 100).
**Paramètres associés** : voir [Paramètres](settings.md).
**Données utilisées** : métadonnées publiques du Hub (auteur, licence, tags, téléchargements, likes…) ; aucune donnée personnelle transmise.
**Résultat** : cartes de résultats, mises en cache localement 15 minutes (900 s) par défaut.
**Fonctionnement hors connexion** : si le Hub devient injoignable, la dernière recherche identique déjà en cache continue de s'afficher, même expirée — voir [Mode hors connexion](offline.md).
**Fonctionnement en ligne** : appel direct à l'API du Hub, résultat mis en cache.
**Limites** : chaque requête est bornée à 100 résultats maximum.
**Erreurs possibles** : voir [Référence → Codes et messages d'erreur](reference.md#codes-et-messages-derreur).
**Dépannage** : [Aucun résultat ne s'affiche](troubleshooting.md#aucun-résultat-ne-saffiche).
**FAQ** : [Puis-je utiliser l'application sans Internet ?](faq.md)

## Recherche par usage (Mon usage)

**Description** : choisir un objectif concret (Chatbot, Coding, RAG, Embeddings, Traduction, Vision, Speech, Génération d'images) plutôt qu'une tâche Hub, croisé avec sa RAM/VRAM déclarée.
**Objectif** : ne remonter que des modèles réellement jouables sur la machine de l'utilisateur.
**Prérequis** : renseigner RAM et/ou VRAM (au moins une valeur non nulle).
**Comment l'utiliser** : voir [Guide → 🎯 Mon usage](guide.md#-mon-usage).
**Options** : sélection multiple d'usages ; un usage partagé par plusieurs objectifs cochés n'est interrogé qu'une seule fois côté Hub.
**Données utilisées** : identiques à la recherche standard, plus les valeurs RAM/VRAM saisies (non transmises au Hub, utilisées uniquement pour le calcul local du verdict).
**Résultat** : cartes avec verdict de précision/vitesse et bouton **⭐ Pin** vers les Favoris.
**Fonctionnement hors connexion** : bénéficie du même secours de cache que la recherche standard.
**Limites** : le verdict de vitesse reste théorique — voir [Limites connues](reference.md#limites-connues).

## Fiche technique et Model Advisor

**Description** : la fiche détaillée d'un modèle (identité, architecture, compatibilité, Model Card, fichiers) et son verdict d'adéquation matérielle (RAM/VRAM nécessaire selon la précision).
**Objectif** : donner une vision technique complète et une recommandation de téléchargement explicite (poids/shards/adapters), sans boîte noire.
**Prérequis** : identifiant de modèle valide (`auteur/nom-du-modele`).
**Comment l'utiliser** : voir [Guide → 📄 Détails](guide.md#-détails).
**Options** : bouton **🔄 Actualiser depuis Hugging Face** pour forcer un rechargement sans cache.
**Données utilisées** : métadonnées, fichiers et tailles, Model Card complète, `config.json` du dépôt.
**Résultat** : identité, architecture, quantification détectée, compatibilités d'exécution, [Huggor Score](#huggor-score), Model Advisor, recommandation de téléchargement, Model Card, arborescence des fichiers, snippets de code.
**Fonctionnement hors connexion** : une fiche déjà consultée reste affichable même si le Hub devient injoignable ensuite — voir [Mode hors connexion](offline.md).
**Limites** : le Model Advisor donne des ordres de grandeur, pas une mesure réelle — voir [Limites connues](reference.md#limites-connues).
**Erreurs possibles** : identifiant invalide, modèle introuvable, dépôt protégé (« gated »), authentification refusée — voir [Référence](reference.md#codes-et-messages-derreur).

## Huggor Score

**Description** : note composite sur 100, calculée à partir de 9 composantes, **toujours affichées avec leur détail** (jamais un chiffre seul).
**Objectif** : donner un indicateur de confiance transparent sur un modèle, sans jamais cacher le calcul.
**Composantes et pondération** :

| Composante | Points |
|---|---:|
| Popularité | 15 |
| Compatibilité locale | 15 |
| Maturité | 15 |
| Fraîcheur | 10 |
| Documentation | 10 |
| Licence | 10 |
| Safetensors | 10 |
| Quantification disponible | 10 |
| Taille | 5 |
| **Total** | **100** |

**Comment l'utiliser** : affiché automatiquement dans l'onglet [📄 Détails](guide.md#-détails), section « Huggor Score ».
**Résultat** : score /100 accompagné, pour chaque composante, des points obtenus, du maximum possible et de l'explication (ex. « Dernière modification il y a X jour(s) »).
**Limites** : une composante non déterminable (ex. paramètres non renseignés par le dépôt) obtient 0 point avec la raison explicitée — jamais une valeur inventée.

## Détection de quantification et variantes existantes

**Description** : identifier automatiquement le format de précision d'un modèle (FP32, FP16, BF16, INT8, paliers GGUF Q8 à Q2, GPTQ, AWQ, EXL2, MLX) et rechercher les versions déjà quantifiées existant sur le Hub.
**Objectif** : éviter de télécharger un modèle trop volumineux quand une version plus légère existe déjà.
**Comment l'utiliser** : automatique à l'ouverture de la fiche [📄 Détails](guide.md#-détails).
**Résultat** : tableau des précisions détectées, et liste des variantes quantifiées trouvées sur le Hub (triées par popularité), en excluant les simples quantifications du modèle affiché lui-même.
**Fonctionnement en ligne** : la recherche de variantes nécessite un appel réseau (recherche par nom de base du modèle) ; une erreur réseau lors de cette recherche annexe n'empêche jamais l'affichage du reste de la fiche.

## Modèles similaires

**Description** : recommandation de modèles proches, rapprochés par famille, tâche, taille, langue déclarée, licence et disponibilité quantifiée.
**Objectif** : proposer des alternatives pertinentes sans jargon.
**Comment l'utiliser** : automatique, affiché dans la fiche [📄 Détails](guide.md#-détails).
**Limites** : rapprochement heuristique, pas une recommandation validée manuellement.

## Calculateur de ressources (Hardware)

**Description** : indiquer, indépendamment de tout modèle précis, quelles précisions (FP32 à Q4_K_M) tiennent réellement selon la RAM/VRAM déclarée.
**Objectif** : aider à choisir une précision avant même de chercher un modèle.
**Comment l'utiliser** : voir [Guide → 💻 Hardware](guide.md#-hardware).
**Données utilisées** : uniquement les valeurs RAM/VRAM saisies, jamais transmises au Hub — calcul 100 % local.
**Résultat** : tableau des précisions supportées avec estimation de vitesse et de contexte.
**Limites** : estimations théoriques fondées sur des repères génériques de bande passante mémoire, **pas** sur le GPU/CPU réellement installé (le matériel renseigné ne sert que pour le calcul, il n'est jamais détecté automatiquement).

## Comparateur décisionnel

**Description** : comparer 2 à 4 modèles avec une recommandation motivée du meilleur compromis pour un usage local.
**Objectif** : trancher entre plusieurs modèles candidats sur des critères objectifs.
**Comment l'utiliser** : voir [Guide → 🆚 Comparateur](guide.md#-comparateur).
**Options** : 2 à 4 identifiants distincts.
**Résultat** : tableau décisionnel (paramètres, popularité, contexte, licence, couverture FR déclarée, adéquation locale, GGUF), recommandation textuelle, tableau technique complet, radar des quantités relatives.
**Fonctionnement hors connexion** : chaque fiche modèle chargée pour la comparaison bénéficie du même secours de cache que la fiche détaillée.
**Limites** : le radar n'est pas une mesure de qualité ; il est masqué si moins de trois quantités communes sont renseignées entre les modèles comparés.
**Erreurs possibles** : « Sélectionnez de 2 à 4 modèles. », « Chaque modèle doit être différent. », « Identifiant invalide : X. ».

## Favoris (collections)

**Description** : gestionnaire de collection personnelle avec tags, statut, note et suivi de test.
**Objectif** : garder une trace personnelle des modèles évalués, sans dépendre du Hub.
**Comment l'utiliser** : voir [Guide → ⭐ Favoris](guide.md#-favoris).
**Options** : Collection (libre), Statut (`à tester`, `testé`, `recommandé`, `à écarter`), Note (0 à 5), Tags (libres, séparés par virgules), Date de dernier test, commentaire libre.
**Données utilisées** : stockées uniquement dans `data/favorites.json`, en local — voir [Données](data.md).
**Résultat** : liste filtrable par collection.
**Fonctionnement hors connexion** : entièrement fonctionnel sans réseau, puisque purement local.

## Analytics — Observatoire du Hub

**Description** : tendances curatées (🔥 plus téléchargés, ❤️ plus appréciés, 🆕 récents, 🇫🇷 français, 💻 optimisés local) et détection de croissance rapide (« Rising models ») fondée sur des observations locales répétées dans le temps.
**Objectif** : suivre l'évolution du Hub sans avoir à connaître ses filtres avancés.
**Comment l'utiliser** : voir [Guide → 📈 Analytics](guide.md#-analytics).
**Données utilisées** : observations enregistrées localement dans `data/analytics/`, séparées par filtres et empreinte d'authentification — voir [Données](data.md).
**Résultat** : listes classées, ou détection de croissance (ex. 100k → 500k téléchargements) avec les deux dates d'observation.
**Limites** : les statistiques portent uniquement sur l'échantillon chargé (jusqu'à 50 résultats), pas sur tout le Hub. L'évolution commence au premier chargement, sans historique reconstruit rétroactivement. Une seule journée observée ne permet pas de détecter de croissance.
**Rétention** : 90 jours d'observations conservés, expiration après un an d'inactivité.

## Gestion du cache

**Description** : administration du cache local par domaine nommé (🔍 Recherches, 📄 Détails de modèles, 📖 Model cards, 📈 Statistiques, 🧪 Benchmarks).
**Objectif** : donner un contrôle explicite sur les données mises en cache, sans boîte noire.
**Comment l'utiliser** : panneau « 🗄️ Gestion du cache » dans l'onglet [📈 Analytics](guide.md#-analytics).
**Options** : **🗑 Vider le cache** (par domaine ou tout), **🔄 Actualiser l'affichage**. Dans la fiche modèle, bouton **🔄 Actualiser depuis Hugging Face** pour forcer un rechargement d'un élément précis sans passer par le cache.
**Données utilisées** : voir la table des durées de vie dans [Données → Stockage local](data.md#stockage-local).
**Résultat** : aperçu par domaine (nombre d'entrées, taille, fraîcheur) et purge ciblée ou totale.
**Note** : le domaine « 🧪 Benchmarks » est déclaré vide dès maintenant avec la note « Aucune donnée : l'onglet Test (inférence) n'est pas encore implémenté. » — l'architecture est prête à l'accueillir sans rien casser ailleurs.

## Mode hors connexion

Voir la page dédiée : [Fonctionnement hors connexion](offline.md).
