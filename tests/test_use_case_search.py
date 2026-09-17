"""Tests de la taxonomie d'usages et de son rapprochement avec des tâches Hub réelles."""

from __future__ import annotations

import unittest

from src.use_case_search import USE_CASES, find_use_case


class UseCaseSearchTests(unittest.TestCase):
    """Vérifier que chaque usage mène à au moins une tâche Hub réelle et non vide."""

    def test_every_use_case_maps_to_at_least_one_real_pipeline_tag(self) -> None:
        """Aucun usage ne doit rester sans tâche Hub concrète associée."""
        for use_case in USE_CASES:
            with self.subTest(use_case=use_case.key):
                self.assertGreater(len(use_case.tasks), 0)
                for task in use_case.tasks:
                    self.assertTrue(task.pipeline_tag)

    def test_use_case_keys_are_unique(self) -> None:
        """Deux usages ne doivent jamais partager la même clé stable."""
        keys = [item.key for item in USE_CASES]
        self.assertEqual(len(keys), len(set(keys)))

    def test_find_use_case_returns_none_for_unknown_key(self) -> None:
        """Une clé inconnue ne doit jamais lever d'exception."""
        self.assertIsNone(find_use_case("does-not-exist"))
        self.assertEqual(find_use_case("chatbot").key, "chatbot")


if __name__ == "__main__":
    unittest.main()
