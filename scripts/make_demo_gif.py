"""Genera el GIF de demostración para el README del proyecto.

Escenario: dos aviones orbitan en direcciones opuestas sobre la misma
circunferencia y COLISIONAN a mitad de vuelo. El GIF muestra las zonas
de proximidad (contacto -> preventiva -> colision) con su marcador rojo.

Ejecutar desde la raíz del proyecto:
    python scripts/make_demo_gif.py
"""
from __future__ import annotations

import os
import sys

# Permite importar el paquete aviooon desde cualquier cwd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib
matplotlib.use("Agg")  # sin ventanas

import numpy as np
from matplotlib import animation
from matplotlib.figure import Figure

from aviooon.config import (
    COLLISION_THRESHOLD,
    DETECTION_THRESHOLD,
    SIM_FRAMES,
    WARNING_THRESHOLD,
)
from aviooon.core.aircraft import Aircraft
from aviooon.core.collision import pair_distances_at, position_at
from aviooon.core.render import draw_plane
from aviooon.core.simulation import Simulation

_BG = "#111827"
_PANEL = "#1f2937"
_GREEN = "#4ade80"
_YELLOW = "#facc15"
_RED = "#ef4444"
_CYAN = "#22d3ee"
_GRAY = "#94a3b8"

FPS = 15

# Recorte: solo la ventana alrededor de la colisión (evita que el GIF
# incluya la órbita completa, que no aporta y triplica el peso).
# La colisión ocurre en t = pi/2; mostramos el acercamiento y la separación.
# En t=0.3 la distancia es ~19 u, y el contacto (<12 u) empieza en t≈0.93:
# así el GIF muestra la secuencia completa contacto → preventiva → colisión.
WINDOW_START = 0.3
WINDOW_END = 2.6


def build_scenario():
    """Dos aviones en órbitas opuestas: colisión en t = pi/2."""
    lap = 2 * np.pi
    return [
        Aircraft("AV-001", "10*cos(t)", "10*sin(t)", "3*t", lap, "#4FC3F7"),
        Aircraft("AV-002", "10*cos(3.1416-t)", "10*sin(3.1416-t)", "3*t",
                 lap, "#F06292"),
    ]


def _setup_axes(ax, sim: Simulation):
    xs = np.concatenate([tr.x for tr in sim.trajectories])
    ys = np.concatenate([tr.y for tr in sim.trajectories])
    zs = np.concatenate([tr.z for tr in sim.trajectories])

    pad = max(2.0, 0.15 * max(xs.max() - xs.min(), ys.max() - ys.min(), 1))
    ax.set_xlim(xs.min() - pad, xs.max() + pad)
    ax.set_ylim(ys.min() - pad, ys.max() + pad)
    ax.set_zlim(0, max(zs.max() + pad, 5))
    ax.set_title("AVIOOON — Simulador de Tráfico Aéreo 3D",
                 color="#e5e7eb", fontsize=12)
    ax.set_xlabel("X", color=_GRAY)
    ax.set_ylabel("Y", color=_GRAY)
    ax.set_zlabel("Z", color=_GRAY)
    ax.tick_params(colors=_GRAY)
    ax.set_facecolor(_BG)

    for tr in sim.trajectories:
        ax.plot(tr.x, tr.y, tr.z, linestyle="--", alpha=0.45,
                color=tr.color, label=tr.name)
    ax.legend(loc="upper left", fontsize=8, facecolor=_PANEL,
              edgecolor="#374151", labelcolor="#e5e7eb")


def main() -> None:
    sim = Simulation(build_scenario(), frames=SIM_FRAMES)

    # Solo los fotogramas necesarios para la duración a FPS
    n_frames = max(30, int(round((WINDOW_END - WINDOW_START) * FPS)))

    fig = Figure(figsize=(6.5, 5.6), dpi=68, facecolor=_BG)
    ax = fig.add_subplot(111, projection="3d")
    _setup_axes(ax, sim)

    status = ax.text2D(0.02, 0.95, "", transform=ax.transAxes,
                       color=_GREEN, fontsize=11, fontweight="bold")
    plane_artists: list = []
    markers: list = []
    marked = set()

    def update(frame: int):
        t = WINDOW_START + frame / n_frames * (WINDOW_END - WINDOW_START)

        for artist in plane_artists:
            artist.remove()
        plane_artists.clear()

        for tr in sim.trajectories:
            pos = position_at(tr, t)
            nxt = position_at(tr, min(t + 0.05, tr.duration))
            direction = nxt - pos
            norm = np.linalg.norm(direction)
            if norm > 1e-9:
                direction = direction / norm
            else:
                direction = np.array([1.0, 0.0, 0.0])
            plane_artists.extend(draw_plane(ax, pos, direction, tr.color))

        pairs = pair_distances_at(sim.trajectories, t)
        if pairs:
            i, j, d = min(pairs, key=lambda p: p[2])
            if d < COLLISION_THRESHOLD and (i, j) not in marked:
                marked.add((i, j))
                mid = (position_at(sim.trajectories[i], t)
                       + position_at(sim.trajectories[j], t)) / 2
                markers.append(ax.scatter(
                    [mid[0]], [mid[1]], [mid[2]], s=190, marker="X",
                    color=_RED, depthshade=False, zorder=10,
                ))
                status.set_text(f"COLISION a {d:.1f} u  (t={t:.1f}s)")
                status.set_color(_RED)
            elif d < WARNING_THRESHOLD:
                status.set_text(f"PREVENTIVA: {d:.1f} u")
                status.set_color(_YELLOW)
            elif d < DETECTION_THRESHOLD:
                status.set_text(f"CONTACTO: {d:.1f} u")
                status.set_color(_CYAN)
            else:
                status.set_text(f"Distancia: {d:.1f} u")
                status.set_color(_GREEN)
        return []

    ani = animation.FuncAnimation(fig, update, frames=n_frames, interval=40)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "assets", "demo.gif")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    ani.save(out, writer="pillow", fps=FPS)

    # Optimización: recompresión con Pillow conservando los fotogramas
    from PIL import Image

    with Image.open(out) as gif:
        frames = [gif.seek(i) or gif.convert("RGB") for i in range(gif.n_frames)]
    frames[0].save(out, save_all=True, append_images=frames[1:],
                   duration=1000 // FPS, loop=0, optimize=True,
                   disposal=2)

    size_kb = os.path.getsize(out) // 1024
    print(f"GIF generado: {os.path.abspath(out)}  ({size_kb} KB)")


if __name__ == "__main__":
    main()
