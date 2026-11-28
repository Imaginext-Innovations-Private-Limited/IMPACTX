
from core.pipeline import process_event

event = process_event(
    domain="web",
    event_type="security_test",
    source_ip="127.0.0.1",
    details={
        "method": "GET",
        "path": "/../../etc/passwd",
        "query_keys": []
    }
)

print("Event ID:", event["event_id"])
print("Risk:", event["risk_assessment"]["risk_score"])
print("Level:", event["risk_assessment"]["risk_level"])
print("Indicators:", event["risk_assessment"]["indicators"])
print("Response:", event["response_policy"]["policy"])
print("Action:", event["response_policy"]["action"])

