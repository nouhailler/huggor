"""Tests de la recherche heuristique de variantes quantifiées d'un modèle."""

from __future__ import annotations

import unittest

from src.api_client import ModelSummary
from src.quantization_search import extract_base_name, find_quantized_variants


def make_summary(repo_id: str, *, tags: tuple[str, ...] = (), downloads: int = 0) -> ModelSummary:
    """Construire un résumé minimal pour tester la classification des candidats."""
    return ModelSummary(
        repo_id=repo_id, author=repo_id.split("/", maxsplit=1)[0], likes=0, downloads=downloads,
        pipeline_tag=None, library_name=None, tags=tags, created_at=None, last_modified=None,
        parameters=None, private=False, gated=False,
    )


class QuantizationSearchTests(unittest.TestCase):
    """Vérifier le filtrage des candidats et l'attribution des formats."""

    def test_extract_base_name_drops_the_author(self) -> None:
        """Le nom de recherche ne doit pas inclure l'auteur du dépôt source."""
        self.assertEqual(extract_base_name("Qwen/Qwen2.5-14B-Instruct"), "Qwen2.5-14B-Instruct")

    def test_finds_gguf_gptq_and_awq_siblings(self) -> None:
        """Chaque famille de quantification nommée dans le repo_id doit être reconnue."""
        source = "Qwen/Qwen2.5-14B-Instruct"
        candidates = [
            make_summary(source),  # Le dépôt source lui-même doit être exclu.
            make_summary("bartowski/Qwen2.5-14B-Instruct-GGUF", downloads=50_000),
            make_summary("TheBloke/Qwen2.5-14B-Instruct-GPTQ", downloads=10_000),
            make_summary("cognitivecomputations/Qwen2.5-14B-Instruct-AWQ", downloads=5_000),
            make_summary("acme/UnrelatedModel-GGUF", downloads=99_999),
        ]

        variants = find_quantized_variants(candidates, source)
        repo_ids = [item.summary.repo_id for item in variants]

        self.assertEqual(
            repo_ids,
            [
                "bartowski/Qwen2.5-14B-Instruct-GGUF",
                "TheBloke/Qwen2.5-14B-Instruct-GPTQ",
                "cognitivecomputations/Qwen2.5-14B-Instruct-AWQ",
            ],
        )
        self.assertNotIn("acme/UnrelatedModel-GGUF", repo_ids)
        self.assertEqual(variants[0].formats, ("GGUF",))

    def test_candidate_without_a_quantization_marker_is_ignored(self) -> None:
        """Un nom proche sans marqueur de format ne doit pas être présenté comme une variante."""
        source = "Qwen/Qwen2.5-14B-Instruct"
        candidates = [make_summary("acme/Qwen2.5-14B-Instruct-finetuned")]

        self.assertEqual(find_quantized_variants(candidates, source), ())

    def test_variants_are_sorted_by_downloads_descending(self) -> None:
        """Le plus téléchargé doit apparaître en premier."""
        source = "acme/Model-7B"
        candidates = [
            make_summary("a/Model-7B-GGUF", downloads=10),
            make_summary("b/Model-7B-AWQ", downloads=500),
        ]

        variants = find_quantized_variants(candidates, source)

        self.assertEqual(variants[0].summary.repo_id, "b/Model-7B-AWQ")
        self.assertEqual(variants[1].summary.repo_id, "a/Model-7B-GGUF")


if __name__ == "__main__":
    unittest.main()
