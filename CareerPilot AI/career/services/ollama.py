import json

import requests
from django.conf import settings

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = getattr(settings, "CAREER_OLLAMA_MODEL", "qwen2.5:3b")

FREE_RESOURCES = {
    "python": ["Official Python tutorial", "Exercism Python track"],
    "data": ["Kaggle Learn", "pandas getting-started guides"],
    "web": ["MDN Web Docs", "Django documentation"],
    "general": ["Official framework documentation", "GitHub Skills"],
}


def generate_json(prompt, timeout=120):
    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": MODEL, "prompt": prompt, "format": "json", "stream": False},
            timeout=timeout,
        )
        response.raise_for_status()
        content = response.json().get("response", "")
        result = json.loads(content)
    except (requests.RequestException, ValueError, TypeError):
        return None
    return result if isinstance(result, dict) else None


def _valid_roadmap(data):
    weeks = data.get("weeks") if isinstance(data, dict) else None
    if not isinstance(weeks, list) or len(weeks) != 4:
        return False
    for week in weeks:
        if not isinstance(week, dict):
            return False
        if not all(isinstance(week.get(key), str) and week[key].strip() for key in ("objective", "outcome")):
            return False
        if any(not isinstance(week.get(key), list) or not week[key] for key in ("topics", "tasks", "resources")):
            return False
        if any(not isinstance(item, str) or not item.strip() for key in ("topics", "tasks", "resources") for item in week[key]):
            return False
    return True


def _fallback_roadmap(analysis):
    missing = analysis.get("missing_skills", [])
    role = analysis["role"]
    focus = missing[:3] or [role]
    resource_set = FREE_RESOURCES["data"] if role == "Data Analyst" else (
        FREE_RESOURCES["web"] if role in {"Frontend Developer", "Full Stack Developer"} else FREE_RESOURCES["python"]
    )
    return {"weeks": [
        {"objective": "Build a reliable foundation", "topics": focus, "tasks": [
            f"Study the fundamentals of {focus[0]}", "Write concise notes and examples", "Complete five focused practice exercises"
        ], "outcome": "A small set of tested examples for the first skill gap", "resources": resource_set},
        {"objective": "Apply the skills in context", "topics": focus[:2], "tasks": [
            "Complete a guided exercise using the target stack", "Add input validation and error handling", "Review the implementation against official documentation"
        ], "outcome": "A working feature with a short explanation", "resources": resource_set},
        {"objective": "Create a portfolio artifact", "topics": focus, "tasks": [
            "Build a role-relevant mini-project", "Add tests or a documented validation checklist", "Write a README describing decisions and limitations"
        ], "outcome": f"A documented {role} project ready to publish", "resources": ["GitHub Skills", *resource_set[:1]]},
        {"objective": "Consolidate and communicate", "topics": analysis.get("interview_topics", [])[:3] or ["Project explanation"], "tasks": [
            "Explain the project design aloud in five minutes", "Answer three role-specific practice questions", "Choose the next skill gap based on your results"
        ], "outcome": "A recorded project walkthrough and next-step checklist", "resources": ["Official documentation", "GitHub Skills"]},
    ]}


def create_roadmap(analysis, github=None):
    profile_context = ", ".join(analysis.get("sections", {}).get("projects", "").splitlines()[:5])
    github_context = ", ".join(repo.get("name", "") for repo in (github or {}).get("top_repos", [])[:4])
    prompt = f"""Create a realistic four-week learning roadmap for a student targeting {analysis['role']}.
Matched skills: {', '.join(analysis.get('matched_skills', [])) or 'None detected'}.
Missing required skills: {', '.join(analysis.get('missing_skills', [])) or 'None detected'}.
Existing resume projects: {profile_context or 'No project section detected'}.
Public GitHub projects: {github_context or 'Not connected'}.
Return JSON only with this exact shape: {{"weeks":[{{"objective":"...","topics":["..."],"tasks":["..."],"outcome":"...","resources":["free resource title"]}}]}}.
Include exactly four weeks, at least two practical tasks per week, and only real free resource names. Never include URLs. Do not claim this predicts employment."""
    roadmap = generate_json(prompt)
    if _valid_roadmap(roadmap):
        resource_set = FREE_RESOURCES["data"] if analysis["role"] == "Data Analyst" else (
            FREE_RESOURCES["web"] if analysis["role"] in {"Frontend Developer", "Full Stack Developer"} else FREE_RESOURCES["python"]
        )
        for week in roadmap["weeks"]:
            week["resources"] = resource_set
        return {"source": "Ollama · " + MODEL, **roadmap}
    return {"source": "Built-in free fallback (local AI unavailable or returned invalid data)", **_fallback_roadmap(analysis)}
