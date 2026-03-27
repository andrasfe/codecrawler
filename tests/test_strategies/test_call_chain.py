"""Tests for cobol_penetrator.strategies.call_chain."""

from __future__ import annotations

from pathlib import Path

import pytest

from cobol_penetrator.agents.base import AgentContext
from cobol_penetrator.mock_reader import (
    ProgramStructure,
    parse_mock_structure,
)
from cobol_penetrator.strategies.call_chain import CallChainStrategy
from cobol_penetrator.tickets.models import ParagraphTicket


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def strategy() -> CallChainStrategy:
    """Create a CallChainStrategy instance."""
    return CallChainStrategy()


@pytest.fixture
def fixtures_dir() -> Path:
    """Path to the test fixtures directory."""
    return Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def sample_structure(fixtures_dir: Path) -> ProgramStructure:
    """Parse sample.mock.cbl to get a realistic structure."""
    return parse_mock_structure(fixtures_dir / "sample.mock.cbl")


@pytest.fixture
def paragraph_ticket() -> ParagraphTicket:
    """Create a ticket targeting 2000-VALIDATE via call chain."""
    return ParagraphTicket(
        id="PARA-2000-VALIDATE",
        paragraph="2000-VALIDATE",
        call_path=["1000-MAIN", "2000-VALIDATE"],
    )


@pytest.fixture
def call_chain_context(
    paragraph_ticket: ParagraphTicket,
    sample_structure: ProgramStructure,
) -> AgentContext:
    """Create an AgentContext for a call chain target."""
    para_code = sample_structure.get_paragraph_code("2000-VALIDATE")
    return AgentContext(
        ticket=paragraph_ticket,
        structure=sample_structure,
        paragraph_code=para_code,
        parent_params={"WS-STATUS": "00"},
        call_path=["1000-MAIN", "2000-VALIDATE"],
        extra={
            "target_paragraph": "2000-VALIDATE",
            "stubs": [],
        },
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCallChainStrategySystemPrompt:
    """Verify system prompt content."""

    def test_contains_cobol_analyst_instruction(
        self, strategy: CallChainStrategy, call_chain_context: AgentContext
    ) -> None:
        prompt = strategy.build_system_prompt(call_chain_context)
        assert "COBOL program analyst" in prompt

    def test_mentions_perform_chain(
        self, strategy: CallChainStrategy, call_chain_context: AgentContext
    ) -> None:
        prompt = strategy.build_system_prompt(call_chain_context)
        assert "PERFORM" in prompt or "call chain" in prompt

    def test_mentions_target_paragraph(
        self, strategy: CallChainStrategy, call_chain_context: AgentContext
    ) -> None:
        prompt = strategy.build_system_prompt(call_chain_context)
        assert "target paragraph" in prompt

    def test_mentions_parent_params(
        self, strategy: CallChainStrategy, call_chain_context: AgentContext
    ) -> None:
        prompt = strategy.build_system_prompt(call_chain_context)
        assert "parent" in prompt.lower()


class TestCallChainStrategyUserPrompt:
    """Verify user prompt content."""

    def test_contains_target_paragraph_name(
        self, strategy: CallChainStrategy, call_chain_context: AgentContext
    ) -> None:
        prompt = strategy.build_user_prompt(call_chain_context)
        assert "2000-VALIDATE" in prompt

    def test_contains_call_path(
        self, strategy: CallChainStrategy, call_chain_context: AgentContext
    ) -> None:
        prompt = strategy.build_user_prompt(call_chain_context)
        assert "1000-MAIN" in prompt
        assert "2000-VALIDATE" in prompt
        assert " -> " in prompt

    def test_contains_paragraph_code(
        self, strategy: CallChainStrategy, call_chain_context: AgentContext
    ) -> None:
        prompt = strategy.build_user_prompt(call_chain_context)
        assert "```cobol" in prompt
        assert "DISPLAY" in prompt

    def test_contains_parent_params(
        self, strategy: CallChainStrategy, call_chain_context: AgentContext
    ) -> None:
        prompt = strategy.build_user_prompt(call_chain_context)
        assert "WS-STATUS" in prompt

    def test_requests_json_format(
        self, strategy: CallChainStrategy, call_chain_context: AgentContext
    ) -> None:
        prompt = strategy.build_user_prompt(call_chain_context)
        assert '"input_state"' in prompt
        assert '"stubs"' in prompt
        assert "JSON" in prompt

    def test_no_parent_params_shows_none(
        self, strategy: CallChainStrategy, call_chain_context: AgentContext
    ) -> None:
        call_chain_context.parent_params = None
        prompt = strategy.build_user_prompt(call_chain_context)
        assert "None" in prompt

    def test_empty_call_path_shows_na(
        self, strategy: CallChainStrategy, call_chain_context: AgentContext
    ) -> None:
        call_chain_context.call_path = []
        prompt = strategy.build_user_prompt(call_chain_context)
        assert "N/A" in prompt

    def test_with_stubs(
        self, strategy: CallChainStrategy, call_chain_context: AgentContext
    ) -> None:
        call_chain_context.extra["stubs"] = ["READ-ACCOUNT", "WRITE-LOG"]
        prompt = strategy.build_user_prompt(call_chain_context)
        assert "READ-ACCOUNT" in prompt
        assert "WRITE-LOG" in prompt
