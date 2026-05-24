from __future__ import annotations

import threading
import wave
from pathlib import Path

import numpy as np
import pygame


class SoundAlert:
    def __init__(self, assets_dir: Path | None = None) -> None:
        base = assets_dir or Path(__file__).resolve().parent.parent / "assets"
        self._soft_path = base / "soft_nudge.wav"
        self._medium_path = base / "medium_chime.wav"
        self._final_path = base / "final_cheerful.wav"
        self._lock = threading.Lock()
        self._ok = False
        self._looping = False
        self._init_mixer()

    def _init_mixer(self) -> None:
        try:
            ensure_sound_assets(self._soft_path, self._medium_path, self._final_path)
            pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)
            self._ok = True
        except Exception:
            self._ok = False

    @property
    def ok(self) -> bool:
        return self._ok

    def start_final_loop(self) -> None:
        if not self._ok:
            return
        with self._lock:
            if self._looping:
                return
            try:
                pygame.mixer.music.load(str(self._final_path))
                pygame.mixer.music.set_volume(0.55)
                pygame.mixer.music.play(loops=-1)
                self._looping = True
            except Exception:
                self._looping = False

    def stop_loop(self) -> None:
        if not self._ok:
            return
        with self._lock:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass
            self._looping = False

    def play_soft(self) -> None:
        if not self._ok:
            return
        try:
            nudge = pygame.mixer.Sound(str(self._soft_path))
            nudge.set_volume(0.68)
            nudge.play()
        except Exception:
            pass

    def play_medium(self) -> None:
        if not self._ok:
            return
        try:
            chime = pygame.mixer.Sound(str(self._medium_path))
            chime.set_volume(0.78)
            chime.play()
        except Exception:
            pass


def ensure_sound_assets(soft_path: Path, medium_path: Path, final_path: Path) -> None:
    soft_path.parent.mkdir(parents=True, exist_ok=True)
    _write_chime(
        soft_path,
        notes=[392.0, 493.88, 587.33],
        note_duration=0.17,
        volume=0.42,
        harmonic_mix=0.3,
    )
    _write_chime(
        medium_path,
        notes=[523.25, 659.25, 783.99, 987.77],
        note_duration=0.2,
        volume=0.48,
        harmonic_mix=0.35,
    )
    if not final_path.exists():
        _write_cheerful_loop(final_path)


def _write_chime(
    path: Path,
    notes: list[float],
    note_duration: float,
    volume: float,
    harmonic_mix: float = 0.0,
) -> None:
    sample_rate = 44100
    segments: list[np.ndarray] = []
    for frequency in notes:
        t = np.linspace(0, note_duration, int(sample_rate * note_duration), endpoint=False)
        envelope = np.minimum(1.0, t / 0.015) * np.exp(-3.5 * t / note_duration)
        fundamental = np.sin(2 * np.pi * frequency * t)
        harmonic = np.sin(2 * np.pi * frequency * 2 * t) if harmonic_mix > 0 else 0.0
        wave_form = volume * envelope * (fundamental + harmonic_mix * harmonic)
        segments.append(wave_form.astype(np.float32))
        segments.append(np.zeros(int(sample_rate * 0.035), dtype=np.float32))
    waveform = np.concatenate(segments)
    peak = np.max(np.abs(waveform))
    if peak > 0:
        waveform = waveform * min(1.0, 0.95 / peak)
    _write_wave(path, waveform, sample_rate)


def _write_cheerful_loop(path: Path) -> None:
    sample_rate = 44100
    melody = [523.25, 587.33, 659.25, 783.99, 659.25, 783.99, 987.77]
    note_duration = 0.22
    segments: list[np.ndarray] = []
    for frequency in melody:
        t = np.linspace(0, note_duration, int(sample_rate * note_duration), endpoint=False)
        envelope = np.minimum(1.0, t / 0.015) * np.exp(-3.0 * t / note_duration)
        wave_form = 0.32 * envelope * np.sin(2 * np.pi * frequency * t)
        segments.append(wave_form.astype(np.float32))
    _write_wave(path, np.concatenate(segments), sample_rate)


def _write_wave(path: Path, waveform: np.ndarray, sample_rate: int) -> None:
    pcm = (waveform * 32767).astype(np.int16)
    with wave.open(str(path), "w") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm.tobytes())
