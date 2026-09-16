"""Tests du Model Advisor : estimation mémoire et verdict d'usage local."""

from __future__ import annotations

import unittest
from dataclasses import replace

from src.hardware_advisor import advise_hardware
from src.model_analysis import CompatibilityFinding, TechnicalProfile


def make_profile(parameters: int | None) -> TechnicalProfile:
    """Construire un profil technique minimal centré sur le nombre de paramètres."""
    return TechnicalProfile(
        model_classes=("LlamaForCausalLM",),
        family="Llama",
        parameters=parameters,
        dtype="bfloat16",
        context_length=8_192,
        vocabulary_size=32_000,
        quantization="Non détectée",
    )


class HardwareAdvisorTests(unittest.TestCase):
    """Vérifier les estimations mémoire et le verdict pour des tailles usuelles."""

    def test_unknown_parameters_yield_an_unknown_verdict(self) -> None:
        """Un dépôt sans nombre de paramètres ne doit pas produire de fausse certitude."""
        advice = advise_hardware(make_profile(None), ())

        self.assertIsNone(advice.parameters)
        self.assertEqual(advice.ram_estimates, ())
        self.assertEqual(advice.verdict_emoji, "⚪")
        self.assertTrue(all(item.status == "unknown" for item in advice.criteria[:4]))

    def test_seven_billion_model_is_a_good_16gb_candidate(self) -> None:
        """Un modèle 7B doit correspondre au repère communautaire de 16 Go RAM."""
        findings = (
            CompatibilityFinding("Ollama", "probable", "Import du fichier GGUF généralement possible."),
            CompatibilityFinding("GGUF", "not_detected", "Aucun poids GGUF détecté."),
        )
        advice = advise_hardware(make_profile(7_000_000_000), findings)

        self.assertEqual(advice.parameters, 7_000_000_000)
        self.assertEqual(advice.verdict_headline, "Bon candidat pour une machine avec 16 Go RAM")
        self.assertEqual(advice.verdict_emoji, "🟢")

        fp16 = next(item for item in advice.ram_estimates if item.label == "FP16 / BF16")
        self.assertAlmostEqual(fp16.low_bytes / 1024**3, 15.0, delta=0.5)

        q4 = next(item for item in advice.ram_estimates if item.label == "INT4 (Q4)")
        self.assertLess(q4.high_bytes, fp16.low_bytes)

        criteria = {item.name: item for item in advice.criteria}
        self.assertEqual(criteria["GPU 8 Go"].status, "ok")
        self.assertEqual(criteria["GPU 4 Go"].status, "warning")
        self.assertEqual(criteria["Ollama"].status, "warning")
        self.assertEqual(criteria["GGUF"].status, "no")

    def test_seventy_billion_model_requires_heavy_hardware(self) -> None:
        """Un modèle 70B ne doit jamais être présenté comme accessible en 16 Go."""
        advice = advise_hardware(make_profile(70_000_000_000), ())

        self.assertIn(advice.verdict_emoji, {"🟠", "🔴"})
        criteria = {item.name: item for item in advice.criteria}
        self.assertEqual(criteria["GPU 8 Go"].status, "no")
        self.assertEqual(criteria["CPU (16 Go RAM)"].status, "no")

    def test_larger_models_require_more_ram_or_equal(self) -> None:
        """L'estimation ne doit jamais réduire les besoins pour un modèle plus gros."""
        small = advise_hardware(make_profile(1_000_000_000), ())
        big = advise_hardware(replace(make_profile(1_000_000_000), parameters=13_000_000_000), ())

        small_fp16 = next(item for item in small.ram_estimates if item.label == "FP16 / BF16")
        big_fp16 = next(item for item in big.ram_estimates if item.label == "FP16 / BF16")
        self.assertLess(small_fp16.low_bytes, big_fp16.low_bytes)


if __name__ == "__main__":
    unittest.main()
