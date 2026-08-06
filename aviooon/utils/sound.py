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

_ALARM_SEQUENCE = ((880, 180), (660, 180), (880, 180), (660, 180))
_WARNING_FREQ = 440
_WARNING_MS = 120


def _play_in_thread(func) -> None:
    """Ejecuta el sonido en un hilo para no congelar la interfaz."""
    threading.Thread(target=func, daemon=True).start()


def play_alarm() -> None:
    """Alarma de colisión: secuencia aguda repetida."""
    if not SOUND_SUPPORTED:
        return

    def _run() -> None:
        for freq, ms in _ALARM_SEQUENCE:
            winsound.Beep(freq, ms)

    _play_in_thread(_run)


def play_warning() -> None:
    """Alerta preventiva: un pitido corto."""
    if not SOUND_SUPPORTED:
        return

    def _run() -> None:
        winsound.Beep(_WARNING_FREQ, _WARNING_MS)

    _play_in_thread(_run)
