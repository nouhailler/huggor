"""Squelette de l'onglet de recherche Gradio."""

import gradio as gr


def build_search_tab() -> None:
    """Afficher l'espace réservé à la recherche multi-critères."""
    gr.Markdown("## Rechercher des modèles")
    gr.HTML(
        '<div class="hf-placeholder">'
        "La recherche multi-critères et les cartes de résultats seront ajoutées à l’étape 3."
        "</div>"
    )
