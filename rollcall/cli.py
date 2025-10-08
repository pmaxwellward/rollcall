# rollcall/cli.py
from __future__ import annotations

from pathlib import Path
from typing import Optional
import typer

# Prefer package-relative import; fall back to absolute when running this file directly in VS Code
try:
    from .core import process_media_directory, OCRConfig, GeminiConfig
except ImportError:
    # allow "Run > Python File" without a launch.json
    import sys
    from pathlib import Path as _Path
    sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))  # add project root
    from rollcall.core import process_media_directory, OCRConfig, GeminiConfig  # type: ignore

app = typer.Typer(add_completion=False, help="RollCall: OCR end credits and rename unlabeled media files.")


@app.command(name="run")
def app_run(
    directory: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        resolve_path=True,
        help="Path to a directory containing media files (.mp4, .mkv, .avi, .mov).",
    ),
    api_key: Optional[str] = typer.Option(
        None,
        "--api-key",
        help="Gemini API key. If omitted, uses env var GEMINI_API_KEY.",
    ),
    # behavior
    dry_run: bool = typer.Option(False, "--dry-run", help="Show planned renames without changing files."),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress non-error output."),
    # OCR & sampling
    fps: str = typer.Option("1/3", "--fps", help='FFmpeg fps filter expression, e.g. "1/3".'),
    variation_threshold: float = typer.Option(
        0.0, "--variation-threshold", help="Pixel-variation threshold for quick text precheck."
    ),
    ocr_delay: float = typer.Option(0.0, "--ocr-delay", help="Delay between OCR requests (seconds)."),
    long_tail_sec: int = typer.Option(210, "--long-tail-sec", help="Tail sample for videos > 1 hour (seconds)."),
    short_tail_sec: int = typer.Option(90, "--short-tail-sec", help="Tail sample for videos ≤ 1 hour (seconds)."),
    max_no_update: int = typer.Option(10, "--max-no-update", help="Stop after this many unchanged guesses."),
    # model
    model: str = typer.Option("gemini-2.5-flash", "--model", help="Gemini model name."),
    # token caps (separate for OCR vs refine)
    ocr_max_tokens: int = typer.Option(256, "--ocr-max-tokens", help="Max tokens for OCR responses."),
    refine_max_tokens: int = typer.Option(64, "--refine-max-tokens", help="Max tokens for refine/search responses."),
    # web-grounded fallback
    use_search: bool = typer.Option(
        False,
        "--use-search",
        help="Use Google Search grounding as a fallback when local refine returns UNKNOWN_TITLE.",
    ),
):
    """
    Run RollCall on a media directory.
    """
    ocr_cfg = OCRConfig(
        delay_seconds=ocr_delay,
        variation_threshold=variation_threshold,
        fps_expr=fps,
        long_video_tail_sec=long_tail_sec,
        short_video_tail_sec=short_tail_sec,
        max_no_update=max_no_update,
    )
    # GeminiConfig currently carries model name; other knobs are set in core for simplicity.
    gemini_cfg = GeminiConfig(model_name=model)

    process_media_directory(
        directory=directory,
        api_key=api_key,
        ocr_cfg=ocr_cfg,
        gemini_cfg=gemini_cfg,
        dry_run=dry_run,
        verbose=not quiet,
        ocr_max_tokens=ocr_max_tokens,
        refine_max_tokens=refine_max_tokens,
        use_search=use_search,
    )


def entrypoint():
    # console_script target in pyproject.toml: rlcl = "rollcall.cli:entrypoint"
    app()


# Optional compatibility if any old wrapper points to rollcall.cli:main
def main():
    entrypoint()


if __name__ == "__main__":
    # Handy for VS Code "Python File" debugging:
    # import sys; sys.argv += ["run", "/absolute/path/to/media", "--dry-run"]
    entrypoint()
