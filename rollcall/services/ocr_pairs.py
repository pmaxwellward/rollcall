from pathlib import Path
import json, re
from typing import Optional
from google import genai
from google.genai import types
from ..schemas import PAIR_SCHEMA
from ..types import OCRResult

class OCRService:
    def __init__(self, client: genai.Client, model: str = "gemini-2.5-flash"):
        self.client = client
        self.model = model

    def extract_pairs(
        self,
        image_path: Path,
        *,
        max_tokens: int = 768,
        fallback_key: str = "text",
        dump_json_to: Optional[Path] = None,
    ) -> OCRResult:
        mime = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"
        with open(image_path, "rb") as f:
            part = types.Part.from_bytes(data = f.read(), mime_type=mime)

        prompt = f"""Extract ALL visible end-credit key→value pairs from this image.

Rules
- Use the exact on-screen label/heading as the key when present.
- If multiple names appear under one label (commas/bullets/newlines/columns), put EACH as a separate string in `values`.
- If a row shows two columns (e.g., character ↔ actor), create entries where LEFT is the key and RIGHT is the single value.
- If a name block has NO visible label, use the key "{fallback_key}".
- Preserve capitalization, punctuation (Jr., ASC, CSA), diacritics.
- Omit unreadable text; do not invent.
- Return ONLY JSON matching the provided schema.
"""

        resp = self.client.models.generate_content(
            model=self.model,
            contents=[part, prompt],
            config=types.GenerateContentConfig(
                temperature=0.0,
                max_output_tokens=max_tokens,
                response_mime_type="application/json",
                response_schema=PAIR_SCHEMA,
            ),
        )

        try:
            data: OCRResult = json.loads(resp.text or "{}")
        except Exception:
            data = {"entries": []}

        data = self._normalize_pairs(data)

        if dump_json_to:
            dump_json_to.mkdir(parents=True, exist_ok=True)
            out = dump_json_to / f"{image_path.stem}.pairs.json"
            out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

        return data

    _split_re = re.compile(r"[;\n•·]|,(?=\s*[A-Z])")

    def _normalize_pairs(self, obj: OCRResult) -> OCRResult:
        entries = obj.get("entries") or []
        normalized = []
        for e in entries:
            key = " ".join(str(e.get("key","")).split()).strip()
            vals = e.get("values") or []
            flat = []
            for v in (vals if isinstance(vals, list) else [vals]):
                s = " ".join(str(v).split()).strip()
                if not s: 
                    continue
                parts = [p.strip(" ;,•·") for p in self._split_re.split(s) if p.strip(" ;,•·")]
                flat.extend(parts or [s])
            if key and flat:
                normalized.append({"key": key, "values": flat})
        return {"entries": normalized}
