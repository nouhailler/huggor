"""Tests de la logique de présentation de l'onglet Détails."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.api_client import HuggingFaceClientError, ModelDetails, ModelFile, ModelSummary
from src.model_analysis import (
    detect_precision_formats,
    extract_technical_profile,
    inspect_compatibility,
    recommend_download,
)
from src.hardware_advisor import advise_hardware
from src.quantization_search import QuantizedVariant
from src.similar_models import SimilarModel
from src.ui.details_tab import (
    add_favorite_for_ui,
    build_file_inventory,
    build_raw_metadata,
    format_architecture_section,
    format_compatibility_section,
    format_download_recommendation,
    format_file_tree,
    format_hardware_advice,
    format_identity_section,
    format_precision_section,
    format_quantized_variants,
    format_similar_models,
    generate_code_snippets,
    load_details_for_ui,
)
from src.utils.favorites import FavoritesStore


def make_details(*, pipeline_tag: str = "text-classification") -> ModelDetails:
    """Créer une fiche synthétique réutilisable dans les tests."""
    return ModelDetails(
        summary=ModelSummary(
            repo_id="acme/modele",
            author="acme",
            likes=12,
            downloads=3_400,
            pipeline_tag=pipeline_tag,
            library_name="transformers",
            tags=("fr", "license:apache-2.0"),
            created_at="2025-01-01T00:00:00+00:00",
            last_modified="2025-02-01T00:00:00+00:00",
            parameters=1_500_000_000,
            private=False,
            gated=False,
        ),
        files=(
            ModelFile(path="config.json", size=1_024, blob_id="a"),
            ModelFile(path="README.md", size=768, blob_id="readme"),
            ModelFile(path="tokenizer.json", size=4_096, blob_id="tokenizer"),
            ModelFile(path="weights/model.safetensors", size=2_048, blob_id="b"),
            ModelFile(path="weights/index.json", size=512, blob_id="c"),
        ),
        card_data={"license": "apache-2.0", "language": ["fr", "en"]},
        config={
            "architectures": ["BertForSequenceClassification"],
            "model_type": "bert",
            "torch_dtype": "float16",
            "max_position_embeddings": 4_096,
            "vocab_size": 32_000,
        },
        used_storage=8_448,
    )


class FakeDetailsClient:
    """Double du client fournissant une fiche et une Model Card."""

    def __init__(self, error: Exception | None = None) -> None:
        """Préparer la réponse ou l'erreur du double."""
        self.error = error

    def get_model_info(self, _repo_id: str) -> ModelDetails:
        """Renvoyer les métadonnées synthétiques."""
        if self.error is not None:
            raise self.error
        return make_details()

    def get_model_card(self, _repo_id: str) -> str:
        """Renvoyer une Model Card synthétique."""
        return "# Carte complète"


class NoopProgress:
    """Remplacement appelable de ``gr.Progress`` pour les tests."""

    def __call__(self, *_args: object, **_kwargs: object) -> None:
        """Ignorer les mises à jour de progression."""


class DetailsFormattingTests(unittest.TestCase):
    """Vérifier les métadonnées, l'arborescence et les snippets."""

    def test_metadata_contains_technical_fields(self) -> None:
        """Le résumé et le JSON doivent exposer l'architecture et la licence."""
        details = make_details()
        profile = extract_technical_profile(details)
        findings = inspect_compatibility(details)
        recommendation = recommend_download(details)
        hardware = advise_hardware(profile, findings)
        precision_findings = detect_precision_formats(details, profile, findings)

        identity = format_identity_section(details)
        architecture = format_architecture_section(profile)
        compatibility = format_compatibility_section(findings)
        precision_section = format_precision_section(precision_findings)
        hardware_section = format_hardware_advice(hardware)
        advice = format_download_recommendation(recommendation)
        raw = build_raw_metadata(details)

        self.assertIn("apache", identity)
        self.assertIn("BertForSequenceClassification", architecture)
        self.assertIn("4 096 tokens", architecture)
        self.assertIn("Transformers", compatibility)
        self.assertIn("FP16", precision_section)
        self.assertIn("GGUF", precision_section)
        self.assertIn("Verdict", hardware_section)
        self.assertIn("VRAM recommandée", hardware_section)
        self.assertIn("model.safetensors", advice)
        self.assertEqual(raw["config"]["model_type"], "bert")
        self.assertEqual(raw["technical_profile"]["family"], "BERT")
        self.assertIn("hardware_advice", raw)
        self.assertIn("precision_formats", raw)

    def test_quantized_variants_are_presented_or_explicitly_absent(self) -> None:
        """La question « existe-t-il une version quantifiée ? » doit toujours avoir une réponse."""
        empty = format_quantized_variants((), "acme/modele")
        self.assertIn("Aucune variante quantifiée trouvée", empty)

        variant = QuantizedVariant(
            summary=ModelSummary(
                repo_id="acme/modele-GGUF", author="acme", likes=5, downloads=1_000,
                pipeline_tag=None, library_name=None, tags=(), created_at=None,
                last_modified=None, parameters=None, private=False, gated=False,
            ),
            formats=("GGUF",),
        )
        present = format_quantized_variants((variant,), "acme/modele")
        self.assertIn("acme/modele-GGUF", present)
        self.assertIn("GGUF", present)

    def test_similar_models_are_presented_or_explicitly_absent(self) -> None:
        """L'onglet doit toujours répondre, même sans résultat, plutôt que rester vide."""
        empty = format_similar_models(())
        self.assertIn("Aucun modèle similaire trouvé", empty)

        similar = SimilarModel(
            summary=ModelSummary(
                repo_id="mistralai/Mistral-7B-Instruct-v0.3", author="mistralai", likes=100, downloads=50_000,
                pipeline_tag="text-generation", library_name="transformers", tags=(), created_at=None,
                last_modified=None, parameters=7_200_000_000, private=False, gated=False,
            ),
            score=4.0,
            reasons=("Même tâche", "Taille proche (7.2 Md paramètres)"),
        )
        present = format_similar_models((similar,))
        self.assertIn("Mistral-7B-Instruct-v0.3", present)
        self.assertIn("Taille proche", present)

    def test_file_inventory_marks_runtime_files(self) -> None:
        """L'inventaire doit expliquer les rôles et signaler les fichiers conseillés."""
        details = make_details()

        rows = build_file_inventory(details, recommend_download(details))
        by_name = {row[0]: row for row in rows}

        self.assertEqual(by_name["config.json"][1], "Configuration du modèle")
        self.assertEqual(by_name["README.md"][1], "Documentation / Model Card")
        self.assertEqual(by_name["tokenizer.json"][1], "Tokenizer")
        self.assertEqual(by_name["weights/model.safetensors"][4], "✅ Oui")

    def test_file_tree_contains_nested_files_and_sizes(self) -> None:
        """Les dossiers imbriqués et tailles doivent figurer dans l'arbre."""
        tree = format_file_tree(make_details())

        self.assertIn("weights/", tree)
        self.assertIn("model.safetensors", tree)
        self.assertIn("2.0 Kio", tree)
        self.assertIn("5 fichiers", tree)

    def test_generated_snippets_are_valid_python(self) -> None:
        """Les deux exemples générés doivent être syntaxiquement valides."""
        local, inference = generate_code_snippets(make_details())

        compile(local, "<local-snippet>", "exec")
        compile(inference, "<inference-snippet>", "exec")
        self.assertIn("from transformers import pipeline", local)
        self.assertIn("InferenceClient", inference)
        self.assertIn("text_classification", inference)


class DetailsHandlerTests(unittest.TestCase):
    """Vérifier le chargement complet et l'ajout aux favoris."""

    def test_handler_returns_all_sections_and_enables_favorite(self) -> None:
        """Une fiche valide doit alimenter chaque composant de l'interface."""
        response = load_details_for_ui(
            FakeDetailsClient(),  # type: ignore[arg-type]
            "acme/modele",
            progress=NoopProgress(),  # type: ignore[arg-type]
        )

        self.assertEqual(response[0], "acme/modele")
        self.assertIn("chargée", response[1])
        self.assertIn("apache", response[2])
        self.assertIn("BertForSequenceClassification", response[3])
        self.assertIn("Transformers", response[4])
        self.assertIn("Précisions et quantifications", response[5])
        self.assertIn("Versions quantifiées existantes", response[6])
        self.assertIn("Modèles similaires", response[7])
        self.assertIn("Model Advisor", response[8])
        self.assertIn("réellement télécharger", response[9])
        self.assertEqual(response[11], "# Carte complète")
        self.assertIn("model.safetensors", response[13])
        self.assertTrue(response[16].interactive)

    def test_handler_turns_client_error_into_clear_state(self) -> None:
        """Une erreur métier doit vider une éventuelle ancienne fiche."""
        response = load_details_for_ui(
            FakeDetailsClient(HuggingFaceClientError("Hub indisponible")),  # type: ignore[arg-type]
            "acme/modele",
            progress=NoopProgress(),  # type: ignore[arg-type]
        )

        self.assertEqual(response[0], "")
        self.assertIn("Hub indisponible", response[1])
        self.assertFalse(response[16].interactive)

    def test_favorite_action_is_idempotent(self) -> None:
        """L'action UI doit distinguer ajout et favori déjà présent."""
        with tempfile.TemporaryDirectory() as directory:
            store = FavoritesStore(Path(directory) / "favorites.json")

            first = add_favorite_for_ui(store, "acme/modele")
            second = add_favorite_for_ui(store, "acme/modele")

        self.assertIn("ajouté", first)
        self.assertIn("déjà", second)


if __name__ == "__main__":
    unittest.main()
