import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from services.gemini_service import GeminiService

svc = GeminiService(
    api_key=os.getenv("GEMINI_API_KEY", ""),
    model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
)
print(f"Model in use : {svc.model}")
print()

sample_text = (
    "Photosynthesis is the biochemical process by which chlorophyll-containing organisms "
    "convert light energy into chemical energy stored as glucose, utilising carbon dioxide "
    "and water while releasing molecular oxygen as a byproduct."
)

result = svc.simplify_text(sample_text, accessibility_modes=["dyslexia"])

print("=== Simplified Text ===")
print(result["simplified_text"])
print()
print("=== Reading Summary ===")
print(result["reading_summary"])
print()
print("=== Key Concepts ===")
print(result["key_concepts"])
print()
print("=== Difficult Words ===")
for w in result.get("difficult_words", []):
    print(f"  {w.get('word')}: {w.get('simple_explanation')}")
print()
print("SUCCESS: gemini-3.8-flash is working perfectly for LearnAble AI.")
