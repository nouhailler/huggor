"""Squelette de l'onglet des modèles favoris."""

import gradio as gr


def build_favorites_tab() -> None:
    """Afficher l'espace réservé aux favoris locaux."""
    gr.Markdown("## Retrouver vos favoris")
    gr.HTML(
        '<div class="hf-placeholder">'
        "Les favoris, notes et exports seront ajoutés à l’étape 7."
        "</div>"
    )
