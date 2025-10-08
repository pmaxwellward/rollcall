from typing import Dict, Set, List
from .types import OCRResult, CreditsMap

def merge_pair_entries(agg: Dict[str, Set[str]], obj: OCRResult) -> None:
    for e in obj.get("entries", []):
        key = e["key"].strip()
        if not key:
            continue
        bucket = agg.setdefault(key, set())
        for v in e["values"]:
            val = " ".join(str(v).split()).strip()
            if val:
                bucket.add(val)

def map_trim(credits_map: Dict[str, Set[str]], per_key: int = 12) -> Dict[str, List[str]]:
    return {k: sorted(list(v))[:per_key] for k, v in credits_map.items()}
