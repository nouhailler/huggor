"""Tests du contenu centralisé des mentions légales."""

from __future__ import annotations

import unittest

from src.legal_notice import (
    EDITOR,
    GPS_WARNING,
    LIABILITY_SECTIONS,
    SHORT_WARNING,
    render_full_notice_markdown,
)

_EXPECTED_SECTION_TITLES = (
    "Avertissement",
    "Limitation de responsabilité",
    "Utilisation de l'application",
    "Exactitude des informations",
    "Dysfonctionnements et disponibilité",
    "Données et résultats",
    "Sources externes",
    "Évolution de l'application",
)


class LegalSectionsTests(unittest.TestCase):
    """Vérifier que les 8 sections minimales existent, sont non vides et jamais dupliquées."""

    def test_all_eight_minimal_sections_are_present_in_order(self) -> None:
        """La structure exigée par la spec doit être respectée exactement."""
        titles = tuple(section.title for section in LIABILITY_SECTIONS)
        self.assertEqual(titles, _EXPECTED_SECTION_TITLES)

    def test_no_section_is_empty(self) -> None:
        """Une section sans paragraphe se dégraderait silencieusement."""
        for section in LIABILITY_SECTIONS:
            with self.subTest(section=section.title):
                self.assertGreater(len(section.paragraphs), 0)
                for paragraph in section.paragraphs:
                    self.assertTrue(paragraph.strip())

    def test_short_warning_is_reused_as_the_first_section(self) -> None:
        """Le bandeau de premier lancement et la page complète partagent le même texte."""
        self.assertEqual(LIABILITY_SECTIONS[0].paragraphs, (SHORT_WARNING,))


class GpsSectionTests(unittest.TestCase):
    """Huggor n'utilise aucune géolocalisation : la section GPS ne doit jamais apparaître."""

    def test_gps_warning_is_explicitly_absent(self) -> None:
        """Absence volontaire et documentée, pas un oubli."""
        self.assertIsNone(GPS_WARNING)

    def test_rendered_markdown_never_mentions_localisation_precision(self) -> None:
        """Le rendu final ne doit jamais faire apparaître une section GPS non voulue."""
        markdown = render_full_notice_markdown()
        self.assertNotIn("Précision de la localisation", markdown)


class RenderFullNoticeMarkdownTests(unittest.TestCase):
    """Vérifier le rendu Markdown consolidé utilisé par la page permanente."""

    def test_every_section_title_and_paragraph_appears_in_the_render(self) -> None:
        """Aucun paragraphe ne doit être perdu lors de l'assemblage."""
        markdown = render_full_notice_markdown()
        for section in LIABILITY_SECTIONS:
            self.assertIn(f"## {section.title}", markdown)
            for paragraph in section.paragraphs:
                self.assertIn(paragraph, markdown)

    def test_editor_identity_is_never_invented(self) -> None:
        """Les informations éditeur affichées doivent venir du module, jamais d'un placeholder vide."""
        markdown = render_full_notice_markdown()
        for value in EDITOR.values():
            self.assertIn(value, markdown)


if __name__ == "__main__":
    unittest.main()
