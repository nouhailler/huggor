"""Tests du contenu centralisé de la visite guidée."""

from __future__ import annotations

import unittest

from src.onboarding import ONBOARDING_STEPS


class OnboardingStepsTests(unittest.TestCase):
    """Vérifier que les étapes existent, sont non vides et jamais dupliquées."""

    def test_there_are_at_least_two_steps(self) -> None:
        """Une visite guidée à une seule étape n'aurait aucun intérêt."""
        self.assertGreaterEqual(len(ONBOARDING_STEPS), 2)

    def test_no_step_is_empty(self) -> None:
        """Une étape sans titre ou sans corps se dégraderait silencieusement."""
        for step in ONBOARDING_STEPS:
            with self.subTest(step=step.title):
                self.assertTrue(step.title.strip())
                self.assertTrue(step.body.strip())

    def test_titles_are_unique(self) -> None:
        """Deux étapes identiques indiqueraient une erreur de contenu."""
        titles = [step.title for step in ONBOARDING_STEPS]
        self.assertEqual(len(titles), len(set(titles)))


if __name__ == "__main__":
    unittest.main()
