# DOCUMENTATION_SPEC.md

# Spécification du moteur documentaire commun pour les applications PWA

- Version de la spécification : 1.2.0 (adaptée Claude Code ; convention d'affichage en accordéons)
- Statut : OBLIGATOIRE
- Public cible : utilisateurs finaux, administrateurs, développeurs
- Projet : Nutritor

Ce fichier est la **source de vérité** de la documentation du projet. Il est
lu et appliqué par Claude Code. Il est versionné avec le code (voir §35).

---

# 0. COMMENT CLAUDE CODE UTILISE CE FICHIER

Claude Code s'appuie sur ce document via trois mécanismes complémentaires :

- **`CLAUDE.md`** — le fichier de contexte projet référence cette spec pour
  que la règle « toute fonctionnalité visible doit être documentée » soit
  active à chaque session. Ajoute-y une ligne du type :
  `> Documentation : suivre DOCUMENTATION_SPEC.md. Une tâche n'est "done" que si la doc est à jour.`
- **Commande `/doc`** — une commande personnelle (`~/.claude/commands/doc.md`)
  déclenche explicitement la génération, la mise à jour ou l'audit de la
  documentation en appliquant cette spec.
- **Sous-agent d'audit** — l'audit de couverture (§38) peut être délégué à un
  sous-agent en lecture seule pour ne pas polluer le contexte principal.

Cette spec **décrit le standard** ; elle ne remplace pas la lecture du code
réel. Voir §41 (Priorité des sources).

---

# 1. OBJECTIF

Cette spécification définit les règles obligatoires permettant de créer,
maintenir et publier une documentation complète pour l'application.

La documentation est une **partie intégrante du produit**. Toute
fonctionnalité ajoutée, modifiée ou supprimée doit entraîner la vérification
et, si nécessaire, la mise à jour de la documentation correspondante. La
documentation n'est jamais optionnelle ni secondaire.

OBJECTIF PRINCIPAL :

> Toute fonctionnalité visible ou utilisable dans l'application doit être documentée.

La documentation doit couvrir : l'installation ; le premier lancement ; la
navigation ; toutes les fonctionnalités ; tous les écrans ; tous les
paramètres ; toutes les permissions ; les données utilisées ; le
fonctionnement hors connexion ; la synchronisation ; les erreurs ; le
dépannage ; la FAQ ; la confidentialité ; les informations légales ; les
versions ; les limites connues ; les procédures de support.

---

# 2. PRINCIPE FONDAMENTAL

Le code source et la documentation doivent rester cohérents.

Avant de considérer une fonctionnalité comme terminée, vérifier
systématiquement :

1. La fonctionnalité existe-t-elle dans le code ?
2. Est-elle accessible à l'utilisateur ?
3. Est-elle documentée ?
4. Ses paramètres sont-ils documentés ?
5. Ses permissions sont-elles documentées ?
6. Ses erreurs possibles sont-elles documentées ?
7. Son comportement hors connexion est-il documenté ?
8. Son comportement avec/sans réseau est-il documenté ?
9. Ses impacts sur les données sont-ils documentés ?
10. La FAQ ou le dépannage doivent-ils être mis à jour ?

Si une réponse est « non », compléter la documentation avant de considérer la
tâche comme terminée.

---

# 3. ARCHITECTURE DU MOTEUR DOCUMENTAIRE

Créer une documentation web statique, responsive et optimisée pour mobile.

Architecture recommandée :

```
/docs
    /index
    /getting-started
    /guide
    /features
    /settings
    /permissions
    /data
    /offline
    /troubleshooting
    /faq
    /reference
    /versions
    /legal
    /support
```

La structure technique exacte peut être adaptée au framework du projet. Ne pas
imposer inutilement un framework spécifique si le projet dispose déjà d'une
infrastructure documentaire compatible.

---

# 4. TECHNOLOGIE

Analyser le projet existant avant toute modification.

Si le projet possède déjà un framework web, un générateur de site statique, un
système Markdown, un routing, un moteur de recherche ou une architecture de
composants : réutiliser prioritairement l'existant.

Ne pas introduire une nouvelle technologie uniquement pour la documentation si
cela augmente inutilement la complexité.

La documentation doit pouvoir être générée, construite, testée, déployée et
versionnée avec Git.

---

# 5. PRINCIPES UX

La documentation est conçue en priorité pour un utilisateur sur smartphone.

Elle doit être : responsive ; rapide ; lisible ; accessible ; utilisable au
doigt ; compatible petits écrans ; compatible mode sombre si l'application le
supporte ; navigable sans connaissance technique.

Navigation à privilégier : menu principal ; fil d'Ariane ; table des matières ;
recherche ; navigation précédent/suivant ; liens internes ; bouton retour ;
accès rapide au dépannage ; accès rapide à la FAQ.

## Présentation des chapitres et sous-chapitres (accordéons)

Le sommaire et la navigation présentent la documentation par **chapitres
repliables (accordéons)** :

- Chaque **chapitre** est une ligne cliquable qui se déplie/replie, avec : une
  icône, le titre du chapitre et un **compteur** du nombre d'éléments qu'il
  contient. Un chevron indique l'état (déplié/replié).
- Les **sous-chapitres** apparaissent au dépliement, **indentés vers la droite**
  et signalés par un filet vertical à gauche, pour matérialiser la hiérarchie.
- Par défaut, les chapitres sont repliés (hormis, éventuellement, le premier).
  L'accordéon peut ouvrir un seul chapitre à la fois ou plusieurs ; le
  comportement doit rester cohérent dans toute la documentation.
- Sur mobile, l'accordéon évite le défilement infini : l'utilisateur ne déplie
  que ce qui l'intéresse. Les cibles tactiles restent suffisamment hautes pour
  être utilisables au doigt.
- L'état déplié/replié ne casse pas l'accès direct : une page de sous-chapitre
  reste accessible et partageable par son URL, indépendamment de l'accordéon
  (voir §45, §46).

Cette convention est **indépendante du framework** : elle décrit le comportement
et la hiérarchie visuelle attendus, pas une implémentation CSS particulière. Elle
respecte les règles d'accessibilité de la §44 (navigation clavier, état annoncé
aux lecteurs d'écran, contraste, structure de titres correcte).

---

# 6. PAGE D'ACCUEIL

Créer une page d'accueil documentaire affichant :

- **Nom de l'application** : [NOM]
- **Description** : description courte de l'application
- **Version** : version actuelle de l'application
- **Documentation** : date de dernière mise à jour
- **Accès rapides** :
  - 🚀 Commencer
  - 📖 Guide utilisateur
  - 🧩 Fonctionnalités
  - ⚙️ Paramètres
  - 🔐 Données et confidentialité
  - 🛠️ Dépannage
  - ❓ FAQ
  - 📘 Référence
  - 🔄 Versions
  - ⚖️ Informations légales
  - 📩 Support

---

# 7. TABLE DES MATIÈRES GLOBALE

Créer automatiquement une table des matières. Structure minimale :

1. Bien démarrer
2. Comprendre l'application
3. Guide utilisateur
4. Fonctionnalités
5. Paramètres
6. Permissions
7. Données et confidentialité
8. Fonctionnement hors connexion
9. Synchronisation
10. Dépannage
11. FAQ
12. Référence
13. Versions
14. Informations légales
15. Support

Cette table doit être générée à partir des pages réellement présentes. Ne
jamais afficher de liens vers des pages inexistantes.

Elle est présentée en **chapitres repliables (accordéons)** avec sous-chapitres
indentés — voir la convention d'affichage en §5.

---

# 8. BIEN DÉMARRER

Créer obligatoirement `/getting-started/`. Contenu minimal : présentation ;
installation PWA ; compatibilité ; premier lancement ; configuration initiale ;
permissions initiales ; première utilisation ; désinstallation ; mise à jour.

---

# 9. INSTALLATION PWA

Documenter seulement les plateformes pertinentes.

## Android

Installation ; ajout à l'écran d'accueil ; lancement ; désinstallation ;
gestion des permissions.

## iOS

Safari ; ajout à l'écran d'accueil ; fonctionnement PWA ; limitations
éventuelles.

## Desktop (si applicable)

Chrome ; Edge ; Firefox ; autres navigateurs supportés.

Ne documenter que les plateformes réellement supportées par l'application.

---

# 10. PREMIER LANCEMENT

Documenter précisément le parcours utilisateur. Exemple :

```
Premier lancement
    ↓
Écran de bienvenue
    ↓
Présentation
    ↓
Consentements
    ↓
Permissions
    ↓
Configuration
    ↓
Écran principal
```

Pour chaque étape, préciser : ce qui est affiché ; ce que l'utilisateur doit
faire ; les options disponibles ; ce qui se passe en cas de refus ; si l'étape
peut être ignorée ; comment revenir sur ce choix ultérieurement.

---

# 11. GUIDE UTILISATEUR

Créer `/guide/`. Chaque écran important a sa propre documentation. Pour chaque
écran documenter : **Nom** (exact, tel qu'affiché) ; **Objectif** ; **Accès** ;
**Éléments de l'interface** (boutons, menus, champs, informations) ;
**Actions** possibles ; **Résultats** de chaque action ; **Cas particuliers** ;
**Erreurs** possibles ; **Navigation** (où aller ensuite).

---

# 12. DOCUMENTATION DES FONCTIONNALITÉS

Toute fonctionnalité utilisateur doit être documentée. Créer `/features/`,
avec une page par fonctionnalité. Structure obligatoire :

```
# [Nom de la fonctionnalité]

## Description            (claire et non technique)
## Objectif               (pourquoi elle existe)
## Prérequis              (permissions, connexion, configuration)
## Comment l'utiliser     (procédure étape par étape)
## Options
## Paramètres associés
## Données utilisées
## Résultat
## Fonctionnement hors connexion
## Fonctionnement en ligne
## Limites
## Erreurs possibles
## Dépannage             (lien vers les procédures correspondantes)
## FAQ                   (questions fréquentes associées)
```

---

# 13. CAPTURES D'ÉCRAN

Utiliser des captures quand cela améliore significativement la compréhension.
Les captures doivent correspondre à la version actuelle, être lisibles sur
mobile, ne pas exposer de données personnelles, utiliser des données fictives
si nécessaire.

Pour les procédures complexes : captures annotées ; étapes numérotées ; GIF ;
courtes vidéos si réellement nécessaires. Ne pas multiplier les images
inutilement.

---

# 14. PARAMÈTRES

Créer `/settings/`. Documenter TOUS les paramètres exposés à l'utilisateur.
Pour chaque paramètre : **Nom** (exact) ; **Identifiant interne** (si
disponible) ; **Description** ; **Type** (booléen, texte, nombre, sélection,
liste, date, durée…) ; **Valeur par défaut** ; **Valeurs possibles** ;
**Effet** ; **Application** (immédiate / au prochain lancement / après
synchronisation) ; **Stockage** (où la valeur est stockée, si pertinent) ;
**Interactions** (autres paramètres influencés) ; **Réinitialisation**.

---

# 15. RÉFÉRENCE DES PARAMÈTRES

Créer `/reference/settings/`. Format recommandé :

| Paramètre | Type | Défaut | Valeurs | Description |
|---|---|---|---|---|

Cette page est maintenue automatiquement. Tout nouveau paramètre doit y
apparaître.

---

# 16. PERMISSIONS

Créer `/permissions/`. Documenter toutes les permissions utilisées
(localisation, caméra, microphone, notifications, stockage, fichiers,
Bluetooth, capteurs, contacts, etc.). Pour chaque permission : **Permission**
(nom) ; **Pourquoi** l'application en a besoin ; **Quand** elle est demandée ;
**Obligatoire ?** ; **Si l'utilisateur refuse** (comportement) ; **Comment
réactiver ?** (Android / iOS / navigateur).

---

# 17. DONNÉES

Créer `/data/`. Documenter les données utilisées. Pour chaque catégorie : nom ;
origine ; finalité ; stockage ; durée ; transmission ; suppression ; export ;
partage éventuel. Tableau récapitulatif :

| Donnée | Origine | Stockage | Transmission | Finalité |
|---|---|---|---|---|

Ne jamais inventer d'information sur la collecte ou le traitement. Sources :
code, configuration, documents juridiques.

---

# 18. STOCKAGE LOCAL

Documenter précisément les données stockées localement : localStorage ;
IndexedDB ; Cache Storage ; Service Worker ; fichiers locaux ; autres. Expliquer
quelles données sont conservées ; quand elles sont supprimées ; ce qui se passe
à la désinstallation ; à l'effacement des données navigateur ; si les données
peuvent être exportées.

---

# 19. MODE HORS CONNEXION

Créer `/offline/`. Documenter : fonctionnalités disponibles offline ;
fonctionnalités nécessitant Internet ; données mises en cache ; opérations
différées ; synchronisation future ; comportement en cas de perte de réseau ;
comportement après reconnexion. Tableau :

| Fonction | Offline | Online | Synchronisation |
|---|---:|---:|---:|

---

# 20. SYNCHRONISATION

Si l'application synchronise, documenter : déclenchement ; fréquence ;
synchronisation automatique / manuelle ; file d'attente ; erreurs ; conflits ;
résolution des conflits ; état de synchronisation. Expliquer le processus avec
un schéma simple.

---

# 21. DÉPANNAGE

Créer `/troubleshooting/`, un article par problème. Structure :

```
# [Problème]

## Symptôme                        (ce que voit l'utilisateur)
## Causes possibles
## Diagnostic                      (étapes pour identifier la cause)
## Solution                        (procédure)
## Si le problème persiste
## Informations à fournir au support
```

Informations utiles au support : version ; appareil ; système ; navigateur ;
message d'erreur ; état réseau.

---

# 22. FAQ

Créer `/faq/`. Formuler les questions comme les utilisateurs les poseraient :

- Comment installer l'application ?
- Pourquoi l'application demande-t-elle ma localisation ?
- Pourquoi le GPS ne fonctionne-t-il pas ?
- Puis-je utiliser l'application sans Internet ?
- Où sont mes données ?
- Comment supprimer mes données ?
- Comment exporter mes données ?
- Comment réinitialiser l'application ?

Chaque réponse reste concise et propose un lien vers la documentation détaillée.

---

# 23. RÉFÉRENCE

Créer `/reference/`. Contenu minimal : paramètres ; permissions ; erreurs ;
formats de données ; statuts ; limites ; compatibilité ; glossaire.

---

# 24. CODES ET ERREURS

Créer `/reference/errors/`. Format :

| Code | Message | Signification | Solution |
|---|---|---|---|

Si l'application utilise des codes d'erreur, les détecter automatiquement dans
le code source quand c'est possible. Ne jamais inventer de codes.

---

# 25. GLOSSAIRE

Créer `/reference/glossary/`. Pour chaque terme : **Terme** (définition
simple) ; **Utilisation dans l'application** (explication spécifique au projet).
Éviter le jargon inutile.

---

# 26. COMPATIBILITÉ

Créer `/reference/compatibility/`. Documenter : Android ; iOS ; navigateurs ;
versions minimales ; fonctionnalités limitées ; restrictions connues.

Ne déclarer compatible que ce qui a été réellement vérifié ou explicitement
supporté.

---

# 27. LIMITES CONNUES

Créer `/reference/limitations/`. Documenter honnêtement : limites techniques ;
fonctionnelles ; navigateurs ; PWA ; GPS ; offline ; stockage ; APIs. Ne
jamais masquer une limitation connue.

---

# 28. VERSIONS

Créer `/versions/`. Documenter chaque version :

```
# Version X.Y.Z

Date :

## Nouveautés
## Améliorations
## Corrections
## Changements
## Changements incompatibles
## Modifications de paramètres
## Modifications de données
## Modifications de confidentialité
## Documentation mise à jour
```

---

# 29. CHANGELOG

Le changelog reste synchronisé avec le projet. Lors d'une modification
fonctionnelle importante : identifier la version concernée ; mettre à jour le
changelog ; mettre à jour la documentation ; vérifier les captures ; vérifier
les paramètres ; vérifier la FAQ ; vérifier le dépannage.

---

# 30. INFORMATIONS LÉGALES

Créer `/legal/`. Prévoir les liens vers : mentions légales ; politique de
confidentialité ; conditions d'utilisation ; politique cookies si applicable ;
licences ; crédits ; gestion des consentements.

**Ne jamais générer de contenu juridique définitif sans validation humaine.**
Le contenu juridique doit être explicitement identifié comme tel.

---

# 31. SUPPORT

Créer `/support/`. Contenu : comment signaler un problème ; comment demander de
l'aide ; informations nécessaires ; version de l'application ; appareil ; OS ;
navigateur ; étapes permettant de reproduire le problème. Si un système de
contact existe, ajouter le lien correspondant.

---

# 32. RECHERCHE

La documentation dispose d'une recherche globale indexant : titres ;
sous-titres ; texte ; paramètres ; fonctionnalités ; erreurs ; FAQ ; glossaire.
Les résultats affichent : titre ; catégorie ; extrait ; lien. La recherche est
optimisée pour mobile.

---

# 33. NAVIGATION

Chaque page dispose : d'un menu principal ; d'un fil d'Ariane ; d'une table des
matières locale si nécessaire ; d'un lien précédent ; d'un lien suivant ; d'un
accès au sommaire ; d'un accès à la recherche.

---

# 34. LIEN DEPUIS L'APPLICATION

Ajouter dans l'application un accès clair à la documentation. Emplacements
recommandés : Paramètres ; Aide ; À propos ; écran de première utilisation.
Libellé recommandé : « 📚 Documentation » ou « ❓ Aide & documentation ». Le
lien ouvre la documentation dans un contexte adapté au mobile.

---

# 35. VERSIONNAGE DE LA DOCUMENTATION

La documentation est versionnée avec Git. Elle indique : version de
l'application ; version de la documentation ; date de mise à jour. Si plusieurs
versions de l'application sont maintenues, prévoir `/docs/versions/`. Ne
supprimer aucune documentation historique sans raison explicite.

---

# 36. DOCUMENTATION MULTI-APPLICATIONS

Le moteur documentaire est conçu pour être réutilisable. Si plusieurs
applications l'utilisent :

```
/documentation
    /apps
        /application-a
        /application-b
        /application-c
    /common
```

La partie `/common` peut contenir : installation PWA ; fonctionnement PWA ;
permissions générales ; confidentialité générale ; FAQ générale ; guide
Android ; guide iOS. Chaque application dispose ensuite de sa propre
documentation fonctionnelle.

---

# 37. DÉTECTION AUTOMATIQUE DES ÉLÉMENTS À DOCUMENTER

À chaque tâche importante, analyser le projet pour détecter : nouveaux écrans ;
routes ; boutons ; fonctionnalités ; paramètres ; permissions ; APIs ; données ;
erreurs ; variables de configuration ; comportements offline ; traitements
réseau.

Comparer ces éléments à la documentation existante et produire :

```
## Documentation potentiellement obsolète
- Fonctionnalité X
- Paramètre Y

## Documentation manquante
- Fonctionnalité Z
- Permission A
```

---

# 38. AUDIT DOCUMENTAIRE

Fournir un mécanisme de vérification de la couverture documentaire. L'audit
recherche : fonctionnalités non documentées ; paramètres non documentés ;
permissions non documentées ; erreurs non documentées ; pages manquantes ;
liens cassés ; images manquantes ; références obsolètes ; versions
incohérentes.

Résultat lisible, par exemple :

```
DOCUMENTATION AUDIT

Fonctionnalités : 18 / 18 documentées
Paramètres      : 24 / 24 documentés
Permissions     :  4 /  4 documentées
Erreurs         : 13 / 15 documentées
Liens           : 100 % valides

STATUT : ⚠️ DOCUMENTATION INCOMPLÈTE

Éléments manquants :
- ERR-014
- ERR-015
```

Sous Claude Code, cet audit peut être délégué à un **sous-agent en lecture
seule** (`allowed-tools: Read, Grep, Glob`) pour ne pas encombrer le contexte
principal.

---

# 39. RÈGLE DE « DONE »

Une fonctionnalité n'est **pas** terminée si elle fonctionne mais que sa
documentation n'est pas à jour. Une tâche fonctionnelle est terminée uniquement
lorsque :

- [ ] Code terminé
- [ ] Tests terminés
- [ ] UI terminée
- [ ] Paramètres documentés
- [ ] Permissions documentées
- [ ] Données documentées
- [ ] Fonctionnement offline documenté
- [ ] Erreurs documentées
- [ ] FAQ vérifiée
- [ ] Dépannage vérifié
- [ ] Captures mises à jour si nécessaire
- [ ] Changelog mis à jour si nécessaire
- [ ] Audit documentaire effectué

---

# 40. RÈGLE POUR CLAUDE CODE

Lorsqu'une demande utilisateur modifie une fonctionnalité, **ne pas se limiter
au code**. Toujours déterminer :

1. Quelles pages de documentation sont concernées ?
2. Quels paramètres sont concernés ?
3. Quelles permissions sont concernées ?
4. Quelles données sont concernées ?
5. Quels problèmes de dépannage sont concernés ?
6. Quelle FAQ doit être modifiée ?
7. Le changelog doit-il être modifié ?
8. Les captures doivent-elles être actualisées ?

Puis effectuer les modifications nécessaires.

Application concrète dans Claude Code :

- **Contexte permanent** — la règle « pas de "done" sans doc » vit dans
  `CLAUDE.md`, qui référence ce fichier. Elle est donc active à chaque session
  sans avoir à la rappeler.
- **Plan mode** — pour une modification fonctionnelle non triviale, présenter un
  plan qui inclut explicitement les fichiers de doc à toucher *avant*
  d'exécuter.
- **Vérification finale** — avant de conclure une tâche, exécuter (ou proposer
  d'exécuter) l'audit de couverture (§38) et cocher la check-list de « done »
  (§39).
- **Ne jamais annoncer une tâche terminée** tant que la doc correspondante n'a
  pas été vérifiée et, si besoin, mise à jour.

---

# 41. PRIORITÉ DES SOURCES

Pour produire la documentation, utiliser dans cet ordre :

1. Code source réel
2. Configuration réelle
3. Tests
4. Schémas de données
5. APIs réellement utilisées
6. Interface utilisateur réelle
7. Documentation existante
8. Informations fournies explicitement par le développeur

**Ne jamais inventer une fonctionnalité. Ne jamais documenter un comportement
supposé.** Si le comportement n'est pas déterminable :

> À vérifier

et signaler le point au développeur.

---

# 42. QUALITÉ RÉDACTIONNELLE

La documentation doit être : claire ; précise ; factuelle ; accessible ;
structurée ; cohérente ; sans jargon inutile. Phrases courtes. Listes et
tableaux quand ils améliorent la compréhension. Éviter les paragraphes
inutilement longs.

---

# 43. NIVEAUX DE LECTURE

- **Niveau 1 — Utilisateur** : explications simples.
- **Niveau 2 — Utilisateur avancé** : paramètres, limites, fonctionnement
  détaillé.
- **Niveau 3 — Technique** : informations techniques utiles quand nécessaires.

Ne pas exposer inutilement des détails techniques à un utilisateur normal.

---

# 44. ACCESSIBILITÉ

Respecter autant que possible les bonnes pratiques : contraste suffisant ;
taille de texte lisible ; navigation clavier ; textes alternatifs ; structure
correcte des titres ; liens explicites ; éléments interactifs suffisamment
grands ; compatibilité lecteurs d'écran.

---

# 45. SEO

Si la documentation est publique, chaque page importante dispose de : titre ;
description ; URL stable ; H1 unique ; structure H2/H3 cohérente ; métadonnées
pertinentes. URLs lisibles, par exemple :

```
/docs/features/gps/
/docs/settings/notifications/
/docs/troubleshooting/gps-not-working/
```

---

# 46. LIENS INTERNES

Créer des liens entre les contenus. Exemple :

```
Fonctionnalité GPS
    ↓
Paramètres GPS
    ↓
Permission localisation
    ↓
Dépannage GPS
    ↓
FAQ GPS
```

La documentation fonctionne comme une base de connaissances interconnectée.

---

# 47. LIENS CASSÉS

Mettre en place un contrôle automatique des liens. Le build ou l'audit doit
détecter : pages inexistantes ; ancres inexistantes ; images manquantes ;
ressources supprimées. Une documentation avec des liens cassés est considérée
comme incorrecte.

---

# 48. IMAGES ET CAPTURES

Organiser les images :

```
/docs/assets/images/
/docs/assets/screenshots/
/docs/assets/diagrams/
```

Nommer les fichiers clairement : `settings-notifications.png`,
`gps-recording.png`, `first-launch.png`. Ne jamais utiliser de captures
contenant des données personnelles réelles.

---

# 49. DIAGRAMMES

Utiliser des diagrammes quand cela facilite la compréhension : architecture ;
synchronisation ; workflow ; cycle de vie ; données ; permissions ;
offline/online. Privilégier des diagrammes simples.

---

# 50. DONNÉES SENSIBLES

Ne jamais inclure dans la documentation : mots de passe ; tokens ; clés API ;
secrets ; identifiants personnels ; données utilisateur réelles ; fichiers de
configuration contenant des secrets.

Avant publication, effectuer si possible un contrôle automatique recherchant
notamment : `API_KEY`, `TOKEN`, `SECRET`, `PASSWORD`, `PRIVATE_KEY`.

---

# 51. GÉNÉRATION AUTOMATIQUE

Quand c'est techniquement possible, générer automatiquement : version de
l'application ; date de build ; liste des paramètres ; liste des permissions ;
liste des routes ; liste des fonctionnalités ; changelog ; index documentaire.
Toute génération automatique utilise les données réellement présentes dans le
projet.

---

# 52. BUILD

Le pipeline de documentation doit pouvoir : vérifier les fichiers ; générer la
documentation ; vérifier les liens ; vérifier les images ; vérifier la
cohérence des versions ; exécuter l'audit ; générer le site ; publier le site.
Si une erreur critique est détectée, le build doit échouer.

---

# 53. INTÉGRATION CONTINUE

Si le projet utilise CI/CD, ajouter un contrôle documentaire :

```text
git push
   ↓
tests
   ↓
build
   ↓
documentation audit
   ↓
link checker
   ↓
build documentation
   ↓
deployment
```

Sous Claude Code, ce contrôle peut aussi être déclenché localement via un
**hook** `PreToolUse`/`Stop` ou via la commande `/doc audit` avant un commit.
