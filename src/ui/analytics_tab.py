"""Observatoire du Hub : tendances curatées, modèles en croissance, et graphiques sur un échantillon."""

from __future__ import annotations

import html
from dataclasses import dataclass
from functools import partial
from typing import Callable
from urllib.parse import quote

from src.paths import data_directory

import gradio as gr
import pandas as pd
import plotly.graph_objects as go

from src.analytics import (
    ANALYTICS_COLUMNS,
    AnalyticsHistory,
    RisingModel,
    TrendTracker,
    analytics_figures,
    analytics_table,
)
from src.api_client import HuggingFaceClient, HuggingFaceClientError, SearchFilters
from src.ui.search_tab import LANGUAGE_CHOICES, LICENSE_CHOICES, PIPELINE_CHOICES
from src.utils.formatters import escape_markdown, format_count


@dataclass(frozen=True, slots=True)
class TrendLens:
    """Une tendance curatée : un tri ou un filtre Hub prêt à l'emploi, sans jargon technique."""

    key: str
    label: str
    note: str
    build_filters: Callable[[], SearchFilters]
    sort_by: str | None = "Téléchargements"


TREND_LENSES: tuple[TrendLens, ...] = (
    TrendLens(
        "top_downloads", "🔥 Plus téléchargés",
        "Les modèles les plus téléchargés du Hub, tous domaines confondus.",
        lambda: SearchFilters(sort="downloads", limit=30),
    ),
    TrendLens(
        "top_likes", "❤️ Plus appréciés",
        "Les modèles ayant reçu le plus de likes : un indice d'intérêt, pas de qualité.",
        lambda: SearchFilters(sort="likes", limit=30), sort_by="Likes",
    ),
    TrendLens(
        "recent", "🆕 Récents",
        "Les modèles créés le plus récemment sur le Hub.",
        lambda: SearchFilters(sort="created_at", limit=30), sort_by=None,
    ),
    TrendLens(
        "french", "🇫🇷 Français",
        "Modèles déclarant le français parmi leurs langues, triés par popularité.",
        lambda: SearchFilters(language="fr", sort="downloads", limit=30),
    ),
    TrendLens(
        "local", "💻 Optimisés local",
        "Repérage approximatif par mot-clé « gguf » dans le nom ou les tags : à vérifier au cas par cas.",
        lambda: SearchFilters(query="gguf", sort="downloads", limit=30),
    ),
)
_LENS_BY_KEY = {lens.key: lens for lens in TREND_LENSES}


def build_analytics_tab(client: HuggingFaceClient) -> None:
    """Construire l'observatoire de tendances et les filtres/graphiques détaillés."""
    history = AnalyticsHistory(data_directory() / "analytics", scope=client.cache_scope)
    tracker = TrendTracker(data_directory() / "analytics", scope=client.cache_scope)

    gr.Markdown(
        "## 🔭 Observatoire du Hub\n\n"
        "Des tendances curatées plutôt que des graphiques bruts : téléchargements, likes, nouveautés, "
        "et une détection de croissance fondée sur vos propres observations locales."
    )
    lens_buttons: dict[str, gr.Button] = {}
    with gr.Row():
        for lens in TREND_LENSES[:3]:
            lens_buttons[lens.key] = gr.Button(lens.label, size="sm")
    with gr.Row():
        for lens in TREND_LENSES[3:]:
            lens_buttons[lens.key] = gr.Button(lens.label, size="sm")
        rising_button = gr.Button("📈 Croissance rapide (Rising models)", size="sm")

    trend_status = gr.Markdown("Choisissez une tendance à explorer.", elem_classes="hf-search-status")
    trend_output = gr.Markdown("", elem_classes=["hf-tech-card"])

    for lens_key, button in lens_buttons.items():
        button.click(
            fn=partial(load_trend_for_ui, client, tracker, lens_key),
            outputs=[trend_status, trend_output],
            api_visibility="private",
            show_progress="minimal",
            concurrency_limit=1,
            concurrency_id="hub-analytics",
        )
    rising_button.click(
        fn=partial(load_rising_models_for_ui, tracker),
        outputs=[trend_status, trend_output],
        api_visibility="private",
        show_progress="hidden",
    )

    with gr.Accordion("🔬 Analyse détaillée par filtres", open=False):
        gr.Markdown(
            "Analyse des **50 modèles les plus téléchargés correspondant aux filtres**. "
            "Les répartitions concernent cet échantillon, pas l’ensemble du Hub."
        )
        with gr.Row():
            query = gr.Textbox(label="Mot-clé Analytics", placeholder="Facultatif : llama, bert…")
            task = gr.Dropdown(choices=PIPELINE_CHOICES, value="", label="Tâche Analytics")
            language = gr.Dropdown(choices=LANGUAGE_CHOICES, value="", label="Langue Analytics")
            license_name = gr.Dropdown(choices=LICENSE_CHOICES, value="", label="Licence Analytics")
        load = gr.Button("📈 Charger les Analytics", variant="primary")
        status = gr.Markdown("Chargez les statistiques pour afficher les graphiques.")
        with gr.Tabs():
            with gr.Tab("Téléchargements"):
                downloads = gr.Plot(label="Top téléchargements")
            with gr.Tab("Tâches et licences"):
                with gr.Row():
                    with gr.Column(min_width=400):
                        tasks = gr.Plot(label="Répartition des tâches")
                    with gr.Column(min_width=400):
                        licenses = gr.Plot(label="Répartition des licences")
            with gr.Tab("Évolution observée"):
                gr.Markdown(
                    "Ce graphique conserve une observation par jour UTC et par jeu de filtres (90 jours observés). "
                    "Le premier chargement n’a qu’un point : il ne reconstitue pas le passé. "
                    "Les compteurs sont ceux renvoyés par le Hub, pas des téléchargements cumulés calculés par l’app."
                )
                evolution = gr.Plot(label="Observations quotidiennes")
        with gr.Accordion("Données de l’échantillon", open=False):
            table = gr.Dataframe(
                headers=ANALYTICS_COLUMNS, value=[], interactive=False, wrap=True, show_search="search"
            )
        load.click(
            fn=partial(analytics_for_ui, client, history, tracker), inputs=[query, task, language, license_name],
            outputs=[status, table, downloads, tasks, licenses, evolution], api_name="model_analytics",
            show_progress="minimal", concurrency_limit=1, concurrency_id="hub-analytics",
        )


def load_trend_for_ui(
    client: HuggingFaceClient,
    tracker: TrendTracker,
    lens_key: str,
    progress: gr.Progress = gr.Progress(),
) -> tuple[str, str]:
    """Charger une tendance curatée, l'enregistrer dans le suivi de croissance, et la présenter."""
    lens = _LENS_BY_KEY[lens_key]
    progress(0.2, desc=f"Chargement « {lens.label} »…")
    try:
        models = client.search_models(lens.build_filters())
    except (ValueError, HuggingFaceClientError) as error:
        return f"⚠️ Tendance indisponible : {html.escape(str(error))}", ""
    except Exception:
        return "⚠️ Tendance indisponible : une erreur inattendue est survenue.", ""

    if not models:
        return f"Aucun modèle ne correspond à « {lens.label} ».", ""

    try:
        tracker.record(models)
    except OSError:
        pass  # Le suivi de croissance est un bonus : son échec ne doit pas cacher la tendance.

    progress(1, desc="Tendance prête")
    table = analytics_table(models, sort_by=lens.sort_by)
    body = format_trend_list(table)
    return f"✅ **{len(table)} modèles** — {lens.note}", f"### {lens.label}\n\n{body}"


def load_rising_models_for_ui(tracker: TrendTracker) -> tuple[str, str]:
    """Présenter les modèles en forte croissance détectés à partir des observations locales."""
    observed_days = tracker.observed_days()
    disclaimer = (
        "_Détection fondée uniquement sur vos observations locales : un modèle n'apparaît ici qu'après avoir "
        "été croisé au moins deux jours différents via une tendance ou l'analyse détaillée. Rien n'est "
        "reconstitué avant votre premier passage sur Huggor._"
    )
    if len(observed_days) < 2:
        remaining = "Chargez au moins une tendance." if not observed_days else (
            f"Une seule journée observée pour l'instant ({observed_days[0]}) : revenez un autre jour."
        )
        return "Pas encore assez de données pour détecter une croissance.", (
            f"### 📈 Croissance rapide (Rising models)\n\n{disclaimer}\n\n_{remaining}_"
        )

    rising = tracker.rising_models()
    if not rising:
        return "Aucune croissance notable détectée.", (
            f"### 📈 Croissance rapide (Rising models)\n\n{disclaimer}\n\n"
            f"_Aucun modèle observé entre le {observed_days[0]} et le {observed_days[-1]} ne dépasse les seuils "
            "de croissance retenus._"
        )

    body = format_rising_models(rising)
    return f"✅ **{len(rising)} modèle(s) en croissance** détecté(s).", (
        f"### 📈 Croissance rapide (Rising models)\n\n{disclaimer}\n\n{body}"
    )


def format_trend_list(table: pd.DataFrame) -> str:
    """Présenter un échantillon classé en liste Markdown numérotée, pas un simple graphique."""
    if table.empty:
        return "_Aucun résultat._"
    lines = []
    for rank, (_, row) in enumerate(table.iterrows(), start=1):
        repo_id = str(row["Modèle"])
        url = f"https://huggingface.co/{quote(repo_id, safe='/')}"
        lines.append(
            f"{rank}. **[{escape_markdown(repo_id)}]({url})** — "
            f"{format_count(row['Téléchargements'])} téléchargements · {format_count(row['Likes'])} likes · "
            f"{escape_markdown(str(row['Tâche']))}"
        )
    return "\n".join(lines)


def format_rising_models(models: list[RisingModel]) -> str:
    """Présenter les modèles en croissance avec leur fourchette d'observation exacte."""
    lines = []
    for rank, item in enumerate(models, start=1):
        url = f"https://huggingface.co/{quote(item.repo_id, safe='/')}"
        ratio_label = "∞" if item.ratio == float("inf") else f"×{item.ratio:.1f}"
        lines.append(
            f"{rank}. **[{escape_markdown(item.repo_id)}]({url})** — "
            f"{format_count(item.first_downloads)} → {format_count(item.last_downloads)} téléchargements "
            f"({ratio_label}, +{format_count(item.growth)}) entre le {item.first_date} et le {item.last_date}"
        )
    return "\n".join(lines)


def analytics_for_ui(
    client: HuggingFaceClient, history: AnalyticsHistory, tracker: TrendTracker,
    query: str, task: str, language: str, license_name: str,
    progress: gr.Progress = gr.Progress(),
) -> tuple[str, pd.DataFrame, go.Figure | None, go.Figure | None, go.Figure | None, go.Figure | None]:
    """Charger cinquante résultats au maximum et gérer les erreurs sans conserver un ancien graphique."""
    empty = pd.DataFrame(columns=ANALYTICS_COLUMNS)
    try:
        filters = SearchFilters(
            query=query or "", pipeline_tag=task or None, language=language or None,
            license=license_name or None, sort="downloads", limit=50,
        )
        progress(0.15, desc="Chargement des 50 modèles…")
        models = client.search_models(filters)[:50]
        table = analytics_table(models)
        if table.empty:
            return "Aucun modèle ne correspond aux filtres.", empty, None, None, None, None
        warning = ""
        try:
            observed = history.record(filters, models)
            tracker.record(models)
        except OSError:
            observed = pd.DataFrame(columns=["Date", "Modèle", "Téléchargements"])
            warning = " ⚠️ L’observation locale n’a pas pu être enregistrée."
        progress(0.75, desc="Préparation des graphiques…")
        figures = analytics_figures(table, observed)
        days = observed["Date"].nunique()
    except (ValueError, HuggingFaceClientError) as error:
        return f"⚠️ Analytics indisponibles : {html.escape(str(error))}", empty, None, None, None, None
    except Exception:
        return "⚠️ Analytics indisponibles : une erreur inattendue est survenue.", empty, None, None, None, None
    progress(1, desc="Analytics prêtes")
    return f"✅ **{len(models)} modèles analysés** · {days} jour(s) observé(s).{warning}", table, *figures
