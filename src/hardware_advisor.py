"""Traduire un nombre de paramètres en besoins mémoire et en verdict d'usage local.

Les paliers utilisés (RAM/VRAM par taille de modèle) reprennent les repères usuels de la
communauté LLM local (llama.cpp/Ollama) : ils restent des ordres de grandeur, pas une mesure
exacte, car la consommation réelle dépend aussi du contexte utilisé et du moteur d'inférence.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

from src.model_analysis import CompatibilityFinding, TechnicalProfile

FitStatus = Literal["ok", "warning", "no", "unknown"]

_GIB = 1024**3
_RUNTIME_OVERHEAD = 1.15  # Marge pour le contexte, le cache KV et l'exécution.

# (paramètres max en milliards, RAM minimale, RAM confortable) en Gio.
_RAM_TIERS_GIB: tuple[tuple[float, int, int], ...] = (
    (3, 4, 8),
    (8, 8, 16),
    (15, 16, 32),
    (35, 32, 64),
    (70, 64, 128),
)

# (paramètres max en milliards, VRAM minimale, VRAM confortable) en Gio, pour une quantification 4 bits.
_VRAM_TIERS_GIB: tuple[tuple[float, int, int], ...] = (
    (3, 2, 4),
    (8, 4, 8),
    (15, 8, 12),
    (35, 16, 24),
    (70, 32, 48),
)

_STATUS_FROM_COMPATIBILITY: dict[str, FitStatus] = {
    "detected": "ok",
    "probable": "warning",
    "conversion": "warning",
    "not_detected": "no",
}


@dataclass(frozen=True, slots=True)
class MemoryEstimate:
    """Empreinte mémoire approchée pour une précision donnée."""

    label: str
    low_bytes: int
    high_bytes: int

    def to_dict(self) -> dict[str, int | str]:
        """Convertir l'estimation en dictionnaire sérialisable."""
        return asdict(self)


@dataclass(frozen=True, slots=True)
class HardwareCriterion:
    """Ligne du tableau d'adéquation matérielle, avec son statut et sa justification."""

    name: str
    status: FitStatus
    detail: str

    def to_dict(self) -> dict[str, str]:
        """Convertir le critère en dictionnaire sérialisable."""
        return asdict(self)


@dataclass(frozen=True, slots=True)
class HardwareAdvice:
    """Synthèse d'adéquation matérielle prête à afficher : le « Model Advisor »."""

    parameters: int | None
    ram_estimates: tuple[MemoryEstimate, ...]
    vram_recommended: MemoryEstimate | None
    criteria: tuple[HardwareCriterion, ...]
    ram_comfortable_gib: int | None
    verdict_emoji: str
    verdict_headline: str
    verdict_detail: str

    def to_dict(self) -> dict[str, Any]:
        """Convertir le conseil en dictionnaire sérialisable."""
        return {
            "parameters": self.parameters,
            "ram_estimates": [item.to_dict() for item in self.ram_estimates],
            "vram_recommended": self.vram_recommended.to_dict() if self.vram_recommended else None,
            "criteria": [item.to_dict() for item in self.criteria],
            "ram_comfortable_gib": self.ram_comfortable_gib,
            "verdict_emoji": self.verdict_emoji,
            "verdict_headline": self.verdict_headline,
            "verdict_detail": self.verdict_detail,
        }


def advise_hardware(
    profile: TechnicalProfile,
    compatibility: tuple[CompatibilityFinding, ...],
) -> HardwareAdvice:
    """Estimer la mémoire nécessaire et rendre un verdict d'usage sur machine locale."""
    findings = {item.name: item for item in compatibility}
    parameters = profile.parameters

    if not parameters or parameters <= 0:
        unknown_detail = "Nombre de paramètres non renseigné par ce dépôt."
        return HardwareAdvice(
            parameters=None,
            ram_estimates=(),
            vram_recommended=None,
            criteria=(
                HardwareCriterion("CPU (16 Go RAM)", "unknown", unknown_detail),
                HardwareCriterion("GPU 8 Go", "unknown", unknown_detail),
                HardwareCriterion("GPU 4 Go", "unknown", unknown_detail),
                HardwareCriterion("CPU seul (sans GPU)", "unknown", unknown_detail),
                _compatibility_criterion("Ollama", findings.get("Ollama")),
                _compatibility_criterion("GGUF", findings.get("GGUF")),
            ),
            ram_comfortable_gib=None,
            verdict_emoji="⚪",
            verdict_headline="Estimation impossible",
            verdict_detail=unknown_detail,
        )

    ram_estimates = (
        _memory_estimate("FP32", parameters, 4.0, 4.0),
        _memory_estimate("FP16 / BF16", parameters, 2.0, 2.0),
        _memory_estimate("INT8", parameters, 1.0, 1.0),
        _memory_estimate("INT4 (Q4)", parameters, 0.5, 0.6),
    )

    ram_min_gib, ram_comfortable_gib = _tier_for(parameters, _RAM_TIERS_GIB)
    vram_min_gib, vram_comfortable_gib = _tier_for(parameters, _VRAM_TIERS_GIB)
    vram_recommended = MemoryEstimate(
        "VRAM recommandée",
        vram_min_gib * _GIB,
        vram_comfortable_gib * _GIB,
    )

    criteria = (
        _tier_criterion(
            "CPU (16 Go RAM)",
            ram_min_gib,
            ram_comfortable_gib,
            16,
            "RAM système nécessaire pour charger une version quantifiée du modèle et l'exécuter avec le processeur.",
        ),
        _tier_criterion(
            "GPU 8 Go",
            vram_min_gib,
            vram_comfortable_gib,
            8,
            "VRAM nécessaire pour charger une version quantifiée du modèle sur une carte graphique de 8 Go.",
        ),
        _tier_criterion(
            "GPU 4 Go",
            vram_min_gib,
            vram_comfortable_gib,
            4,
            "VRAM nécessaire pour charger une version fortement quantifiée sur une carte graphique d'entrée de gamme.",
        ),
        _tier_criterion(
            "CPU seul (sans GPU)",
            ram_min_gib,
            ram_comfortable_gib,
            32,
            "RAM système nécessaire pour se passer complètement d'une carte graphique dédiée.",
        ),
        _compatibility_criterion("Ollama", findings.get("Ollama")),
        _compatibility_criterion("GGUF", findings.get("GGUF")),
    )

    verdict_emoji, verdict_headline, verdict_detail = _verdict(ram_comfortable_gib)
    return HardwareAdvice(
        parameters=parameters,
        ram_estimates=ram_estimates,
        vram_recommended=vram_recommended,
        criteria=criteria,
        ram_comfortable_gib=ram_comfortable_gib,
        verdict_emoji=verdict_emoji,
        verdict_headline=verdict_headline,
        verdict_detail=verdict_detail,
    )


def _memory_estimate(
    label: str,
    parameters: int,
    low_bytes_per_param: float,
    high_bytes_per_param: float,
) -> MemoryEstimate:
    """Convertir un nombre de paramètres en volume mémoire, marge d'exécution incluse."""
    low = int(parameters * low_bytes_per_param * _RUNTIME_OVERHEAD)
    high = int(parameters * high_bytes_per_param * _RUNTIME_OVERHEAD)
    return MemoryEstimate(label, low, max(low, high))


def _tier_for(parameters: int, tiers: tuple[tuple[float, int, int], ...]) -> tuple[int, int]:
    """Choisir le palier (minimal, confortable) correspondant à la taille du modèle."""
    billions = parameters / 1_000_000_000
    for threshold, minimum, comfortable in tiers:
        if billions <= threshold:
            return minimum, comfortable
    return tiers[-1][1] * 2, tiers[-1][2] * 2


def _tier_criterion(
    name: str,
    minimum_gib: int,
    comfortable_gib: int,
    capacity_gib: int,
    detail: str,
) -> HardwareCriterion:
    """Comparer une capacité matérielle donnée aux paliers minimal et confortable."""
    if capacity_gib >= comfortable_gib:
        status: FitStatus = "ok"
    elif capacity_gib >= minimum_gib:
        status = "warning"
    else:
        status = "no"
    return HardwareCriterion(name, status, detail)


def _compatibility_criterion(name: str, finding: CompatibilityFinding | None) -> HardwareCriterion:
    """Réutiliser un résultat de compatibilité existant comme critère matériel."""
    if finding is None:
        return HardwareCriterion(name, "unknown", "Compatibilité non évaluée.")
    return HardwareCriterion(name, _STATUS_FROM_COMPATIBILITY[finding.state], finding.reason)


def _verdict(ram_comfortable_gib: int) -> tuple[str, str, str]:
    """Rendre un verdict d'usage local lisible à partir du palier de RAM confortable."""
    if ram_comfortable_gib <= 8:
        return (
            "🟢",
            "Bon candidat pour une machine avec 8 Go RAM",
            "Le modèle quantifié tient largement dans la mémoire d'un ordinateur grand public.",
        )
    if ram_comfortable_gib <= 16:
        return (
            "🟢",
            "Bon candidat pour une machine avec 16 Go RAM",
            "Une configuration grand public récente suffit pour l'exécuter localement en version quantifiée.",
        )
    if ram_comfortable_gib <= 32:
        return (
            "🟡",
            "Nécessite au moins 32 Go RAM (ou un GPU dédié)",
            "Le modèle reste utilisable en local mais demande une configuration plus généreuse ou une carte graphique dédiée.",
        )
    if ram_comfortable_gib <= 64:
        return (
            "🟠",
            "Réservé aux configurations avec 64 Go RAM ou un GPU riche en VRAM",
            "Une machine grand public standard ne suffira pas ; un GPU dédié ou un serveur local est recommandé.",
        )
    return (
        "🔴",
        "Modèle très lourd : plutôt réservé à un serveur multi-GPU",
        "Le volume de paramètres dépasse ce qu'une machine personnelle gère raisonnablement en local.",
    )
