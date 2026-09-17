"""Onglet Gradio « Mon usage » : chercher par objectif plutôt que par jargon Hugging Face."""

from __future__ import annotations

import html
from functools import partial
from typing import Any
from urllib.parse import quote

import gradio as gr

from src.api_client import HuggingFaceClient, ModelSummary, SearchFilters
from src.resource_calculator import HardwareProfile, calculate_resources
from src.ui.details_tab import DetailsTabComponents, load_details_for_ui
from src.ui.search_tab import select_model_for_details
from src.use_case_search import USE_CASES
from src.utils.formatters import escape_markdown, format_count

_RESULTS_PER_SEARCH = 25
_MAX_RESULTS_PER_USE_CASE = 8


def build_usage_tab(
    client: HuggingFaceClient,
    details: DetailsTabComponents,
    app_tabs: gr.Tabs,
) -> None:
    """Construire le formulaire objectif + machine et la liste de modèles compatibles."""
    gr.Markdown(
        "## 🎯 Recherche pour mon usage\n"
        "Dites ce que vous voulez faire et indiquez votre machine : Huggor cherche des modèles "
        "réellement adaptés, sans avoir à connaître le vocabulaire technique du Hub."
    )

    use_case_group = gr.CheckboxGroup(
        choices=[(item.label, item.key) for item in USE_CASES],
        value=[],
        label="Que voulez-vous faire ?",
    )

    gr.Markdown("### Votre machine")
    with gr.Row():
        ram_input = gr.Number(label="RAM (Go)", value=16, minimum=0, maximum=4096, step=1)
        vram_input = gr.Number(label="VRAM (Go)", value=0, minimum=0, maximum=1024, step=1)
        gpu_input = gr.Textbox(label="GPU (facultatif, non utilisé dans le calcul)", placeholder="Ex. RTX 5060 Ti")
    gr.Markdown(
        "> ⚠️ La compatibilité matérielle est une estimation théorique, pas un benchmark (même principe "
        "que l'onglet Hardware) : le GPU renseigné ci-dessus n'est **pas utilisé dans le calcul**, seules "
        "la RAM et la VRAM comptent.",
        elem_classes="hf-hardware-disclaimer",
    )

    search_button = gr.Button("🎯 Rechercher les modèles compatibles", variant="primary")
    status = gr.Markdown(
        "Cochez au moins un usage, puis lancez la recherche.",
        elem_classes="hf-search-status",
    )
    results = gr.State([])

    search_button.click(
        fn=partial(search_by_usage_for_ui, client),
        inputs=[use_case_group, ram_input, vram_input, gpu_input],
        outputs=[results, status],
        api_name="search_by_usage",
        api_description="Rechercher des modèles adaptés à un usage donné et compatibles avec une machine déclarée.",
        show_progress="minimal",
        scroll_to_output=True,
        concurrency_limit=2,
        concurrency_id="hub-search",
    )

    @gr.render(inputs=results, show_progress="hidden")
    def render_usage_results(sections: list[dict[str, Any]] | None) -> None:
        """Afficher les résultats groupés par usage, avec le verdict matériel de chacun."""
        if not sections:
            return
        for section_index, section in enumerate(sections):
            gr.Markdown(f"### {section['label']}")
            items = section["items"]
            if not items:
                gr.Markdown("_Aucun modèle compatible trouvé pour cet usage avec cette machine._")
                continue
            for item_index, item in enumerate(items):
                repo_id = str(item.get("repo_id") or "")
                key_suffix = f"{section_index}-{item_index}-{repo_id}"
                with gr.Group(key=f"usage-card-{key_suffix}", elem_classes="hf-result-card"):
                    with gr.Row(equal_height=False):
                        gr.Markdown(
                            format_usage_card(item),
                            container=False,
                            elem_classes="hf-result-content",
                        )
                        details_button = gr.Button(
                            "Voir détails →",
                            variant="secondary",
                            size="sm",
                            min_width=135,
                            scale=0,
                            key=f"usage-details-{key_suffix}",
                        )
                    details_button.click(
                        fn=partial(select_model_for_details, repo_id),
                        outputs=[details.repo_id, app_tabs],
                        queue=False,
                        show_progress="hidden",
                        api_visibility="private",
                    ).then(
                        fn=partial(load_details_for_ui, client),
                        inputs=details.repo_id,
                        outputs=list(details.load_outputs),
                        show_progress="minimal",
                        api_visibility="private",
                        concurrency_limit=2,
                        concurrency_id="hub-details",
                    )


def search_by_usage_for_ui(
    client: HuggingFaceClient,
    selected_keys: list[str],
    ram_gib: float | None,
    vram_gib: float | None,
    gpu_name: str | None,
    progress: gr.Progress = gr.Progress(),
) -> tuple[list[dict[str, Any]], str]:
    """Chercher, pour chaque usage coché, des modèles compatibles avec la machine déclarée."""
    if not selected_keys:
        return [], "⚠️ Cochez au moins un usage avant de lancer la recherche."

    try:
        hardware = HardwareProfile(
            ram_gib=float(ram_gib or 0), vram_gib=float(vram_gib or 0), gpu_name=(gpu_name or "").strip()
        )
    except (TypeError, ValueError) as error:
        return [], f"⚠️ {html.escape(str(error))}"
    if hardware.ram_gib <= 0 and hardware.vram_gib <= 0:
        return [], "⚠️ Indiquez au moins une quantité de RAM ou de VRAM supérieure à zéro."

    use_cases = [item for item in USE_CASES if item.key in selected_keys]
    search_cache: dict[tuple[str, str], list[ModelSummary]] = {}
    total_steps = sum(len(use_case.tasks) for use_case in use_cases) or 1
    step = 0
    sections: list[dict[str, Any]] = []

    for use_case in use_cases:
        seen_repo_ids: set[str] = set()
        candidates: list[ModelSummary] = []
        for task in use_case.tasks:
            step += 1
            progress(step / total_steps, desc=f"Recherche « {use_case.label} »…")
            cache_key = (task.pipeline_tag, task.keyword)
            if cache_key not in search_cache:
                try:
                    search_cache[cache_key] = client.search_models(
                        SearchFilters(
                            pipeline_tag=task.pipeline_tag,
                            query=task.keyword,
                            sort="downloads",
                            limit=_RESULTS_PER_SEARCH,
                        )
                    )
                except Exception:
                    search_cache[cache_key] = []
            for summary in search_cache[cache_key]:
                if summary.repo_id in seen_repo_ids:
                    continue
                seen_repo_ids.add(summary.repo_id)
                candidates.append(summary)

        items = _score_by_hardware_fit(candidates, hardware)
        sections.append({"key": use_case.key, "label": use_case.label, "items": items[:_MAX_RESULTS_PER_USE_CASE]})

    progress(1, desc="Résultats prêts")
    total_found = sum(len(section["items"]) for section in sections)
    if total_found == 0:
        return sections, (
            "⚠️ Aucun modèle compatible trouvé. Essayez d'augmenter la RAM/VRAM déclarée, "
            "ou cochez d'autres usages."
        )
    suffix = "modèle compatible" if total_found == 1 else "modèles compatibles"
    return sections, f"**{total_found} {suffix}** réparti(s) sur {len(sections)} usage(s)."


def _score_by_hardware_fit(
    candidates: list[ModelSummary],
    hardware: HardwareProfile,
) -> list[dict[str, Any]]:
    """Ne garder que les modèles jouables ou non évaluables, jamais les incompatibles connus."""
    scored: list[tuple[int, int, dict[str, Any]]] = []
    for summary in candidates:
        calculation = calculate_resources(summary.parameters, hardware)
        item = summary.to_dict()
        if calculation.estimate.precision_label is not None:
            item["hardware_label"] = (
                f"✅ Compatible en {calculation.estimate.precision_label} — {calculation.estimate.speed_label}"
            )
            rank = 2
        elif summary.parameters is None:
            item["hardware_label"] = "❓ Compatibilité non évaluable (paramètres non renseignés par ce dépôt)"
            rank = 1
        else:
            continue
        scored.append((rank, summary.downloads, item))

    scored.sort(key=lambda entry: (entry[0], entry[1]), reverse=True)
    return [item for _rank, _downloads, item in scored]


def format_usage_card(item: dict[str, Any]) -> str:
    """Formater un résultat sous forme de carte Markdown, verdict matériel inclus."""
    repo_id = str(item.get("repo_id") or "Modèle sans nom")
    pipeline_tag = str(item.get("pipeline_tag") or "Tâche non renseignée")
    likes = _safe_int(item.get("likes"))
    downloads = _safe_int(item.get("downloads"))
    parameters = item.get("parameters")
    hardware_label = str(item.get("hardware_label") or "")

    safe_repo = escape_markdown(repo_id)
    url = f"https://huggingface.co/{quote(repo_id, safe='/')}"
    parameter_label = format_count(parameters) if parameters is not None else "—"

    return (
        f"### [{safe_repo}]({url})\n"
        f"❤️ **{format_count(likes)}** likes · ⬇️ **{format_count(downloads)}** téléchargements · "
        f"🧠 **{parameter_label}** paramètres · **Tâche :** `{escape_markdown(pipeline_tag)}`  \n"
        f"{escape_markdown(hardware_label)}"
    )


def _safe_int(value: Any) -> int:
    """Convertir une valeur de compteur optionnelle sans lever d'erreur."""
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0
