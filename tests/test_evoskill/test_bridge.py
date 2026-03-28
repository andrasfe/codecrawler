"""Tests for cobol_penetrator.evoskill_bridge."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

from cobol_penetrator.evoskill_bridge import (
    agent_to_evoskill_role,
    make_async_evoskill_llm,
    make_sync_evoskill_llm,
)
from cobol_penetrator.llm_providers.protocol import CompletionResponse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_provider() -> MagicMock:
    """Create a mock LLMProvider returning a fixed completion."""
    provider = MagicMock()
    provider.complete = AsyncMock(
        return_value=CompletionResponse(
            content="skill text",
            model="test-model",
            tokens_used=10,
        )
    )
    return provider


# ---------------------------------------------------------------------------
# Tests: make_async_evoskill_llm
# ---------------------------------------------------------------------------


class TestMakeAsyncEvoSkillLLM:
    """Verify the async LLM adapter."""

    def test_returns_callable(self) -> None:
        provider = _make_mock_provider()
        llm = make_async_evoskill_llm(provider)
        assert callable(llm)

    def test_calls_provider_complete(self) -> None:
        provider = _make_mock_provider()
        llm = make_async_evoskill_llm(provider)
        messages = [{"role": "user", "content": "hello"}]
        result = asyncio.run(llm(messages))

        assert result == "skill text"
        provider.complete.assert_awaited_once()

    def test_passes_messages_as_typed(self) -> None:
        provider = _make_mock_provider()
        llm = make_async_evoskill_llm(provider)
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "test"},
        ]
        asyncio.run(llm(messages))

        call_args = provider.complete.call_args
        typed_msgs = call_args[0][0]
        assert len(typed_msgs) == 2
        assert typed_msgs[0].role == "system"
        assert typed_msgs[1].content == "test"

    def test_uses_temperature_03(self) -> None:
        provider = _make_mock_provider()
        llm = make_async_evoskill_llm(provider)
        asyncio.run(llm([{"role": "user", "content": "hi"}]))

        call_kwargs = provider.complete.call_args
        assert call_kwargs[1]["temperature"] == 0.3


# ---------------------------------------------------------------------------
# Tests: make_sync_evoskill_llm
# ---------------------------------------------------------------------------


class TestMakeSyncEvoSkillLLM:
    """Verify the sync LLM adapter."""

    def test_returns_callable(self) -> None:
        provider = _make_mock_provider()
        llm = make_sync_evoskill_llm(provider)
        assert callable(llm)

    def test_calls_provider_complete_sync(self) -> None:
        provider = _make_mock_provider()
        llm = make_sync_evoskill_llm(provider)
        result = llm([{"role": "user", "content": "hello"}])

        assert result == "skill text"
        provider.complete.assert_awaited_once()


# ---------------------------------------------------------------------------
# Tests: agent_to_evoskill_role
# ---------------------------------------------------------------------------


class TestAgentToEvoSkillRole:
    """Verify agent-to-role mapping."""

    def test_recon_agent(self) -> None:
        from cobol_penetrator.agents.recon import ReconAgent

        provider = _make_mock_provider()
        agent = ReconAgent(provider)
        assert agent_to_evoskill_role(agent) == "recon"

    def test_paragraph_agent(self) -> None:
        from cobol_penetrator.agents.paragraph import ParagraphAgent

        provider = _make_mock_provider()
        agent = ParagraphAgent(provider)
        assert agent_to_evoskill_role(agent) == "paragraph"

    def test_branch_agent(self) -> None:
        from cobol_penetrator.agents.branch import BranchAgent

        provider = _make_mock_provider()
        agent = BranchAgent(provider)
        assert agent_to_evoskill_role(agent) == "branch"

    def test_unknown_agent(self) -> None:
        assert agent_to_evoskill_role(object()) == "unknown"
