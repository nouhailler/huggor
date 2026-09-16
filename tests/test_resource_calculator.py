"""Tests du calculateur de ressources : précisions jouables, vitesse et contexte estimés."""

from __future__ import annotations

import unittest

from src.resource_calculator import HardwareProfile, calculate_resources


class ResourceCalculatorTests(unittest.TestCase):
    """Vérifier la matrice de précisions et l'estimation détaillée."""

    def test_fourteen_billion_model_matches_the_worked_example(self) -> None:
        """16 Go RAM / 8 Go VRAM sur un modèle 14B doit reproduire la grille de référence."""
        hardware = HardwareProfile(ram_gib=16, vram_gib=8, gpu_name="RTX 5060 Ti", cpu_name="Ryzen 5")

        calculation = calculate_resources(14_000_000_000, hardware)
        statuses = {item.label: item.status for item in calculation.precisions}

        self.assertEqual(statuses["FP32"], "no")
        self.assertEqual(statuses["FP16"], "no")
        self.assertEqual(statuses["INT8"], "warning")
        self.assertEqual(statuses["Q8"], "warning")
        self.assertEqual(statuses["Q6"], "ok")
        self.assertEqual(statuses["Q4_K_M"], "ok")

        # La meilleure précision encore jouable doit être la plus fidèle parmi celles en "ok".
        self.assertEqual(calculation.estimate.precision_label, "Q6")
        self.assertEqual(calculation.estimate.execution_path, "cpu")

    def test_unknown_parameters_produce_no_precision_rows(self) -> None:
        """Un modèle sans nombre de paramètres ne doit produire aucune fausse certitude."""
        calculation = calculate_resources(None, HardwareProfile(ram_gib=16, vram_gib=0))

        self.assertEqual(calculation.precisions, ())
        self.assertIsNone(calculation.estimate.precision_label)
        self.assertIn("inconnu", calculation.estimate.speed_label)

    def test_tiny_machine_cannot_run_a_huge_model(self) -> None:
        """Un modèle 70B sur 8 Go RAM sans GPU doit être signalé comme impraticable."""
        calculation = calculate_resources(70_000_000_000, HardwareProfile(ram_gib=8, vram_gib=0))

        self.assertTrue(all(item.status == "no" for item in calculation.precisions))
        self.assertIsNone(calculation.estimate.precision_label)
        self.assertEqual(calculation.estimate.execution_path, "none")
        self.assertIn("Impraticable", calculation.estimate.speed_label)

    def test_negative_memory_is_rejected(self) -> None:
        """Une machine avec une mémoire négative n'a pas de sens physique."""
        with self.assertRaises(ValueError):
            HardwareProfile(ram_gib=-1, vram_gib=0)

    def test_context_estimate_uses_model_architecture_when_available(self) -> None:
        """Le contexte réaliste doit exploiter les champs d'architecture standards."""
        config = {
            "num_hidden_layers": 32,
            "hidden_size": 4096,
            "num_attention_heads": 32,
            "num_key_value_heads": 8,
        }
        calculation = calculate_resources(
            7_000_000_000,
            HardwareProfile(ram_gib=32, vram_gib=24),
            config=config,
            context_length=32_768,
        )

        self.assertIsNotNone(calculation.estimate.max_context_tokens)
        self.assertGreater(calculation.estimate.max_context_tokens, 0)
        self.assertLessEqual(calculation.estimate.max_context_tokens, 32_768)

    def test_context_estimate_is_none_for_non_standard_architecture(self) -> None:
        """Sans les champs d'architecture usuels, aucun chiffre inventé ne doit être renvoyé."""
        calculation = calculate_resources(
            7_000_000_000,
            HardwareProfile(ram_gib=32, vram_gib=24),
            config={},
            context_length=None,
        )

        self.assertIsNone(calculation.estimate.max_context_tokens)
        self.assertIn("non standard", calculation.estimate.context_note)

    def test_larger_model_never_reports_a_faster_estimated_speed(self) -> None:
        """Un modèle plus gros à précision équivalente ne doit jamais sembler plus rapide."""
        hardware = HardwareProfile(ram_gib=64, vram_gib=24)
        small = calculate_resources(7_000_000_000, hardware)
        big = calculate_resources(30_000_000_000, hardware)

        self.assertGreaterEqual(
            small.estimate.speed_tokens_per_second_low,
            big.estimate.speed_tokens_per_second_low,
        )


if __name__ == "__main__":
    unittest.main()
