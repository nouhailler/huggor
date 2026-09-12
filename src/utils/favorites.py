"""Persistance locale minimale des modèles favoris."""

from __future__ import annotations

import json
import os
import tempfile
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from huggingface_hub.utils import HFValidationError, validate_repo_id


class FavoritesError(RuntimeError):
    """Le fichier local des favoris est illisible ou impossible à modifier."""


@dataclass(frozen=True, slots=True)
class Favorite:
    """Modèle sauvegardé localement par l'utilisateur."""

    repo_id: str
    added_at: str
    note: str = ""

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> Favorite:
        """Restaurer et valider une entrée JSON."""
        repo_id = _validate_repo_id(str(value.get("repo_id") or ""))
        return cls(
            repo_id=repo_id,
            added_at=str(value.get("added_at") or ""),
            note=str(value.get("note") or ""),
        )

    def to_dict(self) -> dict[str, str]:
        """Convertir l'entrée en dictionnaire sérialisable."""
        return asdict(self)


class FavoritesStore:
    """Lire et modifier atomiquement le fichier JSON des favoris."""

    def __init__(self, path: str | Path) -> None:
        """Initialiser le stockage sans créer de favori."""
        self.path = Path(path)
        self._lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def add(self, repo_id: str, note: str = "") -> bool:
        """Ajouter un modèle et indiquer si une nouvelle entrée a été créée."""
        safe_repo_id = _validate_repo_id(repo_id)
        safe_note = note.strip()
        if len(safe_note) > 2_000:
            raise ValueError("La note ne peut pas dépasser 2 000 caractères.")

        with self._lock:
            favorites = self.list_favorites()
            if any(favorite.repo_id.casefold() == safe_repo_id.casefold() for favorite in favorites):
                return False

            favorites.append(
                Favorite(
                    repo_id=safe_repo_id,
                    added_at=datetime.now(timezone.utc).isoformat(),
                    note=safe_note,
                )
            )
            self._write(favorites)
        return True

    def list_favorites(self) -> list[Favorite]:
        """Retourner toutes les entrées valides du fichier local."""
        with self._lock:
            if not self.path.exists():
                return []
            try:
                content = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                raise FavoritesError("Le fichier des favoris est illisible.") from error
            if not isinstance(content, list):
                raise FavoritesError("Le fichier des favoris doit contenir une liste JSON.")

            try:
                return [Favorite.from_dict(item) for item in content if isinstance(item, dict)]
            except (ValueError, HFValidationError) as error:
                raise FavoritesError("Le fichier des favoris contient une entrée invalide.") from error

    def _write(self, favorites: list[Favorite]) -> None:
        """Remplacer le fichier par écriture atomique."""
        temporary_name: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temporary_name = handle.name
                json.dump(
                    [favorite.to_dict() for favorite in favorites],
                    handle,
                    ensure_ascii=False,
                    indent=2,
                )
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            Path(temporary_name).replace(self.path)
        except OSError as error:
            raise FavoritesError("Impossible d'enregistrer le favori.") from error
        finally:
            if temporary_name is not None:
                Path(temporary_name).unlink(missing_ok=True)


def _validate_repo_id(repo_id: str) -> str:
    """Valider un identifiant avant sa persistance locale."""
    cleaned = repo_id.strip()
    try:
        validate_repo_id(cleaned)
    except HFValidationError as error:
        raise ValueError("Identifiant de modèle invalide.") from error
    return cleaned
