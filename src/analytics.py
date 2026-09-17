"""Statistiques sur un échantillon borné et historique des observations locales."""

from __future__ import annotations

import json
import threading
from collections.abc import Sequence
from dataclasses import asdict, dataclass
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


def analytics_table(models: Sequence[ModelSummary], *, sort_by: str | None = "Téléchargements") -> pd.DataFrame:
    """Construire les données de l'échantillon, au plus 50 modèles.

    ``sort_by=None`` conserve l'ordre renvoyé par le Hub (utile pour un tri par date de création,
    que cette fonction ne sait pas reproduire à partir des seules colonnes affichées).
    """
    table = pd.DataFrame([
        [model.repo_id, model.downloads, model.likes, model.pipeline_tag or "Non renseignée", model_license(model)]
        for model in models[:50]
    ], columns=ANALYTICS_COLUMNS)
    if sort_by is None:
        return table
    return table.sort_values(sort_by, ascending=False, kind="stable")


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


@dataclass(frozen=True, slots=True)
class RisingModel:
    """Modèle dont les téléchargements ont significativement augmenté entre deux observations locales."""

    repo_id: str
    first_date: str
    first_downloads: int
    last_date: str
    last_downloads: int

    @property
    def growth(self) -> int:
        """Croissance absolue des téléchargements entre les deux observations."""
        return self.last_downloads - self.first_downloads

    @property
    def ratio(self) -> float:
        """Facteur multiplicatif de croissance, prudent quand la première mesure vaut zéro."""
        if self.first_downloads <= 0:
            return float("inf") if self.last_downloads > 0 else 1.0
        return self.last_downloads / self.first_downloads


class TrendTracker:
    """Historique global (indépendant des filtres) de tous les modèles déjà croisés dans l'app.

    Contrairement à ``AnalyticsHistory``, qui isole chaque combinaison de filtres, ce suivi
    accumule dans un seul journal partagé chaque modèle observé via n'importe quel onglet
    Tendances ou Analytics : c'est ce qui permet de détecter une croissance même si le modèle
    n'a été croisé qu'une fois via un filtre différent de celui qui l'a re-détecté plus tard.
    """

    def __init__(self, directory: str | Path, *, scope: str = "anonymous", retention_days: int = 90) -> None:
        """Initialiser un journal atomique distinct du cache réseau éphémère."""
        self.cache = JsonCache(directory, default_ttl=365 * 86400)
        self.scope = scope
        self.retention_days = retention_days
        self._lock = threading.RLock()

    def record(self, models: Sequence[ModelSummary], *, day: date | None = None) -> None:
        """Ajouter ou compléter l'observation du jour, sans écraser les autres modèles déjà vus ce jour-là."""
        observed_day = (day or datetime.now(timezone.utc).date()).isoformat()
        with self._lock:
            per_day = self._read()
            entries = dict(per_day.get(observed_day, {}))
            for model in models:
                if model.downloads >= 0:
                    entries[model.repo_id] = model.downloads
            per_day[observed_day] = entries
            kept_days = sorted(per_day)[-self.retention_days:]
            trimmed = {day_key: per_day[day_key] for day_key in kept_days}
            self.cache.set("trend_observations", self.scope, trimmed)

    def observed_days(self) -> list[str]:
        """Lister les jours pour lesquels au moins une observation existe, triés."""
        return sorted(self._read())

    def rising_models(self, *, min_growth: int = 1_000, min_ratio: float = 1.2, limit: int = 10) -> list[RisingModel]:
        """Repérer les modèles en forte croissance entre leur première et leur dernière observation.

        Un modèle vu une seule journée ne peut fournir aucune évolution mesurable et est ignoré.
        Les seuils par défaut écartent le bruit statistique des tout petits comptes.
        """
        per_day = self._read()
        days = sorted(per_day)
        if len(days) < 2:
            return []

        first_seen: dict[str, tuple[str, int]] = {}
        last_seen: dict[str, tuple[str, int]] = {}
        for day_key in days:
            for repo_id, downloads in per_day[day_key].items():
                if repo_id not in first_seen:
                    first_seen[repo_id] = (day_key, downloads)
                last_seen[repo_id] = (day_key, downloads)

        candidates = []
        for repo_id, (first_date, first_downloads) in first_seen.items():
            last_date, last_downloads = last_seen[repo_id]
            if first_date == last_date:
                continue
            rising = RisingModel(repo_id, first_date, first_downloads, last_date, last_downloads)
            if rising.growth >= min_growth and rising.ratio >= min_ratio:
                candidates.append(rising)

        candidates.sort(key=lambda item: item.ratio, reverse=True)
        return candidates[:limit]

    def _read(self) -> dict[str, dict[str, int]]:
        """Lire le journal brut, sans jamais lever d'exception sur un cache absent ou corrompu."""
        cached = self.cache.get("trend_observations", self.scope)
        return cached if isinstance(cached, dict) else {}
