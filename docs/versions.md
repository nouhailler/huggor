← [Documentation](index.md)

# Versions

# Version 0.2.0

Date : 2026-09-18.

## Nouveautés

- Onglet 🎯 Mon usage (recherche par objectif croisée avec RAM/VRAM), avec bouton « ⭐ Pin » vers les Favoris
- Model Advisor (verdict RAM/VRAM) et calculateur de ressources (onglet 💻 Hardware)
- Huggor Score (composite /100, 9 composantes toujours détaillées)
- Détection de quantification et recherche de variantes déjà quantifiées sur le Hub
- Recommandation de « Modèles similaires »
- Comparateur transformé en tableau décisionnel avec recommandation motivée
- Navigation pédagogique par domaine puis tâche précise dans la Recherche
- Onglet ⭐ Favoris transformé en gestionnaire de collections (tags, statut, note, dernier test, commentaire)
- Onglet 📈 Analytics : Observatoire du Hub (tendances curatées, détection de croissance « Rising models »)
- Gestion du cache industrialisée par domaine, avec purge ciblée et actualisation forcée
- Mode hors connexion : dégradation gracieuse quand le Hub devient injoignable
- Menu hamburger catégorisé pour la navigation mobile (< 768px)
- Pré-remplissage du champ de recherche avec « Gemma » et recherche déclenchable par la touche Entrée
- Configuration de déploiement pour Hugging Face Spaces et pour Render
- Documentation complète sous `/docs`, conforme à `DOCUMENTATION_SPEC.md`

## Corrections

- `JsonCache.get()` supprimait une entrée expirée avant que le secours hors connexion (`get_allow_stale`) ait pu s'en servir ; le secours est désormais capturé avant cette suppression.
- Le champ de recherche ne déclenchait pas la soumission par la touche Entrée faute de `max_lines` explicitement défini (condition interne de Gradio non satisfaite) ; corrigé en fixant `max_lines=1`.
- Un bug réel de détection de précision (`float16` détecté à tort comme sous-chaîne de `bfloat16`) a été corrigé par une expression régulière stricte dans [`src/model_analysis.py`](../src/model_analysis.py).

## Changements de paramètres

- Le champ « Mot-clé » de l'onglet Recherche a changé de valeur par défaut : vide → `Gemma`.

## Changements de données

- Ajout du domaine de cache « 🧪 Benchmarks » (vide, réservé pour la future fonctionnalité de test d'inférence — aucune donnée n'y est stockée à ce jour).
- Ajout de `data/analytics/` (observations de tendances, 90 jours conservés, expiration après un an d'inactivité).

## Documentation mise à jour

- Création complète de `/docs` à partir du code réel, des tests et du README existant.

---

# Version 0.1.0

Date : 2026-09-14 (première publication, paquet Debian).

## Nouveautés

- Accès au Hub, cache local, recherche par mot-clé et filtres (langue, licence, tri, plage de paramètres)
- Fiche technique du modèle : identité, architecture, quantification, compatibilités d'exécution
- Ouverture automatique de la fiche depuis les résultats de recherche
- Comparateur de modèles, premières statistiques Analytics, infobulles explicatives
- Paquet d'installation Debian/Ubuntu (`.deb`)
