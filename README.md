# HF Explorer

HF Explorer est une application Python destinée à rechercher, examiner, comparer et tester les modèles du Hugging Face Hub depuis une interface Gradio.

## État du projet

Les étapes 1 à 4 sont implémentées : socle d'accès au Hub, cache JSON local, recherche multi-critères et fiches modèles complètes. Le comparateur et les premières analyses seront réalisés à l'étape 5.

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
