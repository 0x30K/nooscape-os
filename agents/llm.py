"""LLM backend abstraction for Nooscape agents.

The rest of the codebase calls get_backend() and uses LLMBackend.complete().
No LLM library is imported anywhere else.

Backends:
    StubBackend  — deterministic, no API keys, always safe for tests and CI
    OpenAIBackend — requires OPENAI_API_KEY, uses openai library (optional dep)
    AnthropicBackend — requires ANTHROPIC_API_KEY, uses anthropic library (optional dep)

Config:
    LLM_BACKEND in config.py controls which backend get_backend() returns.
    Can be overridden via NOOSCAPE_LLM_BACKEND environment variable.
"""
import config


class LLMBackend:
    def complete(self, system: str, user: str) -> str:
        """Generate a completion given a system prompt and user message.

        Args:
            system: System-level instructions for the model
            user: The user message / task description

        Returns:
            str: The model's response text
        """
        raise NotImplementedError

    @property
    def name(self) -> str:
        """Human-readable backend name for logging."""
        raise NotImplementedError


class StubBackend(LLMBackend):
    """Deterministic stub backend for testing and CI.

    Returns a predictable response that includes a fragment of the user prompt.
    No network calls. No API keys required.
    """

    @property
    def name(self) -> str:
        return "stub"

    def complete(self, system: str, user: str) -> str:
        # Return a predictable string that:
        # 1. Is non-empty
        # 2. Contains the first 60 chars of user prompt (for traceability)
        # 3. Is deterministic (same input → same output)
        return f"[STUB] Task completed: {user[:60]}"


class OpenAIBackend(LLMBackend):
    """OpenAI backend. Requires openai package and OPENAI_API_KEY."""

    def __init__(self, api_key: str, model: str):
        # Import openai here (not at module level) so import never fails when package absent
        try:
            import openai
            self._client = openai.OpenAI(api_key=api_key)
            self._model = model
        except ImportError:
            raise ImportError(
                "openai package required for OpenAIBackend. "
                "Install it: pip install openai"
            )

    @property
    def name(self) -> str:
        return f"openai/{self._model}"

    def complete(self, system: str, user: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content


class AnthropicBackend(LLMBackend):
    """Anthropic backend. Requires anthropic package and ANTHROPIC_API_KEY."""

    def __init__(self, api_key: str, model: str):
        try:
            import anthropic
            self._client = anthropic.Anthropic(api_key=api_key)
            self._model = model
        except ImportError:
            raise ImportError(
                "anthropic package required for AnthropicBackend. "
                "Install it: pip install anthropic"
            )

    @property
    def name(self) -> str:
        return f"anthropic/{self._model}"

    def complete(self, system: str, user: str) -> str:
        message = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return message.content[0].text


def get_backend() -> LLMBackend:
    """Return the configured LLM backend.

    Priority:
    1. NOOSCAPE_LLM_BACKEND environment variable (if set)
    2. config.LLM_BACKEND constant

    Returns StubBackend unless explicitly configured otherwise.
    """
    import os
    backend_name = os.environ.get("NOOSCAPE_LLM_BACKEND", config.LLM_BACKEND).lower()

    if backend_name == "openai":
        api_key = os.environ.get("OPENAI_API_KEY", "")
        return OpenAIBackend(api_key=api_key, model=config.LLM_MODEL)
    elif backend_name == "anthropic":
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        return AnthropicBackend(api_key=api_key, model=config.LLM_MODEL)
    else:
        return StubBackend()
