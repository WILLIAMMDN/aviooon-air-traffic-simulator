"""Motor de simulación.

Orquesta el muestreo de trayectorias, la detección de colisiones y el
cálculo de métricas de vuelo. Es independiente de la interfaz gráfica,
por lo que también puede usarse desde consola o tests.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np

from ..config import (
    COLLISION_THRESHOLD,
    SIM_FRAMES,
    WARNING_THRESHOLD,
)
from .aircraft import Aircraft
from .collision import CollisionEvent, detect_collisions
from .trajectory import Trajectory, sample


@dataclass
class FlightMetrics:
    """Métricas calculadas para un vuelo."""

    name: str
    distance: float        # longitud de arco recorrida (u)
    max_altitude: float    # altitud máxima (u)
    max_speed: float       # velocidad máxima (u/s)
    mean_speed: float      # velocidad media (u/s)


class Simulation:
    """Simulación completa de un conjunto de aeronaves."""

    def __init__(
        self,
        aircrafts: List[Aircraft],
        frames: int = SIM_FRAMES,
        collision_threshold: float = COLLISION_THRESHOLD,
        warning_threshold: float = WARNING_THRESHOLD,
    ):
        self.aircrafts = list(aircrafts)
        self.frames = frames
        self.collision_threshold = collision_threshold
        self.warning_threshold = warning_threshold

        self.trajectories: List[Trajectory] = []
        self.collisions: List[CollisionEvent] = []
        self.metrics: List[FlightMetrics] = []
        self.run()

    # ------------------------------------------------------------------
    def run(self) -> None:
        """Ejecuta (o re-ejecuta) todos los cálculos de la simulación."""
        self.trajectories = [sample(a, self.frames) for a in self.aircrafts]
        self.collisions = detect_collisions(
            self.trajectories, self.collision_threshold, self.warning_threshold
        )
        self.metrics = [self._flight_metrics(tr) for tr in self.trajectories]

    # ------------------------------------------------------------------
    @property
    def duration(self) -> float:
        """Duración total (la mayor de las trayectorias)."""
        return max((tr.duration for tr in self.trajectories), default=0.0)

    @property
    def critical_collisions(self) -> List[CollisionEvent]:
        return [e for e in self.collisions if not e.warning]

    @property
    def has_collisions(self) -> bool:
        return bool(self.critical_collisions)

    # ------------------------------------------------------------------
    def _flight_metrics(self, tr: Trajectory) -> FlightMetrics:
        dt = np.diff(tr.t)
        vel = np.linalg.norm(np.diff(tr.position, axis=0), axis=1) / dt
        arc_length = float(np.sum(vel * dt))
        return FlightMetrics(
            name=tr.name,
            distance=arc_length,
            max_altitude=float(np.max(tr.z)) if tr.z.size else 0.0,
            max_speed=float(np.max(vel)) if vel.size else 0.0,
            mean_speed=float(np.mean(vel)) if vel.size else 0.0,
        )
