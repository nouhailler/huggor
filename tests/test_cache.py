"""Tests du cache JSON local."""

from __future__ import annotations

import json
import tempfile
import time
import unittest
from pathlib import Path

from src.utils.cache import JsonCache


class JsonCacheTests(unittest.TestCase):
    """Vérifier les lectures, expirations et corruptions du cache."""

    def test_round_trip_and_clear(self) -> None:
        """Une entrée écrite doit être relue puis supprimée."""
        with tempfile.TemporaryDirectory() as directory:
            cache = JsonCache(directory, default_ttl=60)
            cache.set("search", "cle", {"résultat": 1})

            self.assertEqual(cache.get("search", "cle"), {"résultat": 1})
            self.assertEqual(cache.clear("search"), 1)
            self.assertIsNone(cache.get("search", "cle"))

    def test_expired_entry_is_ignored(self) -> None:
        """Une entrée arrivée à expiration ne doit jamais être renvoyée."""
        with tempfile.TemporaryDirectory() as directory:
            cache = JsonCache(directory, default_ttl=60)
            path = cache._path_for("search", "cle")
            path.write_text(
                json.dumps({"version": 1, "expires_at": time.time() - 1, "value": "ancien"}),
                encoding="utf-8",
            )

            self.assertIsNone(cache.get("search", "cle"))
            self.assertFalse(path.exists())

    def test_corrupted_entry_is_ignored(self) -> None:
        """Un JSON corrompu ne doit pas faire échouer l'application."""
        with tempfile.TemporaryDirectory() as directory:
            cache = JsonCache(directory, default_ttl=60)
            path = cache._path_for("search", "cle")
            Path(path).write_text("{invalide", encoding="utf-8")

            self.assertIsNone(cache.get("search", "cle"))

    def test_age_seconds_reflects_time_since_creation(self) -> None:
        """L'âge affiché doit refléter le moment réel d'écriture, pas la lecture."""
        with tempfile.TemporaryDirectory() as directory:
            cache = JsonCache(directory, default_ttl=60)
            cache.set("search", "cle", {"résultat": 1})

            age = cache.age_seconds("search", "cle")

            self.assertIsNotNone(age)
            self.assertLess(age, 1.0)

    def test_age_seconds_is_none_for_missing_or_expired_entries(self) -> None:
        """Une entrée absente ou expirée ne doit jamais afficher un âge inventé."""
        with tempfile.TemporaryDirectory() as directory:
            cache = JsonCache(directory, default_ttl=60)

            self.assertIsNone(cache.age_seconds("search", "absente"))

            path = cache._path_for("search", "cle")
            path.write_text(
                json.dumps({"version": 1, "created_at": time.time() - 100, "expires_at": time.time() - 1}),
                encoding="utf-8",
            )
            self.assertIsNone(cache.age_seconds("search", "cle"))

    def test_iter_entries_lists_only_valid_entries_of_the_namespace(self) -> None:
        """Le relevé pour l'administration ne doit pas confondre les namespaces ni ressusciter l'expiré."""
        with tempfile.TemporaryDirectory() as directory:
            cache = JsonCache(directory, default_ttl=60)
            cache.set("search", "a", {"x": 1})
            cache.set("search", "b", {"x": 2})
            cache.set("model", "c", {"x": 3})
            expired_path = cache._path_for("search", "expired")
            expired_path.write_text(
                json.dumps({"version": 1, "created_at": time.time() - 100, "expires_at": time.time() - 1, "value": 0}),
                encoding="utf-8",
            )

            search_entries = cache.iter_entries("search")
            all_entries = cache.iter_entries()

            self.assertEqual(len(search_entries), 2)
            self.assertEqual(len(all_entries), 3)
            for _created_at, size in search_entries:
                self.assertGreater(size, 0)

    def test_iter_entries_never_deletes_expired_files(self) -> None:
        """L'inspection pour les statistiques ne doit jamais avoir d'effet de bord destructeur."""
        with tempfile.TemporaryDirectory() as directory:
            cache = JsonCache(directory, default_ttl=60)
            path = cache._path_for("search", "expired")
            path.write_text(
                json.dumps({"version": 1, "created_at": time.time() - 100, "expires_at": time.time() - 1, "value": 0}),
                encoding="utf-8",
            )

            cache.iter_entries("search")

            self.assertTrue(path.exists())


if __name__ == "__main__":
    unittest.main()

