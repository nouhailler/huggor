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

    def test_update_changes_only_the_provided_fields(self) -> None:
        """Un champ omis lors d'une mise à jour doit conserver sa valeur précédente."""
        with tempfile.TemporaryDirectory() as directory:
            store = FavoritesStore(Path(directory) / "favorites.json")
            store.add("acme/modele", note="Première note")

            store.update("acme/modele", collection="Coding", tags=["python", "chat"], score=4)
            updated = store.update("acme/modele", status="recommandé")

            self.assertEqual(updated.note, "Première note")
            self.assertEqual(updated.collection, "Coding")
            self.assertEqual(updated.tags, ("python", "chat"))
            self.assertEqual(updated.score, 4)
            self.assertEqual(updated.status, "recommandé")

    def test_update_unknown_repo_id_is_rejected(self) -> None:
        """On ne peut pas modifier un favori qui n'existe pas."""
        with tempfile.TemporaryDirectory() as directory:
            store = FavoritesStore(Path(directory) / "favorites.json")

            with self.assertRaises(ValueError):
                store.update("acme/absent", note="test")

    def test_score_out_of_range_is_rejected(self) -> None:
        """La note personnelle doit rester entre 1 et 5."""
        with tempfile.TemporaryDirectory() as directory:
            store = FavoritesStore(Path(directory) / "favorites.json")
            store.add("acme/modele")

            with self.assertRaises(ValueError):
                store.update("acme/modele", score=6)

    def test_clear_score_removes_the_previous_rating(self) -> None:
        """clear_score doit permettre de revenir à « non noté », contrairement à score=None."""
        with tempfile.TemporaryDirectory() as directory:
            store = FavoritesStore(Path(directory) / "favorites.json")
            store.add("acme/modele")
            store.update("acme/modele", score=3)

            cleared = store.update("acme/modele", clear_score=True)

            self.assertIsNone(cleared.score)

    def test_remove_reports_whether_the_favorite_existed(self) -> None:
        """Retirer un favori absent ne doit pas être confondu avec un retrait réel."""
        with tempfile.TemporaryDirectory() as directory:
            store = FavoritesStore(Path(directory) / "favorites.json")
            store.add("acme/modele")

            self.assertTrue(store.remove("acme/modele"))
            self.assertFalse(store.remove("acme/modele"))
            self.assertEqual(store.list_favorites(), [])

    def test_list_collections_is_sorted_and_deduplicated(self) -> None:
        """Les collections affichées ne doivent contenir ni doublon ni entrée vide."""
        with tempfile.TemporaryDirectory() as directory:
            store = FavoritesStore(Path(directory) / "favorites.json")
            store.add("acme/a")
            store.add("acme/b")
            store.add("acme/c")
            store.update("acme/a", collection="Coding")
            store.update("acme/b", collection="Coding")
            store.update("acme/c", collection="Vision")

            self.assertEqual(store.list_collections(), ["Coding", "Vision"])


if __name__ == "__main__":
    unittest.main()
