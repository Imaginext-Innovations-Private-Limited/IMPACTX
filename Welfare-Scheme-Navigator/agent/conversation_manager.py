"""
Conversation Context and Session Manager for Sahaaya AI.
Maintains bounded multi-turn conversation history and merges citizen profile attributes
across interaction turns while strictly preventing PII retention and cross-session data leaks.
"""

import re
import uuid
import time
import logging
from threading import Lock
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("conversation_manager")

# PII Regex patterns to strictly detect and reject
AADHAAR_PATTERN = re.compile(r"\b[2-9]{1}[0-9]{3}\s?[0-9]{4}\s?[0-9]{4}\b")
PAN_PATTERN = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b", re.IGNORECASE)
BANK_ACCOUNT_PATTERN = re.compile(r"\b[0-9]{9,18}\b")

# Maximum limits
MAX_MESSAGES_PER_SESSION = 20
MAX_SESSIONS_IN_MEMORY = 1000
SESSION_TTL_SECONDS = 3600 * 24  # 24 hours


class ConversationSession:
    """Represents an isolated multi-turn citizen conversation session."""

    def __init__(self, conversation_id: str):
        self.conversation_id = conversation_id
        self.messages: List[Dict[str, Any]] = []
        self.citizen_profile: Dict[str, Any] = {}
        self.last_active_scheme: Optional[str] = None
        self.created_at = time.time()
        self.updated_at = time.time()

    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """Append a message to the session history with bound enforcement."""
        self.updated_at = time.time()
        msg_entry = {
            "role": role,  # 'user', 'model', or 'system'
            "content": content,
            "timestamp": self.updated_at,
        }
        if metadata:
            msg_entry["metadata"] = metadata

        self.messages.append(msg_entry)

        # Keep history strictly bounded to prevent unbounded memory growth
        if len(self.messages) > MAX_MESSAGES_PER_SESSION:
            self.messages = self.messages[-MAX_MESSAGES_PER_SESSION:]

    def update_profile(self, new_attributes: Dict[str, Any]):
        """Merge non-sensitive profile attributes safely."""
        if not new_attributes or not isinstance(new_attributes, dict):
            return

        self.updated_at = time.time()
        for k, v in new_attributes.items():
            if v is None or (isinstance(v, str) and v.strip() == ""):
                continue

            # Strip any potential PII keys
            key_lower = str(k).lower()
            if any(term in key_lower for term in ("aadhaar", "pan", "bank", "account", "otp", "password", "secret")):
                logger.warning(f"Discarded sensitive PII key '{k}' from citizen session.")
                continue

            # Check value for PII patterns
            val_str = str(v)
            if AADHAAR_PATTERN.search(val_str) or PAN_PATTERN.search(val_str):
                logger.warning(f"Discarded attribute '{k}' containing detected PII pattern.")
                continue

            self.citizen_profile[k] = v

    def to_dict(self) -> Dict[str, Any]:
        """Serialize session state safely for diagnostics/API."""
        return {
            "conversation_id": self.conversation_id,
            "message_count": len(self.messages),
            "citizen_profile": self.citizen_profile,
            "last_active_scheme": self.last_active_scheme,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class ConversationManager:
    """Thread-safe conversation manager for active Sahaaya AI sessions."""

    _instance = None
    _lock = Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ConversationManager, cls).__new__(cls)
                cls._instance._sessions: Dict[str, ConversationSession] = {}
            return cls._instance

    @staticmethod
    def sanitize_conversation_id(raw_id: Optional[str]) -> str:
        """Validate and sanitize conversation_id to safe alphanumeric characters."""
        if not raw_id or not str(raw_id).strip():
            return f"sess_{uuid.uuid4().hex[:12]}"

        clean_id = re.sub(r"[^a-zA-Z0-9_\-]", "", str(raw_id).strip())
        if not clean_id or len(clean_id) > 64:
            return f"sess_{uuid.uuid4().hex[:12]}"
        return clean_id

    def get_or_create_session(self, conversation_id: Optional[str]) -> ConversationSession:
        """Retrieve an existing session or initialize a new one safely."""
        clean_id = self.sanitize_conversation_id(conversation_id)

        with self._lock:
            # Enforce max sessions bound by removing expired sessions if limit approached
            if len(self._sessions) >= MAX_SESSIONS_IN_MEMORY:
                self._prune_expired_sessions()

            if clean_id not in self._sessions:
                logger.info(f"Creating new conversation session: {clean_id}")
                self._sessions[clean_id] = ConversationSession(clean_id)

            return self._sessions[clean_id]

    def get_session(self, conversation_id: str) -> Optional[ConversationSession]:
        """Retrieve an existing session if present."""
        clean_id = self.sanitize_conversation_id(conversation_id)
        with self._lock:
            return self._sessions.get(clean_id)

    def reset_session(self, conversation_id: str) -> bool:
        """Clear and delete an active conversation session."""
        clean_id = self.sanitize_conversation_id(conversation_id)
        with self._lock:
            if clean_id in self._sessions:
                del self._sessions[clean_id]
                logger.info(f"Reset and cleared session: {clean_id}")
                return True
            return False

    def _prune_expired_sessions(self):
        """Remove sessions inactive for more than SESSION_TTL_SECONDS."""
        now = time.time()
        expired_ids = [
            cid for cid, s in self._sessions.items()
            if now - s.updated_at > SESSION_TTL_SECONDS
        ]
        for cid in expired_ids:
            del self._sessions[cid]

        # If still over limit, remove oldest by updated_at
        if len(self._sessions) >= MAX_SESSIONS_IN_MEMORY:
            sorted_by_activity = sorted(self._sessions.items(), key=lambda item: item[1].updated_at)
            for cid, _ in sorted_by_activity[:100]:
                del self._sessions[cid]
