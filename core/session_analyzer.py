def analyze_session(row):
    """Analyze an SSH session using transparent behavioral rules."""

    failed_logins = int(row.get("failed_logins", 0))
    commands = int(row.get("commands", 0))
    failed_commands = int(row.get("failed_commands", 0))
    downloads = int(row.get("downloads", 0))
    unique_commands = int(row.get("unique_command_count", 0))

    categories = row.get("command_categories", {})
    if not isinstance(categories, dict):
        categories = {}

    score = 0
    indicators = []

    # Existing behavioral rules
    if failed_logins >= 3:
        score += 20
        indicators.append("repeated_login_failures")

    if commands > 0:
        score += 10
        indicators.append("command_activity")

    if failed_commands > 0:
        score += 15
        indicators.append("failed_commands")

    if downloads > 0:
        score += 25
        indicators.append("download_activity")

    if unique_commands >= 5:
        score += 15
        indicators.append("command_diversity")

    # New privacy-preserving command behavior rules
    category_weights = {
        "read_sensitive_file": 40,
        "privilege_modification": 40,
        "reverse_shell_attempt": 60,
        "interactive_shell": 25,
        "download_attempt": 25,
        "network_request": 15,
    }

    for category, weight in category_weights.items():
        if categories.get(category, 0) > 0:

            # Avoid counting the same download activity twice.
            if category == "download_attempt" and downloads > 0:
                continue

            score += weight
            indicators.append(category)

    score = min(score, 100)

    if score >= 50:
        level = "high"
        response = "enhanced_simulated_decoy"
    elif score >= 25:
        level = "medium"
        response = "extended_simulated_logging"
    else:
        level = "low"
        response = "standard_simulated_response"

    return {
        "risk_score": score,
        "risk_level": level,
        "indicators": indicators,
        "recommended_response": response,
        "response_mode": "simulation_only",
    }
