# HF Explorer

HF Explorer est une application Python destinée à rechercher, examiner, comparer et tester les modèles du Hugging Face Hub depuis une interface Gradio.

## État du projet

Les étapes 1 à 5 sont implémentées : accès au Hub, cache local, recherche, fiches techniques, comparateur et Analytics. L’étape 6 ajoutera le test d’inférence.

### Fonctionnalités disponibles

- Recherche par mot-clé, domaine et tâche précise (navigation pédagogique 🧠 LLM, 👁️ Vision, 🖼️ Image, 🎙️ Audio, 🗣️ Speech, 🔤 Embeddings, 🌐 Multimodal, 🧩 Reranking, chacune détaillée en tâches réellement couvertes par le Hub), langue et licence
- Filtrage par plage de paramètres et limite de 5 à 100 résultats
- Tri par téléchargements, likes, date de création ou pertinence
- Cartes synthétiques avec lien direct vers le Hub
- Ouverture et chargement automatiques de la fiche depuis « Voir détails »
- Fiche technique centrale : identité, architecture, quantification et compatibilités d'exécution
- Recommandation explicite des poids, shards ou adapters à télécharger
- Model Card complète, inventaire annoté et arborescence des fichiers avec leurs tailles
- Génération de snippets pour une utilisation locale et avec `InferenceClient`
- [Onglet ⭐ Favoris](src/ui/favorites_tab.py) : collections personnalisées, tags, statut, note personnelle (1 à 5), date du dernier test et commentaire libre pour chaque modèle enregistré, avec filtrage par collection et retrait direct
- Fiche technique : tableau des précisions et quantifications détectées (FP32/FP16/BF16/INT8, paliers GGUF Q8 à Q2, GPTQ, AWQ, EXL2, MLX)
- Fiche technique : recherche automatique des versions déjà quantifiées d'un modèle sur le Hub (GGUF, GPTQ, AWQ, EXL2, MLX), triées par popularité
- Fiche technique : verdict d'adéquation matérielle (« Model Advisor ») estimant la RAM/VRAM nécessaire selon la précision
- Fiche technique : [Huggor Score](src/huggor_score.py) sur 100, toujours accompagné du détail de ses neuf composantes (popularité, fraîcheur, documentation, licence, Safetensors, quantification, compatibilité locale, taille, maturité) pour ne jamais rester une boîte noire
- Fiche technique : modèles similaires rapprochés par famille, tâche, taille, langue déclarée, licence et disponibilité quantifiée, en excluant les simples quantifications du modèle affiché
- [Onglet 💻 Hardware](src/ui/hardware_tab.py) : calculateur de ressources indiquant, selon votre RAM/VRAM déclarée, quelles précisions (FP32 à Q4_K_M) tiennent réellement, avec une estimation de vitesse et de contexte clairement présentée comme théorique
- [Onglet 🎯 Mon usage](src/ui/usage_tab.py) : recherche par objectif (Chatbot, Coding, RAG, Embeddings, Traduction, Vision, Speech, Génération d'images) plutôt que par jargon Hugging Face, croisée avec votre RAM/VRAM pour ne remonter que des modèles jouables sur votre machine, verdict de précision et de vitesse à l'appui, avec un bouton « ⭐ Pin » pour ajouter directement un résultat aux favoris
- Comparaison décisionnelle de 2 à 4 modèles : tableau critère par critère (paramètres, popularité, contexte, licence, couverture FR déclarée, adéquation locale, GGUF) et recommandation motivée du meilleur compromis pour un usage local, en plus du tableau technique complet et du radar des quantités relatives
- [Onglet 📈 Analytics](src/ui/analytics_tab.py) — 🔭 Observatoire du Hub : tendances curatées en listes classées (🔥 plus téléchargés, ❤️ plus appréciés, 🆕 récents, 🇫🇷 français, 💻 optimisés local) et détection de « Rising models » (ex. 100k → 500k téléchargements) fondée sur vos propres observations locales dans le temps, en plus de l'analyse détaillée par filtres (top 50, répartition des tâches/licences, évolution observée)
- [Gestion du cache](src/cache_manager.py) industrialisée par domaine (recherches, détails, model cards, statistiques, benchmarks à venir) : aperçu entrées/taille/fraîcheur et purge ciblée dans l'onglet Analytics (« 🗄️ Gestion du cache »), et dans la fiche modèle un repère « ⏱ Dernière mise à jour » avec un bouton « 🔄 Actualiser depuis Hugging Face » pour forcer un rechargement sans passer par le cache

Le radar n’est pas une mesure de qualité. Les statistiques portent uniquement sur les 50 résultats sélectionnés, pas sur tout le Hub. L’évolution commence au premier chargement, sans historique reconstruit. Les observations sont séparées par filtres et empreinte d’authentification dans `data/analytics/`, avec 90 jours observés conservés et une expiration après un an d’inactivité.

## Prérequis

- Python 3.10 ou supérieur
- Un token Hugging Face est facultatif pour les modèles publics et nécessaire pour les ressources privées ou protégées

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Renseignez `HF_TOKEN` dans `.env`, ou authentifiez la machine avec `hf auth login`. Ne versionnez jamais le fichier `.env`.

## Lancement

```bash
python app.py
```

L'interface est ensuite disponible par défaut sur <http://127.0.0.1:7860>. Les variables `GRADIO_SERVER_NAME` et `GRADIO_SERVER_PORT` permettent de modifier cette adresse.

## Utilisation du client API

```python
from src.api_client import HuggingFaceClient, SearchFilters

client = HuggingFaceClient()
models = client.search_models(
    SearchFilters(
        query="bert",
        pipeline_tag="text-classification",
        language="fr",
        sort="downloads",
        limit=20,
    )
)

details = client.get_model_info("google-bert/bert-base-multilingual-cased")
card_markdown = client.get_model_card("google-bert/bert-base-multilingual-cased")
```

Chaque recherche impose une limite comprise entre 5 et 100 résultats. Les réponses sont conservées dans `data/cache/` avec une durée de vie configurable.

## Tests

Les tests sont isolés du réseau et utilisent la bibliothèque standard :

```bash
python -m unittest discover -s tests -v
```

## Capture d'écran

_À ajouter avec l'interface Gradio._

## Paquet Debian / Ubuntu

Téléchargez le fichier `.deb` depuis les [releases GitHub](https://github.com/nouhailler/huggor/releases), puis installez-le :

```bash
sudo apt install ./hf-explorer_0.1.0_all.deb
hf-explorer
```

Python 3.10 ou supérieur est requis (par exemple Ubuntu 22.04+ ou Debian 12+).
L’entrée **HF Explorer** du menu des applications ouvre aussi le lanceur dans un terminal.
Au premier lancement, une connexion Internet est nécessaire pour télécharger les dépendances Python dans un environnement isolé. Gardez le terminal ouvert, puis ouvrez `http://127.0.0.1:7860` dans votre navigateur. Pour arrêter l’application, utilisez `Ctrl+C`.

Le lanceur conserve son environnement Python et les données dans `${XDG_DATA_HOME:-~/.local/share}/hf-explorer/`. Aucune donnée personnelle n’est incluse dans le paquet. Les mises à jour conservent les favoris et l’historique. La désinstallation du paquet conserve également ces données. Pour utiliser un token, lancez `export HF_TOKEN=…` avant `hf-explorer` ou utilisez `hf auth login`.

Pour reconstruire le paquet depuis les sources avec Python et `dpkg-deb` :

```bash
python3 scripts/build_deb.py --version 0.1.0
```

Le résultat est écrit dans `dist/`. `HF_EXPLORER_DATA_DIR` permet de choisir un autre emplacement pour les données.
