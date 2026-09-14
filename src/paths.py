"""Emplacement des données, configurable pour une installation système."""

import os
from pathlib import Path


def data_directory() -> Path:
    """Conserver le chemin de développement sauf si le lanceur le remplace."""
    return Path(os.environ.get("HF_EXPLORER_DATA_DIR") or Path(__file__).resolve().parents[1] / "data")
