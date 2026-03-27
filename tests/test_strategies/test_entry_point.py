"""Tests for cobol_penetrator.strategies.entry_point."""

from __future__ import annotations

from pathlib import Path

import pytest

from cobol_penetrator.agents.base import AgentContext
from cobol_penetrator.mock_reader import (
    ParagraphInfo,
    ProgramStructure,
    parse_mock_structure,
)
from cobol_penetrator.strategies.entry_point import EntryPointStrategy
from cobol_penetrator.tickets.models import ParagraphTicket


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def strategy() -> EntryPointStrategy:
    """Create an EntryPointStrategy instance."""
    return EntryPointStrategy()


@pytest.fixture
def fixtures_dir() -> Path:
    """Path to the test fixtures directory."""
    return Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def sample_structure(fixtures_dir: Path) -> ProgramStructure:
    """Parse sample.mock.cbl to get a realistic structure."""
    return parse_mock_structure(fixtures_dir / "sample.mock.cbl")


@pytest.fixture
def entry_ticket(sample_structure: ProgramStructure) -> ParagraphTicket:
    """Create a ticket for the entry paragraph."""
    entry = sample_structure.entry_paragraph
    return ParagraphTicket(id=f"PARA-{entry}", paragraph=entry)


@pytest.fixture
def entry_context(
    entry_ticket: ParagraphTicket,
    sample_structure: ProgramStructure,
) -> AgentContext:
    """Create an AgentContext for the entry paragraph."""
    entry_code = sample_structure.get_paragraph_code(
        sample_structure.entry_paragraph
    )
    return AgentContext(
        ticket=entry_ticket,
        structure=sample_structure,
        paragraph_code=entry_code,
        extra={"stubs": ["WRITE-ERROR-LOG"]},
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestEntryPointStrategySystemPrompt:
    """Verify system prompt content."""

    def test_contains_cobol_analyst_instruction(
        self, strategy: EntryPointStrategy, entry_context: AgentContext
    ) -> None:
        prompt = strategy.build_system_prompt(entry_context)
        assert "COBOL program analyst" in prompt

    def test_contains_entry_paragraph_focus(
        self, strategy: EntryPointStrategy, entry_context: AgentContext
    ) -> None:
        prompt = strategy.build_system_prompt(entry_context)
        assert "entry paragraph" in prompt

    def test_mentions_input_variables(
        self, strategy: EntryPointStrategy, entry_context: AgentContext
    ) -> None:
        prompt = strategy.build_system_prompt(entry_context)
        assert "input variables" in prompt

    def test_mentions_stub_outcomes(
        self, strategy: EntryPointStrategy, entry_context: AgentContext
    ) -> None:
        prompt = strategy.build_system_prompt(entry_context)
        assert "stub outcomes" in prompt


class TestEntryPointStrategyUserPrompt:
    """Verify user prompt content."""

    def test_contains_paragraph_code(
        self, strategy: EntryPointStrategy, entry_context: AgentContext
    ) -> None:
        prompt = strategy.build_user_prompt(entry_context)
        assert "1000-MAIN" in prompt

    def test_contains_cobol_code_block(
        self, strategy: EntryPointStrategy, entry_context: AgentContext
    ) -> None:
        prompt = strategy.build_user_prompt(entry_context)
        assert "```cobol" in prompt

    def test_contains_stubs_info(
        self, strategy: EntryPointStrategy, entry_context: AgentContext
    ) -> None:
        prompt = strategy.build_user_prompt(entry_context)
        assert "WRITE-ERROR-LOG" in prompt

    def test_requests_json_format(
        self, strategy: EntryPointStrategy, entry_context: AgentContext
    ) -> None:
        prompt = strategy.build_user_prompt(entry_context)
        assert '"input_state"' in prompt
        assert '"stubs"' in prompt
        assert "JSON" in prompt

    def test_no_stubs_shows_none_found(
        self, strategy: EntryPointStrategy, entry_context: AgentContext
    ) -> None:
        entry_context.extra["stubs"] = []
        prompt = strategy.build_user_prompt(entry_context)
        assert "None found" in prompt

    def test_contains_entry_paragraph_keyword(
        self, strategy: EntryPointStrategy, entry_context: AgentContext
    ) -> None:
        prompt = strategy.build_user_prompt(entry_context)
        assert "entry paragraph" in prompt

    def test_with_minimal_context(
        self, strategy: EntryPointStrategy, entry_context: AgentContext
    ) -> None:
        """Strategy should handle a context with minimal data."""
        minimal_ctx = AgentContext(
            ticket=entry_context.ticket,
            structure=entry_context.structure,
            paragraph_code="",
            extra={},
        )
        prompt = strategy.build_user_prompt(minimal_ctx)
        assert "None found" in prompt
        assert "```cobol" in prompt
