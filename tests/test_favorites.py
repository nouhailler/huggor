"""Tests du stockage local des favoris."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.utils.favorites import FavoritesError, FavoritesStore


class FavoritesStoreTests(unittest.TestCase):
    """Vérifier la persistance, les doublons et les fichiers invalides."""

    def test_add_is_persistent_and_idempotent(self) -> None:
        """Le même modèle ne doit être ajouté qu'une seule fois."""
        with tempfile.TemporaryDirectory() as directory:
            store = FavoritesStore(Path(directory) / "favorites.json")

            self.assertTrue(store.add("acme/modele"))
            self.assertFalse(store.add("ACME/modele"))
            favorites = store.list_favorites()

            self.assertEqual(len(favorites), 1)
            self.assertEqual(favorites[0].repo_id, "acme/modele")
            self.assertTrue(favorites[0].added_at)

    def test_invalid_repo_id_is_rejected(self) -> None:
        """Un identifiant non conforme ne doit jamais être écrit."""
        with tempfile.TemporaryDirectory() as directory:
            store = FavoritesStore(Path(directory) / "favorites.json")

            with self.assertRaises(ValueError):
                store.add("a/b/c")

            self.assertFalse(store.path.exists())

    def test_corrupted_file_is_not_overwritten(self) -> None:
        """Une corruption doit être signalée sans perte silencieuse de données."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "favorites.json"
            path.write_text("{invalide", encoding="utf-8")
            store = FavoritesStore(path)

            with self.assertRaises(FavoritesError):
                store.add("acme/modele")

            self.assertEqual(path.read_text(encoding="utf-8"), "{invalide")


if __name__ == "__main__":
    unittest.main()
