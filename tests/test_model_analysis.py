"""Tests de l'analyse technique et des recommandations de téléchargement."""

from __future__ import annotations

import shlex
import unittest
from dataclasses import replace

from src.api_client import ModelDetails, ModelFile, ModelSummary
from src.model_analysis import (
    classify_file,
    extract_technical_profile,
    inspect_compatibility,
    recommend_download,
)


def make_details(
    files: tuple[ModelFile, ...],
    *,
    repo_id: str = "acme/model",
    pipeline_tag: str | None = "text-generation",
    library_name: str | None = "transformers",
    tags: tuple[str, ...] = (),
    card_data: dict[str, object] | None = None,
    config: dict[str, object] | None = None,
) -> ModelDetails:
    """Construire une fiche ciblée pour un format donné."""
    return ModelDetails(
        summary=ModelSummary(
            repo_id=repo_id,
            author="acme",
            likes=0,
            downloads=0,
            pipeline_tag=pipeline_tag,
            library_name=library_name,
            tags=tags,
            created_at=None,
            last_modified=None,
            parameters=7_000_000_000,
            private=False,
            gated=False,
        ),
        files=files,
        card_data=card_data or {},
        config=config
        or {
            "architectures": ["LlamaForCausalLM"],
            "model_type": "llama",
        },
        used_storage=sum(item.size or 0 for item in files),
    )


class TechnicalProfileTests(unittest.TestCase):
    """Vérifier l'extraction depuis les configurations composites."""

    def test_nested_text_config_is_normalised(self) -> None:
        """Les architectures multimodales placent souvent ces champs dans text_config."""
        details = make_details(
            (),
            config={
                "text_config": {
                    "architectures": ["Qwen2ForCausalLM"],
                    "model_type": "qwen2",
                    "torch_dtype": "torch.bfloat16",
                    "max_position_embeddings": 131_072,
                    "vocab_size": 151_936,
                    "quantization_config": {"quant_method": "awq", "bits": 4},
                }
            },
        )

        profile = extract_technical_profile(details)

        self.assertEqual(profile.family, "Qwen 2")
        self.assertEqual(profile.dtype, "bfloat16")
        self.assertEqual(profile.context_length, 131_072)
        self.assertEqual(profile.vocabulary_size, 151_936)
        self.assertEqual(profile.quantization, "AWQ · 4 bits")

    def test_tensor_metadata_is_a_dtype_fallback(self) -> None:
        """Les anciennes configs sans dtype peuvent s'appuyer sur les Safetensors."""
        details = replace(make_details(()), tensor_dtypes=("F32",))

        profile = extract_technical_profile(details)

        self.assertEqual(profile.dtype, "float32 (Safetensors)")


class DownloadRecommendationTests(unittest.TestCase):
    """Vérifier la sélection concrète des artefacts à récupérer."""

    def test_safetensors_requires_weight_config_and_tokenizer(self) -> None:
        """Un poids Transformers unique ne doit pas être présenté comme autonome."""
        details = make_details(
            (
                ModelFile("README.md", 200, None),
                ModelFile("config.json", 100, None),
                ModelFile("tokenizer.json", 300, None),
                ModelFile("model.safetensors", 1_000, None),
            )
        )

        recommendation = recommend_download(details)

        self.assertEqual(recommendation.strategy, "snapshot")
        self.assertEqual(recommendation.primary_files, ("model.safetensors",))
        self.assertIn("config.json", recommendation.companion_files)
        self.assertIn("tokenizer.json", recommendation.companion_files)
        self.assertNotIn("README.md", recommendation.companion_files)
        arguments = shlex.split(recommendation.command)
        self.assertEqual(
            arguments[3:-2],
            ["model.safetensors", "config.json", "tokenizer.json"],
        )

    def test_all_safetensor_shards_and_index_are_required(self) -> None:
        """Aucun shard ne doit être conseillé isolément."""
        details = make_details(
            (
                ModelFile("config.json", 100, None),
                ModelFile("model-00001-of-00002.safetensors", 1_000, None),
                ModelFile("model-00002-of-00002.safetensors", 1_100, None),
                ModelFile("model.safetensors.index.json", 200, None),
            )
        )

        recommendation = recommend_download(details)

        self.assertEqual(len(recommendation.primary_files), 2)
        self.assertIn("model.safetensors.index.json", recommendation.companion_files)
        self.assertIn("shard isolé", recommendation.warning or "")

    def test_gguf_prefers_balanced_single_file(self) -> None:
        """Q4_K_M doit être la recommandation locale par défaut quand elle existe."""
        details = make_details(
            (
                ModelFile("model-Q8_0.gguf", 8_000, None),
                ModelFile("model-Q4_K_M.gguf", 4_500, None),
            ),
            library_name=None,
            repo_id="acme/model-gguf",
        )

        recommendation = recommend_download(details)

        self.assertEqual(recommendation.strategy, "single_file")
        self.assertEqual(recommendation.primary_files, ("model-Q4_K_M.gguf",))
        self.assertIn("model-Q4_K_M.gguf", recommendation.command)

    def test_split_gguf_requires_all_parts_of_one_variant(self) -> None:
        """Une quantification GGUF découpée doit conserver toutes ses parties."""
        details = make_details(
            (
                ModelFile("model-Q4_K_M-00001-of-00002.gguf", 2_000, None),
                ModelFile("model-Q4_K_M-00002-of-00002.gguf", 2_100, None),
                ModelFile("model-Q8_0.gguf", 8_000, None),
            ),
            library_name=None,
        )

        recommendation = recommend_download(details)

        self.assertEqual(recommendation.strategy, "snapshot")
        self.assertEqual(len(recommendation.primary_files), 2)
        self.assertEqual(recommendation.estimated_bytes, 4_100)
        self.assertIn("toutes les parties", recommendation.warning or "")
        self.assertNotIn("model-Q8_0.gguf", recommendation.command)

    def test_canonical_safetensor_does_not_download_duplicate_variant(self) -> None:
        """La variante fp16 ne doit pas doubler le téléchargement du poids canonique."""
        details = make_details(
            (
                ModelFile("model.safetensors", 1_000, None),
                ModelFile("model.fp16.safetensors", 500, None),
                ModelFile("config.json", 100, None),
            )
        )

        recommendation = recommend_download(details)

        self.assertEqual(recommendation.primary_files, ("model.safetensors",))
        self.assertNotIn("model.fp16.safetensors", recommendation.command)

    def test_unknown_file_size_does_not_produce_an_incomplete_total(self) -> None:
        """Une taille inconnue doit empêcher un volume sélectionné trompeur."""
        details = make_details(
            (
                ModelFile("model.safetensors", 1_000, None),
                ModelFile("config.json", None, None),
            )
        )

        self.assertIsNone(recommend_download(details).estimated_bytes)

    def test_coreml_binary_is_not_mislabelled_as_pytorch(self) -> None:
        """L'extension .bin ne suffit pas à qualifier un artefact CoreML."""
        model_file = ModelFile("coreml/model.mlpackage/weights/weight.bin", 1_000, None)
        details = make_details((model_file,))
        recommendation = recommend_download(details)

        role, file_format, _selected = classify_file(model_file, recommendation)

        self.assertEqual(role, "Artefact CoreML")
        self.assertEqual(file_format, "CoreML")
        self.assertEqual(recommendation.strategy, "metadata_only")

    def test_adapter_mentions_separate_base_model(self) -> None:
        """Un adapter PEFT ne doit jamais être présenté comme un modèle complet."""
        details = make_details(
            (
                ModelFile("adapter_config.json", 100, None),
                ModelFile("adapter_model.safetensors", 500, None),
            ),
            card_data={"base_model": "acme/base"},
        )

        recommendation = recommend_download(details)

        self.assertEqual(recommendation.strategy, "adapter")
        self.assertIn("acme/base", recommendation.explanation)
        self.assertIn("séparément", recommendation.warning or "")


class CompatibilityTests(unittest.TestCase):
    """Vérifier les niveaux de confiance affichés pour les moteurs."""

    def test_gguf_declares_direct_and_probable_runtimes(self) -> None:
        """GGUF implique llama.cpp et rend l'import Ollama probable."""
        details = make_details(
            (ModelFile("model-Q4_K_M.gguf", 4_500, None),),
            library_name=None,
        )

        findings = {item.name: item for item in inspect_compatibility(details)}

        self.assertEqual(findings["GGUF"].state, "detected")
        self.assertEqual(findings["llama.cpp"].state, "detected")
        self.assertEqual(findings["Ollama"].state, "probable")

    def test_causal_transformers_runtimes_are_probable(self) -> None:
        """vLLM et TGI nécessitent une validation runtime malgré un format standard."""
        details = make_details((ModelFile("model.safetensors", 1_000, None),))

        findings = {item.name: item for item in inspect_compatibility(details)}

        self.assertEqual(findings["Transformers"].state, "detected")
        self.assertEqual(findings["Safetensors"].state, "detected")
        self.assertEqual(findings["vLLM"].state, "probable")
        self.assertEqual(findings["TGI"].state, "probable")


if __name__ == "__main__":
    unittest.main()
