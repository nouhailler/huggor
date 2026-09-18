"""Tests des métadonnées de build de l'écran « À propos »."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from src import app_info

# Environnement propre, sans variable RENDER_* : la plupart des tests veulent isoler le
# comportement de repli Git, indépendamment de la machine (locale ou Render) qui les exécute.
_NO_RENDER_ENV: dict[str, str] = {}


class GitDerivedValuesTests(unittest.TestCase):
    """Vérifier que rien n'est codé en dur : tout vient (ou échoue proprement) de Git/Render."""

    def test_app_version_is_never_empty(self) -> None:
        """Un dépôt Git valide doit toujours produire une valeur, jamais une chaîne vide."""
        self.assertTrue(app_info.get_app_version())

    def test_commit_sha_is_never_empty(self) -> None:
        """Idem pour le SHA de commit."""
        self.assertTrue(app_info.get_commit_sha())

    def test_missing_git_and_render_env_falls_back_to_unknown_marker(self) -> None:
        """Sans Git ni variables Render disponibles, afficher « — » plutôt qu'inventer une valeur."""
        with (
            patch.object(app_info, "_run_git", return_value=None),
            patch.dict(app_info.os.environ, _NO_RENDER_ENV, clear=True),
        ):
            self.assertEqual(app_info.get_app_version(), "—")
            self.assertEqual(app_info.get_commit_sha(), "—")
            self.assertIsNone(app_info.get_issue_url())
            self.assertIsNone(app_info.get_repo_url())

    def test_build_number_is_always_the_unknown_marker(self) -> None:
        """Aucun système de build n'existe dans ce projet : ne jamais inventer un numéro."""
        self.assertEqual(app_info.get_build_number(), "—")


class RenderEnvironmentPriorityTests(unittest.TestCase):
    """Sur Render, le clone Git est superficiel (confirmé empiriquement, voir app_info.py) :
    les variables RENDER_GIT_* doivent prendre le relais plutôt que produire un hash nu ou "—".
    """

    def test_commit_uses_the_render_variable_over_a_bare_git_hash(self) -> None:
        with (
            patch.object(app_info, "_run_git", return_value="0000000"),
            patch.dict(app_info.os.environ, {"RENDER_GIT_COMMIT": "abcdef1234567890"}, clear=True),
        ):
            self.assertEqual(app_info.get_commit_sha(), "abcdef1")

    def test_version_combines_render_branch_and_commit_when_no_real_tag_is_reachable(self) -> None:
        """Un clone superficiel sans tags fait échouer `git describe --tags` vers un hash nu ;
        reconstruire depuis Render reste plus honnête qu'un hash sans étiquette."""
        with (
            patch.object(app_info, "_run_git", return_value="abcdef1"),  # repli --always, pas un vrai tag
            patch.dict(
                app_info.os.environ,
                {"RENDER_GIT_BRANCH": "main", "RENDER_GIT_COMMIT": "abcdef1234567890"},
                clear=True,
            ),
        ):
            self.assertEqual(app_info.get_app_version(), "main@abcdef1")

    def test_version_still_prefers_a_real_git_tag_when_one_is_reachable(self) -> None:
        """Quand un vrai tag existe (dépôt local complet), il reste prioritaire sur Render."""
        with (
            patch.object(app_info, "_run_git", return_value="v0.3.0-2-gabcdef1"),
            patch.dict(
                app_info.os.environ,
                {"RENDER_GIT_BRANCH": "main", "RENDER_GIT_COMMIT": "abcdef1234567890"},
                clear=True,
            ),
        ):
            self.assertEqual(app_info.get_app_version(), "v0.3.0-2-gabcdef1")

    def test_repo_and_issue_urls_use_the_render_slug_over_git_remote(self) -> None:
        with (
            patch.object(app_info, "_run_git", return_value=None),
            patch.dict(app_info.os.environ, {"RENDER_GIT_REPO_SLUG": "nouhailler/huggor"}, clear=True),
        ):
            self.assertEqual(app_info.get_repo_url(), "https://github.com/nouhailler/huggor")
            self.assertEqual(app_info.get_issue_url(), "https://github.com/nouhailler/huggor/issues/new")


class IssueUrlDerivationTests(unittest.TestCase):
    """Vérifier la dérivation de l'URL d'issues depuis le remote Git réel, sans dépôt en dur."""

    def test_https_github_remote_is_converted_to_the_issues_url(self) -> None:
        with (
            patch.object(app_info, "_run_git", return_value="https://github.com/nouhailler/huggor.git"),
            patch.dict(app_info.os.environ, _NO_RENDER_ENV, clear=True),
        ):
            self.assertEqual(app_info.get_issue_url(), "https://github.com/nouhailler/huggor/issues/new")
            self.assertEqual(app_info.get_repo_url(), "https://github.com/nouhailler/huggor")

    def test_ssh_github_remote_is_converted_to_the_issues_url(self) -> None:
        with (
            patch.object(app_info, "_run_git", return_value="git@github.com:nouhailler/huggor.git"),
            patch.dict(app_info.os.environ, _NO_RENDER_ENV, clear=True),
        ):
            self.assertEqual(app_info.get_issue_url(), "https://github.com/nouhailler/huggor/issues/new")

    def test_non_github_remote_yields_no_url_rather_than_a_guess(self) -> None:
        with (
            patch.object(app_info, "_run_git", return_value="https://gitlab.com/someone/other.git"),
            patch.dict(app_info.os.environ, _NO_RENDER_ENV, clear=True),
        ):
            self.assertIsNone(app_info.get_issue_url())


class CopyrightYearTests(unittest.TestCase):
    """L'année de copyright ne doit jamais être figée en dur."""

    def test_current_year_is_a_plausible_recent_year(self) -> None:
        self.assertGreaterEqual(app_info.current_copyright_year(), 2024)


if __name__ == "__main__":
    unittest.main()
