"""Squelette de l'onglet de détails Gradio."""

import gradio as gr


def build_details_tab() -> None:
    """Afficher l'espace réservé à la fiche détaillée d'un modèle."""
    gr.Markdown("## Examiner un modèle")
    gr.HTML(
        '<div class="hf-placeholder">'
        "La Model Card, les fichiers et le générateur de code seront ajoutés à l’étape 4."
        "</div>"
    )
