"""Tests unitaires du wrapper Hugging Face sans requête réseau."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from huggingface_hub.errors import EntryNotFoundError

from src.api_client import HuggingFaceClient, SearchFilters
from src.utils.cache import JsonCache


class FakeApi:
    """Double minimal de ``HfApi`` enregistrant les appels reçus."""

    def __init__(self) -> None:
        """Initialiser les compteurs du double."""
        self.search_calls: list[dict[str, object]] = []
        self.info_calls: list[tuple[str, bool]] = []
        self.next_search_error: Exception | None = None
        self.next_info_error: Exception | None = None

    def list_models(self, **kwargs: object) -> list[SimpleNamespace]:
        """Renvoyer un modèle synthétique pour la recherche, ou lever l'erreur programmée."""
        self.search_calls.append(kwargs)
        if self.next_search_error is not None:
            error, self.next_search_error = self.next_search_error, None
            raise error
        return [
            SimpleNamespace(
                id="acme/modele",
                author="acme",
                likes=12,
                downloads=345,
                pipeline_tag="text-classification",
                library_name="transformers",
                tags=["fr", "license:apache-2.0"],
                created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
                last_modified=datetime(2024, 2, 1, tzinfo=timezone.utc),
                safetensors=SimpleNamespace(total=1_500_000),
                private=False,
                gated=False,
            )
        ]

    def model_info(self, repo_id: str, *, files_metadata: bool) -> SimpleNamespace:
        """Renvoyer des détails synthétiques avec une taille de fichier, ou lever l'erreur programmée."""
        self.info_calls.append((repo_id, files_metadata))
        if self.next_info_error is not None:
            error, self.next_info_error = self.next_info_error, None
            raise error
        return SimpleNamespace(
            id=repo_id,
            author="acme",
            likes=12,
            downloads=345,
            pipeline_tag="text-classification",
            library_name="transformers",
            tags=["fr"],
            created_at=None,
            last_modified=None,
            safetensors=SimpleNamespace(total=1_500_000, parameters={"F32": 1_500_000}),
            private=False,
            gated=False,
            siblings=[SimpleNamespace(rfilename="model.safetensors", size=42, blob_id="abc")],
            card_data={"license": "apache-2.0"},
            config={"architectures": ["BertForSequenceClassification"]},
            used_storage=42,
        )


class SearchFiltersTests(unittest.TestCase):
    """Vérifier la validation et la traduction des filtres."""

    def test_defaults_always_include_limit(self) -> None:
        """La recherche par défaut doit rester strictement bornée."""
        self.assertEqual(SearchFilters().to_api_kwargs()["limit"], 20)

    def test_filters_are_translated_for_hub(self) -> None:
        """Les filtres UI doivent employer le format attendu par le Hub."""
        filters = SearchFilters(
            query="  bert  ",
            pipeline_tag="text-classification",
            language="fr",
            license="apache-2.0",
            min_parameters=1_500_000,
            max_parameters=7_000_000_000,
            sort="relevance",
            limit=25,
        )

        kwargs = filters.to_api_kwargs()

        self.assertEqual(kwargs["search"], "bert")
        self.assertEqual(kwargs["filter"], ["fr", "license:apache-2.0"])
        self.assertEqual(kwargs["num_parameters"], "min:1.5M,max:7B")
        self.assertIsNone(kwargs["sort"])
        self.assertEqual(kwargs["limit"], 25)

    def test_invalid_limits_and_ranges_are_rejected(self) -> None:
        """Les bornes dangereuses ou incohérentes doivent être refusées."""
        with self.assertRaises(ValueError):
            SearchFilters(limit=101)
        with self.assertRaises(ValueError):
            SearchFilters(min_parameters=10, max_parameters=5)


class HuggingFaceClientTests(unittest.TestCase):
    """Vérifier les appels réseau simulés et l'utilisation du cache."""

    def setUp(self) -> None:
        """Créer un cache temporaire et un faux client pour chaque test."""
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.fake_api = FakeApi()
        self.client = HuggingFaceClient(
            token=False,
            cache=JsonCache(self.temporary_directory.name),
            api=self.fake_api,  # type: ignore[arg-type]
        )

    def tearDown(self) -> None:
        """Libérer le répertoire temporaire."""
        self.temporary_directory.cleanup()

    def test_search_is_limited_and_cached(self) -> None:
        """Deux recherches identiques ne doivent effectuer qu'un appel au Hub."""
        filters = SearchFilters(query="modele", limit=20)

        first = self.client.search_models(filters)
        second = self.client.search_models(filters)

        self.assertEqual(first, second)
        self.assertEqual(first[0].repo_id, "acme/modele")
        self.assertEqual(self.fake_api.search_calls[0]["limit"], 20)
        self.assertEqual(len(self.fake_api.search_calls), 1)

    def test_model_info_requests_file_metadata_and_is_cached(self) -> None:
        """Les détails doivent inclure la taille des fichiers sans second appel."""
        first = self.client.get_model_info("acme/modele")
        second = self.client.get_model_info("acme/modele")

        self.assertEqual(first, second)
        self.assertEqual(first.files[0].size, 42)
        self.assertEqual(first.tensor_dtypes, ("F32",))
        self.assertEqual(self.fake_api.info_calls, [("acme/modele", True)])

    def test_model_info_enriches_the_api_summary_from_config_json(self) -> None:
        """Le contexte, le vocabulaire et le dtype doivent provenir du vrai config.json."""
        self.fake_api.model_info = lambda repo_id, files_metadata: SimpleNamespace(
            id=repo_id,
            author="acme",
            likes=0,
            downloads=0,
            pipeline_tag="text-generation",
            library_name="transformers",
            tags=[],
            created_at=None,
            last_modified=None,
            safetensors=SimpleNamespace(total=10),
            private=False,
            gated=False,
            siblings=[SimpleNamespace(rfilename="config.json", size=100, blob_id="config")],
            card_data={},
            config={"architectures": ["Qwen2ForCausalLM"], "model_type": "qwen2"},
            used_storage=100,
        )
        config_path = Path(self.temporary_directory.name) / "config.json"
        config_path.write_text(
            json.dumps(
                {
                    "max_position_embeddings": 32_768,
                    "vocab_size": 151_936,
                    "torch_dtype": "bfloat16",
                }
            ),
            encoding="utf-8",
        )

        with patch("src.api_client.hf_hub_download", return_value=str(config_path)) as download:
            details = self.client.get_model_info("acme/full-config")

        self.assertEqual(details.config["max_position_embeddings"], 32_768)
        self.assertEqual(details.config["vocab_size"], 151_936)
        self.assertEqual(details.config["architectures"], ["Qwen2ForCausalLM"])
        download.assert_called_once_with(
            repo_id="acme/full-config",
            filename="config.json",
            token=False,
        )

    def test_model_card_is_cached(self) -> None:
        """La Model Card Markdown doit être récupérée une seule fois."""
        with patch("src.api_client.ModelCard.load") as load:
            load.return_value = "# Carte"

            first = self.client.get_model_card("acme/modele")
            second = self.client.get_model_card("acme/modele")

        self.assertEqual(first, "# Carte")
        self.assertEqual(second, "# Carte")
        load.assert_called_once_with("acme/modele", token=False)

    def test_missing_model_card_returns_a_markdown_placeholder(self) -> None:
        """Un dépôt sans README doit conserver une fiche exploitable."""
        with patch("src.api_client.ModelCard.load", side_effect=EntryNotFoundError("absent")):
            card = self.client.get_model_card("acme/sans-carte")

        self.assertIn("acme/sans-carte", card)
        self.assertIn("Model Card", card)

    def test_invalid_repo_id_is_rejected_before_network(self) -> None:
        """Un identifiant invalide ne doit jamais atteindre le Hub."""
        with self.assertRaises(ValueError):
            self.client.get_model_info("a/b/c")
        self.assertEqual(self.fake_api.info_calls, [])

    def test_force_refresh_bypasses_the_cache_but_repopulates_it(self) -> None:
        """« Actualiser depuis Hugging Face » doit ignorer le cache, pas le désactiver durablement."""
        self.client.get_model_info("acme/modele")
        self.client.get_model_info("acme/modele", force_refresh=True)
        self.client.get_model_info("acme/modele")

        self.assertEqual(len(self.fake_api.info_calls), 2)  # Le 3e appel réutilise le cache réécrit.

    def test_model_info_age_seconds_is_none_before_any_fetch(self) -> None:
        """Sans fiche jamais chargée, il ne doit pas y avoir de « dernière mise à jour »."""
        self.assertIsNone(self.client.model_info_age_seconds("acme/jamais-charge"))

    def test_model_info_age_seconds_reflects_the_cached_fetch(self) -> None:
        """Après un chargement, l'âge doit être mesurable et très récent."""
        self.client.get_model_info("acme/modele")

        age = self.client.model_info_age_seconds("acme/modele")

        self.assertIsNotNone(age)
        self.assertLess(age, 5.0)

    def test_model_card_force_refresh_bypasses_the_cache(self) -> None:
        """Le rafraîchissement doit aussi s'appliquer à la Model Card, pas seulement aux métadonnées."""
        with patch("src.api_client.ModelCard.load") as load:
            load.side_effect = ["# Ancienne", "# Nouvelle"]

            first = self.client.get_model_card("acme/modele")
            refreshed = self.client.get_model_card("acme/modele", force_refresh=True)

        self.assertEqual(first, "# Ancienne")
        self.assertEqual(refreshed, "# Nouvelle")
        self.assertEqual(load.call_count, 2)


class OfflineModeTests(unittest.TestCase):
    """Vérifier la détection de connectivité et la dégradation gracieuse hors connexion."""

    def setUp(self) -> None:
        """Créer un cache temporaire et un faux client pour chaque test."""
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.fake_api = FakeApi()
        self.client = HuggingFaceClient(
            token=False,
            cache=JsonCache(self.temporary_directory.name),
            api=self.fake_api,  # type: ignore[arg-type]
        )

    def test_client_starts_online_by_default(self) -> None:
        """Avant toute tentative réseau, l'état ne doit jamais présumer une panne."""
        self.assertFalse(self.client.is_offline)
        self.assertEqual(self.client.offline_notice, "")

    def test_connectivity_failure_with_no_cache_marks_offline_and_raises(self) -> None:
        """Sans donnée locale disponible, la panne doit rester visible, pas masquée silencieusement."""
        self.fake_api.next_info_error = ConnectionError("DNS indisponible")

        with self.assertRaises(Exception):
            self.client.get_model_info("acme/jamais-vu")

        self.assertTrue(self.client.is_offline)
        self.assertIn("Mode hors connexion", self.client.offline_notice)

    def test_stale_model_info_is_served_when_offline(self) -> None:
        """Une fiche déjà consultée doit rester consultable hors connexion, même expirée."""
        self.client.get_model_info("acme/modele")
        self.fake_api.next_info_error = ConnectionError("Coupure réseau")

        details = self.client.get_model_info("acme/modele", force_refresh=True)

        self.assertEqual(details.summary.repo_id, "acme/modele")
        self.assertTrue(self.client.is_offline)

    def test_naturally_expired_model_info_still_serves_as_fallback_when_offline(self) -> None:
        """Une entrée expirée par le TTL normal (pas force_refresh) ne doit pas être perdue avant
        que le secours hors connexion ait pu s'en servir : get() la supprimerait sinon lui-même."""
        self.client.get_model_info("acme/modele")
        cache_key = self.client._model_info_cache_key("acme/modele")
        path = self.client._cache._path_for("model", cache_key)
        entry = json.loads(path.read_text(encoding="utf-8"))
        entry["expires_at"] = entry["created_at"] - 1
        path.write_text(json.dumps(entry), encoding="utf-8")
        self.fake_api.next_info_error = ConnectionError("Coupure réseau")

        details = self.client.get_model_info("acme/modele")

        self.assertEqual(details.summary.repo_id, "acme/modele")
        self.assertTrue(self.client.is_offline)

    def test_stale_search_results_are_served_when_offline(self) -> None:
        """Une recherche déjà faite doit rester disponible hors connexion (« dernières recherches »)."""
        filters = SearchFilters(query="modele", limit=20)
        self.client.search_models(filters)
        self.fake_api.next_search_error = ConnectionError("Coupure réseau")

        # Une entrée fraîche est déjà servie par le cache normal ; on doit d'abord la faire
        # expirer pour vérifier le secours hors connexion plutôt que le chemin heureux.
        cache = JsonCache(self.temporary_directory.name)
        cache_key = self.client._cache_key({
            "query": "modele", "pipeline_tag": None, "language": None, "license": None,
            "min_parameters": None, "max_parameters": None, "sort": "downloads", "limit": 20,
        })
        entry_path = cache._path_for("search", cache_key)
        entry = json.loads(entry_path.read_text(encoding="utf-8"))
        entry["expires_at"] = entry["created_at"] - 1
        entry_path.write_text(json.dumps(entry), encoding="utf-8")

        results = self.client.search_models(filters)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].repo_id, "acme/modele")
        self.assertTrue(self.client.is_offline)

    def test_hub_level_rejection_does_not_mark_offline(self) -> None:
        """Un 404/403 prouve que le Hub répond : ce n'est pas une panne de connectivité."""
        import httpx
        from huggingface_hub.errors import RepositoryNotFoundError

        fake_response = httpx.Response(404, request=httpx.Request("GET", "https://huggingface.co"))
        self.fake_api.next_info_error = RepositoryNotFoundError("introuvable", response=fake_response)

        with self.assertRaises(Exception):
            self.client.get_model_info("acme/absent")

        self.assertFalse(self.client.is_offline)

    def test_successful_call_after_failure_clears_offline_state(self) -> None:
        """La connectivité doit se rétablir dès qu'un appel réseau réussit à nouveau."""
        self.fake_api.next_info_error = ConnectionError("Coupure réseau")
        with self.assertRaises(Exception):
            self.client.get_model_info("acme/jamais-vu")
        self.assertTrue(self.client.is_offline)

        self.client.get_model_info("acme/modele")

        self.assertFalse(self.client.is_offline)


if __name__ == "__main__":
    unittest.main()
