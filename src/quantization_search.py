"""Recherche heuristique de variantes quantifiées d'un modèle sur le Hub.

La détection repose sur une recherche texte du nom du modèle puis un filtrage par
marqueurs de format dans l'identifiant et les tags des résultats. C'est un indice, pas une
garantie : un dépôt peut porter un nom proche sans être une quantification du même modèle,
ou au contraire ne pas être retrouvé s'il porte un nom très différent.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from typing import Any

from src.api_client import ModelSummary

_FORMAT_MARKERS: tuple[tuple[str, str], ...] = (
    ("gguf", "GGUF"),
    ("gptq", "GPTQ"),
    ("awq", "AWQ"),
    ("exl2", "EXL2"),
    ("exllamav2", "EXL2"),
    ("mlx", "MLX"),
)


@dataclass(frozen=True, slots=True)
class QuantizedVariant:
    """Dépôt candidat identifié comme une variante quantifiée probable."""

    summary: ModelSummary
    formats: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        """Convertir la variante en dictionnaire sérialisable."""
        return {"summary": self.summary.to_dict(), "formats": list(self.formats)}


def extract_base_name(repo_id: str) -> str:
    """Isoler le nom du modèle sans l'auteur, pour chercher ses variantes quantifiées."""
    return repo_id.rsplit("/", maxsplit=1)[-1]


def find_quantized_variants(
    candidates: Sequence[ModelSummary],
    source_repo_id: str,
) -> tuple[QuantizedVariant, ...]:
    """Filtrer des résultats de recherche pour ne garder que les variantes quantifiées probables.

    Un candidat est retenu s'il contient le nom du modèle source et au moins un marqueur de
    format de quantification connu, dans son identifiant ou ses tags.
    """
    base_name = extract_base_name(source_repo_id).casefold()
    if not base_name:
        return ()

    variants: list[QuantizedVariant] = []
    for summary in candidates:
        if summary.repo_id.casefold() == source_repo_id.casefold():
            continue
        if base_name not in summary.repo_id.casefold():
            continue
        haystack = " ".join([summary.repo_id, *summary.tags]).casefold()
        formats = tuple(dict.fromkeys(label for marker, label in _FORMAT_MARKERS if _contains_marker(haystack, marker)))
        if formats:
            variants.append(QuantizedVariant(summary=summary, formats=formats))

    variants.sort(key=lambda item: item.summary.downloads, reverse=True)
    return tuple(variants)


def _contains_marker(haystack: str, marker: str) -> bool:
    """Chercher un marqueur comme mot significatif, pas comme sous-chaîne arbitraire."""
    pattern = re.compile(rf"(?:^|[-_/. ]){re.escape(marker)}(?:$|[-_/. ])")
    return bool(pattern.search(haystack))
