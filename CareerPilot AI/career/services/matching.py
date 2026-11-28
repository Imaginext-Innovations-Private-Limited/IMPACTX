ROLE_PROFILES = {
    "Python Developer": {
        "required": ["python", "django", "flask", "rest api", "sql", "git", "oop", "data structures", "algorithms"],
        "preferred": ["fastapi", "docker", "postgresql", "pytest"],
        "tools": ["Git", "PostgreSQL", "Docker", "pytest"],
        "projects": ["REST API with authentication", "Tested Django service"],
        "interview_topics": ["Python data model", "HTTP and REST", "SQL joins", "Testing strategy"],
    },
    "Data Analyst": {
        "required": ["python", "sql", "excel", "power bi", "tableau", "pandas", "numpy", "statistics", "data analysis"],
        "preferred": ["matplotlib", "postgresql", "machine learning"],
        "tools": ["Jupyter", "Power BI", "Tableau", "PostgreSQL"],
        "projects": ["Exploratory analysis with a public dataset", "Interactive business dashboard"],
        "interview_topics": ["SQL aggregation", "Data cleaning", "Statistical significance", "Dashboard design"],
    },
    "Machine Learning Engineer": {
        "required": ["python", "machine learning", "deep learning", "pandas", "numpy", "scikit-learn", "statistics", "sql"],
        "preferred": ["tensorflow", "pytorch", "docker", "nlp"],
        "tools": ["scikit-learn", "PyTorch", "TensorFlow", "Docker"],
        "projects": ["Reproducible model training pipeline", "Deployed model API with evaluation"],
        "interview_topics": ["Bias and variance", "Evaluation metrics", "Feature engineering", "Model deployment"],
    },
    "Frontend Developer": {
        "required": ["html", "css", "javascript", "typescript", "react", "bootstrap", "git", "rest api"],
        "preferred": ["node.js", "firebase", "algorithms"],
        "tools": ["React", "Vite", "Browser devtools", "Git"],
        "projects": ["Accessible responsive dashboard", "API-powered interactive application"],
        "interview_topics": ["DOM and events", "CSS layout", "React state", "Web accessibility"],
    },
    "Full Stack Developer": {
        "required": ["html", "css", "javascript", "python", "django", "node.js", "sql", "rest api", "git"],
        "preferred": ["react", "docker", "postgresql", "aws"],
        "tools": ["Django", "React", "PostgreSQL", "Docker"],
        "projects": ["Authenticated full-stack application", "CRUD app with documented API"],
        "interview_topics": ["Request lifecycle", "Database design", "API security", "Frontend-backend integration"],
    },
}

ALTERNATIVE_ROLE_MIN_MANDATORY_COVERAGE = 0.5

def analyze_match(student_skills, role, github_skills=None):
    if role not in ROLE_PROFILES:
        role = "Python Developer"
    profile = ROLE_PROFILES[role]
    resume_skills = {str(skill).strip().lower() for skill in student_skills if str(skill).strip()}
    github_skills = {
        str(skill).strip().lower()
        for skill in (github_skills or [])
        if str(skill).strip()
    }
    skills = resume_skills | github_skills
    required = profile["required"]
    preferred = profile["preferred"]
    required = list(dict.fromkeys(str(skill).strip().lower() for skill in required if str(skill).strip()))
    preferred = list(dict.fromkeys(str(skill).strip().lower() for skill in preferred if str(skill).strip()))
    preferred = [skill for skill in preferred if skill not in required]
    have = [skill for skill in required if skill in skills]
    have_preferred = [skill for skill in preferred if skill in skills]
    missing = [skill for skill in required if skill not in skills]
    missing_preferred = [skill for skill in preferred if skill not in skills]
    required_coverage = len(have) / len(required) if required else 0
    preferred_coverage = len(have_preferred) / len(preferred) if preferred else 0
    if preferred:
        score = round(100 * (0.80 * required_coverage + 0.20 * preferred_coverage))
    else:
        score = round(100 * required_coverage)
    perfect_match = not missing
    all_defined_requirements_satisfied = perfect_match and not missing_preferred
    if score == 100 and not perfect_match:
        score = 99
    mandatory_coverage = round(required_coverage * 100)
    optional_coverage = round(preferred_coverage * 100) if preferred else None
    readiness_status = (
        "NO MANDATORY SKILL ENHANCEMENT REQUIRED"
        if perfect_match
        else "SKILL ENHANCEMENT REQUIRED"
    )
    category = (
        "Perfect Match" if perfect_match else
        "Strong Match" if score >= 75 else
        "Moderate Match" if score >= 50 else
        "Needs Improvement"
    )
    recommendations = []
    for skill in missing:
        index = required.index(skill)
        priority_boundary = len(required) / 3
        priority = "High" if index < priority_boundary else (
            "Medium" if index < priority_boundary * 2 else "Low"
        )
        recommendations.append({
            "skill": skill,
            "priority": priority,
            "sequence": len(recommendations) + 1,
        })
    if preferred:
        expected_score = round(100 * (0.80 + 0.20 * preferred_coverage))
    else:
        expected_score = 100
    if missing_preferred and expected_score == 100:
        expected_score = 99
    return {
        "role": role,
        "score": score,
        "mandatory_coverage": mandatory_coverage,
        "optional_coverage": optional_coverage,
        "ready_for_role": perfect_match,
        "readiness_status": readiness_status,
        "match_category": category,
        "perfect_match": perfect_match,
        "all_defined_requirements_satisfied": all_defined_requirements_satisfied,
        "student_skills": sorted(skills),
        "resume_skills": sorted(resume_skills),
        "github_skills": sorted(github_skills),
        "matched_skills": have,
        "github_matched_skills": [skill for skill in have if skill not in resume_skills and skill in github_skills],
        "missing_skills": missing,
        "required_skills": required,
        "preferred_skills": have_preferred,
        "missing_preferred_skills": missing_preferred,
        "enhancement_recommendations": recommendations,
        "enhancement_priority": recommendations[0]["priority"] if recommendations else None,
        "expected_score_after_mandatory_skills": expected_score,
        "expected_score_note": "Indicative estimate assuming the listed mandatory skills are acquired; it does not predict hiring outcomes.",
        "skill_breakdown": [
            {"skill": skill, "category": "Required", "matched": skill in skills}
            for skill in required
        ] + [
            {"skill": skill, "category": "Preferred", "matched": skill in skills}
            for skill in preferred
        ],
        "tools": profile["tools"],
        "suggested_projects": profile["projects"],
        "interview_topics": profile["interview_topics"],
        "score_explanation": "Score = 80% mandatory-skill coverage + 20% optional-skill coverage. If no optional skills are defined, mandatory coverage is used for the full score. Readiness is determined only by mandatory skill coverage. This is an indicative compatibility estimate, not a hiring probability or guarantee.",
        "total_required": len(required),
    }


def recommend_alternative_roles(student_skills, selected_role, github_skills=None):
    """Compare the user's profile with every supported role except the target role.

    The returned groups deliberately keep immediately applicable roles separate from
    roles that need mandatory skill enhancement. GitHub skills are expected to be
    explicit terms extracted from repository descriptions by the GitHub service.
    """
    recommendations = []
    for role in ROLE_PROFILES:
        if role == selected_role:
            continue
        match = analyze_match(student_skills, role, github_skills)
        if match["mandatory_coverage"] / 100 < ALTERNATIVE_ROLE_MIN_MANDATORY_COVERAGE:
            continue
        matched = match["matched_skills"]
        source_note = (
            " and explicit public project descriptions"
            if match["github_matched_skills"] else ""
        )
        if matched:
            skill_text = ", ".join(matched)
            explanation = (
                f"Your {skill_text} skills{source_note} make you a potential match "
                "for this role."
            )
        else:
            explanation = "This role is included because its defined requirements are close to your current profile."
        if match["ready_for_role"]:
            explanation += " You already satisfy the defined mandatory technical requirements."
        else:
            explanation += " A small set of mandatory skills would still need to be developed."
        recommendations.append({
            **match,
            "matched_mandatory_skills": matched,
            "missing_mandatory_skills": match["missing_skills"],
            "missing_optional_skills": match["missing_preferred_skills"],
            "matched_mandatory_count": len(matched),
            "explanation": explanation,
        })

    ready = sorted(
        (item for item in recommendations if item["ready_for_role"]),
        key=lambda item: (-item["score"], item["role"]),
    )
    enhancement = sorted(
        (item for item in recommendations if not item["ready_for_role"]),
        key=lambda item: (-item["mandatory_coverage"], -item["score"], item["role"]),
    )
    return {"ready": ready, "enhancement": enhancement}
