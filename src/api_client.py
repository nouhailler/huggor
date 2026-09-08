"""Couche métier autour de l'API officielle du Hugging Face Hub."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from dotenv import load_dotenv
from huggingface_hub import HfApi, ModelCard, get_token
from huggingface_hub.errors import GatedRepoError, HfHubHTTPError, RepositoryNotFoundError
from huggingface_hub.utils import HFValidationError, validate_repo_id

from src.utils.cache import JsonCache
from src.utils.formatters import to_iso8601

SortOption = Literal["relevance", "likes", "downloads", "created_at", "last_modified"]

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_SAFE_FILTER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+\-]{0,79}$")
_SEARCH_EXPANSIONS = [
    "author",
    "createdAt",
    "downloads",
    "gated",
    "lastModified",
    "library_name",
    "likes",
    "pipeline_tag",
    "private",
    "safetensors",
    "tags",
]


class HuggingFaceClientError(RuntimeError):
    """Erreur métier sûre à afficher dans l'interface utilisateur."""


class ModelNotFoundError(HuggingFaceClientError):
    """Le dépôt demandé n'existe pas ou n'est pas visible."""


class AuthenticationError(HuggingFaceClientError):
    """Le Hub a refusé les informations d'authentification."""


class RateLimitError(HuggingFaceClientError):
    """La limite de requêtes du Hub a été atteinte."""


@dataclass(frozen=True, slots=True)
class SearchFilters:
    """Filtres validés acceptés par la recherche de modèles."""

    query: str = ""
    pipeline_tag: str | None = None
    language: str | None = None
    license: str | None = None
    min_parameters: int | None = None
    max_parameters: int | None = None
    sort: SortOption = "downloads"
    limit: int = 20

    def __post_init__(self) -> None:
        """Refuser les valeurs dangereuses ou incompatibles avec l'API."""
        query = self.query.strip()
        if len(query) > 200:
            raise ValueError("Le mot-clé ne peut pas dépasser 200 caractères.")
        object.__setattr__(self, "query", query)

        for field_name, value in (
            ("pipeline_tag", self.pipeline_tag),
            ("language", self.language),
            ("license", self.license),
        ):
            cleaned = value.strip() if value else None
            if cleaned is not None and not _SAFE_FILTER_RE.fullmatch(cleaned):
                raise ValueError(f"Le filtre {field_name} contient des caractères invalides.")
            object.__setattr__(self, field_name, cleaned)

        if not 5 <= self.limit <= 100:
            raise ValueError("La limite doit être comprise entre 5 et 100.")
        if self.sort not in {"relevance", "likes", "downloads", "created_at", "last_modified"}:
            raise ValueError("Critère de tri invalide.")
        if self.min_parameters is not None and self.min_parameters < 0:
            raise ValueError("Le nombre minimal de paramètres ne peut pas être négatif.")
        if self.max_parameters is not None and self.max_parameters < 0:
            raise ValueError("Le nombre maximal de paramètres ne peut pas être négatif.")
        if (
            self.min_parameters is not None
            and self.max_parameters is not None
            and self.min_parameters > self.max_parameters
        ):
            raise ValueError("Le minimum de paramètres dépasse le maximum.")

    def to_api_kwargs(self) -> dict[str, Any]:
        """Traduire les filtres de l'application vers ceux de ``HfApi``."""
        tags: list[str] = []
        if self.language:
            tags.append(self.language)
        if self.license:
            tags.append(f"license:{self.license}")

        parameter_parts: list[str] = []
        if self.min_parameters is not None:
            parameter_parts.append(f"min:{_format_parameter_filter(self.min_parameters)}")
        if self.max_parameters is not None:
            parameter_parts.append(f"max:{_format_parameter_filter(self.max_parameters)}")

        return {
            "search": self.query or None,
            "pipeline_tag": self.pipeline_tag,
            "filter": tags or None,
            "num_parameters": ",".join(parameter_parts) or None,
            "sort": None if self.sort == "relevance" else self.sort,
            "limit": self.limit,
            "expand": _SEARCH_EXPANSIONS,
        }


@dataclass(frozen=True, slots=True)
class ModelSummary:
    """Vue normalisée d'un modèle renvoyé par une recherche."""

    repo_id: str
    author: str | None
    likes: int
    downloads: int
    pipeline_tag: str | None
    library_name: str | None
    tags: tuple[str, ...]
    created_at: str | None
    last_modified: str | None
    parameters: int | None
    private: bool
    gated: bool | str

    @classmethod
    def from_hub(cls, model: Any) -> ModelSummary:
        """Normaliser un objet ``ModelInfo`` dont les champs sont optionnels."""
        repo_id = str(_read_field(model, "id") or _read_field(model, "modelId") or "")
        author = _read_field(model, "author")
        if author is None and "/" in repo_id:
            author = repo_id.split("/", maxsplit=1)[0]

        tags = _read_field(model, "tags") or []
        safetensors = _read_field(model, "safetensors")
        parameters = _read_field(safetensors, "total")

        return cls(
            repo_id=repo_id,
            author=str(author) if author is not None else None,
            likes=int(_read_field(model, "likes") or 0),
            downloads=int(_read_field(model, "downloads") or 0),
            pipeline_tag=_optional_string(_read_field(model, "pipeline_tag")),
            library_name=_optional_string(_read_field(model, "library_name")),
            tags=tuple(str(tag) for tag in tags),
            created_at=to_iso8601(_read_field(model, "created_at")),
            last_modified=to_iso8601(_read_field(model, "last_modified")),
            parameters=int(parameters) if parameters is not None else None,
            private=bool(_read_field(model, "private") or False),
            gated=_normalise_gated(_read_field(model, "gated")),
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ModelSummary:
        """Restaurer un résumé depuis le cache JSON."""
        values = dict(data)
        values["tags"] = tuple(values.get("tags") or ())
        return cls(**values)

    def to_dict(self) -> dict[str, Any]:
        """Convertir le résumé en valeur sérialisable en JSON."""
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ModelFile:
    """Fichier appartenant à un dépôt de modèle."""

    path: str
    size: int | None
    blob_id: str | None

    @classmethod
    def from_hub(cls, sibling: Any) -> ModelFile:
        """Normaliser un objet ``RepoSibling``."""
        size = _read_field(sibling, "size")
        return cls(
            path=str(_read_field(sibling, "rfilename") or ""),
            size=int(size) if size is not None else None,
            blob_id=_optional_string(_read_field(sibling, "blob_id")),
        )


@dataclass(frozen=True, slots=True)
class ModelDetails:
    """Informations détaillées et fichiers d'un modèle."""

    summary: ModelSummary
    files: tuple[ModelFile, ...]
    card_data: dict[str, Any]
    config: dict[str, Any]
    used_storage: int | None

    @classmethod
    def from_hub(cls, model: Any) -> ModelDetails:
        """Normaliser les détails renvoyés par ``model_info``."""
        siblings = _read_field(model, "siblings") or []
        card_data = _read_field(model, "card_data")
        if hasattr(card_data, "to_dict"):
            card_data = card_data.to_dict()
        config = _read_field(model, "config") or {}
        used_storage = _read_field(model, "used_storage")

        return cls(
            summary=ModelSummary.from_hub(model),
            files=tuple(ModelFile.from_hub(file) for file in siblings),
            card_data=_json_mapping(card_data),
            config=_json_mapping(config),
            used_storage=int(used_storage) if used_storage is not None else None,
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ModelDetails:
        """Restaurer les détails depuis le cache JSON."""
        return cls(
            summary=ModelSummary.from_dict(data["summary"]),
            files=tuple(ModelFile(**file) for file in data.get("files", [])),
            card_data=dict(data.get("card_data") or {}),
            config=dict(data.get("config") or {}),
            used_storage=data.get("used_storage"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convertir les détails en valeur sérialisable en JSON."""
        return asdict(self)


class HuggingFaceClient:
    """Fournir un accès borné, validé et mis en cache au Hugging Face Hub."""

    def __init__(
        self,
        token: str | bool | None = None,
        *,
        cache: JsonCache | None = None,
        cache_ttl: int = 900,
        api: HfApi | None = None,
    ) -> None:
        """Initialiser le client sans persister ni journaliser le token."""
        load_dotenv(_PROJECT_ROOT / ".env")
        self._token = token
        self._api = api or HfApi(token=token, library_name="hf-explorer")
        self._cache = cache or JsonCache(_PROJECT_ROOT / "data" / "cache", default_ttl=cache_ttl)

    @property
    def has_token(self) -> bool:
        """Indiquer si un token explicite, environnemental ou local est disponible."""
        if self._token is False:
            return False
        if isinstance(self._token, str):
            return bool(self._token.strip())
        return get_token() is not None

    def search_models(self, filters: SearchFilters | None = None) -> list[ModelSummary]:
        """Rechercher au plus 100 modèles, avec une limite de 20 par défaut."""
        safe_filters = filters or SearchFilters()
        cache_key = self._cache_key(asdict(safe_filters))
        cached = self._cache.get("search", cache_key)
        if isinstance(cached, list):
            return [ModelSummary.from_dict(item) for item in cached]

        try:
            # La présence obligatoire de limit empêche toute itération globale du Hub.
            models = list(self._api.list_models(**safe_filters.to_api_kwargs()))
            summaries = [ModelSummary.from_hub(model) for model in models]
        except Exception as error:
            raise self._translate_error(error) from error

        self._cache.set("search", cache_key, [model.to_dict() for model in summaries])
        return summaries

    def get_model_info(self, repo_id: str) -> ModelDetails:
        """Récupérer les métadonnées et tailles de fichiers d'un dépôt de modèle."""
        safe_repo_id = _validate_repo(repo_id)
        cache_key = self._cache_key({"repo_id": safe_repo_id})
        cached = self._cache.get("model", cache_key)
        if isinstance(cached, dict):
            return ModelDetails.from_dict(cached)

        try:
            model = self._api.model_info(safe_repo_id, files_metadata=True)
            details = ModelDetails.from_hub(model)
        except Exception as error:
            raise self._translate_error(error, repo_id=safe_repo_id) from error

        # Les métadonnées privées restent séparées par empreinte d'authentification.
        self._cache.set("model", cache_key, details.to_dict(), ttl=1800)
        return details

    def get_model_card(self, repo_id: str) -> str:
        """Récupérer la Model Card complète au format Markdown."""
        safe_repo_id = _validate_repo(repo_id)
        cache_key = self._cache_key({"repo_id": safe_repo_id})
        cached = self._cache.get("card", cache_key)
        if isinstance(cached, str):
            return cached

        try:
            card = ModelCard.load(safe_repo_id, token=self._token)
            markdown = str(card)
        except Exception as error:
            raise self._translate_error(error, repo_id=safe_repo_id) from error

        self._cache.set("card", cache_key, markdown, ttl=3600)
        return markdown

    def clear_cache(self) -> int:
        """Vider uniquement les entrées gérées par l'application."""
        return self._cache.clear()

    def _cache_key(self, payload: Mapping[str, Any]) -> str:
        """Créer une clé stable incluant une empreinte non réversible du contexte auth."""
        envelope = {"auth": self._authentication_scope(), "payload": payload}
        return json.dumps(envelope, ensure_ascii=True, sort_keys=True, separators=(",", ":"))

    def _authentication_scope(self) -> str:
        """Séparer les caches anonymes et authentifiés sans conserver le token."""
        if self._token is False:
            return "anonymous"
        token = self._token if isinstance(self._token, str) else get_token()
        if not token:
            return "anonymous"
        return "token-" + hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _translate_error(error: Exception, repo_id: str | None = None) -> HuggingFaceClientError:
        """Transformer les erreurs techniques en messages français sans secret."""
        if isinstance(error, HuggingFaceClientError):
            return error
        if isinstance(error, GatedRepoError):
            return AuthenticationError(
                "Ce modèle est protégé. Acceptez ses conditions sur le Hub et fournissez un token autorisé."
            )
        if isinstance(error, RepositoryNotFoundError):
            target = f" « {repo_id} »" if repo_id else ""
            return ModelNotFoundError(f"Le modèle{target} est introuvable ou inaccessible.")
        if isinstance(error, HfHubHTTPError):
            status = getattr(getattr(error, "response", None), "status_code", None)
            if status in {401, 403}:
                return AuthenticationError("Authentification Hugging Face refusée. Vérifiez votre token.")
            if status == 429:
                return RateLimitError("Limite de requêtes Hugging Face atteinte. Réessayez dans quelques instants.")
            return HuggingFaceClientError("Le Hugging Face Hub a renvoyé une erreur. Réessayez plus tard.")
        return HuggingFaceClientError(
            "Impossible de contacter le Hugging Face Hub. Vérifiez votre connexion et réessayez."
        )


def _validate_repo(repo_id: str) -> str:
    """Nettoyer et valider un identifiant de dépôt selon les règles officielles."""
    cleaned = repo_id.strip()
    try:
        validate_repo_id(cleaned)
    except HFValidationError as error:
        raise ValueError("Identifiant de modèle invalide (exemple : auteur/nom-du-modele).") from error
    return cleaned


def _format_parameter_filter(value: int) -> str:
    """Convertir un nombre brut dans le format compact attendu par le Hub."""
    for divisor, suffix in ((1_000_000_000, "B"), (1_000_000, "M"), (1_000, "K")):
        if value >= divisor:
            compact = value / divisor
            return f"{compact:.6f}".rstrip("0").rstrip(".") + suffix
    return str(value)


def _read_field(value: Any, field: str) -> Any:
    """Lire indifféremment un attribut d'objet ou une clé de dictionnaire."""
    if value is None:
        return None
    if isinstance(value, Mapping):
        return value.get(field)
    return getattr(value, field, None)


def _optional_string(value: Any) -> str | None:
    """Convertir une valeur optionnelle en chaîne."""
    return str(value) if value is not None else None


def _normalise_gated(value: Any) -> bool | str:
    """Conserver les états booléens ou textuels utilisés par le Hub."""
    if isinstance(value, (bool, str)):
        return value
    return False


def _json_mapping(value: Any) -> dict[str, Any]:
    """Normaliser un mapping potentiellement composé de types non JSON."""
    if not isinstance(value, Mapping):
        return {}
    normalised = json.loads(json.dumps(dict(value), default=str, ensure_ascii=False))
    return normalised if isinstance(normalised, dict) else {}

