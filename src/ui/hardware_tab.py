"""Onglet Gradio du calculateur de ressources : confronter un modèle à sa propre machine."""

from __future__ import annotations

import html
from functools import partial

import gradio as gr

from src.api_client import HuggingFaceClient, HuggingFaceClientError
from src.model_analysis import extract_technical_profile
from src.resource_calculator import (
    HardwareProfile,
    PrecisionFit,
    ResourceCalculation,
    calculate_resources,
)
from src.utils.formatters import escape_markdown, format_bytes, format_count

_STATUS_LABELS = {"ok": "✅", "warning": "⚠️", "no": "❌"}
_PATH_LABELS = {"gpu": "GPU (VRAM)", "cpu": "CPU (RAM)", "none": "—"}


def build_hardware_tab(client: HuggingFaceClient) -> None:
    """Construire l'onglet Hardware et câbler son calcul de ressources."""
    gr.Markdown(
        "## 💻 Hardware — Calculateur de ressources\n"
        "Indiquez votre machine, chargez un modèle, et regardez quelles précisions tiennent "
        "réellement sur votre configuration."
    )
    gr.Markdown(
        "> ⚠️ **Ces chiffres sont des ordres de grandeur théoriques, pas des mesures réelles.** "
        "Ils reposent sur des repères génériques de bande passante mémoire, pas sur une base de "
        "données de matériel : le GPU et le CPU renseignés ci-dessous ne sont **pas utilisés dans "
        "le calcul**, ils ne servent que de repère pour vous. Seules la RAM et la VRAM comptent.",
        elem_classes="hf-hardware-disclaimer",
    )

    with gr.Row():
        repo_id = gr.Textbox(
            label="Identifiant du modèle",
            placeholder="Ex. Qwen/Qwen2.5-14B-Instruct",
            info="Indépendant de l'onglet Détails : copiez-collez l'identifiant du modèle à évaluer.",
            scale=3,
        )
        calculate_button = gr.Button("🧮 Calculer", variant="primary", scale=1, min_width=150)

    with gr.Row():
        ram_input = gr.Number(label="RAM (Go)", value=16, minimum=0, maximum=4096, step=1)
        vram_input = gr.Number(label="VRAM (Go)", value=0, minimum=0, maximum=1024, step=1)
        gpu_input = gr.Textbox(label="GPU (facultatif, non utilisé dans le calcul)", placeholder="Ex. RTX 5060 Ti")
        cpu_input = gr.Textbox(label="CPU (facultatif, non utilisé dans le calcul)", placeholder="Ex. Ryzen 5")

    status = gr.Markdown(
        "Renseignez un modèle et votre machine, puis lancez le calcul.",
        elem_classes="hf-details-status",
    )
    matrix = gr.Markdown("", elem_classes=["hf-tech-card", "hf-hardware-card"])
    estimate = gr.Markdown("", elem_classes=["hf-tech-card", "hf-hardware-card"])

    calculate_button.click(
        fn=partial(calculate_for_ui, client),
        inputs=[repo_id, ram_input, vram_input, gpu_input, cpu_input],
        outputs=[status, matrix, estimate],
        api_name="hardware_calculator",
        api_description="Estimer l'adéquation d'un modèle avec une configuration matérielle donnée.",
        show_progress="minimal",
        concurrency_limit=2,
        concurrency_id="hub-details",
    )
    repo_id.submit(
        fn=partial(calculate_for_ui, client),
        inputs=[repo_id, ram_input, vram_input, gpu_input, cpu_input],
        outputs=[status, matrix, estimate],
        api_visibility="private",
        show_progress="minimal",
        concurrency_limit=2,
        concurrency_id="hub-details",
    )


def calculate_for_ui(
    client: HuggingFaceClient,
    repo_id: str,
    ram_gib: float | None,
    vram_gib: float | None,
    gpu_name: str | None,
    cpu_name: str | None,
) -> tuple[str, str, str]:
    """Charger le modèle et produire le tableau de précisions et l'estimation détaillée."""
    try:
        hardware = HardwareProfile(
            ram_gib=float(ram_gib or 0),
            vram_gib=float(vram_gib or 0),
            gpu_name=(gpu_name or "").strip(),
            cpu_name=(cpu_name or "").strip(),
        )
    except (TypeError, ValueError) as error:
        return f"⚠️ {html.escape(str(error))}", "", ""

    if hardware.ram_gib <= 0 and hardware.vram_gib <= 0:
        return "⚠️ Indiquez au moins une quantité de RAM ou de VRAM supérieure à zéro.", "", ""

    try:
        details = client.get_model_info(repo_id or "")
    except ValueError as error:
        return f"⚠️ **Identifiant invalide :** {html.escape(str(error))}", "", ""
    except HuggingFaceClientError as error:
        return f"⚠️ **Chargement impossible :** {html.escape(str(error))}", "", ""
    except Exception:
        return "⚠️ **Chargement impossible :** une erreur inattendue est survenue.", "", ""

    profile = extract_technical_profile(details)
    safe_repo_id = escape_markdown(details.summary.repo_id)
    if profile.parameters is None:
        return (
            f"⚠️ **{safe_repo_id}** ne déclare pas de nombre de paramètres : le calcul est impossible.",
            "",
            "",
        )

    calculation = calculate_resources(profile.parameters, hardware, details.config, profile.context_length)
    heading = f"✅ Estimation pour **{safe_repo_id}** ({format_count(profile.parameters)} paramètres)."
    return heading, format_precision_matrix(calculation), format_resource_estimate(calculation)


def format_precision_matrix(calculation: ResourceCalculation) -> str:
    """Présenter le statut de chaque précision face à la machine déclarée."""
    if not calculation.precisions:
        return ""
    rows = "\n".join(_precision_row(item) for item in calculation.precisions)
    return (
        "### Compatibilité par précision\n\n"
        "| Précision | Statut | Mémoire nécessaire | Exécution possible |\n"
        "|---|---|---|---|\n"
        f"{rows}"
    )


def _precision_row(item: PrecisionFit) -> str:
    """Formater une ligne du tableau de compatibilité par précision."""
    execution = _PATH_LABELS[item.path] if item.status != "no" else "—"
    return f"| {item.label} | {_STATUS_LABELS[item.status]} | ≈ {format_bytes(item.memory_bytes)} | {execution} |"


def format_resource_estimate(calculation: ResourceCalculation) -> str:
    """Détailler VRAM/RAM, vitesse et contexte pour la meilleure précision jouable."""
    estimate = calculation.estimate
    if estimate.precision_label is None:
        return (
            "### 📊 Estimation détaillée\n\n"
            f"{estimate.speed_label}\n\n"
            f"{escape_markdown(estimate.context_note)}"
        )

    location = _PATH_LABELS[estimate.execution_path]
    memory_row = f"≈ {format_bytes(estimate.memory_bytes)} ({location})"
    speed_range = (
        f" — ≈ {estimate.speed_tokens_per_second_low:.0f}–{estimate.speed_tokens_per_second_high:.0f} tokens/s"
        if estimate.speed_tokens_per_second_low is not None
        else ""
    )
    context_row = (
        f"≈ {estimate.max_context_tokens:,}".replace(",", " ") + " tokens"
        if estimate.max_context_tokens
        else "Non calculable pour cette architecture"
    )

    return (
        f"### 📊 Estimation détaillée — précision retenue : {estimate.precision_label}\n\n"
        "| Indicateur | Valeur |\n"
        "|---|---|\n"
        f"| Mémoire utilisée | {memory_row} |\n"
        f"| Vitesse d'inférence estimée | {estimate.speed_label}{speed_range} |\n"
        f"| Contexte maximum réaliste | {context_row} |\n\n"
        f"_{escape_markdown(estimate.context_note)}_\n\n"
        "> ⚠️ Estimation théorique à partir de repères génériques ; ce n'est pas un benchmark. "
        "Confirmez toujours par un test réel sur votre machine avant de vous engager."
    )
