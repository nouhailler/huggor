"""Calculateur de ressources : confronter un modèle à la machine déclarée par l'utilisateur.

Toutes les estimations (mémoire, vitesse, contexte) sont des ordres de grandeur théoriques
fondés sur des repères génériques (bande passante mémoire, tailles de quantification usuelles).
Elles ne remplacent pas un test réel : le nom du GPU/CPU renseigné n'est pas utilisé dans le
calcul, il sert uniquement de repère pour l'utilisateur.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

from src.model_analysis import config_value

FitStatus = Literal["ok", "warning", "no"]
ExecutionPath = Literal["gpu", "cpu", "none"]

_GIB = 1024**3
_RUNTIME_OVERHEAD = 1.1  # Marge pour les buffers d'exécution, hors cache KV (compté séparément).
_COMFORTABLE_MARGIN = 0.85  # Fraction de la mémoire totale jugée utilisable sans risque de saturation.
_GPU_BANDWIDTH_GBPS = 300.0  # Repère générique pour une carte graphique dédiée récente.
_CPU_BANDWIDTH_GBPS = 40.0  # Repère générique pour de la RAM double canal grand public.
_KV_CACHE_BYTES_PER_ELEMENT = 2.0  # Cache KV en FP16, choix par défaut usuel (llama.cpp, Transformers).
_DEFAULT_MAX_CONTEXT_TOKENS = 131_072  # Plafond de sécurité si le contexte d'entraînement est inconnu.

# Précisions évaluées, de la plus fidèle à la plus compressée, avec leur poids approximatif en
# octets par paramètre (Q8/Q6/Q4_K_M reprennent les tailles usuelles des quantifications GGUF).
_PRECISIONS: tuple[tuple[str, float], ...] = (
    ("FP32", 4.0),
    ("FP16", 2.0),
    ("INT8", 1.0),
    ("Q8", 1.0625),
    ("Q6", 0.8203),
    ("Q4_K_M", 0.6094),
)


@dataclass(frozen=True, slots=True)
class HardwareProfile:
    """Machine déclarée par l'utilisateur pour le calcul de ressources."""

    ram_gib: float
    vram_gib: float
    gpu_name: str = ""
    cpu_name: str = ""

    def __post_init__(self) -> None:
        """Refuser une machine dont la mémoire déclarée serait négative."""
        if self.ram_gib < 0 or self.vram_gib < 0:
            raise ValueError("La RAM et la VRAM ne peuvent pas être négatives.")


@dataclass(frozen=True, slots=True)
class PrecisionFit:
    """Statut d'une précision donnée sur la machine déclarée."""

    label: str
    status: FitStatus
    memory_bytes: int
    path: ExecutionPath

    def to_dict(self) -> dict[str, Any]:
        """Convertir le résultat en dictionnaire sérialisable."""
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ResourceEstimate:
    """Estimation détaillée pour la meilleure précision encore jouable."""

    precision_label: str | None
    execution_path: ExecutionPath
    memory_bytes: int | None
    speed_label: str
    speed_tokens_per_second_low: float | None
    speed_tokens_per_second_high: float | None
    max_context_tokens: int | None
    context_note: str

    def to_dict(self) -> dict[str, Any]:
        """Convertir l'estimation en dictionnaire sérialisable."""
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ResourceCalculation:
    """Résultat complet du calculateur de ressources pour un modèle et une machine."""

    parameters: int | None
    hardware: HardwareProfile
    precisions: tuple[PrecisionFit, ...]
    estimate: ResourceEstimate

    def to_dict(self) -> dict[str, Any]:
        """Convertir le résultat complet en dictionnaire sérialisable."""
        return {
            "parameters": self.parameters,
            "hardware": asdict(self.hardware),
            "precisions": [item.to_dict() for item in self.precisions],
            "estimate": self.estimate.to_dict(),
        }


def calculate_resources(
    parameters: int | None,
    hardware: HardwareProfile,
    config: dict[str, Any] | None = None,
    context_length: int | None = None,
) -> ResourceCalculation:
    """Confronter un nombre de paramètres au matériel déclaré, précision par précision."""
    if not parameters or parameters <= 0:
        empty_estimate = ResourceEstimate(
            precision_label=None,
            execution_path="none",
            memory_bytes=None,
            speed_label="⚪ Non estimable : nombre de paramètres inconnu.",
            speed_tokens_per_second_low=None,
            speed_tokens_per_second_high=None,
            max_context_tokens=None,
            context_note="Le nombre de paramètres n'est pas renseigné par ce dépôt.",
        )
        return ResourceCalculation(None, hardware, (), empty_estimate)

    ram_bytes = hardware.ram_gib * _GIB
    vram_bytes = hardware.vram_gib * _GIB

    precisions = tuple(
        _fit_precision(label, bytes_per_param, parameters, ram_bytes, vram_bytes)
        for label, bytes_per_param in _PRECISIONS
    )

    best = _select_best(precisions)
    estimate = _estimate_for(best, hardware, config or {}, context_length)
    return ResourceCalculation(parameters, hardware, precisions, estimate)


def _fit_precision(
    label: str,
    bytes_per_param: float,
    parameters: int,
    ram_bytes: float,
    vram_bytes: float,
) -> PrecisionFit:
    """Déterminer si une précision tient sur la machine, et sur quelle mémoire."""
    memory_bytes = int(parameters * bytes_per_param * _RUNTIME_OVERHEAD)

    if vram_bytes > 0 and memory_bytes <= vram_bytes * _COMFORTABLE_MARGIN:
        return PrecisionFit(label, "ok", memory_bytes, "gpu")
    if ram_bytes > 0 and memory_bytes <= ram_bytes * _COMFORTABLE_MARGIN:
        return PrecisionFit(label, "ok", memory_bytes, "cpu")
    if vram_bytes > 0 and memory_bytes <= vram_bytes:
        return PrecisionFit(label, "warning", memory_bytes, "gpu")
    if ram_bytes > 0 and memory_bytes <= ram_bytes:
        return PrecisionFit(label, "warning", memory_bytes, "cpu")
    return PrecisionFit(label, "no", memory_bytes, "none")


def _select_best(precisions: tuple[PrecisionFit, ...]) -> PrecisionFit | None:
    """Choisir la meilleure qualité encore jouable, à défaut la moins mauvaise."""
    for status in ("ok", "warning"):
        for item in precisions:
            if item.status == status:
                return item
    return None


def _estimate_for(
    best: PrecisionFit | None,
    hardware: HardwareProfile,
    config: dict[str, Any],
    context_length: int | None,
) -> ResourceEstimate:
    """Construire l'estimation mémoire, vitesse et contexte pour la précision retenue."""
    if best is None or best.path == "none":
        return ResourceEstimate(
            precision_label=None,
            execution_path="none",
            memory_bytes=None,
            speed_label="🔴 Impraticable : aucune précision ne tient sur cette configuration.",
            speed_tokens_per_second_low=None,
            speed_tokens_per_second_high=None,
            max_context_tokens=None,
            context_note=(
                "Aucune mémoire disponible n'est suffisante, même pour la version la plus compressée."
            ),
        )

    bandwidth_gbps = _GPU_BANDWIDTH_GBPS if best.path == "gpu" else _CPU_BANDWIDTH_GBPS
    tokens_per_second = (bandwidth_gbps * 1_000_000_000) / best.memory_bytes
    speed_label = _speed_label(tokens_per_second, best.path)

    capacity_bytes = hardware.vram_gib * _GIB if best.path == "gpu" else hardware.ram_gib * _GIB
    leftover_bytes = capacity_bytes * _COMFORTABLE_MARGIN - best.memory_bytes
    max_context_tokens, context_note = _estimate_context(leftover_bytes, config, context_length)

    return ResourceEstimate(
        precision_label=best.label,
        execution_path=best.path,
        memory_bytes=best.memory_bytes,
        speed_label=speed_label,
        speed_tokens_per_second_low=round(tokens_per_second * 0.6, 1),
        speed_tokens_per_second_high=round(tokens_per_second * 1.4, 1),
        max_context_tokens=max_context_tokens,
        context_note=context_note,
    )


def _speed_label(tokens_per_second: float, path: ExecutionPath) -> str:
    """Traduire un débit approché en appréciation qualitative prudente."""
    location = "GPU" if path == "gpu" else "CPU"
    if tokens_per_second >= 15:
        return f"🟢 Fluide sur {location} (usage interactif confortable)"
    if tokens_per_second >= 5:
        return f"🟡 Correct sur {location} (léger délai perceptible)"
    if tokens_per_second >= 1:
        return f"🟠 Lent sur {location} (utilisable mais peu confortable)"
    return f"🔴 Très lent sur {location} (peu adapté à un usage interactif)"


def _estimate_context(
    leftover_bytes: float,
    config: dict[str, Any],
    context_length: int | None,
) -> tuple[int | None, str]:
    """Estimer le contexte réaliste à partir du cache KV, quand l'architecture le permet."""
    if leftover_bytes <= 0:
        return 0, "Aucune marge mémoire ne reste après le chargement des poids : contexte quasiment nul."

    num_layers = config_value(config, "num_hidden_layers", "n_layer", "num_layers")
    hidden_size = config_value(config, "hidden_size", "n_embd", "d_model")
    num_heads = config_value(config, "num_attention_heads", "n_head")
    num_kv_heads = config_value(config, "num_key_value_heads") or num_heads

    if not (num_layers and hidden_size and num_heads):
        return None, "Architecture non standard : le contexte n'est pas calculable précisément à partir du cache KV."

    try:
        head_dim = float(hidden_size) / float(num_heads)
        kv_cache_bytes_per_token = (
            2 * float(num_layers) * float(num_kv_heads) * head_dim * _KV_CACHE_BYTES_PER_ELEMENT
        )
        if kv_cache_bytes_per_token <= 0:
            raise ValueError
    except (TypeError, ValueError, ZeroDivisionError):
        return None, "Architecture non standard : le contexte n'est pas calculable précisément à partir du cache KV."

    estimated_tokens = int(leftover_bytes / kv_cache_bytes_per_token)
    ceiling = context_length or _DEFAULT_MAX_CONTEXT_TOKENS
    capped_tokens = max(0, min(estimated_tokens, ceiling))
    note = (
        "Estimation fondée sur un cache KV en FP16, plafonnée au contexte d'entraînement du modèle."
        if capped_tokens < estimated_tokens
        else "Estimation fondée sur un cache KV en FP16 ; un moteur qui le quantifie peut faire mieux."
    )
    return capped_tokens, note
