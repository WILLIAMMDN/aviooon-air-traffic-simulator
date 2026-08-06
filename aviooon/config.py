"""Configuración central del proyecto.

Toda constante configurable vive aquí para no esparcir "números mágicos"
por el código.
"""

APP_TITLE = "AVIOOON — Simulador de Tráfico Aéreo 3D"
APP_VERSION = "2.2.0"

# --- Simulación ---
SIM_FRAMES = 500          # fotogramas de la animación
SIM_INTERVAL_MS = 40      # intervalo entre fotogramas (ms)
COLLISION_THRESHOLD = 3.0   # distancia mínima (u) para considerar COLISIÓN
WARNING_THRESHOLD = 8.0     # distancia para alerta preventiva
DETECTION_THRESHOLD = 12.0  # distancia para primer contacto (se acercan)

# --- Tema de la interfaz ---
APPEARANCE_MODE = "dark"
COLOR_THEME = "blue"
FONT_FAMILY = "Segoe UI"

# --- Trayectorias ---
DEFAULT_DURATION = 15.0   # segundos por defecto
