"""
Response Formatter for Sahaaya AI Agent.
Standardizes and validates agent responses, preserves deterministic eligibility outcomes,
aggregates citations, attaches source verification badges, and appends mandatory disclaimers.
"""

from typing import Dict, Any, List, Optional
from config import Config

INDICATIVE_DISCLAIMER = Config.INDICATIVE_ONLY_DISCLAIMER


class ResponseFormatter:
    """Formats, validates, and structures the final response for citizen API consumers."""

    @classmethod
    def format_agent_response(
        cls,
        assistant_message: str,
        conversation_id: str,
        tools_invoked: Optional[List[Dict[str, Any]]] = None,
        eligibility_result: Optional[Dict[str, Any]] = None,
        citations: Optional[List[Dict[str, Any]]] = None,
        follow_up_questions: Optional[List[str]] = None,
        is_fallback: bool = False,
    ) -> Dict[str, Any]:
        """
        Build a comprehensive, structured response dictionary.
        Enforces strict preservation of eligibility outcomes and source verification labels.
        """
        tools_invoked = tools_invoked or []
        citations = citations or []
        follow_ups = list(follow_up_questions or [])

        # Extract next questions from eligibility result if not already populated
        eligibility_status = None
        if eligibility_result and isinstance(eligibility_result, dict):
            raw_status = eligibility_result.get("overall_status")
            if raw_status in {"potentially_eligible", "not_eligible", "needs_more_information", "unable_to_verify"}:
                eligibility_status = raw_status
            else:
                eligibility_status = "unable_to_verify"

            engine_next_questions = (
                eligibility_result.get("next_questions", [])
                or eligibility_result.get("next_recommended_questions", [])
            )
            for q in engine_next_questions:
                if isinstance(q, dict):
                    q_str = q.get("question") or q.get("prompt") or q.get("field_name", "")
                else:
                    q_str = str(q)
                if q_str and q_str not in follow_ups and q_str not in ("[object Object]", "undefined", "null"):
                    follow_ups.append(q_str)

        # Collect unique verification labels and badges across citations
        verification_labels = []
        for cit in citations:
            badge = cit.get("verification_badge")
            if badge and badge not in verification_labels:
                verification_labels.append(badge)

        # Build clean formatted response payload
        tools_names = [
            t.get("tool_name") if isinstance(t, dict) else str(t)
            for t in tools_invoked
        ]
        response = {
            "success": True,
            "conversation_id": conversation_id,
            "assistant_message": assistant_message.strip(),
            "response": assistant_message.strip(),
            "tools_invoked": tools_invoked,
            "tools_executed": tools_names,
            "total_tools_called": len(tools_invoked),
            "eligibility_result": eligibility_result,
            "eligibility_status": eligibility_status,
            "citations": citations,
            "total_citations": len(citations),
            "verification_labels": verification_labels,
            "has_demonstration_material": any(
                "[DEMO ONLY" in label for label in verification_labels
            ),
            "follow_up_questions": follow_ups,
            "disclaimer": INDICATIVE_DISCLAIMER,
            "is_fallback_mode": is_fallback,
        }

        return response

    @classmethod
    def format_error_response(
        cls,
        error_message: str,
        conversation_id: str,
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Format a clean, structured error response without exposing internal stack traces."""
        return {
            "success": False,
            "conversation_id": conversation_id,
            "error": error_message,
            "status_code": status_code,
            "details": details or {},
            "disclaimer": INDICATIVE_DISCLAIMER,
        }
