"""Ventana de simulación.

Muestra la animación 3D de las trayectorias (Matplotlib embebido en
CustomTkinter), detecta y anuncia colisiones en tiempo real (con sonido),
y presenta métricas de vuelo calculadas por el motor.
"""
from __future__ import annotations

from typing import List

import customtkinter as ctk
import numpy as np
from matplotlib import animation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from .. import __version__
from ..config import APP_TITLE, FONT_FAMILY, SIM_FRAMES, SIM_INTERVAL_MS
from ..core.aircraft import Aircraft
from ..core.collision import CollisionEvent
from ..core.simulation import Simulation
from ..core.trajectory import Trajectory, TrajectoryError
from ..utils.sound import play_alarm, play_warning

FONT = (FONT_FAMILY, 12)

_BG = "#111827"
_PANEL = "#1f2937"
_GREEN = "#4ade80"
_YELLOW = "#facc15"
_RED = "#ef4444"
_GRAY = "#94a3b8"


class SimulationWindow(ctk.CTkToplevel):
    """Ventana de simulación animada en 3D."""

    def __init__(self, master, aircrafts: List[Aircraft]):
        super().__init__(master)
        self.title(f"🚀 Simulación — {APP_TITLE} v{__version__}")
        self.geometry("1120x760")
        self.minsize(960, 620)

        self.aircrafts = list(aircrafts)
        try:
            self.sim = Simulation(self.aircrafts)
        except TrajectoryError as exc:
            self.destroy()
            raise ValueError(str(exc)) from exc

        self._sound_enabled = True
        self._paused = False
        self._sounded: set = set()
        self._plane_artists: list = []
        self._marker_artists: list = []
        self.ani: animation.FuncAnimation | None = None

        self._build_ui()
        self._setup_plot()
        self._write_header_log()
        self._create_animation()

    # ------------------------------------------------------------------
    # Interfaz
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Barra de estado superior
        self._status = ctk.CTkLabel(
            self, text="🛫  Preparando simulación…",
            font=(FONT_FAMILY, 14, "bold"), text_color=_GRAY,
        )
        self._status.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 4))

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 12))
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)

        # --- Visor 3D ---
        viewport = ctk.CTkFrame(body, fg_color=_BG, corner_radius=10)
        viewport.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.fig = Figure(figsize=(7, 6), dpi=100, facecolor=_BG)
        self.ax = self.fig.add_subplot(111, projection="3d")
        self.ax.set_facecolor(_BG)
        self._canvas = FigureCanvasTkAgg(self.fig, master=viewport)
        self._canvas.get_tk_widget().pack(fill="both", expand=True)

        # --- Panel lateral ---
        panel = ctk.CTkFrame(body, fg_color=_PANEL, corner_radius=10)
        panel.grid(row=0, column=1, sticky="ns", padx=(0, 0))
        panel.grid_columnconfigure(0, weight=1)

        self._build_controls(panel)
        self._build_metrics(panel)
        self._build_log(panel)

    def _build_controls(self, parent: ctk.CTkFrame) -> None:
        ctk.CTkLabel(
            parent, text="CONTROLES", font=(FONT_FAMILY, 13, "bold"),
            text_color=_GREEN,
        ).grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 4))

        row1 = ctk.CTkFrame(parent, fg_color="transparent")
        row1.grid(row=1, column=0, sticky="ew", padx=12, pady=4)
        self._play_btn = ctk.CTkButton(
            row1, text="⏸  Pausar", font=FONT, command=self._toggle_play,
        )
        self._play_btn.pack(side="left", expand=True, fill="x", padx=(0, 6))
        ctk.CTkButton(
            row1, text="↺ Reiniciar", font=FONT, fg_color="#7c3aed",
            hover_color="#6d28d9", command=self._reset,
        ).pack(side="left", expand=True, fill="x")

        ctk.CTkLabel(
            parent, text="Velocidad", font=FONT, text_color=_GRAY,
        ).grid(row=2, column=0, sticky="w", padx=12, pady=(8, 0))
        self._speed_var = ctk.DoubleVar(value=1.0)
        self._speed_slider = ctk.CTkSlider(
            parent, from_=0.25, to=2.0, number_of_steps=14,
            variable=self._speed_var, command=self._on_speed,
        )
        self._speed_slider.grid(row=3, column=0, sticky="ew", padx=12, pady=2)
        self._speed_label = ctk.CTkLabel(
            parent, text="1.0x", font=FONT, text_color=_GRAY,
        )
        self._speed_label.grid(row=3, column=0, sticky="e", padx=18, pady=2)

        self._sound_btn = ctk.CTkButton(
            parent, text="🔊 Sonido: ON", font=FONT,
            command=self._toggle_sound,
        )
        self._sound_btn.grid(row=4, column=0, sticky="ew", padx=12, pady=(8, 4))

    def _build_metrics(self, parent: ctk.CTkFrame) -> None:
        ctk.CTkLabel(
            parent, text="MÉTRICAS DE VUELO", font=(FONT_FAMILY, 13, "bold"),
            text_color=_GREEN,
        ).grid(row=5, column=0, sticky="ew", padx=12, pady=(16, 4))

        container = ctk.CTkFrame(parent, fg_color="transparent")
        container.grid(row=6, column=0, sticky="ew", padx=12)
        self._metric_labels = []
        for i, m in enumerate(self.sim.metrics):
            text = (
                f"✈ {m.name}\n"
                f"   Distancia: {m.distance:.1f} u\n"
                f"   Alt. máx:   {m.max_altitude:.1f} u\n"
                f"   Vel. media: {m.mean_speed:.1f} u/s"
            )
            lbl = ctk.CTkLabel(
                container, text=text, font=(FONT_FAMILY, 11),
                text_color=_GRAY, justify="left",
            )
            lbl.grid(row=i, column=0, sticky="w", pady=2)
            self._metric_labels.append(lbl)

    def _build_log(self, parent: ctk.CTkFrame) -> None:
        ctk.CTkLabel(
            parent, text="REGISTRO DE ALERTAS", font=(FONT_FAMILY, 13, "bold"),
            text_color=_GREEN,
        ).grid(row=7, column=0, sticky="ew", padx=12, pady=(16, 4))

        self._log = ctk.CTkTextbox(
            parent, width=300, height=180, font=(FONT_FAMILY, 11),
            fg_color=_BG, text_color="#e5e7eb", state="disabled",
        )
        self._log.grid(row=8, column=0, sticky="ew", padx=12, pady=(0, 12))

    # ------------------------------------------------------------------
    # Plot 3D
    # ------------------------------------------------------------------
    def _setup_plot(self) -> None:
        ax = self.ax
        xs = np.concatenate([tr.x for tr in self.sim.trajectories])
        ys = np.concatenate([tr.y for tr in self.sim.trajectories])
        zs = np.concatenate([tr.z for tr in self.sim.trajectories])

        pad = max(2.0, 0.15 * max(xs.max() - xs.min(), ys.max() - ys.min(), 1))
        ax.set_xlim(xs.min() - pad, xs.max() + pad)
        ax.set_ylim(ys.min() - pad, ys.max() + pad)
        ax.set_zlim(0, max(zs.max() + pad, 5))
        ax.set_title("Simulación de Tráfico Aéreo 3D", color="#e5e7eb", fontsize=12)
        ax.set_xlabel("X", color=_GRAY)
        ax.set_ylabel("Y", color=_GRAY)
        ax.set_zlabel("Z", color=_GRAY)
        ax.tick_params(colors=_GRAY)

        for tr in self.sim.trajectories:
            ax.plot(tr.x, tr.y, tr.z, linestyle="--", alpha=0.45,
                    color=tr.color, label=tr.name)
        ax.legend(loc="upper left", fontsize=8, facecolor=_PANEL,
                  edgecolor="#374151", labelcolor="#e5e7eb")

    # ------------------------------------------------------------------
    # Animación
    # ------------------------------------------------------------------
    def _create_animation(self) -> None:
        if self.ani is not None:
            self.ani.event_source.stop()
            self.ani = None

        total_frames = SIM_FRAMES
        duration = self.sim.duration

        def update(frame: int):
            t = frame / total_frames * duration

            # Limpia los aviones del fotograma anterior
            for artist in self._plane_artists:
                artist.remove()
            self._plane_artists.clear()

            for tr in self.sim.trajectories:
                pos = self._position(tr, t)
                nxt = self._position(tr, min(t + 0.05, tr.duration))
                direction = nxt - pos
                norm = np.linalg.norm(direction)
                if norm > 1e-9:
                    direction = direction / norm
                else:
                    direction = np.array([1.0, 0.0, 0.0])
                self._draw_plane(pos, direction, tr.color)

            # Alerta de colisiones al alcanzar su instante
            for event in self.sim.collisions:
                if event.t <= t and id(event) not in self._sounded:
                    self._sounded.add(id(event))
                    self._on_collision_event(event)

            self._canvas.draw_idle()
            return []

        self.ani = animation.FuncAnimation(
            self.fig, update, frames=total_frames,
            interval=SIM_INTERVAL_MS, blit=False, repeat=False,
        )
        self._status.configure(
            text=self._status_text(), text_color=_GREEN
        )
        self.bind("<Destroy>", lambda _e: self._stop_animation())

    def _draw_plane(self, pos: np.ndarray, direction: np.ndarray,
                    color: str, size: float = 1.2) -> None:
        """Dibuja un avión orientado según su dirección de vuelo."""
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

        # Matriz de rotación de Rodrigues: alinea eje X con `direction`
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
            faces, facecolors=color, linewidths=0.3, edgecolors="k",
            alpha=0.95,
        )
        self.ax.add_collection3d(fuselage)
        self._plane_artists.append(fuselage)

        wing_line = self.ax.plot(
            [rotated_wings[0][0], rotated_wings[1][0]],
            [rotated_wings[0][1], rotated_wings[1][1]],
            [rotated_wings[0][2], rotated_wings[1][2]],
            color="black", linewidth=1.5,
        )
        self._plane_artists.extend(wing_line)

    # ------------------------------------------------------------------
    # Eventos de colisión
    # ------------------------------------------------------------------
    def _on_collision_event(self, event: CollisionEvent) -> None:
        self._log_line(event.describe())
        x, y, z = event.position
        marker = self.ax.scatter(
            [x], [y], [z], s=160, marker="X", color=_RED if not event.warning
            else _YELLOW, depthshade=False,
        )
        self._marker_artists.append(marker)

        if event.warning:
            self._status.configure(text=event.describe(), text_color=_YELLOW)
            if self._sound_enabled:
                play_warning()
        else:
            self._status.configure(text=event.describe(), text_color=_RED)
            if self._sound_enabled:
                play_alarm()

    def _log_line(self, text: str) -> None:
        self._log.configure(state="normal")
        self._log.insert("end", text + "\n")
        self._log.see("end")
        self._log.configure(state="disabled")

    def _write_header_log(self) -> None:
        n = len(self.sim.trajectories)
        critical = len(self.sim.critical_collisions)
        self._log_line(
            f"Simulación: {n} aeronaves · {len(self.sim.collisions)} alertas "
            f"({critical} críticas)."
        )
        if self.sim.has_collisions:
            self._log_line("⚠  ¡Se detectaron colisiones en este escenario!")

    # ------------------------------------------------------------------
    # Controles
    # ------------------------------------------------------------------
    def _toggle_play(self) -> None:
        if self.ani is None:
            return
        if self._paused:
            self.ani.event_source.start()
            self._paused = False
            self._play_btn.configure(text="⏸  Pausar")
        else:
            self.ani.event_source.stop()
            self._paused = True
            self._play_btn.configure(text="▶  Reanudar")

    def _reset(self) -> None:
        self._paused = False
        self._play_btn.configure(text="⏸  Pausar")
        for artist in self._marker_artists:
            artist.remove()
        self._marker_artists.clear()
        self._sounded.clear()
        self._log.configure(state="normal")
        self._log.delete("1.0", "end")
        self._log.configure(state="disabled")
        self._write_header_log()
        self._create_animation()
        self.ani.event_source.start()

    def _on_speed(self, _value) -> None:
        speed = max(0.25, float(self._speed_var.get()))
        self._speed_label.configure(text=f"{speed:.2f}x")
        if self.ani is not None:
            self.ani.event_source.interval = int(SIM_INTERVAL_MS / speed)

    def _toggle_sound(self) -> None:
        self._sound_enabled = not self._sound_enabled
        self._sound_btn.configure(
            text="🔊 Sonido: ON" if self._sound_enabled else "🔇 Sonido: OFF"
        )

    def _stop_animation(self) -> None:
        if self.ani is not None:
            self.ani.event_source.stop()

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------
    def _position(self, tr: Trajectory, t: float) -> np.ndarray:
        return np.array([
            float(np.interp(t, tr.t, tr.x)),
            float(np.interp(t, tr.t, tr.y)),
            float(np.interp(t, tr.t, tr.z)),
        ])

    def _status_text(self) -> str:
        if self.sim.has_collisions:
            return "⚠  Simulación con colisiones detectadas"
        return "✅  Simulación sin colisiones críticas"
