"""Tests du rapprochement heuristique de modèles similaires."""

from __future__ import annotations

import unittest

from src.api_client import ModelSummary
from src.model_analysis import TechnicalProfile
from src.similar_models import find_similar_models


def make_summary(
    repo_id: str,
    *,
    parameters: int | None,
    pipeline_tag: str | None = "text-generation",
    tags: tuple[str, ...] = (),
    downloads: int = 0,
) -> ModelSummary:
    """Construire un résumé minimal pour tester le rapprochement."""
    return ModelSummary(
        repo_id=repo_id, author=repo_id.split("/", maxsplit=1)[0], likes=0, downloads=downloads,
        pipeline_tag=pipeline_tag, library_name="transformers", tags=tags, created_at=None,
        last_modified=None, parameters=parameters, private=False, gated=False,
    )


def make_profile(parameters: int | None, family: str = "Qwen 2") -> TechnicalProfile:
    """Construire un profil technique minimal centré sur la famille et les paramètres."""
    return TechnicalProfile(
        model_classes=("Qwen2ForCausalLM",), family=family, parameters=parameters, dtype="bfloat16",
        context_length=32_768, vocabulary_size=151_936, quantization="Non détectée",
    )


class SimilarModelsTests(unittest.TestCase):
    """Vérifier le classement, la diversité de familles et les critères mis en avant."""

    def test_worked_example_mixes_same_and_other_families(self) -> None:
        """Qwen2.5-7B doit renvoyer des variantes Qwen et des alternatives d'autres familles."""
        source = make_summary("Qwen/Qwen2.5-7B-Instruct", parameters=7_000_000_000, tags=("qwen2", "en"))
        profile = make_profile(7_000_000_000)
        candidates = [
            make_summary("Qwen/Qwen2.5-3B-Instruct", parameters=3_000_000_000, tags=("qwen2", "en"), downloads=900_000),
            make_summary("Qwen/Qwen2.5-14B-Instruct", parameters=14_000_000_000, tags=("qwen2", "en"), downloads=800_000),
            make_summary("Qwen/Qwen2.5-32B-Instruct", parameters=32_000_000_000, tags=("qwen2", "en"), downloads=700_000),
            make_summary("mistralai/Mistral-7B-Instruct-v0.3", parameters=7_200_000_000, tags=("mistral", "en"), downloads=2_000_000),
            make_summary("meta-llama/Llama-3.1-8B-Instruct", parameters=8_000_000_000, tags=("llama", "en"), downloads=3_000_000),
            make_summary("google/gemma-7b-it", parameters=7_000_000_000, tags=("gemma", "en"), downloads=500_000),
        ]

        results = find_similar_models(source, profile, {}, candidates, limit=5, same_family_cap=2)
        repo_ids = [item.summary.repo_id for item in results]

        self.assertEqual(len(results), 5)
        qwen_count = sum(1 for repo_id in repo_ids if "qwen" in repo_id.casefold())
        self.assertLessEqual(qwen_count, 2)
        self.assertIn("mistralai/Mistral-7B-Instruct-v0.3", repo_ids)
        self.assertIn("meta-llama/Llama-3.1-8B-Instruct", repo_ids)

    def test_source_model_is_excluded_from_its_own_results(self) -> None:
        """Le modèle examiné ne doit jamais se recommander lui-même."""
        source = make_summary("acme/model-7b", parameters=7_000_000_000)
        profile = make_profile(7_000_000_000, family="Llama")
        candidates = [source, make_summary("acme/model-7b-v2", parameters=7_000_000_000, downloads=10)]

        results = find_similar_models(source, profile, {}, candidates)

        self.assertNotIn("acme/model-7b", [item.summary.repo_id for item in results])

    def test_own_quantized_siblings_are_excluded(self) -> None:
        """Les quantifications du modèle source ne doivent pas doublonner la fiche « versions existantes »."""
        source = make_summary("Qwen/Qwen2.5-7B-Instruct", parameters=7_000_000_000, tags=("qwen2",))
        profile = make_profile(7_000_000_000)
        own_gguf = make_summary(
            "bartowski/Qwen2.5-7B-Instruct-GGUF", parameters=None, tags=("gguf",), downloads=999_999
        )
        genuine_alternative = make_summary(
            "mistralai/Mistral-7B-Instruct-v0.3", parameters=7_200_000_000, tags=("mistral",), downloads=100
        )

        results = find_similar_models(source, profile, {}, [own_gguf, genuine_alternative])
        repo_ids = [item.summary.repo_id for item in results]

        self.assertNotIn("bartowski/Qwen2.5-7B-Instruct-GGUF", repo_ids)
        self.assertIn("mistralai/Mistral-7B-Instruct-v0.3", repo_ids)

    def test_wildly_different_size_scores_lower_than_close_size(self) -> None:
        """Un modèle 100 fois plus gros ne doit pas primer sur un modèle de taille comparable."""
        source = make_summary("acme/model-7b", parameters=7_000_000_000)
        profile = make_profile(7_000_000_000, family="Non renseignée")  # pas de famille détectable
        close = make_summary("other/close-8b", parameters=8_000_000_000, downloads=1)
        huge = make_summary("other/huge-700b", parameters=700_000_000_000, downloads=1_000_000)

        results = find_similar_models(source, profile, {}, [close, huge], limit=2)
        by_id = {item.summary.repo_id: item for item in results}

        self.assertGreater(by_id["other/close-8b"].score, by_id["other/huge-700b"].score)

    def test_no_pipeline_tag_or_family_still_scores_on_shared_signals(self) -> None:
        """Sans famille détectée, la taille et la licence doivent suffire à produire un résultat."""
        source = make_summary(
            "acme/mystery-7b", parameters=7_000_000_000, pipeline_tag="text-generation", tags=("license:apache-2.0",)
        )
        profile = make_profile(7_000_000_000, family="Non renseignée")
        candidate = make_summary(
            "other/similar-7b", parameters=7_000_000_000, pipeline_tag="text-generation",
            tags=("license:apache-2.0",), downloads=5,
        )

        results = find_similar_models(source, profile, {}, [candidate])

        self.assertEqual(len(results), 1)
        self.assertIn("Licence identique", results[0].reasons)


if __name__ == "__main__":
    unittest.main()
