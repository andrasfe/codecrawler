"""Tests for cobol_penetrator.strategies.branch_flip."""

from __future__ import annotations

from pathlib import Path

import pytest

from cobol_penetrator.agents.base import AgentContext
from cobol_penetrator.mock_reader import (
    ProgramStructure,
    parse_mock_structure,
)
from cobol_penetrator.strategies.branch_flip import BranchFlipStrategy
from cobol_penetrator.tickets.models import BranchTicket


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def strategy() -> BranchFlipStrategy:
    """Create a BranchFlipStrategy instance."""
    return BranchFlipStrategy()


@pytest.fixture
def fixtures_dir() -> Path:
    """Path to the test fixtures directory."""
    return Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def sample_structure(fixtures_dir: Path) -> ProgramStructure:
    """Parse sample.mock.cbl to get a realistic structure."""
    return parse_mock_structure(fixtures_dir / "sample.mock.cbl")


@pytest.fixture
def branch_ticket() -> BranchTicket:
    """Create a ticket for branch 1, targeting the T direction."""
    return BranchTicket(
        id="BRANCH-1-T",
        branch_id="1",
        direction="T",
        paragraph="1000-MAIN",
        condition_text="WS-STATUS = '00'",
        condition_vars=["WS-STATUS"],
    )


@pytest.fixture
def branch_context(
    branch_ticket: BranchTicket,
    sample_structure: ProgramStructure,
) -> AgentContext:
    """Create an AgentContext for a branch flip target."""
    para_code = sample_structure.get_paragraph_code("1000-MAIN")
    return AgentContext(
        ticket=branch_ticket,
        structure=sample_structure,
        paragraph_code=para_code,
        variable_snapshots={
            "1": {"WS-STATUS": "99", "WS-FLAG": "N"},
        },
        extra={
            "branch_id": "1",
            "target_direction": "T",
            "condition_text": "WS-STATUS = '00'",
            "condition_vars": ["WS-STATUS"],
            "containing_paragraph": "1000-MAIN",
        },
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBranchFlipStrategySystemPrompt:
    """Verify system prompt content."""

    def test_contains_cobol_analyst_instruction(
        self, strategy: BranchFlipStrategy, branch_context: AgentContext
    ) -> None:
        prompt = strategy.build_system_prompt(branch_context)
        assert "COBOL program analyst" in prompt

    def test_mentions_branch_direction(
        self, strategy: BranchFlipStrategy, branch_context: AgentContext
    ) -> None:
        prompt = strategy.build_system_prompt(branch_context)
        assert "direction" in prompt

    def test_mentions_direction_codes(
        self, strategy: BranchFlipStrategy, branch_context: AgentContext
    ) -> None:
        prompt = strategy.build_system_prompt(branch_context)
        assert "T for true" in prompt
        assert "F for false" in prompt

    def test_mentions_variable_snapshots(
        self, strategy: BranchFlipStrategy, branch_context: AgentContext
    ) -> None:
        prompt = strategy.build_system_prompt(branch_context)
        assert "variable snapshots" in prompt or "snapshot" in prompt


class TestBranchFlipStrategyUserPrompt:
    """Verify user prompt content."""

    def test_contains_branch_id(
        self, strategy: BranchFlipStrategy, branch_context: AgentContext
    ) -> None:
        prompt = strategy.build_user_prompt(branch_context)
        assert "branch 1" in prompt

    def test_contains_target_direction(
        self, strategy: BranchFlipStrategy, branch_context: AgentContext
    ) -> None:
        prompt = strategy.build_user_prompt(branch_context)
        assert "direction T" in prompt

    def test_contains_condition_text(
        self, strategy: BranchFlipStrategy, branch_context: AgentContext
    ) -> None:
        prompt = strategy.build_user_prompt(branch_context)
        assert "WS-STATUS = '00'" in prompt

    def test_contains_condition_vars(
        self, strategy: BranchFlipStrategy, branch_context: AgentContext
    ) -> None:
        prompt = strategy.build_user_prompt(branch_context)
        assert "WS-STATUS" in prompt

    def test_contains_variable_snapshots(
        self, strategy: BranchFlipStrategy, branch_context: AgentContext
    ) -> None:
        prompt = strategy.build_user_prompt(branch_context)
        assert "WS-STATUS = 99" in prompt
        assert "WS-FLAG = N" in prompt

    def test_contains_paragraph_code(
        self, strategy: BranchFlipStrategy, branch_context: AgentContext
    ) -> None:
        prompt = strategy.build_user_prompt(branch_context)
        assert "```cobol" in prompt
        assert "1000-MAIN" in prompt

    def test_contains_containing_paragraph(
        self, strategy: BranchFlipStrategy, branch_context: AgentContext
    ) -> None:
        prompt = strategy.build_user_prompt(branch_context)
        assert "1000-MAIN" in prompt

    def test_requests_json_format(
        self, strategy: BranchFlipStrategy, branch_context: AgentContext
    ) -> None:
        prompt = strategy.build_user_prompt(branch_context)
        assert '"input_state"' in prompt
        assert '"stubs"' in prompt
        assert "JSON" in prompt

    def test_no_snapshots_shows_no_snapshots_message(
        self, strategy: BranchFlipStrategy, branch_context: AgentContext
    ) -> None:
        branch_context.variable_snapshots = {}
        prompt = strategy.build_user_prompt(branch_context)
        assert "No snapshots available" in prompt

    def test_no_condition_vars_shows_none_identified(
        self, strategy: BranchFlipStrategy, branch_context: AgentContext
    ) -> None:
        branch_context.extra["condition_vars"] = []
        prompt = strategy.build_user_prompt(branch_context)
        assert "None identified" in prompt

    def test_f_direction(
        self, strategy: BranchFlipStrategy, branch_context: AgentContext
    ) -> None:
        branch_context.extra["target_direction"] = "F"
        prompt = strategy.build_user_prompt(branch_context)
        assert "direction F" in prompt
