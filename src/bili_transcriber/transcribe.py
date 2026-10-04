"""Speech-to-text with faster-whisper, plus transcript exporters."""

from __future__ import annotations

import json
from dataclasses import dataclass

import numpy as np


@dataclass
class Segment:
    start: float
    end: float
    text: str


def _fmt_ts(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def transcribe(audio: np.ndarray, model: str = "small", model_path: str | None = None,
               language: str = "zh", device: str = "cpu",
               compute_type: str = "int8", beam_size: int = 5) -> list[Segment]:
    """Transcribe 16 kHz mono float32 *audio*.

    *model* is a faster-whisper model name (``tiny``/``base``/``small``/
    ``medium``/``large-v3`` …). *model_path* overrides it with a local
    directory containing the CTranslate2 model files.
    """
    from faster_whisper import WhisperModel

    wm = WhisperModel(model_path or model, device=device, compute_type=compute_type)
    segments, info = wm.transcribe(audio, language=language, beam_size=beam_size)
    print(f"识别语言: {info.language} (置信度 {info.language_probability:.2f})")
    out = []
    total = len(audio) / 16000
    done = 0.0
    for s in segments:
        text = s.text.strip()
        out.append(Segment(start=s.start, end=s.end, text=text))
        done = s.end
        print(f"\r转写进度: {done / total:.0%}", end="", flush=True)
    print()
    return out


def to_txt(segments: list[Segment]) -> str:
    return "\n".join(f"[{s.start:.1f}-{s.end:.1f}] {s.text}" for s in segments)


def to_srt(segments: list[Segment]) -> str:
    lines = []
    for i, s in enumerate(segments, 1):
        lines += [str(i), f"{_fmt_ts(s.start)} --> {_fmt_ts(s.end)}", s.text, ""]
    return "\n".join(lines)


def to_json(segments: list[Segment], meta: dict | None = None) -> str:
    payload = {
        "meta": meta or {},
        "segments": [
            {"start": s.start, "end": s.end, "text": s.text} for s in segments
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


EXPORTERS = {"txt": to_txt, "srt": to_srt, "json": to_json}
