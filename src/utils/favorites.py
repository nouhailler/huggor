"""Persistance locale des modèles favoris : collections, notes, tags, statut, score et suivi de test."""

from __future__ import annotations

import json
import os
import tempfile
import threading
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from huggingface_hub.utils import HFValidationError, validate_repo_id

_MAX_NOTE_LENGTH = 2_000
_MAX_COLLECTION_LENGTH = 200
_MAX_STATUS_LENGTH = 100
_MAX_DATE_LENGTH = 40
_MAX_TAG_LENGTH = 40
_MAX_TAGS = 20


class FavoritesError(RuntimeError):
    """Le fichier local des favoris est illisible ou impossible à modifier."""


@dataclass(frozen=True, slots=True)
class Favorite:
    """Modèle sauvegardé localement par l'utilisateur, avec son classement personnel."""

    repo_id: str
    added_at: str
    note: str = ""
    collection: str = ""
    tags: tuple[str, ...] = ()
    status: str = ""
    last_tested_at: str = ""
    score: int | None = None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> Favorite:
        """Restaurer et valider une entrée JSON, tolérante aux favoris enregistrés avant ces champs."""
        repo_id = _validate_repo_id(str(value.get("repo_id") or ""))
        raw_tags = value.get("tags")
        tags = tuple(str(tag) for tag in raw_tags) if isinstance(raw_tags, list) else ()
        raw_score = value.get("score")
        score = int(raw_score) if isinstance(raw_score, (int, float)) and 1 <= int(raw_score) <= 5 else None
        return cls(
            repo_id=repo_id,
            added_at=str(value.get("added_at") or ""),
            note=str(value.get("note") or ""),
            collection=str(value.get("collection") or ""),
            tags=tags,
            status=str(value.get("status") or ""),
            last_tested_at=str(value.get("last_tested_at") or ""),
            score=score,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convertir l'entrée en dictionnaire sérialisable."""
        return asdict(self)


class FavoritesStore:
    """Lire et modifier atomiquement le fichier JSON des favoris."""

    def __init__(self, path: str | Path) -> None:
        """Initialiser le stockage sans créer de favori."""
        self.path = Path(path)
        self._lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def add(self, repo_id: str, note: str = "", collection: str = "") -> bool:
        """Ajouter un modèle et indiquer si une nouvelle entrée a été créée."""
        safe_repo_id = _validate_repo_id(repo_id)
        safe_note = _clean_text(note, _MAX_NOTE_LENGTH, "La note")
        safe_collection = _clean_text(collection, _MAX_COLLECTION_LENGTH, "Le nom de collection")

        with self._lock:
            favorites = self.list_favorites()
            if any(favorite.repo_id.casefold() == safe_repo_id.casefold() for favorite in favorites):
                return False

            favorites.append(
                Favorite(
                    repo_id=safe_repo_id,
                    added_at=datetime.now(timezone.utc).isoformat(),
                    note=safe_note,
                    collection=safe_collection,
                )
            )
            self._write(favorites)
        return True

    def update(
        self,
        repo_id: str,
        *,
        note: str | None = None,
        collection: str | None = None,
        tags: Sequence[str] | None = None,
        status: str | None = None,
        last_tested_at: str | None = None,
        score: int | None = None,
        clear_score: bool = False,
    ) -> Favorite:
        """Modifier les métadonnées personnelles d'un favori déjà enregistré.

        Chaque champ omis (``None``) conserve sa valeur actuelle. ``clear_score`` efface
        explicitement la note personnelle, puisque ``score=None`` seul signifie « inchangé ».
        """
        safe_repo_id = _validate_repo_id(repo_id)
        safe_note = _clean_text(note, _MAX_NOTE_LENGTH, "La note") if note is not None else None
        safe_collection = (
            _clean_text(collection, _MAX_COLLECTION_LENGTH, "Le nom de collection") if collection is not None else None
        )
        safe_status = _clean_text(status, _MAX_STATUS_LENGTH, "Le statut") if status is not None else None
        safe_date = _clean_text(last_tested_at, _MAX_DATE_LENGTH, "La date de test") if last_tested_at is not None else None
        safe_tags = _clean_tags(tags) if tags is not None else None
        safe_score = _validate_score(score) if score is not None else None

        with self._lock:
            favorites = self.list_favorites()
            index = next(
                (i for i, favorite in enumerate(favorites) if favorite.repo_id.casefold() == safe_repo_id.casefold()),
                None,
            )
            if index is None:
                raise ValueError(f"« {repo_id} » ne figure pas dans vos favoris.")

            current = favorites[index]
            updated = Favorite(
                repo_id=current.repo_id,
                added_at=current.added_at,
                note=current.note if safe_note is None else safe_note,
                collection=current.collection if safe_collection is None else safe_collection,
                tags=current.tags if safe_tags is None else safe_tags,
                status=current.status if safe_status is None else safe_status,
                last_tested_at=current.last_tested_at if safe_date is None else safe_date,
                score=None if clear_score else (current.score if safe_score is None else safe_score),
            )
            favorites[index] = updated
            self._write(favorites)
        return updated

    def remove(self, repo_id: str) -> bool:
        """Retirer un favori ; indique s'il existait réellement."""
        safe_repo_id = _validate_repo_id(repo_id)
        with self._lock:
            favorites = self.list_favorites()
            remaining = [favorite for favorite in favorites if favorite.repo_id.casefold() != safe_repo_id.casefold()]
            if len(remaining) == len(favorites):
                return False
            self._write(remaining)
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

    def list_collections(self) -> list[str]:
        """Lister les collections utilisées, triées et sans doublons."""
        favorites = self.list_favorites()
        return sorted({favorite.collection for favorite in favorites if favorite.collection})

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


def _clean_text(value: str, max_length: int, field_label: str) -> str:
    """Nettoyer un champ texte libre et refuser un contenu trop long."""
    cleaned = value.strip()
    if len(cleaned) > max_length:
        raise ValueError(f"{field_label} ne peut pas dépasser {max_length} caractères.")
    return cleaned


def _clean_tags(tags: Sequence[str]) -> tuple[str, ...]:
    """Nettoyer et dédupliquer une liste de tags, sans en accepter un nombre excessif."""
    cleaned = tuple(dict.fromkeys(tag.strip() for tag in tags if tag.strip()))
    if len(cleaned) > _MAX_TAGS:
        raise ValueError(f"{_MAX_TAGS} tags au maximum par favori.")
    for tag in cleaned:
        if len(tag) > _MAX_TAG_LENGTH:
            raise ValueError(f"Un tag ne peut pas dépasser {_MAX_TAG_LENGTH} caractères.")
    return cleaned


def _validate_score(score: int) -> int:
    """Vérifier que la note personnelle reste dans l'échelle affichée (1 à 5)."""
    if not 1 <= score <= 5:
        raise ValueError("La note personnelle doit être comprise entre 1 et 5.")
    return score
