"""Tests de la logique de présentation et d'édition de l'onglet Favoris."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.ui.favorites_tab import (
    _filter_favorites,
    _refresh_after_mutation,
    _remove_favorite_for_ui,
    _save_favorite_edits,
    format_favorite_card,
)
from src.utils.favorites import FavoritesStore


class FavoriteCardFormattingTests(unittest.TestCase):
    """Vérifier que la carte reflète fidèlement les champs personnels du favori."""

    def test_card_shows_stars_tags_note_and_dates(self) -> None:
        """L'exemple fourni (5/5, tags, citation, date) doit apparaître tel quel."""
        card = format_favorite_card(
            {
                "repo_id": "Qwen/Qwen2.5-7B-Instruct",
                "collection": "LLM locaux",
                "score": 5,
                "tags": ["coding", "français", "local"],
                "note": "Très bon compromis 16 Go RAM",
                "status": "recommandé",
                "last_tested_at": "11/09/2026",
                "added_at": "2026-09-01T00:00:00+00:00",
            }
        )

        self.assertIn("Qwen2.5-7B-Instruct", card)
        self.assertIn("LLM locaux", card)
        self.assertIn("5/5", card)
        self.assertIn("coding", card)
        self.assertIn("Très bon compromis 16 Go RAM", card)
        self.assertIn("recommandé", card)
        self.assertIn("11/09/2026", card)

    def test_card_handles_an_unrated_uncategorised_favorite(self) -> None:
        """Un favori tout juste ajouté ne doit afficher aucune fausse information."""
        card = format_favorite_card({"repo_id": "acme/model", "added_at": "2026-01-01T00:00:00+00:00"})

        self.assertIn("Non classé", card)
        self.assertIn("Non noté", card)
        self.assertIn("Aucune note personnelle", card)
        self.assertIn("non renseigné", card)
        self.assertIn("jamais", card)


class FavoritesTabLogicTests(unittest.TestCase):
    """Vérifier le filtrage, l'édition et le retrait depuis l'onglet Favoris."""

    def test_filter_favorites_by_collection(self) -> None:
        """Seuls les favoris de la collection choisie doivent être renvoyés."""
        with tempfile.TemporaryDirectory() as directory:
            store = FavoritesStore(Path(directory) / "favorites.json")
            store.add("acme/a")
            store.add("acme/b")
            store.update("acme/a", collection="Coding")

            coding_only = _filter_favorites(store, "Coding")
            everything = _filter_favorites(store, "")

            self.assertEqual([item["repo_id"] for item in coding_only], ["acme/a"])
            self.assertEqual(len(everything), 2)

    def test_save_favorite_edits_persists_all_fields(self) -> None:
        """Enregistrer le formulaire d'édition doit répercuter chaque champ dans le favori."""
        with tempfile.TemporaryDirectory() as directory:
            store = FavoritesStore(Path(directory) / "favorites.json")
            store.add("acme/model")

            message, items, _dropdown = _save_favorite_edits(
                store, "acme/model", "Coding", "recommandé", 4, "python, chat", "17/09/2026",
                "Très bon compromis 16 Go RAM", "",
            )

            self.assertIn("mis à jour", message)
            saved = next(item for item in items if item["repo_id"] == "acme/model")
            self.assertEqual(saved["collection"], "Coding")
            self.assertEqual(saved["status"], "recommandé")
            self.assertEqual(saved["score"], 4)
            self.assertEqual(saved["tags"], ("python", "chat"))
            self.assertEqual(saved["last_tested_at"], "17/09/2026")
            self.assertEqual(saved["note"], "Très bon compromis 16 Go RAM")

    def test_save_favorite_edits_reports_validation_errors(self) -> None:
        """Une erreur de validation (ex. tag trop long) doit rester lisible, pas une trace Python."""
        with tempfile.TemporaryDirectory() as directory:
            store = FavoritesStore(Path(directory) / "favorites.json")
            store.add("acme/model")

            message, _items, _dropdown = _save_favorite_edits(
                store, "acme/model", "", "", 0, "x" * 41, "", "", "",
            )

            self.assertIn("⚠️", message)

    def test_remove_favorite_clears_it_from_the_list(self) -> None:
        """Retirer un favori doit le faire disparaître immédiatement de la liste rechargée."""
        with tempfile.TemporaryDirectory() as directory:
            store = FavoritesStore(Path(directory) / "favorites.json")
            store.add("acme/model")

            message, items, _dropdown = _remove_favorite_for_ui(store, "acme/model", "")

            self.assertIn("retiré", message)
            self.assertEqual(items, [])

    def test_refresh_resets_filter_when_collection_no_longer_exists(self) -> None:
        """Si la collection filtrée disparaît, le filtre doit revenir à « toutes »."""
        with tempfile.TemporaryDirectory() as directory:
            store = FavoritesStore(Path(directory) / "favorites.json")
            store.add("acme/model")
            store.update("acme/model", collection="Coding")
            store.update("acme/model", collection="")  # La collection "Coding" n'existe plus.

            items, dropdown = _refresh_after_mutation(store, "Coding")

            self.assertEqual(dropdown.value, "")
            self.assertEqual(len(items), 1)


if __name__ == "__main__":
    unittest.main()
