"""Ventana de simulación.

Muestra la animación 3D de las trayectorias (Matplotlib embebido en
CustomTkinter) junto con un radar cenital. La reproducción usa un bucle
propio con ``after()`` para que pausar, reanudar, reiniciar, cambiar la
velocidad y detectar el fin funcionen de forma fiable.

Además, monitorea la proximidad entre aeronaves **en tiempo real**:
cada fotograma se mide la distancia entre todos los pares y se emiten
eventos con su propio sonido (contacto, aproximación, colisión,
separación).
"""
from __future__ import annotations

from tkinter import filedialog, messagebox
from typing import Dict, List, Optional, Tuple

import customtkinter as ctk
import numpy as np
from matplotlib import animation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.patches import Circle
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from .. import __version__
from ..config import (
    APP_TITLE,
    COLLISION_THRESHOLD,
    DETECTION_THRESHOLD,
    FONT_FAMILY,
    SIM_FRAMES,
    SIM_INTERVAL_MS,
    WARNING_THRESHOLD,
)
from ..core.aircraft import Aircraft
from ..core.collision import CollisionEvent, pair_distances_at
from ..core.simulation import Simulation
from ..core.trajectory import Trajectory, TrajectoryError
from ..data.exporter import export_animation, export_metrics_csv
from ..utils.sound import play_alarm, play_clear, play_contact, play_warning

FONT = (FONT_FAMILY, 12)

_BG = "#111827"
_PANEL = "#1f2937"
_GREEN = "#4ade80"
_YELLOW = "#facc15"
_RED = "#ef4444"
_CYAN = "#22d3ee"
_GRAY = "#94a3b8"

# Estados de proximidad por par de aeronaves
_STATE_NONE = None
_STATE_DETECT = "detect"   # primer contacto (se acercan)
_STATE_WARN = "warn"       # alerta preventiva
_STATE_CRIT = "crit"       # colisión


class SimulationWindow(ctk.CTkToplevel):
    """Ventana de simulación animada en 3D + radar."""

    def __init__(self, master, aircrafts: List[Aircraft]):
        super().__init__(master)
        self.title(f"🚀 Simulación — {APP_TITLE} v{__version__}")
        self.geometry("1120x800")
        self.minsize(980, 660)

        self.aircrafts = list(aircrafts)
        try:
            self.sim = Simulation(self.aircrafts)
        except TrajectoryError as exc:
            self.destroy()
            raise ValueError(str(exc)) from exc

        # --- Estado de reproducción (bucle propio) ---
        self._total_frames = SIM_FRAMES
        self._frame = 0
        self._playing = False
        self._after_id: Optional[str] = None
        self._speed = 1.0

        self._sound_enabled = True
        self._plane_artists: list = []
        self._marker_artists: list = []
        self._radar_markers: list = []
        self._pair_states: Dict[Tuple[int, int], Optional[str]] = {}

        self._build_ui()
        self._setup_plot()
        self._setup_radar()
        self._write_header_log()
        self._start_loop()
        self.bind("<Destroy>", lambda _e: self._stop_loop())

    # ------------------------------------------------------------------
    # Interfaz
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

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

        # --- Radar 2D (vista cenital) ---
        radar_frame = ctk.CTkFrame(body, fg_color=_BG, corner_radius=10)
        radar_frame.grid(row=1, column=0, sticky="ew", padx=(0, 10), pady=(10, 0))
        self._radar_fig = Figure(figsize=(7, 2.2), dpi=90, facecolor=_BG)
        self._radar_ax = self._radar_fig.add_subplot(111)
        self._radar_ax.set_facecolor(_BG)
        self._radar_canvas = FigureCanvasTkAgg(self._radar_fig, master=radar_frame)
        self._radar_canvas.get_tk_widget().pack(fill="both", expand=True)

        # --- Panel lateral ---
        panel = ctk.CTkFrame(body, fg_color=_PANEL, corner_radius=10)
        panel.grid(row=0, column=1, rowspan=2, sticky="ns", padx=(0, 0))
        panel.grid_columnconfigure(0, weight=1)

        self._build_controls(panel)
        self._build_metrics(panel)
        self._build_log(panel)
        self._build_export(panel)

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
            parent, text="1.00x", font=FONT, text_color=_GRAY,
        )
        self._speed_label.grid(row=3, column=0, sticky="e", padx=18, pady=2)

        self._sound_btn = ctk.CTkButton(
            parent, text="🔊 Sonido: ON", font=FONT,
            command=self._toggle_sound,
        )
        self._sound_btn.grid(row=4, column=0, sticky="ew", padx=12, pady=(8, 4))

        ctk.CTkLabel(
            parent,
            text="Zonas: 🟡 contacto <12u · ⚠ preventiva <8u · 🚨 colisión <3u",
            font=(FONT_FAMILY, 10), text_color=_GRAY, justify="left",
            wraplength=280,
        ).grid(row=5, column=0, sticky="w", padx=12, pady=(4, 0))

    def _build_metrics(self, parent: ctk.CTkFrame) -> None:
        ctk.CTkLabel(
            parent, text="MÉTRICAS DE VUELO", font=(FONT_FAMILY, 13, "bold"),
            text_color=_GREEN,
        ).grid(row=6, column=0, sticky="ew", padx=12, pady=(14, 4))

        container = ctk.CTkFrame(parent, fg_color="transparent")
        container.grid(row=7, column=0, sticky="ew", padx=12)
        for i, m in enumerate(self.sim.metrics):
            text = (
                f"✈ {m.name}\n"
                f"   Distancia: {m.distance:.1f} u\n"
                f"   Alt. máx:   {m.max_altitude:.1f} u\n"
                f"   Vel. media: {m.mean_speed:.1f} u/s"
            )
            ctk.CTkLabel(
                container, text=text, font=(FONT_FAMILY, 11),
                text_color=_GRAY, justify="left",
            ).grid(row=i, column=0, sticky="w", pady=2)

    def _build_log(self, parent: ctk.CTkFrame) -> None:
        ctk.CTkLabel(
            parent, text="REGISTRO DE EVENTOS", font=(FONT_FAMILY, 13, "bold"),
            text_color=_GREEN,
        ).grid(row=8, column=0, sticky="ew", padx=12, pady=(14, 4))

        self._log = ctk.CTkTextbox(
            parent, width=300, height=170, font=(FONT_FAMILY, 11),
            fg_color=_BG, text_color="#e5e7eb", state="disabled",
        )
        self._log.grid(row=9, column=0, sticky="ew", padx=12, pady=(0, 4))

    def _build_export(self, parent: ctk.CTkFrame) -> None:
        export_row = ctk.CTkFrame(parent, fg_color="transparent")
        export_row.grid(row=10, column=0, sticky="ew", padx=12, pady=(0, 12))
        ctk.CTkButton(
            export_row, text="🎞 GIF", font=FONT, command=self._export_gif,
        ).pack(side="left", expand=True, fill="x", padx=(0, 6))
        ctk.CTkButton(
            export_row, text="🎬 MP4", font=FONT, fg_color="#7c3aed",
            hover_color="#6d28d9", command=self._export_mp4,
        ).pack(side="left", expand=True, fill="x", padx=(0, 6))
        ctk.CTkButton(
            export_row, text="📊 CSV", font=FONT, fg_color="#0e7490",
            hover_color="#155e75", command=self._export_csv,
        ).pack(side="left", expand=True, fill="x")

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
    # Radar 2D
    # ------------------------------------------------------------------
    def _setup_radar(self) -> None:
        ax = self._radar_ax
        ax.set_facecolor(_BG)
        ax.set_title("RADAR — Vista cenital (XY)", color="#e5e7eb", fontsize=10)

        xs = np.concatenate([tr.x for tr in self.sim.trajectories])
        ys = np.concatenate([tr.y for tr in self.sim.trajectories])
        pad = max(3.0, 0.15 * max(xs.max() - xs.min(), ys.max() - ys.min(), 1))
        ax.set_xlim(xs.min() - pad, xs.max() + pad)
        ax.set_ylim(ys.min() - pad, ys.max() + pad)
        ax.set_aspect("equal", adjustable="box")
        ax.tick_params(colors=_GRAY, labelsize=7)
        ax.grid(True, alpha=0.15, color=_GRAY)
        ax.set_xlabel("X", color=_GRAY, fontsize=8)
        ax.set_ylabel("Y", color=_GRAY, fontsize=8)

        center = ((xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2)
        radius = max(np.hypot(xs - center[0], ys - center[1]))
        for r in np.linspace(radius / 3, radius, 3):
            ax.add_patch(
                Circle(center, r, fill=False, color=_GRAY, alpha=0.25,
                       linewidth=0.7)
            )

        for tr in self.sim.trajectories:
            ax.plot(tr.x, tr.y, color=tr.color, alpha=0.25, linewidth=0.8)

        self._radar_scatter = ax.scatter([], [], s=45, zorder=5)
        self._radar_labels = [
            ax.text(0.0, 0.0, tr.name, fontsize=8, color=tr.color)
            for tr in self.sim.trajectories
        ]

    # ------------------------------------------------------------------
    # Bucle de reproducción (pausa / reanudar / reiniciar / fin)
    # ------------------------------------------------------------------
    def _start_loop(self) -> None:
        if self._playing:
            return
        self._playing = True
        self._play_btn.configure(text="⏸  Pausar")
        self._schedule_tick()

    def _stop_loop(self) -> None:
        self._playing = False
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def _schedule_tick(self) -> None:
        if not self._playing:
            return
        interval = max(1, int(SIM_INTERVAL_MS / max(0.1, self._speed)))
        self._after_id = self.after(interval, self._tick)

    def _tick(self) -> None:
        self._after_id = None
        if not self._playing:
            return

        if self._frame >= self._total_frames:
            self._playing = False
            self._play_btn.configure(text="▶  Reanudar")
            self._status.configure(text="✅ Simulación terminada",
                                   text_color=_GREEN)
            return

        self._render_frame(self._frame)
        self._frame += 1
        self._schedule_tick()

    def _toggle_play(self) -> None:
        if self._playing:
            self._stop_loop()
            self._play_btn.configure(text="▶  Reanudar")
        else:
            if self._frame >= self._total_frames:
                self._frame = 0          # al terminar, reanudar = empezar
                self._render_frame(0)
            self._start_loop()

    def _on_speed(self, value) -> None:
        self._speed = max(0.25, min(2.0, float(value)))
        self._speed_label.configure(text=f"{self._speed:.2f}x")
        # El siguiente tick usará el nuevo intervalo automáticamente.

    def _toggle_sound(self) -> None:
        self._sound_enabled = not self._sound_enabled
        self._sound_btn.configure(
            text="🔊 Sonido: ON" if self._sound_enabled else "🔇 Sonido: OFF"
        )

    def _reset(self) -> None:
        self._stop_loop()
        for artist in self._marker_artists:
            artist.remove()
        self._marker_artists.clear()
        for artist in self._radar_markers:
            artist.remove()
        self._radar_markers.clear()
        self._pair_states.clear()

        self._log.configure(state="normal")
        self._log.delete("1.0", "end")
        self._log.configure(state="disabled")
        self._write_header_log()

        self._frame = 0
        self._status.configure(text=self._status_text(), text_color=_GREEN)
        self._start_loop()

    # ------------------------------------------------------------------
    # Render de un fotograma + monitoreo de proximidad en vivo
    # ------------------------------------------------------------------
    def _render_frame(self, frame: int) -> None:
        t = frame / self._total_frames * self.sim.duration

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

        self._monitor_proximity(t)
        self._update_radar(t)
        self._canvas.draw_idle()

    def _monitor_proximity(self, t: float) -> None:
        """Mide las distancias actuales y dispara eventos con su sonido."""
        pairs = pair_distances_at(self.sim.trajectories, t)
        for i, j, d in pairs:
            key = (i, j)
            old = self._pair_states.get(key)

            if d < self.sim.collision_threshold:
                new = _STATE_CRIT
            elif d < self.sim.warning_threshold:
                new = _STATE_WARN
            elif d < DETECTION_THRESHOLD:
                new = _STATE_DETECT
            else:
                new = _STATE_NONE

            if new == old:
                continue
            self._pair_states[key] = new
            self._on_proximity_change(key, new, d, t)

    def _on_proximity_change(self, key, new, d: float, t: float) -> None:
        i, j = key
        a = self.sim.trajectories[i].name
        b = self.sim.trajectories[j].name

        if new == _STATE_CRIT:
            self._log_line(f"🚨 COLISIÓN: {a} ↔ {b} a {d:.1f} u (t={t:.1f}s)")
            self._status.configure(text=f"🚨 ¡COLISIÓN! {a} ↔ {b} ({d:.1f} u)",
                                   text_color=_RED)
            self._add_collision_marker(i, j, t)
            if self._playing and self._sound_enabled:
                play_alarm()
        elif new == _STATE_WARN:
            self._log_line(f"⚠ PREVENTIVA: {a} ↔ {b} a {d:.1f} u (se acercan)")
            self._status.configure(text=f"⚠ PREVENTIVA: {a} ↔ {b} ({d:.1f} u)",
                                   text_color=_YELLOW)
            if self._playing and self._sound_enabled:
                play_warning()
        elif new == _STATE_DETECT:
            self._log_line(f"🛰 CONTACTO: {a} ↔ {b} a {d:.1f} u (se acercan)")
            self._status.configure(text=f"🛰 CONTACTO: {a} ↔ {b} ({d:.1f} u)",
                                   text_color=_CYAN)
            if self._playing and self._sound_enabled:
                play_contact()
        else:  # se separaron
            if old in (_STATE_WARN, _STATE_CRIT):
                self._log_line(f"✅ SEPARACIÓN: {a} ↔ {b} a {d:.1f} u")
                if self._playing and self._sound_enabled:
                    play_clear()
            self._status.configure(text=self._status_text(), text_color=_GREEN)

    def _add_collision_marker(self, i: int, j: int, t: float) -> None:
        """Marca el punto medio entre las dos aeronaves en el 3D y el radar."""
        p1 = self._position(self.sim.trajectories[i], t)
        p2 = self._position(self.sim.trajectories[j], t)
        mid = (p1 + p2) / 2
        x, y, z = mid

        marker = self.ax.scatter(
            [x], [y], [z], s=170, marker="X", color=_RED, depthshade=False,
            zorder=10,
        )
        self._marker_artists.append(marker)

        radar_marker = self._radar_ax.scatter(
            [x], [y], s=120, marker="X", color=_RED, zorder=6,
        )
        self._radar_markers.append(radar_marker)

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

    def _update_radar(self, t: float) -> None:
        offsets, colors = [], []
        for tr in self.sim.trajectories:
            pos = self._position(tr, t)
            offsets.append([pos[0], pos[1]])
            colors.append(tr.color)
        self._radar_scatter.set_offsets(np.asarray(offsets))
        self._radar_scatter.set_facecolors(colors)
        for label, tr in zip(self._radar_labels, self.sim.trajectories):
            pos = self._position(tr, t)
            label.set_position((pos[0], pos[1]))
        self._radar_canvas.draw_idle()

    # ------------------------------------------------------------------
    # Exportación
    # ------------------------------------------------------------------
    def _export_gif(self) -> None:
        self._export_animation_dialog("GIF", ".gif", "animacion.gif")

    def _export_mp4(self) -> None:
        self._export_animation_dialog("MP4", ".mp4", "animacion.mp4")

    def _export_animation_dialog(self, label: str, ext: str, initial: str) -> None:
        path = filedialog.asksaveasfilename(
            title=f"Exportar animación {label}", defaultextension=ext,
            filetypes=[(f"Video {label}", f"*{ext}")], initialfile=initial,
        )
        if not path:
            return

        was_playing = self._playing
        self._stop_loop()
        self._status.configure(text=f"🎞 Exportando {label}…", text_color=_GRAY)
        self.update()

        ani = self._build_export_animation()
        try:
            export_animation(ani, path, fps=20)
            self._status.configure(
                text=f"✅ {label} exportado: {path}", text_color=_GREEN
            )
            self._log_line(f"{label} exportado: {path}")
        except Exception as exc:
            messagebox.showerror(f"Error al exportar {label}", str(exc))
            self._status.configure(text=f"Exportación {label} fallida",
                                   text_color=_RED)
        finally:
            del ani
            if was_playing:
                self._start_loop()

    def _build_export_animation(self) -> animation.FuncAnimation:
        """Animación temporal solo para exportar (sin sonidos)."""
        def update(frame):
            self._render_frame(frame)
            return []

        return animation.FuncAnimation(
            self.fig, update, frames=self._total_frames,
            interval=SIM_INTERVAL_MS, blit=False,
        )

    def _export_csv(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Exportar métricas", defaultextension=".csv",
            filetypes=[("CSV", "*.csv")], initialfile="metricas.csv",
        )
        if not path:
            return
        try:
            export_metrics_csv(self.sim.metrics, self.sim.collisions, path)
            self._status.configure(text=f"✅ CSV exportado: {path}",
                                   text_color=_GREEN)
            self._log_line(f"CSV exportado: {path}")
        except Exception as exc:
            messagebox.showerror("Error al exportar CSV", str(exc))
            self._status.configure(text="Exportación CSV fallida",
                                   text_color=_RED)

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

    def _write_header_log(self) -> None:
        n = len(self.sim.trajectories)
        critical = len(self.sim.critical_collisions)
        self._log_line(
            f"Simulación: {n} aeronaves · {len(self.sim.collisions)} puntos "
            f"de alerta ({critical} críticos)."
        )
        if self.sim.has_collisions:
            self._log_line("⚠  ¡Se detectaron colisiones en este escenario!")

    def _log_line(self, text: str) -> None:
        self._log.configure(state="normal")
        self._log.insert("end", text + "\n")
        self._log.see("end")
        self._log.configure(state="disabled")
