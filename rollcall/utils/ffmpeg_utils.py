from pathlib import Path
from typing import Optional
from datetime import timedelta
from ..config import OCRConfig
import ffmpeg
import re

def ffprobe_duration_seconds(video_path: Path) -> Optional[float]:
    """
    Robust duration using ffmpeg.probe:
    - Prefer container-level format.duration
    - Fall back to a duration-like tag in the video stream if needed
    """
    try:
        probe = ffmpeg.probe(str(video_path))
        fmt = probe.get("format") or {}
        dur_str = fmt.get("duration")
        if dur_str:
            return float(dur_str)

        streams = probe.get("streams") or []
        v = next((s for s in streams if s.get("codec_type") == "video"), None)
        if v:
            tags = v.get("tags") or {}
            key = next((k for k in tags if re.search(r"duration", k, re.I)), None)
            if key:
                cleaned = tags[key].split(",")[0].strip()[:15]  # HH:MM:SS.mmm
                h, m, s = cleaned.split(":")
                td = timedelta(hours=int(h), minutes=int(m), seconds=float(s))
                return float(td.total_seconds())
    except ffmpeg.Error as e:
        try:
            err = e.stderr.decode("utf-8", errors="ignore")
        except Exception:
            err = str(e)
        print(f"[ffprobe] Error: {err}")
    except Exception as e:
        print(f"[ffprobe] Unexpected error: {e}")

    return None


def tail_start_time(duration_s: float, cfg: OCRConfig) -> float:
    if duration_s > 3600:
        return max(0.0, duration_s - cfg.long_video_tail_sec)
    return max(0.0, duration_s - cfg.short_video_tail_sec)


def extract_frames(video_path: Path, out_dir: Path, start_time: float, fps_expr: str) -> None:
    try:
        (
            ffmpeg
            .input(str(video_path), ss=start_time)
            .filter("fps", fps=fps_expr)
            .output(str(out_dir / "frame_%03d.png"))
            .run(capture_stdout=True, capture_stderr=True)
        )
    except ffmpeg.Error as e:
        stdout = ""
        stderr = ""
        try:
            stdout = e.stdout.decode("utf-8", errors="ignore")
            stderr = e.stderr.decode("utf-8", errors="ignore")
        except Exception:
            pass
        print(f"[ffmpeg] Error extracting frames for {video_path.name}:\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}")