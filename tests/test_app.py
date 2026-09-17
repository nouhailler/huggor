"""Tests de structure de l'interface Gradio."""

from __future__ import annotations

import unittest

import gradio as gr

from app import (
    NAV_CATEGORIES,
    connection_badge,
    create_app,
    create_theme,
    select_tab_from_menu,
    toggle_nav_menu,
)


class StubClient:
    """Client minimal exposant seulement le statut requis par le header."""

    def __init__(self, has_token: bool) -> None:
        """Définir le statut d'authentification simulé."""
        self.has_token = has_token
        self.cache_scope = "anonymous"


class AppStructureTests(unittest.TestCase):
    """Vérifier que le squelette contient tous les éléments attendus."""

    def test_create_app_builds_eight_named_tabs(self) -> None:
        """Les huit onglets fonctionnels du cahier des charges doivent exister."""
        demo = create_app(StubClient(has_token=False))  # type: ignore[arg-type]
        labels = [
            component.get("props", {}).get("label")
            for component in demo.config["components"]
            if component.get("type") == "tabitem" and component.get("props", {}).get("id")
        ]

        self.assertIsInstance(demo, gr.Blocks)
        self.assertEqual(
            labels,
            [
                "🔍 Recherche",
                "🎯 Mon usage",
                "📄 Détails",
                "💻 Hardware",
                "🆚 Comparateur",
                "🧪 Test",
                "📈 Analytics",
                "⭐ Favoris",
            ],
        )

    def test_connection_badge_never_contains_a_secret(self) -> None:
        """Le header doit indiquer un état, sans interpoler de token."""
        self.assertIn("Token HF configuré", connection_badge(True))
        self.assertIn("Accès public", connection_badge(False))

    def test_theme_is_soft(self) -> None:
        """L'application doit utiliser le thème Soft imposé."""
        self.assertIsInstance(create_theme(), gr.themes.Soft)


class HamburgerMenuTests(unittest.TestCase):
    """Vérifier que le menu hamburger couvre bien les huit onglets, par catégorie."""

    def test_every_tab_is_reachable_from_exactly_one_category(self) -> None:
        """Aucun onglet ne doit manquer ou apparaître deux fois dans le menu."""
        expected_ids = {"search", "usage", "details", "hardware", "compare", "test", "analytics", "favorites"}
        menu_ids = [tab_id for _category, items in NAV_CATEGORIES for tab_id, _label in items]

        self.assertEqual(set(menu_ids), expected_ids)
        self.assertEqual(len(menu_ids), len(set(menu_ids)))

    def test_toggle_opens_then_closes(self) -> None:
        """Le bouton hamburger doit inverser l'état à chaque clic."""
        opened_state, opened_column = toggle_nav_menu(False)
        closed_state, closed_column = toggle_nav_menu(True)

        self.assertTrue(opened_state)
        self.assertTrue(opened_column.visible)
        self.assertFalse(closed_state)
        self.assertFalse(closed_column.visible)

    def test_selecting_a_tab_closes_the_menu_and_selects_it(self) -> None:
        """Choisir un onglet dans le menu doit naviguer puis refermer le panneau."""
        selected_tabs, is_open, column = select_tab_from_menu("hardware")

        self.assertEqual(selected_tabs.selected, "hardware")
        self.assertFalse(is_open)
        self.assertFalse(column.visible)


if __name__ == "__main__":
    unittest.main()
