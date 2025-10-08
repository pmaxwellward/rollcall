from pathlib import Path
from PIL import Image

def image_has_text(frame_path: Path, variation_threshold: float = 0.0) -> bool:
    """
    Quick and cheap heuristic: if grayscale extrema are identical,
    there is likely no text or variation.
    """
    with Image.open(frame_path).convert("L") as img:
        lo, hi = img.getextrema()
    return hi > (lo + variation_threshold)
