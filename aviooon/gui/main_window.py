"""Ventana principal de AVIOOON.

Permite agregar, editar, eliminar y duplicar aeronaves, cargar presets,
guardar/recargar escenarios y lanzar la simulación.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox
from typing import List, Optional

import customtkinter as ctk

from .. import __version__
from ..config import APP_TITLE, FONT_FAMILY
from ..core.aircraft import Aircraft
from ..data.scenario_manager import PRESETS, build_preset, load_scenario, save_scenario
from .simulation_window import SimulationWindow

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

FONT = (FONT_FAMILY, 13)


class MainWindow(ctk.CTk):
    """Ventana de configuración de la simulación."""

    def __init__(self):
        super().__init__()
        self.title(f"{APP_TITLE} v{__version__}")
        self.geometry("980x640")
        self.minsize(860, 560)

        self.aircrafts: List[Aircraft] = []
        self.editing_index: Optional[int] = None
        self._selected_color = "#4FC3F7"

        self._build_ui()
        self._refresh_list()

    # ------------------------------------------------------------------
    # Construcción de la interfaz
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_form(ctk.CTkFrame(self, corner_radius=12))
        self._build_list(ctk.CTkFrame(self, corner_radius=12))

    def _build_form(self, parent: ctk.CTkFrame) -> None:
        parent.grid(row=0, column=0, sticky="nsew", padx=(14, 7), pady=14)

        ctk.CTkLabel(
            parent, text="✈  CONFIGURACIÓN DE VUELO",
            font=(FONT_FAMILY, 16, "bold"), text_color="#4ADE80",
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(14, 6))

        self._form_fields: dict = {}
        labels = [
            ("name", "Nombre del avión", "AV-001"),
            ("x", "Función x(t)", "10*cos(t)"),
            ("y", "Función y(t)", "10*sin(t)"),
            ("z", "Función z(t)", "t"),
            ("duration", "Tiempo (seg)", "15"),
        ]
        for i, (key, label, placeholder) in enumerate(labels, start=1):
            ctk.CTkLabel(parent, text=label, font=FONT).grid(
                row=i, column=0, sticky="w", padx=14, pady=(8, 0)
            )
            entry = ctk.CTkEntry(parent, placeholder_text=placeholder, font=FONT)
            entry.grid(row=i, column=0, columnspan=2, sticky="ew",
                       padx=14, pady=(2, 0))
            self._form_fields[key] = entry

        # Color
        ctk.CTkLabel(parent, text="Color del avión", font=FONT).grid(
            row=len(labels) + 1, column=0, sticky="w", padx=14, pady=(8, 0)
        )
        color_row = ctk.CTkFrame(parent, fg_color="transparent")
        color_row.grid(row=len(labels) + 1, column=0, columnspan=2,
                       sticky="ew", padx=14, pady=(2, 0))
        self._color_entry = ctk.CTkEntry(color_row, font=FONT, width=120)
        self._color_entry.insert(0, self._selected_color)
        self._color_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkButton(
            color_row, text="🎨 Elegir", width=90,
            command=self._pick_color,
        ).pack(side="left")
        self._swatch = tk.Canvas(color_row, width=26, height=26,
                                 highlightthickness=1, highlightbackground="#444")
        self._swatch.pack(side="left", padx=(6, 0))
        self._update_swatch()

        # Acciones del formulario
        self._submit_btn = ctk.CTkButton(
            parent, text="➕  Agregar avión", font=(FONT_FAMILY, 13, "bold"),
            command=self._submit,
        )
        self._submit_btn.grid(row=len(labels) + 2, column=0, columnspan=2,
                              sticky="ew", padx=14, pady=(14, 4))

        # Presets
        ctk.CTkLabel(parent, text="Presets de ejemplo", font=FONT).grid(
            row=len(labels) + 3, column=0, sticky="w", padx=14, pady=(12, 0)
        )
        self._preset_box = ctk.CTkComboBox(
            parent, values=list(PRESETS.keys()), font=FONT, state="readonly",
        )
        self._preset_box.set(list(PRESETS.keys())[0])
        self._preset_box.grid(row=len(labels) + 4, column=0, columnspan=2,
                              sticky="ew", padx=14, pady=(4, 0))
        ctk.CTkButton(
            parent, text="Aplicar preset", font=FONT,
            command=self._apply_preset,
        ).grid(row=len(labels) + 5, column=0, columnspan=2,
               sticky="ew", padx=14, pady=(6, 0))

        parent.columnconfigure(0, weight=1)

    def _build_list(self, parent: ctk.CTkFrame) -> None:
        parent.grid(row=0, column=1, sticky="nsew", padx=(7, 14), pady=14)
        parent.grid_rowconfigure(1, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 4))
        ctk.CTkLabel(
            header, text="🛫  AERONAVES", font=(FONT_FAMILY, 16, "bold"),
            text_color="#4ADE80",
        ).pack(side="left")
        self._count_label = ctk.CTkLabel(header, text="0 aviones", font=FONT)
        self._count_label.pack(side="right")

        self._listbox = tk.Listbox(
            parent, font=(FONT_FAMILY, 12), bg="#1f2937", fg="#e5e7eb",
            selectbackground="#2563eb", highlightthickness=0, relief="flat",
            activestyle="none",
        )
        self._listbox.grid(row=1, column=0, sticky="nsew", padx=14, pady=4)
        self._listbox.bind("<Double-Button-1>", lambda _e: self._on_edit())

        # Botones de gestión
        btns = ctk.CTkFrame(parent, fg_color="transparent")
        btns.grid(row=2, column=0, sticky="ew", padx=14, pady=(6, 0))
        for text, cmd, color in (
            ("✏️ Editar", self._on_edit, "#2563eb"),
            ("🗑 Eliminar", self._on_delete, "#dc2626"),
            ("📋 Duplicar", self._on_duplicate, "#7c3aed"),
        ):
            ctk.CTkButton(btns, text=text, font=FONT, fg_color=color,
                          hover_color=_darken(color), command=cmd).pack(
                side="left", expand=True, fill="x", padx=(0, 6)
            )

        # Archivo
        file_btns = ctk.CTkFrame(parent, fg_color="transparent")
        file_btns.grid(row=3, column=0, sticky="ew", padx=14, pady=(6, 0))
        ctk.CTkButton(file_btns, text="💾 Guardar", font=FONT,
                      command=self._on_save).pack(
            side="left", expand=True, fill="x", padx=(0, 6))
        ctk.CTkButton(file_btns, text="📂 Cargar", font=FONT,
                      command=self._on_load).pack(
            side="left", expand=True, fill="x")

        # Simulación
        ctk.CTkButton(
            parent, text="🚀  INICIAR SIMULACIÓN", font=(FONT_FAMILY, 15, "bold"),
            fg_color="#059669", hover_color="#047857", height=44,
            command=self._on_simulate,
        ).grid(row=4, column=0, sticky="ew", padx=14, pady=(10, 4))

        self._status_label = ctk.CTkLabel(
            parent, text="Listo. Agrega aviones o aplica un preset.",
            font=(FONT_FAMILY, 12), text_color="#94a3b8",
        )
        self._status_label.grid(row=5, column=0, sticky="ew", padx=14, pady=(0, 12))

    # ------------------------------------------------------------------
    # Lógica del formulario
    # ------------------------------------------------------------------
    def _read_form(self) -> Aircraft:
        raw = {k: e.get().strip() for k, e in self._form_fields.items()}
        aircraft = Aircraft(
            name=raw["name"],
            x=raw["x"],
            y=raw["y"],
            z=raw["z"],
            duration=float(raw["duration"]),
            color=self._selected_color,
        )
        aircraft.validate()
        return aircraft

    def _submit(self) -> None:
        try:
            aircraft = self._read_form()
        except ValueError as exc:
            messagebox.showwarning("Datos inválidos", str(exc))
            return

        if self.editing_index is not None:
            self.aircrafts[self.editing_index] = aircraft
            self.editing_index = None
            self._submit_btn.configure(text="➕  Agregar avión")
            self._status_label.configure(text=f"✏️ '{aircraft.name}' actualizado.")
        else:
            self.aircrafts.append(aircraft)
            self._status_label.configure(text=f"✅ '{aircraft.name}' agregado.")

        self._clear_form()
        self._refresh_list()

    def _pick_color(self) -> None:
        color = colorchooser.askcolor(
            title="Selecciona un color", color=self._selected_color
        )[1]
        if color:
            self._selected_color = color
            self._color_entry.delete(0, "end")
            self._color_entry.insert(0, color)
            self._update_swatch()

    def _update_swatch(self) -> None:
        self._swatch.configure(bg=self._selected_color)

    def _clear_form(self) -> None:
        for entry in self._form_fields.values():
            entry.delete(0, "end")

    # ------------------------------------------------------------------
    # Gestión de la lista
    # ------------------------------------------------------------------
    def _selected_index(self) -> Optional[int]:
        selection = self._listbox.curselection()
        return int(selection[0]) if selection else None

    def _refresh_list(self) -> None:
        self._listbox.delete(0, "end")
        for a in self.aircrafts:
            self._listbox.insert("end", f"✈  {a.name}   |   {a.color}   |   {a.duration:.0f}s")
        self._count_label.configure(text=f"{len(self.aircrafts)} aviones")

    def _on_edit(self) -> None:
        idx = self._selected_index()
        if idx is None:
            messagebox.showinfo("Selecciona un avión",
                                "Selecciona un avión de la lista primero.")
            return
        a = self.aircrafts[idx]
        self.editing_index = idx
        self._form_fields["name"].delete(0, "end"); self._form_fields["name"].insert(0, a.name)
        self._form_fields["x"].delete(0, "end"); self._form_fields["x"].insert(0, a.x)
        self._form_fields["y"].delete(0, "end"); self._form_fields["y"].insert(0, a.y)
        self._form_fields["z"].delete(0, "end"); self._form_fields["z"].insert(0, a.z)
        self._form_fields["duration"].delete(0, "end")
        self._form_fields["duration"].insert(0, str(a.duration))
        self._selected_color = a.color
        self._color_entry.delete(0, "end"); self._color_entry.insert(0, a.color)
        self._update_swatch()
        self._submit_btn.configure(text="💾  Actualizar avión")
        self._status_label.configure(text=f"Editando '{a.name}'…")

    def _on_delete(self) -> None:
        idx = self._selected_index()
        if idx is None:
            return
        removed = self.aircrafts.pop(idx)
        # Reacomodar el índice de edición para que no apunte a otro avión.
        if self.editing_index is not None:
            if self.editing_index == idx:
                self.editing_index = None
                self._submit_btn.configure(text="➕  Agregar avión")
                self._clear_form()
            elif self.editing_index > idx:
                self.editing_index -= 1
        self._refresh_list()
        self._status_label.configure(text=f"🗑 '{removed.name}' eliminado.")

    def _on_duplicate(self) -> None:
        idx = self._selected_index()
        if idx is None:
            return
        copy = Aircraft.from_dict(self.aircrafts[idx].to_dict())
        copy.name = f"{copy.name}-2"
        self.aircrafts.insert(idx + 1, copy)
        self._refresh_list()
        self._status_label.configure(text=f"📋 '{copy.name}' duplicado.")

    # ------------------------------------------------------------------
    # Presets y archivos
    # ------------------------------------------------------------------
    def _apply_preset(self) -> None:
        self.aircrafts = build_preset(self._preset_box.get())
        self._refresh_list()
        self._status_label.configure(
            text=f"Preset '{self._preset_box.get()}' cargado."
        )

    def _on_save(self) -> None:
        if not self.aircrafts:
            messagebox.showinfo("Nada que guardar", "Agrega aviones primero.")
            return
        path = filedialog.asksaveasfilename(
            title="Guardar escenario",
            defaultextension=".json",
            filetypes=[("Escenario AVIOOON", "*.json"), ("Todos", "*.*")],
            initialfile="escenario.json",
        )
        if path:
            save_scenario(self.aircrafts, path)
            self._status_label.configure(text=f"💾 Escenario guardado en {path}")

    def _on_load(self) -> None:
        path = filedialog.askopenfilename(
            title="Cargar escenario",
            filetypes=[("Escenario AVIOOON", "*.json"), ("Todos", "*.*")],
        )
        if path:
            try:
                self.aircrafts = load_scenario(path)
            except (ValueError, OSError) as exc:
                messagebox.showerror("Error al cargar", str(exc))
                return
            self._refresh_list()
            self._status_label.configure(text=f"📂 Escenario cargado: {path}")

    # ------------------------------------------------------------------
    # Simulación
    # ------------------------------------------------------------------
    def _on_simulate(self) -> None:
        if not self.aircrafts:
            messagebox.showinfo("Sin aviones",
                                "Agrega al menos un avión para simular.")
            return
        try:
            SimulationWindow(self, self.aircrafts)
        except Exception as exc:  # TrajectoryError u otros
            messagebox.showerror("Error de simulación", str(exc))


def _darken(hex_color: str, factor: float = 0.85) -> str:
    """Devuelve una versión más oscura de un color hex."""
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    return f"#{int(r * factor):02x}{int(g * factor):02x}{int(b * factor):02x}"
