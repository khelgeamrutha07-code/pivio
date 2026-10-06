"""Configuration loading: .env locally, st.secrets on Streamlit Cloud."""
from __future__ import annotations

import functools
import os
from pathlib import Path
from typing import Any, Callable

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
QUESTION_BANK_DIR = ROOT / "data" / "question_bank"
CHROMA_DIR = ROOT / ".chroma"
RESUME_BUCKET = "resumes"
MAX_QUESTIONS_HARD_CAP = 10

load_dotenv(ROOT / ".env")


def get_setting(key: str, default: str = "") -> str:
    """Return a setting from the environment, then st.secrets, then the default."""
    value = os.getenv(key)
    if value:
        return value
    try:
        import streamlit as st

        if key in st.secrets:
            return str(st.secrets[key])
    except Exception:  # secrets file missing or streamlit not installed
        pass
    return default


def firebase_key() -> str:
    return get_setting("FIREBASE_API_KEY")


def require_email_verification() -> bool:
    return get_setting("REQUIRE_EMAIL_VERIFICATION", "true").strip().lower() not in ("false", "0", "no", "off")


def data_dir() -> Path:
    custom = get_setting("DATA_DIR")
    return Path(custom) if custom else ROOT / ".data"


def db_path() -> Path:
    return data_dir() / "pivio.db"

def gemini_key() -> str:
    return get_setting("GEMINI_API_KEY")


def gemini_model() -> str:
    return get_setting("GEMINI_MODEL", "gemini-2.0-flash")


def llm_provider() -> str:
    """'ollama' (local, default) or 'gemini'."""
    return get_setting("LLM_PROVIDER", "ollama").strip().lower()


def ollama_host() -> str:
    return get_setting("OLLAMA_HOST", "http://localhost:11434").rstrip("/")


def ollama_model() -> str:
    return get_setting("OLLAMA_MODEL", "llama3.1:8b")


def whisper_size() -> str:
    return get_setting("WHISPER_MODEL_SIZE", "base")


def missing_settings() -> list[str]:
    """List required settings that are not configured."""
    required = {"FIREBASE_API_KEY": firebase_key()}
    if llm_provider() == "gemini":
        required["GEMINI_API_KEY"] = gemini_key()
    return [name for name, val in required.items() if not val]


def cached_resource(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Cache heavy objects with st.cache_resource (falls back to lru_cache without Streamlit)."""
    try:
        import streamlit as st

        return st.cache_resource(show_spinner=False)(fn)
    except Exception:
        return functools.lru_cache(maxsize=None)(fn)
