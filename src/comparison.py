"""Comparaison bornée de fiches modèles, sans score de qualité artificiel."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd
import plotly.graph_objects as go
from huggingface_hub.utils import HFValidationError, validate_repo_id

from src.api_client import ModelDetails, ModelSummary
from src.hardware_advisor import HardwareAdvice, advise_hardware
from src.model_analysis import extract_technical_profile, inspect_compatibility
from src.utils.formatters import format_bytes, format_count

COMPARISON_COLUMNS = [
    "Modèle", "Auteur", "Tâche", "Architecture", "Paramètres", "Taille des fichiers",
    "Licence", "Dtype", "Contexte (tokens)", "Likes", "Téléchargements", "Dernière MAJ",
]

# Nombre de paramètres au-delà duquel un modèle est classé dans le palier suivant, avec le
# nombre d'étoiles associé — repris directement des paliers RAM confortables du Model Advisor.
_LOCAL_STAR_TIERS: tuple[tuple[int, int], ...] = ((8, 5), (16, 4), (32, 3), (64, 2), (128, 1))
_GGUF_STATUS_FROM_COMPATIBILITY: dict[str, str] = {
    "detected": "ok",
    "probable": "warning",
    "conversion": "warning",
    "not_detected": "no",
}
_GGUF_STATUS_LABELS = {"ok": "✅ détecté", "warning": "⚠️ probable / à convertir", "no": "❌ non détecté"}


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


@dataclass(frozen=True, slots=True)
class ModelDecision:
    """Ligne du tableau décisionnel pour un modèle comparé."""

    repo_id: str
    parameters_label: str
    downloads_label: str
    likes_label: str
    context_label: str
    license_label: str
    fr_stars: int | None
    fr_note: str
    local_stars: int | None
    local_note: str
    gguf_status: str
    gguf_note: str

    def to_dict(self) -> dict[str, Any]:
        """Convertir la ligne en dictionnaire sérialisable."""
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ComparisonDecision:
    """Tableau décisionnel et recommandation d'usage local pour une sélection de modèles."""

    rows: tuple[ModelDecision, ...]
    recommended_repo_id: str | None
    recommendation_reason: str

    def to_dict(self) -> dict[str, Any]:
        """Convertir la décision complète en dictionnaire sérialisable."""
        return {
            "rows": [row.to_dict() for row in self.rows],
            "recommended_repo_id": self.recommended_repo_id,
            "recommendation_reason": self.recommendation_reason,
        }


def build_comparison_decision(models: Sequence[ModelDetails]) -> ComparisonDecision:
    """Construire le tableau décisionnel et recommander le meilleur compromis local.

    La recommandation combine l'adéquation RAM/VRAM déjà calculée par le Model Advisor,
    la disponibilité GGUF, et la popularité comme simple critère de départage. Ce n'est pas
    un jugement de qualité : un modèle absent de la recommandation peut rester un bon choix
    pour un autre usage que l'exécution locale.
    """
    rows: list[ModelDecision] = []
    scored: list[tuple[tuple[int, int, int], str]] = []

    for details in models:
        summary = details.summary
        profile = extract_technical_profile(details)
        compatibility = inspect_compatibility(details)
        advice = advise_hardware(profile, compatibility)
        gguf_finding = next((item for item in compatibility if item.name == "GGUF"), None)
        gguf_status = (
            _GGUF_STATUS_FROM_COMPATIBILITY[gguf_finding.state] if gguf_finding is not None else "no"
        )
        fr_stars, fr_note = _fr_rating(details)
        local_stars, local_note = _local_rating(advice)

        rows.append(
            ModelDecision(
                repo_id=summary.repo_id,
                parameters_label=format_count(profile.parameters),
                downloads_label=format_count(summary.downloads),
                likes_label=format_count(summary.likes),
                context_label=str(profile.context_length) if profile.context_length is not None else "—",
                license_label=model_license(summary, details.card_data),
                fr_stars=fr_stars,
                fr_note=fr_note,
                local_stars=local_stars,
                local_note=local_note,
                gguf_status=gguf_status,
                gguf_note=gguf_finding.reason if gguf_finding is not None else "Compatibilité GGUF non évaluée.",
            )
        )
        gguf_bonus = {"ok": 2, "warning": 1, "no": 0}[gguf_status]
        popularity = summary.downloads + summary.likes * 10  # Simple départage, jamais le critère principal.
        scored.append(((local_stars or 0, gguf_bonus, popularity), summary.repo_id))

    recommended_repo_id, reason = _pick_recommendation(rows, scored)
    return ComparisonDecision(rows=tuple(rows), recommended_repo_id=recommended_repo_id, recommendation_reason=reason)


def _fr_rating(details: ModelDetails) -> tuple[int | None, str]:
    """Évaluer un signal déclaratif de couverture du français, jamais une qualité de sortie."""
    card_languages = details.card_data.get("language")
    if isinstance(card_languages, str):
        card_languages = [card_languages]
    languages = {str(item).casefold() for item in card_languages} if isinstance(card_languages, list) else set()
    tags = {tag.casefold() for tag in details.summary.tags}

    if "fr" in languages or "french" in languages or "fr" in tags:
        return 5, "Français explicitement déclaré parmi les langues du modèle."
    if "multilingual" in tags or len(languages) >= 4:
        return 3, "Dépôt multilingue déclaré, sans confirmation explicite du français."
    return None, "Aucune langue déclarée : couverture du français inconnue."


def _local_rating(advice: HardwareAdvice) -> tuple[int | None, str]:
    """Traduire le palier de RAM confortable du Model Advisor en note d'usage local."""
    if advice.ram_comfortable_gib is None:
        return None, advice.verdict_detail
    for threshold, stars in _LOCAL_STAR_TIERS:
        if advice.ram_comfortable_gib <= threshold:
            return stars, f"{advice.verdict_emoji} {advice.verdict_headline}"
    return 1, f"{advice.verdict_emoji} {advice.verdict_headline}"


def _pick_recommendation(
    rows: list[ModelDecision],
    scored: list[tuple[tuple[int, int, int], str]],
) -> tuple[str | None, str]:
    """Choisir le meilleur compromis local parmi les modèles évaluables, ou expliquer l'impasse."""
    known = [(score, repo_id) for score, repo_id in scored if score[0] > 0]
    if not known:
        return None, "Paramètres non renseignés pour évaluer l'usage local d'aucun des modèles comparés."

    _best_score, best_repo_id = max(known, key=lambda item: item[0])
    best_row = next(row for row in rows if row.repo_id == best_repo_id)
    reason = (
        f"{best_row.local_note} · GGUF {_GGUF_STATUS_LABELS[best_row.gguf_status]} · "
        f"{best_row.downloads_label} téléchargements, {best_row.likes_label} likes."
    )
    return best_repo_id, reason
