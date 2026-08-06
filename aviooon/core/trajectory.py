"""Evaluación numérica de trayectorias paramétricas.

Convierte expresiones matemáticas escritas como texto (SymPy) en
funciones evaluables con NumPy y las muestrea en una malla temporal.
Incluye validación de errores y de valores no finitos.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import sympy as sp

from .aircraft import Aircraft


class TrajectoryError(ValueError):
    """Error al parsear o evaluar una trayectoria."""


@dataclass
class Trajectory:
    """Trayectoria muestreada numéricamente."""

    name: str
    color: str
    t: np.ndarray
    x: np.ndarray
    y: np.ndarray
    z: np.ndarray

    @property
    def position(self) -> np.ndarray:
        """Posiciones como arreglo (N, 3)."""
        return np.stack([self.x, self.y, self.z], axis=-1)

    @property
    def duration(self) -> float:
        return float(self.t[-1])


def _lambdify(expr_text: str, symbol: sp.Symbol, label: str):
    """Convierte texto en función numérica, con error legible.

    ``lambdify`` devuelve la constante directamente (no una función)
    cuando la expresión no depende de ``t`` (p. ej. ``"0"``); en ese
    caso se envuelve en una función que repite el valor.
    """
    try:
        expr = sp.sympify(expr_text)
    except (sp.SympifyError, SyntaxError, TypeError) as exc:
        raise TrajectoryError(
            f"Función inválida en {label}: '{expr_text}'"
        ) from exc

    raw = sp.lambdify(symbol, expr, "numpy")

    def _safe(*args) -> np.ndarray:
        """Evalúa y normaliza el resultado a la forma de la entrada.

        ``lambdify`` de una constante (p. ej. ``"5"``) devuelve un
        escalar en vez de un arreglo; aquí se repite sobre ``t_vals``.
        También convierte errores por valores complejos o no numéricos
        en ``TrajectoryError`` legibles.
        """
        result = raw(*args)
        if np.ndim(result) == 0:
            shape = np.shape(args[0]) if args else ()
            return np.full(shape, result, dtype=float)
        try:
            return np.asarray(result, dtype=float)
        except (TypeError, ValueError) as exc:
            raise TrajectoryError(
                f"{label} produce valores complejos o no numéricos: {exc}"
            ) from exc

    return _safe


def sample(aircraft: Aircraft, frames: int = 500) -> Trajectory:
    """Muestrea la trayectoria de una aeronave en una malla uniforme.

    Raises:
        TrajectoryError: si la expresión no se puede evaluar o la
            trayectoria produce valores no finitos (p. ej. divisiones
            entre cero dentro del intervalo).
    """
    t = sp.Symbol("t")
    fx = _lambdify(aircraft.x, t, f"x(t) de '{aircraft.name}'")
    fy = _lambdify(aircraft.y, t, f"y(t) de '{aircraft.name}'")
    fz = _lambdify(aircraft.z, t, f"z(t) de '{aircraft.name}'")

    t_vals = np.linspace(0.0, float(aircraft.duration), int(frames))
    with np.errstate(all="ignore"):
        x = np.asarray(fx(t_vals), dtype=float)
        y = np.asarray(fy(t_vals), dtype=float)
        z = np.asarray(fz(t_vals), dtype=float)

    finite = np.isfinite(x) & np.isfinite(y) & np.isfinite(z)
    if not bool(finite.all()):
        idx = int(np.argmax(~finite))
        raise TrajectoryError(
            f"La trayectoria de '{aircraft.name}' produce valores no "
            f"finitos en t ≈ {t_vals[idx]:.2f}s. Revisa divisiones entre "
            f"cero o raíces de negativos en tus funciones."
        )

    return Trajectory(
        name=aircraft.name,
        color=aircraft.color,
        t=t_vals,
        x=x,
        y=y,
        z=z,
    )
