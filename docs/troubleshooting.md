← [Documentation](index.md)

# Dépannage

Informations utiles à fournir au support pour tout problème (voir [Support](support.md)) : version (0.1.0, ou commit Git), mode d'accès (local / Hugging Face Space / Render), navigateur, message d'erreur exact, état de la connexion réseau.

## Aucun résultat ne s'affiche

**Symptôme** : après une recherche, le message « Aucun modèle ne correspond à ces critères. » apparaît.
**Causes possibles** : filtres trop restrictifs (domaine + tâche précise + langue + licence combinés), plage de paramètres incohérente (minimum > maximum), mot-clé trop spécifique.
**Diagnostic** : retirer les filtres un par un en commençant par la tâche précise (c'est le seul filtre qui restreint réellement les résultats côté Hub, voir [Recherche par domaine et tâche](features.md#recherche-par-domaine-et-tâche)).
**Solution** : élargir un filtre à la fois, ou cliquer « Réinitialiser » pour repartir des valeurs par défaut.
**Si le problème persiste** : vérifier directement sur [huggingface.co/models](https://huggingface.co/models) avec les mêmes critères pour confirmer qu'il existe des résultats côté Hub.

## Le Hub refuse l'authentification

**Symptôme** : message « Authentification Hugging Face refusée. Vérifiez votre token. » ou « Ce modèle est protégé. Acceptez ses conditions sur le Hub et fournissez un token autorisé. »
**Causes possibles** : token absent, expiré, révoqué, ou sans les droits nécessaires ; conditions d'accès au dépôt (« gated ») non acceptées sur le Hub.
**Diagnostic** : vérifier le bandeau d'en-tête (« Accès public » signifie qu'aucun token n'est détecté).
**Solution** : configurer `HF_TOKEN` — voir [Permissions](permissions.md) — et, pour un dépôt protégé, accepter ses conditions sur sa page Hugging Face avant de réessayer.
**Si le problème persiste** : régénérer un token sur [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) avec les droits appropriés.

## Modèle introuvable

**Symptôme** : message « Le modèle « X » est introuvable ou inaccessible. »
**Causes possibles** : identifiant mal orthographié, modèle supprimé ou renommé, modèle privé sans droit d'accès.
**Diagnostic** : vérifier l'identifiant exact sur le Hub (format `auteur/nom-du-modele`).
**Solution** : corriger l'identifiant ou vérifier les droits d'accès si le dépôt est privé.

## L'application met du temps à répondre au premier chargement

**Symptôme** : la page reste sur « Chargement… » plusieurs dizaines de secondes lors d'un déploiement Hugging Face Spaces ou Render.
**Causes possibles** : le service gratuit était en veille après inactivité (comportement normal des tiers gratuits de ces plateformes) et redémarre à la demande.
**Diagnostic** : recharger la page après 30 à 50 secondes.
**Solution** : patienter puis rafraîchir ; ce n'est pas un dysfonctionnement mais un comportement attendu du tier gratuit — voir le [README](../README.md#déploiement-sur-render).
**Si le problème persiste** : vérifier les logs de déploiement de la plateforme (Render : `hf spaces logs` n'est pas applicable ici, utiliser le tableau de bord Render).

## Le bandeau « Mode hors connexion » apparaît de façon inattendue

**Symptôme** : le message « 🟠 Mode hors connexion » s'affiche alors que la connexion Internet semble fonctionner.
**Causes possibles** : le Hugging Face Hub lui-même est temporairement indisponible (panne côté Hub), ou un pare-feu/proxy bloque spécifiquement les requêtes vers `huggingface.co`.
**Diagnostic** : vérifier [status.huggingface.co](https://status.huggingface.co) ou l'accès direct à `https://huggingface.co` depuis le même réseau.
**Solution** : attendre le rétablissement ; l'application repasse en ligne automatiquement dès qu'un appel réussit — voir [Mode hors connexion](offline.md).

## Le radar du Comparateur ne s'affiche pas

**Symptôme** : le tableau de comparaison s'affiche mais pas le radar, avec le message « Radar indisponible : moins de trois quantités communes renseignées. »
**Causes possibles** : les modèles comparés ne déclarent pas assez de valeurs numériques communes (paramètres, contexte, etc.).
**Solution** : ce n'est pas une erreur — comparer des modèles qui renseignent davantage de métadonnées communes fait apparaître le radar.
