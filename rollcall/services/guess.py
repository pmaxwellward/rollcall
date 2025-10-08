# services/guess.py
import json
import re
from google import genai
from google.genai import types as gtypes  # ← alias SDK types to avoid collisions
from ..schemas import REFINE_SCHEMA
from ..types import CreditsMap

STRICT_EP_RE    = re.compile(r"^.+_S(\d{2})E(\d{2})$")
STRICT_MOVIE_RE = re.compile(r"^(.+?)(?: \((19|20)\d{2}\))?$")


def _normalize_guess(text: str) -> str:
    t = (text or "").strip()
    if not t or t.upper() == "UNKNOWN_TITLE":
        return "UNKNOWN_TITLE"
    if STRICT_EP_RE.match(t):
        return t
    m = STRICT_MOVIE_RE.match(t)
    if m:
        title = m.group(1).strip()
        year  = m.group(2)
        if len(title) >= 2:
            return f"{title} ({year})" if year else title
    return "UNKNOWN_TITLE"


def _safe_text(resp) -> str:
    """Extract plain text from a genai response (works without schemas)."""
    txt = getattr(resp, "text", "") or ""
    if txt:
        return txt.strip()
    for c in getattr(resp, "candidates", []) or []:
        parts = getattr(c, "content", None) and c.content.parts or []
        buf = "".join(getattr(p, "text", "") or "" for p in parts)
        if buf:
            return buf.strip()
    return ""


def _make_search_tool():
    """Return a grounded search tool across SDK variants."""
    if hasattr(gtypes, "GoogleSearch"):
        return gtypes.Tool(google_search=gtypes.GoogleSearch())
    if hasattr(gtypes, "GoogleSearchRetrieval"):
        return gtypes.Tool(google_search_retrieval=gtypes.GoogleSearchRetrieval())
    return None


class GuesserService:
    def __init__(self, client: genai.Client, model: str = "gemini-2.5-flash"):
        self.client = client
        self.model = model

    def refine_title(self, credits_map: CreditsMap, *, max_tokens: int = 64, previous: str | None = None) -> str:
        # Trim/sort for determinism and token control
        payload = {"credits": {k: sorted([str(x) for x in v])[:12] for k, v in credits_map.items()}}
        instr = (
            "Identify the media title from these end-credit key→values.\n"
            "Return JSON with field 'title' only. Formats allowed:\n"
            " • TV: Title_SxxEyy\n"
            " • Film: Title        or Title (YYYY)\n"
            "If unsure, return 'UNKNOWN_TITLE'."
        )
        if previous:
            instr += f"\nPrevious guess: {previous}"

        resp = self.client.models.generate_content(
            model=self.model,
            contents=[instr, json.dumps(payload, ensure_ascii=False)],
            config=gtypes.GenerateContentConfig(
                temperature=0.0,
                max_output_tokens=max_tokens,
                response_mime_type="application/json",  # schemas OK here (no tools)
                response_schema=REFINE_SCHEMA,
            ),
        )
        try:
            return _normalize_guess(json.loads(resp.text or "{}").get("title", "UNKNOWN_TITLE"))
        except Exception:
            return "UNKNOWN_TITLE"

    def search_fallback(self, credits_map: CreditsMap, *, max_tokens: int = 64) -> str:
        """
        Grounded search fallback. NOTE: response_schema is NOT supported with tools,
        so we request a single plain line and normalize it.
        """
        tool = _make_search_tool()
        if not tool:
            return "UNKNOWN_TITLE"

        payload = {"credits": {k: sorted([str(x) for x in v])[:12] for k, v in credits_map.items()}}
        instr = (
            "Using ONLY grounded web results, identify the media (TV episode or feature film) "
            "that matches these end-credit key→values. Prefer imdb.com, thetvdb.com, tvmaze.com, "
            "wikipedia.org, tcm.com.\n\n"
            "Return EXACTLY ONE LINE (no JSON, no code fences):\n"
            "  • TV episode: Title_SxxEyy\n"
            "  • Feature film: Title        or Title (YYYY)\n"
            "If uncertain, return exactly: UNKNOWN_TITLE"
        )

        cfg = gtypes.GenerateContentConfig(
            temperature=0.0,
            max_output_tokens=max_tokens,
            tools=[tool],  # ← tools enabled; no response_schema / response_mime_type here
        )

        resp = self.client.models.generate_content(
            model=self.model,
            contents=[instr, json.dumps(payload, ensure_ascii=False)],
            config=cfg,
        )
        return _normalize_guess(_safe_text(resp))
