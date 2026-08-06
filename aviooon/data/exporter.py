"""Exportación de resultados.

Permite guardar las métricas de vuelo y las alertas en CSV, y exportar
la animación a GIF (siempre disponible) o MP4 (requiere imageio-ffmpeg).
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import List

from ..core.collision import CollisionEvent
from ..core.simulation import FlightMetrics

_CSV_COLUMNS = [
    "avion", "distancia_u", "altitud_max_u", "vel_max_u_s", "vel_media_u_s",
]


def export_metrics_csv(
    metrics: List[FlightMetrics],
    collisions: List[CollisionEvent],
    path: str | Path,
) -> Path:
    """Guarda métricas y alertas de colisión en un archivo CSV."""
    path = Path(path)
    # utf-8-sig: incluye BOM para que Excel muestre los acentos correctamente.
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["MÉTRICAS DE VUELO"])
        writer.writerow(_CSV_COLUMNS)
        for m in metrics:
            writer.writerow([
                m.name,
                f"{m.distance:.2f}",
                f"{m.max_altitude:.2f}",
                f"{m.max_speed:.2f}",
                f"{m.mean_speed:.2f}",
            ])
        writer.writerow([])
        writer.writerow(["ALERTAS DE COLISIÓN"])
        writer.writerow(["tipo", "avion_a", "avion_b", "tiempo_s", "distancia_u"])
        for c in collisions:
            writer.writerow([
                "preventiva" if c.warning else "colision",
                c.a,
                c.b,
                f"{c.t:.2f}",
                f"{c.distance:.2f}",
            ])
    return path


def export_animation(ani, path: str | Path, fps: int = 20) -> Path:
    """Guarda la animación según la extensión del archivo.

    - ``.gif``  → usa Pillow (siempre disponible)
    - ``.mp4``  → usa ffmpeg; requiere ``pip install imageio-ffmpeg``

    Raises:
        RuntimeError: si se pide MP4 sin tener ffmpeg disponible.
    """
    path = Path(path)
    ext = path.suffix.lower()

    if ext == ".mp4":
        try:
            import imageio_ffmpeg
        except ImportError as exc:
            raise RuntimeError(
                "Para exportar MP4 instala primero:  pip install imageio-ffmpeg"
            ) from exc
        import matplotlib

        matplotlib.rcParams["animation.ffmpeg_path"] = (
            imageio_ffmpeg.get_ffmpeg_exe()
        )
        writer = "ffmpeg"
    elif ext == ".gif":
        writer = "pillow"
    else:
        raise ValueError(
            f"Formato no soportado: '{ext}' (usa .gif o .mp4)."
        )

    ani.save(str(path), writer=writer, fps=fps)
    return path
