from core.pipeline import process_event


class BaseService:
    """Common interface for honeypot service adapters."""

    def __init__(self, service_name, domain, port):
        self.service_name = service_name
        self.domain = domain
        self.port = port

    def record_event(self, event_type, source_ip, details=None):
        """Send a normalized service event to the existing pipeline."""
        event_details = {
            "service": self.service_name,
            "destination_port": self.port,
            **(details or {}),
        }

        return process_event(
            domain=self.domain,
            event_type=event_type,
            source_ip=source_ip or "unknown",
            details=event_details,
        )
