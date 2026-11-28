
import json
from datetime import datetime, timezone
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
AUDIT_LOG = PROJECT_DIR / "data" / "adaptation_audit.jsonl"


def log_adaptation(session_id, analysis, adaptation, ssh_ml=None):
    """Append an auditable simulated adaptation and SSH ML prediction."""

    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": str(session_id),
        "risk_score": analysis.get("risk_score"),
        "risk_level": analysis.get("risk_level"),
        "indicators": analysis.get("indicators", []),
        "selected_response": adaptation.get("selected_response"),
        "reason": adaptation.get("reason"),
        "mode": adaptation.get("mode", "simulation_only"),
        "ssh_ml": ssh_ml or {
            "mode": "shadow",
            "status": "not_provided"
        },
    }

    with AUDIT_LOG.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record) + "\n")

    return record
