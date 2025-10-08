import os
from google import genai
from typing import Optional

def make_client(api_key: Optional[str] = None) -> genai.Client:
    # If the user passed --api-key, honor it. Otherwise the SDK uses GEMINI_API_KEY.
    if api_key:
        import os
        os.environ.setdefault("GEMINI_API_KEY", api_key)
    return genai.Client()