import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

for m in genai.list_models():
    methods = getattr(m, "supported_generation_methods", [])
    if "generateContent" in methods:
        print(m.name, "|", methods)
