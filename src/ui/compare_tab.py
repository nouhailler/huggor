"""Comparateur Gradio de deux à quatre modèles du Hub."""

from __future__ import annotations

import html
from functools import partial

import gradio as gr
import pandas as pd
import plotly.graph_objects as go

from src.api_client import HuggingFaceClient, HuggingFaceClientError
from src.comparison import (
    COMPARISON_COLUMNS,
    ComparisonDecision,
    build_comparison_decision,
    comparison_radar,
    comparison_table,
    validate_comparison_ids,
)
from src.utils.formatters import escape_markdown

_GGUF_ICONS = {"ok": "✅", "warning": "⚠️", "no": "❌"}


def build_compare_tab(client: HuggingFaceClient) -> None:
    """Construire la sélection, le tableau décisionnel, le tableau technique et le radar."""
    gr.Markdown("## Comparer des modèles\n\nSaisissez **2 à 4 identifiants distincts** du Hub.")
    with gr.Row():
        model_one = gr.Textbox(label="Modèle 1", placeholder="google-bert/bert-base-uncased")
        model_two = gr.Textbox(label="Modèle 2", placeholder="FacebookAI/roberta-base")
    with gr.Row():
        model_three = gr.Textbox(label="Modèle 3 (facultatif)")
        model_four = gr.Textbox(label="Modèle 4 (facultatif)")
    compare = gr.Button("🆚 Comparer", variant="primary")
    status = gr.Markdown("Choisissez au moins deux modèles.")

    decision_table = gr.Markdown("", elem_classes=["hf-tech-card", "hf-hardware-card"])
    recommendation = gr.Markdown("", elem_classes=["hf-tech-card", "hf-hardware-card"])

    with gr.Accordion("Tableau technique complet et radar", open=False):
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

    outputs = [status, decision_table, recommendation, table, radar]
    compare.click(
        fn=partial(compare_for_ui, client),
        inputs=[model_one, model_two, model_three, model_four], outputs=outputs,
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
) -> tuple[str, str, str, pd.DataFrame, go.Figure | None]:
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
        decision = build_comparison_decision(models)
    except ValueError as error:
        return f"⚠️ {html.escape(str(error))}", "", "", empty, None
    except HuggingFaceClientError as error:
        return f"⚠️ Comparaison impossible : {html.escape(str(error))}", "", "", empty, None
    except Exception:
        return "⚠️ Comparaison impossible : une erreur inattendue est survenue.", "", "", empty, None
    progress(1, desc="Comparaison prête")
    message = f"✅ **{len(models)} modèles comparés.**"
    if radar is None:
        message += " Radar indisponible : moins de trois quantités communes renseignées."
    return message, format_decision_table(decision), format_recommendation(decision), table, radar


def format_decision_table(decision: ComparisonDecision) -> str:
    """Présenter les modèles comparés en colonnes, critères de décision en lignes."""
    if not decision.rows:
        return ""

    def row(label: str, values: list[str]) -> str:
        """Formater une ligne du tableau décisionnel."""
        return f"| {label} | " + " | ".join(values) + " |"

    header = "| Critère | " + " | ".join(escape_markdown(item.repo_id) for item in decision.rows) + " |"
    separator = "|" + "---|" * (len(decision.rows) + 1)
    lines = [
        header,
        separator,
        row("Paramètres", [item.parameters_label for item in decision.rows]),
        row("Téléchargements", [item.downloads_label for item in decision.rows]),
        row("Likes", [item.likes_label for item in decision.rows]),
        row("Contexte (tokens)", [item.context_label for item in decision.rows]),
        row("Licence", [escape_markdown(item.license_label) for item in decision.rows]),
        row("🇫🇷 FR", [_stars_label(item.fr_stars) for item in decision.rows]),
        row("🖥️ Local", [_stars_label(item.local_stars) for item in decision.rows]),
        row("GGUF", [_GGUF_ICONS[item.gguf_status] for item in decision.rows]),
    ]
    return (
        "### 🏁 Comparaison décisionnelle\n\n"
        + "\n".join(lines)
        + "\n\n_🇫🇷 FR : couverture du français **déclarée**, pas une mesure de qualité linguistique. "
        "🖥️ Local : palier de RAM confortable du Model Advisor, traduit en étoiles._"
    )


def format_recommendation(decision: ComparisonDecision) -> str:
    """Mettre en avant le meilleur compromis local, ou expliquer pourquoi ce n'est pas possible."""
    if not decision.rows:
        return ""
    if decision.recommended_repo_id is None:
        return f"### 🏆 Recommandation\n\n_{escape_markdown(decision.recommendation_reason)}_"

    safe_repo_id = escape_markdown(decision.recommended_repo_id)
    return (
        "### 🏆 Recommandation\n\n"
        f"**Meilleur compromis pour usage local : {safe_repo_id}**\n\n"
        f"_{escape_markdown(decision.recommendation_reason)}_\n\n"
        "> Ce choix combine l'estimation RAM/VRAM du Model Advisor, la disponibilité GGUF et, en dernier "
        "recours, la popularité. Ce n'est pas un jugement de qualité absolu : vérifiez toujours la Model Card."
    )


def _stars_label(stars: int | None) -> str:
    """Afficher une note en étoiles, ou signaler explicitement l'absence de donnée."""
    if stars is None:
        return "— (non renseigné)"
    return "⭐" * stars + "☆" * (5 - stars)
