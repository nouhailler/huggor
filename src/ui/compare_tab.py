"""Comparateur Gradio de deux à quatre modèles du Hub."""

from __future__ import annotations

import html
from functools import partial

import gradio as gr
import pandas as pd
import plotly.graph_objects as go

from src.api_client import HuggingFaceClient, HuggingFaceClientError
from src.comparison import COMPARISON_COLUMNS, comparison_radar, comparison_table, validate_comparison_ids


def build_compare_tab(client: HuggingFaceClient) -> None:
    """Construire la sélection, le tableau et le radar interactif."""
    gr.Markdown("## Comparer des modèles\n\nSaisissez **2 à 4 identifiants distincts** du Hub.")
    with gr.Row():
        model_one = gr.Textbox(label="Modèle 1", placeholder="google-bert/bert-base-uncased")
        model_two = gr.Textbox(label="Modèle 2", placeholder="FacebookAI/roberta-base")
    with gr.Row():
        model_three = gr.Textbox(label="Modèle 3 (facultatif)")
        model_four = gr.Textbox(label="Modèle 4 (facultatif)")
    compare = gr.Button("🆚 Comparer", variant="primary")
    status = gr.Markdown("Choisissez au moins deux modèles.")
    table = gr.Dataframe(
        headers=COMPARISON_COLUMNS, value=[], interactive=False, wrap=True,
        label="Tableau comparatif", show_search="search", max_height=420,
    )
    gr.Markdown(
        "Le radar ramène chaque quantité au maximum de la sélection (100 %). "
        "**Plus grand ne signifie pas meilleur** : ce n’est ni un benchmark ni une mesure de qualité. "
        "Les axes incomplets sont retirés. La taille additionne les fichiers courants du dépôt, "
        "pas la RAM/VRAM nécessaire ni seulement le fichier recommandé."
    )
    radar = gr.Plot(label="Radar comparatif")
    compare.click(
        fn=partial(compare_for_ui, client),
        inputs=[model_one, model_two, model_three, model_four], outputs=[status, table, radar],
        api_name="compare_models", show_progress="minimal", concurrency_limit=2,
        concurrency_id="hub-details",
    )


def compare_for_ui(
    client: HuggingFaceClient,
    model_one: str,
    model_two: str,
    model_three: str = "",
    model_four: str = "",
    progress: gr.Progress = gr.Progress(),
) -> tuple[str, pd.DataFrame, go.Figure | None]:
    """Charger au plus quatre fiches et vider les résultats en cas d'erreur."""
    empty = pd.DataFrame(columns=COMPARISON_COLUMNS)
    try:
        ids = validate_comparison_ids([model_one, model_two, model_three, model_four])
        models = []
        for index, repo_id in enumerate(ids):
            progress(index / len(ids), desc=f"Chargement de {repo_id}…")
            models.append(client.get_model_info(repo_id))
        table = comparison_table(models)
        radar = comparison_radar(models)
    except ValueError as error:
        return f"⚠️ {html.escape(str(error))}", empty, None
    except HuggingFaceClientError as error:
        return f"⚠️ Comparaison impossible : {html.escape(str(error))}", empty, None
    except Exception:
        return "⚠️ Comparaison impossible : une erreur inattendue est survenue.", empty, None
    progress(1, desc="Comparaison prête")
    message = f"✅ **{len(models)} modèles comparés.**"
    if radar is None:
        message += " Radar indisponible : moins de trois quantités communes renseignées."
    return message, table, radar
