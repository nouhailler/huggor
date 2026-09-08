"""Squelette de l'onglet Analytics Gradio."""

import gradio as gr


def build_analytics_tab() -> None:
    """Afficher l'espace réservé aux visualisations Plotly."""
    gr.Markdown("## Analyser le Hub")
    gr.HTML(
        '<div class="hf-placeholder">'
        "Les tendances et graphiques interactifs seront ajoutés à l’étape 5."
        "</div>"
    )
