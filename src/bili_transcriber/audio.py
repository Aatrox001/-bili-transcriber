"""Audio helpers: convert any downloaded stream to 16 kHz mono WAV and load it.

The WAV is loaded with the stdlib ``wave`` module on purpose, so transcription
does not depend on a specific PyAV version (some PyAV releases break
faster-whisper's built-in audio decoding).
"""

from __future__ import annotations

import shutil
import subprocess
import wave

import numpy as np


def check_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("需要安装 ffmpeg（https://ffmpeg.org/download.html）")


def to_wav_16k(src: str, dest: str) -> str:
    """Convert *src* to 16 kHz mono WAV via ffmpeg. Returns *dest*."""
    check_ffmpeg()
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-i", src,
        "-ar", "16000", "-ac", "1",
        dest,
    ]
    subprocess.run(cmd, check=True)
    return dest


def load_wav_mono_16k(path: str) -> np.ndarray:
    """Load a 16-bit PCM WAV as float32 mono samples in [-1, 1]."""
    with wave.open(path, "rb") as w:
        if w.getnchannels() != 1 or w.getsampwidth() != 2:
            raise RuntimeError(f"需要 16-bit 单声道 WAV: {path}")
        frames = w.readframes(w.getnframes())
    return np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
