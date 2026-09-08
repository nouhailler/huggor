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


if __name__ == "__main__":
    unittest.main()

