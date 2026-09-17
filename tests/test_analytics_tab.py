"""Tests de l'observatoire de tendances de l'onglet Analytics."""

from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from datetime import date

from src.analytics import ANALYTICS_COLUMNS, RisingModel, TrendTracker
from src.api_client import HuggingFaceClientError, SearchFilters
from src.ui.analytics_tab import (
    TREND_LENSES,
    format_rising_models,
    format_trend_list,
    load_rising_models_for_ui,
    load_trend_for_ui,
)
from test_details_tab import NoopProgress, make_details


class TrendClient:
    """Double renvoyant un échantillon synthétique ou une erreur, sans réseau."""

    def __init__(self, models, error: Exception | None = None) -> None:
        """Préparer la réponse et l'erreur éventuelle."""
        self.models = models
        self.error = error
        self.filters = None

    def search_models(self, filters):
        """Enregistrer les filtres reçus et renvoyer l'échantillon préparé."""
        self.filters = filters
        if self.error:
            raise self.error
        return self.models


class LoadTrendForUiTests(unittest.TestCase):
    """Vérifier le chargement d'une tendance curatée et son alimentation du suivi de croissance."""

    def setUp(self) -> None:
        """Préparer un répertoire isolé, un suivi de tendances et un modèle de test."""
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.tracker = TrendTracker(self.directory.name)
        self.model = make_details().summary

    def test_every_lens_is_reachable_and_uses_a_distinct_key(self) -> None:
        """Chaque bouton de tendance doit correspondre à une configuration réelle et unique."""
        keys = [lens.key for lens in TREND_LENSES]
        self.assertEqual(len(keys), len(set(keys)))
        for lens in TREND_LENSES:
            with self.subTest(lens=lens.key):
                filters = lens.build_filters()
                self.assertIsInstance(filters, SearchFilters)
                self.assertIn(lens.sort_by, (None, *ANALYTICS_COLUMNS))

    def test_loading_a_lens_records_it_in_the_tracker(self) -> None:
        """Charger une tendance doit alimenter le suivi de croissance, sans action supplémentaire."""
        client = TrendClient([self.model])

        status, body = load_trend_for_ui(client, self.tracker, "top_downloads", progress=NoopProgress())

        self.assertIn("1 modèles", status)
        self.assertIn(self.model.repo_id, body)
        self.assertEqual(self.tracker.observed_days(), [date.today().isoformat()])

    def test_recent_lens_preserves_hub_order_instead_of_resorting_by_downloads(self) -> None:
        """Les modèles récents doivent garder l'ordre du Hub, pas être re-triés par téléchargements."""
        first = replace(self.model, repo_id="acme/newest", downloads=10)
        second = replace(self.model, repo_id="acme/older", downloads=10_000)
        client = TrendClient([first, second])

        _status, body = load_trend_for_ui(client, self.tracker, "recent", progress=NoopProgress())

        self.assertLess(body.index("acme/newest"), body.index("acme/older"))

    def test_network_error_is_reported_without_raising(self) -> None:
        """Une erreur du Hub doit rester un message lisible, jamais une exception qui remonte."""
        client = TrendClient([], HuggingFaceClientError("Hub indisponible"))

        status, body = load_trend_for_ui(client, self.tracker, "top_likes", progress=NoopProgress())

        self.assertIn("Hub indisponible", status)
        self.assertEqual(body, "")

    def test_empty_results_are_reported_clearly(self) -> None:
        """Aucun résultat ne doit produire un message vide ou trompeur."""
        client = TrendClient([])

        status, body = load_trend_for_ui(client, self.tracker, "french", progress=NoopProgress())

        self.assertIn("Aucun modèle", status)
        self.assertEqual(body, "")


class LoadRisingModelsForUiTests(unittest.TestCase):
    """Vérifier les messages honnêtes selon la quantité de données locales déjà accumulées."""

    def setUp(self) -> None:
        """Préparer un répertoire isolé et un suivi de tendances dédié."""
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.tracker = TrendTracker(self.directory.name)
        self.model = make_details().summary

    def test_no_observation_yet_asks_to_load_a_trend_first(self) -> None:
        """Sans aucune observation, le message doit orienter vers l'action à faire."""
        _status, body = load_rising_models_for_ui(self.tracker)

        self.assertIn("Chargez au moins une tendance", body)

    def test_single_day_explains_growth_needs_a_second_visit(self) -> None:
        """Une seule journée observée doit expliquer pourquoi rien n'est détecté, sans confusion."""
        self.tracker.record([self.model], day=date(2026, 9, 1))

        _status, body = load_rising_models_for_ui(self.tracker)

        self.assertIn("Une seule journée observée", body)

    def test_detected_growth_is_shown_with_its_observation_range(self) -> None:
        """Une croissance détectée doit afficher les deux dates et le facteur de croissance."""
        self.tracker.record([self.model], day=date(2026, 9, 1))
        grown = replace(self.model, downloads=self.model.downloads * 10 + 100_000)
        self.tracker.record([grown], day=date(2026, 9, 15))

        status, body = load_rising_models_for_ui(self.tracker)

        self.assertIn("croissance", status)
        self.assertIn("2026-09-01", body)
        self.assertIn("2026-09-15", body)


class FormattingTests(unittest.TestCase):
    """Vérifier les fonctions de mise en forme pures, indépendamment du réseau."""

    def test_format_rising_models_shows_growth_and_ratio(self) -> None:
        """L'exemple 100k → 500k doit se lire clairement dans la liste formatée."""
        rising = RisingModel("acme/model", "2026-09-01", 100_000, "2026-09-10", 500_000)

        body = format_rising_models([rising])

        self.assertIn("acme/model", body)
        self.assertIn("×5.0", body)
        self.assertIn("2026-09-01", body)
        self.assertIn("2026-09-10", body)

    def test_format_trend_list_handles_an_empty_table(self) -> None:
        """Un échantillon vide ne doit jamais produire une liste cassée."""
        import pandas as pd

        self.assertIn("Aucun résultat", format_trend_list(pd.DataFrame(columns=ANALYTICS_COLUMNS)))


if __name__ == "__main__":
    unittest.main()
