"""Tests de la logique de présentation de l'onglet Recherche."""

from __future__ import annotations

import unittest

from src.api_client import HuggingFaceClientError, ModelSummary, SearchFilters
from src.ui.search_tab import (
    TASK_DOMAINS,
    _domain_task_choices,
    _parse_task_value,
    format_model_card,
    search_for_ui,
    select_model_for_details,
)


class RecordingClient:
    """Double enregistrant les filtres transmis par le formulaire."""

    def __init__(self, *, error: Exception | None = None) -> None:
        """Préparer un résultat synthétique ou une erreur."""
        self.error = error
        self.filters: SearchFilters | None = None
        self.offline_notice = ""

    def search_models(self, filters: SearchFilters) -> list[ModelSummary]:
        """Enregistrer les filtres et fournir un modèle de test."""
        self.filters = filters
        if self.error is not None:
            raise self.error
        return [
            ModelSummary(
                repo_id="acme/modele-fr",
                author="acme",
                likes=1_250,
                downloads=2_500_000,
                pipeline_tag="text-classification",
                library_name="transformers",
                tags=("fr", "license:apache-2.0"),
                created_at=None,
                last_modified=None,
                parameters=1_500_000_000,
                private=False,
                gated=False,
            )
        ]


class NoopProgress:
    """Remplacement appelable de ``gr.Progress`` pour les tests."""

    def __call__(self, *_args: object, **_kwargs: object) -> None:
        """Ignorer les mises à jour de progression."""


class SearchHandlerTests(unittest.TestCase):
    """Vérifier la conversion du formulaire et les messages utilisateur."""

    def test_search_form_is_converted_and_bounded(self) -> None:
        """Les milliards des sliders doivent devenir des nombres de paramètres."""
        client = RecordingClient()

        payload, status = search_for_ui(
            client,  # type: ignore[arg-type]
            "bert",
            "text-classification",
            "fr",
            "apache-2.0",
            1.5,
            7,
            "likes",
            25,
            progress=NoopProgress(),  # type: ignore[arg-type]
        )

        self.assertEqual(len(payload), 1)
        self.assertEqual(status, "**1 modèle trouvé.**")
        self.assertIsNotNone(client.filters)
        assert client.filters is not None
        self.assertEqual(client.filters.min_parameters, 1_500_000_000)
        self.assertEqual(client.filters.max_parameters, 7_000_000_000)
        self.assertEqual(client.filters.limit, 25)

    def test_offline_notice_is_prefixed_to_the_status_when_the_client_is_offline(self) -> None:
        """Une recherche servie depuis le secours hors connexion doit rester visible pour l'utilisateur."""
        client = RecordingClient()
        client.offline_notice = "🟠 **Mode hors connexion** — "

        _payload, status = search_for_ui(
            client,  # type: ignore[arg-type]
            "bert",
            "",
            "",
            "",
            0,
            0,
            "downloads",
            20,
            progress=NoopProgress(),  # type: ignore[arg-type]
        )

        self.assertTrue(status.startswith("🟠 **Mode hors connexion** — "))

    def test_client_error_becomes_a_clear_message(self) -> None:
        """Une erreur métier ne doit pas s'échapper du callback Gradio."""
        client = RecordingClient(error=HuggingFaceClientError("Service indisponible."))

        payload, status = search_for_ui(
            client,  # type: ignore[arg-type]
            "bert",
            "",
            "",
            "",
            0,
            0,
            "downloads",
            20,
            progress=NoopProgress(),  # type: ignore[arg-type]
        )

        self.assertEqual(payload, [])
        self.assertIn("Service indisponible", status)

    def test_composite_task_value_adds_the_keyword_to_the_query(self) -> None:
        """Une tâche pédagogique (ex. Code) doit filtrer par pipeline_tag ET mot-clé combinés."""
        client = RecordingClient()

        search_for_ui(
            client,  # type: ignore[arg-type]
            "python",
            "text-generation::code",
            "",
            "",
            0,
            0,
            "downloads",
            20,
            progress=NoopProgress(),  # type: ignore[arg-type]
        )

        assert client.filters is not None
        self.assertEqual(client.filters.pipeline_tag, "text-generation")
        self.assertEqual(client.filters.query, "python code")

    def test_plain_task_value_has_no_implicit_keyword(self) -> None:
        """Une tâche directement reliée à un pipeline_tag ne doit rien ajouter à la requête."""
        client = RecordingClient()

        search_for_ui(
            client,  # type: ignore[arg-type]
            "",
            "translation",
            "",
            "",
            0,
            0,
            "downloads",
            20,
            progress=NoopProgress(),  # type: ignore[arg-type]
        )

        assert client.filters is not None
        self.assertEqual(client.filters.pipeline_tag, "translation")
        self.assertEqual(client.filters.query, "")

    def test_invalid_limit_is_reported_without_calling_client(self) -> None:
        """Une limite hors bornes doit être présentée comme une erreur de filtre."""
        client = RecordingClient()

        payload, status = search_for_ui(
            client,  # type: ignore[arg-type]
            "",
            "",
            "",
            "",
            0,
            0,
            "downloads",
            101,
            progress=NoopProgress(),  # type: ignore[arg-type]
        )

        self.assertEqual(payload, [])
        self.assertIn("Filtres invalides", status)
        self.assertIsNone(client.filters)


class TaskTaxonomyTests(unittest.TestCase):
    """Vérifier la navigation par domaine et la valeur composite tâche/mot-clé."""

    def test_parse_task_value_splits_pipeline_and_keyword(self) -> None:
        """Une valeur composite doit se décomposer en pipeline_tag réel et mot-clé."""
        self.assertEqual(_parse_task_value("text-generation::chat"), ("text-generation", "chat"))
        self.assertEqual(_parse_task_value("translation"), ("translation", ""))
        self.assertEqual(_parse_task_value(""), (None, ""))

    def test_every_domain_task_maps_to_a_non_empty_pipeline_tag(self) -> None:
        """Chaque tâche pédagogique doit être reliée à une tâche Hub réelle, jamais vide."""
        for domain in TASK_DOMAINS:
            for task in domain.tasks:
                with self.subTest(domain=domain.key, task=task.label):
                    self.assertTrue(task.pipeline_tag)

    def test_domain_choices_are_scoped_to_that_domain(self) -> None:
        """Choisir un domaine ne doit proposer que ses propres tâches, pas celles d'un autre."""
        llm_choices = dict(_domain_task_choices("llm"))

        self.assertIn("Chat", llm_choices)
        self.assertNotIn("Détection d'objets", llm_choices)

    def test_all_domains_choice_prefixes_tasks_with_their_domain_emoji(self) -> None:
        """Sans domaine choisi, chaque tâche doit rester identifiable par son domaine d'origine."""
        all_choices = dict(_domain_task_choices(""))

        self.assertIn("🧠 Chat", all_choices)
        self.assertIn("👁️ Détection d'objets", all_choices)


class SearchRenderingTests(unittest.TestCase):
    """Vérifier les cartes Markdown et la navigation inter-onglets."""

    def test_card_contains_metrics_tags_and_hub_link(self) -> None:
        """Une carte doit présenter les informations prioritaires du modèle."""
        card = format_model_card(
            {
                "repo_id": "acme/modele",
                "author": "acme",
                "likes": 1_250,
                "downloads": 2_500_000,
                "parameters": 1_500_000_000,
                "pipeline_tag": "text-generation",
                "library_name": "transformers",
                "tags": ["fr", "tag`injecté"],
            }
        )

        self.assertIn("https://huggingface.co/acme/modele", card)
        self.assertIn("1.2 k", card)
        self.assertIn("2.5 M", card)
        self.assertIn("1.5 Md", card)
        self.assertNotIn("`tag`injecté`", card)

    def test_navigation_targets_details_tab(self) -> None:
        """Le clic d'une carte doit préremplir le modèle et sélectionner Détails."""
        repo_id, tabs_update = select_model_for_details("acme/modele")

        self.assertEqual(repo_id, "acme/modele")
        self.assertEqual(tabs_update.selected, "details")


if __name__ == "__main__":
    unittest.main()
