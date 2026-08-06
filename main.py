"""Punto de entrada de AVIOOON — Simulador de Tráfico Aéreo 3D.

Ejecutar con:
    python main.py
"""
import matplotlib

# Debe fijarse el backend antes de crear cualquier figura.
matplotlib.use("TkAgg")

from aviooon.gui.main_window import MainWindow  # noqa: E402


def main() -> None:
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
