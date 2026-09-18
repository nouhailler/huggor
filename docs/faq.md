← [Documentation](index.md)

# FAQ

**Comment installer l'application ?**
Il n'y a pas d'installation obligatoire : ouvrez le lien d'une instance déployée (Hugging Face Space ou Render) dans un navigateur. Pour une installation locale ou le paquet Debian, voir [Bien démarrer](getting-started.md#installation).

**Pourquoi l'application me demande-t-elle un token Hugging Face ?**
Elle ne le demande jamais de force : il est facultatif pour les modèles publics et n'est nécessaire que pour accéder à des ressources privées ou protégées. Voir [Permissions](permissions.md).

**Puis-je utiliser l'application sans Internet ?**
Non, l'application reste un service web qu'il faut joindre. En revanche, si le Hugging Face Hub devient injoignable après une utilisation, les recherches, fiches et comparaisons déjà consultées restent affichables depuis le cache local — voir [Mode hors connexion](offline.md).

**Où sont mes données ?**
Localement, sur la machine ou le serveur qui exécute l'application (`data/cache/`, `data/analytics/`, `data/favorites.json`). Rien n'est envoyé à un tiers autre que le Hugging Face Hub lui-même pour les requêtes de recherche. Voir [Données](data.md).

**Comment supprimer mes données ?**
Videz le cache depuis l'onglet Analytics (« 🗑 Vider le cache »), ou supprimez directement les fichiers `data/cache/`, `data/analytics/` et `data/favorites.json` sur le serveur qui héberge l'instance. Voir [Gestion du cache](features.md#gestion-du-cache).

**Comment exporter mes données ?**
`data/favorites.json` est un fichier JSON standard, copiable directement. Il n'existe pas de bouton d'export dans l'interface.

**Comment réinitialiser l'application ?**
Le bouton « Réinitialiser » de l'onglet Recherche remet les filtres à zéro. Pour repartir de zéro complètement (cache et favoris), voir « Comment supprimer mes données ? » ci-dessus.

**Le radar du Comparateur ou les tendances Analytics portent-ils sur tout le Hub ?**
Non. Le radar ne compare que les modèles sélectionnés, et les listes Analytics ne portent que sur l'échantillon chargé (jusqu'à 50 résultats) — voir [Limites connues](reference.md#limites-connues).

**Pourquoi l'onglet 🧪 Test n'affiche-t-il rien de fonctionnel ?**
Cette fonctionnalité n'est pas encore implémentée — voir [Limites connues](reference.md#limites-connues).
