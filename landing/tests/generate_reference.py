"""Régénère python-reference.json à partir du vrai calculateur Python.

Usage (depuis la racine du dépôt) : .venv/bin/python landing/tests/generate_reference.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.resource_calculator import HardwareProfile, calculate_resources

cases = []
for params_b in (0.6, 1.0, 3.0, 7.0, 14.8, 32.0, 70.0, 120.0):
    for ram, vram in ((0, 0), (8, 0), (16, 0), (16, 8), (32, 12), (64, 24), (128, 0), (16, 24), (0, 16)):
        parameters = int(round(params_b * 1e9))
        result = calculate_resources(parameters, HardwareProfile(ram_gib=ram, vram_gib=vram))
        cases.append({
            "parametersBillions": params_b,
            "parameters": parameters,
            "ramGib": ram,
            "vramGib": vram,
            "precisions": [
                {"label": p.label, "status": p.status, "memoryBytes": p.memory_bytes, "path": p.path}
                for p in result.precisions
            ],
            "best": result.estimate.precision_label,
            "path": result.estimate.execution_path,
            "tpsLow": result.estimate.speed_tokens_per_second_low,
            "tpsHigh": result.estimate.speed_tokens_per_second_high,
        })

target = Path(__file__).with_name("python-reference.json")
target.write_text(json.dumps({"generatedBy": "src.resource_calculator.calculate_resources", "cases": cases}, indent=1))
print(f"{len(cases)} cas écrits dans {target}")
