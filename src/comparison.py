"""Comparaison bornée de fiches modèles, sans score de qualité artificiel."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd
import plotly.graph_objects as go
from huggingface_hub.utils import HFValidationError, validate_repo_id

from src.api_client import ModelDetails, ModelSummary
from src.model_analysis import extract_technical_profile
from src.utils.formatters import format_bytes, format_count

COMPARISON_COLUMNS = [
    "Modèle", "Auteur", "Tâche", "Architecture", "Paramètres", "Taille des fichiers",
    "Licence", "Dtype", "Contexte (tokens)", "Likes", "Téléchargements", "Dernière MAJ",
]


def validate_comparison_ids(values: Sequence[str | None]) -> tuple[str, ...]:
    """Valider deux à quatre identifiants distincts avant toute requête réseau."""
    ids = tuple(value.strip() for value in values if value and value.strip())
    if not 2 <= len(ids) <= 4:
        raise ValueError("Sélectionnez de 2 à 4 modèles.")
    if len(set(ids)) != len(ids):
        raise ValueError("Chaque modèle doit être différent.")
    for repo_id in ids:
        try:
            validate_repo_id(repo_id)
        except HFValidationError as error:
            raise ValueError(f"Identifiant invalide : {repo_id}.") from error
    return ids


def model_license(summary: ModelSummary, card_data: dict | None = None) -> str:
    """Lire la licence de la Model Card puis des tags, sans la deviner."""
    license_value = (card_data or {}).get("license")
    if isinstance(license_value, str) and license_value:
        return license_value
    if isinstance(license_value, list):
        return ", ".join(str(value) for value in license_value)
    return next((tag.split(":", 1)[1] for tag in summary.tags if tag.startswith("license:")), "Non renseignée")


def file_storage(details: ModelDetails) -> int | None:
    """Sommer les fichiers courants uniquement si toutes les tailles sont connues."""
    if not details.files or any(file.size is None for file in details.files):
        return None
    return sum(file.size or 0 for file in details.files)


def comparison_table(models: Sequence[ModelDetails]) -> pd.DataFrame:
    """Construire un tableau lisible incluant les métadonnées techniques."""
    rows = []
    for details in models:
        summary = details.summary
        profile = extract_technical_profile(details)
        rows.append([
            summary.repo_id, summary.author or "—", summary.pipeline_tag or "—",
            profile.family, format_count(profile.parameters), format_bytes(file_storage(details)),
            model_license(summary, details.card_data), profile.dtype,
            str(profile.context_length) if profile.context_length is not None else "—",
            summary.likes, summary.downloads, summary.last_modified or "—",
        ])
    return pd.DataFrame(rows, columns=COMPARISON_COLUMNS)


def comparison_radar(models: Sequence[ModelDetails]) -> go.Figure | None:
    """Normaliser les quantités communes à 0–100 ; ne pas combler un champ absent."""
    profiles = [extract_technical_profile(details) for details in models]
    candidates = {
        "Paramètres": [profile.parameters for profile in profiles],
        "Taille des fichiers": [file_storage(details) for details in models],
        "Contexte": [profile.context_length for profile in profiles],
        "Likes": [details.summary.likes for details in models],
        "Téléchargements": [details.summary.downloads for details in models],
    }
    axes = {
        name: values for name, values in candidates.items()
        if all(value is not None for value in values) and max(values) > 0
    }
    if len(axes) < 3:
        return None
    labels = list(axes)
    figure = go.Figure()
    for index, details in enumerate(models):
        values = [100 * axes[name][index] / max(axes[name]) for name in labels]
        raw = [axes[name][index] for name in labels]
        figure.add_trace(go.Scatterpolar(
            r=values + values[:1], theta=labels + labels[:1],
            customdata=raw + raw[:1], name=details.summary.repo_id, fill="toself",
            hovertemplate="%{theta} : %{customdata:,}<br>Relatif : %{r:.1f}%<extra>%{fullData.name}</extra>",
        ))
    figure.update_layout(
        template="plotly_white", title="Quantités relatives — pas un classement de qualité",
        polar={"radialaxis": {"visible": True, "range": [0, 100]}},
        legend={"orientation": "h", "y": -0.15}, margin={"t": 70, "b": 100}, height=520,
    )
    return figure
