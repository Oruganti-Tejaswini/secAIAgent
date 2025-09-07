import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
_API_KEY = os.getenv("GEMINI_API_KEY")
if not _API_KEY:
    raise RuntimeError("GEMINI_API_KEY missing")
_MODEL = os.getenv("GEMINI_MODEL", "models/gemini-1.5-flash")

genai.configure(api_key=_API_KEY)

class GeminiClient:
    def __init__(self, model: str | None = None):
        self.model = model or _MODEL

    def generate(self, prompt: str) -> str:
        model = genai.GenerativeModel(self.model)
        resp = model.generate_content(prompt)
        text = getattr(resp, "text", None)
        if text:
            return text.strip()

        candidates = getattr(resp, "candidates", [])
        if candidates and candidates[0].content.parts:
            return candidates[0].content.parts[0].text.strip()

        return ""
