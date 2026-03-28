"""Tests for agents/llm.py — LLM backend abstraction.

All tests use StubBackend only. No API keys required.
"""
import pytest
from agents.llm import StubBackend, get_backend


def test_stub_backend_returns_string():
    backend = StubBackend()
    result = backend.complete(system="You are a test agent.", user="Do something useful.")
    assert isinstance(result, str)


def test_stub_backend_is_deterministic():
    backend = StubBackend()
    system = "System prompt."
    user = "User message for determinism check."
    result1 = backend.complete(system=system, user=user)
    result2 = backend.complete(system=system, user=user)
    assert result1 == result2


def test_stub_backend_includes_prompt_fragment():
    backend = StubBackend()
    user = "Earn tokens by completing a bounty task in the world."
    result = backend.complete(system="You are an agent.", user=user)
    assert user[:60] in result


def test_stub_backend_nonempty():
    backend = StubBackend()
    result = backend.complete(system="", user="")
    assert isinstance(result, str)
    assert len(result) > 0


def test_get_backend_returns_stub_by_default():
    # config.LLM_BACKEND defaults to "stub" and no env override is set in CI
    import os
    # Ensure env var is not set so we get the config default
    env_backup = os.environ.pop("NOOSCAPE_LLM_BACKEND", None)
    try:
        backend = get_backend()
        assert isinstance(backend, StubBackend)
    finally:
        if env_backup is not None:
            os.environ["NOOSCAPE_LLM_BACKEND"] = env_backup
