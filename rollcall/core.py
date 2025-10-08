from pathlib import Path
import shutil, tempfile, time
from typing import Optional

from .config import OCRConfig, GeminiConfig, resolve_api_key, VIDEO_EXTS, is_media_file
from .services.genai_client import make_client
from .services.ocr_pairs import OCRService
from .services.guess import GuesserService
from .utils.ffmpeg_utils import (
    ffprobe_duration_seconds as _ffprobe_duration_seconds,
    tail_start_time as _tail_start_time,
    extract_frames as _extract_frames,
)
from .utils.image_utils import image_has_text
from .merge import merge_pair_entries, map_trim

def process_media_directory(
    directory: Path,
    api_key: Optional[str] = None,
    ocr_cfg: Optional[OCRConfig] = None,
    gemini_cfg: Optional[GeminiConfig] = None,
    dry_run: bool = False,
    verbose: bool = True,
    ocr_max_tokens: int = 768,
    refine_max_tokens: int = 64,
    use_search: bool = True,
) -> None:
    ocr_cfg = ocr_cfg or OCRConfig()
    gemini_cfg = gemini_cfg or GeminiConfig()
    client = make_client(api_key)

    ocr = OCRService(client, model=gemini_cfg.model_name)
    guess = GuesserService(client, model=gemini_cfg.model_name)

    with tempfile.TemporaryDirectory(prefix="rollcall_") as tmpdir:
        frames_dir = Path(tmpdir)

        for entry in sorted(directory.iterdir()):
            if not entry.is_file() or entry.suffix.lower() not in {".mp4", ".mkv", ".avi", ".mov"}:
                continue
            if verbose:
                print(f"Processing {entry.name} ...")

            duration = _ffprobe_duration_seconds(entry)
            if not duration:
                if verbose: print("  Skipping (no duration found).")
                continue

            start_time = _tail_start_time(duration, ocr_cfg)
            for f in frames_dir.glob("*"): f.unlink(missing_ok=True)
            _extract_frames(entry, frames_dir, start_time, ocr_cfg.fps_expr)

            credits_map: dict[str, set[str]] = {}
            current_guess: Optional[str] = None
            no_update_count = 0

            for frame_file in sorted(frames_dir.glob("frame_*.png")):
                if not image_has_text(frame_file, ocr_cfg.variation_threshold):
                    continue

                obj = ocr.extract_pairs(frame_file, max_tokens=ocr_max_tokens)
                if obj.get("entries"):
                    merge_pair_entries(credits_map, obj)
                else:
                    continue

                # (trim large maps to keep token use sane)
                trimmed = map_trim(credits_map, per_key=12)

                new_guess = guess.refine_title(trimmed, max_tokens=refine_max_tokens, previous=current_guess)
                if new_guess == current_guess and new_guess != "UNKNOWN_TITLE":
                    no_update_count += 1
                else:
                    current_guess, no_update_count = new_guess, 0

                if no_update_count >= ocr_cfg.max_no_update:
                    break

                time.sleep(ocr_cfg.delay_seconds)

            if (not current_guess or current_guess == "UNKNOWN_TITLE") and use_search:
                if verbose: print("  Local guess unknown. Trying search-backed fallback...")
                trimmed = map_trim(credits_map, per_key=12)
                current_guess = guess.search_fallback(trimmed, max_tokens=refine_max_tokens)

            if not current_guess or current_guess == "UNKNOWN_TITLE":
                if verbose: print("  No usable title. Skipping rename.")
                continue

            new_name = f"{current_guess}{entry.suffix}"
            new_path = entry.with_name(new_name)
            if verbose:
                print(f"  Rename: '{entry.name}' -> '{new_name}'" + (" [DRY RUN]" if dry_run else ""))
            if not dry_run:
                try: shutil.move(str(entry), str(new_path))
                except Exception as e: print(f"  Rename failed: {e}")

    if verbose: print("Processing complete.")
