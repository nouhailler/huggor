"""Tests de structure de l'interface Gradio."""

from __future__ import annotations

import unittest

import gradio as gr

from app import connection_badge, create_app, create_theme


class StubClient:
    """Client minimal exposant seulement le statut requis par le header."""

    def __init__(self, has_token: bool) -> None:
        """Définir le statut d'authentification simulé."""
        self.has_token = has_token


class AppStructureTests(unittest.TestCase):
    """Vérifier que le squelette contient tous les éléments attendus."""

    def test_create_app_builds_six_named_tabs(self) -> None:
        """Les six onglets fonctionnels du cahier des charges doivent exister."""
        demo = create_app(StubClient(has_token=False))  # type: ignore[arg-type]
        labels = [
            component.get("props", {}).get("label")
            for component in demo.config["components"]
            if component.get("type") == "tabitem" and component.get("props", {}).get("id")
        ]

        self.assertIsInstance(demo, gr.Blocks)
        self.assertEqual(
            labels,
            ["🔍 Recherche", "📄 Détails", "🆚 Comparateur", "🧪 Test", "📈 Analytics", "⭐ Favoris"],
        )

    def test_connection_badge_never_contains_a_secret(self) -> None:
        """Le header doit indiquer un état, sans interpoler de token."""
        self.assertIn("Token HF configuré", connection_badge(True))
        self.assertIn("Accès public", connection_badge(False))

    def test_theme_is_soft(self) -> None:
        """L'application doit utiliser le thème Soft imposé."""
        self.assertIsInstance(create_theme(), gr.themes.Soft)


if __name__ == "__main__":
    unittest.main()
