"""Graphiques Gradio sur un échantillon borné à cinquante modèles."""

from __future__ import annotations

import html
from functools import partial
from pathlib import Path

import gradio as gr
import pandas as pd
import plotly.graph_objects as go

from src.analytics import ANALYTICS_COLUMNS, AnalyticsHistory, analytics_figures, analytics_table
from src.api_client import HuggingFaceClient, HuggingFaceClientError, SearchFilters
from src.ui.search_tab import LANGUAGE_CHOICES, LICENSE_CHOICES, PIPELINE_CHOICES

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def build_analytics_tab(client: HuggingFaceClient) -> None:
    """Construire les filtres et les quatre graphiques interactifs."""
    history = AnalyticsHistory(_PROJECT_ROOT / "data" / "analytics", scope=client.cache_scope)
    gr.Markdown(
        "## Analyser le Hub\n\nAnalyse des **50 modèles les plus téléchargés correspondant aux filtres**. "
        "Les répartitions concernent cet échantillon, pas l’ensemble du Hub."
    )
    with gr.Row():
        query = gr.Textbox(label="Mot-clé Analytics", placeholder="Facultatif : llama, bert…")
        task = gr.Dropdown(choices=PIPELINE_CHOICES, value="", label="Tâche Analytics")
        language = gr.Dropdown(choices=LANGUAGE_CHOICES, value="", label="Langue Analytics")
        license_name = gr.Dropdown(choices=LICENSE_CHOICES, value="", label="Licence Analytics")
    load = gr.Button("📈 Charger les Analytics", variant="primary")
    status = gr.Markdown("Chargez les statistiques pour afficher les graphiques.")
    with gr.Tabs():
        with gr.Tab("Téléchargements"):
            downloads = gr.Plot(label="Top téléchargements")
        with gr.Tab("Tâches et licences"):
            with gr.Row():
                with gr.Column(min_width=400):
                    tasks = gr.Plot(label="Répartition des tâches")
                with gr.Column(min_width=400):
                    licenses = gr.Plot(label="Répartition des licences")
        with gr.Tab("Évolution observée"):
            gr.Markdown(
                "Ce graphique conserve une observation par jour UTC et par jeu de filtres (90 jours observés). "
                "Le premier chargement n’a qu’un point : il ne reconstitue pas le passé. "
                "Les compteurs sont ceux renvoyés par le Hub, pas des téléchargements cumulés calculés par l’app."
            )
            evolution = gr.Plot(label="Observations quotidiennes")
    with gr.Accordion("Données de l’échantillon", open=False):
        table = gr.Dataframe(headers=ANALYTICS_COLUMNS, value=[], interactive=False, wrap=True, show_search="search")
    load.click(
        fn=partial(analytics_for_ui, client, history), inputs=[query, task, language, license_name],
        outputs=[status, table, downloads, tasks, licenses, evolution], api_name="model_analytics",
        show_progress="minimal", concurrency_limit=1, concurrency_id="hub-analytics",
    )


def analytics_for_ui(
    client: HuggingFaceClient, history: AnalyticsHistory,
    query: str, task: str, language: str, license_name: str,
    progress: gr.Progress = gr.Progress(),
) -> tuple[str, pd.DataFrame, go.Figure | None, go.Figure | None, go.Figure | None, go.Figure | None]:
    """Charger cinquante résultats au maximum et gérer les erreurs sans conserver un ancien graphique."""
    empty = pd.DataFrame(columns=ANALYTICS_COLUMNS)
    try:
        filters = SearchFilters(
            query=query or "", pipeline_tag=task or None, language=language or None,
            license=license_name or None, sort="downloads", limit=50,
        )
        progress(0.15, desc="Chargement des 50 modèles…")
        models = client.search_models(filters)[:50]
        table = analytics_table(models)
        if table.empty:
            return "Aucun modèle ne correspond aux filtres.", empty, None, None, None, None
        warning = ""
        try:
            observed = history.record(filters, models)
        except OSError:
            observed = pd.DataFrame(columns=["Date", "Modèle", "Téléchargements"])
            warning = " ⚠️ L’observation locale n’a pas pu être enregistrée."
        progress(0.75, desc="Préparation des graphiques…")
        figures = analytics_figures(table, observed)
        days = observed["Date"].nunique()
    except (ValueError, HuggingFaceClientError) as error:
        return f"⚠️ Analytics indisponibles : {html.escape(str(error))}", empty, None, None, None, None
    except Exception:
        return "⚠️ Analytics indisponibles : une erreur inattendue est survenue.", empty, None, None, None, None
    progress(1, desc="Analytics prêtes")
    return f"✅ **{len(models)} modèles analysés** · {days} jour(s) observé(s).{warning}", table, *figures
