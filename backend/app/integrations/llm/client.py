"""Optional LLM client (Anthropic Messages API).

The application never requires an LLM. This client is used only when
``LLM_PROVIDER=anthropic``, ``ANTHROPIC_API_KEY`` and ``LLM_MODEL`` are set
*and* the user has explicitly consented to sending profile data to the
provider. No model name is assumed — the operator chooses one.
"""

from __future__ import annotations

import httpx

from app.core.config import Settings

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"

# Tests replace this with an httpx.MockTransport.
transport: httpx.BaseTransport | None = None


class LLMUnavailable(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def complete(settings: Settings, system: str, prompt: str, max_tokens: int = 1200) -> str:
    if not settings.llm_configured:
        raise LLMUnavailable("No LLM provider is configured on this server.")
    try:
        with httpx.Client(timeout=settings.llm_timeout_seconds, transport=transport) as client:
            response = client.post(
                ANTHROPIC_URL,
                headers={
                    "x-api-key": settings.anthropic_api_key,
                    "anthropic-version": ANTHROPIC_VERSION,
                    "content-type": "application/json",
                },
                json={
                    "model": settings.llm_model,
                    "max_tokens": max_tokens,
                    "system": system,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
    except httpx.HTTPError:
        raise LLMUnavailable("The LLM provider could not be reached.") from None
    if response.status_code == 429:
        raise LLMUnavailable("The LLM provider is rate-limiting requests. Please try again later.")
    if response.status_code >= 400:
        raise LLMUnavailable(f"The LLM provider returned HTTP {response.status_code}.")
    try:
        data = response.json()
        text = "".join(block.get("text", "") for block in data.get("content", []) if block.get("type") == "text")
    except (ValueError, AttributeError):
        raise LLMUnavailable("The LLM provider returned an unexpected response.") from None
    if not text.strip():
        raise LLMUnavailable("The LLM provider returned an empty response.")
    return text.strip()
