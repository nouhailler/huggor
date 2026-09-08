"""Squelette de l'onglet de comparaison Gradio."""

import gradio as gr


def build_compare_tab() -> None:
    """Afficher l'espace réservé à la comparaison de modèles."""
    gr.Markdown("## Comparer des modèles")
    gr.HTML(
        '<div class="hf-placeholder">'
        "Le tableau comparatif et le graphique radar seront ajoutés à l’étape 5."
        "</div>"
    )
