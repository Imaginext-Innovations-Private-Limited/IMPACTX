
def choose_response(assessment):
    """Choose a safe, simulated response based on risk."""

    score = assessment.get("risk_score", 0)

    if score >= 60:
        return {
            "policy": "high_risk_simulation",
            "message": "Simulated resource unavailable",
            "action": "record_and_monitor"
        }

    if score >= 30:
        return {
            "policy": "medium_risk_simulation",
            "message": "Simulated access restricted",
            "action": "record_event"
        }

    return {
        "policy": "normal_simulation",
        "message": "Simulated resource available",
        "action": "record_event"
    }
