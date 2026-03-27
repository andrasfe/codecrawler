"""Tests for cobol_penetrator.agents.paragraph."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from cobol_penetrator.agents.paragraph import ParagraphAgent
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
def paragraph_ticket() -> ParagraphTicket:
    """Create a ticket targeting 2000-VALIDATE."""
    return ParagraphTicket(
        id="PARA-2000-VALIDATE",
        paragraph="2000-VALIDATE",
        call_path=["1000-MAIN", "2000-VALIDATE"],
    )


@pytest.fixture
def mock_provider() -> MockLLMProvider:
    """Create a mock LLM provider with a valid JSON response."""
    return MockLLMProvider(
        response_content=json.dumps({
            "input_state": {"WS-FLAG": "Y"},
            "stubs": {},
        })
    )


@pytest.fixture
def paragraph_agent(mock_provider: MockLLMProvider) -> ParagraphAgent:
    """Create a ParagraphAgent with mock provider."""
    return ParagraphAgent(llm_provider=mock_provider)


# ---------------------------------------------------------------------------
# Tests: build_context
# ---------------------------------------------------------------------------


class TestParagraphAgentBuildContext:
    """Verify build_context produces correct AgentContext."""

    async def test_context_has_target_paragraph_code(
        self,
        paragraph_agent: ParagraphAgent,
        paragraph_ticket: ParagraphTicket,
        sample_structure: ProgramStructure,
        mock_cbl_path: Path,
    ) -> None:
        ctx = await paragraph_agent.build_context(
            paragraph_ticket, sample_structure, mock_cbl_path
        )
        assert "2000-VALIDATE" in ctx.paragraph_code

    async def test_context_has_correct_ticket(
        self,
        paragraph_agent: ParagraphAgent,
        paragraph_ticket: ParagraphTicket,
        sample_structure: ProgramStructure,
        mock_cbl_path: Path,
    ) -> None:
        ctx = await paragraph_agent.build_context(
            paragraph_ticket, sample_structure, mock_cbl_path
        )
        assert ctx.ticket is paragraph_ticket

    async def test_context_has_call_path(
        self,
        paragraph_agent: ParagraphAgent,
        paragraph_ticket: ParagraphTicket,
        sample_structure: ProgramStructure,
        mock_cbl_path: Path,
    ) -> None:
        ctx = await paragraph_agent.build_context(
            paragraph_ticket, sample_structure, mock_cbl_path
        )
        assert ctx.call_path == ["1000-MAIN", "2000-VALIDATE"]

    async def test_context_has_parent_params_when_provided(
        self,
        paragraph_agent: ParagraphAgent,
        paragraph_ticket: ParagraphTicket,
        sample_structure: ProgramStructure,
        mock_cbl_path: Path,
    ) -> None:
        parent = {"WS-STATUS": "00"}
        ctx = await paragraph_agent.build_context(
            paragraph_ticket,
            sample_structure,
            mock_cbl_path,
            parent_params=parent,
        )
        assert ctx.parent_params == {"WS-STATUS": "00"}

    async def test_context_parent_params_none_by_default(
        self,
        paragraph_agent: ParagraphAgent,
        paragraph_ticket: ParagraphTicket,
        sample_structure: ProgramStructure,
        mock_cbl_path: Path,
    ) -> None:
        ctx = await paragraph_agent.build_context(
            paragraph_ticket, sample_structure, mock_cbl_path
        )
        assert ctx.parent_params is None

    async def test_context_extra_has_target_paragraph(
        self,
        paragraph_agent: ParagraphAgent,
        paragraph_ticket: ParagraphTicket,
        sample_structure: ProgramStructure,
        mock_cbl_path: Path,
    ) -> None:
        ctx = await paragraph_agent.build_context(
            paragraph_ticket, sample_structure, mock_cbl_path
        )
        assert ctx.extra["target_paragraph"] == "2000-VALIDATE"

    async def test_context_extra_has_stubs(
        self,
        paragraph_agent: ParagraphAgent,
        paragraph_ticket: ParagraphTicket,
        sample_structure: ProgramStructure,
        mock_cbl_path: Path,
    ) -> None:
        ctx = await paragraph_agent.build_context(
            paragraph_ticket, sample_structure, mock_cbl_path
        )
        assert "stubs" in ctx.extra
        assert isinstance(ctx.extra["stubs"], list)


# ---------------------------------------------------------------------------
# Tests: generate_params
# ---------------------------------------------------------------------------


class TestParagraphAgentGenerateParams:
    """Verify generate_params calls LLM and parses response."""

    async def test_returns_input_state_and_stubs(
        self,
        paragraph_agent: ParagraphAgent,
        paragraph_ticket: ParagraphTicket,
        sample_structure: ProgramStructure,
        mock_cbl_path: Path,
    ) -> None:
        ctx = await paragraph_agent.build_context(
            paragraph_ticket, sample_structure, mock_cbl_path
        )
        params = await paragraph_agent.generate_params(ctx)
        assert "input_state" in params
        assert "stubs" in params

    async def test_returns_expected_values(
        self,
        paragraph_agent: ParagraphAgent,
        paragraph_ticket: ParagraphTicket,
        sample_structure: ProgramStructure,
        mock_cbl_path: Path,
    ) -> None:
        ctx = await paragraph_agent.build_context(
            paragraph_ticket, sample_structure, mock_cbl_path
        )
        params = await paragraph_agent.generate_params(ctx)
        assert params["input_state"]["WS-FLAG"] == "Y"

    async def test_sends_correct_messages_to_llm(
        self,
        mock_provider: MockLLMProvider,
        paragraph_agent: ParagraphAgent,
        paragraph_ticket: ParagraphTicket,
        sample_structure: ProgramStructure,
        mock_cbl_path: Path,
    ) -> None:
        ctx = await paragraph_agent.build_context(
            paragraph_ticket,
            sample_structure,
            mock_cbl_path,
            parent_params={"WS-STATUS": "00"},
        )
        await paragraph_agent.generate_params(ctx)

        assert mock_provider.last_messages is not None
        assert len(mock_provider.last_messages) == 2

        system_msg = mock_provider.last_messages[0]
        user_msg = mock_provider.last_messages[1]

        assert system_msg.role == "system"
        assert "COBOL" in system_msg.content

        assert user_msg.role == "user"
        assert "2000-VALIDATE" in user_msg.content
        assert "1000-MAIN" in user_msg.content
        assert "WS-STATUS" in user_msg.content

    async def test_handles_empty_llm_response(
        self,
        paragraph_ticket: ParagraphTicket,
        sample_structure: ProgramStructure,
        mock_cbl_path: Path,
    ) -> None:
        provider = MockLLMProvider(response_content="")
        agent = ParagraphAgent(llm_provider=provider)
        ctx = await agent.build_context(
            paragraph_ticket, sample_structure, mock_cbl_path
        )
        params = await agent.generate_params(ctx)
        assert params == {"input_state": {}, "stubs": {}}

    async def test_handles_malformed_llm_response(
        self,
        paragraph_ticket: ParagraphTicket,
        sample_structure: ProgramStructure,
        mock_cbl_path: Path,
    ) -> None:
        provider = MockLLMProvider(
            response_content="Sorry, I cannot parse this COBOL."
        )
        agent = ParagraphAgent(llm_provider=provider)
        ctx = await agent.build_context(
            paragraph_ticket, sample_structure, mock_cbl_path
        )
        params = await agent.generate_params(ctx)
        assert params == {"input_state": {}, "stubs": {}}

    async def test_handles_partial_json_response(
        self,
        paragraph_ticket: ParagraphTicket,
        sample_structure: ProgramStructure,
        mock_cbl_path: Path,
    ) -> None:
        provider = MockLLMProvider(
            response_content='{"input_state": {"WS-FLAG": "N"}}'
        )
        agent = ParagraphAgent(llm_provider=provider)
        ctx = await agent.build_context(
            paragraph_ticket, sample_structure, mock_cbl_path
        )
        params = await agent.generate_params(ctx)
        assert "input_state" in params
        assert "stubs" in params
        assert params["stubs"] == {}


# ---------------------------------------------------------------------------
# Tests: __init__
# ---------------------------------------------------------------------------


class TestParagraphAgentInit:
    """Verify ParagraphAgent initialization."""

    def test_has_strategy(self, paragraph_agent: ParagraphAgent) -> None:
        from cobol_penetrator.strategies.call_chain import CallChainStrategy

        assert isinstance(paragraph_agent.strategy, CallChainStrategy)

    def test_name_is_paragraph_agent(
        self, paragraph_agent: ParagraphAgent
    ) -> None:
        assert paragraph_agent.name == "ParagraphAgent"

    def test_custom_model_and_temperature(
        self, mock_provider: MockLLMProvider
    ) -> None:
        agent = ParagraphAgent(
            llm_provider=mock_provider,
            model="gpt-4",
            temperature=0.1,
        )
        assert agent.model == "gpt-4"
        assert agent.temperature == 0.1
