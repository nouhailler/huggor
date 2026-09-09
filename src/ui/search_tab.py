"""Onglet Gradio de recherche multi-critères sur le Hub."""

from __future__ import annotations

import html
import time
from dataclasses import dataclass
from functools import partial
from typing import Any
from urllib.parse import quote

import gradio as gr

from src.api_client import HuggingFaceClient, HuggingFaceClientError, SearchFilters
from src.utils.formatters import format_count

PIPELINE_CHOICES = [
    ("Tous les types de tâche", ""),
    ("Génération de texte", "text-generation"),
    ("Classification de texte", "text-classification"),
    ("Question-réponse", "question-answering"),
    ("Résumé", "summarization"),
    ("Traduction", "translation"),
    ("Embeddings / similarité", "sentence-similarity"),
    ("Génération d'images", "text-to-image"),
    ("Classification d'images", "image-classification"),
    ("Reconnaissance vocale", "automatic-speech-recognition"),
    ("Synthèse vocale", "text-to-speech"),
]

LANGUAGE_CHOICES = [
    ("Toutes les langues", ""),
    ("Français", "fr"),
    ("Anglais", "en"),
    ("Allemand", "de"),
    ("Espagnol", "es"),
    ("Italien", "it"),
    ("Portugais", "pt"),
    ("Arabe", "ar"),
    ("Chinois", "zh"),
    ("Japonais", "ja"),
    ("Multilingue", "multilingual"),
]

LICENSE_CHOICES = [
    ("Toutes les licences", ""),
    ("Apache 2.0", "apache-2.0"),
    ("MIT", "mit"),
    ("BSD 3-Clause", "bsd-3-clause"),
    ("OpenRAIL", "openrail"),
    ("CreativeML OpenRAIL-M", "creativeml-openrail-m"),
    ("Llama 3", "llama3"),
    ("Gemma", "gemma"),
    ("Autre", "other"),
]

SORT_CHOICES = [
    ("Téléchargements", "downloads"),
    ("Likes", "likes"),
    ("Date de création", "created_at"),
    ("Pertinence", "relevance"),
]


@dataclass(frozen=True, slots=True)
class SearchTabComponents:
    """Composants nécessaires au câblage inter-onglets."""

    selected_model: gr.State


def build_search_tab(client: HuggingFaceClient) -> SearchTabComponents:
    """Construire le formulaire, la zone d'état et les cartes de résultats."""
    gr.Markdown(
        "## Rechercher des modèles\n"
        "Affinez la recherche avec les filtres du Hub. Chaque requête reste bornée à 100 résultats."
    )

    with gr.Row():
        query = gr.Textbox(
            label="Mot-clé",
            placeholder="Ex. llama, bert, transcription…",
            scale=3,
        )
        pipeline_tag = gr.Dropdown(
            choices=PIPELINE_CHOICES,
            value="",
            label="Type de tâche",
            scale=2,
        )

    with gr.Row():
        language = gr.Dropdown(
            choices=LANGUAGE_CHOICES,
            value="",
            label="Langue",
        )
        license_name = gr.Dropdown(
            choices=LICENSE_CHOICES,
            value="",
            label="Licence",
        )
        sort = gr.Dropdown(
            choices=SORT_CHOICES,
            value="downloads",
            label="Trier par",
        )

    with gr.Accordion("Paramètres avancés", open=False):
        gr.Markdown(
            "Les nombres de paramètres sont exprimés en milliards. "
            "La valeur 0 désactive la borne correspondante."
        )
        with gr.Row():
            min_parameters = gr.Slider(
                minimum=0,
                maximum=200,
                value=0,
                step=0.1,
                label="Minimum (milliards)",
            )
            max_parameters = gr.Slider(
                minimum=0,
                maximum=200,
                value=0,
                step=0.1,
                label="Maximum (milliards)",
            )
            limit = gr.Slider(
                minimum=5,
                maximum=100,
                value=20,
                step=5,
                label="Nombre de résultats",
            )

    with gr.Row():
        search_button = gr.Button("🔍 Rechercher", variant="primary", scale=2)
        gr.ClearButton(
            [
                query,
                pipeline_tag,
                language,
                license_name,
                min_parameters,
                max_parameters,
                sort,
                limit,
            ],
            value="Réinitialiser",
            scale=1,
        )

    status = gr.Markdown(
        "Lancez une recherche pour explorer les modèles.",
        elem_classes="hf-search-status",
    )
    results = gr.State([])
    selected_model = gr.State(None)

    search_inputs = [
        query,
        pipeline_tag,
        language,
        license_name,
        min_parameters,
        max_parameters,
        sort,
        limit,
    ]
    search_button.click(
        fn=partial(search_for_ui, client),
        inputs=search_inputs,
        outputs=[results, status],
        api_name="search_models",
        api_description="Rechercher des modèles Hugging Face avec des filtres bornés.",
        show_progress="minimal",
        scroll_to_output=True,
        concurrency_limit=2,
        concurrency_id="hub-search",
    )
    query.submit(
        fn=partial(search_for_ui, client),
        inputs=search_inputs,
        outputs=[results, status],
        api_visibility="private",
        show_progress="minimal",
        concurrency_limit=2,
        concurrency_id="hub-search",
    )

    @gr.render(inputs=results, show_progress="hidden")
    def render_model_cards(items: list[dict[str, Any]] | None) -> None:
        """Créer une carte et son bouton de navigation pour chaque résultat."""
        if not items:
            return

        for index, item in enumerate(items):
            repo_id = str(item.get("repo_id") or "")
            with gr.Group(key=f"model-card-{index}-{repo_id}", elem_classes="hf-result-card"):
                with gr.Row(equal_height=False):
                    gr.Markdown(
                        format_model_card(item),
                        container=False,
                        elem_classes="hf-result-content",
                    )
                    details_button = gr.Button(
                        "Voir détails →",
                        variant="secondary",
                        size="sm",
                        min_width=135,
                        scale=0,
                        key=f"details-{index}-{repo_id}",
                    )
                details_button.click(
                    fn=partial(make_navigation_request, repo_id),
                    outputs=selected_model,
                    queue=False,
                    show_progress="hidden",
                    api_visibility="private",
                )

    return SearchTabComponents(selected_model=selected_model)


def search_for_ui(
    client: HuggingFaceClient,
    query: str,
    pipeline_tag: str,
    language: str,
    license_name: str,
    min_parameters_billions: float,
    max_parameters_billions: float,
    sort: str,
    limit: float,
    progress: gr.Progress = gr.Progress(),
) -> tuple[list[dict[str, Any]], str]:
    """Valider le formulaire, interroger le client et préparer l'affichage."""
    progress(0.1, desc="Validation des filtres…")
    try:
        filters = SearchFilters(
            query=query or "",
            pipeline_tag=pipeline_tag or None,
            language=language or None,
            license=license_name or None,
            min_parameters=_billions_to_parameters(min_parameters_billions),
            max_parameters=_billions_to_parameters(max_parameters_billions),
            sort=sort or "downloads",  # type: ignore[arg-type]
            limit=int(limit),
        )
        progress(0.35, desc="Interrogation du Hugging Face Hub…")
        models = client.search_models(filters)
    except ValueError as error:
        return [], f"⚠️ **Filtres invalides :** {html.escape(str(error))}"
    except HuggingFaceClientError as error:
        return [], f"⚠️ **Recherche impossible :** {html.escape(str(error))}"
    except Exception:
        return [], "⚠️ **Recherche impossible :** une erreur inattendue est survenue."

    progress(1, desc="Résultats prêts")
    payload = [model.to_dict() for model in models]
    if not payload:
        return [], "Aucun modèle ne correspond à ces critères."

    suffix = "modèle trouvé" if len(payload) == 1 else "modèles trouvés"
    return payload, f"**{len(payload)} {suffix}.**"


def format_model_card(model: dict[str, Any]) -> str:
    """Formater un résultat sous forme de carte Markdown sûre."""
    repo_id = str(model.get("repo_id") or "Modèle sans nom")
    author = str(model.get("author") or "Auteur inconnu")
    pipeline_tag = str(model.get("pipeline_tag") or "Tâche non renseignée")
    library_name = str(model.get("library_name") or "Bibliothèque non renseignée")
    likes = _safe_int(model.get("likes"))
    downloads = _safe_int(model.get("downloads"))
    parameters = _safe_optional_int(model.get("parameters"))
    tags = [str(tag) for tag in (model.get("tags") or [])][:8]

    safe_repo = _escape_markdown(repo_id)
    safe_author = _escape_markdown(author)
    url = f"https://huggingface.co/{quote(repo_id, safe='/')}"
    tag_line = " ".join(f"`{_escape_inline_code(tag)}`" for tag in tags) or "_Aucun tag_"
    parameter_label = format_count(parameters) if parameters is not None else "—"

    return (
        f"### [{safe_repo}]({url})\n"
        f"**Auteur :** {safe_author}  \n"
        f"❤️ **{format_count(likes)}** likes · ⬇️ **{format_count(downloads)}** téléchargements "
        f"· 🧠 **{parameter_label}** paramètres  \n"
        f"**Tâche :** `{_escape_inline_code(pipeline_tag)}` · "
        f"**Bibliothèque :** `{_escape_inline_code(library_name)}`  \n"
        f"{tag_line}"
    )


def make_navigation_request(repo_id: str) -> dict[str, Any]:
    """Créer un événement unique même si le même modèle est sélectionné deux fois."""
    return {"repo_id": repo_id, "nonce": time.time_ns()}


def resolve_navigation(request: dict[str, Any] | None) -> tuple[str, gr.Tabs]:
    """Préparer le repo_id et la sélection de l'onglet Détails."""
    repo_id = str((request or {}).get("repo_id") or "")
    return repo_id, gr.Tabs(selected="details")


def _billions_to_parameters(value: float | int | None) -> int | None:
    """Convertir la valeur d'un slider en nombre brut de paramètres."""
    if value is None or float(value) <= 0:
        return None
    return int(round(float(value) * 1_000_000_000))


def _safe_int(value: Any) -> int:
    """Convertir une valeur de compteur optionnelle sans lever d'erreur."""
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _safe_optional_int(value: Any) -> int | None:
    """Convertir un compteur optionnel en entier."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _escape_markdown(value: str) -> str:
    """Neutraliser les caractères Markdown dans une valeur issue du Hub."""
    escaped = html.escape(value)
    special_characters = "\\`*_{}[]<>()#+-.!|"
    for character in special_characters:
        escaped = escaped.replace(character, f"\\{character}")
    return escaped


def _escape_inline_code(value: str) -> str:
    """Empêcher une valeur du Hub de fermer un fragment de code Markdown."""
    return html.escape(value).replace("`", "ˋ").replace("\n", " ").replace("\r", " ")
