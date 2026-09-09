"""Squelette de l'onglet de détails Gradio."""

from __future__ import annotations

from dataclasses import dataclass

import gradio as gr


@dataclass(frozen=True, slots=True)
class DetailsTabComponents:
    """Composants accessibles depuis les autres onglets."""

    repo_id: gr.Textbox


def build_details_tab() -> DetailsTabComponents:
    """Construire le point d'entrée de la future fiche détaillée."""
    gr.Markdown("## Examiner un modèle")
    repo_id = gr.Textbox(
        label="Identifiant du modèle",
        placeholder="Ex. meta-llama/Llama-3.2-1B",
        info="Le bouton « Voir détails » d'une recherche remplit automatiquement ce champ.",
    )
    gr.HTML(
        '<div class="hf-placeholder">'
        "La Model Card, les fichiers et le générateur de code seront ajoutés à l’étape 4."
        "</div>"
    )
    return DetailsTabComponents(repo_id=repo_id)
