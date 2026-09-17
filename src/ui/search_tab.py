"""Onglet Gradio de recherche multi-critères sur le Hub."""

from __future__ import annotations

import html
from dataclasses import dataclass
from functools import partial
from typing import Any
from urllib.parse import quote

import gradio as gr

from src.api_client import HuggingFaceClient, HuggingFaceClientError, SearchFilters
from src.ui.details_tab import DetailsTabComponents, load_details_for_ui
from src.utils.formatters import format_count


@dataclass(frozen=True, slots=True)
class TaskOption:
    """Une tâche précise du Hub, reliée à un pipeline_tag réel et un mot-clé optionnel.

    Certaines tâches pédagogiques (Chat, Code, Raisonnement…) ne correspondent à aucun
    pipeline_tag distinct côté Hub : elles partagent le même pipeline_tag que la génération
    de texte et se distinguent seulement par un mot-clé de recherche ajouté à la requête.
    """

    label: str
    pipeline_tag: str
    keyword: str = ""

    @property
    def value(self) -> str:
        """Encoder pipeline_tag et mot-clé dans une seule valeur de menu déroulant."""
        return f"{self.pipeline_tag}::{self.keyword}" if self.keyword else self.pipeline_tag


@dataclass(frozen=True, slots=True)
class TaskDomain:
    """Un domaine pédagogique regroupant plusieurs tâches précises réellement couvertes par le Hub."""

    key: str
    label: str
    description: str
    tasks: tuple[TaskOption, ...]


TASK_DOMAINS: tuple[TaskDomain, ...] = (
    TaskDomain(
        "llm", "🧠 LLM",
        "Modèles de langage : dialogue, rédaction, code, raisonnement et compréhension de texte.",
        (
            TaskOption("Génération de texte", "text-generation"),
            TaskOption("Chat", "text-generation", "chat"),
            TaskOption("Code", "text-generation", "code"),
            TaskOption("Raisonnement", "text-generation", "reasoning"),
            TaskOption("Traduction", "translation"),
            TaskOption("Résumé", "summarization"),
            TaskOption("Classification de texte", "text-classification"),
            TaskOption("Question-réponse", "question-answering"),
        ),
    ),
    TaskDomain(
        "vision", "👁️ Vision", "Analyse et compréhension d'images.",
        (
            TaskOption("Classification d'images", "image-classification"),
            TaskOption("Détection d'objets", "object-detection"),
            TaskOption("Segmentation", "image-segmentation"),
            TaskOption("Classification sans exemple", "zero-shot-image-classification"),
            TaskOption("Estimation de profondeur", "depth-estimation"),
        ),
    ),
    TaskDomain(
        "image", "🖼️ Image", "Génération et transformation d'images.",
        (
            TaskOption("Génération d'images", "text-to-image"),
            TaskOption("Transformation d'images", "image-to-image"),
            TaskOption("Génération sans condition", "unconditional-image-generation"),
        ),
    ),
    TaskDomain(
        "audio", "🎙️ Audio", "Classification et traitement de sons non vocaux.",
        (
            TaskOption("Classification audio", "audio-classification"),
            TaskOption("Audio vers audio", "audio-to-audio"),
        ),
    ),
    TaskDomain(
        "speech", "🗣️ Speech", "Conversion entre parole et texte.",
        (
            TaskOption("Reconnaissance vocale", "automatic-speech-recognition"),
            TaskOption("Synthèse vocale", "text-to-speech"),
        ),
    ),
    TaskDomain(
        "embeddings", "🔤 Embeddings", "Représentations vectorielles de texte.",
        (
            TaskOption("Similarité de phrases", "sentence-similarity"),
            TaskOption("Extraction de caractéristiques", "feature-extraction"),
        ),
    ),
    TaskDomain(
        "multimodal", "🌐 Multimodal", "Modèles combinant plusieurs types d'entrées.",
        (
            TaskOption("Conversation image + texte", "image-text-to-text"),
            TaskOption("Question-réponse visuelle", "visual-question-answering"),
            TaskOption("Question-réponse sur documents", "document-question-answering"),
        ),
    ),
    TaskDomain(
        "reranking", "🧩 Reranking", "Reclassement de résultats de recherche par pertinence.",
        (
            TaskOption("Reclassement (reranking)", "text-ranking"),
        ),
    ),
)

DOMAIN_CHOICES = [("Tous les domaines", "")] + [(domain.label, domain.key) for domain in TASK_DOMAINS]


def _build_flat_pipeline_choices() -> list[tuple[str, str]]:
    """Dériver une liste plate et dédupliquée de pipeline_tag réels, pour l'onglet Analytics."""
    seen: dict[str, str] = {}
    for domain in TASK_DOMAINS:
        for task in domain.tasks:
            seen.setdefault(task.pipeline_tag, task.label)
    return [("Tous les types de tâche", "")] + [(label, tag) for tag, label in seen.items()]


PIPELINE_CHOICES = _build_flat_pipeline_choices()

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


def _domain_task_choices(domain_key: str) -> list[tuple[str, str]]:
    """Lister les tâches précises d'un domaine, ou toutes les tâches préfixées par domaine."""
    if not domain_key:
        return [("Toutes les tâches", "")] + [
            (f"{domain.label.split(' ', 1)[0]} {task.label}", task.value)
            for domain in TASK_DOMAINS
            for task in domain.tasks
        ]
    domain = next((item for item in TASK_DOMAINS if item.key == domain_key), None)
    if domain is None:
        return [("Toutes les tâches", "")]
    return [("Toutes les tâches de ce domaine", "")] + [(task.label, task.value) for task in domain.tasks]


def _update_task_choices(domain_key: str) -> gr.Dropdown:
    """Renouveler les choix de tâche précise quand le domaine change."""
    return gr.Dropdown(
        choices=_domain_task_choices(domain_key),
        value="",
        info="Choisissez une tâche précise pour filtrer réellement les résultats.",
    )


def _parse_task_value(value: str) -> tuple[str | None, str]:
    """Décomposer la valeur du menu Tâche précise en pipeline_tag et mot-clé de recherche."""
    if not value:
        return None, ""
    if "::" in value:
        pipeline, keyword = value.split("::", 1)
        return (pipeline or None), keyword
    return value, ""


def _describe_task_selection(value: str) -> gr.Dropdown:
    """Expliciter le filtre réellement appliqué : pipeline_tag et mot-clé implicite éventuel."""
    pipeline, keyword = _parse_task_value(value)
    if pipeline and keyword:
        info = f"Filtre réel : tâche « {pipeline} » + mot-clé « {keyword} »."
    elif pipeline:
        info = f"Filtre réel : tâche « {pipeline} »."
    else:
        info = "Choisissez une tâche précise pour filtrer réellement les résultats."
    return gr.Dropdown(info=info)


def build_search_tab(
    client: HuggingFaceClient,
    details: DetailsTabComponents,
    app_tabs: gr.Tabs,
) -> None:
    """Construire le formulaire, la zone d'état et les cartes de résultats."""
    gr.Markdown(
        "## Rechercher des modèles\n"
        "Affinez la recherche avec les filtres du Hub. Chaque requête reste bornée à 100 résultats."
    )
    gr.Markdown(
        "🤗 Modèles → choisissez un domaine puis une tâche précise, réellement couverte par le Hub : "
        "seule la tâche précise filtre effectivement les résultats.",
        elem_classes="hf-search-status",
    )

    with gr.Row():
        query = gr.Textbox(
            label="Mot-clé",
            placeholder="Ex. llama, bert, transcription…",
            scale=3,
        )
        domain = gr.Dropdown(
            choices=DOMAIN_CHOICES,
            value="",
            label="Domaine",
            scale=2,
        )
        pipeline_tag = gr.Dropdown(
            choices=_domain_task_choices(""),
            value="",
            label="Tâche précise",
            info="Choisissez une tâche précise pour filtrer réellement les résultats.",
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
                domain,
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

    domain.change(
        fn=_update_task_choices,
        inputs=domain,
        outputs=pipeline_tag,
        api_visibility="private",
        show_progress="hidden",
    )
    pipeline_tag.change(
        fn=_describe_task_selection,
        inputs=pipeline_tag,
        outputs=pipeline_tag,
        api_visibility="private",
        show_progress="hidden",
    )

    status = gr.Markdown(
        "Lancez une recherche pour explorer les modèles.",
        elem_classes="hf-search-status",
    )
    results = gr.State([])

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
    real_pipeline_tag, task_keyword = _parse_task_value(pipeline_tag)
    effective_query = " ".join(part for part in ((query or "").strip(), task_keyword) if part)
    try:
        filters = SearchFilters(
            query=effective_query,
            pipeline_tag=real_pipeline_tag,
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


def select_model_for_details(repo_id: str) -> tuple[str, gr.Tabs]:
    """Préremplir la fiche et sélectionner directement l'onglet Détails."""
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
