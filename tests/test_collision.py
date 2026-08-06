"""Pruebas unitarias del motor de simulación y detección de colisiones.

Ejecutar desde la raíz del proyecto:
    python -m unittest discover -s tests -v
"""
import os
import tempfile
import unittest

import numpy as np

from aviooon.core.aircraft import Aircraft
from aviooon.core.simulation import Simulation
from aviooon.core.trajectory import TrajectoryError, sample


class TestTrajectory(unittest.TestCase):
    def test_circle_sample(self):
        """Una circunferencia de radio 10 se muestra correctamente."""
        tr = sample(Aircraft("A", "10*cos(t)", "10*sin(t)", "t", 15), 500)
        self.assertEqual(len(tr.x), 500)
        radio = float(np.max(np.hypot(tr.x, tr.y)))
        self.assertAlmostEqual(radio, 10.0, delta=0.2)

    def test_invalid_function(self):
        """Una expresión mal formada lanza TrajectoryError."""
        with self.assertRaises(TrajectoryError):
            sample(Aircraft("A", "10*cos(t", "0", "0", 5), 100)

    def test_non_finite_values(self):
        """Una singularidad (1/t en t=0) lanza TrajectoryError."""
        with self.assertRaises(TrajectoryError):
            sample(Aircraft("A", "1/t", "0", "0", 5), 500)


class TestCollisions(unittest.TestCase):
    def test_crossing_planes_collide(self):
        """Dos aviones que se cruzan en el origen generan colisión."""
        sim = Simulation([
            Aircraft("A", "t", "0", "5", 10),
            Aircraft("B", "t", "t", "5", 10),
        ], frames=500)
        self.assertTrue(sim.has_collisions)
        self.assertEqual(len(sim.critical_collisions), 1)

    def test_parallel_planes_no_collision(self):
        """Aviones paralelos muy separados no generan alertas."""
        sim = Simulation([
            Aircraft("A", "t", "0", "5", 10),
            Aircraft("B", "t", "50", "5", 10),
        ], frames=500)
        self.assertFalse(sim.has_collisions)
        self.assertEqual(sim.collisions, [])

    def test_identical_paths_collide(self):
        """Dos aviones en la misma trayectoria colisionan en t=0."""
        sim = Simulation([
            Aircraft("A", "10*cos(t)", "10*sin(t)", "t", 10),
            Aircraft("B", "10*cos(t)", "10*sin(t)", "t", 10),
        ], frames=500)
        self.assertTrue(sim.has_collisions)
        self.assertAlmostEqual(sim.critical_collisions[0].t, 0.0, delta=0.2)


class TestProximityLive(unittest.TestCase):
    def test_pair_distances_at_juntas(self):
        """Dos aviones en la misma trayectoria están a distancia ~0 en t dado."""
        from aviooon.core.collision import pair_distances_at

        sim = Simulation([
            Aircraft("A", "t", "0", "5", 10),
            Aircraft("B", "t", "0", "5", 10),
        ], frames=100)
        pairs = pair_distances_at(sim.trajectories, 3.0)
        self.assertEqual(len(pairs), 1)
        self.assertAlmostEqual(pairs[0][2], 0.0, delta=0.1)

    def test_pair_distances_at_separados(self):
        """Dos aviones paralelos a 50 u se mantienen separados."""
        from aviooon.core.collision import pair_distances_at

        sim = Simulation([
            Aircraft("A", "t", "0", "5", 10),
            Aircraft("B", "t", "50", "5", 10),
        ], frames=100)
        pairs = pair_distances_at(sim.trajectories, 3.0)
        self.assertGreater(pairs[0][2], 40.0)


class TestMetrics(unittest.TestCase):
    def test_circle_arc_length(self):
        """La distancia recorrida en una vuelta de radio 10 ≈ 2π·10."""
        sim = Simulation([
            Aircraft("A", "10*cos(t)", "10*sin(t)", "0", 2 * np.pi),
        ], frames=1000)
        distance = sim.metrics[0].distance
        self.assertAlmostEqual(distance, 2 * np.pi * 10, delta=1.0)


class TestScenarioManager(unittest.TestCase):
    def test_roundtrip(self):
        """Guardar y cargar un escenario conserva los datos."""
        from aviooon.data.scenario_manager import load_scenario, save_scenario

        original = [Aircraft("T-001", "t", "0", "1", 5, "#ffffff")]
        with tempfile.TemporaryDirectory() as tmp:
            path = save_scenario(original, os.path.join(tmp, "s.json"))
            restored = load_scenario(path)
        self.assertEqual(restored[0].name, "T-001")
        self.assertEqual(restored[0].x, "t")
        self.assertEqual(restored[0].duration, 5.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
