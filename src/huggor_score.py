"""Huggor Score : synthèse composite sur 100, jamais affichée sans le détail qui l'explique.

Comme le Model Advisor, ce score ne remplace aucun jugement humain. Chaque composante est
calculée à partir de signaux déjà présentés ailleurs dans la fiche (popularité, compatibilité,
licence…) et reste visible avec son propre nombre de points : additionner neuf signaux publics
détectés automatiquement ne mesure ni la qualité des réponses du modèle ni son adéquation à un
projet donné.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from src.api_client import ModelDetails
from src.comparison import model_license
from src.hardware_advisor import HardwareAdvice
from src.model_analysis import CompatibilityFinding, TechnicalProfile
from src.utils.formatters import format_count

_PERMISSIVE_LICENSES = {"apache-2.0", "mit", "bsd-3-clause", "bsd-2-clause", "cc-by-4.0", "openrail"}
_QUANT_FORMAT_NAMES = ("GGUF", "GPTQ", "AWQ", "EXL2", "MLX")
MAX_TOTAL = 100


@dataclass(frozen=True, slots=True)
class ScoreComponent:
    """Une composante du Huggor Score, avec assez de détail pour ne pas être une boîte noire."""

    name: str
    points: int
    max_points: int
    reason: str

    def to_dict(self) -> dict[str, Any]:
        """Convertir la composante en dictionnaire sérialisable."""
        return {"name": self.name, "points": self.points, "max_points": self.max_points, "reason": self.reason}


@dataclass(frozen=True, slots=True)
class HuggorScore:
    """Score composite sur 100, toujours accompagné du détail de ses neuf composantes."""

    total: int
    max_total: int
    components: tuple[ScoreComponent, ...]

    def to_dict(self) -> dict[str, Any]:
        """Convertir le score complet en dictionnaire sérialisable."""
        return {
            "total": self.total,
            "max_total": self.max_total,
            "components": [item.to_dict() for item in self.components],
        }


def compute_huggor_score(
    details: ModelDetails,
    profile: TechnicalProfile,
    compatibility: tuple[CompatibilityFinding, ...],
    hardware: HardwareAdvice,
    model_card_markdown: str,
    *,
    has_known_quantized_variants: bool = False,
) -> HuggorScore:
    """Calculer le Huggor Score et le détail de chacune de ses neuf composantes.

    ``has_known_quantized_variants`` reflète la recherche de versions quantifiées déjà affichée
    plus haut sur la fiche : elle évite de pénaliser un modèle dont une variante GGUF/AWQ/GPTQ
    existe ailleurs sur le Hub même si ce dépôt précis ne la fournit pas.
    """
    findings = {item.name: item for item in compatibility}
    components = (
        _popularity_component(details),
        _freshness_component(details),
        _documentation_component(model_card_markdown),
        _license_component(details),
        _safetensors_component(findings),
        _quantization_component(findings, has_known_quantized_variants),
        _local_compatibility_component(hardware),
        _size_component(profile),
        _maturity_component(details),
    )
    return HuggorScore(total=sum(item.points for item in components), max_total=MAX_TOTAL, components=components)


def _popularity_component(details: ModelDetails) -> ScoreComponent:
    """Récompenser un usage réel mesuré, sans confondre popularité et qualité."""
    downloads = details.summary.downloads
    likes = details.summary.likes
    tiers = ((1_000_000, 15), (100_000, 12), (10_000, 9), (1_000, 6), (100, 3))
    points = next((score for threshold, score in tiers if downloads >= threshold), 0)
    return ScoreComponent(
        "Popularité", points, 15, f"{format_count(downloads)} téléchargements, {format_count(likes)} likes."
    )


def _freshness_component(details: ModelDetails) -> ScoreComponent:
    """Valoriser une mise à jour récente, sans supposer qu'un dépôt stable est abandonné."""
    age_days = _days_since(details.summary.last_modified)
    if age_days is None:
        return ScoreComponent("Fraîcheur", 0, 10, "Date de dernière modification non renseignée ou illisible.")
    tiers = ((30, 10), (90, 8), (180, 6), (365, 4), (730, 2))
    points = next((score for threshold, score in tiers if age_days <= threshold), 0)
    return ScoreComponent("Fraîcheur", points, 10, f"Dernière modification il y a {age_days} jour(s).")


def _documentation_component(model_card_markdown: str) -> ScoreComponent:
    """Mesurer une quantité (longueur, présence d'exemples), jamais une qualité rédactionnelle."""
    text = (model_card_markdown or "").strip()
    length = len(text)
    if length < 200:
        points = 0
    elif length < 500:
        points = 3
    elif length < 1_500:
        points = 6
    else:
        points = 8
    has_code_example = "```" in text
    if has_code_example and points > 0:
        points = min(points + 2, 10)
    detail = f"Model Card de {length} caractères" + (", avec exemple de code." if has_code_example else ".")
    return ScoreComponent("Documentation", points, 10, detail)


def _license_component(details: ModelDetails) -> ScoreComponent:
    """Distinguer une licence permissive confirmée d'une licence seulement déclarée."""
    license_name = model_license(details.summary, details.card_data)
    normalized = license_name.casefold()
    if normalized in _PERMISSIVE_LICENSES:
        return ScoreComponent("Licence", 10, 10, f"Licence permissive détectée : {license_name}.")
    if normalized and normalized != "non renseignée":
        return ScoreComponent("Licence", 6, 10, f"Licence déclarée : {license_name} (conditions à vérifier).")
    return ScoreComponent("Licence", 0, 10, "Aucune licence renseignée.")


def _safetensors_component(findings: dict[str, CompatibilityFinding]) -> ScoreComponent:
    """Réutiliser le constat de compatibilité déjà établi, sans le recalculer."""
    finding = findings.get("Safetensors")
    if finding is None:
        return ScoreComponent("Safetensors", 0, 10, "Compatibilité Safetensors non évaluée.")
    points = {"detected": 10, "probable": 6}.get(finding.state, 0)
    return ScoreComponent("Safetensors", points, 10, finding.reason)


def _quantization_component(
    findings: dict[str, CompatibilityFinding],
    has_known_quantized_variants: bool,
) -> ScoreComponent:
    """Valoriser une quantification disponible ici ou ailleurs sur le Hub, jamais devinée."""
    own_formats = [name for name in _QUANT_FORMAT_NAMES if findings.get(name) and findings[name].state == "detected"]
    if own_formats:
        return ScoreComponent(
            "Quantification disponible", 10, 10, f"Format(s) détecté(s) dans ce dépôt : {', '.join(own_formats)}."
        )
    if has_known_quantized_variants:
        return ScoreComponent(
            "Quantification disponible", 7, 10,
            "Aucune quantification dans ce dépôt, mais des variantes ont été trouvées ailleurs sur le Hub.",
        )
    return ScoreComponent("Quantification disponible", 0, 10, "Aucune quantification détectée ni trouvée ailleurs.")


def _local_compatibility_component(hardware: HardwareAdvice) -> ScoreComponent:
    """Reprendre le palier RAM confortable déjà calculé par le Model Advisor."""
    if hardware.ram_comfortable_gib is None:
        return ScoreComponent("Compatibilité locale", 0, 15, "Paramètres inconnus : adéquation locale non évaluable.")
    tiers = ((8, 15), (16, 12), (32, 8), (64, 4))
    points = next((score for threshold, score in tiers if hardware.ram_comfortable_gib <= threshold), 0)
    return ScoreComponent("Compatibilité locale", points, 15, f"{hardware.verdict_emoji} {hardware.verdict_headline}")


def _size_component(profile: TechnicalProfile) -> ScoreComponent:
    """Récompenser la seule transparence sur la taille, pas une taille jugée « bonne »."""
    if profile.parameters is None:
        return ScoreComponent("Taille", 0, 5, "Nombre de paramètres non renseigné par ce dépôt.")
    return ScoreComponent("Taille", 5, 5, f"{format_count(profile.parameters)} paramètres déclarés.")


def _maturity_component(details: ModelDetails) -> ScoreComponent:
    """Combiner ancienneté et adoption : un dépôt tout juste créé reste à valider dans la durée."""
    age_days = _days_since(details.summary.created_at)
    if age_days is None:
        return ScoreComponent("Maturité", 0, 15, "Date de création non renseignée ou illisible.")
    if age_days < 30:
        return ScoreComponent(
            "Maturité", 0, 15, "Dépôt créé il y a moins d'un mois : trop récent pour juger de sa maturité."
        )
    engagement = details.summary.downloads + details.summary.likes * 10
    tiers = ((100_000, 15), (10_000, 12), (1_000, 9), (100, 6))
    points = next((score for threshold, score in tiers if engagement >= threshold), 3)
    return ScoreComponent(
        "Maturité", points, 15,
        f"Dépôt créé il y a {age_days} jour(s), {format_count(details.summary.downloads)} téléchargements cumulés.",
    )


def _days_since(iso_date: str | None) -> int | None:
    """Convertir une date ISO 8601 en nombre de jours écoulés, sans jamais lever d'exception."""
    if not iso_date:
        return None
    try:
        parsed = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return max((datetime.now(timezone.utc) - parsed).days, 0)
