"""Modelo de datos de una aeronave.

Una aeronave queda definida por una trayectoria paramétrica
r(t) = (x(t), y(t), z(t)) donde cada componente es una expresión
matemática escrita como texto (p. ej. ``"10*cos(t)"``).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from matplotlib.colors import is_color_like


@dataclass
class Aircraft:
    """Representa un avión con su trayectoria paramétrica."""

    name: str
    x: str          # expresión de x(t)
    y: str          # expresión de y(t)
    z: str          # expresión de z(t)
    duration: float = 15.0
    color: str = "#4FC3F7"

    def to_dict(self) -> dict:
        """Serializa la aeronave a diccionario (para JSON)."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Aircraft":
        """Reconstruye una aeronave desde diccionario (JSON).

        Soporta el formato legado con la clave ``tiempo``.
        """
        return cls(
            name=str(data.get("name", "Avión")),
            x=str(data.get("x", "10*cos(t)")),
            y=str(data.get("y", "10*sin(t)")),
            z=str(data.get("z", "t")),
            duration=float(data.get("duration") or data.get("tiempo") or 15.0),
            color=str(data.get("color", "#4FC3F7")),
        )

    def validate(self) -> None:
        """Valida los campos básicos; lanza ValueError si algo falla."""
        if not self.name.strip():
            raise ValueError("El nombre del avión no puede estar vacío.")
        if self.duration <= 0:
            raise ValueError(f"El tiempo de '{self.name}' debe ser mayor que 0.")
        for comp, label in ((self.x, "x(t)"), (self.y, "y(t)"), (self.z, "z(t)")):
            if not comp.strip():
                raise ValueError(f"La función {label} de '{self.name}' está vacía.")
        if not is_color_like(self.color):
            raise ValueError(
                f"El color '{self.color}' de '{self.name}' no es un color válido."
            )
