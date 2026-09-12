"""Onglet Gradio présentant la fiche complète d'un modèle."""

from __future__ import annotations

import html
import json
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path
from typing import Any
from urllib.parse import quote

import gradio as gr

from src.api_client import HuggingFaceClient, HuggingFaceClientError, ModelDetails, ModelFile
from src.model_analysis import (
    CompatibilityFinding,
    DownloadRecommendation,
    TechnicalProfile,
    classify_file,
    extract_technical_profile,
    inspect_compatibility,
    recommend_download,
)
from src.utils.favorites import FavoritesError, FavoritesStore
from src.utils.formatters import format_bytes, format_count

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@dataclass(frozen=True, slots=True)
class DetailsTabComponents:
    """Composants accessibles depuis les autres onglets."""

    repo_id: gr.Textbox
    load_outputs: tuple[gr.components.Component, ...]


@dataclass(slots=True)
class _FileTreeNode:
    """Nœud interne utilisé pour construire l'arborescence des fichiers."""

    directories: dict[str, _FileTreeNode] = field(default_factory=dict)
    files: list[ModelFile] = field(default_factory=list)


def build_details_tab(
    client: HuggingFaceClient,
    favorites: FavoritesStore | None = None,
    repo_id: gr.Textbox | None = None,
) -> DetailsTabComponents:
    """Construire la fiche modèle et câbler ses actions."""
    favorites_store = favorites or FavoritesStore(_PROJECT_ROOT / "data" / "favorites.json")

    gr.Markdown(
        "## Examiner un modèle\n"
        "Chargez les métadonnées, la Model Card et les fichiers d’un dépôt du Hub."
    )
    with gr.Row():
        if repo_id is None:
            repo_id = create_repo_id_input()
        else:
            repo_id.render()
        load_button = gr.Button("📄 Charger la fiche", variant="primary", scale=1, min_width=170)
        favorite_button = gr.Button(
            "⭐ Ajouter aux favoris",
            interactive=False,
            scale=1,
            min_width=180,
        )

    status = gr.Markdown(
        "Saisissez un identifiant de modèle pour afficher sa fiche.",
        elem_classes="hf-details-status",
    )
    loaded_repo_id = gr.State("")
    with gr.Row(equal_height=False):
        identity = gr.Markdown("", elem_classes=["hf-tech-card", "hf-identity-card"])
        architecture = gr.Markdown("", elem_classes=["hf-tech-card", "hf-architecture-card"])

    compatibility = gr.Markdown("", elem_classes=["hf-tech-card", "hf-compatibility-card"])
    download_advice = gr.Markdown("", elem_classes="hf-download-advice")

    with gr.Tabs():
        with gr.Tab("📖 Model Card"):
            model_card = gr.Markdown(
                "_La Model Card apparaîtra ici._",
                sanitize_html=True,
                header_links=True,
                elem_classes="hf-model-card",
            )
        with gr.Tab("🗂️ Fichiers"):
            file_inventory = gr.Dataframe(
                headers=["Fichier", "Rôle", "Format", "Taille", "À télécharger"],
                datatype=["str", "str", "str", "str", "str"],
                value=[],
                label="Inventaire des fichiers",
                interactive=False,
                wrap=True,
                max_height=560,
                show_search="search",
                show_row_numbers=True,
            )
            files_tree = gr.Markdown(
                "_L’arborescence des fichiers apparaîtra ici._",
                elem_classes="hf-file-tree",
            )
        with gr.Tab("💻 Code"):
            gr.Markdown(
                "Les snippets utilisent `HF_TOKEN` depuis l’environnement. Vérifiez les dépendances "
                "de la Model Card et la disponibilité d’un fournisseur pour `InferenceClient`. "
                "Les dépôts GGUF/adapters peuvent nécessiter le modèle de base pour Transformers."
            )
            with gr.Row(equal_height=False):
                local_code = gr.Code(
                    language="python",
                    label="Transformers / bibliothèque locale",
                    lines=14,
                    max_lines=24,
                    interactive=False,
                    buttons=["copy"],
                )
                inference_code = gr.Code(
                    language="python",
                    label="Hugging Face InferenceClient",
                    lines=14,
                    max_lines=24,
                    interactive=False,
                    buttons=["copy"],
                )

    with gr.Accordion("Métadonnées techniques brutes", open=False):
        raw_metadata = gr.JSON(
            value={},
            label="Configuration et métadonnées de la Model Card",
            show_indices=True,
            buttons=["copy"],
        )

    favorite_status = gr.Markdown("", elem_classes="hf-favorite-status")

    load_outputs = [
        loaded_repo_id,
        status,
        identity,
        architecture,
        compatibility,
        download_advice,
        raw_metadata,
        model_card,
        file_inventory,
        files_tree,
        local_code,
        inference_code,
        favorite_button,
        favorite_status,
    ]
    load_button.click(
        fn=partial(load_details_for_ui, client),
        inputs=repo_id,
        outputs=load_outputs,
        api_name="model_details",
        api_description="Charger les informations détaillées d'un modèle Hugging Face.",
        show_progress="minimal",
        concurrency_limit=2,
        concurrency_id="hub-details",
    )
    repo_id.submit(
        fn=partial(load_details_for_ui, client),
        inputs=repo_id,
        outputs=load_outputs,
        api_visibility="private",
        show_progress="minimal",
        concurrency_limit=2,
        concurrency_id="hub-details",
    )
    favorite_button.click(
        fn=partial(add_favorite_for_ui, favorites_store),
        inputs=loaded_repo_id,
        outputs=favorite_status,
        api_visibility="private",
        show_progress="hidden",
    )

    return DetailsTabComponents(repo_id=repo_id, load_outputs=tuple(load_outputs))


def create_repo_id_input(*, render: bool = True) -> gr.Textbox:
    """Créer le champ partageable entre les onglets Recherche et Détails."""
    return gr.Textbox(
        label="Identifiant du modèle",
        placeholder="Ex. meta-llama/Llama-3.2-1B",
        info="Le bouton « Voir détails » d'une recherche remplit automatiquement ce champ.",
        scale=4,
        render=render,
    )


def load_details_for_ui(
    client: HuggingFaceClient,
    repo_id: str,
    progress: gr.Progress = gr.Progress(),
) -> tuple[
    str,
    str,
    str,
    str,
    str,
    str,
    dict[str, Any],
    str,
    list[list[str]],
    str,
    str,
    str,
    gr.Button,
    str,
]:
    """Charger et formater toutes les parties visibles de la fiche modèle."""
    progress(0.1, desc="Validation du modèle…")
    try:
        details = client.get_model_info(repo_id or "")
        progress(0.55, desc="Chargement de la Model Card…")
        card = client.get_model_card(details.summary.repo_id)
    except ValueError as error:
        return _empty_details_response(f"⚠️ **Identifiant invalide :** {html.escape(str(error))}")
    except HuggingFaceClientError as error:
        return _empty_details_response(f"⚠️ **Chargement impossible :** {html.escape(str(error))}")
    except Exception:
        return _empty_details_response(
            "⚠️ **Chargement impossible :** une erreur inattendue est survenue."
        )

    progress(0.8, desc="Préparation de la fiche…")
    profile = extract_technical_profile(details)
    compatibility = inspect_compatibility(details)
    recommendation = recommend_download(details)
    local_snippet, inference_snippet = generate_code_snippets(details)
    progress(1, desc="Fiche prête")
    return (
        details.summary.repo_id,
        f"✅ Fiche de **{_escape_markdown(details.summary.repo_id)}** chargée.",
        format_identity_section(details),
        format_architecture_section(profile),
        format_compatibility_section(compatibility),
        format_download_recommendation(recommendation),
        build_raw_metadata(details, profile, compatibility, recommendation),
        card,
        build_file_inventory(details, recommendation),
        format_file_tree(details),
        local_snippet,
        inference_snippet,
        gr.Button(interactive=True),
        "",
    )


def add_favorite_for_ui(store: FavoritesStore, repo_id: str) -> str:
    """Ajouter le modèle chargé aux favoris et produire un message utilisateur."""
    if not repo_id:
        return "⚠️ Chargez d’abord une fiche modèle."
    try:
        created = store.add(repo_id)
    except (ValueError, FavoritesError) as error:
        return f"⚠️ **Favori non enregistré :** {html.escape(str(error))}"
    except Exception:
        return "⚠️ **Favori non enregistré :** une erreur inattendue est survenue."

    safe_repo_id = _escape_markdown(repo_id)
    if created:
        return f"⭐ **{safe_repo_id}** a été ajouté aux favoris."
    return f"ℹ️ **{safe_repo_id}** figure déjà dans les favoris."


def format_identity_section(details: ModelDetails) -> str:
    """Présenter l'identité et la popularité du modèle."""
    summary = details.summary
    license_name = details.card_data.get("license")
    languages = details.card_data.get("language")
    repo_url = f"https://huggingface.co/{quote(summary.repo_id, safe='/')}"

    rows = [
        ("Auteur", summary.author),
        ("Création", summary.created_at),
        ("Dernière modification", summary.last_modified),
        ("Licence", license_name),
        ("Pipeline", summary.pipeline_tag),
        ("Bibliothèque", summary.library_name),
        ("Langue(s)", languages),
        ("Téléchargements", format_count(summary.downloads)),
        ("Likes", format_count(summary.likes)),
        ("Stockage du dépôt", format_bytes(details.used_storage)),
        ("Accès restreint", _format_gated(summary.gated)),
    ]
    table = "\n".join(
        f"| **{label}** | {_escape_markdown(_display_value(value))} |" for label, value in rows
    )
    tags = " ".join(f"`{_escape_inline_code(tag)}`" for tag in summary.tags[:16])

    return (
        "### 🪪 Identité\n\n"
        f"#### [{_escape_markdown(summary.repo_id)}]({repo_url})\n\n"
        "| Champ | Valeur |\n"
        "|---|---|\n"
        f"{table}\n\n"
        f"**Tags principaux :** {tags or '—'}"
    )


def format_architecture_section(profile: TechnicalProfile) -> str:
    """Présenter les caractéristiques d'architecture normalisées."""
    rows = [
        ("Famille", profile.family),
        ("Classe(s)", profile.model_classes),
        ("Paramètres", format_count(profile.parameters)),
        ("Dtype", profile.dtype),
        ("Contexte maximal", _format_integer(profile.context_length, "tokens")),
        ("Vocabulaire", _format_integer(profile.vocabulary_size, "tokens")),
        ("Quantification", profile.quantization),
    ]
    table = "\n".join(
        f"| **{label}** | {_escape_markdown(_display_value(value))} |" for label, value in rows
    )
    return "### 🧠 Architecture\n\n| Champ | Valeur |\n|---|---|\n" + table


def format_compatibility_section(findings: tuple[CompatibilityFinding, ...]) -> str:
    """Afficher les compatibilités avec une légende empêchant les faux positifs."""
    labels = {
        "detected": "✅ Détecté",
        "probable": "🟡 Probable",
        "conversion": "🔄 Conversion",
        "not_detected": "⚪ Non détecté",
    }
    rows = "\n".join(
        f"| **{_escape_markdown(item.name)}** | {labels[item.state]} | "
        f"{_escape_markdown(item.reason)} |"
        for item in findings
    )
    return (
        "### 🧩 Compatibilité\n\n"
        "| Format / moteur | Statut | Indice |\n"
        "|---|---|---|\n"
        f"{rows}\n\n"
        "_« Non détecté » ne signifie pas incompatible. Ces indices ne remplacent pas une validation "
        "de l’architecture avec la version du moteur que vous utilisez._"
    )


def format_download_recommendation(recommendation: DownloadRecommendation) -> str:
    """Répondre clairement à la question du fichier réellement nécessaire."""
    primary = _format_recommended_files(recommendation.primary_files)
    companions = _format_recommended_files(recommendation.companion_files)
    size = format_bytes(recommendation.estimated_bytes)
    warning = (
        f"\n\n> ⚠️ {_escape_markdown(recommendation.warning)}"
        if recommendation.warning else ""
    )
    companion_block = (
        f"\n\n**Fichiers associés :**\n\n{companions}" if recommendation.companion_files else ""
    )
    return (
        "### ⬇️ Quel fichier faut-il réellement télécharger ?\n\n"
        f"#### {recommendation.headline}\n\n"
        f"{_escape_markdown(recommendation.explanation)}\n\n"
        f"**Poids / artefacts principaux :**\n\n{primary}\n\n"
        f"**Volume estimé des fichiers sélectionnés :** {size}"
        f"{companion_block}{warning}\n\n"
        "```bash\n"
        f"{recommendation.command}\n"
        "```"
    )


def build_file_inventory(
    details: ModelDetails,
    recommendation: DownloadRecommendation,
) -> list[list[str]]:
    """Créer l'inventaire tabulaire complet des fichiers et de leur rôle."""
    rows = []
    for model_file in sorted(details.files, key=lambda item: item.path.casefold()):
        role, file_format, selected = classify_file(model_file, recommendation)
        rows.append(
            [
                model_file.path,
                role,
                file_format,
                format_bytes(model_file.size),
                "✅ Oui" if selected else "—",
            ]
        )
    return rows


def build_raw_metadata(
    details: ModelDetails,
    profile: TechnicalProfile | None = None,
    compatibility: tuple[CompatibilityFinding, ...] | None = None,
    recommendation: DownloadRecommendation | None = None,
) -> dict[str, Any]:
    """Rassembler les informations techniques sans les objets internes du SDK."""
    technical_profile = profile or extract_technical_profile(details)
    compatibility_findings = compatibility or inspect_compatibility(details)
    download_recommendation = recommendation or recommend_download(details)
    return {
        "model": details.summary.to_dict(),
        "used_storage": details.used_storage,
        "tensor_dtypes": details.tensor_dtypes,
        "technical_profile": technical_profile.to_dict(),
        "compatibility": [item.to_dict() for item in compatibility_findings],
        "download_recommendation": download_recommendation.to_dict(),
        "card_data": details.card_data,
        "config": details.config,
    }


def format_file_tree(details: ModelDetails) -> str:
    """Construire une arborescence complète avec la taille de chaque fichier."""
    root = _FileTreeNode()
    for model_file in sorted(details.files, key=lambda item: item.path.casefold()):
        parts = _safe_path_parts(model_file.path)
        if not parts:
            continue
        node = root
        for directory in parts[:-1]:
            node = node.directories.setdefault(directory, _FileTreeNode())
        node.files.append(
            ModelFile(path=parts[-1], size=model_file.size, blob_id=model_file.blob_id)
        )

    lines = [f"{_escape_code_text(details.summary.repo_id)}/"]
    _render_tree(root, lines, prefix="")
    known_total = sum(item.size for item in details.files if item.size is not None)
    size_label = format_bytes(known_total) if details.files else "0 o"
    if any(item.size is None for item in details.files):
        size_label = f"au moins {size_label} (tailles partielles)"
    count = len(details.files)
    suffix = "fichier" if count == 1 else "fichiers"
    return f"**{count} {suffix} · {size_label}**\n\n```text\n" + "\n".join(lines) + "\n```"


def generate_code_snippets(details: ModelDetails) -> tuple[str, str]:
    """Générer les exemples local et distant adaptés au pipeline du modèle."""
    repo_literal = json.dumps(details.summary.repo_id, ensure_ascii=False)
    task = details.summary.pipeline_tag or "text-generation"
    task_literal = json.dumps(task, ensure_ascii=False)

    if task == "text-to-image" or details.summary.library_name == "diffusers":
        local = (
            "import os\n"
            "from diffusers import DiffusionPipeline\n\n"
            f"model_id = {repo_literal}\n"
            "pipe = DiffusionPipeline.from_pretrained(\n"
            "    model_id,\n"
            "    token=os.getenv(\"HF_TOKEN\"),\n"
            ")\n"
            "image = pipe(\"Décrivez l’image à générer\").images[0]\n"
            "image.save(\"generation.png\")\n"
        )
    else:
        local_call = _transformers_call(task)
        local = (
            "import os\n"
            "from transformers import pipeline\n\n"
            f"model_id = {repo_literal}\n"
            "pipe = pipeline(\n"
            f"    task={task_literal},\n"
            "    model=model_id,\n"
            "    token=os.getenv(\"HF_TOKEN\"),\n"
            ")\n"
            f"{local_call}\n"
            "print(result)\n"
        )

    inference_call = _inference_client_call(task)
    inference = (
        "import os\n"
        "from huggingface_hub import InferenceClient\n\n"
        f"model_id = {repo_literal}\n"
        "client = InferenceClient(\n"
        "    model=model_id,\n"
        "    token=os.getenv(\"HF_TOKEN\"),\n"
        ")\n"
        f"{inference_call}\n"
    )
    return local, inference


def _empty_details_response(
    message: str,
) -> tuple[
    str,
    str,
    str,
    str,
    str,
    str,
    dict[str, Any],
    str,
    list[list[str]],
    str,
    str,
    str,
    gr.Button,
    str,
]:
    """Réinitialiser la fiche après une erreur de chargement."""
    return (
        "",
        message,
        "",
        "",
        "",
        "",
        {},
        "_Model Card indisponible._",
        [],
        "_Fichiers indisponibles._",
        "",
        "",
        gr.Button(interactive=False),
        "",
    )


def _render_tree(node: _FileTreeNode, lines: list[str], prefix: str) -> None:
    """Ajouter récursivement les lignes d'un nœud à l'arborescence."""
    entries: list[tuple[str, _FileTreeNode | None, ModelFile | None]] = []
    entries.extend(
        (name, child, None) for name, child in sorted(node.directories.items(), key=lambda item: item[0].casefold())
    )
    entries.extend(
        (item.path, None, item) for item in sorted(node.files, key=lambda item: item.path.casefold())
    )

    for index, (name, directory, model_file) in enumerate(entries):
        is_last = index == len(entries) - 1
        connector = "└── " if is_last else "├── "
        safe_name = _escape_code_text(name)
        if directory is not None:
            lines.append(f"{prefix}{connector}{safe_name}/")
            child_prefix = prefix + ("    " if is_last else "│   ")
            _render_tree(directory, lines, child_prefix)
        elif model_file is not None:
            lines.append(f"{prefix}{connector}{safe_name}  ({format_bytes(model_file.size)})")


def _safe_path_parts(path: str) -> list[str]:
    """Découper un chemin distant sans conserver de segments ambigus."""
    return [part for part in path.replace("\\", "/").split("/") if part not in {"", ".", ".."}]


def _transformers_call(task: str) -> str:
    """Choisir un appel d'exemple compatible avec un pipeline Transformers."""
    calls = {
        "automatic-speech-recognition": 'result = pipe("audio.wav")',
        "fill-mask": 'result = pipe(f"Paris est la capitale de {pipe.tokenizer.mask_token}.")',
        "image-classification": 'result = pipe("image.jpg")',
        "question-answering": (
            'result = pipe(question="Votre question", context="Le texte contenant la réponse")'
        ),
        "summarization": 'result = pipe("Le long texte à résumer")',
        "translation": 'result = pipe("Le texte à traduire")',
        "text-classification": 'result = pipe("Le texte à classifier")',
        "text-generation": 'result = pipe("Votre prompt", max_new_tokens=128)',
        "text-to-speech": 'result = pipe("Le texte à synthétiser")',
    }
    return calls.get(task, 'result = pipe("Votre entrée")')


def _inference_client_call(task: str) -> str:
    """Choisir la méthode InferenceClient correspondant au pipeline."""
    calls = {
        "automatic-speech-recognition": 'result = client.automatic_speech_recognition("audio.wav")\nprint(result)',
        "feature-extraction": 'result = client.feature_extraction("Votre texte")\nprint(result)',
        "fill-mask": 'result = client.fill_mask("Paris is the capital of [MASK].")\nprint(result)',
        "image-classification": 'result = client.image_classification("image.jpg")\nprint(result)',
        "question-answering": (
            'result = client.question_answering(\n'
            '    question="Votre question",\n'
            '    context="Le texte contenant la réponse",\n'
            ')\n'
            'print(result)'
        ),
        "sentence-similarity": (
            'result = client.sentence_similarity(\n'
            '    sentence="Phrase de référence",\n'
            '    other_sentences=["Phrase à comparer"],\n'
            ')\n'
            'print(result)'
        ),
        "summarization": 'result = client.summarization("Le long texte à résumer")\nprint(result)',
        "text-classification": 'result = client.text_classification("Le texte à classifier")\nprint(result)',
        "text-generation": 'result = client.text_generation("Votre prompt", max_new_tokens=128)\nprint(result)',
        "text-to-image": (
            'image = client.text_to_image("Décrivez l’image à générer")\n'
            'image.save("generation.png")'
        ),
        "text-to-speech": (
            'audio = client.text_to_speech("Le texte à synthétiser")\n'
            'with open("speech.flac", "wb") as file:\n'
            '    file.write(audio)'
        ),
        "translation": 'result = client.translation("Le texte à traduire")\nprint(result)',
    }
    return calls.get(task, '# Adaptez la méthode à la tâche du modèle.\nprint(client)')


def _format_gated(value: bool | str) -> str:
    """Afficher clairement le niveau de restriction du dépôt."""
    if value is True:
        return "Oui"
    if isinstance(value, str) and value:
        return value
    return "Non"


def _format_integer(value: int | None, unit: str) -> str:
    """Afficher un entier technique avec des séparateurs lisibles."""
    if value is None:
        return "Non renseigné"
    return f"{value:,}".replace(",", "\u202f") + f" {unit}"


def _format_recommended_files(files: tuple[str, ...]) -> str:
    """Afficher sans ambiguïté la liste exacte des fichiers conseillés."""
    if not files:
        return "_Aucun fichier unique identifié._"
    return "\n".join(f"- `{_escape_inline_code(path)}`" for path in files)


def _display_value(value: Any) -> str:
    """Aplatir une métadonnée pour son affichage dans un tableau."""
    if value is None or value == "":
        return "—"
    if isinstance(value, (list, tuple, set)):
        return ", ".join(_display_value(item) for item in value) or "—"
    if isinstance(value, dict):
        return ", ".join(f"{key}: {_display_value(item)}" for key, item in value.items())
    return str(value)


def _escape_markdown(value: str) -> str:
    """Neutraliser les caractères Markdown d'une métadonnée distante."""
    escaped = html.escape(value).replace("\n", " ").replace("\r", " ")
    for character in "\\`*_{}[]<>()#+-.!|":
        escaped = escaped.replace(character, f"\\{character}")
    return escaped


def _escape_inline_code(value: str) -> str:
    """Empêcher un tag de fermer son fragment de code Markdown."""
    return html.escape(value).replace("`", "ˋ").replace("\n", " ").replace("\r", " ")


def _escape_code_text(value: str) -> str:
    """Rendre un nom de fichier sûr à l'intérieur d'un bloc de code."""
    return "".join(character if character.isprintable() else "�" for character in value).replace("`", "ˋ")
