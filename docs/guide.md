← [Documentation](index.md)

# Guide utilisateur

Huit onglets composent l'application, plus un menu hamburger qui prend le relais sur petit écran. Chaque onglet est décrit ci-dessous : nom exact, objectif, éléments d'interface, actions possibles, résultats, cas particuliers, navigation.

## 🔍 Recherche

**Objectif** : trouver des modèles sur le Hugging Face Hub par mot-clé, domaine/tâche, langue et licence.

**Accès** : onglet par défaut à l'ouverture de l'application.

**Éléments d'interface** :
- Champ **Mot-clé** (pré-rempli avec « Gemma » par défaut)
- Menu **Domaine** (🧠 LLM, 👁️ Vision, 🖼️ Image, 🎙️ Audio, 🗣️ Speech, 🔤 Embeddings, 🌐 Multimodal, 🧩 Reranking, ou « Tous les domaines »)
- Menu **Tâche précise**, dont les choix dépendent du domaine sélectionné — seule la tâche précise filtre réellement les résultats côté Hub
- Menus **Langue**, **Licence**, **Trier par** (téléchargements, likes, date de création, pertinence)
- Accordéon **Paramètres avancés** : sliders Minimum/Maximum de paramètres (en milliards, 0 = pas de borne) et Nombre de résultats (5 à 100)
- Boutons **🔍 Rechercher** et **Réinitialiser**

**Actions** : taper un mot-clé puis appuyer sur **Entrée** (déclenche la recherche directement) ou cliquer **🔍 Rechercher**. Chaque résultat affiche un bouton **Voir détails →**.

**Résultat** : liste de cartes synthétiques (auteur, likes, téléchargements, paramètres, tâche, bibliothèque, tags) avec lien direct vers le Hub.

**Cas particuliers** : aucun résultat → message « Aucun modèle ne correspond à ces critères. ». Voir [Fonctionnalités → Recherche par domaine et tâche](features.md#recherche-par-domaine-et-tâche).

**Navigation** : « Voir détails → » ouvre directement l'onglet **📄 Détails** avec la fiche du modèle chargée.

## 🎯 Mon usage

**Objectif** : trouver des modèles compatibles avec sa machine, en partant d'un objectif (Chatbot, Coding, RAG, …) plutôt que du jargon Hugging Face.

**Éléments d'interface** :
- Cases à cocher **usages** (Chatbot, Coding, RAG, Embeddings, Traduction, Vision, Speech, Génération d'images)
- Champs **RAM (Go)** et **VRAM (Go)**
- Bouton **🎯 Rechercher les modèles compatibles**

**Actions** : cocher un ou plusieurs usages, renseigner RAM/VRAM (au moins un des deux requis, sinon rejet avant tout appel réseau), lancer la recherche.

**Résultat** : cartes de modèles compatibles avec verdict de précision/vitesse, chacune avec un bouton **⭐ Pin** pour ajouter directement aux favoris sans repasser par la fiche détaillée.

**Navigation** : bouton Pin → ajout direct aux [Favoris](#-favoris) ; sinon, comme pour Recherche, un lien mène à la fiche détaillée.

## 📄 Détails

**Objectif** : examiner en profondeur un modèle précis (identité, architecture, compatibilité, Model Card, fichiers).

**Éléments d'interface** :
- Champ **Identifiant du modèle** (`auteur/nom-du-modele`)
- Boutons **📄 Charger la fiche**, **⭐ Ajouter aux favoris**, **🔄 Actualiser depuis Hugging Face** (force un rechargement sans passer par le cache)
- Repère **⏱ Dernière mise à jour** (âge de l'entrée en cache)
- Sections : Identité, Architecture, [Huggor Score](features.md#huggor-score), Compatibilité, Précisions et quantifications, Versions quantifiées existantes, Modèles similaires, Model Advisor (verdict matériel), Recommandation de téléchargement, Model Card complète, inventaire des fichiers, arborescence, snippets de code (local et `InferenceClient`)

**Actions** : saisir un identifiant puis **Charger la fiche** ; le champ se pré-remplit automatiquement en venant de Recherche/Mon usage via « Voir détails ».

**Résultat** : « ✅ Fiche de **X** chargée. » suivi de toutes les sections ci-dessus.

**Erreurs possibles** : identifiant invalide, modèle introuvable, accès refusé (token requis) — voir [Référence → Codes et messages d'erreur](reference.md#codes-et-messages-derreur).

**Navigation** : « ⭐ Ajouter aux favoris » → visible ensuite dans l'onglet [Favoris](#-favoris).

## 💻 Hardware

**Objectif** : savoir, indépendamment d'un modèle précis, quelles précisions (FP32 à Q4_K_M) tiennent sur sa machine.

**Éléments d'interface** : champs **RAM (Go)** et **VRAM (Go)**.

**Résultat** : tableau des précisions supportées avec estimation de vitesse et de contexte, **présentée explicitement comme théorique** (reposant sur des repères génériques de bande passante mémoire, pas sur une mesure du GPU/CPU réellement installé).

**Limites** : ces chiffres ne remplacent pas un test réel — voir [Limites connues](reference.md#limites-connues).

## 🆚 Comparateur

**Objectif** : comparer 2 à 4 modèles côte à côte pour choisir le meilleur compromis local.

**Éléments d'interface** : 2 à 4 champs d'identifiants de modèles, bouton **🆚 Comparer**.

**Actions** : saisir entre 2 et 4 identifiants **distincts** puis comparer.

**Résultat** : tableau décisionnel critère par critère (paramètres, popularité, contexte, licence, couverture FR déclarée, adéquation locale, GGUF disponible) avec une **recommandation motivée**, plus un tableau technique complet et un radar des quantités relatives (masqué si moins de trois quantités communes sont renseignées).

**Erreurs possibles** : « Sélectionnez de 2 à 4 modèles. », « Chaque modèle doit être différent. », « Identifiant invalide : X. ».

## 🧪 Test

**Statut : non implémenté.** Cet onglet affiche actuellement un espace réservé : *« L'interface adaptative d'inférence sera ajoutée à l'étape 6. »* Aucune fonctionnalité de test d'inférence n'existe encore — voir [Limites connues](reference.md#limites-connues).

## 📈 Analytics

**Objectif** : observer les tendances du Hub et administrer le cache local de l'application.

**Éléments d'interface** :
- 5 boutons de **tendances curatées** : 🔥 Plus téléchargés, ❤️ Plus appréciés, 🆕 Récents, 🇫🇷 Français, 💻 Optimisés local
- Bouton **📈 Croissance rapide (Rising models)** — détection de croissance (ex. 100k → 500k téléchargements) fondée sur les observations locales dans le temps
- Bouton **📈 Charger les Analytics** — analyse détaillée par filtres (top 50, répartition tâches/licences, évolution observée)
- Panneau **🗄️ Gestion du cache** : aperçu par domaine (entrées, taille, fraîcheur) et boutons **🗑 Vider le cache** / **🔄 Actualiser l'affichage**

**Cas particuliers** : « Rising models » sans historique suffisant affiche un message explicite invitant à charger au moins une tendance, ou à revenir un autre jour (une seule journée observée ne suffit pas à détecter une croissance).

**Limites** : le radar et les statistiques portent uniquement sur l'échantillon chargé (jusqu'à 50 résultats), pas sur tout le Hub. Voir [Fonctionnalités → Analytics](features.md#analytics-observatoire-du-hub) et [Gestion du cache](features.md#gestion-du-cache).

## ⭐ Favoris

**Objectif** : gérer une collection personnelle de modèles suivis.

**Éléments d'interface** :
- Filtre **Collection**, bouton **🔄 Actualiser**
- Pour chaque favori : bouton pour recharger sa fiche détaillée, accordéon **✏️ Modifier** avec : **Collection** (menu ou saisie libre), **Statut** (`à tester`, `testé`, `recommandé`, `à écarter`), **Note personnelle** (0 à 5, 0 = aucune), **Tags** (séparés par des virgules), **Dernier test** (date JJ/MM/AAAA), commentaire libre, et un bouton de retrait

**Résultat** : liste filtrable par collection, entièrement locale (aucun appel réseau nécessaire pour consulter les favoris).

## ☰ Menu hamburger (mobile)

**Objectif** : naviguer entre les onglets sur petit écran (< 768px), où la barre des huit onglets est masquée.

**Éléments d'interface** : bouton **☰** dans l'en-tête, ouvrant un panneau à trois catégories :
- **🔍 Explorer** : Recherche, Mon usage
- **🔬 Analyser un modèle** : Détails, Hardware, Comparateur, Test
- **📊 Suivre et organiser** : Analytics, Favoris

**Actions** : cliquer une entrée navigue vers l'onglet correspondant et referme automatiquement le menu. Sur desktop (≥ 768px), le bouton reste masqué et la barre d'onglets classique fonctionne normalement — c'est la même interface, pas un mode séparé.

<a id="a-propos"></a>
## ℹ️ À propos

**Objectif** : identité de l'application, support et informations légales, accessibles en permanence.

**Accès** : tout en bas du [menu hamburger](#-menu-hamburger-mobile), en dessous des trois catégories.

**Éléments d'interface** :
- Logo, nom, **version et commit** (dérivés de Git au démarrage, jamais codés en dur — « — » si indéterminable)
- Lien **Notes de version**, liens **auteur/site/portfolio/dépôt/signaler un bug** (dérivés du remote Git réel du dépôt)
- Bouton **📧 Contacter le support** : ouvre un brouillon d'e-mail pré-rempli (version, commit, navigateur) que l'utilisateur relit et envoie lui-même — jamais d'envoi automatique
- Bouton **⚖️ Mentions légales** : ouvre directement la page complète des [mentions légales](legal.md)
- Bouton **🧭 Revoir la visite guidée** : relance la [visite guidée](#visite-guidée-onboarding) depuis le début, quel que soit son état d'avancement précédent
- Crédits des dépendances open source et copyright

**Navigation** : bouton **Fermer** pour revenir à l'écran en cours.

## Visite guidée (onboarding)

**Objectif** : présenter les fonctionnalités principales à un nouvel utilisateur, juste après l'avertissement légal.

**Accès** : automatique à la première visite d'un navigateur (une fois l'avertissement légal accepté), ou rejouable à tout moment depuis [« ℹ️ À propos »](#a-propos) (« 🧭 Revoir la visite guidée »).

**Éléments d'interface** : 5 étapes (Bienvenue ; Recherche & Mon usage ; Fiche technique & Huggor Score ; Comparateur & Hardware ; Favoris, Analytics & mode hors connexion), un indicateur de progression (points), boutons **← Précédent**, **Suivant →** (devient **🚀 Commencer** sur la dernière étape) et **Passer l'introduction**.

**Actions** : naviguer étape par étape, ou passer directement à la fin à tout moment.

**Résultat** : une fois terminée ou passée, ne réapparaît plus automatiquement sur ce même navigateur (mémorisé dans son `localStorage`, indépendamment de l'avertissement légal).
