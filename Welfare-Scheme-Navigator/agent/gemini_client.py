"""
Gemini Client Wrapper for Sahaaya AI.
Interfaces with Google Gemini API via official google-genai SDK.
Configures v1beta API version and request timeouts via types.HttpOptions.
Provides safe initialization, structured transport error diagnostics,
bounded retries, and graceful fallback modes.
Never exposes API credentials in logs or responses.
"""

import os
import time
import logging
from typing import Any, Dict, List, Optional, Union
from config import Config

logger = logging.getLogger("gemini_client")

try:
    from google import genai
    from google.genai import types
    from google.genai import errors as genai_errors
    GENAI_SDK_AVAILABLE = True
except ImportError:
    genai = None
    types = None
    genai_errors = None
    GENAI_SDK_AVAILABLE = False


# Custom Exception Hierarchy for Gemini Operations
class GeminiError(Exception):
    """Base exception for Gemini client operations."""
    def __init__(self, message: str, status_code: int = 500, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class GeminiUnavailableError(GeminiError):
    """Raised when Gemini API is not configured or unavailable."""
    def __init__(self, message: str = "Gemini API is not configured or unavailable."):
        super().__init__(message, status_code=503)


class GeminiAuthError(GeminiError):
    """Raised when API key is invalid or unauthorized."""
    def __init__(self, message: str = "Invalid or unauthorized Gemini API key."):
        super().__init__(message, status_code=401)


class GeminiRateLimitError(GeminiError):
    """Raised when quota or rate limits are exceeded."""
    def __init__(self, message: str = "Gemini API rate limit or quota exceeded."):
        super().__init__(message, status_code=429)


class GeminiModelError(GeminiError):
    """Raised when the specified model is invalid or unavailable."""
    def __init__(self, message: str = "Configured Gemini model is unavailable."):
        super().__init__(message, status_code=404)


class GeminiNetworkError(GeminiError):
    """Raised when network, connection, or timeout issues occur."""
    def __init__(self, message: str = "Network connection failure to Gemini API.", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=504, details=details)


class GeminiClient:
    """
    Thread-safe client wrapper for Google Gemini API via google-genai SDK.
    Explicitly configures v1beta API version and milliseconds timeout using types.HttpOptions.
    Inspects exception chains for underlying transport issues without exposing secrets.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        max_retries: int = 2,
        request_timeout: float = 30.0,
        api_version: str = "v1beta",
    ):
        self.api_key = api_key if api_key is not None else Config.GEMINI_API_KEY
        self.model_name = model_name if model_name is not None else Config.GEMINI_MODEL
        self.max_retries = max(0, min(5, max_retries))
        self.request_timeout = max(5.0, request_timeout)
        self.api_version = api_version
        self.http_options = None
        self._client = None
        self._init_error = None

        self._initialize_client()

    def _initialize_client(self):
        """Safely initialize the underlying genai.Client instance with HttpOptions."""
        if not GENAI_SDK_AVAILABLE:
            self._init_error = "google-genai SDK is not installed in the active environment."
            logger.warning(self._init_error)
            return

        # Explicitly configure HttpOptions with api_version and timeout in milliseconds
        timeout_ms = int(self.request_timeout * 1000)
        if types is not None and hasattr(types, "HttpOptions"):
            self.http_options = types.HttpOptions(
                api_version=self.api_version,
                timeout=timeout_ms,
            )

        clean_key = (self.api_key or "").strip()
        if not clean_key or clean_key.lower() in ("your_gemini_api_key_here", "none", "placeholder"):
            self._init_error = "GEMINI_API_KEY is not configured or contains placeholder value."
            logger.info("Gemini client running in fallback mode: No valid API key configured.")
            return

        try:
            client_kwargs = {"api_key": clean_key}
            if self.http_options is not None:
                client_kwargs["http_options"] = self.http_options

            self._client = genai.Client(**client_kwargs)
            self._init_error = None
            # Log initialization safely without exposing key
            logger.info(
                f"Gemini client successfully initialized with model: '{self.model_name}', "
                f"api_version: '{self.api_version}', timeout: {timeout_ms}ms"
            )
        except Exception as e:
            self._init_error = f"Failed to initialize Gemini Client: {type(e).__name__}"
            logger.error(self._init_error)
            self._client = None

    def is_available(self) -> bool:
        """Check if Gemini client is properly configured and ready for generation."""
        return self._client is not None and self._init_error is None

    def get_status(self) -> Dict[str, Any]:
        """Return diagnostic status of the Gemini client (safe for public health endpoints)."""
        clean_key = (self.api_key or "").strip()
        has_key = bool(clean_key and clean_key.lower() not in ("your_gemini_api_key_here", "none", "placeholder"))
        timeout_ms = int(self.request_timeout * 1000)
        return {
            "available": self.is_available(),
            "sdk_installed": GENAI_SDK_AVAILABLE,
            "api_key_configured": has_key,
            "configured_model": self.model_name,
            "api_version": self.api_version,
            "timeout_ms": timeout_ms,
            "initialization_status": "ready" if self.is_available() else "fallback_mode",
            "message": "Gemini client ready" if self.is_available() else (self._init_error or "Client unavailable"),
        }

    def generate_content(
        self,
        contents: Union[str, List[Any]],
        config: Optional[Any] = None,
        model_override: Optional[str] = None,
    ) -> Any:
        """
        Execute generate_content against the configured Gemini model with bounded retries.
        
        Args:
            contents: User string prompt or list of types.Content / types.Part objects.
            config: Optional types.GenerateContentConfig instance containing tools, temperature, etc.
            model_override: Optional string to override the default model name for this call.

        Returns:
            types.GenerateContentResponse object from google-genai.

        Raises:
            GeminiUnavailableError: If client is not configured.
            GeminiAuthError: If API credentials fail authentication.
            GeminiRateLimitError: If quota or rate limits are encountered.
            GeminiModelError: If model is not found or unsupported.
            GeminiNetworkError: If connection fails after retries.
        """
        if not self.is_available():
            raise GeminiUnavailableError(
                self._init_error or "Gemini client is unavailable. Check GEMINI_API_KEY."
            )

        target_model = model_override or self.model_name
        attempts = 0
        last_error = None

        while attempts <= self.max_retries:
            attempts += 1
            try:
                response = self._client.models.generate_content(
                    model=target_model,
                    contents=contents,
                    config=config,
                )
                return response
            except Exception as exc:
                last_error = exc
                mapped_error = self._map_exception(exc)

                # Do not retry auth errors, bad client requests, or unavailable models
                if isinstance(mapped_error, (GeminiAuthError, GeminiModelError)):
                    logger.error(f"Unrecoverable Gemini error: {type(mapped_error).__name__} - {mapped_error.message}")
                    raise mapped_error

                # For rate limits and network errors, bounded backoff retry if attempts remain
                if attempts <= self.max_retries:
                    backoff = 0.5 * (2 ** (attempts - 1))
                    logger.warning(
                        f"Transient Gemini error (attempt {attempts}/{self.max_retries + 1}): "
                        f"{type(exc).__name__} -> {mapped_error.message}. Retrying in {backoff:.1f}s..."
                    )
                    time.sleep(backoff)
                else:
                    logger.error(f"Gemini call exhausted retries. Final error: {mapped_error.message}")
                    raise mapped_error

        raise self._map_exception(last_error or Exception("Unknown generation failure"))

    @staticmethod
    def _extract_diagnostic_chain(exc: Exception) -> Dict[str, Any]:
        """
        Inspect the exception chain to extract actionable transport diagnostics
        (exception types, root cause, transport error type) without logging credentials or payload.
        """
        chain = []
        curr = exc
        seen = set()

        while curr and id(curr) not in seen:
            seen.add(id(curr))
            curr_str = str(curr)
            # Scrub any potential embedded URL query keys
            safe_msg = curr_str.split("?key=")[0].split("&key=")[0]
            chain.append({
                "type": type(curr).__name__,
                "module": getattr(type(curr), "__module__", ""),
                "message": safe_msg,
            })
            curr = getattr(curr, "__cause__", None) or getattr(curr, "__context__", None)

        root = chain[-1] if chain else {"type": type(exc).__name__, "message": str(exc)}
        return {
            "top_exception": type(exc).__name__,
            "root_cause_type": root["type"],
            "root_cause_message": root["message"],
            "chain_types": [item["type"] for item in chain],
        }

    def _map_exception(self, exc: Exception) -> GeminiError:
        """
        Map raw SDK, HTTPX, or transport exceptions into typed GeminiError instances.
        Inspects the underlying cause chain for ConnectError, socket, or SSL issues without hiding errors.
        """
        diag = self._extract_diagnostic_chain(exc)
        chain_summary = " -> ".join(diag["chain_types"])
        err_str = (str(exc) + " " + diag["root_cause_message"]).lower()

        logger.error(
            f"Gemini transport diagnostics: Top='{diag['top_exception']}', "
            f"RootCause='{diag['root_cause_type']}' (Message: '{diag['root_cause_message']}'), "
            f"ExceptionChain=[{chain_summary}]"
        )

        # 1. Check for authentication / authorization errors
        if any(term in err_str for term in ("api_key_invalid", "unauthenticated", "permission_denied", "api key not valid")):
            return GeminiAuthError(
                f"Gemini authentication failed: Invalid or unauthorized API key ({diag['root_cause_type']}: {diag['root_cause_message']})"
            )

        # 2. Check for rate limits / quota exhaustion
        if any(term in err_str for term in ("resource_exhausted", "429", "quota", "rate limit")):
            return GeminiRateLimitError(
                f"Gemini quota or rate limit exceeded ({diag['root_cause_type']}: {diag['root_cause_message']})"
            )

        # 3. Check for invalid or unavailable model
        if any(term in err_str for term in ("not_found", "model")) and any(term in err_str for term in ("unknown", "unsupported", "404", "does not exist")):
            return GeminiModelError(
                f"Gemini model '{self.model_name}' was not found or is unsupported ({diag['root_cause_type']}: {diag['root_cause_message']})"
            )

        # 4. Check for network, connection, socket, or timeout errors (including ConnectError)
        is_connect_or_network = (
            "connecterror" in [t.lower() for t in diag["chain_types"]]
            or any(t in diag["root_cause_type"].lower() for t in ("connect", "socket", "timeout", "network", "gai", "ssl", "connection"))
            or any(term in err_str for term in ("connecterror", "connection", "network", "getaddrinfo", "econnreset", "unavailable", "503", "timed out", "timeout"))
        )

        if is_connect_or_network:
            detailed_msg = (
                f"Network connection error communicating with Gemini API "
                f"[{diag['top_exception']} -> {diag['root_cause_type']}: {diag['root_cause_message']}]"
            )
            return GeminiNetworkError(detailed_msg, details=diag)

        # 5. Default general generation error with preserved diagnostic chain
        return GeminiError(
            f"Gemini generation error: [{chain_summary}] {diag['root_cause_message']}",
            details=diag,
        )
