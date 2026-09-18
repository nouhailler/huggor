← [Documentation](index.md)

# Versions

# Non publié (postérieur à v0.3.0)

- Visite guidée (onboarding) en 5 étapes, accessible à la demande depuis l'écran « ⚙️ Paramètres ». Mémorise sa complétion localement dans le navigateur (`localStorage`, clé `onboarding_completed`), indépendamment de l'avertissement légal. Voir [Guide → Visite guidée](guide.md#visite-guidée-onboarding).
- Nouvel écran « ⚙️ Paramètres » (menu hamburger), regroupant les réglages généraux de l'application indépendants d'un onglet précis — pour l'instant, uniquement « 🧭 Revoir la visite guidée » (déplacé depuis l'écran « À propos », qui ne le propose plus).
- Documentation de l'écran « ℹ️ À propos » (ajouté en v0.3.0 mais jamais documenté, sa doc ayant été volontairement différée à ce moment).
- Correction : sur Render, l'écran « À propos » affichait un hash brut au lieu d'une version et « à renseigner » pour les liens dépôt/issues, à cause d'un clone Git superficiel sans tags ni remote côté Render. `src/app_info.py` utilise désormais les variables `RENDER_GIT_*` fournies par Render en priorité, avant de retomber sur Git local puis sur « — ». `render.yaml` déclare aussi `PYTHONUNBUFFERED=1`, sans quoi les logs de démarrage Python n'apparaissaient pas de façon fiable sur Render.
- Correction : la visite guidée s'affichait initialement de façon automatique juste après l'acceptation de l'avertissement légal ; un chargement lent (Render en sortie de veille, notamment) laissait alors le bouton « Suivant » visuellement figé sans aucun retour, perçu comme cassé. L'affichage automatique a été retiré — la visite reste entièrement fonctionnelle, mais uniquement à la demande depuis « ⚙️ Paramètres ».

# Version 0.3.0

Date : 2026-09-18.

## Nouveautés

- Avertissement légal de premier lancement + page « ⚖️ Mentions légales » accessible en permanence depuis le pied de page. Contenu centralisé dans `src/legal_notice.py`, acceptation mémorisée localement dans le navigateur (`localStorage`), aucune donnée transmise au serveur. Voir [Informations légales](legal.md).
- Écran « ℹ️ À propos » tout en bas du menu hamburger : version et commit dérivés de Git au démarrage (jamais codés en dur), liens auteur/site/portfolio/dépôt/signaler un bug (dérivés du remote Git réel), bouton support ouvrant un brouillon d'e-mail avec diagnostic, crédits des licences des dépendances open source. Voir [`src/app_info.py`](../src/app_info.py).
- Capture d'écran ajoutée au README.

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
