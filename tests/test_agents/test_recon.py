"""Tests for cobol_penetrator.agents.recon."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from cobol_penetrator.agents.recon import ReconAgent
from cobol_penetrator.llm_providers.protocol import (
    CompletionResponse,
    Message,
)
from cobol_penetrator.mock_reader import (
    ProgramStructure,
    parse_mock_structure,
)
from cobol_penetrator.tickets.models import ParagraphTicket


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
def entry_ticket(sample_structure: ProgramStructure) -> ParagraphTicket:
    """Create a ticket for the entry paragraph."""
    entry = sample_structure.entry_paragraph
    return ParagraphTicket(id=f"PARA-{entry}", paragraph=entry)


@pytest.fixture
def mock_provider() -> MockLLMProvider:
    """Create a mock LLM provider with a valid JSON response."""
    return MockLLMProvider(
        response_content=json.dumps({
            "input_state": {"WS-STATUS": "00", "WS-FLAG": "Y"},
            "stubs": {"WRITE-ERROR-LOG": "00"},
        })
    )


@pytest.fixture
def recon_agent(mock_provider: MockLLMProvider) -> ReconAgent:
    """Create a ReconAgent with mock provider."""
    return ReconAgent(llm_provider=mock_provider)


# ---------------------------------------------------------------------------
# Tests: build_context
# ---------------------------------------------------------------------------


class TestReconAgentBuildContext:
    """Verify build_context produces correct AgentContext."""

    async def test_context_has_entry_paragraph_code(
        self,
        recon_agent: ReconAgent,
        entry_ticket: ParagraphTicket,
        sample_structure: ProgramStructure,
        mock_cbl_path: Path,
    ) -> None:
        ctx = await recon_agent.build_context(
            entry_ticket, sample_structure, mock_cbl_path
        )
        assert "1000-MAIN" in ctx.paragraph_code

    async def test_context_has_correct_ticket(
        self,
        recon_agent: ReconAgent,
        entry_ticket: ParagraphTicket,
        sample_structure: ProgramStructure,
        mock_cbl_path: Path,
    ) -> None:
        ctx = await recon_agent.build_context(
            entry_ticket, sample_structure, mock_cbl_path
        )
        assert ctx.ticket is entry_ticket

    async def test_context_has_structure(
        self,
        recon_agent: ReconAgent,
        entry_ticket: ParagraphTicket,
        sample_structure: ProgramStructure,
        mock_cbl_path: Path,
    ) -> None:
        ctx = await recon_agent.build_context(
            entry_ticket, sample_structure, mock_cbl_path
        )
        assert ctx.structure is sample_structure

    async def test_context_extra_contains_stubs(
        self,
        recon_agent: ReconAgent,
        entry_ticket: ParagraphTicket,
        sample_structure: ProgramStructure,
        mock_cbl_path: Path,
    ) -> None:
        ctx = await recon_agent.build_context(
            entry_ticket, sample_structure, mock_cbl_path
        )
        # The sample.mock.cbl has stubs for paragraphs PERFORMed
        # but not defined (e.g., 9000-ERROR PERFORMs nothing external,
        # but 1000-MAIN PERFORMs 3000-PROCESS which exists).
        assert "stubs" in ctx.extra
        assert isinstance(ctx.extra["stubs"], list)


# ---------------------------------------------------------------------------
# Tests: generate_params
# ---------------------------------------------------------------------------


class TestReconAgentGenerateParams:
    """Verify generate_params calls LLM and parses response."""

    async def test_returns_input_state_and_stubs(
        self,
        recon_agent: ReconAgent,
        entry_ticket: ParagraphTicket,
        sample_structure: ProgramStructure,
        mock_cbl_path: Path,
    ) -> None:
        ctx = await recon_agent.build_context(
            entry_ticket, sample_structure, mock_cbl_path
        )
        params = await recon_agent.generate_params(ctx)
        assert "input_state" in params
        assert "stubs" in params

    async def test_returns_expected_values(
        self,
        recon_agent: ReconAgent,
        entry_ticket: ParagraphTicket,
        sample_structure: ProgramStructure,
        mock_cbl_path: Path,
    ) -> None:
        ctx = await recon_agent.build_context(
            entry_ticket, sample_structure, mock_cbl_path
        )
        params = await recon_agent.generate_params(ctx)
        assert params["input_state"]["WS-STATUS"] == "00"
        assert params["input_state"]["WS-FLAG"] == "Y"
        assert params["stubs"]["WRITE-ERROR-LOG"] == "00"

    async def test_sends_correct_messages_to_llm(
        self,
        mock_provider: MockLLMProvider,
        recon_agent: ReconAgent,
        entry_ticket: ParagraphTicket,
        sample_structure: ProgramStructure,
        mock_cbl_path: Path,
    ) -> None:
        ctx = await recon_agent.build_context(
            entry_ticket, sample_structure, mock_cbl_path
        )
        await recon_agent.generate_params(ctx)

        assert mock_provider.last_messages is not None
        assert len(mock_provider.last_messages) == 2

        system_msg = mock_provider.last_messages[0]
        user_msg = mock_provider.last_messages[1]

        assert system_msg.role == "system"
        assert "COBOL program analyst" in system_msg.content

        assert user_msg.role == "user"
        assert "entry paragraph" in user_msg.content
        assert "1000-MAIN" in user_msg.content

    async def test_handles_empty_llm_response(
        self,
        entry_ticket: ParagraphTicket,
        sample_structure: ProgramStructure,
        mock_cbl_path: Path,
    ) -> None:
        provider = MockLLMProvider(response_content="")
        agent = ReconAgent(llm_provider=provider)
        ctx = await agent.build_context(
            entry_ticket, sample_structure, mock_cbl_path
        )
        params = await agent.generate_params(ctx)
        assert params == {"input_state": {}, "stubs": {}}

    async def test_handles_malformed_llm_response(
        self,
        entry_ticket: ParagraphTicket,
        sample_structure: ProgramStructure,
        mock_cbl_path: Path,
    ) -> None:
        provider = MockLLMProvider(response_content="not valid json at all!")
        agent = ReconAgent(llm_provider=provider)
        ctx = await agent.build_context(
            entry_ticket, sample_structure, mock_cbl_path
        )
        params = await agent.generate_params(ctx)
        assert params == {"input_state": {}, "stubs": {}}

    async def test_handles_partial_json_response(
        self,
        entry_ticket: ParagraphTicket,
        sample_structure: ProgramStructure,
        mock_cbl_path: Path,
    ) -> None:
        """If LLM returns JSON missing one key, the agent fills defaults."""
        provider = MockLLMProvider(
            response_content='{"input_state": {"WS-FLAG": "Y"}}'
        )
        agent = ReconAgent(llm_provider=provider)
        ctx = await agent.build_context(
            entry_ticket, sample_structure, mock_cbl_path
        )
        params = await agent.generate_params(ctx)
        assert "input_state" in params
        assert "stubs" in params
        assert params["stubs"] == {}


# ---------------------------------------------------------------------------
# Tests: __init__
# ---------------------------------------------------------------------------


class TestReconAgentInit:
    """Verify ReconAgent initialization."""

    def test_has_strategy(self, recon_agent: ReconAgent) -> None:
        from cobol_penetrator.strategies.entry_point import (
            EntryPointStrategy,
        )

        assert isinstance(recon_agent.strategy, EntryPointStrategy)

    def test_name_is_recon_agent(self, recon_agent: ReconAgent) -> None:
        assert recon_agent.name == "ReconAgent"

    def test_custom_model_and_temperature(
        self, mock_provider: MockLLMProvider
    ) -> None:
        agent = ReconAgent(
            llm_provider=mock_provider,
            model="custom-model",
            temperature=0.2,
        )
        assert agent.model == "custom-model"
        assert agent.temperature == 0.2
