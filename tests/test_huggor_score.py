"""Tests du Huggor Score : chaque composante doit rester explicable, jamais devinée."""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from src.api_client import ModelDetails, ModelFile, ModelSummary
from src.hardware_advisor import advise_hardware
from src.huggor_score import MAX_TOTAL, compute_huggor_score
from src.model_analysis import extract_technical_profile, inspect_compatibility


def make_details(
    *,
    downloads: int = 0,
    likes: int = 0,
    last_modified: str | None = None,
    created_at: str | None = None,
    parameters: int | None = None,
    files: tuple[ModelFile, ...] = (),
    card_data: dict | None = None,
    config: dict | None = None,
    tags: tuple[str, ...] = (),
) -> ModelDetails:
    """Construire une fiche synthétique couvrant les champs utilisés par le score."""
    return ModelDetails(
        summary=ModelSummary(
            repo_id="acme/modele", author="acme", likes=likes, downloads=downloads,
            pipeline_tag="text-generation", library_name="transformers", tags=tags,
            created_at=created_at, last_modified=last_modified, parameters=parameters,
            private=False, gated=False,
        ),
        files=files, card_data=card_data or {}, config=config or {}, used_storage=0,
    )


def _iso_days_ago(days: int) -> str:
    """Produire une date ISO 8601 UTC vieille de N jours, pour des scénarios reproductibles."""
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


class HuggorScoreTests(unittest.TestCase):
    """Vérifier le calcul, la transparence et les bornes du score composite."""

    def test_component_max_points_always_sum_to_max_total(self) -> None:
        """La somme des points maximaux doit toujours valoir 100, quel que soit le scénario."""
        details = make_details()
        profile = extract_technical_profile(details)
        compatibility = inspect_compatibility(details)
        hardware = advise_hardware(profile, compatibility)

        score = compute_huggor_score(details, profile, compatibility, hardware, "")

        self.assertEqual(sum(item.max_points for item in score.components), MAX_TOTAL)
        self.assertEqual(score.max_total, MAX_TOTAL)

    def test_favorable_signals_score_highly_with_full_breakdown(self) -> None:
        """Un dépôt populaire, récent, documenté et compatible doit obtenir un score élevé."""
        details = make_details(
            downloads=2_000_000, likes=5_000,
            last_modified=_iso_days_ago(5), created_at=_iso_days_ago(900),
            parameters=3_000_000_000,
            files=(ModelFile("model.safetensors", 1_000, None), ModelFile("model-Q4_K_M.gguf", 900, None)),
            card_data={"license": "apache-2.0"},
            config={"architectures": ["LlamaForCausalLM"], "model_type": "llama"},
        )
        profile = extract_technical_profile(details)
        compatibility = inspect_compatibility(details)
        hardware = advise_hardware(profile, compatibility)
        long_card = "# Modèle\n\nDescription détaillée.\n\n```python\nprint('usage')\n```\n" * 20

        score = compute_huggor_score(details, profile, compatibility, hardware, long_card)

        self.assertGreaterEqual(score.total, 90)
        by_name = {item.name: item for item in score.components}
        self.assertEqual(by_name["Popularité"].points, 15)
        self.assertEqual(by_name["Licence"].points, 10)
        self.assertEqual(by_name["Safetensors"].points, 10)
        self.assertEqual(by_name["Quantification disponible"].points, 10)
        self.assertEqual(by_name["Compatibilité locale"].points, 15)
        self.assertEqual(by_name["Taille"].points, 5)

    def test_unknown_everything_scores_zero_without_crashing(self) -> None:
        """Un dépôt sans aucune métadonnée ne doit ni planter ni inventer un score positif."""
        details = make_details()
        profile = extract_technical_profile(details)
        compatibility = inspect_compatibility(details)
        hardware = advise_hardware(profile, compatibility)

        score = compute_huggor_score(details, profile, compatibility, hardware, "")

        self.assertEqual(score.total, 0)
        for component in score.components:
            self.assertEqual(component.points, 0)

    def test_documentation_rewards_length_and_code_examples_only(self) -> None:
        """La composante documentation mesure une quantité, pas une qualité rédactionnelle jugée."""
        details = make_details()
        profile = extract_technical_profile(details)
        compatibility = inspect_compatibility(details)
        hardware = advise_hardware(profile, compatibility)

        empty = compute_huggor_score(details, profile, compatibility, hardware, "")
        short = compute_huggor_score(details, profile, compatibility, hardware, "Un mini résumé.")
        long_with_code = compute_huggor_score(
            details, profile, compatibility, hardware, "Texte. " * 400 + "```py\nprint(1)\n```"
        )

        doc_points = lambda result: next(c.points for c in result.components if c.name == "Documentation")
        self.assertEqual(doc_points(empty), 0)
        self.assertLess(doc_points(short), doc_points(long_with_code))
        self.assertEqual(doc_points(long_with_code), 10)

    def test_license_component_distinguishes_permissive_declared_and_missing(self) -> None:
        """Une licence permissive, une licence custom et l'absence de licence doivent se distinguer."""
        profile_hardware = lambda details: (
            extract_technical_profile(details),
            inspect_compatibility(details),
        )

        permissive = make_details(card_data={"license": "apache-2.0"})
        declared = make_details(card_data={"license": "some-custom-license"})
        missing = make_details()

        results = {}
        for label, details in (("permissive", permissive), ("declared", declared), ("missing", missing)):
            profile, compatibility = profile_hardware(details)
            hardware = advise_hardware(profile, compatibility)
            score = compute_huggor_score(details, profile, compatibility, hardware, "")
            results[label] = next(c.points for c in score.components if c.name == "Licence")

        self.assertEqual(results["permissive"], 10)
        self.assertEqual(results["declared"], 6)
        self.assertEqual(results["missing"], 0)

    def test_very_new_repository_cannot_score_maturity_points(self) -> None:
        """Un dépôt créé il y a une semaine ne peut pas déjà avoir prouvé sa maturité."""
        details = make_details(downloads=5_000_000, likes=50_000, created_at=_iso_days_ago(7))
        profile = extract_technical_profile(details)
        compatibility = inspect_compatibility(details)
        hardware = advise_hardware(profile, compatibility)

        score = compute_huggor_score(details, profile, compatibility, hardware, "")

        maturity = next(c for c in score.components if c.name == "Maturité")
        self.assertEqual(maturity.points, 0)
        self.assertIn("trop récent", maturity.reason)

    def test_quantization_gives_partial_credit_for_variants_found_elsewhere(self) -> None:
        """Une variante quantifiée trouvée ailleurs vaut moins qu'une disponible dans ce dépôt."""
        details = make_details(files=(ModelFile("model.safetensors", 1_000, None),))
        profile = extract_technical_profile(details)
        compatibility = inspect_compatibility(details)
        hardware = advise_hardware(profile, compatibility)

        without_variants = compute_huggor_score(details, profile, compatibility, hardware, "")
        with_variants = compute_huggor_score(
            details, profile, compatibility, hardware, "", has_known_quantized_variants=True
        )

        quant_points = lambda result: next(c.points for c in result.components if c.name == "Quantification disponible")
        self.assertEqual(quant_points(without_variants), 0)
        self.assertEqual(quant_points(with_variants), 7)


if __name__ == "__main__":
    unittest.main()
