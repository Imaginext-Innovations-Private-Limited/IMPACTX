"""Safe adaptive deception policy for the honeypot lab."""

ALLOWED_RESPONSES = {
    "standard_simulated_response",
    "extended_simulated_logging",
    "enhanced_simulated_decoy",
}


def choose_adaptive_response(analysis):
    """Choose a predefined response using the session risk assessment."""

    risk_level = analysis.get("risk_level", "low")

    if risk_level == "high":
        response = "enhanced_simulated_decoy"
    elif risk_level == "medium":
        response = "extended_simulated_logging"
    else:
        response = "standard_simulated_response"

    return {
        "selected_response": response,
        "reason": f"Selected using the {risk_level} risk classification",
        "mode": "simulation_only",
        "allowed": response in ALLOWED_RESPONSES,
    }
