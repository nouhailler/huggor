← [Documentation](index.md)

# Fonctionnement hors connexion

Huggor n'a pas de mode « application installée fonctionnant sans réseau » (ce n'est pas une PWA avec Service Worker actif en dehors de Hugging Face Spaces — voir [Bien démarrer](getting-started.md#présentation-et-compatibilité)). Son « mode hors connexion » désigne une **dégradation gracieuse côté serveur** quand le Hugging Face Hub devient injoignable, pas un fonctionnement 100 % local de l'application elle-même (qui reste un serveur web à joindre).

## Détection

Une panne de connectivité (coupure réseau, DNS, timeout) est distinguée d'un **refus légitime** du Hub (404 introuvable, 403/401 authentification refusée, 429 limite de requêtes, dépôt protégé) : seule une vraie panne déclenche le mode hors connexion. Un refus du Hub prouve au contraire qu'il est joignable.

## Comportement

| Fonction | Hors connexion | En ligne | Synchronisation |
|---|---:|---:|---:|
| Recherche déjà effectuée | ✅ servie depuis le cache, même expiré | ✅ appel direct au Hub | — |
| Nouvelle recherche jamais faite | ❌ erreur explicite | ✅ | — |
| Fiche modèle déjà consultée | ✅ servie depuis le cache, même expiré | ✅ | — |
| Fiche modèle jamais consultée | ❌ erreur explicite | ✅ | — |
| Comparateur (modèles déjà consultés) | ✅ | ✅ | — |
| Favoris | ✅ toujours (100 % local) | ✅ | — |
| Analytics / tendances | ⚠️ dépend du cache déjà chargé, pas de secours dédié | ✅ | — |
| Hardware (calculateur) | ✅ toujours (aucun réseau requis) | ✅ | — |

Il n'y a aucune synchronisation multi-appareil ni file d'attente d'opérations différées : Huggor ne synchronise rien entre plusieurs installations (§20 de la spec ne s'applique pas à ce projet).

## Indicateur visuel

Quand une donnée est servie depuis le cache à cause d'une panne, le message de statut de l'onglet concerné (Recherche, Détails, Comparateur) commence par :

> 🟠 **Mode hors connexion** — …

## Retour en ligne

L'état repasse automatiquement en ligne dès qu'un appel réseau réussit à nouveau — aucune action manuelle n'est nécessaire.

## Limites

- Une recherche, une fiche ou une comparaison **jamais consultées avant la panne** ne peuvent pas être servies (rien à mettre en secours) : une erreur explicite s'affiche.
- Les Favoris fonctionnent toujours sans réseau car ils sont purement locaux — ils ne dépendent d'aucun mécanisme de secours.
