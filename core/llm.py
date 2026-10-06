"""Single module that talks to the LLM provider: local Ollama (default) or Gemini. Swap providers by editing this file only."""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from core import config

T = TypeVar("T", bound=BaseModel)
MAX_RETRIES = 2


class LLMError(Exception):
    """Raised with a user-friendly message when the LLM cannot deliver a usable result."""


def extract_json(text: str) -> dict:
    """Parse a JSON object from raw model text, tolerating code fences and surrounding prose."""
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start == -1 or end <= start:
            raise
        return json.loads(cleaned[start : end + 1])


GEMINI_TIMEOUT_MS = 25000  # give up on one request after 25s so the retry logic can kick in
_GENAI_CLIENT = None  # kept alive for the whole session: a throwaway Client gets closed when garbage-collected


def _client():
    global _GENAI_CLIENT
    from google import genai

    key = config.gemini_key()
    if not key:
        raise LLMError("The AI service is not configured. Please add GEMINI_API_KEY.")
    if _GENAI_CLIENT is None:
        from google.genai import types

        _GENAI_CLIENT = genai.Client(api_key=key, http_options=types.HttpOptions(timeout=GEMINI_TIMEOUT_MS))
    return _GENAI_CLIENT


OLLAMA_TIMEOUT = 240  # seconds; the first call loads the model into memory and can be slow


def _ollama_text(system: str, prompt: str, temperature: float, json_mode: bool) -> str:
    """One chat call to a local Ollama server (https://ollama.com)."""
    body = {
        "model": config.ollama_model(),
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": temperature, "num_ctx": 4096, "num_predict": 1200 if json_mode else 300},
        "keep_alive": "30m",  # keep the model in memory between questions (avoids a slow reload)
    }
    if json_mode:
        body["format"] = "json"
    req = urllib.request.Request(
        config.ollama_host() + "/api/chat",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.time()
    print(f"[LLM] asking {config.ollama_model()} ({len(system) + len(prompt)} chars, json={json_mode})...", flush=True)
    try:
        with urllib.request.urlopen(req, timeout=OLLAMA_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        print(f"[LLM] answered in {time.time() - started:.0f}s", flush=True)
    except TimeoutError as exc:
        print(f"[LLM] gave up after {time.time() - started:.0f}s", flush=True)
        raise LLMError(f"The local model took longer than {OLLAMA_TIMEOUT // 60} minutes. This computer is too slow "
                       "for it. Try a smaller model, or set LLM_PROVIDER=gemini.") from exc
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "ignore")[:200]
        if exc.code == 404:
            raise LLMError(f"Ollama does not have the model '{config.ollama_model()}'. "
                           f"Run: ollama pull {config.ollama_model()}") from exc
        raise LLMError(f"Ollama returned an error ({exc.code}): {detail}") from exc
    except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
        raise LLMError(f"Cannot reach Ollama at {config.ollama_host()}. Start it with 'ollama serve' "
                       "(or open the Ollama app) and try again.") from exc
    return ((data.get("message") or {}).get("content") or "").strip()


def _is_temporary(exc: Exception) -> bool:
    """True for errors that usually clear on their own: overload (503), rate limit (429), timeouts."""
    msg = str(exc)
    return any(t in msg for t in ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "500", "INTERNAL", "504", "DEADLINE", "Timeout", "timed out"))


def _gemini_models() -> list[str]:
    """The configured model first, then fallbacks (comma-separated GEMINI_FALLBACK_MODELS)."""
    fallbacks = config.get_setting("GEMINI_FALLBACK_MODELS", "gemini-flash-lite-latest,gemini-2.5-flash")
    models = [config.gemini_model()] + [m.strip() for m in fallbacks.split(",") if m.strip()]
    return list(dict.fromkeys(models))  # drop duplicates, keep order


GEMINI_ATTEMPTS_PER_MODEL = 3
GEMINI_BASE_DELAY = 1.5  # seconds; waits 1.5s, then 3s between tries


def _gemini_config(system: str, temperature: float, json_mode: bool, thinking: bool):
    from google.genai import types

    kwargs = dict(
        system_instruction=system,
        temperature=temperature,
        response_mime_type="application/json" if json_mode else "text/plain",
        max_output_tokens=1500 if json_mode else 400,
    )
    if not thinking:  # "thinking" models spend seconds reasoning before answering: not needed here
        kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
    return types.GenerateContentConfig(**kwargs)


def _gemini_text(system: str, prompt: str, temperature: float, json_mode: bool) -> str:
    last_exc: Exception | None = None
    thinking = False
    for model in _gemini_models():
        for attempt in range(GEMINI_ATTEMPTS_PER_MODEL):
            started = time.time()
            try:
                cfg = _gemini_config(system, temperature, json_mode, thinking)
                resp = _client().models.generate_content(model=model, contents=prompt, config=cfg)
                print(f"[LLM] {model} answered in {time.time() - started:.1f}s", flush=True)
                return (resp.text or "").strip()
            except LLMError:
                raise
            except Exception as exc:
                last_exc = exc
                msg = str(exc)
                if not thinking and ("thinking" in msg.lower() or "INVALID_ARGUMENT" in msg) and "503" not in msg:
                    thinking = True  # this model does not accept thinking_budget=0: retry once without it
                    print(f"[LLM] {model} rejected the thinking setting, retrying without it", flush=True)
                    continue
                if not _is_temporary(exc):
                    if "404" in msg or "NOT_FOUND" in msg:
                        print(f"[LLM] model {model} not available, trying next", flush=True)
                        break
                    raise
                print(f"[LLM] {model} busy/slow ({type(exc).__name__}), try {attempt + 1}/{GEMINI_ATTEMPTS_PER_MODEL}", flush=True)
                if attempt < GEMINI_ATTEMPTS_PER_MODEL - 1:
                    time.sleep(GEMINI_BASE_DELAY * (2 ** attempt))
        print(f"[LLM] giving up on {model}, switching model", flush=True)
    assert last_exc is not None
    raise last_exc


def generate_text(system: str, prompt: str, temperature: float = 0.7, json_mode: bool = False) -> str:
    """Call the model once and return its text. Raises LLMError with a friendly message on failure."""
    try:
        print("[LLM] provider:", config.llm_provider(), flush=True)
        if config.llm_provider() == "gemini":
            text = _gemini_text(system, prompt, temperature, json_mode)
        else:
            text = _ollama_text(system, prompt, temperature, json_mode)
    except LLMError:
        raise
    except Exception as exc:  # network, quota, auth, safety block...
        print("[LLM ERROR]", type(exc).__name__, exc, flush=True)
        raise LLMError("The AI service is unavailable (" + type(exc).__name__ + ": " + str(exc)[:150] + ")") from exc
    if not text:
        raise LLMError("The AI returned an empty response. Please try again.")
    return text


def generate_json(model_cls: type[T], system: str, prompt: str, temperature: float = 0.2) -> T:
    """Call the model expecting JSON matching ``model_cls``; retry up to MAX_RETRIES on invalid output."""
    last_error = ""
    for attempt in range(MAX_RETRIES + 1):
        retry_note = ""
        if attempt:
            retry_note = (
                f"\n\nYour previous reply was invalid ({last_error[:300]}). "
                "Reply again with ONLY a valid JSON object that matches the requested schema."
            )
        raw = generate_text(system, prompt + retry_note, temperature=temperature, json_mode=True)
        try:
            return model_cls.model_validate(extract_json(raw))
        except (json.JSONDecodeError, ValidationError, ValueError) as exc:
            last_error = str(exc)
    raise LLMError("The AI returned an unreadable answer several times. Please try again.")