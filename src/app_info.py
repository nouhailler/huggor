"""Métadonnées réelles de build pour l'écran « À propos ».

Rien n'est codé en dur. Deux sources possibles, jamais un troisième choix inventé :

1. Les variables ``RENDER_GIT_*`` que Render injecte lui-même à l'exécution — nécessaires car
   Render déploie depuis un clone Git superficiel (``git rev-parse --is-shallow-repository``
   y répond ``true``) sans tags ni remote ``origin`` configuré, ce qui fait échouer toute
   dérivation par commande ``git`` locale (confirmé empiriquement le 2026-09-18 via un
   diagnostic de démarrage temporaire — voir l'historique Git de ce fichier).
2. À défaut (exécution locale, ou tout autre hébergeur), les commandes ``git`` locales, qui
   fonctionnent normalement quand le dépôt est complet.

Une valeur non déterminable par aucune des deux affiche « — » plutôt que d'être inventée.
"""

from __future__ import annotations

import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_UNKNOWN = "—"


def _run_git(*args: str) -> str | None:
    """Exécuter une commande git dans le dépôt, ou renvoyer None si indisponible."""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    output = result.stdout.strip()
    return output or None


def get_app_version() -> str:
    """Version : tag Git s'il est atteignable, sinon branche+commit fournis par Render.

    Un clone superficiel sans tags (le cas sur Render, confirmé empiriquement) fait échouer
    ``git describe --tags`` silencieusement vers son repli ``--always`` — un simple hash, pas
    une vraie version. Dans ce cas précis, reconstruire depuis ``RENDER_GIT_BRANCH``/
    ``RENDER_GIT_COMMIT`` reste plus honnête qu'un hash nu sans étiquette.
    """
    described = _run_git("describe", "--tags", "--always", "--dirty")
    looks_like_a_real_tag = bool(described) and not re.fullmatch(r"[0-9a-f]{4,40}(-dirty)?", described)
    if looks_like_a_real_tag:
        return described  # type: ignore[return-value]

    render_branch = os.environ.get("RENDER_GIT_BRANCH")
    render_commit = os.environ.get("RENDER_GIT_COMMIT")
    if render_branch and render_commit:
        return f"{render_branch}@{render_commit[:7]}"

    return described or _UNKNOWN


def get_commit_sha() -> str:
    """SHA de commit court : Render en priorité (fiable même sur un clone superficiel), sinon Git local."""
    render_commit = os.environ.get("RENDER_GIT_COMMIT")
    if render_commit:
        return render_commit[:7]
    return _run_git("rev-parse", "--short", "HEAD") or _UNKNOWN


def get_build_number() -> str:
    """Aucun système de build/CI n'attribue de numéro de build à ce projet.

    Champ volontairement affiché comme indéterminable (pas inventé) : voir /apropos,
    "si une valeur n'est pas déterminable, afficher « — » et le signaler".
    """
    return _UNKNOWN


def _github_slug_from_git_remote() -> str | None:
    """Repli local : extraire ``owner/repo`` du remote ``origin`` (absent sur Render)."""
    remote = _run_git("remote", "get-url", "origin")
    if not remote:
        return None
    match = re.search(r"github\.com[:/]+([^/]+)/(.+?)(?:\.git)?/?$", remote)
    return f"{match.group(1)}/{match.group(2)}" if match else None


def _github_slug() -> str | None:
    """``owner/repo`` : variable Render en priorité, sinon remote Git local."""
    return os.environ.get("RENDER_GIT_REPO_SLUG") or _github_slug_from_git_remote()


def get_issue_url() -> str | None:
    """Dériver l'URL des issues GitHub, jamais un dépôt codé en dur."""
    slug = _github_slug()
    return f"https://github.com/{slug}/issues/new" if slug else None


def get_repo_url() -> str | None:
    """Dériver l'URL web du dépôt (pour le lien README), jamais un dépôt codé en dur."""
    slug = _github_slug()
    return f"https://github.com/{slug}" if slug else None


def current_copyright_year() -> int:
    """Année courante, jamais figée dans le code."""
    return datetime.now().year


# Licences des dépendances directes de requirements.txt, vérifiées via `pip show <paquet>`
# le 2026-09-18 — à revérifier si requirements.txt change de version épinglée.
DEPENDENCY_CREDITS: tuple[tuple[str, str], ...] = (
    ("gradio", "Apache-2.0"),
    ("huggingface-hub", "Apache-2.0"),
    ("pandas", "BSD-3-Clause"),
    ("plotly", "MIT"),
    ("python-dotenv", "BSD-3-Clause"),
)
