"""
Agent Orchestrator for Sahaaya AI.
Coordinates multi-turn conversations, tool invocations, Gemini API calling cycles,
deterministic eligibility preservation, citation tracking, and graceful fallback modes.
"""

import re
import json
import logging
from typing import Dict, Any, List, Optional, Union
from config import Config
from agent.gemini_client import GeminiClient, GeminiError
from agent.conversation_manager import ConversationManager, ConversationSession
from agent.prompts import SAHAAYA_SYSTEM_INSTRUCTION, FALLBACK_SYSTEM_MESSAGE
from agent.tools import execute_tool, get_gemini_tools, ALLOWED_TOOL_NAMES
from agent.response_formatter import ResponseFormatter
from models import GovernmentScheme

logger = logging.getLogger("agent_orchestrator")

try:
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    types = None
    GENAI_AVAILABLE = False


MAX_MESSAGE_LENGTH = 2500
MAX_TOOL_ITERATIONS = 5


class AgentOrchestrator:
    """
    Core agent orchestrator for Sahaaya AI.
    Executes the loop: User -> Gemini -> Tool Selection -> Python Backend -> Tool Results -> Gemini -> Final Response.
    """

    def __init__(
        self,
        gemini_client: Optional[GeminiClient] = None,
        conversation_manager: Optional[ConversationManager] = None,
        max_tool_iterations: int = MAX_TOOL_ITERATIONS,
    ):
        self.gemini_client = gemini_client or GeminiClient()
        self.conversation_manager = conversation_manager or ConversationManager()
        self.max_tool_iterations = max(1, min(10, max_tool_iterations))

    def process_message(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        citizen_profile: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Process a citizen natural-language message through the agentic loop.
        
        Args:
            message: Natural language prompt from the citizen.
            conversation_id: Optional session identifier for conversation continuity.
            citizen_profile: Optional dictionary of demographic/eligibility attributes.

        Returns:
            Structured dictionary formatted by ResponseFormatter.
        """
        # 1. Validate incoming message
        if not message or not isinstance(message, str) or not message.strip():
            clean_id = self.conversation_manager.sanitize_conversation_id(conversation_id)
            return ResponseFormatter.format_error_response(
                error_message="Message cannot be empty. Please provide your query.",
                conversation_id=clean_id,
                status_code=400,
            )

        if len(message) > MAX_MESSAGE_LENGTH:
            clean_id = self.conversation_manager.sanitize_conversation_id(conversation_id)
            return ResponseFormatter.format_error_response(
                error_message=f"Message exceeds maximum allowed length of {MAX_MESSAGE_LENGTH} characters.",
                conversation_id=clean_id,
                status_code=400,
            )

        # 2. Get or initialize conversation session and merge profile attributes
        session = self.conversation_manager.get_or_create_session(conversation_id)
        if citizen_profile and isinstance(citizen_profile, dict):
            session.update_profile(citizen_profile)

        # 3. Detect and handle potential prompt injection or credential submission
        user_text = message.strip()
        pii_warning = self._check_for_pii_in_text(user_text)

        # 4. If Gemini is unavailable, execute deterministic fallback workflow
        if not self.gemini_client.is_available():
            logger.info("Gemini client is unavailable. Routing to deterministic fallback handler.")
            return self._handle_fallback_turn(user_text, session, pii_warning)

        # 5. Execute genuine Gemini Tool-Calling Loop
        return self._execute_gemini_agent_loop(user_text, session, pii_warning)

    def _execute_gemini_agent_loop(
        self,
        user_message: str,
        session: ConversationSession,
        pii_warning: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute genuine multi-step Gemini function calling using google-genai SDK."""
        tools_invoked: List[Dict[str, Any]] = []
        all_citations: List[Dict[str, Any]] = []
        eligibility_result: Optional[Dict[str, Any]] = None
        follow_up_questions: List[str] = []

        # Prepare system instruction and tool configuration
        gemini_tools = get_gemini_tools()
        config = types.GenerateContentConfig(
            system_instruction=SAHAAYA_SYSTEM_INSTRUCTION,
            temperature=0.2,
            tools=gemini_tools,
        )

        # Build conversation contents from session history + current turn
        contents: List[Any] = []
        for past_msg in session.messages:
            role = "user" if past_msg["role"] == "user" else "model"
            contents.append(
                types.Content(role=role, parts=[types.Part.from_text(text=past_msg["content"])])
            )

        # Append current user prompt (including current known non-sensitive profile context)
        prompt_with_context = user_message
        if session.citizen_profile:
            known_profile_summary = json.dumps(session.citizen_profile)
            prompt_with_context = (
                f"{user_message}\n\n"
                f"[Known Citizen Profile Context from Conversation: {known_profile_summary}]"
            )

        contents.append(
            types.Content(role="user", parts=[types.Part.from_text(text=prompt_with_context)])
        )

        iteration = 0
        final_answer = ""

        try:
            while iteration < self.max_tool_iterations:
                iteration += 1
                logger.info(f"Gemini agent loop iteration {iteration}/{self.max_tool_iterations}")

                response = self.gemini_client.generate_content(
                    contents=contents,
                    config=config,
                )

                # Check if Gemini returned function calls
                function_calls = getattr(response, "function_calls", None)

                if not function_calls:
                    # Model produced final natural language response
                    final_answer = response.text or ""
                    break

                # Gemini requested tool execution: Append model candidate content
                if response.candidates and response.candidates[0].content:
                    contents.append(response.candidates[0].content)

                # Process all function calls returned in this turn
                tool_parts = []
                for fc in function_calls:
                    fn_name = getattr(fc, "name", "")
                    fn_args = getattr(fc, "args", {}) or {}

                    # Strict whitelist check
                    if fn_name not in ALLOWED_TOOL_NAMES:
                        logger.warning(f"Gemini requested disallowed tool '{fn_name}'. Rejecting.")
                        tool_output = {
                            "success": False,
                            "error": f"Tool '{fn_name}' is not permitted in Welfare Scheme Navigator.",
                        }
                    else:
                        # Auto-inject session citizen profile if checking eligibility and not provided
                        if fn_name == "check_eligibility":
                            if "citizen_profile" not in fn_args or not fn_args["citizen_profile"]:
                                fn_args["citizen_profile"] = session.citizen_profile
                            else:
                                # Merge with session profile
                                merged = dict(session.citizen_profile)
                                if isinstance(fn_args["citizen_profile"], dict):
                                    merged.update(fn_args["citizen_profile"])
                                fn_args["citizen_profile"] = merged

                            # Track last active scheme slug
                            if "scheme_slug" in fn_args:
                                session.last_active_scheme = fn_args["scheme_slug"]

                        elif fn_name in ("get_required_documents", "get_application_guidance"):
                            if "scheme_slug" in fn_args:
                                session.last_active_scheme = fn_args["scheme_slug"]

                        # Execute tool safely
                        tool_output = execute_tool(fn_name, fn_args)

                        # Capture structured outcomes
                        if fn_name == "check_eligibility":
                            eligibility_result = tool_output
                        elif fn_name == "retrieve_scheme_information" and tool_output.get("citations"):
                            all_citations.extend(tool_output["citations"])

                    # Record tool invocation record
                    tools_invoked.append({
                        "tool_name": fn_name,
                        "status": "success" if tool_output.get("success", False) else "error",
                        "args_summary": list(fn_args.keys()),
                    })

                    # Build function response part
                    response_part = types.Part.from_function_response(
                        name=fn_name,
                        response=tool_output,
                    )
                    tool_parts.append(response_part)

                # Append single Content with all tool parts for this turn
                if tool_parts:
                    contents.append(
                        types.Content(role="tool", parts=tool_parts)
                    )

        except GeminiError as ge:
            logger.error(f"Gemini error during agent loop: {ge.message}")
            return self._handle_fallback_turn(user_message, session, pii_warning)
        except Exception as exc:
            logger.error(f"Unexpected error in agent orchestrator: {type(exc).__name__} - {exc}")
            return self._handle_fallback_turn(user_message, session, pii_warning)

        # 6. Strict Decision Protection Guard
        # Protect all four deterministic eligibility statuses against LLM contradictions
        if eligibility_result and isinstance(eligibility_result, dict):
            final_answer = self._enforce_eligibility_decision_protection(final_answer, eligibility_result)

        # 7. Append PII warning if citizen provided sensitive credential patterns
        if pii_warning:
            final_answer = f"{final_answer}\n\n⚠️ **Privacy Notice**: {pii_warning}"

        # 8. Record turn in session history
        session.add_message(role="user", content=user_message)
        session.add_message(role="model", content=final_answer)

        # 9. Format response
        return ResponseFormatter.format_agent_response(
            assistant_message=final_answer,
            conversation_id=session.conversation_id,
            tools_invoked=tools_invoked,
            eligibility_result=eligibility_result,
            citations=all_citations,
            follow_up_questions=follow_up_questions,
            is_fallback=False,
        )

    def _handle_fallback_turn(
        self,
        user_message: str,
        session: ConversationSession,
        pii_warning: Optional[str] = None,
        error_prefix: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Deterministic, offline fallback navigation when Gemini API is unconfigured or unreachable.
        Uses exact Python database matching, EligibilityEngine, DocumentEngine, and FTS5 retrieval.
        """
        tools_invoked: List[Dict[str, Any]] = []
        all_citations: List[Dict[str, Any]] = []
        eligibility_result: Optional[Dict[str, Any]] = None
        follow_ups: List[str] = []

        query_lower = user_message.lower()
        assistant_message_parts = []

        assistant_message_parts.append(
            "> [!NOTE]\n"
            "> AI assistance is temporarily limited. You can still explore schemes and access available scheme information.\n"
        )

        # Identify scheme mention in user message or from session context
        matched_scheme = self._detect_scheme_mention(query_lower, session)

        # Scenario A: Eligibility inquiry
        if any(term in query_lower for term in ("eligible", "eligibility", "qualify", "can i get", "am i")):
            if matched_scheme:
                session.last_active_scheme = matched_scheme.slug
                elig_res = execute_tool("check_eligibility", {
                    "scheme_slug": matched_scheme.slug,
                    "citizen_profile": session.citizen_profile,
                })
                tools_invoked.append({"tool_name": "check_eligibility", "status": "success", "args_summary": ["scheme_slug", "citizen_profile"]})
                eligibility_result = elig_res

                status = elig_res.get("overall_status")
                if status == "potentially_eligible":
                    assistant_message_parts.append(
                        f"### Eligibility Assessment: {matched_scheme.name}\n"
                        f"**Status: Potentially Eligible** ✅\n\n"
                        f"Based on your profile attributes, you satisfy all verified eligibility conditions evaluated so far.\n"
                    )
                elif status == "not_eligible":
                    failed = elig_res.get("failed_rules", [])
                    reasons = "\n".join([f"- {r.get('explanation')}" for r in failed])
                    assistant_message_parts.append(
                        f"### Eligibility Assessment: {matched_scheme.name}\n"
                        f"**Status: Not Eligible** ❌\n\n"
                        f"Your profile does not satisfy one or more required government criteria:\n{reasons}\n"
                    )
                else:  # needs_more_information
                    missing = elig_res.get("missing_information", [])
                    questions = elig_res.get("next_questions", [])
                    q_list = "\n".join([f"{i+1}. {q}" for i, q in enumerate(questions)])
                    assistant_message_parts.append(
                        f"### Eligibility Assessment: {matched_scheme.name}\n"
                        f"**Status: More Information Needed** ℹ️\n\n"
                        f"To determine whether you qualify for {matched_scheme.name}, please answer:\n\n{q_list}\n"
                    )
            else:
                assistant_message_parts.append(
                    "Which government scheme would you like to check eligibility for? "
                    "For example, you can check eligibility for **Gruha Lakshmi**, **Yuva Nidhi**, **Gruha Jyothi**, or **PM-KISAN**."
                )

        # Scenario B: Document inquiry
        elif any(term in query_lower for term in ("document", "documents", "papers", "certificate", "checklist")):
            if matched_scheme:
                session.last_active_scheme = matched_scheme.slug
                doc_res = execute_tool("get_required_documents", {"scheme_slug": matched_scheme.slug})
                tools_invoked.append({"tool_name": "get_required_documents", "status": "success", "args_summary": ["scheme_slug"]})

                mandatory = doc_res.get("mandatory_documents", [])
                doc_list = "\n".join([f"- **{d['document_name']}**: {d['description']}" for d in mandatory])
                assistant_message_parts.append(
                    f"### Required Documents for {matched_scheme.name}\n\n"
                    f"**Mandatory Documents Checklist:**\n{doc_list}\n\n"
                    f"*(Note: Welfare Scheme Navigator does not ask for or collect document uploads.)*"
                )
            else:
                assistant_message_parts.append("Which scheme's document checklist would you like to review?")

        # Scenario C: Application guidance
        elif any(term in query_lower for term in ("apply", "application", "how to apply", "registration", "portal")):
            if matched_scheme:
                session.last_active_scheme = matched_scheme.slug
                app_res = execute_tool("get_application_guidance", {"scheme_slug": matched_scheme.slug})
                tools_invoked.append({"tool_name": "get_application_guidance", "status": "success", "args_summary": ["scheme_slug"]})

                steps = app_res.get("steps", [])
                step_list = "\n".join([f"**Step {s['step_number']}**: {s['instruction']}" for s in steps])
                assistant_message_parts.append(
                    f"### How to Apply for {matched_scheme.name}\n\n"
                    f"{step_list}\n\n"
                    f"🔗 **Official Application Portal**: {app_res.get('official_application_url')}\n"
                )
            else:
                assistant_message_parts.append("Which scheme would you like application guidance for?")

        # Scenario D: Multi-scheme comparison
        elif "compare" in query_lower:
            # Check for multiple scheme mentions using direct match and aliases
            all_schemes = GovernmentScheme.query.all()
            found_slugs = []
            for s in all_schemes:
                if s.slug in query_lower or s.name.lower() in query_lower:
                    if s.slug not in found_slugs:
                        found_slugs.append(s.slug)

            aliases = {
                "pm kisan": "pm-kisan",
                "pm-kisan": "pm-kisan",
                "kisan": "pm-kisan",
                "ayushman": "ayushman-bharat-pmjay",
                "pmjay": "ayushman-bharat-pmjay",
                "gruha lakshmi": "gruha-lakshmi",
                "yuva nidhi": "yuva-nidhi",
                "gruha jyothi": "gruha-jyothi",
                "shakti": "shakti-scheme",
                "anna bhagya": "anna-bhagya",
                "ssp": "ssp-post-matric-scholarship",
                "pmay": "pmay-housing",
                "sukanya": "sukanya-samriddhi-yojana",
            }
            for alias, slug in aliases.items():
                if alias in query_lower and slug not in found_slugs:
                    found_slugs.append(slug)

            if len(found_slugs) >= 2:
                comp_res = execute_tool("compare_schemes", {"scheme_slugs": found_slugs})
                tools_invoked.append({"tool_name": "compare_schemes", "status": "success", "args_summary": ["scheme_slugs"]})
                rows = []
                for s in comp_res.get("schemes", []):
                    rows.append(f"**{s['scheme_name']}** ({s['government_level']}):\n- *Benefits*: {s['benefits']}\n- *Official Portal*: {s['official_portal_url']}")
                assistant_message_parts.append(
                    f"### Scheme Comparison\n\n" + "\n\n".join(rows) + "\n"
                )
            else:
                assistant_message_parts.append("Please specify at least two scheme names to compare (e.g. 'Compare PM-KISAN and Ayushman Bharat').")

        # Scenario E: Scheme Search / General Exploration
        else:
            search_res = execute_tool("search_schemes", {"query": user_message})
            tools_invoked.append({"tool_name": "search_schemes", "status": "success", "args_summary": ["query"]})
            schemes = search_res.get("schemes", [])

            if schemes:
                scheme_cards = []
                for s in schemes[:4]:
                    scheme_cards.append(
                        f"- **{s['scheme_name']}** ({s['government_level']}, {s['state']})\n"
                        f"  *Category*: {s['category']}\n"
                        f"  *Benefits*: {s['benefits']}\n"
                        f"  *Official Portal*: {s['official_portal_url']}"
                    )
                assistant_message_parts.append(
                    f"### Matching Welfare Schemes ({len(schemes)} found):\n\n" + "\n\n".join(scheme_cards)
                )
            else:
                # Try RAG retrieval
                rag_res = execute_tool("retrieve_scheme_information", {"query": user_message})
                tools_invoked.append({"tool_name": "retrieve_scheme_information", "status": "success", "args_summary": ["query"]})
                if rag_res.get("citations"):
                    all_citations.extend(rag_res["citations"])
                    assistant_message_parts.append(
                        f"### Relevant Government Guidelines:\n\n" + rag_res["citations"][0]["formatted_citation"] + "\n\n"
                        f"\"{rag_res['citations'][0]['passage_snippet']}\""
                    )
                else:
                    assistant_message_parts.append(
                        f"No verified government welfare schemes were found matching '{user_message}'. "
                        "Try searching by categories like 'farmer', 'women', 'scholarship', 'electricity', or 'housing'."
                    )

        if pii_warning:
            assistant_message_parts.append(f"\n\n⚠️ **Privacy Notice**: {pii_warning}")

        final_msg = "\n\n".join(assistant_message_parts)

        # Update session history
        session.add_message(role="user", content=user_message)
        session.add_message(role="model", content=final_msg)

        return ResponseFormatter.format_agent_response(
            assistant_message=final_msg,
            conversation_id=session.conversation_id,
            tools_invoked=tools_invoked,
            eligibility_result=eligibility_result,
            citations=all_citations,
            follow_up_questions=follow_ups,
            is_fallback=True,
        )

    def _detect_scheme_mention(self, text: str, session: ConversationSession) -> Optional[GovernmentScheme]:
        """Detect which scheme the user is referring to from text or session context."""
        all_schemes = GovernmentScheme.query.all()

        # Check explicit mention in current text
        for s in all_schemes:
            if s.slug in text or s.name.lower() in text or s.slug.replace("-", " ") in text:
                return s

        # Check common aliases
        aliases = {
            "gruha lakshmi": "gruha-lakshmi",
            "gruhalakshmi": "gruha-lakshmi",
            "yuva nidhi": "yuva-nidhi",
            "yuvanidhi": "yuva-nidhi",
            "gruha jyothi": "gruha-jyothi",
            "gruhajyothi": "gruha-jyothi",
            "free electricity": "gruha-jyothi",
            "shakti": "shakti-scheme",
            "free bus": "shakti-scheme",
            "anna bhagya": "anna-bhagya",
            "annabhagya": "anna-bhagya",
            "free rice": "anna-bhagya",
            "ssp": "ssp-post-matric-scholarship",
            "scholarship": "ssp-post-matric-scholarship",
            "pm kisan": "pm-kisan",
            "pmkisan": "pm-kisan",
            "kisan": "pm-kisan",
            "pmay": "pmay-housing",
            "awas": "pmay-housing",
            "ayushman": "ayushman-bharat-pmjay",
            "pmjay": "ayushman-bharat-pmjay",
            "health card": "ayushman-bharat-pmjay",
            "sukanya": "sukanya-samriddhi-yojana",
        }

        for alias, slug in aliases.items():
            if alias in text:
                return GovernmentScheme.query.filter_by(slug=slug).first()

        # Fallback to session's last active scheme
        if session.last_active_scheme:
            return GovernmentScheme.query.filter_by(slug=session.last_active_scheme).first()

        return None

    def _check_for_pii_in_text(self, text: str) -> Optional[str]:
        """Detect PII patterns in message text and return warning string if found."""
        from agent.conversation_manager import AADHAAR_PATTERN, PAN_PATTERN
        found = []
        if AADHAAR_PATTERN.search(text):
            found.append("Aadhaar number")
        if PAN_PATTERN.search(text):
            found.append("PAN card number")

        if found:
            items = " and ".join(found)
            return (
                f"We noticed what appears to be a {items} in your message. "
                "For your privacy and security, Welfare Scheme Navigator never collects or requires Aadhaar or PAN numbers. "
                "This information has been discarded and is not retained in your session."
            )
        return None

    def _enforce_eligibility_decision_protection(
        self,
        gemini_response: str,
        eligibility_result: Dict[str, Any],
    ) -> str:
        """
        Safety guard: Enforce deterministic outcomes for all four eligibility statuses:
        1. not_eligible: Never allow Gemini to claim the citizen qualifies or is approved.
        2. needs_more_information: Never allow Gemini to confirm qualification when data is missing.
        3. unable_to_verify: Never allow Gemini to invent eligibility for unverified schemes.
        4. potentially_eligible: Never allow Gemini to claim guaranteed government approval.
        """
        overall_status = eligibility_result.get("overall_status")
        scheme_name = eligibility_result.get("scheme_name") or eligibility_result.get("scheme_slug", "the scheme")
        text_lower = gemini_response.lower()

        eligibility_claim_patterns = [
            "you are eligible",
            "you're eligible",
            "you qualify for",
            "you qualify to",
            "you are approved",
            "you're approved",
            "you will receive",
            "congratulations, you are eligible",
            "congratulations! you are eligible",
            "congratulations, you qualify",
            "you meet all requirements",
            "you satisfy all conditions",
            "you meet all the eligibility",
            "eligibility confirmed",
            "you are entitled to receive",
            "fully eligible",
        ]

        guaranteed_approval_patterns = [
            "guaranteed government approval",
            "government approval is guaranteed",
            "guaranteed to receive",
            "100% approved by the government",
            "guaranteed benefit",
            "official government approval has been granted",
            "disbursement is guaranteed",
            "guaranteed approval",
        ]

        # Case 1: not_eligible
        if overall_status == "not_eligible":
            if any(p in text_lower for p in eligibility_claim_patterns):
                logger.warning(
                    f"Contradiction detected: Gemini claimed eligibility for {scheme_name} "
                    f"when engine returned not_eligible. Enforcing determination."
                )
                failed = (
                    eligibility_result.get("failed_rules")
                    or eligibility_result.get("rules_failed")
                    or []
                )
                reasons = "\n".join([f"- {r.get('explanation') or r.get('description')}" for r in failed])
                if not reasons:
                    reasons = f"- One or more mandatory requirements for {scheme_name} were not satisfied."

                banner = (
                    f"⚠️ **Official Eligibility Determination: Not Eligible** ❌\n\n"
                    f"Based on the verified government guidelines for **{scheme_name}**, "
                    f"your current profile does not satisfy the following mandatory condition(s):\n{reasons}\n\n"
                    f"*(Note: Automated language models cannot grant eligibility. Only published government criteria apply.)*\n\n"
                )
                cleaned = gemini_response
                for p in eligibility_claim_patterns:
                    cleaned = re.sub(re.escape(p), "are not eligible", cleaned, flags=re.IGNORECASE)
                return banner + cleaned

        # Case 2: needs_more_information
        elif overall_status == "needs_more_information":
            if any(p in text_lower for p in eligibility_claim_patterns):
                logger.warning(
                    f"Contradiction detected: Gemini claimed eligibility for {scheme_name} "
                    f"when engine returned needs_more_information. Enforcing determination."
                )
                questions = (
                    eligibility_result.get("next_questions")
                    or eligibility_result.get("next_recommended_questions")
                    or []
                )
                formatted_questions = []
                for q in questions:
                    if isinstance(q, dict):
                        q_str = q.get("question") or q.get("prompt") or q.get("field_name", "")
                    else:
                        q_str = str(q)
                    if q_str and q_str not in ("[object Object]", "undefined", "null"):
                        formatted_questions.append(q_str)
                missing_items = "\n".join([f"{i+1}. {q}" for i, q in enumerate(formatted_questions)])
                if not missing_items:
                    missing_info = eligibility_result.get("missing_information") or []
                    missing_items = "\n".join([f"- {m.replace('_', ' ').capitalize()}" for m in missing_info])

                banner = (
                    f"ℹ️ **Official Eligibility Determination: More Information Needed** ⚠️\n\n"
                    f"Your eligibility for **{scheme_name}** cannot be confirmed yet because required details are missing from your profile:\n\n"
                    f"{missing_items}\n\n"
                    f"*(Note: Eligibility cannot be determined until this information is provided. Language models cannot assume missing criteria.)*\n\n"
                )
                cleaned = gemini_response
                for p in eligibility_claim_patterns:
                    cleaned = re.sub(re.escape(p), "need additional information to assess eligibility", cleaned, flags=re.IGNORECASE)
                return banner + cleaned

        # Case 3: unable_to_verify
        elif overall_status == "unable_to_verify":
            if any(p in text_lower for p in eligibility_claim_patterns):
                logger.warning(
                    f"Contradiction detected: Gemini claimed eligibility for {scheme_name} "
                    f"when engine returned unable_to_verify. Enforcing determination."
                )
                error_msg = eligibility_result.get("error") or "Official rules could not be verified."
                banner = (
                    f"❓ **Official Eligibility Determination: Unable to Verify** ⚠️\n\n"
                    f"Welfare Scheme Navigator cannot confirm eligibility for **{scheme_name}** because the scheme's verified rules are not established in our database ({error_msg}). "
                    f"Please consult the official government portal.\n\n"
                )
                cleaned = gemini_response
                for p in eligibility_claim_patterns:
                    cleaned = re.sub(re.escape(p), "cannot confirm eligibility", cleaned, flags=re.IGNORECASE)
                return banner + cleaned

        # Case 4: potentially_eligible
        elif overall_status == "potentially_eligible":
            if any(p in text_lower for p in guaranteed_approval_patterns):
                logger.warning(
                    f"Contradiction detected: Gemini promised guaranteed approval for {scheme_name}. "
                    f"Enforcing indicative disclaimer."
                )
                disclaimer_banner = (
                    f"⚠️ **Important Disclaimer on Eligibility Determination**:\n"
                    f"While your profile indicates that you are **potentially eligible** for **{scheme_name}**, "
                    f"this constitutes an **indicative assessment only** based on published guidelines. "
                    f"It does NOT constitute guaranteed government approval. Final approval and disbursement are strictly subject to official document verification by competent government authorities.\n\n"
                )
                cleaned = gemini_response
                for p in guaranteed_approval_patterns:
                    cleaned = re.sub(re.escape(p), "indicative potential eligibility", cleaned, flags=re.IGNORECASE)
                return disclaimer_banner + cleaned

        return gemini_response
