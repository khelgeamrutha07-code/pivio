"""Speech-to-text (faster-whisper) and delivery statistics (fillers, pace, length)."""
from __future__ import annotations

import os
import re
import tempfile
import time

from core import config

FILLER_PROMPT = "Umm, uh, so, like, you know, I was, uh, basically doing, um, actually that."
FILLER_PATTERNS: dict[str, str] = {
    "um": r"\b(?:u+m+|u+h+m+)\b",
    "uh": r"\b(?:u+h+|e+r+m*)\b",
    "like": r"\blike\b",
    "you know": r"\byou know\b",
    "basically": r"\bbasically\b",
    "actually": r"\bactually\b",
    "so": r"\bso\b",
}


class TranscriptionError(Exception):
    """Raised when audio cannot be transcribed."""


def count_fillers(text: str) -> dict[str, int]:
    """Count filler words in text; only fillers that occur are returned."""
    lowered = text.lower()
    counts = {name: len(re.findall(pat, lowered)) for name, pat in FILLER_PATTERNS.items()}
    return {k: v for k, v in counts.items() if v}


def word_count(text: str) -> int:
    """Number of words in the text."""
    return len(re.findall(r"[A-Za-z0-9']+", text))


def words_per_minute(text: str, seconds: float | None) -> float | None:
    """Speaking pace; None when the duration is unknown or too short to be meaningful."""
    if not seconds or seconds < 1:
        return None
    return round(word_count(text) / (seconds / 60.0), 1)


def delivery_stats(text: str, seconds: float | None = None) -> dict:
    """Return filler counts, pace and length for one answer."""
    fillers = count_fillers(text)
    words = word_count(text)
    return {
        "words": words,
        "filler_total": sum(fillers.values()),
        "fillers": fillers,
        "wpm": words_per_minute(text, seconds),
        "duration_s": round(seconds, 1) if seconds else None,
    }


def aggregate_delivery(stats: list[dict]) -> dict:
    """Combine per-answer delivery stats into a session summary."""
    if not stats:
        return {"answers": 0, "avg_words": 0, "filler_total": 0, "fillers": {}, "avg_wpm": None}
    fillers: dict[str, int] = {}
    for s in stats:
        for k, v in s.get("fillers", {}).items():
            fillers[k] = fillers.get(k, 0) + v
    wpms = [s["wpm"] for s in stats if s.get("wpm")]
    return {
        "answers": len(stats),
        "avg_words": round(sum(s["words"] for s in stats) / len(stats), 1),
        "filler_total": sum(fillers.values()),
        "fillers": fillers,
        "avg_wpm": round(sum(wpms) / len(wpms), 1) if wpms else None,
    }


@config.cached_resource
def _load_model(size: str):
    from faster_whisper import WhisperModel

    return WhisperModel(size, device="cpu", compute_type="int8")


def transcribe(audio_bytes: bytes) -> tuple[str, float]:
    """Transcribe WAV/audio bytes. Returns (text, duration_seconds)."""
    path = ""
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_bytes)
            path = tmp.name
        t0 = time.time()
        model = _load_model(config.whisper_size())
        print(f"[TIMING] speech model ready in {time.time() - t0:.1f}s", flush=True)
        t1 = time.time()
        language = config.get_setting("WHISPER_LANGUAGE", "en").strip().lower()

        def run(use_vad: bool):
            segments, info = model.transcribe(
                path,
                language=None if language in ("", "auto") else language,
                beam_size=1,
                initial_prompt=FILLER_PROMPT,
                vad_filter=use_vad,
                vad_parameters={"min_silence_duration_ms": 600} if use_vad else None,
                condition_on_previous_text=False,
            )
            return " ".join(seg.text.strip() for seg in segments).strip(), float(info.duration)

        text, duration = run(True)
        print(f"[TIMING] transcribing took {time.time() - t1:.1f}s", flush=True)
        if not text:  # the silence filter may have removed quiet speech: try again without it
            text, duration = run(False)
    except Exception as exc:
        raise TranscriptionError("Voice transcription failed. You can type your answer instead.") from exc
    finally:
        if path and os.path.exists(path):
            os.remove(path)
    if not text:
        raise TranscriptionError("No speech was detected. Check that your headphone microphone is selected "
                                 "and speak a little louder, or type your answer instead.")
    return text, duration