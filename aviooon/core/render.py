"""Funciones de renderizado 3D compartidas (GUI y scripts de demo).

Centraliza el dibujo de las aeronaves para no duplicar código entre la
ventana de simulación y la generación de GIFs de demostración.
"""
from __future__ import annotations

from typing import List

import numpy as np
from mpl_toolkits.mplot3d.art3d import Poly3DCollection


def draw_plane(
    ax,
    pos: np.ndarray,
    direction: np.ndarray,
    color: str,
    size: float = 1.2,
) -> List:
    """Dibuja un avión orientado según su dirección de vuelo.

    Devuelve la lista de artistas creados (fuselaje + alas) para poder
    eliminarlos en el siguiente fotograma.
    """
    length, width, height = size * 2, size * 0.5, size * 0.3
    vertices = np.array([
        [0, -width, -height], [0, width, -height],
        [length, width, -height], [length, -width, -height],
        [0, -width, height], [0, width, height],
        [length, width, height], [length, -width, height],
    ])
    wing_span = size * 3
    wings = np.array([
        [length * 0.5, -wing_span / 2, 0],
        [length * 0.5, wing_span / 2, 0],
        [length * 0.5, 0, 0],
    ])

    # Matriz de rotación de Rodrigues: alinea el eje X con `direction`
    z_axis = np.array([1.0, 0.0, 0.0])
    v = np.cross(z_axis, direction)
    c = float(np.dot(z_axis, direction))
    s = np.linalg.norm(v)
    if s > 1e-9:
        vx = np.array([
            [0, -v[2], v[1]],
            [v[2], 0, -v[0]],
            [-v[1], v[0], 0],
        ])
        R = np.eye(3) + vx + vx @ vx * ((1 - c) / s ** 2)
    else:
        R = np.eye(3) if c > 0 else np.diag([-1.0, 1.0, 1.0])

    rotated_vertices = (R @ vertices.T).T + pos
    rotated_wings = (R @ wings.T).T + pos

    faces = [
        rotated_vertices[[0, 1, 2, 3]],
        rotated_vertices[[4, 5, 6, 7]],
        rotated_vertices[[0, 1, 5, 4]],
        rotated_vertices[[2, 3, 7, 6]],
        rotated_vertices[[1, 2, 6, 5]],
        rotated_vertices[[0, 3, 7, 4]],
    ]
    fuselage = Poly3DCollection(
        faces, facecolors=color, linewidths=0.3, edgecolors="k", alpha=0.95,
    )
    ax.add_collection3d(fuselage)

    wing_line = ax.plot(
        [rotated_wings[0][0], rotated_wings[1][0]],
        [rotated_wings[0][1], rotated_wings[1][1]],
        [rotated_wings[0][2], rotated_wings[1][2]],
        color="black", linewidth=1.5,
    )
    return [fuselage, *wing_line]
