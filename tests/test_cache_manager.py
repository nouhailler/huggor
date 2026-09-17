"""Tests de l'administration du cache par domaines."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.cache_manager import CacheManager
from src.utils.cache import JsonCache


class CacheManagerTests(unittest.TestCase):
    """Vérifier les statistiques, la purge ciblée et le repère global de fraîcheur."""

    def setUp(self) -> None:
        """Préparer un répertoire de données isolé pour chaque test."""
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.manager = CacheManager(self.directory.name)

    def test_empty_domains_report_zero_without_crashing(self) -> None:
        """Un domaine jamais alimenté doit afficher zéro, pas planter ou inventer une valeur."""
        for key in self.manager.domain_keys():
            with self.subTest(domain=key):
                stats = self.manager.stats(key)
                self.assertEqual(stats.entry_count, 0)
                self.assertEqual(stats.total_bytes, 0)
                self.assertIsNone(stats.newest_age_seconds)

    def test_benchmarks_domain_is_explicitly_documented_as_not_yet_used(self) -> None:
        """Le domaine Benchmarks doit expliquer pourquoi il est vide, pas le cacher."""
        stats = self.manager.stats("benchmarks")

        self.assertEqual(stats.entry_count, 0)
        self.assertIn("pas encore implémenté", stats.note)

    def test_populating_the_underlying_cache_is_reflected_in_stats(self) -> None:
        """Écrire dans le cache API partagé doit se refléter dans le domaine correspondant."""
        api_cache = JsonCache(Path(self.directory.name) / "cache", default_ttl=900)
        api_cache.set("search", "une-recherche", {"resultats": [1, 2, 3]})
        api_cache.set("model", "un-modele", {"repo_id": "acme/modele"})

        manager = CacheManager(self.directory.name)  # Rouvre les mêmes fichiers sur disque.

        self.assertEqual(manager.stats("recherches").entry_count, 1)
        self.assertEqual(manager.stats("details").entry_count, 1)
        self.assertEqual(manager.stats("model_cards").entry_count, 0)

    def test_clear_only_empties_the_targeted_domain(self) -> None:
        """Vider un domaine ne doit jamais toucher aux autres."""
        api_cache = JsonCache(Path(self.directory.name) / "cache", default_ttl=900)
        api_cache.set("search", "une-recherche", {"resultats": []})
        api_cache.set("model", "un-modele", {"repo_id": "acme/modele"})
        manager = CacheManager(self.directory.name)

        removed = manager.clear("recherches")

        self.assertEqual(removed, 1)
        self.assertEqual(manager.stats("recherches").entry_count, 0)
        self.assertEqual(manager.stats("details").entry_count, 1)

    def test_clear_all_empties_every_domain(self) -> None:
        """Vider tout doit couvrir chaque domaine, y compris ceux répartis sur plusieurs namespaces."""
        api_cache = JsonCache(Path(self.directory.name) / "cache", default_ttl=900)
        analytics_cache = JsonCache(Path(self.directory.name) / "analytics", default_ttl=365 * 86400)
        api_cache.set("search", "a", {})
        api_cache.set("model", "b", {})
        api_cache.set("card", "c", "# Carte")
        analytics_cache.set("observations", "d", [])
        analytics_cache.set("trend_observations", "e", {})
        manager = CacheManager(self.directory.name)

        removed = manager.clear_all()

        self.assertEqual(removed, 5)
        for key in manager.domain_keys():
            self.assertEqual(manager.stats(key).entry_count, 0)

    def test_last_updated_age_uses_the_most_recent_entry_across_domains(self) -> None:
        """Le repère global doit refléter l'entrée la plus fraîche, pas la plus ancienne."""
        api_cache = JsonCache(Path(self.directory.name) / "cache", default_ttl=900)
        api_cache.set("search", "vieille", {})
        manager = CacheManager(self.directory.name)

        self.assertIsNotNone(manager.last_updated_age_seconds())
        self.assertLess(manager.last_updated_age_seconds(), 5.0)

    def test_last_updated_age_is_none_when_nothing_cached_yet(self) -> None:
        """Sans aucune entrée nulle part, il ne doit pas y avoir de « dernière mise à jour »."""
        self.assertIsNone(self.manager.last_updated_age_seconds())


if __name__ == "__main__":
    unittest.main()
