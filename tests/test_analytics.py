"""Tests des statistiques bornées et des observations locales."""

from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from datetime import date, timedelta
from unittest.mock import patch

from src.analytics import AnalyticsHistory, analytics_figures, analytics_table
from src.api_client import HuggingFaceClientError, SearchFilters
from src.ui.analytics_tab import analytics_for_ui
from test_details_tab import NoopProgress, make_details


class AnalyticsClient:
    """Double enregistrant les filtres et retournant un échantillon synthétique."""

    def __init__(self, models, error: Exception | None = None) -> None:
        """Définir l'échantillon et l'erreur éventuelle."""
        self.models = models
        self.error = error
        self.filters = None

    def search_models(self, filters):
        """Renvoyer les modèles sans contacter le Hub."""
        self.filters = filters
        if self.error:
            raise self.error
        return self.models


class AnalyticsTests(unittest.TestCase):
    """Vérifier les statistiques, l'historique et les callbacks."""

    def setUp(self) -> None:
        """Préparer un répertoire isolé et deux modèles."""
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.history = AnalyticsHistory(self.directory.name)
        summary = make_details().summary
        self.models = [summary, replace(summary, repo_id="acme/other", downloads=100, pipeline_tag=None, tags=())]
        self.filters = SearchFilters(sort="downloads", limit=50)

    def test_table_is_bounded_sorted_and_explicit_about_missing_data(self) -> None:
        """Même un client défectueux ne produit pas plus de cinquante lignes."""
        table = analytics_table(self.models * 30)
        self.assertEqual(len(table), 50)
        self.assertEqual(table.iloc[0]["Téléchargements"], 3400)
        self.assertIn("Non renseignée", table["Tâche"].tolist())
        self.assertIn("Non renseignée", table["Licence"].tolist())

    def test_history_replaces_same_day_without_inventing_past_dates(self) -> None:
        """Une deuxième observation le même jour remplace le point précédent."""
        first = self.history.record(self.filters, self.models, day=date(2026, 9, 1))
        self.assertEqual(first["Date"].nunique(), 1)
        changed = [replace(self.models[0], downloads=5000)]
        second = self.history.record(self.filters, changed, day=date(2026, 9, 1))
        self.assertEqual(len(second), 1)
        self.assertEqual(second.iloc[0]["Téléchargements"], 5000)
        third = self.history.record(self.filters, changed, day=date(2026, 9, 3))
        self.assertEqual(third["Date"].tolist(), ["2026-09-01", "2026-09-03"])

    def test_history_is_persistent_and_isolated_by_filter_and_authentication(self) -> None:
        """Deux filtres ou contextes auth ne partagent pas leurs observations."""
        self.history.record(self.filters, self.models, day=date(2026, 9, 1))
        restored = AnalyticsHistory(self.directory.name).record(self.filters, self.models, day=date(2026, 9, 2))
        self.assertEqual(restored["Date"].nunique(), 2)
        other_filter = self.history.record(SearchFilters(query="bert", limit=50), self.models, day=date(2026, 9, 2))
        self.assertEqual(other_filter["Date"].nunique(), 1)
        private = AnalyticsHistory(self.directory.name, scope="token-fingerprint")
        isolated = private.record(self.filters, self.models, day=date(2026, 9, 2))
        self.assertEqual(isolated["Date"].nunique(), 1)

    def test_history_keeps_only_ninety_daily_snapshots(self) -> None:
        """Le stockage ne croît pas indéfiniment."""
        for offset in range(92):
            frame = self.history.record(self.filters, self.models, day=date(2026, 1, 1) + timedelta(days=offset))
        self.assertEqual(frame["Date"].nunique(), 90)

    def test_figures_are_serializable_and_show_only_observed_points(self) -> None:
        """Les courbes ne créent pas de jours historiques supplémentaires."""
        observed = self.history.record(self.filters, self.models, day=date(2026, 9, 1))
        figures = analytics_figures(analytics_table(self.models), observed)
        self.assertEqual(len(figures), 4)
        for figure in figures:
            figure.to_json()
        self.assertEqual(len(figures[3].data[0].x), 1)

    def test_handler_requests_exactly_fifty_and_translates_filters(self) -> None:
        """La requête conserve la limite obligatoire et tous les filtres."""
        client = AnalyticsClient(self.models)
        response = analytics_for_ui(client, self.history, "bert", "fill-mask", "fr", "apache-2.0", progress=NoopProgress())
        self.assertEqual(client.filters.limit, 50)
        self.assertEqual(client.filters.sort, "downloads")
        self.assertEqual(client.filters.language, "fr")
        self.assertIn("2 modèles", response[0])
        self.assertTrue(all(figure is not None for figure in response[2:]))

    def test_empty_results_clear_all_figures(self) -> None:
        """Une recherche vide ne conserve pas de statistiques obsolètes."""
        response = analytics_for_ui(AnalyticsClient([]), self.history, "", "", "", "", progress=NoopProgress())
        self.assertTrue(response[1].empty)
        self.assertEqual(response[2:], (None, None, None, None))

    def test_network_error_is_safe_and_clears_results(self) -> None:
        """Une erreur réseau ne fait pas sortir le callback."""
        response = analytics_for_ui(AnalyticsClient([], HuggingFaceClientError("Hub indisponible")), self.history, "", "", "", "", progress=NoopProgress())
        self.assertIn("Hub indisponible", response[0])
        self.assertEqual(response[2:], (None, None, None, None))

    def test_failed_history_write_does_not_hide_current_statistics(self) -> None:
        """Un disque indisponible n'empêche pas les trois statistiques instantanées."""
        with patch.object(self.history, "record", side_effect=OSError("disk")):
            response = analytics_for_ui(AnalyticsClient(self.models), self.history, "", "", "", "", progress=NoopProgress())
        self.assertIn("pas pu être enregistrée", response[0])
        self.assertIsNotNone(response[2])
