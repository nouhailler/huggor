"""Métadonnées réelles de build pour l'écran « À propos ».

Rien n'est codé en dur : la version, le SHA de commit et l'URL de dépôt sont dérivés de Git
au moment où l'application démarre (voir /apropos). Une valeur non déterminable affiche
« — » plutôt que d'être inventée.
"""

from __future__ import annotations

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
    """Dériver la version depuis le tag Git le plus proche (``git describe``)."""
    return _run_git("describe", "--tags", "--always", "--dirty") or _UNKNOWN


def get_commit_sha() -> str:
    """SHA de commit court, tel qu'il tourne réellement."""
    return _run_git("rev-parse", "--short", "HEAD") or _UNKNOWN


def get_build_number() -> str:
    """Aucun système de build/CI n'attribue de numéro de build à ce projet.

    Champ volontairement affiché comme indéterminable (pas inventé) : voir /apropos,
    "si une valeur n'est pas déterminable, afficher « — » et le signaler".
    """
    return _UNKNOWN


def get_issue_url() -> str | None:
    """Dériver l'URL des issues GitHub depuis le remote ``origin`` réel du dépôt."""
    remote = _run_git("remote", "get-url", "origin")
    if not remote:
        return None
    match = re.search(r"github\.com[:/]+([^/]+)/(.+?)(?:\.git)?/?$", remote)
    if not match:
        return None
    owner, repo = match.group(1), match.group(2)
    return f"https://github.com/{owner}/{repo}/issues/new"


def get_repo_url() -> str | None:
    """Dériver l'URL web du dépôt (pour le lien README) depuis le remote ``origin``."""
    remote = _run_git("remote", "get-url", "origin")
    if not remote:
        return None
    match = re.search(r"github\.com[:/]+([^/]+)/(.+?)(?:\.git)?/?$", remote)
    if not match:
        return None
    owner, repo = match.group(1), match.group(2)
    return f"https://github.com/{owner}/{repo}"


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
