"""Genera la imagen de portada (social preview) para GitHub.

Diseño 2D estilo radar del simulador: las dos órbitas enfrentadas, el
punto de colisión marcado en rojo y los aviones en el instante del
impacto, con tipografía del proyecto. Tamaño 1280x640, el formato que
GitHub usa para la social preview.

Ejecutar desde la raíz del proyecto:
    python scripts/make_social_preview.py
"""
from __future__ import annotations

import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

_BG = (11, 18, 32)
_PANEL = (31, 41, 55)
_GREEN = (74, 222, 128)
_RED = (239, 68, 68)
_CYAN = (34, 211, 238)
_GRAY = (148, 163, 184)
_TEXT = (229, 231, 235)
_BLUE = (79, 195, 247)
_PINK = (240, 98, 146)

OUT_W, OUT_H = 1280, 640


def _font(size: int, bold: bool = False):
    bold_path = "C:/Windows/Fonts/segoeuib.ttf" if bold else ""
    normal_path = "C:/Windows/Fonts/segoeui.ttf"
    candidates = [bold_path, "C:/Windows/Fonts/arialbd.ttf", normal_path,
                  "C:/Windows/Fonts/arial.ttf"]
    for path in candidates:
        if path and os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _draw_plane_icon(draw: ImageDraw.ImageDraw, cx: float, cy: float,
                     angle: float, color, size: float = 26) -> None:
    """Dibuja un avión visto desde arriba, orientado por `angle` (rad)."""
    points = [(1.0, 0.0), (0.25, -0.35), (0.2, -0.85), (-0.55, -0.5),
              (-0.7, -0.75), (-1.0, -0.3), (-0.75, 0.0), (-1.0, 0.3),
              (-0.7, 0.75), (-0.55, 0.5), (0.2, 0.85), (0.25, 0.35)]
    cos, sin = math.cos(angle), math.sin(angle)
    pts = []
    for px, py in points:
        rx = px * cos - py * sin
        ry = px * sin + py * cos
        pts.append((cx + rx * size, cy + ry * size))
    draw.polygon(pts, fill=color)


def main() -> None:
    canvas = Image.new("RGB", (OUT_W, OUT_H), _BG)
    d = ImageDraw.Draw(canvas)

    # ------------------------------------------------------------------
    # Panel izquierdo: título + descripción (más oscuro, separado)
    # ------------------------------------------------------------------
    d.rectangle([0, 0, 620, OUT_H], fill=(8, 13, 24, 255))
    d.line([620, 0, 620, OUT_H], fill=_PANEL, width=1)

    title = _font(52, bold=True)
    d.text((54, 96), "AVIOOON", font=title, fill=_CYAN)

    sub = _font(26)
    d.text((54, 168), "Simulador de Tráfico Aéreo 3D", font=sub, fill=_TEXT)

    body = _font(19)
    desc = ("Define trayectorias paramétricas x(t), y(t), z(t) y observa\n"
            "el vuelo animado con detección de colisiones, alertas\n"
            "sonoras, radar 2D y exportación de resultados.")
    for i, line in enumerate(desc.splitlines()):
        d.text((54, 250 + i * 34), line, font=body, fill=_GRAY)

    feats = ["\u2022  Colisiones con marcador rojo y alarma",
             "\u2022  Contacto \u2192 preventiva \u2192 colisi\u00f3n",
             "\u2022  Radar cenital + m\u00e9tricas de vuelo",
             "\u2022  Exporta GIF / MP4 / CSV"]
    for i, f in enumerate(feats):
        d.text((54, 400 + i * 34), f, font=_font(18), fill=_TEXT)

    d.text((54, OUT_H - 58), "Python \u00b7 CustomTkinter \u00b7 Matplotlib \u00b7 SymPy",
           font=_font(17), fill=_GREEN)

    # ------------------------------------------------------------------
    # Panel derecho: escena radar 2D de la colisión
    # ------------------------------------------------------------------
    cx, cy, R = 950, 320, 230
    for r in (R, R * 0.66, R * 0.33):
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=_PANEL, width=2)
    d.line([cx - R - 40, cy, cx + R + 40, cy], fill=_PANEL, width=1)
    d.line([cx, cy - R - 40, cx, cy + R - 40], fill=_PANEL, width=1)

    # Órbitas: AV-001 = 10cos t, 10sin t  |  AV-002 = -10cos t, 10sin t
    # (colisión en t = pi/2, punto (0, 10) → abajo del centro)
    steps = 240
    for name, color in (("AV-001", _BLUE), ("AV-002", _PINK)):
        pts = []
        for k in range(steps + 1):
            t = k / steps * 2 * math.pi
            x = 10 * math.cos(t)
            y = 10 * math.sin(t)
            if name == "AV-002":
                x = -x
            pts.append((cx + x / 12 * R, cy + y / 12 * R))
        d.line(pts, fill=color, width=3)

    # Posiciones en t = pi/2 (mismo punto: colisión)
    px, py = cx, cy + R  # (0, 10) → abajo
    _draw_plane_icon(d, px, py + 18, -math.pi / 2, _BLUE)
    _draw_plane_icon(d, px, py - 18, math.pi / 2, _PINK)

    # Marcador de colisión: anillo + X roja
    ring_r = 34
    d.ellipse([px - ring_r, py - ring_r, px + ring_r, py + ring_r],
              outline=_RED, width=4)
    for s in (-1, 1):
        d.line([px - s * 18, py - 18, px + s * 18, py + 18],
               fill=_RED, width=6)

    d.text((px - 16, py + 40), "COLISI\u00d3N", font=_font(17, bold=True),
           fill=_RED)
    d.text((px - 6, py + 62), "t = 1.57 s", font=_font(14), fill=_GRAY)

    # Etiquetas de aviones
    d.text((cx - 20, cy - R - 48), "AV-001", font=_font(15, bold=True),
           fill=_BLUE)
    d.text((cx + 26, cy - R - 48), "AV-002", font=_font(15, bold=True),
           fill=_PINK)
    # Flechas de aproximación
    for x, y, col in ((cx - R - 60, cy - 8, _BLUE), (cx + R + 10, cy + 8, _PINK)):
        d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=col)

    # Leyenda inferior derecha
    ly = OUT_H - 46
    d.ellipse([cx - R - 30, ly - 7, cx - R - 12, ly + 11], fill=_BLUE)
    d.text((cx - R, ly - 12), "AV-001", font=_font(16), fill=_TEXT)
    d.ellipse([cx - R + 90, ly - 7, cx - R + 108, ly + 11], fill=_PINK)
    d.text((cx - R + 120, ly - 12), "AV-002", font=_font(16), fill=_TEXT)
    d.text((cx + R - 150, ly - 12), "\u00d7 colisi\u00f3n", font=_font(16),
           fill=_RED)

    # ------------------------------------------------------------------
    # Guardar
    # ------------------------------------------------------------------
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "assets", "social-preview.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    canvas.save(out, optimize=True)
    print(f"Portada generada: {os.path.abspath(out)}  "
          f"({canvas.size[0]}x{canvas.size[1]}, "
          f"{os.path.getsize(out) // 1024} KB)")


if __name__ == "__main__":
    main()
