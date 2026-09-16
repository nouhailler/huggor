"""Tests du comparateur, isolés du réseau."""

from __future__ import annotations

import unittest
from dataclasses import replace

from src.api_client import HuggingFaceClientError, ModelFile
from src.comparison import (
    build_comparison_decision,
    comparison_radar,
    comparison_table,
    file_storage,
    validate_comparison_ids,
)
from src.ui.compare_tab import compare_for_ui
from test_details_tab import NoopProgress, make_details


class CompareClient:
    """Double enregistrant les fiches demandées."""

    def __init__(self, error: Exception | None = None) -> None:
        """Préparer la réponse et les compteurs."""
        self.calls = []
        self.error = error

    def get_model_info(self, repo_id: str):
        """Retourner une fiche distincte pour chaque identifiant."""
        self.calls.append(repo_id)
        if self.error:
            raise self.error
        details = make_details()
        return replace(details, summary=replace(details.summary, repo_id=repo_id))


class ComparisonTests(unittest.TestCase):
    """Vérifier les bornes et les résultats graphiques."""

    def test_validation_rejects_duplicates_invalid_ids_and_counts(self) -> None:
        """Aucune sélection ambiguë ou non bornée n'est acceptée."""
        for values in (["acme/a"], ["acme/a"] * 2, ["acme/a", "a/b/c"], [f"acme/{i}" for i in range(5)]):
            with self.assertRaises(ValueError):
                validate_comparison_ids(values)
        self.assertEqual(validate_comparison_ids([" acme/a ", "", "acme/b"]), ("acme/a", "acme/b"))

    def test_table_contains_required_fields(self) -> None:
        """Le tableau présente licence, taille, paramètres et date de mise à jour."""
        table = comparison_table([make_details()])
        self.assertEqual(table.iloc[0]["Licence"], "apache-2.0")
        self.assertIn("Paramètres", table.columns)
        self.assertIn("Dernière MAJ", table.columns)
        self.assertEqual(table.iloc[0]["Contexte (tokens)"], "4096")

    def test_radar_is_normalized_and_closed(self) -> None:
        """Le maximum vaut 100 et chaque polygone revient à son premier point."""
        first = make_details()
        second = replace(first, summary=replace(first.summary, repo_id="acme/second", likes=24))
        radar = comparison_radar([first, second])
        self.assertEqual(len(radar.data), 2)
        self.assertEqual(radar.data[0].r[0], radar.data[0].r[-1])
        like_index = list(radar.data[0].theta).index("Likes")
        self.assertEqual(radar.data[0].r[like_index], 50)
        self.assertEqual(radar.data[1].r[like_index], 100)
        radar.to_json()

    def test_unknown_axes_are_removed_instead_of_zero_filled(self) -> None:
        """Une valeur manquante ne représente pas un score nul."""
        first = make_details()
        second = replace(first, summary=replace(first.summary, parameters=None))
        radar = comparison_radar([first, second])
        self.assertNotIn("Paramètres", radar.data[0].theta)
        unknown_size = replace(first, files=(ModelFile("model.safetensors", None, None),))
        self.assertIsNone(file_storage(unknown_size))

    def test_insufficient_common_values_do_not_create_a_radar(self) -> None:
        """Les compteurs nuls et champs absents ne provoquent aucune division par zéro."""
        details = make_details()
        sparse = replace(details, files=(), config={}, summary=replace(details.summary, parameters=None, likes=0, downloads=0))
        self.assertIsNone(comparison_radar([sparse, sparse]))

    def test_handler_loads_at_most_four_models(self) -> None:
        """La sélection maximale effectue exactement quatre appels."""
        client = CompareClient()
        status, decision_table, recommendation, table, radar = compare_for_ui(
            client, "acme/a", "acme/b", "acme/c", "acme/d", progress=NoopProgress()
        )
        self.assertEqual(len(client.calls), 4)
        self.assertEqual(len(table), 4)
        self.assertIn("4 modèles", status)
        self.assertIsNotNone(radar)
        self.assertIn("Comparaison décisionnelle", decision_table)
        self.assertIn("Recommandation", recommendation)

    def test_invalid_input_does_not_call_the_client(self) -> None:
        """La validation précède le réseau."""
        client = CompareClient()
        status, decision_table, recommendation, table, radar = compare_for_ui(
            client, "acme/a", "acme/a", progress=NoopProgress()
        )
        self.assertFalse(client.calls)
        self.assertTrue(table.empty)
        self.assertIsNone(radar)
        self.assertEqual(decision_table, "")
        self.assertEqual(recommendation, "")

    def test_network_error_clears_the_previous_comparison(self) -> None:
        """L'interface retourne un état vide et un message sûr."""
        status, decision_table, recommendation, table, radar = compare_for_ui(
            CompareClient(HuggingFaceClientError("Hub indisponible")), "acme/a", "acme/b", progress=NoopProgress()
        )
        self.assertIn("Hub indisponible", status)
        self.assertTrue(table.empty)
        self.assertIsNone(radar)
        self.assertEqual(decision_table, "")
        self.assertEqual(recommendation, "")

    def test_decision_recommends_the_best_local_compromise(self) -> None:
        """Le modèle le plus léger et compatible GGUF doit être recommandé pour le local."""
        light = make_details()  # 1.5 Md paramètres, langues fr/en déclarées.
        heavy = replace(
            light,
            summary=replace(light.summary, repo_id="acme/heavy", parameters=70_000_000_000),
        )
        decision = build_comparison_decision([light, heavy])
        rows = {row.repo_id: row for row in decision.rows}

        self.assertEqual(rows["acme/modele"].fr_stars, 5)
        self.assertGreater(rows["acme/modele"].local_stars, rows["acme/heavy"].local_stars)
        self.assertEqual(decision.recommended_repo_id, "acme/modele")
        self.assertIn("téléchargements", decision.recommendation_reason)

    def test_decision_without_any_known_parameters_cannot_recommend(self) -> None:
        """Sans paramètres connus pour aucun modèle, aucune recommandation ne doit être inventée."""
        details = make_details()
        unknown = replace(details, summary=replace(details.summary, repo_id="acme/unknown", parameters=None))
        decision = build_comparison_decision([unknown, unknown])

        self.assertIsNone(decision.recommended_repo_id)
        self.assertIn("non renseignés", decision.recommendation_reason)
