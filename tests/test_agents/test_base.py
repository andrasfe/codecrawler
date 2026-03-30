"""Tests for cobol_penetrator.agents.base."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest

from cobol_penetrator.agents.base import AgentContext, BaseAgent
from cobol_penetrator.llm_providers.protocol import (
    CompletionResponse,
    LLMProvider,
    Message,
)
from cobol_penetrator.mock_reader import BranchInfo, ParagraphInfo, ProgramStructure
from cobol_penetrator.tickets.models import BranchTicket, ParagraphTicket


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_structure() -> ProgramStructure:
    """Minimal ProgramStructure for testing."""
    return ProgramStructure(
        entry_paragraph="1000-MAIN",
        paragraphs={
            "1000-MAIN": ParagraphInfo(
                name="1000-MAIN",
                line_start=10,
                line_end=20,
                source_code="       1000-MAIN.\n           DISPLAY 'HELLO'.",
            ),
        },
        branches={},
        call_graph={"1000-MAIN": []},
    )


@pytest.fixture
def sample_paragraph_ticket() -> ParagraphTicket:
    """Minimal ParagraphTicket for testing."""
    return ParagraphTicket(id="PARA-1000-MAIN", paragraph="1000-MAIN")


@pytest.fixture
def sample_branch_ticket() -> BranchTicket:
    """Minimal BranchTicket for testing."""
    return BranchTicket(
        id="BRANCH-1-T",
        branch_id="1",
        direction="T",
        paragraph="1000-MAIN",
    )


class FakeLLMProvider:
    """Fake LLM provider that satisfies the LLMProvider protocol."""

    def __init__(self, response_text: str = '{"input_state": {}, "stubs": {}}'):
        self._response_text = response_text

    @property
    def default_model(self) -> str:
        return "fake-model"

    async def complete(
        self,
        messages: list[Message],
        model: str | None = None,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> CompletionResponse:
        return CompletionResponse(
            content=self._response_text,
            model=model or self.default_model,
            tokens_used=10,
        )


class ConcreteAgent(BaseAgent):
    """Concrete subclass for testing the ABC's non-abstract methods."""

    async def build_context(
        self,
        ticket: ParagraphTicket | BranchTicket,
        structure: ProgramStructure,
        mock_cbl_path: Path,
    ) -> AgentContext:
        return AgentContext(ticket=ticket, structure=structure)

    async def generate_params(self, context: AgentContext) -> dict:
        messages = self._build_messages(
            system_prompt="You are a test agent.",
            user_prompt="Generate params.",
        )
        raw = await self._complete(messages)
        return self._parse_json_response(raw)


# ===========================================================================
# AgentContext tests
# ===========================================================================


class TestAgentContext:
    """Verify AgentContext creation and defaults."""

    def test_creation_with_defaults(
        self, sample_paragraph_ticket: ParagraphTicket, sample_structure: ProgramStructure
    ) -> None:
        ctx = AgentContext(
            ticket=sample_paragraph_ticket, structure=sample_structure
        )
        assert ctx.ticket is sample_paragraph_ticket
        assert ctx.structure is sample_structure
        assert ctx.paragraph_code == ""
        assert ctx.parent_params is None
        assert ctx.variable_snapshots == {}
        assert ctx.call_path == []
        assert ctx.extra == {}

    def test_creation_with_all_fields(
        self, sample_paragraph_ticket: ParagraphTicket, sample_structure: ProgramStructure
    ) -> None:
        ctx = AgentContext(
            ticket=sample_paragraph_ticket,
            structure=sample_structure,
            paragraph_code="       DISPLAY 'HELLO'.",
            parent_params={"WS-STATUS": "00"},
            variable_snapshots={"1": {"WS-FLAG": "Y"}},
            call_path=["1000-MAIN", "2000-VALIDATE"],
            extra={"strategy": "entry_point"},
        )
        assert ctx.paragraph_code == "       DISPLAY 'HELLO'."
        assert ctx.parent_params == {"WS-STATUS": "00"}
        assert ctx.variable_snapshots == {"1": {"WS-FLAG": "Y"}}
        assert ctx.call_path == ["1000-MAIN", "2000-VALIDATE"]
        assert ctx.extra == {"strategy": "entry_point"}

    def test_default_dicts_are_independent(
        self, sample_paragraph_ticket: ParagraphTicket, sample_structure: ProgramStructure
    ) -> None:
        """Each AgentContext instance should get its own mutable defaults."""
        ctx1 = AgentContext(ticket=sample_paragraph_ticket, structure=sample_structure)
        ctx2 = AgentContext(ticket=sample_paragraph_ticket, structure=sample_structure)
        ctx1.call_path.append("X")
        ctx1.extra["key"] = "val"
        assert ctx2.call_path == []
        assert ctx2.extra == {}

    def test_works_with_branch_ticket(
        self, sample_branch_ticket: BranchTicket, sample_structure: ProgramStructure
    ) -> None:
        ctx = AgentContext(ticket=sample_branch_ticket, structure=sample_structure)
        assert ctx.ticket is sample_branch_ticket


# ===========================================================================
# BaseAgent ABC tests
# ===========================================================================


class TestBaseAgentABC:
    """Verify that BaseAgent cannot be instantiated directly."""

    def test_cannot_instantiate_directly(self) -> None:
        provider = FakeLLMProvider()
        with pytest.raises(TypeError, match="abstract method"):
            BaseAgent(llm_provider=provider)  # type: ignore[abstract]

    def test_concrete_subclass_instantiates(self) -> None:
        provider = FakeLLMProvider()
        agent = ConcreteAgent(llm_provider=provider)
        assert agent.name == "ConcreteAgent"
        assert agent.llm is provider
        assert agent.model is None
        assert agent.temperature == 0.7

    def test_custom_model_and_temperature(self) -> None:
        provider = FakeLLMProvider()
        agent = ConcreteAgent(
            llm_provider=provider, model="custom-model", temperature=0.2
        )
        assert agent.model == "custom-model"
        assert agent.temperature == 0.2


# ===========================================================================
# _build_messages tests
# ===========================================================================


class TestBuildMessages:
    """Verify _build_messages produces correct Message list."""

    def test_produces_system_and_user_messages(self) -> None:
        agent = ConcreteAgent(llm_provider=FakeLLMProvider())
        messages = agent._build_messages(
            system_prompt="System instruction",
            user_prompt="User request",
        )
        assert len(messages) == 2
        assert isinstance(messages[0], Message)
        assert isinstance(messages[1], Message)
        assert messages[0].role == "system"
        assert messages[0].content == "System instruction"
        assert messages[1].role == "user"
        assert messages[1].content == "User request"


# ===========================================================================
# _parse_json_response tests
# ===========================================================================


class TestParseJsonResponse:
    """Verify _parse_json_response handles various LLM output formats."""

    def test_raw_json(self) -> None:
        text = '{"input_state": {"WS-STATUS": "00"}, "stubs": {}}'
        result = BaseAgent._parse_json_response(text)
        assert result == {"input_state": {"WS-STATUS": "00"}, "stubs": {}}

    def test_raw_json_with_whitespace(self) -> None:
        text = '  \n {"key": "value"} \n  '
        result = BaseAgent._parse_json_response(text)
        assert result == {"key": "value"}

    def test_markdown_code_block_with_json_tag(self) -> None:
        text = 'Here is the result:\n```json\n{"input_state": {}, "stubs": {"READ": "00"}}\n```'
        result = BaseAgent._parse_json_response(text)
        assert result == {"input_state": {}, "stubs": {"READ": "00"}}

    def test_markdown_code_block_without_json_tag(self) -> None:
        text = 'Result:\n```\n{"a": 1}\n```'
        result = BaseAgent._parse_json_response(text)
        assert result == {"a": 1}

    def test_embedded_json_in_natural_language(self) -> None:
        text = (
            "Based on my analysis, here are the parameters:\n"
            '{"input_state": {"WS-FLAG": "Y"}, "stubs": {"WRITE-LOG": "00"}}\n'
            "These should reach the target paragraph."
        )
        result = BaseAgent._parse_json_response(text)
        assert result == {
            "input_state": {"WS-FLAG": "Y"},
            "stubs": {"WRITE-LOG": "00"},
        }

    def test_invalid_input_returns_empty_dict(self) -> None:
        assert BaseAgent._parse_json_response("not json at all") == {}

    def test_empty_string_returns_empty_dict(self) -> None:
        assert BaseAgent._parse_json_response("") == {}

    def test_json_array_returns_empty_dict(self) -> None:
        """A JSON array is valid JSON but not the expected dict."""
        assert BaseAgent._parse_json_response('[1, 2, 3]') == {}

    def test_nested_json(self) -> None:
        text = '{"input_state": {"NESTED": {"DEEP": "value"}}, "stubs": {}}'
        result = BaseAgent._parse_json_response(text)
        assert result["input_state"]["NESTED"]["DEEP"] == "value"

    def test_malformed_json_in_code_block_falls_to_brace_extraction(self) -> None:
        """If the code block contains malformed JSON, try brace extraction."""
        text = '```json\nnot json\n```\nSome text {"fallback": true} more text'
        result = BaseAgent._parse_json_response(text)
        assert result == {"fallback": True}

    def test_malformed_everywhere_returns_empty(self) -> None:
        """When all strategies fail, return empty dict."""
        text = '```json\n{broken\n```\nno valid json {also broken'
        result = BaseAgent._parse_json_response(text)
        assert result == {}

    def test_no_braces_at_all(self) -> None:
        assert BaseAgent._parse_json_response("plain text no braces") == {}

    def test_trailing_comma_in_code_block(self) -> None:
        """LLMs frequently emit trailing commas before } or ]."""
        text = '```json\n{"input_state": {"WS-STATUS": "00",}, "stubs": {}}\n```'
        result = BaseAgent._parse_json_response(text)
        assert result == {"input_state": {"WS-STATUS": "00"}, "stubs": {}}

    def test_trailing_comma_multiline(self) -> None:
        text = (
            '```json\n'
            '{\n'
            '  "input_state": {\n'
            '    "WS-FLAG": "Y",\n'
            '  },\n'
            '  "stubs": {\n'
            '    "READ-FILE": "00",\n'
            '  }\n'
            '}\n'
            '```'
        )
        result = BaseAgent._parse_json_response(text)
        assert result == {
            "input_state": {"WS-FLAG": "Y"},
            "stubs": {"READ-FILE": "00"},
        }

    def test_trailing_comma_raw_json(self) -> None:
        text = '{"key": "value",}'
        result = BaseAgent._parse_json_response(text)
        assert result == {"key": "value"}

    def test_github_issue_case_json_with_newlines(self) -> None:
        """Test the specific case from GitHub issue #2 with ```json wrapper."""
        text = '''```json
{
  "input_state": {
    "WS-STATUS": "00"
  },
  "stubs": {}
}
```'''
        result = BaseAgent._parse_json_response(text)
        assert result == {"input_state": {"WS-STATUS": "00"}, "stubs": {}}

    def test_json_code_block_with_extra_whitespace(self) -> None:
        """Test ```json with extra whitespace around the JSON content."""
        text = '''```json  
  {
    "input_state": {"WS-STATUS": "00"},
    "stubs": {}
  }  
  ```'''
        result = BaseAgent._parse_json_response(text)
        assert result == {"input_state": {"WS-STATUS": "00"}, "stubs": {}}

    def test_json_code_block_no_newlines(self) -> None:
        """Test ```json format without newlines."""
        text = '```json{"input_state": {"WS-STATUS": "00"}, "stubs": {}}```'
        result = BaseAgent._parse_json_response(text)
        assert result == {"input_state": {"WS-STATUS": "00"}, "stubs": {}}


# ===========================================================================
# _complete tests
# ===========================================================================


class TestComplete:
    """Verify _complete calls the LLM provider correctly."""

    @pytest.mark.asyncio
    async def test_complete_returns_content(self) -> None:
        provider = FakeLLMProvider(response_text="hello from LLM")
        agent = ConcreteAgent(llm_provider=provider)
        messages = [Message(role="user", content="test")]
        result = await agent._complete(messages)
        assert result == "hello from LLM"

    @pytest.mark.asyncio
    async def test_complete_passes_model_and_temperature(self) -> None:
        provider = FakeLLMProvider()
        # Replace complete with a mock to inspect call args
        provider.complete = AsyncMock(  # type: ignore[method-assign]
            return_value=CompletionResponse(
                content="ok", model="custom", tokens_used=5
            )
        )
        agent = ConcreteAgent(
            llm_provider=provider, model="my-model", temperature=0.3
        )
        messages = [Message(role="user", content="test")]
        await agent._complete(messages)

        provider.complete.assert_called_once_with(
            messages, model="my-model", temperature=0.3
        )
