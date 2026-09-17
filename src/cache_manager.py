"""Vue d'ensemble et administration des caches locaux, regroupés en domaines nommés.

Ce module n'introduit aucun nouveau stockage : il ouvre les mêmes répertoires de cache déjà
utilisés par ``HuggingFaceClient`` (``data/cache``) et par les historiques Analytics
(``data/analytics``), et se contente de les inspecter ou de les vider par domaine. Le domaine
« Benchmarks » est déclaré vide dès maintenant, avec une note explicite : l'onglet Test n'existe
pas encore, mais l'architecture est prête à l'accueillir sans rien casser ailleurs.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from src.utils.cache import JsonCache


@dataclass(frozen=True, slots=True)
class CacheDomainStats:
    """Statistiques d'un domaine de cache, prêtes à afficher telles quelles."""

    key: str
    label: str
    entry_count: int
    total_bytes: int
    newest_age_seconds: float | None
    oldest_age_seconds: float | None
    note: str = ""


@dataclass(frozen=True, slots=True)
class _CacheSource:
    """Un (cache, namespace) concret alimentant un domaine ; jamais exposé hors de ce module."""

    cache: JsonCache
    namespace: str


class CacheManager:
    """Regrouper les caches épars de l'application en domaines nommés et administrables."""

    def __init__(self, data_dir: str | Path) -> None:
        """Ouvrir les répertoires de cache déjà utilisés par le reste de l'application."""
        root = Path(data_dir)
        api_cache = JsonCache(root / "cache", default_ttl=900)
        analytics_cache = JsonCache(root / "analytics", default_ttl=365 * 86400)
        self._domains: dict[str, tuple[str, tuple[_CacheSource, ...], str]] = {
            "recherches": ("🔍 Recherches", (_CacheSource(api_cache, "search"),), ""),
            "details": ("📄 Détails de modèles", (_CacheSource(api_cache, "model"),), ""),
            "model_cards": ("📖 Model cards", (_CacheSource(api_cache, "card"),), ""),
            "statistiques": (
                "📈 Statistiques",
                (
                    _CacheSource(analytics_cache, "observations"),
                    _CacheSource(analytics_cache, "trend_observations"),
                ),
                "",
            ),
            "benchmarks": (
                "🧪 Benchmarks", (),
                "Aucune donnée : l'onglet Test (inférence) n'est pas encore implémenté.",
            ),
        }

    def domain_keys(self) -> tuple[str, ...]:
        """Lister les domaines dans un ordre d'affichage stable."""
        return tuple(self._domains)

    def stats(self, domain_key: str) -> CacheDomainStats:
        """Calculer les statistiques d'un domaine sans jamais purger d'entrée expirée en passant."""
        label, sources, note = self._domains[domain_key]
        entry_count = 0
        total_bytes = 0
        newest_created: float | None = None
        oldest_created: float | None = None
        for source in sources:
            for created_at, size in source.cache.iter_entries(source.namespace):
                entry_count += 1
                total_bytes += size
                newest_created = created_at if newest_created is None else max(newest_created, created_at)
                oldest_created = created_at if oldest_created is None else min(oldest_created, created_at)
        now = time.time()
        return CacheDomainStats(
            key=domain_key,
            label=label,
            entry_count=entry_count,
            total_bytes=total_bytes,
            newest_age_seconds=(now - newest_created) if newest_created is not None else None,
            oldest_age_seconds=(now - oldest_created) if oldest_created is not None else None,
            note=note,
        )

    def all_stats(self) -> tuple[CacheDomainStats, ...]:
        """Calculer les statistiques de chaque domaine, dans l'ordre déclaré."""
        return tuple(self.stats(key) for key in self._domains)

    def clear(self, domain_key: str) -> int:
        """Vider un domaine précis et retourner le nombre d'entrées supprimées."""
        _label, sources, _note = self._domains[domain_key]
        return sum(source.cache.clear(source.namespace) for source in sources)

    def clear_all(self) -> int:
        """Vider tous les domaines et retourner le nombre total d'entrées supprimées."""
        return sum(self.clear(key) for key in self._domains)

    def last_updated_age_seconds(self) -> float | None:
        """Âge de l'entrée la plus récente tous domaines confondus, pour un repère global."""
        ages = [stat.newest_age_seconds for stat in self.all_stats() if stat.newest_age_seconds is not None]
        return min(ages) if ages else None
