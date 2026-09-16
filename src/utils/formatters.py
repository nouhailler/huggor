"""Fonctions de formatage sans dépendance à l'interface graphique."""

from __future__ import annotations

import html
from datetime import date, datetime
from typing import Any


def format_count(value: int | None) -> str:
    """Afficher un compteur sous une forme compacte et lisible."""
    if value is None:
        return "—"
    for threshold, suffix in ((1_000_000_000, "Md"), (1_000_000, "M"), (1_000, "k")):
        if abs(value) >= threshold:
            compact = value / threshold
            precision = 0 if compact >= 100 else 1
            return f"{compact:.{precision}f} {suffix}"
    return str(value)


def format_bytes(value: int | None) -> str:
    """Afficher une taille en unités binaires."""
    if value is None:
        return "—"
    size = float(value)
    for unit in ("o", "Kio", "Mio", "Gio", "Tio"):
        if abs(size) < 1024 or unit == "Tio":
            precision = 0 if unit == "o" else 1
            return f"{size:.{precision}f} {unit}"
        size /= 1024
    return f"{size:.1f} Tio"


def to_iso8601(value: Any) -> str | None:
    """Convertir une date reçue du Hub en chaîne ISO 8601 sérialisable."""
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def escape_markdown(value: str) -> str:
    """Neutraliser les caractères Markdown d'une valeur distante ou saisie par l'utilisateur."""
    escaped = html.escape(value).replace("\n", " ").replace("\r", " ")
    for character in "\\`*_{}[]<>()#+-.!|":
        escaped = escaped.replace(character, f"\\{character}")
    return escaped


def escape_inline_code(value: str) -> str:
    """Empêcher une valeur distante de fermer son fragment de code Markdown."""
    return html.escape(value).replace("`", "ˋ").replace("\n", " ").replace("\r", " ")

