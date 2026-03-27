"""Tests for cobol_penetrator.agents.branch."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from cobol_penetrator.agents.branch import BranchAgent
from cobol_penetrator.llm_providers.protocol import (
    CompletionResponse,
    Message,
)
from cobol_penetrator.mock_reader import (
    ProgramStructure,
    parse_mock_structure,
)
from cobol_penetrator.tickets.models import BranchTicket


# ---------------------------------------------------------------------------
# Mock LLM Provider
# ---------------------------------------------------------------------------


class MockLLMProvider:
    """Mock provider that returns predetermined responses."""

    def __init__(
        self,
        response_content: str = '{"input_state": {}, "stubs": {}}',
    ):
        self.response_content = response_content
        self.last_messages: list[Message] | None = None

    @property
    def default_model(self) -> str:
        return "mock-model"

    async def complete(
        self,
        messages: list[Message],
        model: str | None = None,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> CompletionResponse:
        self.last_messages = messages
        return CompletionResponse(
            content=self.response_content,
            model="mock",
            tokens_used=0,
        )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fixtures_dir() -> Path:
    """Path to the test fixtures directory."""
    return Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def sample_structure(fixtures_dir: Path) -> ProgramStructure:
    """Parse sample.mock.cbl to get a realistic structure."""
    return parse_mock_structure(fixtures_dir / "sample.mock.cbl")


@pytest.fixture
def mock_cbl_path(fixtures_dir: Path) -> Path:
    """Path to the sample mock CBL file."""
    return fixtures_dir / "sample.mock.cbl"


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
def branch_ticket_f() -> BranchTicket:
    """Create a ticket for branch 2, targeting the F direction."""
    return BranchTicket(
        id="BRANCH-2-F",
        branch_id="2",
        direction="F",
        paragraph="2000-VALIDATE",
        condition_text="WS-FLAG = 'Y'",
        condition_vars=["WS-FLAG"],
    )


@pytest.fixture
def mock_provider() -> MockLLMProvider:
    """Create a mock LLM provider with a valid JSON response."""
    return MockLLMProvider(
        response_content=json.dumps({
            "input_state": {"WS-STATUS": "00"},
            "stubs": {},
        })
    )


@pytest.fixture
def branch_agent(mock_provider: MockLLMProvider) -> BranchAgent:
    """Create a BranchAgent with mock provider."""
    return BranchAgent(llm_provider=mock_provider)


# ---------------------------------------------------------------------------
# Tests: build_context
# ---------------------------------------------------------------------------


class TestBranchAgentBuildContext:
    """Verify build_context produces correct AgentContext."""

    async def test_context_has_containing_paragraph_code(
        self,
        branch_agent: BranchAgent,
        branch_ticket: BranchTicket,
        sample_structure: ProgramStructure,
        mock_cbl_path: Path,
    ) -> None:
        ctx = await branch_agent.build_context(
            branch_ticket, sample_structure, mock_cbl_path
        )
        assert "1000-MAIN" in ctx.paragraph_code

    async def test_context_has_correct_ticket(
        self,
        branch_agent: BranchAgent,
        branch_ticket: BranchTicket,
        sample_structure: ProgramStructure,
        mock_cbl_path: Path,
    ) -> None:
        ctx = await branch_agent.build_context(
            branch_ticket, sample_structure, mock_cbl_path
        )
        assert ctx.ticket is branch_ticket

    async def test_context_extra_has_branch_id(
        self,
        branch_agent: BranchAgent,
        branch_ticket: BranchTicket,
        sample_structure: ProgramStructure,
        mock_cbl_path: Path,
    ) -> None:
        ctx = await branch_agent.build_context(
            branch_ticket, sample_structure, mock_cbl_path
        )
        assert ctx.extra["branch_id"] == "1"

    async def test_context_extra_has_target_direction(
        self,
        branch_agent: BranchAgent,
        branch_ticket: BranchTicket,
        sample_structure: ProgramStructure,
        mock_cbl_path: Path,
    ) -> None:
        ctx = await branch_agent.build_context(
            branch_ticket, sample_structure, mock_cbl_path
        )
        assert ctx.extra["target_direction"] == "T"

    async def test_context_extra_has_condition_text(
        self,
        branch_agent: BranchAgent,
        branch_ticket: BranchTicket,
        sample_structure: ProgramStructure,
        mock_cbl_path: Path,
    ) -> None:
        ctx = await branch_agent.build_context(
            branch_ticket, sample_structure, mock_cbl_path
        )
        assert ctx.extra["condition_text"] != ""

    async def test_context_extra_has_condition_vars(
        self,
        branch_agent: BranchAgent,
        branch_ticket: BranchTicket,
        sample_structure: ProgramStructure,
        mock_cbl_path: Path,
    ) -> None:
        ctx = await branch_agent.build_context(
            branch_ticket, sample_structure, mock_cbl_path
        )
        assert isinstance(ctx.extra["condition_vars"], list)
        assert len(ctx.extra["condition_vars"]) > 0

    async def test_context_extra_has_containing_paragraph(
        self,
        branch_agent: BranchAgent,
        branch_ticket: BranchTicket,
        sample_structure: ProgramStructure,
        mock_cbl_path: Path,
    ) -> None:
        ctx = await branch_agent.build_context(
            branch_ticket, sample_structure, mock_cbl_path
        )
        assert ctx.extra["containing_paragraph"] == "1000-MAIN"

    async def test_context_includes_variable_snapshots(
        self,
        branch_agent: BranchAgent,
        branch_ticket: BranchTicket,
        sample_structure: ProgramStructure,
        mock_cbl_path: Path,
    ) -> None:
        snapshots = {"1": {"WS-STATUS": "99"}}
        ctx = await branch_agent.build_context(
            branch_ticket,
            sample_structure,
            mock_cbl_path,
            variable_snapshots=snapshots,
        )
        assert ctx.variable_snapshots["1"]["WS-STATUS"] == "99"

    async def test_context_incorporates_ticket_snapshot(
        self,
        branch_agent: BranchAgent,
        sample_structure: ProgramStructure,
        mock_cbl_path: Path,
    ) -> None:
        ticket = BranchTicket(
            id="BRANCH-1-T",
            branch_id="1",
            direction="T",
            paragraph="1000-MAIN",
            variable_snapshot={"WS-STATUS": "00"},
        )
        ctx = await branch_agent.build_context(
            ticket, sample_structure, mock_cbl_path
        )
        assert "1" in ctx.variable_snapshots
        assert ctx.variable_snapshots["1"]["WS-STATUS"] == "00"

    async def test_different_branch_ticket(
        self,
        branch_agent: BranchAgent,
        branch_ticket_f: BranchTicket,
        sample_structure: ProgramStructure,
        mock_cbl_path: Path,
    ) -> None:
        ctx = await branch_agent.build_context(
            branch_ticket_f, sample_structure, mock_cbl_path
        )
        assert ctx.extra["branch_id"] == "2"
        assert ctx.extra["target_direction"] == "F"
        assert "2000-VALIDATE" in ctx.paragraph_code


# ---------------------------------------------------------------------------
# Tests: generate_params
# ---------------------------------------------------------------------------


class TestBranchAgentGenerateParams:
    """Verify generate_params calls LLM and parses response."""

    async def test_returns_input_state_and_stubs(
        self,
        branch_agent: BranchAgent,
        branch_ticket: BranchTicket,
        sample_structure: ProgramStructure,
        mock_cbl_path: Path,
    ) -> None:
        ctx = await branch_agent.build_context(
            branch_ticket, sample_structure, mock_cbl_path
        )
        params = await branch_agent.generate_params(ctx)
        assert "input_state" in params
        assert "stubs" in params

    async def test_returns_expected_values(
        self,
        branch_agent: BranchAgent,
        branch_ticket: BranchTicket,
        sample_structure: ProgramStructure,
        mock_cbl_path: Path,
    ) -> None:
        ctx = await branch_agent.build_context(
            branch_ticket, sample_structure, mock_cbl_path
        )
        params = await branch_agent.generate_params(ctx)
        assert params["input_state"]["WS-STATUS"] == "00"

    async def test_sends_correct_messages_to_llm(
        self,
        mock_provider: MockLLMProvider,
        branch_agent: BranchAgent,
        branch_ticket: BranchTicket,
        sample_structure: ProgramStructure,
        mock_cbl_path: Path,
    ) -> None:
        snapshots = {"1": {"WS-STATUS": "99"}}
        ctx = await branch_agent.build_context(
            branch_ticket,
            sample_structure,
            mock_cbl_path,
            variable_snapshots=snapshots,
        )
        await branch_agent.generate_params(ctx)

        assert mock_provider.last_messages is not None
        assert len(mock_provider.last_messages) == 2

        system_msg = mock_provider.last_messages[0]
        user_msg = mock_provider.last_messages[1]

        assert system_msg.role == "system"
        assert "COBOL" in system_msg.content
        assert "direction" in system_msg.content

        assert user_msg.role == "user"
        assert "branch 1" in user_msg.content
        assert "direction T" in user_msg.content
        assert "WS-STATUS" in user_msg.content

    async def test_handles_empty_llm_response(
        self,
        branch_ticket: BranchTicket,
        sample_structure: ProgramStructure,
        mock_cbl_path: Path,
    ) -> None:
        provider = MockLLMProvider(response_content="")
        agent = BranchAgent(llm_provider=provider)
        ctx = await agent.build_context(
            branch_ticket, sample_structure, mock_cbl_path
        )
        params = await agent.generate_params(ctx)
        assert params == {"input_state": {}, "stubs": {}}

    async def test_handles_malformed_llm_response(
        self,
        branch_ticket: BranchTicket,
        sample_structure: ProgramStructure,
        mock_cbl_path: Path,
    ) -> None:
        provider = MockLLMProvider(
            response_content="I don't understand the condition."
        )
        agent = BranchAgent(llm_provider=provider)
        ctx = await agent.build_context(
            branch_ticket, sample_structure, mock_cbl_path
        )
        params = await agent.generate_params(ctx)
        assert params == {"input_state": {}, "stubs": {}}

    async def test_handles_partial_json_response(
        self,
        branch_ticket: BranchTicket,
        sample_structure: ProgramStructure,
        mock_cbl_path: Path,
    ) -> None:
        provider = MockLLMProvider(
            response_content='{"stubs": {"READ": "00"}}'
        )
        agent = BranchAgent(llm_provider=provider)
        ctx = await agent.build_context(
            branch_ticket, sample_structure, mock_cbl_path
        )
        params = await agent.generate_params(ctx)
        assert "input_state" in params
        assert "stubs" in params
        assert params["input_state"] == {}
        assert params["stubs"]["READ"] == "00"


# ---------------------------------------------------------------------------
# Tests: __init__
# ---------------------------------------------------------------------------


class TestBranchAgentInit:
    """Verify BranchAgent initialization."""

    def test_has_strategy(self, branch_agent: BranchAgent) -> None:
        from cobol_penetrator.strategies.branch_flip import (
            BranchFlipStrategy,
        )

        assert isinstance(branch_agent.strategy, BranchFlipStrategy)

    def test_name_is_branch_agent(self, branch_agent: BranchAgent) -> None:
        assert branch_agent.name == "BranchAgent"

    def test_custom_model_and_temperature(
        self, mock_provider: MockLLMProvider
    ) -> None:
        agent = BranchAgent(
            llm_provider=mock_provider,
            model="claude-3",
            temperature=0.5,
        )
        assert agent.model == "claude-3"
        assert agent.temperature == 0.5
