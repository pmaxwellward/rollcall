# RollCall (UNRELEASED)

OCRs **end credits** from video files and renames them using Google’s Gemini models.
RollCall samples the tail of each video, extracts and aggregates film credits, then uses Gemini to determine the title of the media.
---

## Installation (dev)

**Requirements**
- Python ≥ 3.10
- FFmpeg (`ffmpeg`, `ffprobe`) on your `PATH`
- A Gemini API key (`GEMINI_API_KEY` preferred; `GOOGLE_API_KEY` also supported)

**Steps**
```bash
# from project root (where pyproject.toml lives)
python -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate
python -m pip install -U pip wheel
python -m pip install -e .

# set your key (bash/zsh)
export GEMINI_API_KEY="your-key-here"
# PowerShell:
# $env:GEMINI_API_KEY="your-key-here"
```

---

## Quick Start

Dry run (no changes):
```bash
rlcl --dry-run /path/to/media
```

Rename for real:
```bash
rlcl /path/to/media
```

Useful options:
```bash
# sample more frames (slower, higher recall)
rlcl --fps "1/2" /path/to/media

# add a small delay between OCR calls
rlcl --ocr-delay 0.2 /path/to/media

# disable grounded web search (local refine only)
rlcl --no-search /path/to/media

# override the model/API key for this run
rlcl --model gemini-2.5-flash --api-key "$GEMINI_API_KEY" /path/to/media
```

**Notes**
- Supports `.mp4`, `.mkv`, `.avi`, `.mov`.
- Project is **unreleased** and subject to change.