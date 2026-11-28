
from core.session_analyzer import analyze_session
from core.adaptive_policy import choose_adaptive_response
from core.adaptation_logger import log_adaptation


def evaluate_session(session_features, session_id="unknown", ssh_ml=None):
    """Analyze a session, select a simulated response, and audit the decision."""

    analysis = analyze_session(session_features)
    adaptation = choose_adaptive_response(analysis)

    audit_record = log_adaptation(
        session_id=session_id,
        analysis=analysis,
        adaptation=adaptation,
        ssh_ml=ssh_ml,
    )

    return {
        "analysis": analysis,
        "adaptation": adaptation,
        "audit_record": audit_record,
    }
