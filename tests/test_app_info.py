"""Tests des métadonnées de build de l'écran « À propos »."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from src import app_info


class GitDerivedValuesTests(unittest.TestCase):
    """Vérifier que rien n'est codé en dur : tout vient (ou échoue proprement) de Git."""

    def test_app_version_is_never_empty(self) -> None:
        """Un dépôt Git valide doit toujours produire une valeur, jamais une chaîne vide."""
        self.assertTrue(app_info.get_app_version())

    def test_commit_sha_is_never_empty(self) -> None:
        """Idem pour le SHA de commit."""
        self.assertTrue(app_info.get_commit_sha())

    def test_missing_git_falls_back_to_unknown_marker(self) -> None:
        """Sans Git disponible, afficher « — » plutôt qu'inventer une valeur."""
        with patch.object(app_info, "_run_git", return_value=None):
            self.assertEqual(app_info.get_app_version(), "—")
            self.assertEqual(app_info.get_commit_sha(), "—")
            self.assertIsNone(app_info.get_issue_url())
            self.assertIsNone(app_info.get_repo_url())

    def test_build_number_is_always_the_unknown_marker(self) -> None:
        """Aucun système de build n'existe dans ce projet : ne jamais inventer un numéro."""
        self.assertEqual(app_info.get_build_number(), "—")


class IssueUrlDerivationTests(unittest.TestCase):
    """Vérifier la dérivation de l'URL d'issues depuis le remote Git réel, sans dépôt en dur."""

    def test_https_github_remote_is_converted_to_the_issues_url(self) -> None:
        with patch.object(app_info, "_run_git", return_value="https://github.com/nouhailler/huggor.git"):
            self.assertEqual(app_info.get_issue_url(), "https://github.com/nouhailler/huggor/issues/new")
            self.assertEqual(app_info.get_repo_url(), "https://github.com/nouhailler/huggor")

    def test_ssh_github_remote_is_converted_to_the_issues_url(self) -> None:
        with patch.object(app_info, "_run_git", return_value="git@github.com:nouhailler/huggor.git"):
            self.assertEqual(app_info.get_issue_url(), "https://github.com/nouhailler/huggor/issues/new")

    def test_non_github_remote_yields_no_url_rather_than_a_guess(self) -> None:
        with patch.object(app_info, "_run_git", return_value="https://gitlab.com/someone/other.git"):
            self.assertIsNone(app_info.get_issue_url())


class CopyrightYearTests(unittest.TestCase):
    """L'année de copyright ne doit jamais être figée en dur."""

    def test_current_year_is_a_plausible_recent_year(self) -> None:
        self.assertGreaterEqual(app_info.current_copyright_year(), 2024)


if __name__ == "__main__":
    unittest.main()
