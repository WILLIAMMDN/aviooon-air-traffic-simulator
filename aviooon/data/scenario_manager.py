"""Gestión de escenarios: guardado, carga y presets de ejemplo.

Un escenario es una lista de aeronaves serializadas a JSON.
Los presets permiten cargar configuraciones interesantes con un clic.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List

from ..core.aircraft import Aircraft

# Carpeta de escenarios por defecto: <proyecto>/scenarios
DEFAULT_SCENARIO_DIR = Path(__file__).resolve().parents[2] / "scenarios"

# ----------------------------------------------------------------------
# Presets: configuraciones de ejemplo listas para simular
# ----------------------------------------------------------------------
PRESETS: dict = {
    "Hélice ascendente": [
        Aircraft("HE-001", "10*cos(t)", "10*sin(t)", "2*t", 15, "#4FC3F7"),
    ],
    "Lissajous": [
        Aircraft("LJ-001", "8*sin(2*t)", "8*sin(3*t)", "1.5*t", 15, "#FFD54F"),
    ],
    "Cruce frontal (colisión)": [
        Aircraft("FR-001", "t", "0", "5", 15, "#4FC3F7"),
        Aircraft("FR-002", "t", "t", "5", 15, "#F06292"),
    ],
    "Órbitas cercanas (colisión)": [
        Aircraft("OR-001", "10*cos(t)", "10*sin(t)", "t", 15, "#4FC3F7"),
        Aircraft("OR-002", "10*cos(t+0.2)", "10*sin(t+0.2)", "t", 15, "#F06292"),
    ],
    "Dos círculos opuestos": [
        Aircraft("OP-001", "10*cos(t)", "10*sin(t)", "t", 15, "#4FC3F7"),
        Aircraft("OP-002", "-10*cos(t)", "-10*sin(t)", "t", 15, "#F06292"),
    ],
}

# ----------------------------------------------------------------------
def save_scenario(aircrafts: List[Aircraft], path: str | Path | None = None) -> Path:
    """Guarda una lista de aeronaves en un archivo JSON."""
    path = Path(path) if path else DEFAULT_SCENARIO_DIR / "escenario.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [a.to_dict() for a in aircrafts]
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return path


def load_scenario(path: str | Path) -> List[Aircraft]:
    """Carga una lista de aeronaves desde un archivo JSON."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"El escenario '{path}' no es una lista de aeronaves.")
    return [Aircraft.from_dict(item) for item in data]


def build_preset(name: str) -> List[Aircraft]:
    """Devuelve una copia del preset indicado (None si no existe)."""
    preset = PRESETS.get(name)
    if preset is None:
        return []
    return [Aircraft.from_dict(a.to_dict()) for a in preset]
