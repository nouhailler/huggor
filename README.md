# HF Explorer

HF Explorer est une application Python destinée à rechercher, examiner, comparer et tester les modèles du Hugging Face Hub depuis une interface Gradio.

## État du projet

Les étapes 1 à 5 sont implémentées : accès au Hub, cache local, recherche, fiches techniques, comparateur et Analytics. L’étape 6 ajoutera le test d’inférence.

### Fonctionnalités disponibles

- Recherche par mot-clé, type de tâche, langue et licence
- Filtrage par plage de paramètres et limite de 5 à 100 résultats
- Tri par téléchargements, likes, date de création ou pertinence
- Cartes synthétiques avec lien direct vers le Hub
- Ouverture et chargement automatiques de la fiche depuis « Voir détails »
- Fiche technique centrale : identité, architecture, quantification et compatibilités d'exécution
- Recommandation explicite des poids, shards ou adapters à télécharger
- Model Card complète, inventaire annoté et arborescence des fichiers avec leurs tailles
- Génération de snippets pour une utilisation locale et avec `InferenceClient`
- Ajout local d'un modèle aux favoris
- Comparaison de 2 à 4 modèles : tableau technique et radar des quantités relatives
- Analytics filtrées : top 50 téléchargements, répartition des tâches et licences
- Évolution des compteurs du top 5 actuel à partir d’observations locales quotidiennes

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
