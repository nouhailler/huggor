"""Squelette de l'onglet de test d'inférence Gradio."""

import gradio as gr


def build_test_tab() -> None:
    """Afficher l'espace réservé aux tests d'inférence."""
    gr.Markdown("## Tester un modèle")
    gr.HTML(
        '<div class="hf-placeholder">'
        "L’interface adaptative d’inférence sera ajoutée à l’étape 6."
        "</div>"
    )
