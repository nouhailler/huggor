# 🎯 Projet : Application Gradio d'exploration des modèles Hugging Face

## 📖 Contexte
Je souhaite développer une application Python avec une interface graphique (Gradio) permettant d'explorer, rechercher, analyser et tester les modèles disponibles sur le Hugging Face Hub. L'application doit être élégante, performante et utile au quotidien pour un praticien en IA.

## 🛠️ Stack technique imposée
- **Langage** : Python 3.10+
- **Interface** : Gradio 4.x+ (avec `gr.Blocks` et thème moderne `gr.themes.Soft()`)
- **Backend** : `huggingface_hub` (API officielle)
- **Inférence** : `huggingface_hub.InferenceClient`
- **Visualisation** : `plotly` (graphiques interactifs)
- **Données** : `pandas` (manipulation des résultats)
- **Optionnel** : `matplotlib`, `rich` (pour logs console)

## 📁 Structure du projet attendue
hf_explorer/
├── app.py # Point d'entrée principal
├── requirements.txt # Dépendances
├── README.md # Documentation
├── .env.example # Template pour le token HF
├── src/
│ ├── init.py
│ ├── api_client.py # Wrapper autour de HfApi (avec cache)
│ ├── ui/
│ │ ├── init.py
│ │ ├── search_tab.py # Onglet recherche
│ │ ├── details_tab.py # Onglet fiche modèle
│ │ ├── compare_tab.py # Onglet comparateur
│ │ ├── test_tab.py # Onglet test d'inférence
│ │ └── analytics_tab.py # Onglet graphiques
│ └── utils/
│ ├── init.py
│ ├── formatters.py # Formatage des données
│ └── cache.py # Gestion du cache local (JSON)
└── data/
└── favorites.json # Stockage des favoris utilisateur


## 🎨 Design & UX
- Utiliser le thème `gr.themes.Soft()` avec une palette cohérente
- Interface organisée en **onglets** (`gr.Tabs()`) :
  1. 🔍 **Recherche** - Recherche multi-critères
  2. 📄 **Détails** - Fiche complète d'un modèle
  3. 🆚 **Comparateur** - Comparaison côte à côte (2-4 modèles)
  4. 🧪 **Test** - Inférence directe
  5. 📈 **Analytics** - Graphiques et tendances
  6. ⭐ **Favoris** - Modèles sauvegardés
- Ajouter un **header** avec le titre, une icône et un indicateur de statut de connexion
- Gérer proprement les états de chargement (`gr.Progress()`) et les erreurs

## ✅ Fonctionnalités à implémenter (par ordre de priorité)

### 🔴 PRIORITÉ 1 - Cœur de l'application

#### 1. Onglet Recherche
- Champ texte pour mot-clé
- Dropdowns pour : type de tâche (pipeline_tag), langue, licence
- Sliders pour : nombre min/max de paramètres, nombre de résultats (5-100)
- Tri par : likes, téléchargements, date de création, pertinence
- Affichage des résultats sous forme de **cartes** (Markdown) avec :
  - Nom du modèle (lien cliquable vers HF)
  - Auteur
  - Nombre de likes et téléchargements
  - Tags principaux
  - Bouton "Voir détails" qui pré-remplit l'onglet Détails
- ⚠️ **Contrainte critique** : Toujours utiliser `limit` pour éviter de charger trop de données. Par défaut à 20.

#### 2. Onglet Détails
- Champ pour saisir un `repo_id` (ex: `meta-llama/Llama-3.2-1B`)
- Affichage de :
  - Model Card complète rendue en Markdown (`hf models card`)
  - Liste des fichiers avec tailles (vue arborescente)
  - Métadonnées techniques (architecture, bibliothèque, pipeline)
  - **Générateur de code** : afficher automatiquement le snippet Python pour utiliser le modèle via `transformers` ou `InferenceClient`
  - Bouton "Ajouter aux favoris"

#### 3. Onglet Comparateur
- Sélection de 2 à 4 modèles (champs texte ou dropdown)
- Tableau comparatif avec : paramètres, taille, licence, likes, downloads, dernière MAJ
- Graphique radar Plotly comparant les caractéristiques

### 🟡 PRIORITÉ 2 - Fonctionnalités interactives

#### 4. Onglet Test d'inférence
- Sélection du modèle à tester
- Interface adaptative selon le `pipeline_tag` :
  - `text-generation` → zone de texte + paramètres (temperature, max_tokens)
  - `text-to-image` → prompt + affichage de l'image générée
  - `automatic-speech-recognition` → upload audio + transcription
- Utilisation de `InferenceClient` avec gestion des erreurs (modèle non disponible, rate limit...)

#### 5. Onglet Analytics
- Graphiques Plotly :
  - Top 50 modèles les plus téléchargés (bar chart)
  - Répartition par type de tâche (pie chart)
  - Évolution des modèles populaires (line chart)
  - Répartition des licences
- Filtres pour affiner les statistiques

### 🟢 PRIORITÉ 3 

#### 6. Système de favoris
- Sauvegarde locale dans `data/favorites.json`
- Possibilité d'ajouter des notes personnelles
- Export en CSV/JSON

#### 7. Mode "Trending"
- Section dédiée affichant les modèles les plus populaires des 7 derniers jours
- Badges visuels : 🔥 Nouveau, 📈 En hausse

## ⚙️ Contraintes techniques importantes

1. **Performance** :
   - Ne JAMAIS charger tous les modèles sans filtre
   - Utiliser la pagination de `api.list_models()`
   - Mettre en cache les résultats fréquents (fichiers JSON dans `data/cache/`)

2. **Gestion des erreurs** :
   - Capturer toutes les exceptions réseau
   - Afficher des messages d'erreur clairs dans l'UI (pas de crash)
   - Gérer les cas : modèle inexistant, rate limit, token invalide

3. **Authentification** :
   - Charger le token depuis `.env` ou via `huggingface-cli login`
   - Permettre de se connecter/déconnecter depuis l'app
   - Indicateur visuel du statut de connexion

4. **Code qualité** :
   - Typage complet (type hints)
   - Docstrings pour toutes les fonctions
   - Séparation stricte UI / logique métier / API
   - Commentaires en français

5. **Sécurité** :
   - Ne jamais exposer le token dans les logs
   - Valider les entrées utilisateur (repo_id, paramètres)

## 📦 Livrables attendus

1. **Code source complet** fonctionnel et testé
2. **`requirements.txt`** avec versions épinglées
3. **`README.md`** contenant :
   - Description du projet
   - Prérequis (Python, token HF)
   - Installation (`pip install -r requirements.txt`)
   - Lancement (`python app.py`)
   - Capture d'écran (placeholder)
   - Liste des fonctionnalités
4. **`.env.example`** avec `HF_TOKEN=votre_token_ici`
5. **Instructions de déploiement** (optionnel : Spaces HF, Docker)

## 🚀 Plan de développement suggéré

**Étape 1** : Mettre en place la structure du projet et `api_client.py` avec les fonctions de base (recherche, info modèle, model card).

**Étape 2** : Créer le squelette de l'app Gradio avec les onglets vides et le header.

**Étape 3** : Implémenter l'onglet Recherche (le plus critique).

**Étape 4** : Implémenter l'onglet Détails avec la Model Card et le générateur de code.

**Étape 5** : Ajouter le Comparateur et les Analytics.

**Étape 6** : Ajouter le Test d'inférence.

**Étape 7** : Système de favoris et polish final.

**Étape 8** : Rédiger le README et tester l'ensemble.

## 💡 Notes supplémentaires

- Utilise des composants Gradio modernes : `gr.Markdown`, `gr.Dataframe`, `gr.Plot`, `gr.Chatbot`
- Pour les graphiques, préfère Plotly (interactif) à Matplotlib
- Le code doit être **immédiatement exécutable** après `pip install -r requirements.txt`
- Si une fonctionnalité est trop complexe, implémente une version simplifiée mais fonctionnelle, et ajoute un commentaire `# TODO: améliorer`
- N'hésite pas à me poser des questions si un point n'est pas clair avant de commencer

Commence par créer la structure du projet et l'Étape 1. Attends ma validation avant de passer à l'étape suivante.
