"""Recherche heuristique de modèles similaires à partir de métadonnées publiques du Hub.

Le rapprochement combine plusieurs signaux visibles (famille, tâche, taille, langue déclarée,
licence, disponibilité d'une version quantifiée) en un score simple. Ce n'est ni un classement
de qualité ni une recommandation d'usage : deux modèles proches sur ces critères peuvent rester
très différents en pratique. Vérifiez toujours la Model Card avant de choisir.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from src.api_client import ModelSummary
from src.comparison import model_license
from src.model_analysis import TechnicalProfile
from src.quantization_search import find_quantized_variants
from src.utils.formatters import format_count

_FAMILY_KEYWORDS = (
    "qwen", "llama", "mistral", "mixtral", "gemma", "phi", "falcon", "deepseek",
    "yi", "command-r", "starcoder", "baichuan", "internlm", "olmo", "dbrx",
    "granite", "smollm", "bert", "roberta", "t5", "whisper", "clip", "gpt2",
)
_QUANT_MARKERS = ("gguf", "gptq", "awq", "exl2", "mlx")
_LANGUAGE_TAGS = {
    "en", "fr", "de", "es", "it", "pt", "nl", "ru", "zh", "ja", "ko", "ar", "hi", "multilingual",
}
_PERMISSIVE_LICENSES = {"apache-2.0", "mit", "bsd-3-clause", "bsd-2-clause", "cc-by-4.0", "openrail"}


@dataclass(frozen=True, slots=True)
class SimilarModel:
    """Modèle candidat retenu comme similaire, avec les critères qui l'expliquent."""

    summary: ModelSummary
    score: float
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        """Convertir le résultat en dictionnaire sérialisable."""
        return {"summary": self.summary.to_dict(), "score": self.score, "reasons": list(self.reasons)}


def find_similar_models(
    source: ModelSummary,
    source_profile: TechnicalProfile,
    source_card_data: dict[str, Any],
    candidates: Sequence[ModelSummary],
    *,
    limit: int = 5,
    same_family_cap: int = 2,
) -> tuple[SimilarModel, ...]:
    """Composer un classement de similarité borné, sans laisser une seule famille tout occuper.

    Au plus `same_family_cap` résultats partagent la famille du modèle source : le reste met en
    avant des alternatives d'autres familles avec une tâche et une taille comparables, pour rester
    utile à la découverte plutôt que de renvoyer uniquement des variantes de taille du même modèle.
    Les quantifications du modèle source lui-même (déjà listées ailleurs dans la fiche) sont exclues
    pour ne pas doublonner avec la recherche de versions quantifiées existantes.
    """
    source_family = _detect_family(source.repo_id, source.tags, source_profile.family)
    source_languages = _detect_languages(source.tags)
    source_license = model_license(source, source_card_data).casefold()
    source_params = source_profile.parameters
    own_quantized_variants = {
        item.summary.repo_id.casefold() for item in find_quantized_variants(candidates, source.repo_id)
    }

    scored: list[tuple[float, str | None, ModelSummary, tuple[str, ...]]] = []
    for summary in candidates:
        if summary.repo_id.casefold() == source.repo_id.casefold():
            continue
        if summary.repo_id.casefold() in own_quantized_variants:
            continue
        score = 0.0
        reasons: list[str] = []
        candidate_family = _detect_family(summary.repo_id, summary.tags, "")

        if source_family and candidate_family == source_family:
            score += 3
            reasons.append(f"Même famille ({candidate_family})")
        if source.pipeline_tag and summary.pipeline_tag == source.pipeline_tag:
            score += 1
            reasons.append("Même tâche")
        if source_params and summary.parameters:
            ratio = max(source_params, summary.parameters) / max(min(source_params, summary.parameters), 1)
            if ratio <= 2.5:
                score += 2
                reasons.append(f"Taille proche ({format_count(summary.parameters)} paramètres)")
            elif ratio <= 6:
                score += 1
                reasons.append(f"Taille du même ordre de grandeur ({format_count(summary.parameters)} paramètres)")
        candidate_languages = _detect_languages(summary.tags)
        if source_languages and (source_languages & candidate_languages):
            score += 1
            reasons.append("Langue(s) déclarée(s) commune(s)")
        candidate_license = model_license(summary, {}).casefold()
        if candidate_license != "non renseignée" and candidate_license == source_license:
            score += 1
            reasons.append("Licence identique")
        elif candidate_license in _PERMISSIVE_LICENSES and source_license in _PERMISSIVE_LICENSES:
            score += 0.5
            reasons.append("Licences permissives compatibles")
        if _contains_any_marker(" ".join([summary.repo_id, *summary.tags]).casefold(), _QUANT_MARKERS):
            score += 1
            reasons.append("Version quantifiée déjà disponible")

        if score > 0:
            scored.append((score, candidate_family, summary, tuple(reasons)))

    def sort_key(item: tuple[float, str | None, ModelSummary, tuple[str, ...]]) -> tuple[float, int]:
        """Trier par score puis par téléchargements, pour départager les égalités."""
        score, _family, summary, _reasons = item
        return (score, summary.downloads)

    same_family_items = sorted(
        (item for item in scored if source_family and item[1] == source_family),
        key=sort_key, reverse=True,
    )
    other_family_items = sorted(
        (item for item in scored if not (source_family and item[1] == source_family)),
        key=sort_key, reverse=True,
    )

    selected = same_family_items[:same_family_cap] + other_family_items[: limit - min(len(same_family_items), same_family_cap)]
    if len(selected) < limit:
        chosen_ids = {item[2].repo_id for item in selected}
        leftover = sorted(
            (item for item in scored if item[2].repo_id not in chosen_ids),
            key=sort_key, reverse=True,
        )
        selected.extend(leftover[: limit - len(selected)])

    selected.sort(key=sort_key, reverse=True)
    return tuple(SimilarModel(summary=s, score=sc, reasons=r) for sc, _f, s, r in selected[:limit])


def _detect_family(repo_id: str, tags: Sequence[str], extra_text: str) -> str | None:
    """Repérer une famille de modèle connue comme mot significatif, pas comme sous-chaîne arbitraire."""
    haystack = " ".join([repo_id, *tags, extra_text]).casefold()
    for keyword in _FAMILY_KEYWORDS:
        if re.search(rf"\b{re.escape(keyword)}\b", haystack):
            return keyword
    return None


def _detect_languages(tags: Sequence[str]) -> set[str]:
    """Ne retenir que les tags correspondant à un code de langue connu."""
    return {tag.casefold() for tag in tags if tag.casefold() in _LANGUAGE_TAGS}


def _contains_any_marker(haystack: str, markers: Sequence[str]) -> bool:
    """Chercher un marqueur comme mot significatif parmi plusieurs candidats."""
    return any(re.search(rf"(?:^|[-_/. ]){re.escape(marker)}(?:$|[-_/. ])", haystack) for marker in markers)
