import re

import requests

from .matching import ROLE_PROFILES

API = "https://api.github.com"
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")


def _get_json(url, params=None):
    headers = {"Accept": "application/vnd.github+json"}
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
    except requests.RequestException as exc:
        raise ConnectionError("GitHub could not be reached. Check the connection and try again.") from exc
    if response.status_code == 403 and response.headers.get("X-RateLimit-Remaining") == "0":
        raise ValueError("GitHub's public API rate limit is temporarily exhausted. Try again later.")
    if response.status_code == 404:
        raise ValueError("GitHub username not found.")
    try:
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise ValueError("GitHub could not return this public profile right now.") from exc
    except ValueError as exc:
        raise ValueError("GitHub returned an unreadable response.") from exc


def fetch_github_profile(username, role=None):
    username = username.strip()
    if not USERNAME_PATTERN.fullmatch(username):
        raise ValueError("Enter a valid public GitHub username.")
    user = _get_json(f"{API}/users/{username}")
    if not isinstance(user, dict):
        raise ValueError("GitHub returned an unexpected profile response.")
    repos = _get_json(
        f"{API}/users/{username}/repos",
        params={"per_page": 100, "sort": "updated", "type": "owner"},
    )
    if not isinstance(repos, list):
        raise ValueError("GitHub returned an unexpected repository list.")

    languages = {}
    for repo in repos:
        lang = repo.get("language")
        if lang:
            languages[lang] = languages.get(lang, 0) + 1

    profile = ROLE_PROFILES.get(role, {})
    relevant_terms = set(profile.get("required", []) + profile.get("preferred", []))
    recognized_skills = {
        term.lower()
        for role_profile in ROLE_PROFILES.values()
        for term in role_profile["required"] + role_profile["preferred"]
    }
    portfolio_skills = set()
    for repo in repos:
        description = str(repo.get("description") or "").lower()
        for skill in recognized_skills:
            if re.search(rf"(?<!\w){re.escape(skill)}(?!\w)", description):
                portfolio_skills.add(skill.lower())
    normalized_repos = [{
        "name": r.get("name"),
        "description": r.get("description") or "No description provided",
        "language": r.get("language") or "Not specified",
        "stars": r.get("stargazers_count", 0),
        "forks": r.get("forks_count", 0),
        "updated_at": r.get("updated_at"),
        "pushed_at": r.get("pushed_at"),
        "url": r.get("html_url"),
        "relevance": sum(
            bool(re.search(
                rf"(?<!\w){re.escape(term)}(?!\w)",
                f"{r.get('name', '')} {r.get('description') or ''} {r.get('language') or ''}".lower(),
            ))
            for term in relevant_terms
        ),
    } for r in repos]
    normalized_repos.sort(key=lambda repo: (repo["relevance"], repo["updated_at"] or ""), reverse=True)
    top_repos = normalized_repos[:6]

    return {
        "name": user.get("name") or username,
        "username": username,
        "avatar": user.get("avatar_url"),
        "bio": user.get("bio") or "No bio available",
        "public_repos": user.get("public_repos", 0),
        "followers": user.get("followers", 0),
        "profile_url": user.get("html_url"),
        "languages": languages,
        "portfolio_skills": sorted(portfolio_skills),
        "portfolio_skills_source": "Explicit mentions in public repository descriptions only; repository languages are not treated as proficiency.",
        "top_repos": top_repos,
        "repository_count": user.get("public_repos", len(repos)),
        "analyzed_repository_count": len(repos),
        "total_stars": sum(repo["stars"] for repo in normalized_repos),
        "total_forks": sum(repo["forks"] for repo in normalized_repos),
        "role": role or "",
        "portfolio_summary": (
            f"{len(repos)} public repositories, {len(languages)} primary languages, "
            f"{sum(repo['stars'] for repo in normalized_repos)} stars and "
            f"{sum(repo['forks'] for repo in normalized_repos)} forks."
        ),
    }
