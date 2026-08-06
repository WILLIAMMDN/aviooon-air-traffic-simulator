"""Reproducción de sonidos de alarma.

Usa ``winsound`` (biblioteca estándar de Windows) para generar beeps
sin necesidad de archivos de audio. En sistemas no Windows la
funcionalidad se desactiva de forma silenciosa.
"""
from __future__ import annotations

import threading

try:
    import winsound
except ImportError:  # pragma: no cover — solo ocurre fuera de Windows
    winsound = None

SOUND_SUPPORTED = winsound is not None

# Cada evento tiene su propio patrón de sonido.
_CONTACT_SEQUENCE = ((660, 100),)                      # primer contacto
_WARNING_SEQUENCE = ((440, 120), (50, 40), (440, 120)) # se acercan (preventiva)
_ALARM_SEQUENCE = ((880, 180), (660, 180), (880, 180), (660, 180))  # colisión
_CLEAR_SEQUENCE = ((660, 120), (520, 150))             # se separaron


def _play_in_thread(func) -> None:
    """Ejecuta el sonido en un hilo para no congelar la interfaz."""
    threading.Thread(target=func, daemon=True).start()


def _play(sequence) -> None:
    if not SOUND_SUPPORTED:
        return

    def _run() -> None:
        for freq, ms in sequence:
            if freq > 0:
                winsound.Beep(freq, ms)
            else:
                threading.Event().wait(ms / 1000)

    _play_in_thread(_run)


def play_contact() -> None:
    """Primer contacto: un pitido medio corto."""
    _play(_CONTACT_SEQUENCE)


def play_warning() -> None:
    """Alerta preventiva: doble pitido grave (se están acercando)."""
    _play(_WARNING_SEQUENCE)


def play_alarm() -> None:
    """Alarma de colisión: secuencia aguda de sirena."""
    _play(_ALARM_SEQUENCE)


def play_clear() -> None:
    """Separación: dos tonos descendentes (todo en orden)."""
    _play(_CLEAR_SEQUENCE)
