"""Statistiques sur un échantillon borné et historique des observations locales."""

from __future__ import annotations

import json
import threading
from collections.abc import Sequence
from dataclasses import asdict
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.api_client import ModelSummary, SearchFilters
from src.comparison import model_license
from src.utils.cache import JsonCache

ANALYTICS_COLUMNS = ["Modèle", "Téléchargements", "Likes", "Tâche", "Licence"]


class AnalyticsHistory:
    """Conserver les 90 dernières observations quotidiennes par filtre et contexte auth."""

    def __init__(self, directory: str | Path, *, scope: str = "anonymous") -> None:
        """Initialiser un stockage atomique indépendant du cache réseau éphémère."""
        self.cache = JsonCache(directory, default_ttl=365 * 86400)
        self.scope = scope
        self._lock = threading.RLock()

    def record(
        self, filters: SearchFilters, models: Sequence[ModelSummary], *, day: date | None = None,
    ) -> pd.DataFrame:
        """Remplacer l'observation du jour et retourner seulement les mesures réellement prises."""
        observed_day = (day or datetime.now(timezone.utc).date()).isoformat()
        key = json.dumps({"scope": self.scope, "filters": asdict(filters)}, sort_keys=True)
        with self._lock:
            cached = self.cache.get("observations", key)
            snapshots = []
            if isinstance(cached, list):
                for item in cached:
                    if not isinstance(item, dict) or not isinstance(item.get("models"), list):
                        continue
                    try:
                        date.fromisoformat(item.get("date", ""))
                    except (TypeError, ValueError):
                        continue
                    if item["date"] != observed_day:
                        snapshots.append(item)
            snapshots.append({
                "date": observed_day,
                "models": [{"repo_id": model.repo_id, "downloads": model.downloads} for model in models[:50]],
            })
            snapshots = sorted(snapshots, key=lambda item: item["date"])[-90:]
            self.cache.set("observations", key, snapshots)
        rows = []
        for snapshot in snapshots:
            for model in snapshot["models"]:
                if (isinstance(model, dict) and isinstance(model.get("repo_id"), str)
                        and isinstance(model.get("downloads"), int) and model["downloads"] >= 0):
                    rows.append([snapshot["date"], model["repo_id"], model["downloads"]])
        return pd.DataFrame(rows, columns=["Date", "Modèle", "Téléchargements"])


def analytics_table(models: Sequence[ModelSummary]) -> pd.DataFrame:
    """Construire les données de l'échantillon, au plus 50 modèles."""
    return pd.DataFrame([
        [model.repo_id, model.downloads, model.likes, model.pipeline_tag or "Non renseignée", model_license(model)]
        for model in models[:50]
    ], columns=ANALYTICS_COLUMNS).sort_values("Téléchargements", ascending=False, kind="stable")


def analytics_figures(
    table: pd.DataFrame, history: pd.DataFrame,
) -> tuple[go.Figure | None, go.Figure | None, go.Figure | None, go.Figure | None]:
    """Afficher téléchargements, tâches, licences et observations du top 5 actuel."""
    if table.empty:
        return None, None, None, None
    ordered = table.sort_values("Téléchargements", ascending=True)
    downloads = px.bar(
        ordered, x="Téléchargements", y="Modèle", orientation="h",
        title=f"Top {len(table)} téléchargements — sélection actuelle",
        hover_data=["Likes", "Tâche", "Licence"],
    )
    downloads.update_layout(height=max(450, len(table) * 25), margin={"l": 20})
    task_counts = table["Tâche"].value_counts().rename_axis("Tâche").reset_index(name="Modèles")
    tasks = px.pie(task_counts, names="Tâche", values="Modèles", title="Tâches dans l’échantillon", hole=0.35)
    license_counts = table["Licence"].value_counts().rename_axis("Licence").reset_index(name="Modèles")
    licenses = px.pie(license_counts, names="Licence", values="Modèles", title="Licences dans l’échantillon", hole=0.35)
    top_ids = table.head(5)["Modèle"].tolist()
    observed = history[history["Modèle"].isin(top_ids)].sort_values("Date")
    evolution = px.line(
        observed, x="Date", y="Téléchargements", color="Modèle", markers=True,
        title="Top 5 actuel — observations locales quotidiennes",
    )
    evolution.update_layout(xaxis={"type": "date"}, legend={"orientation": "h", "y": -0.25}, height=520)
    evolution.update_xaxes(tickformat="%d/%m/%Y")
    if observed["Date"].nunique() == 1:
        observation_day = pd.Timestamp(observed["Date"].iloc[0])
        evolution.update_xaxes(
            range=[(observation_day - pd.Timedelta(hours=12)).isoformat(),
                   (observation_day + pd.Timedelta(hours=12)).isoformat()],
            tickvals=[observation_day.isoformat()],
        )
    for figure in (downloads, tasks, licenses, evolution):
        figure.update_layout(template="plotly_white")
    return downloads, tasks, licenses, evolution
