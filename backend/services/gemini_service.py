
import json
import re
import time
import random
import os
from typing import Any, Dict, List

from google import genai
from google.genai import types


class AIServiceError(Exception):
    """Raised when Gemini API is not configured or returns an error."""

    def __init__(self, message: str, status_code: int = 503):
        super().__init__(message)
        self.status_code = status_code


class GeminiService:
    """Server-side wrapper for Google Gemini API educational accessibility tasks."""

    def __init__(
        self,
        api_key: str,
        model: str = None,
        fallback_model: str = None
    ):
        self.api_key = (api_key or "").strip()

        self.model = (
            model
            or os.getenv("GEMINI_MODEL")
            or "gemini-3.8-flash"
        ).strip()

        self.fallback_model = (
            fallback_model
            or os.getenv("GEMINI_FALLBACK_MODEL")
            or "gemini-3.5-flash-lite"
        ).strip()

        # Avoid retrying the same model twice.
        if self.fallback_model == self.model:
            self.fallback_model = None

        self.max_retries = 3

    def _get_client(self):
        if not self.api_key:
            raise AIServiceError(
                "Google Gemini API key is not configured on the server. "
                "Set GEMINI_API_KEY in backend/.env to enable AI features.",
                status_code=503,
            )

        return genai.Client(api_key=self.api_key)

    def _is_retryable_error(self, exc):
        """Identify temporary API errors that may succeed on retry."""

        status_code = (
            getattr(exc, "code", None)
            or getattr(exc, "status_code", None)
        )

        error_message = str(exc).upper()

        retryable_codes = {429, 500, 502, 503, 504}

        if status_code in retryable_codes:
            return True

        retryable_messages = [
            "503",
            "UNAVAILABLE",
            "429",
            "RESOURCE_EXHAUSTED",
            "500",
            "INTERNAL",
            "502",
            "504",
            "DEADLINE_EXCEEDED",
            "TIMEOUT",
        ]

        return any(
            message in error_message
            for message in retryable_messages
        )

    def _generate_with_retry(self, client, model, prompt, system_instruction):
        """Generate content with exponential backoff."""

        for attempt in range(self.max_retries):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        response_mime_type="application/json",
                        temperature=0.3,
                    ),
                )

                return response

            except Exception as exc:

                if not self._is_retryable_error(exc):
                    raise

                if attempt == self.max_retries - 1:
                    raise

                delay = (2 ** attempt) + random.uniform(0, 1)

                print(
                    f"Gemini model {model} temporarily unavailable. "
                    f"Retry {attempt + 1}/{self.max_retries - 1} "
                    f"in {delay:.2f} seconds."
                )

                time.sleep(delay)

    def _generate_json(self, prompt: str, system_instruction: str) -> Dict[str, Any]:

        client = self._get_client()

        models_to_try = [self.model]

        if self.fallback_model:
            models_to_try.append(self.fallback_model)

        last_error = None

        for model in models_to_try:
            try:
                print(f"Using Gemini model: {model}")

                response = self._generate_with_retry(
                    client=client,
                    model=model,
                    prompt=prompt,
                    system_instruction=system_instruction,
                )

                raw_text = getattr(response, "text", None) or ""

                if not raw_text.strip():
                    raise AIServiceError(
                        "Gemini AI returned an empty response. Please try again.",
                        status_code=502,
                    )

                cleaned = raw_text.strip()

                # Remove accidental Markdown code fences.
                cleaned = re.sub(
                    r"^```(?:json)?\s*", "", cleaned
                )
                cleaned = re.sub(
                    r"\s*```$", "", cleaned
                )

                try:
                    return json.loads(cleaned)

                except json.JSONDecodeError as exc:
                    raise AIServiceError(
                        "Gemini AI returned an unexpected response format. "
                        "Please try again.",
                        status_code=502,
                    ) from exc

            except AIServiceError:
                raise

            except Exception as exc:
                last_error = exc

                print(
                    f"Gemini model {model} failed: {str(exc)}"
                )

                # Try the fallback only for temporary failures.
                if not self._is_retryable_error(exc):
                    break

                if model != models_to_try[-1]:
                    print("Switching to fallback Gemini model...")

        error_message = str(last_error or "Unknown Gemini API error")

        status_code = (
            getattr(last_error, "code", None)
            or getattr(last_error, "status_code", None)
        )

        if status_code not in {429, 500, 502, 503, 504}:
            status_code = 502

        raise AIServiceError(
            f"Gemini AI is temporarily unavailable. "
            f"Please try again later. Details: {error_message}",
            status_code=status_code,
        ) from last_error


    def simplify_text(self, text: str, accessibility_modes: List[str] | None = None) -> Dict[str, Any]:
        modes_note = (
            f"Student accessibility preferences: {', '.join(accessibility_modes)}."
            if accessibility_modes
            else "Design for high readability and clarity."
        )
        system_instruction = (
            "You are an expert inclusive education specialist helping students with dyslexia, "
            "low vision, or hearing impairment understand academic content. "
            "You NEVER claim to diagnose any condition. "
            "Follow these strict rules:\n"
            "1. Use simple, everyday vocabulary where possible without losing academic accuracy.\n"
            "2. Break long complex sentences into shorter, clearer sentences.\n"
            "3. Organize output into short, clear paragraphs.\n"
            "4. Preserve all important academic concepts and factual meaning.\n"
            "5. Do not delete essential facts or invent new claims.\n"
            "6. Explain difficult terms in student-friendly language.\n"
            f"7. {modes_note}"
        )
        prompt = f"""
Analyze and simplify the following educational text.

Return a JSON object with this exact schema:
{{
  "simplified_text": "string (clear paragraphs separated by double newlines)",
  "reading_summary": "string (2-3 simple sentences summarizing the passage)",
  "difficult_words": [
    {{
      "word": "string",
      "simple_explanation": "string",
      "example": "string"
    }}
  ],
  "key_concepts": ["string"]
}}

Source Educational Text:
\"\"\"
{text[:18000]}
\"\"\"
"""
        data = self._generate_json(prompt, system_instruction)
        return {
            "simplified_text": str(data.get("simplified_text", "")).strip(),
            "reading_summary": str(data.get("reading_summary", "")).strip(),
            "difficult_words": data.get("difficult_words") or [],
            "key_concepts": data.get("key_concepts") or [],
        }

    def explain_word(self, word: str, context: str = "") -> Dict[str, Any]:
        system_instruction = (
            "You explain academic vocabulary simply and accurately for students who benefit "
            "from accessible, jargon-free explanations."
        )
        prompt = f"""
Explain the word or term "{word}" for a student.
Context from their study notes (if any): "{context[:1500]}"

Return JSON:
{{
  "word": "{word}",
  "simple_explanation": "string (plain-language definition)",
  "example": "string (a simple everyday or academic example sentence)",
  "syllables_hint": "string (optional syllable breakdown for easier reading, e.g. pho-to-syn-the-sis)"
}}
"""
        data = self._generate_json(prompt, system_instruction)
        return {
            "word": str(data.get("word", word)),
            "simple_explanation": str(data.get("simple_explanation", "")).strip(),
            "example": str(data.get("example", "")).strip(),
            "syllables_hint": str(data.get("syllables_hint", "")).strip(),
        }

    def generate_practice(
        self,
        document_title: str,
        text: str,
        question_count: int = 5,
        question_types: List[str] | None = None,
        difficulty: str = "mixed",
    ) -> Dict[str, Any]:
        types_list = question_types or ["multiple_choice", "short_answer", "concept"]
        system_instruction = (
            "You create accessible, clear, encouraging practice questions strictly grounded "
            "in the student's uploaded educational document. Use clear phrasing and short sentences."
        )
        prompt = f"""
Based ONLY on the educational material below from "{document_title}", generate {question_count} practice questions.
Allowed question_type values: {json.dumps(types_list)}.
Target difficulty: {difficulty} (each question's difficulty must be "easy", "medium", or "hard").

Rules:
- For "multiple_choice", provide 4 clear options in "options" and set "correct_answer" to match one of the options exactly.
- For "short_answer" and "concept", set "options" to [] and provide a clear model "correct_answer".
- Every question MUST include a simple, student-friendly "explanation" grounded in the text.

Return JSON:
{{
  "title": "string (concise practice set title)",
  "questions": [
    {{
      "id": "q1",
      "question_type": "multiple_choice | short_answer | concept",
      "difficulty": "easy | medium | hard",
      "question_text": "string",
      "options": ["string"],
      "correct_answer": "string",
      "explanation": "string"
    }}
  ]
}}

Document Text:
\"\"\"
{text[:18000]}
\"\"\"
"""
        data = self._generate_json(prompt, system_instruction)
        questions = data.get("questions") or []
        normalized = []
        for idx, q in enumerate(questions, start=1):
            q_type = q.get("question_type", "multiple_choice")
            if q_type not in {"multiple_choice", "short_answer", "concept"}:
                q_type = "short_answer"
            diff = q.get("difficulty", "medium")
            if diff not in {"easy", "medium", "hard"}:
                diff = "medium"
            normalized.append(
                {
                    "id": str(q.get("id") or f"q{idx}"),
                    "question_type": q_type,
                    "difficulty": diff,
                    "question_text": str(q.get("question_text", "")).strip(),
                    "options": q.get("options") if q_type == "multiple_choice" else [],
                    "correct_answer": str(q.get("correct_answer", "")).strip(),
                    "explanation": str(q.get("explanation", "")).strip(),
                }
            )
        return {
            "title": str(data.get("title") or f"Practice: {document_title}").strip(),
            "questions": normalized,
        }

    def evaluate_open_answers(self, items: List[Dict[str, str]]) -> Dict[str, Dict[str, Any]]:
        """Evaluate short-answer and concept questions using Gemini for fair semantic grading."""
        if not items:
            return {}
        system_instruction = (
            "You are a fair, supportive tutor grading a student's short-answer and concept responses. "
            "Accept answers that capture the core meaning even if worded differently or with minor spelling variations."
        )
        prompt = f"""
Evaluate each student response against the expected answer.

Items:
{json.dumps(items, indent=2)}

Return JSON:
{{
  "results": [
    {{
      "id": "string",
      "is_correct": true,
      "feedback": "string (short, clear, encouraging feedback)"
    }}
  ]
}}
"""
        data = self._generate_json(prompt, system_instruction)
        output = {}
        for r in data.get("results") or []:
            qid = str(r.get("id", ""))
            if qid:
                output[qid] = {
                    "is_correct": bool(r.get("is_correct", False)),
                    "feedback": str(r.get("feedback", "")).strip(),
                }
        return output

    def generate_revision_plan(
        self,
        accessibility_modes: List[str],
        documents_summary: List[Dict[str, Any]],
        attempts_summary: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        system_instruction = (
            "You are an inclusive learning coach creating realistic, accessible study and revision plans. "
            "Never diagnose any learning or sensory condition. Keep steps short, structured, and encouraging."
        )
        prompt = f"""
Create a personalised revision plan for a student based on their uploaded materials and recent practice performance.

Student accessibility preferences: {json.dumps(accessibility_modes)}
Uploaded documents: {json.dumps(documents_summary[:10])}
Recent practice attempts: {json.dumps(attempts_summary[:10])}

Return JSON:
{{
  "plan_title": "string",
  "summary": "string (2-3 simple sentences)",
  "focus_areas": ["string"],
  "daily_steps": [
    {{
      "step_number": 1,
      "title": "string",
      "activity": "string (clear actionable instruction using accessible tools like reader, TTS, or practice)",
      "duration_minutes": 15
    }}
  ],
  "accessibility_tips": ["string"]
}}
"""
        data = self._generate_json(prompt, system_instruction)
        return {
            "plan_title": str(data.get("plan_title", "Your Personalised Revision Plan")).strip(),
            "summary": str(data.get("summary", "")).strip(),
            "focus_areas": data.get("focus_areas") or [],
            "daily_steps": data.get("daily_steps") or [],
            "accessibility_tips": data.get("accessibility_tips") or [],
        }
