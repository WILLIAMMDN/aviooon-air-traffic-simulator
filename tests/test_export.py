"""Pruebas de la exportación de resultados (CSV y GIF)."""
import os
import tempfile
import unittest

import matplotlib

matplotlib.use("Agg")  # backend sin ventanas para los tests

from matplotlib import animation
from matplotlib.figure import Figure

from aviooon.core.collision import CollisionEvent
from aviooon.core.simulation import FlightMetrics
from aviooon.data.exporter import export_animation, export_metrics_csv


class TestExportMetricsCSV(unittest.TestCase):
    def test_csv_content(self):
        metrics = [
            FlightMetrics("AV-1", 100.0, 50.0, 12.0, 8.0),
            FlightMetrics("AV-2", 200.0, 90.0, 20.0, 15.0),
        ]
        collisions = [
            CollisionEvent("AV-1", "AV-2", 5.0, 2.5, None, warning=False),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = export_metrics_csv(metrics, collisions, os.path.join(tmp, "m.csv"))
            with open(path, encoding="utf-8") as f:
                content = f.read()
        self.assertIn("AV-1", content)
        self.assertIn("100.00", content)
        self.assertIn("colision", content)
        self.assertIn("5.00", content)


class TestExportAnimation(unittest.TestCase):
    def _make_animation(self):
        fig = Figure(figsize=(3, 2))
        ax = fig.add_subplot(111)
        line, = ax.plot([], [])
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)

        def update(i):
            line.set_data([0, i / 10.0], [0, i / 10.0])
            return [line]

        return animation.FuncAnimation(fig, update, frames=10)

    def test_gif_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "anim.gif")
            export_animation(self._make_animation(), path, fps=10)
            self.assertTrue(os.path.getsize(path) > 0)

    def test_unsupported_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                export_animation(
                    self._make_animation(), os.path.join(tmp, "anim.png")
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
