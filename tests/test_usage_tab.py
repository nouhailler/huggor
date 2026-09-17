"""Tests de l'onglet « Mon usage » : recherche par objectif filtrée par compatibilité matérielle."""

from __future__ import annotations

import unittest

from src.api_client import ModelSummary, SearchFilters
from src.resource_calculator import HardwareProfile
from src.ui.usage_tab import (
    _score_by_hardware_fit,
    format_usage_card,
    search_by_usage_for_ui,
)


def make_summary(
    repo_id: str,
    *,
    parameters: int | None,
    pipeline_tag: str = "text-generation",
    downloads: int = 0,
) -> ModelSummary:
    """Construire un résumé minimal pour les tests de compatibilité matérielle."""
    return ModelSummary(
        repo_id=repo_id, author=repo_id.split("/", maxsplit=1)[0], likes=0, downloads=downloads,
        pipeline_tag=pipeline_tag, library_name="transformers", tags=(), created_at=None,
        last_modified=None, parameters=parameters, private=False, gated=False,
    )


class FakeUsageClient:
    """Double renvoyant des résultats distincts selon la tâche et le mot-clé demandés."""

    def __init__(self, responses: dict[tuple[str, str], list[ModelSummary]]) -> None:
        """Indexer les réponses par (pipeline_tag, mot-clé) et enregistrer les appels."""
        self.responses = responses
        self.calls: list[SearchFilters] = []

    def search_models(self, filters: SearchFilters) -> list[ModelSummary]:
        """Renvoyer la réponse préparée pour ce couple tâche/mot-clé, et journaliser l'appel."""
        self.calls.append(filters)
        return self.responses.get((filters.pipeline_tag or "", filters.query), [])


class NoopProgress:
    """Remplacement appelable de ``gr.Progress`` pour les tests."""

    def __call__(self, *_args: object, **_kwargs: object) -> None:
        """Ignorer les mises à jour de progression."""


class HardwareFitScoringTests(unittest.TestCase):
    """Vérifier que seuls les modèles jouables ou non évaluables restent affichés."""

    def test_incompatible_known_model_is_dropped(self) -> None:
        """Un modèle trop gros et connu ne doit pas polluer les résultats."""
        hardware = HardwareProfile(ram_gib=8, vram_gib=0)
        tiny = make_summary("acme/tiny", parameters=1_000_000_000, downloads=10)
        huge = make_summary("acme/huge", parameters=500_000_000_000, downloads=1_000_000)

        results = _score_by_hardware_fit([tiny, huge], hardware)
        repo_ids = [item["repo_id"] for item in results]

        self.assertIn("acme/tiny", repo_ids)
        self.assertNotIn("acme/huge", repo_ids)

    def test_unknown_parameters_are_kept_but_marked_unevaluated(self) -> None:
        """Un modèle sans paramètres déclarés doit rester visible, jamais rejeté silencieusement."""
        hardware = HardwareProfile(ram_gib=16, vram_gib=0)
        unknown = make_summary("acme/unknown", parameters=None)

        results = _score_by_hardware_fit([unknown], hardware)

        self.assertEqual(len(results), 1)
        self.assertIn("non évaluable", results[0]["hardware_label"])

    def test_compatible_models_are_ranked_above_unevaluated_ones(self) -> None:
        """Un modèle dont la compatibilité est confirmée doit passer avant l'inconnu."""
        hardware = HardwareProfile(ram_gib=16, vram_gib=0)
        unknown = make_summary("acme/unknown", parameters=None, downloads=1_000_000)
        compatible = make_summary("acme/compatible", parameters=1_000_000_000, downloads=1)

        results = _score_by_hardware_fit([unknown, compatible], hardware)

        self.assertEqual(results[0]["repo_id"], "acme/compatible")


class SearchByUsageTests(unittest.TestCase):
    """Vérifier le regroupement par usage et les garde-fous du formulaire."""

    def test_requires_at_least_one_use_case(self) -> None:
        """Sans usage coché, la recherche ne doit interroger aucun client."""
        client = FakeUsageClient({})

        sections, status = search_by_usage_for_ui(
            client, [], 16, 0, "", progress=NoopProgress()  # type: ignore[arg-type]
        )

        self.assertEqual(sections, [])
        self.assertIn("Cochez au moins un usage", status)
        self.assertEqual(client.calls, [])

    def test_requires_some_memory(self) -> None:
        """RAM et VRAM à zéro doivent être rejetées avant toute recherche réseau."""
        client = FakeUsageClient({})

        sections, status = search_by_usage_for_ui(
            client, ["chatbot"], 0, 0, "", progress=NoopProgress()  # type: ignore[arg-type]
        )

        self.assertEqual(sections, [])
        self.assertIn("RAM ou de VRAM", status)
        self.assertEqual(client.calls, [])

    def test_groups_results_by_selected_use_case(self) -> None:
        """Chaque usage coché doit produire sa propre section de résultats."""
        client = FakeUsageClient(
            {
                ("text-generation", "chat"): [make_summary("acme/chat-model", parameters=1_000_000_000)],
                ("translation", ""): [make_summary("acme/translate-model", parameters=1_000_000_000, pipeline_tag="translation")],
            }
        )

        sections, status = search_by_usage_for_ui(
            client, ["chatbot", "translation"], 16, 0, "", progress=NoopProgress()  # type: ignore[arg-type]
        )

        self.assertEqual(len(sections), 2)
        self.assertEqual(sections[0]["key"], "chatbot")
        self.assertEqual(sections[1]["key"], "translation")
        self.assertEqual(sections[0]["items"][0]["repo_id"], "acme/chat-model")
        self.assertIn("2 modèles compatibles", status)

    def test_shared_task_across_use_cases_is_only_searched_once(self) -> None:
        """Deux usages qui recouvrent la même tâche ne doivent pas doubler l'appel réseau."""
        client = FakeUsageClient(
            {("sentence-similarity", ""): [make_summary("acme/embed", parameters=100_000_000)]}
        )

        # RAG et Embeddings interrogent tous deux sentence-similarity/feature-extraction :
        # au plus une requête par couple (tâche, mot-clé) distinct doit être émise.
        search_by_usage_for_ui(
            client, ["rag", "embeddings"], 16, 0, "", progress=NoopProgress()  # type: ignore[arg-type]
        )
        distinct_pairs = {(call.pipeline_tag, call.query) for call in client.calls}
        self.assertEqual(len(client.calls), len(distinct_pairs))


class UsageCardFormattingTests(unittest.TestCase):
    """Vérifier que la carte affiche le verdict matériel sans jamais planter sur des champs absents."""

    def test_card_contains_hardware_label_and_hub_link(self) -> None:
        """Le verdict matériel calculé doit apparaître tel quel dans la carte."""
        card = format_usage_card(
            {
                "repo_id": "acme/model", "pipeline_tag": "text-generation", "likes": 10, "downloads": 100,
                "parameters": 7_000_000_000, "hardware_label": "✅ Compatible en Q4_K_M — 🟢 Fluide",
            }
        )

        self.assertIn("https://huggingface.co/acme/model", card)
        self.assertIn("Compatible en Q4", card)
        self.assertIn("Fluide", card)

    def test_card_handles_missing_fields_gracefully(self) -> None:
        """Une carte sans champ optionnel ne doit jamais lever d'exception."""
        card = format_usage_card({"repo_id": "acme/model"})

        self.assertIn("acme/model", card)
        self.assertIn("—", card)


if __name__ == "__main__":
    unittest.main()
