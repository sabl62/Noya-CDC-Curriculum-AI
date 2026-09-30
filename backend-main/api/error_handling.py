"""Safe, user-facing classifications for AI provider failures."""

import json


MODEL_TRAFFIC = "model_traffic"
USER_API_QUOTA = "user_api_quota"
AI_TIMEOUT = "ai_timeout"
SERVER_FAILURE = "server_failure"

_USER_QUOTA_MARKERS = (
    "insufficient_quota",
    "quota exceeded",
    "current quota",
    "billing hard limit",
    "out of tokens",
    "token balance",
    "no credits remaining",
)
_PROVIDER_QUOTA_MARKERS = (
    "insufficient_quota",
    "quota exceeded",
    "billing hard limit",
    "out of tokens",
    "token balance",
    "no credits remaining",
    "resource_exhausted",
    "resource exhausted",
    "current quota",
    "daily quota",
    "monthly quota",
    "usage limit",
)
_TRAFFIC_MARKERS = (
    "overloaded",
    "over capacity",
    "at capacity",
    "high demand",
    "model busy",
    "server busy",
    "too many requests",
    "rate limit",
    "rate_limit",
    "rate limited",
    "requests per minute",
    "tokens per minute",
    "temporarily unavailable",
)

USER_MESSAGES = {
    MODEL_TRAFFIC: "The AI models are under heavy traffic right now. Please try again in a little while.",
    USER_API_QUOTA: "Your custom API key has run out of available usage. Add credits or use a key with available quota.",
    AI_TIMEOUT: "The AI service took too long to respond. Please try again.",
    SERVER_FAILURE: "Noya's AI service couldn't generate a response right now. Please try again later.",
}


def _provider_error_text(error=None, response=None, details=None):
    parts = [str(value) for value in (error, details) if value]
    if response is not None:
        parts.append(str(getattr(response, "status_code", "")))
        try:
            payload = response.json()
            if isinstance(payload, (dict, list)):
                parts.append(json.dumps(payload, ensure_ascii=False, default=str))
            else:
                parts.append(str(payload))
        except Exception:
            parts.append(str(getattr(response, "text", "")))
    return " ".join(parts).lower()


def classify_provider_error(error=None, response=None, details=None, user_api_key=False):
    """Classify one failure without returning raw provider text to the client."""
    text = _provider_error_text(error, response, details)
    if response is None:
        response = getattr(error, "response", None)
    status_code = getattr(response, "status_code", None)

    if user_api_key and any(marker in text for marker in _USER_QUOTA_MARKERS):
        return USER_API_QUOTA
    if any(marker in text for marker in _TRAFFIC_MARKERS):
        return MODEL_TRAFFIC
    if any(marker in text for marker in _PROVIDER_QUOTA_MARKERS):
        return SERVER_FAILURE
    if status_code == 429 or "429" in text:
        return MODEL_TRAFFIC
    if "timeout" in text or "timed out" in text or "deadline exceeded" in text:
        return AI_TIMEOUT
    return SERVER_FAILURE


def classify_provider_failures(failures):
    """Summarize fallback failures; mixed/unknown failures remain server errors."""
    categories = [
        item.get("category", SERVER_FAILURE) if isinstance(item, dict) else SERVER_FAILURE
        for item in failures
    ]
    if categories and all(category == USER_API_QUOTA for category in categories):
        return USER_API_QUOTA
    if categories and all(category == AI_TIMEOUT for category in categories):
        return AI_TIMEOUT
    if categories and all(category == MODEL_TRAFFIC for category in categories):
        return MODEL_TRAFFIC
    return SERVER_FAILURE


def user_error_message(code):
    return USER_MESSAGES.get(code, USER_MESSAGES[SERVER_FAILURE])
