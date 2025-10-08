from typing import Mapping, Iterable, Set, Dict, List, TypedDict

CreditsMap = Mapping[str, Iterable[str]]

class OCRPair(TypedDict):
    key: str
    values: List[str]

class OCRResult(TypedDict):
    entries: List[OCRPair]
