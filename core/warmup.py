"""Load the slow, heavy models (question-bank embeddings and speech-to-text) in the background.

On a computer without a GPU, importing sentence-transformers/torch and loading Whisper can take
30-60 seconds the first time. Doing it once at login means the user does not wait for it later.
"""
from __future__ import annotations

import threading
import time

_started = False
_lock = threading.Lock()


def _run() -> None:
    from core import config, rag, voice

    t0 = time.time()
    try:
        n = rag.build_index()
        print(f"[WARMUP] question bank ready ({n} chunks) in {time.time() - t0:.1f}s", flush=True)
    except Exception as exc:  # noqa: BLE001
        print("[WARMUP] question bank failed:", type(exc).__name__, exc, flush=True)
    t1 = time.time()
    try:
        voice._load_model(config.whisper_size())
        print(f"[WARMUP] speech model '{config.whisper_size()}' ready in {time.time() - t1:.1f}s", flush=True)
    except Exception as exc:  # noqa: BLE001
        print("[WARMUP] speech model failed:", type(exc).__name__, exc, flush=True)


def start() -> None:
    """Start the background warm-up once per server process."""
    global _started
    with _lock:
        if _started:
            return
        _started = True
    threading.Thread(target=_run, name="pivio-warmup", daemon=True).start()