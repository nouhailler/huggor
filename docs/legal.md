← [Documentation](index.md)

# Informations légales

> ⚠️ **Texte fourni par l'éditeur, à valider juridiquement.** Le contenu ci-dessous est implémenté et affiché dans l'application (bandeau de premier lancement + page permanente). Il a été rédigé à partir d'un texte type fourni par l'éditeur (commande `/mentions-legales`), pas rédigé par un professionnel du droit pour ce projet précis. §30 de [DOCUMENTATION_SPEC.md](../DOCUMENTATION_SPEC.md) reste applicable : une relecture juridique est recommandée avant de considérer ce texte comme définitif, en particulier sa qualification juridique (le contenu est exact sur ce que fait le code, sa portée légale n'est pas garantie).

## Où c'est affiché dans l'application

- **Premier lancement** : un bandeau (« ⚠️ Information importante ») s'affiche à la première visite d'un navigateur donné, avec un bouton **Voir les détails** (page complète, dans le même panneau) et **J'ai compris** (accepte et ferme).
- **En permanence** : lien **⚖️ Mentions légales** dans le pied de page de l'application, ouvrant directement la page complète — pas besoin d'attendre un premier lancement pour la consulter.

## Mécanisme technique

- **100 % côté client, rien envoyé au serveur** : l'acceptation est enregistrée dans le `localStorage` du navigateur (clé `legal_notice_acknowledged`, plus `legal_notice_acknowledged_version`), jamais transmise à l'application ni journalisée.
- **Ne réapparaît pas** une fois accepté sur ce navigateur, sauf effacement des données de site ou navigation privée (qui ne persiste pas `localStorage` entre les sessions).
- **Contenu centralisé** dans [`src/legal_notice.py`](../src/legal_notice.py) — un seul texte, rendu aux deux endroits (bandeau et page permanente), pour qu'une modification ne se fasse jamais qu'à un seul endroit.
- **Section GPS absente volontairement** : Huggor n'utilise aucune géolocalisation, donc la section « Précision de la localisation » prévue par le modèle type n'est pas incluse — vérifié dans [`tests/test_legal_notice.py`](../tests/test_legal_notice.py).
- **Pas de gestion d'historique/retour Android** : Gradio ne fait pas de routing côté client dans cette application, cette partie du modèle type ne s'applique donc pas ici (absence volontaire, pas un oubli).

## Contenu affiché (résumé structurel)

Huit sections, dans cet ordre : Avertissement, Limitation de responsabilité, Utilisation de l'application, Exactitude des informations, Dysfonctionnements et disponibilité, Données et résultats, Sources externes, Évolution de l'application — plus l'identité de l'éditeur et une clause de clôture. Le texte complet, verbatim, est visible directement dans l'application (lien « ⚖️ Mentions légales ») ou dans [`src/legal_notice.py`](../src/legal_notice.py).

## Identité de l'éditeur

| Champ | Valeur |
|---|---|
| Éditeur | Swinux |
| Adresse | Canton de Vaud, Suisse |
| Contact | contact@swinux.ch |
| Hébergement (déploiement actuel) | Render (render.com) |

## Ce qui reste hors de ce texte

- **Licence du projet** : aucun fichier `LICENSE` n'est présent dans le dépôt — la licence de Huggor lui-même n'est pas déterminée. **À décider par le développeur**, indépendamment de la limitation de responsabilité ci-dessus (deux sujets différents).
- **Politique de confidentialité** : non demandée, donc non créée par défaut (voir [Données](data.md) pour l'état des lieux factuel, non juridique, de ce qui est collecté et stocké). Si une politique de confidentialité formelle est souhaitée, elle doit être un document séparé, décrivant précisément ce que fait le code — pas un texte type.
- **Conditions d'utilisation (CGU)** formelles : inexistantes en tant que document séparé ; la clause de clôture de l'avertissement (« vous reconnaissez avoir pris connaissance... et acceptez les conditions d'utilisation applicables ») en tient lieu a minima.
- **Cookies** : l'application n'utilise ni cookie de tracking ni script tiers observé dans le code ; elle repose sur les mécanismes de session standards de Gradio (identifiant technique nécessaire au fonctionnement, pas à des fins de suivi).
- **Dépendances tierces principales** (voir [`requirements.txt`](../requirements.txt)) : `gradio`, `huggingface-hub`, `pandas`, `plotly`, `python-dotenv`, chacune sous sa propre licence open source — inventaire détaillé non produit à ce jour.

## Comment modifier ce texte

Voir [`CLAUDE.md`](../CLAUDE.md) pour la procédure (fichier à éditer, gestion de version, comment retester le premier lancement).

## Actions requises

- [ ] Relecture juridique du texte par un professionnel, avant publication à grande échelle.
- [ ] Décider d'une licence pour le projet.
- [ ] Politique de confidentialité formelle, si un jour souhaitée — document séparé, pas une section ajoutée ici.
