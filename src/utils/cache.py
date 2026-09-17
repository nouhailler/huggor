"""Cache JSON local, atomique et limité dans le temps."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
import time
from pathlib import Path
from typing import Any


class JsonCache:
    """Stocker des valeurs sérialisables en JSON dans des fichiers individuels."""

    def __init__(self, directory: str | Path, default_ttl: int = 900) -> None:
        """Créer un cache dans ``directory`` avec une durée de vie en secondes."""
        if default_ttl <= 0:
            raise ValueError("La durée de vie du cache doit être positive.")

        self.directory = Path(directory)
        self.default_ttl = default_ttl
        self._lock = threading.RLock()
        self.directory.mkdir(parents=True, exist_ok=True)

    def get(self, namespace: str, key: str) -> Any | None:
        """Retourner une valeur non expirée, ou ``None`` en cas d'absence."""
        path = self._path_for(namespace, key)
        with self._lock:
            try:
                with path.open("r", encoding="utf-8") as handle:
                    entry = json.load(handle)
                if not isinstance(entry, dict) or entry.get("version") != 1:
                    return None
                if float(entry["expires_at"]) <= time.time():
                    path.unlink(missing_ok=True)
                    return None
                return entry.get("value")
            except (FileNotFoundError, json.JSONDecodeError, KeyError, TypeError, ValueError, OSError):
                # Un cache défectueux ne doit jamais bloquer un appel au Hub.
                return None

    def get_allow_stale(self, namespace: str, key: str) -> tuple[Any, float] | None:
        """Relire une entrée même expirée, avec son âge : secours pour le mode hors connexion.

        Contrairement à ``get()``, une entrée expirée n'est ni ignorée ni supprimée ici : elle
        reste la meilleure donnée disponible quand le Hub est injoignable. Un appelant qui a
        déjà réussi une requête réseau n'a aucune raison d'utiliser cette méthode.
        """
        path = self._path_for(namespace, key)
        with self._lock:
            try:
                with path.open("r", encoding="utf-8") as handle:
                    entry = json.load(handle)
                if not isinstance(entry, dict) or entry.get("version") != 1:
                    return None
                age = max(time.time() - float(entry["created_at"]), 0.0)
                return entry.get("value"), age
            except (FileNotFoundError, json.JSONDecodeError, KeyError, TypeError, ValueError, OSError):
                return None

    def set(
        self,
        namespace: str,
        key: str,
        value: Any,
        *,
        ttl: int | None = None,
    ) -> None:
        """Écrire une valeur de façon atomique dans le cache."""
        effective_ttl = self.default_ttl if ttl is None else ttl
        if effective_ttl <= 0:
            raise ValueError("La durée de vie du cache doit être positive.")

        now = time.time()
        entry = {
            "version": 1,
            "created_at": now,
            "expires_at": now + effective_ttl,
            "value": value,
        }
        path = self._path_for(namespace, key)

        with self._lock:
            temporary_name: str | None = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode="w",
                    encoding="utf-8",
                    dir=self.directory,
                    prefix=f".{path.name}.",
                    suffix=".tmp",
                    delete=False,
                ) as handle:
                    temporary_name = handle.name
                    json.dump(entry, handle, ensure_ascii=False, separators=(",", ":"))
                    handle.flush()
                    os.fsync(handle.fileno())
                Path(temporary_name).replace(path)
            finally:
                if temporary_name is not None:
                    Path(temporary_name).unlink(missing_ok=True)

    def clear(self, namespace: str | None = None) -> int:
        """Supprimer les entrées du namespace demandé et retourner leur nombre."""
        prefix = "" if namespace is None else f"{self._safe_namespace(namespace)}-"
        removed = 0
        with self._lock:
            for path in self.directory.glob(f"{prefix}*.json"):
                if path.is_file():
                    path.unlink(missing_ok=True)
                    removed += 1
        return removed

    def age_seconds(self, namespace: str, key: str) -> float | None:
        """Âge en secondes de l'entrée si elle existe et n'est pas expirée, sinon ``None``."""
        path = self._path_for(namespace, key)
        with self._lock:
            try:
                with path.open("r", encoding="utf-8") as handle:
                    entry = json.load(handle)
                if not isinstance(entry, dict) or entry.get("version") != 1:
                    return None
                if float(entry["expires_at"]) <= time.time():
                    return None
                return max(time.time() - float(entry["created_at"]), 0.0)
            except (FileNotFoundError, json.JSONDecodeError, KeyError, TypeError, ValueError, OSError):
                return None

    def iter_entries(self, namespace: str | None = None) -> list[tuple[float, int]]:
        """Lister (date de création, taille en octets) de chaque entrée valide du namespace.

        Pensé pour l'administration du cache (statistiques, purge ciblée), pas pour la lecture
        normale : une entrée expirée ou corrompue est simplement ignorée, jamais supprimée ici.
        """
        prefix = "" if namespace is None else f"{self._safe_namespace(namespace)}-"
        entries: list[tuple[float, int]] = []
        with self._lock:
            for path in self.directory.glob(f"{prefix}*.json"):
                if not path.is_file():
                    continue
                try:
                    with path.open("r", encoding="utf-8") as handle:
                        entry = json.load(handle)
                    if not isinstance(entry, dict) or entry.get("version") != 1:
                        continue
                    if float(entry["expires_at"]) <= time.time():
                        continue
                    entries.append((float(entry["created_at"]), path.stat().st_size))
                except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
                    continue
        return entries

    def _path_for(self, namespace: str, key: str) -> Path:
        """Produire un chemin stable sans réutiliser directement l'entrée utilisateur."""
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self.directory / f"{self._safe_namespace(namespace)}-{digest}.json"

    @staticmethod
    def _safe_namespace(namespace: str) -> str:
        """Valider un namespace interne avant son utilisation comme nom de fichier."""
        if not namespace or not namespace.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Namespace de cache invalide.")
        return namespace

