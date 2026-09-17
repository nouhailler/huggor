"""Onglet Gradio présentant la fiche complète d'un modèle."""

from __future__ import annotations

import html
import json
from dataclasses import dataclass, field
from functools import partial
from typing import Any
from urllib.parse import quote

from src.paths import data_directory

import gradio as gr

from src.api_client import HuggingFaceClient, HuggingFaceClientError, ModelDetails, ModelFile, SearchFilters
from src.hardware_advisor import HardwareAdvice, MemoryEstimate, advise_hardware
from src.model_analysis import (
    CompatibilityFinding,
    DownloadRecommendation,
    TechnicalProfile,
    classify_file,
    detect_precision_formats,
    extract_technical_profile,
    inspect_compatibility,
    recommend_download,
)
from src.quantization_search import QuantizedVariant, extract_base_name, find_quantized_variants
from src.similar_models import SimilarModel, find_similar_models
from src.utils.favorites import FavoritesError, FavoritesStore
from src.utils.formatters import (
    escape_inline_code as _escape_inline_code,
    escape_markdown as _escape_markdown,
    format_bytes,
    format_count,
)




_FIELD_HELP = {
    "Auteur": "Personne ou organisation qui publie ce modèle sur Hugging Face. Ce compte n’est pas forcément son créateur initial.",
    "Création": "Date de création de l’espace où sont publiés les fichiers du modèle, appelé dépôt.",
    "Dernière modification": "Date de la dernière mise à jour du dépôt : elle peut concerner les fichiers ou simplement la documentation.",
    "Licence": "Conditions fixées par l’auteur pour utiliser, modifier ou partager le modèle. Consultez le texte de la licence pour connaître les usages autorisés.",
    "Pipeline": "Tâche principale prévue pour ce modèle, par exemple rédiger du texte, traduire ou classer des messages.",
    "Bibliothèque": "Ensemble d’outils logiciels utilisé pour charger et faire fonctionner le modèle, par exemple Transformers.",
    "Langue(s)": "Langues déclarées par l’auteur. Leur présence ne garantit pas la même qualité de résultat dans chacune d’elles.",
    "Téléchargements": "Nombre de téléchargements comptabilisés par Hugging Face sur sa période de mesure. C’est un indice d’utilisation, pas une mesure de qualité ni un nombre de personnes.",
    "Likes": "Nombre de personnes ayant marqué leur intérêt pour ce modèle sur Hugging Face. Cela ne garantit pas sa fiabilité.",
    "Stockage du dépôt": "Espace occupé par l’ensemble des fichiers publiés. Il peut inclure plusieurs versions du modèle et ne correspond pas à la mémoire nécessaire pour l’exécuter.",
    "Accès restreint": "Indique si l’auteur impose des conditions d’accès, comme accepter un accord ou obtenir une autorisation avant de télécharger le modèle.",
    "Tags principaux": "Mots-clés décrivant le modèle, ses usages ou ses formats. Ils aident à le retrouver et proviennent des informations du dépôt.",
    "Famille": "Type général de conception du modèle, par exemple BERT ou Llama. Les modèles d’une même famille partagent des principes de fonctionnement.",
    "Classe(s)": "Nom technique utilisé par le logiciel pour charger le modèle avec sa tâche prévue. Ce n’est pas un classement de qualité.",
    "Paramètres": "Nombre de valeurs que le modèle a apprises pendant son entraînement. Plus il en contient, plus il demande généralement de mémoire ; cela ne garantit pas de meilleurs résultats. M signifie millions et B milliards.",
    "Dtype": "Précision des nombres utilisés pour représenter le modèle, par exemple float16. Une précision plus faible réduit généralement la mémoire nécessaire.",
    "Contexte maximal": "Quantité maximale de texte que le modèle peut traiter à la fois, mesurée en tokens : des morceaux de mots ou des signes. Pour la génération de texte, la question et la réponse partagent généralement cette limite.",
    "Vocabulaire": "Nombre de tokens différents que le modèle reconnaît. Un token peut être un mot, un morceau de mot ou un signe ; ce n’est donc pas le nombre de mots ou de langues connus.",
    "Quantification": "Technique qui réduit la précision des nombres du modèle pour prendre moins de place et de mémoire. Elle peut modifier la qualité des réponses et nécessite des outils adaptés.",
    "Format / moteur": "Un format décrit comment le modèle est enregistré dans ses fichiers. Un moteur ou une bibliothèque est un logiciel qui permet de le faire fonctionner.",
    "Statut": "Niveau de compatibilité estimé à partir des fichiers et des informations publiées. Le modèle n’a pas été exécuté pour vérifier ces résultats.",
    "Indice": "Information du dépôt utilisée pour établir le statut, par exemple la présence d’un fichier ou d’un mot-clé.",
    "Transformers": "Bibliothèque Python permettant de charger et d’utiliser de nombreux modèles. Le modèle doit être pris en charge par la version installée.",
    "Safetensors": "Format de fichier contenant les valeurs apprises par le modèle, appelées poids. Il faut aussi un logiciel compatible pour utiliser ces fichiers.",
    "GGUF": "Format de fichier souvent utilisé pour exécuter des modèles sur son ordinateur, notamment avec llama.cpp ou Ollama.",
    "GPTQ": "Méthode de compression des valeurs du modèle pour réduire la mémoire nécessaire, souvent utilisée sur carte graphique. Elle nécessite un logiciel compatible.",
    "AWQ": "Méthode de compression qui cherche à préserver les valeurs importantes du modèle tout en réduisant la mémoire nécessaire. Elle nécessite un logiciel compatible.",
    "MLX": "Ensemble d’outils pour faire fonctionner des modèles notamment sur les Mac équipés d’une puce Apple Silicon, comme les puces M1 ou M2.",
    "Ollama": "Application qui simplifie le téléchargement et l’exécution de modèles sur votre ordinateur. Le modèle doit être dans un format pris en charge.",
    "vLLM": "Logiciel conçu pour servir des modèles de génération de texte et traiter efficacement plusieurs demandes, souvent sur un serveur avec carte graphique.",
    "llama.cpp": "Logiciel qui permet d’exécuter des modèles de langage sur différents ordinateurs, avec le processeur et éventuellement une carte graphique. Il utilise notamment le format GGUF.",
    "TGI": "Text Generation Inference : logiciel de Hugging Face pour faire fonctionner un modèle de génération de texte sur un serveur et le rendre accessible à des applications.",
    "detected": "Un indice explicite a été trouvé dans le dépôt. Cela ne garantit pas que le modèle fonctionnera sur votre matériel avec votre version du logiciel.",
    "probable": "Les caractéristiques du modèle suggèrent une compatibilité, mais elle reste à vérifier avec le logiciel choisi.",
    "conversion": "Les fichiers doivent être transformés dans un autre format avant utilisation. La conversion et la prise en charge du modèle restent à vérifier.",
    "not_detected": "Aucun indice suffisant n’a été trouvé. Le modèle peut néanmoins être compatible : consultez sa documentation.",
    "RAM estimée": "Mémoire vive approximative nécessaire pour charger les poids du modèle à cette précision, marge d’exécution incluse. C’est un ordre de grandeur, pas une mesure exacte.",
    "VRAM recommandée": "Mémoire de carte graphique conseillée pour exécuter une version quantifiée du modèle avec un contexte d’usage courant.",
    "CPU (16 Go RAM)": "Capacité à faire tourner une version quantifiée du modèle sur un ordinateur équipé de 16 Go de mémoire vive, sans carte graphique dédiée.",
    "GPU 8 Go": "Capacité à charger une version quantifiée du modèle sur une carte graphique disposant de 8 Go de mémoire vidéo.",
    "GPU 4 Go": "Capacité à charger une version quantifiée du modèle sur une carte graphique d’entrée de gamme disposant de 4 Go de mémoire vidéo.",
    "CPU seul (sans GPU)": "Capacité à se passer complètement d’une carte graphique dédiée, avec une machine bien pourvue en mémoire vive.",
    "FP32": "Nombres à virgule flottante sur 32 bits : la précision la plus complète, mais aussi la plus gourmande en mémoire.",
    "FP16": "Nombres à virgule flottante sur 16 bits : réduit la mémoire par rapport au FP32, avec une perte de précision généralement mineure.",
    "BF16": "Variante du FP16 utilisée pour l’entraînement et l’inférence, avec la même mémoire que le FP16 mais une plage de valeurs proche du FP32.",
    "INT8": "Nombres entiers sur 8 bits : une quantification qui réduit fortement la mémoire, distincte des variantes GGUF Q8.",
    "Q8": "Variante de quantification GGUF proche de 8 bits par paramètre, parmi les moins compressées de ce format.",
    "Q6": "Variante de quantification GGUF autour de 6 bits par paramètre.",
    "Q5": "Variante de quantification GGUF autour de 5 bits par paramètre.",
    "Q4": "Variante de quantification GGUF autour de 4 bits par paramètre : un compromis courant entre mémoire et qualité.",
    "Q3": "Variante de quantification GGUF autour de 3 bits par paramètre, très compressée.",
    "Q2": "Variante de quantification GGUF autour de 2 bits par paramètre, la plus compressée : la qualité peut être fortement affectée.",
    "EXL2": "Format de quantification utilisé par ExLlamaV2, pensé pour l’inférence rapide sur carte graphique.",
}

_HARDWARE_STATUS_LABELS = {
    "ok": "✅",
    "warning": "⚠️",
    "no": "❌",
    "unknown": "⚪",
}


def _field_with_help(label: str, *, help_key: str | None = None) -> str:
    """Ajouter une aide accessible au survol, au clavier et au toucher."""
    key = help_key or label
    explanation = _FIELD_HELP.get(key, "Format ou logiciel mentionné dans les informations du modèle. Consultez sa documentation pour connaître son utilisation.")
    safe_label = html.escape(label)
    safe_help = html.escape(explanation)
    return (
        f'<span class="hf-field-label">{safe_label} '
        f'<button type="button" class="hf-field-help" '
        f'aria-label="Aide pour {safe_label} : {safe_help}">ⓘ'
        f'<span class="hf-field-tooltip" role="tooltip">{safe_help}</span>'
        '</button></span>'
    )


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
    favorites_store = favorites or FavoritesStore(data_directory() / "favorites.json")

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
    precision_formats = gr.Markdown("", elem_classes=["hf-tech-card", "hf-compatibility-card"])
    quantized_variants = gr.Markdown("", elem_classes=["hf-tech-card", "hf-hardware-card"])
    similar_models = gr.Markdown("", elem_classes=["hf-tech-card", "hf-hardware-card"])
    hardware_advice = gr.Markdown("", elem_classes=["hf-tech-card", "hf-hardware-card"])
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
        precision_formats,
        quantized_variants,
        similar_models,
        hardware_advice,
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
    precision_findings = detect_precision_formats(details, profile, compatibility)
    recommendation = recommend_download(details)
    hardware = advise_hardware(profile, compatibility)
    variants = _search_quantized_variants(client, details.summary.repo_id)
    similar = _search_similar_models(client, details, profile)
    local_snippet, inference_snippet = generate_code_snippets(details)
    progress(1, desc="Fiche prête")
    return (
        details.summary.repo_id,
        f"✅ Fiche de **{_escape_markdown(details.summary.repo_id)}** chargée.",
        format_identity_section(details),
        format_architecture_section(profile),
        format_compatibility_section(compatibility),
        format_precision_section(precision_findings),
        format_quantized_variants(variants, details.summary.repo_id),
        format_similar_models(similar),
        format_hardware_advice(hardware),
        format_download_recommendation(recommendation),
        build_raw_metadata(details, profile, compatibility, recommendation, hardware, precision_findings),
        card,
        build_file_inventory(details, recommendation),
        format_file_tree(details),
        local_snippet,
        inference_snippet,
        gr.Button(interactive=True),
        "",
    )


def _search_quantized_variants(client: HuggingFaceClient, repo_id: str) -> tuple[QuantizedVariant, ...]:
    """Chercher des variantes quantifiées sans jamais faire échouer le chargement de la fiche."""
    try:
        candidates = client.search_models(
            SearchFilters(query=extract_base_name(repo_id), sort="downloads", limit=50)
        )
        return find_quantized_variants(candidates, repo_id)
    except Exception:
        return ()


def _search_similar_models(
    client: HuggingFaceClient,
    details: ModelDetails,
    profile: TechnicalProfile,
) -> tuple[SimilarModel, ...]:
    """Chercher des modèles similaires sans jamais faire échouer le chargement de la fiche."""
    if not details.summary.pipeline_tag:
        return ()
    try:
        candidates = client.search_models(
            SearchFilters(pipeline_tag=details.summary.pipeline_tag, sort="downloads", limit=100)
        )
        return find_similar_models(details.summary, profile, details.card_data, candidates)
    except Exception:
        return ()


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
        f"| {_field_with_help(label)} | {_escape_markdown(_display_value(value))} |" for label, value in rows
    )
    tags = " ".join(f"`{_escape_inline_code(tag)}`" for tag in summary.tags[:16])

    return (
        "### 🪪 Identité\n\n"
        f"#### [{_escape_markdown(summary.repo_id)}]({repo_url})\n\n"
        "| Champ | Valeur |\n"
        "|---|---|\n"
        f"{table}\n\n"
        f"{_field_with_help('Tags principaux')} : {tags or '—'}"
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
        f"| {_field_with_help(label)} | {_escape_markdown(_display_value(value))} |" for label, value in rows
    )
    return "### 🧠 Architecture\n\n| Champ | Valeur |\n|---|---|\n" + table


_FINDING_STATUS_LABELS = {
    "detected": "✅ Détecté",
    "probable": "🟡 Probable",
    "conversion": "🔄 Conversion",
    "not_detected": "⚪ Non détecté",
}


def format_compatibility_section(findings: tuple[CompatibilityFinding, ...]) -> str:
    """Afficher les compatibilités avec une légende empêchant les faux positifs."""
    return _format_finding_table(
        findings,
        title="### 🧩 Compatibilité",
        column_label="Format / moteur",
        footer=(
            "_« Non détecté » ne signifie pas incompatible. Ces indices ne remplacent pas une validation "
            "de l’architecture avec la version du moteur que vous utilisez._"
        ),
    )


def format_precision_section(findings: tuple[CompatibilityFinding, ...]) -> str:
    """Afficher les précisions et quantifications trouvées dans le dépôt, sans juger leur qualité."""
    return _format_finding_table(
        findings,
        title="### 🎛️ Précisions et quantifications détectées",
        column_label="Format",
        footer=(
            "_Ce tableau signale des représentations trouvées dans les fichiers ou la configuration du dépôt, "
            "pas une recommandation d’usage. Voir le Model Advisor et l’onglet Hardware pour choisir laquelle "
            "télécharger selon votre machine._"
        ),
    )


def _format_finding_table(
    findings: tuple[CompatibilityFinding, ...],
    *,
    title: str,
    column_label: str,
    footer: str,
) -> str:
    """Factoriser le rendu tabulaire commun aux compatibilités et aux précisions détectées."""
    rows = "\n".join(
        f"| {_field_with_help(item.name)} | "
        f"{_field_with_help(_FINDING_STATUS_LABELS[item.state], help_key=item.state)} | "
        f"{_escape_markdown(item.reason)} |"
        for item in findings
    )
    return (
        f"{title}\n\n"
        f"| {_field_with_help(column_label)} | {_field_with_help('Statut')} | {_field_with_help('Indice')} |\n"
        "|---|---|---|\n"
        f"{rows}\n\n"
        f"{footer}"
    )


def format_quantized_variants(variants: tuple[QuantizedVariant, ...], source_repo_id: str) -> str:
    """Répondre à « ce modèle existe-t-il déjà en version quantifiée ? »."""
    header = "### 🔎 Versions quantifiées existantes\n\n"
    if not variants:
        return (
            f"{header}_Aucune variante quantifiée trouvée automatiquement par recherche du nom du modèle. "
            "Elle peut exister sous un nom différent, ou dans un dépôt que la recherche du Hub ne fait pas "
            "remonter : consultez la Model Card ou cherchez manuellement._"
        )

    rows = "\n".join(
        f"| [{_escape_markdown(item.summary.repo_id)}]"
        f"(https://huggingface.co/{quote(item.summary.repo_id, safe='/')}) | "
        f"{', '.join(item.formats)} | {format_count(item.summary.downloads)} | {format_count(item.summary.likes)} |"
        for item in variants[:10]
    )
    return (
        f"{header}D’autres dépôts semblent proposer une version compressée de "
        f"**{_escape_markdown(source_repo_id)}** :\n\n"
        "| Dépôt | Format(s) détecté(s) | Téléchargements | Likes |\n"
        "|---|---|---|---|\n"
        f"{rows}\n\n"
        "_Détection par recherche de texte sur le nom du modèle : vérifiez toujours qu’il s’agit bien du même "
        "modèle avant de l’utiliser, un nom proche ne suffit pas à le garantir._"
    )


def format_similar_models(results: tuple[SimilarModel, ...]) -> str:
    """Répondre à « quels autres modèles pourraient m’intéresser ? »."""
    header = "### 🧭 Modèles similaires\n\n"
    if not results:
        return (
            f"{header}_Aucun modèle similaire trouvé automatiquement pour cette tâche. "
            "Essayez une recherche manuelle depuis l’onglet Recherche._"
        )
    rows = "\n".join(
        f"- [{_escape_markdown(item.summary.repo_id)}]"
        f"(https://huggingface.co/{quote(item.summary.repo_id, safe='/')}) — "
        f"{_escape_markdown(', '.join(item.reasons))}"
        for item in results
    )
    return (
        f"{header}Rapprochés par famille, tâche, taille, langue déclarée, licence et disponibilité "
        f"quantifiée :\n\n"
        f"{rows}\n\n"
        "_Rapprochement heuristique à partir des métadonnées publiques du Hub, pas un classement de "
        "qualité : vérifiez toujours la Model Card avant de choisir._"
    )


def format_hardware_advice(advice: HardwareAdvice) -> str:
    """Traduire l'estimation matérielle en fiche lisible : le « Model Advisor »."""
    header = "### 🖥️ Model Advisor — Adéquation matérielle\n\n"
    if advice.parameters is None:
        return (
            f"{header}{advice.verdict_emoji} **{_escape_markdown(advice.verdict_headline)}**\n\n"
            f"{_escape_markdown(advice.verdict_detail)}"
        )

    rows: list[tuple[str, str]] = [("Paramètres", format_count(advice.parameters))]
    for estimate in advice.ram_estimates:
        if estimate.label == "FP32":
            continue
        rows.append((f"RAM estimée · {estimate.label}", _format_memory_range(estimate)))
    if advice.vram_recommended is not None:
        rows.append(("VRAM recommandée", _format_memory_range(advice.vram_recommended)))
    for criterion in advice.criteria:
        rows.append((criterion.name, _HARDWARE_STATUS_LABELS[criterion.status]))

    table = "\n".join(
        f"| {_field_with_help(label, help_key=_hardware_help_key(label))} | {value} |"
        for label, value in rows
    )
    verdict = (
        f"#### Verdict\n\n{advice.verdict_emoji} **{_escape_markdown(advice.verdict_headline)}**\n\n"
        f"{_escape_markdown(advice.verdict_detail)}"
    )
    return f"{header}| Critère | Analyse |\n|---|---|\n{table}\n\n{verdict}"


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
    hardware: HardwareAdvice | None = None,
    precision_formats: tuple[CompatibilityFinding, ...] | None = None,
) -> dict[str, Any]:
    """Rassembler les informations techniques sans les objets internes du SDK."""
    technical_profile = profile or extract_technical_profile(details)
    compatibility_findings = compatibility or inspect_compatibility(details)
    download_recommendation = recommendation or recommend_download(details)
    hardware_advice = hardware or advise_hardware(technical_profile, compatibility_findings)
    precision_findings = precision_formats or detect_precision_formats(
        details, technical_profile, compatibility_findings
    )
    return {
        "model": details.summary.to_dict(),
        "used_storage": details.used_storage,
        "tensor_dtypes": details.tensor_dtypes,
        "technical_profile": technical_profile.to_dict(),
        "compatibility": [item.to_dict() for item in compatibility_findings],
        "precision_formats": [item.to_dict() for item in precision_findings],
        "download_recommendation": download_recommendation.to_dict(),
        "hardware_advice": hardware_advice.to_dict(),
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


def _hardware_help_key(label: str) -> str:
    """Regrouper les libellés dynamiques de RAM sous une seule entrée d'aide."""
    return "RAM estimée" if label.startswith("RAM estimée") else label


def _format_memory_range(estimate: MemoryEstimate) -> str:
    """Afficher une estimation mémoire en valeur unique ou en intervalle lisible."""
    low = format_bytes(estimate.low_bytes)
    high = format_bytes(estimate.high_bytes)
    return f"≈ {low}" if low == high else f"≈ {low} – {high}"


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


def _escape_code_text(value: str) -> str:
    """Rendre un nom de fichier sûr à l'intérieur d'un bloc de code."""
    return "".join(character if character.isprintable() else "�" for character in value).replace("`", "ˋ")
