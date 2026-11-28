"""
Sahaaya AI Agent Package.
Provides Gemini Agent Orchestration, Tool Calling, Conversation Management,
and Grounded Response Formatting for welfare scheme navigation.
"""

from agent.gemini_client import (
    GeminiClient,
    GeminiError,
    GeminiUnavailableError,
    GeminiAuthError,
    GeminiRateLimitError,
    GeminiModelError,
    GeminiNetworkError,
)
from agent.conversation_manager import (
    ConversationManager,
    ConversationSession,
)
from agent.tools import (
    execute_tool,
    get_gemini_tools,
    ALLOWED_TOOL_NAMES,
)
from agent.prompts import (
    SAHAAYA_SYSTEM_INSTRUCTION,
    FALLBACK_SYSTEM_MESSAGE,
)
from agent.response_formatter import ResponseFormatter
from agent.agent_orchestrator import AgentOrchestrator

__all__ = [
    "GeminiClient",
    "GeminiError",
    "GeminiUnavailableError",
    "GeminiAuthError",
    "GeminiRateLimitError",
    "GeminiModelError",
    "GeminiNetworkError",
    "ConversationManager",
    "ConversationSession",
    "execute_tool",
    "get_gemini_tools",
    "ALLOWED_TOOL_NAMES",
    "SAHAAYA_SYSTEM_INSTRUCTION",
    "FALLBACK_SYSTEM_MESSAGE",
    "ResponseFormatter",
    "AgentOrchestrator",
]
