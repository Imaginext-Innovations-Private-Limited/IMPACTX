import re

from .matching import ROLE_PROFILES
from .ollama import generate_json


RUBRIC_WEIGHTS = {
    "relevance": 25,
    "technical_correctness": 35,
    "completeness": 20,
    "practical_understanding": 10,
    "clarity": 10,
}


CONCEPT_SETS = {
    "Python data model": ["class", "dataclass", "attribute", "method", "dunder", "__init__", "type hint", "validation", "test"],
    "HTTP and REST": ["endpoint", "method", "get", "post", "put", "delete", "status code", "json", "validation", "authentication"],
    "SQL joins": ["join", "inner join", "left join", "on", "primary key", "foreign key", "null", "duplicate", "result"],
    "Testing strategy": ["unit test", "integration test", "edge case", "invalid input", "assert", "pytest", "mock", "test data", "response"],
    "SQL aggregation": ["group by", "aggregate", "count", "sum", "average", "having", "where", "null"],
    "Data cleaning": ["missing", "duplicate", "outlier", "data type", "dtype", "impute", "validation", "normalization"],
    "Statistical significance": ["null hypothesis", "p-value", "confidence interval", "sample", "significance", "effect size", "assumption"],
    "Dashboard design": ["metric", "filter", "chart", "audience", "compare", "drilldown", "layout", "accessibility"],
    "Bias and variance": ["bias", "variance", "overfit", "underfit", "cross-validation", "regularization", "training", "validation"],
    "Evaluation metrics": ["precision", "recall", "accuracy", "f1", "roc", "confusion matrix", "baseline", "trade-off"],
    "Feature engineering": ["feature", "encoding", "scaling", "missing", "selection", "leakage", "transformation", "validation"],
    "Model deployment": ["api", "endpoint", "monitor", "latency", "version", "container", "docker", "drift", "rollback"],
    "DOM and events": ["dom", "event", "listener", "button", "preventdefault", "bubbling", "delegation", "state"],
    "CSS layout": ["flex", "grid", "responsive", "breakpoint", "box model", "media query", "accessibility", "overflow"],
    "React state": ["state", "props", "component", "hook", "render", "effect", "controlled", "immutability"],
    "Web accessibility": ["keyboard", "focus", "aria", "label", "contrast", "semantic", "screen reader", "tab"],
    "Request lifecycle": ["request", "route", "middleware", "controller", "database", "response", "authentication", "error"],
    "Database design": ["table", "schema", "primary key", "foreign key", "normalization", "index", "relationship", "constraint"],
    "API security": ["authentication", "authorization", "input validation", "csrf", "cors", "secret", "rate limit", "tls"],
    "Frontend-backend integration": ["api", "json", "http", "request", "response", "error", "loading", "authentication"],
}


def interview_questions(role):
    profile = ROLE_PROFILES.get(role, ROLE_PROFILES["Python Developer"])
    templates = {
        "Python Developer": [
            "How would you design and test a {topic} feature in a Python service?",
            "Describe a production issue involving {topic} and how you would investigate it.",
        ],
        "Data Analyst": [
            "How would you use {topic} to answer a business question from a messy dataset?",
            "What checks would you make before presenting an analysis of {topic}?",
        ],
        "Machine Learning Engineer": [
            "How would you apply {topic} while building a reliable machine-learning pipeline?",
            "What trade-offs would you consider when evaluating {topic} in a model?",
        ],
        "Frontend Developer": [
            "How would you implement {topic} in an accessible, responsive interface?",
            "How would you debug a user-facing issue related to {topic}?",
        ],
        "Full Stack Developer": [
            "How would you implement {topic} across the frontend and backend?",
            "What security and testing concerns matter for {topic} in a full-stack application?",
        ],
    }
    questions = templates.get(role, templates["Python Developer"])
    return [questions[index % len(questions)].format(topic=topic) for index, topic in enumerate(profile["interview_topics"][:4])]


ROLE_QUESTION_FALLBACKS = {
    "Python Developer": [
        "How would you use Python classes and object-oriented principles to model a real application feature?",
        "How would you design and test a Django REST API with validation and authentication?",
        "How would you optimize a slow Python data-processing function using profiling and data structures?",
        "How would you investigate and fix a production error in a Flask or Django service?",
    ],
    "Data Analyst": [
        "How would you clean a messy SQL or CSV dataset before analysis?",
        "How would you use SQL aggregation and joins to answer a business question?",
        "How would you communicate an analysis using Power BI or Tableau?",
        "How would you validate that a statistical conclusion is reliable?",
    ],
    "Machine Learning Engineer": [
        "How would you split data and prevent leakage in a machine-learning pipeline?",
        "How would you choose and interpret evaluation metrics for an imbalanced classification problem?",
        "How would you engineer features and control overfitting?",
        "How would you deploy, monitor, and update a trained model?",
    ],
    "Frontend Developer": [
        "How would you build an accessible, responsive layout with HTML and CSS?",
        "How would you manage state in a React application?",
        "How would you debug DOM event bubbling or a user-facing JavaScript issue?",
        "How would you optimize browser rendering and loading performance?",
    ],
    "Full Stack Developer": [
        "How would you connect a frontend form to a secure backend API?",
        "How would you design database tables and relationships for an application?",
        "How would authentication and authorization work in a full-stack application?",
        "How would you test, secure, and deploy a full-stack feature?",
    ],
}


def generate_interview_questions(role):
    if role not in ROLE_PROFILES:
        role = "Python Developer"
    prompt = f"""Generate exactly four distinct interview questions for a {role} candidate.
Cover role-specific fundamentals, implementation, debugging or analysis, and trade-offs.
The questions must be suitable for written answers and directly relevant to {role}.
Return JSON only with this exact shape: {{"questions":["question 1","question 2","question 3","question 4"]}}."""
    result = generate_json(prompt, timeout=60)
    questions = result.get("questions") if isinstance(result, dict) else None
    if (
        isinstance(questions, list)
        and len(questions) == 4
        and all(isinstance(question, str) and question.strip() for question in questions)
        and len(set(question.strip() for question in questions)) == 4
    ):
        return [question.strip() for question in questions]
    return ROLE_QUESTION_FALLBACKS.get(role, ROLE_QUESTION_FALLBACKS["Python Developer"])


def evaluate_answer(role, question, answer):
    answer = str(answer or "").strip()
    if not answer:
        return _fallback_feedback(question, answer)

    prompt = f"""Evaluate this practice interview answer for a student targeting {role}.
Exact interview question: {question}
Submitted answer: {answer}
Use this rubric with weights: relevance 25%, technical correctness 35%, completeness 20%, practical understanding 10%, clarity 10%.
Return JSON only with this exact shape:
{{"rubric":{{"relevance":0-100,"technical_correctness":0-100,"completeness":0-100,"practical_understanding":0-100,"clarity":0-100}},"feedback":"answer-specific feedback","strengths":["demonstrated point"],"improvements":["missing or incorrect point"],"got_right":["specific correct content"],"incorrect":["specific incorrect content"],"missing":["important missing concept"],"suggested_answer_structure":"specific structure for this answer"}}
Assess only the submitted answer against the exact question and the expected technical concepts. Do not award marks for technical keywords alone or for an unrelated answer. Every array item must describe evidence in the submitted answer. This is practice feedback, not an employer assessment."""
    result = generate_json(prompt, timeout=60)
    if _valid_feedback(result):
        rubric = result.get("rubric")
        if isinstance(rubric, dict):
            result["score"] = round(sum(
                _bounded_score(rubric.get(key)) * weight / 100
                for key, weight in RUBRIC_WEIGHTS.items()
            ))
            result["rubric"] = {key: _bounded_score(rubric.get(key)) for key in RUBRIC_WEIGHTS}
        else:
            result["score"] = _bounded_score(result.get("score"))
        result.setdefault("got_right", [])
        result.setdefault("incorrect", [])
        result.setdefault("missing", [])
        result.setdefault("suggested_answer_structure", "")
        result["source"] = "Local AI · Ollama · qwen2.5:3b"
        return result
    return _fallback_feedback(question, answer)


def _valid_feedback(result):
    if not isinstance(result, dict):
        return False
    if not isinstance(result.get("feedback"), str) or not result["feedback"].strip():
        return False
    for key in ("strengths", "improvements"):
        if not isinstance(result.get(key), list) or not all(isinstance(item, str) and item.strip() for item in result[key]):
            return False
    rubric = result.get("rubric")
    if rubric is not None:
        if not isinstance(rubric, dict):
            return False
        if not all(isinstance(rubric.get(key), (int, float)) and not isinstance(rubric.get(key), bool) and 0 <= rubric[key] <= 100 for key in RUBRIC_WEIGHTS):
            return False
    elif not isinstance(result.get("score"), (int, float)) or isinstance(result.get("score"), bool):
        return False
    return 0 <= _bounded_score(result.get("score", 0)) <= 100


def _bounded_score(value):
    try:
        return max(0, min(100, round(float(value))))
    except (TypeError, ValueError):
        return 0


def _expected_concepts(question):
    for topic, concepts in CONCEPT_SETS.items():
        if topic.lower() in question.lower():
            return concepts
    lowered = question.lower()
    if "test" in lowered:
        return CONCEPT_SETS["Testing strategy"]
    if "api" in lowered or "rest" in lowered:
        return CONCEPT_SETS["HTTP and REST"]
    if "database" in lowered or "sql" in lowered:
        return CONCEPT_SETS["Database design"]
    if "data" in lowered:
        return CONCEPT_SETS["Data cleaning"]
    if "interface" in lowered or "accessible" in lowered:
        return CONCEPT_SETS["Web accessibility"]
    if "security" in lowered:
        return CONCEPT_SETS["API security"]
    return ["approach", "reasoning", "implementation", "validation", "trade-off"]


def _concept_present(answer, concept):
    if len(concept) <= 3:
        return re.search(rf"\b{re.escape(concept)}\b", answer) is not None
    return concept in answer


def _detect_incorrect_claims(answer):
    incorrect = []
    contradiction_patterns = [
        ("inner join", "an inner join excludes unmatched rows"),
        ("left join", "a left join retains unmatched rows from the left table"),
        ("overfit", "overfitting means low training error with poor generalization"),
        ("precision", "precision is true positives divided by predicted positives"),
        ("recall", "recall is true positives divided by actual positives"),
    ]
    for concept, explanation in contradiction_patterns:
        if concept in answer:
            continue
    if "always correct" in answer or "all answers" in answer:
        incorrect.append("The answer makes an absolute claim without accounting for context or validation.")
    if "there is no difference" in answer:
        incorrect.append("The answer may be dismissing an important technical distinction.")
    return incorrect


def _suggested_structure(question, present, missing):
    parts = [
        f"Answer the question directly: {question}",
        "Define the core concept or approach.",
    ]
    if present:
        parts.append("Build on the concepts already used: " + ", ".join(present[:4]) + ".")
    if missing:
        parts.append("Include: " + ", ".join(missing[:5]) + ".")
    parts.append("Give one concrete example and explain how you would test or validate the result.")
    return " ".join(parts)


def _fallback_feedback(question, answer):
    answer = str(answer or "").strip()
    if not answer:
        return {
            "score": 0,
            "rubric": {"relevance": 0, "technical_correctness": 0, "completeness": 0, "practical_understanding": 0, "clarity": 0},
            "feedback": "No answer was submitted.",
            "strengths": [],
            "improvements": ["Answer the question and include the relevant concepts and reasoning."],
            "got_right": [],
            "incorrect": [],
            "missing": ["The complete answer to the interview question"],
            "suggested_answer_structure": "Start by defining the approach, explain the key concepts, show a concrete step or example, and finish with trade-offs or validation.",
            "source": "Built-in practice rubric (local AI unavailable)",
        }

    normalized = answer.lower()
    concepts = _expected_concepts(question)
    present = [concept for concept in concepts if _concept_present(normalized, concept)]
    missing = [concept for concept in concepts if concept not in present]

    words = re.findall(r"[a-z0-9+#.-]+", normalized)
    question_terms = set(re.findall(r"[a-z0-9+#.-]+", question.lower()))
    stop = {"how", "what", "when", "where", "which", "would", "would", "you", "the", "a", "an", "to", "of", "in", "for", "with", "from", "and", "or"}
    meaningful_question_terms = question_terms - stop
    meaningful_answer_terms = set(words) - stop
    term_overlap = len(meaningful_question_terms & meaningful_answer_terms)
    coverage = len(present) / len(concepts) if concepts else 0
    relevant_topic = bool(present) or (len(meaningful_question_terms) > 0 and term_overlap >= 2)

    relevance = 100 if relevant_topic and (coverage >= 0.25 or term_overlap >= 2) else (20 if term_overlap else 0)
    technical = round(coverage * 100)
    completeness = round(coverage * 80 + min(len(words), 80) / 80 * 20)
    completeness = min(completeness, 100)

    practical_terms = ["example", "for example", "test", "testing", "measure", "metric", "implement", "api", "database", "query", "component", "chart", "pipeline", "deploy"]
    practical_hits = sum(term in normalized for term in practical_terms)
    practical = min(100, practical_hits * 25 + (20 if len(words) >= 25 else 0))

    sentence_count = max(1, len(re.findall(r"[.!?]+", answer)))
    if len(words) >= 40 and sentence_count >= 2:
        clarity = 90
    elif len(words) >= 20:
        clarity = 75
    elif len(words) >= 8:
        clarity = 55
    else:
        clarity = 25

    if not relevant_topic:
        relevance = 0
        technical = 0
        completeness = 0
        practical = 0
    elif technical < 20:
        technical = min(technical, 15)

    rubric = {
        "relevance": round(relevance),
        "technical_correctness": round(technical),
        "completeness": round(completeness),
        "practical_understanding": round(practical),
        "clarity": round(clarity),
    }
    score = round(sum(rubric[key] * weight / 100 for key, weight in RUBRIC_WEIGHTS.items()))

    got_right = [f"The answer mentions {concept}." for concept in present[:4]]
    strengths = got_right[:3] if got_right else []
    incorrect = _detect_incorrect_claims(normalized)
    improvements = []
    if missing:
        improvements.append("Cover missing concepts: " + ", ".join(missing[:5]) + ".")
    if practical < 50:
        improvements.append("Add a concrete implementation step, example, test, or measurable result.")
    if score < 50:
        improvements.append("Connect the explanation directly to the interview question instead of giving an unrelated or generic response.")
    if not improvements:
        improvements.append("Make the trade-offs and validation criteria explicit.")

    feedback = (
        "This answer is largely unrelated to the question." if not relevant_topic
        else f"The answer demonstrates some relevant understanding across {len(present)} expected concept areas."
        if present
        else "The answer does not yet demonstrate the expected technical concepts."
    )
    return {
        "score": score,
        "rubric": rubric,
        "feedback": feedback,
        "strengths": strengths,
        "improvements": improvements,
        "got_right": got_right,
        "incorrect": incorrect,
        "missing": missing[:8],
        "suggested_answer_structure": _suggested_structure(question, present, missing),
        "source": "Built-in practice rubric (local AI unavailable)",
    }


def summarize_interview(answer_records):
    if not answer_records:
        return {"score": 0, "strengths": [], "improvements": [], "message": "No answers were recorded."}
    feedback = [record.feedback for record in answer_records]
    strengths = list(dict.fromkeys(item for item in feedback for item in item.get("strengths", [])))[:5]
    improvements = list(dict.fromkeys(item for item in feedback for item in item.get("improvements", [])))[:5]
    score = round(sum(item.get("score", 0) for item in feedback) / len(feedback))
    sources = [item.get("source", "") for item in feedback]
    local_used = any(source.startswith("Local AI") for source in sources)
    fallback_used = any(source.startswith("Built-in") for source in sources)
    evaluator = (
        "Local AI · Ollama · qwen2.5:3b" if local_used and not fallback_used
        else "Rubric fallback" if fallback_used and not local_used
        else "Mixed: Local AI and Rubric fallback"
    )
    return {
        "score": score,
        "strengths": strengths,
        "improvements": improvements,
        "got_right": list(dict.fromkeys(item for record in feedback for item in record.get("got_right", [])))[:5],
        "missing": list(dict.fromkeys(item for record in feedback for item in record.get("missing", [])))[:5],
        "evaluator": evaluator,
        "message": "Practice performance summary based on the submitted answers; not an employer assessment.",
    }
