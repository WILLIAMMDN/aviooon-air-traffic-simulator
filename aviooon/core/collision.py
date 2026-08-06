"""Detección de colisiones entre pares de trayectorias.

Calcula la distancia mínima entre cada par de aeronaves a lo largo de su
intervalo temporal común y clasifica el resultado como colisión crítica
o alerta preventiva según los umbrales de configuración.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

import numpy as np

from .trajectory import Trajectory

_RESHAPE = 1200  # resolución de la malla temporal común para medir distancias


@dataclass
class CollisionEvent:
    """Instante en el que dos aeronaves se acercan por debajo del umbral."""

    a: str
    b: str
    t: float
    distance: float
    position: np.ndarray
    warning: bool = False  # True = preventiva (cerca), False = colisión crítica

    def describe(self) -> str:
        kind = "⚠ PREVENTIVA" if self.warning else "🚨 COLISIÓN"
        return (
            f"{kind}: {self.a} ↔ {self.b} a {self.distance:.2f} u "
            f"en t={self.t:.1f}s"
        )


def _min_distance(ta: Trajectory, tb: Trajectory) -> Tuple[float, float]:
    """Distancia mínima entre dos trayectorias y el tiempo donde ocurre.

    Ambas se remuestrean sobre el intervalo temporal común
    [0, min(duration_a, duration_b)].
    """
    t_end = min(ta.duration, tb.duration)
    if t_end <= 0:
        return float("inf"), 0.0

    t_grid = np.linspace(0.0, t_end, _RESHAPE)
    ax = np.interp(t_grid, ta.t, ta.x)
    ay = np.interp(t_grid, ta.t, ta.y)
    az = np.interp(t_grid, ta.t, ta.z)
    bx = np.interp(t_grid, tb.t, tb.x)
    by = np.interp(t_grid, tb.t, tb.y)
    bz = np.interp(t_grid, tb.t, tb.z)

    dist = np.sqrt((ax - bx) ** 2 + (ay - by) ** 2 + (az - bz) ** 2)
    idx = int(np.argmin(dist))
    return float(dist[idx]), float(t_grid[idx])


def detect_collisions(
    trajectories: List[Trajectory],
    collision_threshold: float,
    warning_threshold: float,
) -> List[CollisionEvent]:
    """Detecta colisiones entre todos los pares de aeronaves.

    Los eventos se devuelven ordenados cronológicamente.
    """
    events: List[CollisionEvent] = []
    for i in range(len(trajectories)):
        for j in range(i + 1, len(trajectories)):
            distance, t = _min_distance(trajectories[i], trajectories[j])
            if distance < collision_threshold:
                events.append(
                    CollisionEvent(
                        a=trajectories[i].name,
                        b=trajectories[j].name,
                        t=t,
                        distance=distance,
                        position=position_at(trajectories[i], t),
                        warning=False,
                    )
                )
            elif distance < warning_threshold:
                events.append(
                    CollisionEvent(
                        a=trajectories[i].name,
                        b=trajectories[j].name,
                        t=t,
                        distance=distance,
                        position=position_at(trajectories[i], t),
                        warning=True,
                    )
                )
    events.sort(key=lambda e: e.t)
    return events


def position_at(tr: Trajectory, t: float) -> np.ndarray:
    """Posición interpolada de una trayectoria en el instante t."""
    return np.array(
        [
            float(np.interp(t, tr.t, tr.x)),
            float(np.interp(t, tr.t, tr.y)),
            float(np.interp(t, tr.t, tr.z)),
        ]
    )


def pair_distances_at(
    trajectories: List[Trajectory], t: float
) -> List[Tuple[int, int, float]]:
    """Distancias actuales entre todos los pares de trayectorias en t.

    Devuelve una lista de ``(i, j, distancia)`` con ``i < j``, calculada
    en tiempo real para el monitoreo de proximidad durante la animación.
    """
    positions = [position_at(tr, t) for tr in trajectories]
    pairs: List[Tuple[int, int, float]] = []
    for i in range(len(positions)):
        for j in range(i + 1, len(positions)):
            d = float(np.linalg.norm(positions[i] - positions[j]))
            pairs.append((i, j, d))
    return pairs
