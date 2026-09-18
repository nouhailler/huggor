← [Documentation](index.md)

# Versions

Un seul tag Git existe à ce jour : `v0.1.0`. Le développement s'est poursuivi sur `main` après ce tag sans nouvelle version taguée — cette page documente donc l'ensemble des changements réels observés dans l'historique Git jusqu'à aujourd'hui, sous cette même version. **Recommandation** : tagger une nouvelle version (ex. `v0.2.0`) pour refléter l'ampleur des ajouts depuis `v0.1.0`.

# Version 0.1.0

Date de première publication du paquet Debian : 2026-09-14. Développement continu documenté ci-dessous jusqu'au 2026-09-17.

## Nouveautés

- Accès au Hub, cache local, recherche par mot-clé/domaine/tâche/langue/licence
- Onglet 🎯 Mon usage (recherche par objectif croisée avec RAM/VRAM)
- Fiche technique complète : identité, architecture, quantification, compatibilités
- Model Advisor (verdict RAM/VRAM), calculateur de ressources (onglet 💻 Hardware)
- Huggor Score (composite /100, 9 composantes toujours détaillées)
- Détection de quantification et recherche de variantes déjà quantifiées
- Recommandation de « Modèles similaires »
- Comparateur décisionnel de 2 à 4 modèles avec recommandation motivée
- Onglet ⭐ Favoris : collections, tags, statut, note, dernier test, commentaire
- Bouton « ⭐ Pin » depuis Mon usage vers les Favoris
- Onglet 📈 Analytics : Observatoire du Hub (tendances curatées, détection de croissance « Rising models »)
- Gestion du cache industrialisée par domaine, avec purge ciblée et actualisation forcée
- Mode hors connexion : dégradation gracieuse quand le Hub devient injoignable
- Menu hamburger catégorisé pour la navigation mobile (< 768px)
- Pré-remplissage du champ de recherche avec « Gemma » et recherche déclenchable par la touche Entrée
- Paquet d'installation Debian/Ubuntu (`.deb`)
- Configuration de déploiement pour Hugging Face Spaces et pour Render

## Corrections

- `JsonCache.get()` supprimait une entrée expirée avant que le secours hors connexion (`get_allow_stale`) ait pu s'en servir ; le secours est désormais capturé avant cette suppression.
- Le champ de recherche ne déclenchait pas la soumission par la touche Entrée faute de `max_lines` explicitement défini (condition interne de Gradio non satisfaite) ; corrigé en fixant `max_lines=1`.
- Un bug réel de détection de précision (`float16` détecté à tort comme sous-chaîne de `bfloat16`) a été corrigé par une expression régulière stricte dans [`src/model_analysis.py`](../src/model_analysis.py).

## Changements de paramètres

- Le champ « Mot-clé » de l'onglet Recherche a changé de valeur par défaut : vide → `Gemma`.

## Changements de données

- Ajout du domaine de cache « 🧪 Benchmarks » (vide, réservé pour la future fonctionnalité de test d'inférence — aucune donnée n'y est stockée à ce jour).

## Documentation mise à jour

- Cette documentation (`/docs`) a été créée dans son intégralité à cette version, à partir du code réel, des tests et du README existant.
