import re

import pymupdf

from django.conf import settings

SKILL_KEYWORDS = [
    "python", "java", "javascript", "typescript", "c++", "sql", "mysql",
    "postgresql", "html", "css", "bootstrap", "react", "node.js", "django",
    "flask", "fastapi", "git", "github", "rest api", "machine learning",
    "deep learning", "nlp", "pandas", "numpy", "matplotlib", "power bi",
    "tableau", "excel", "data analysis", "statistics", "scikit-learn",
    "tensorflow", "pytorch", "docker", "aws", "azure", "linux", "data structures",
    "algorithms", "oop", "mongodb", "firebase", "pytest", "matplotlib"
]

SECTION_ALIASES = {
    "education": {"education", "academic background", "academics"},
    "experience": {"experience", "work experience", "employment", "internship"},
    "projects": {"projects", "personal projects", "academic projects"},
    "skills": {"skills", "technical skills", "technology"},
    "summary": {"summary", "profile", "objective", "professional summary"},
}

def extract_pdf_text(file_bytes):
    try:
        with pymupdf.open(stream=file_bytes, filetype="pdf") as doc:
            text = "\n".join(page.get_text("text") for page in doc)
    except Exception as exc:
        raise ValueError("The uploaded file is not a readable PDF.") from exc
    return text


def extract_resume_sections(text):
    sections = {name: "" for name in SECTION_ALIASES}
    current = None
    chunks = {name: [] for name in sections}
    aliases = {
        re.sub(r"[^a-z ]", "", alias.lower()): name
        for name, values in SECTION_ALIASES.items()
        for alias in values
    }
    for line in text.splitlines():
        normalized = re.sub(r"[^a-z ]", "", line.lower()).strip()
        heading = aliases.get(normalized)
        if heading:
            current = heading
            continue
        if current and line.strip():
            chunks[current].append(line.strip())
    for name, lines in chunks.items():
        sections[name] = "\n".join(lines).strip()
    return sections

def detect_skills(text):
    normalized = re.sub(r"\s+", " ", text.lower())
    configured_keywords = getattr(settings, "CAREER_SKILL_KEYWORDS", None) or SKILL_KEYWORDS
    return sorted({
        skill.lower() for skill in configured_keywords
        if re.search(rf"(?<!\w){re.escape(skill.lower())}(?!\w)", normalized)
    })
