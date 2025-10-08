from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Iterable, Set
import os


# ---- App-wide constants ------------------------------------------------------

# File types we consider as media inputs
VIDEO_EXTS: Final[Set[str]] = {".mp4", ".mkv", ".avi", ".mov"}

# Environment variables checked for the Gemini API key (in order)
API_KEY_ENV_ORDER: Final[tuple[str, ...]] = (
    "GEMINI_API_KEY",      # preferred for the google-genai SDK
    "GOOGLE_API_KEY",      # fallback (older name)
)


def resolve_api_key() -> str | None:
    """
    Returns the first non-empty API key found from API_KEY_ENV_ORDER, or None.
    """
    for var in API_KEY_ENV_ORDER:
        val = os.getenv(var)
        if val:
            return val
    return None


# ---- Dataclass configs -------------------------------------------------------

@dataclass(slots=True)
class OCRConfig:
    """
    Controls how frames are sampled and lightly pre-filtered before OCR.

    - delay_seconds: sleep between OCR calls to avoid rate limits.
    - variation_threshold: quick grayscale-extrema check; if (hi - lo) <= threshold,
      we assume the frame is blank/solid and skip OCR.
    - fps_expr: ffmpeg fps filter expression; e.g., "1/3" = one frame every 3 seconds.
    - long_video_tail_sec / short_video_tail_sec: how far back from the end to sample.
    - max_no_update: early-stop if the title guess doesn’t change after N iterations.
    """
    delay_seconds: float = 0.0
    variation_threshold: float = 0.0
    fps_expr: str = "1/3"
    long_video_tail_sec: int = 210   # > 1 hour → last ~3.5 minutes
    short_video_tail_sec: int = 90   # ≤ 1 hour → last ~1.5 minutes
    max_no_update: int = 10


@dataclass(slots=True)
class GeminiConfig:
    """
    Model knobs for google-genai calls. Token limits are usually passed per-call
    (e.g., ocr_max_tokens / refine_max_tokens) in core.py.
    """
    model_name: str = "gemini-2.5-flash"
    temperature: float = 0.0
    top_p: float = 1.0
    top_k: int = 1


# ---- Helpers for callers -----------------------------------------------------

def is_media_file(path_suffix: str, *, exts: Iterable[str] = VIDEO_EXTS) -> bool:
    """Case-insensitive check for allowed media extensions."""
    return path_suffix.lower() in exts
