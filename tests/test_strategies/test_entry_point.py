"""Tests for cobol_penetrator.strategies.entry_point."""

from __future__ import annotations

from pathlib import Path

import pytest

from cobol_penetrator.agents.base import AgentContext
from cobol_penetrator.analysis.variable_domain import VariableDomain
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


# ---------------------------------------------------------------------------
# Helpers for field report tests
# ---------------------------------------------------------------------------


class _FakeFieldReport:
    """Minimal FieldReport-like object for testing prompt enrichment."""

    def __init__(
        self,
        fields: dict[str, VariableDomain] | None = None,
        condition_hints: dict[str, list] | None = None,
    ) -> None:
        self.fields = fields or {}
        self.condition_hints = condition_hints or {}
        self.stub_variables: dict[str, str] = {}
        self.stub_operations: list[str] = []


def _make_domain(
    name: str,
    data_type: str = "alpha",
    max_length: int = 2,
    semantic_type: str = "status_file",
    classification: str = "status",
    condition_literals: list | None = None,
) -> VariableDomain:
    return VariableDomain(
        name=name,
        data_type=data_type,
        max_length=max_length,
        semantic_type=semantic_type,
        classification=classification,
        condition_literals=condition_literals or [],
    )


# ---------------------------------------------------------------------------
# Tests: Enriched prompts with field report
# ---------------------------------------------------------------------------


class TestEntryPointStrategyEnrichedPrompt:
    """Verify prompts include metadata when field_report is present."""

    def test_prompt_includes_variable_definitions(
        self, strategy: EntryPointStrategy, entry_context: AgentContext
    ) -> None:
        fields = {
            "WS-STATUS": _make_domain(
                "WS-STATUS",
                condition_literals=["00", "10"],
            ),
        }
        entry_context.field_report = _FakeFieldReport(fields=fields)
        prompt = strategy.build_user_prompt(entry_context)
        assert "Variable definitions from DATA DIVISION:" in prompt
        assert "WS-STATUS" in prompt
        assert "type=alpha" in prompt

    def test_prompt_includes_condition_hints(
        self, strategy: EntryPointStrategy, entry_context: AgentContext
    ) -> None:
        fields = {"WS-STATUS": _make_domain("WS-STATUS")}
        hints = {"WS-STATUS": ["00", "10", "23"]}
        entry_context.field_report = _FakeFieldReport(
            fields=fields, condition_hints=hints
        )
        prompt = strategy.build_user_prompt(entry_context)
        assert "Condition values found in program:" in prompt
        assert "WS-STATUS is compared to:" in prompt
        assert "'00'" in prompt

    def test_prompt_includes_execution_history(
        self, strategy: EntryPointStrategy, entry_context: AgentContext
    ) -> None:
        entry_context.execution_history = [
            {
                "input_state": {"WS-STATUS": "00"},
                "stubs": {},
                "paragraphs_hit": ["1000-MAIN"],
                "branches_hit": {},
            }
        ]
        prompt = strategy.build_user_prompt(entry_context)
        assert "Prior attempts" in prompt
        assert "Attempt 1:" in prompt

    def test_no_field_report_no_enrichment(
        self, strategy: EntryPointStrategy, entry_context: AgentContext
    ) -> None:
        """Without field_report, prompt should be identical to before."""
        entry_context.field_report = None
        prompt = strategy.build_user_prompt(entry_context)
        assert "Variable definitions from DATA DIVISION:" not in prompt
        assert "Condition values found in program:" not in prompt

    def test_field_report_prioritizes_status_and_flag(
        self, strategy: EntryPointStrategy, entry_context: AgentContext
    ) -> None:
        """Status and flag fields should appear before internal fields."""
        fields = {
            "WS-INTERNAL": _make_domain(
                "WS-INTERNAL",
                classification="internal",
                semantic_type="generic",
            ),
            "WS-STATUS": _make_domain(
                "WS-STATUS",
                classification="status",
                semantic_type="status_file",
            ),
            "WS-FLAG": _make_domain(
                "WS-FLAG",
                classification="flag",
                semantic_type="flag_bool",
            ),
        }
        entry_context.field_report = _FakeFieldReport(fields=fields)
        prompt = strategy.build_user_prompt(entry_context)
        # Status should come before internal in the output
        status_pos = prompt.find("WS-STATUS")
        internal_pos = prompt.find("WS-INTERNAL")
        assert status_pos < internal_pos


# ---------------------------------------------------------------------------
# Tests: Knowledge context in prompts
# ---------------------------------------------------------------------------


class TestEntryPointStrategyKnowledgeContext:
    """Verify prompts include knowledge context when available."""

    def test_prompt_includes_knowledge_section(
        self, strategy: EntryPointStrategy, entry_context: AgentContext
    ) -> None:
        from cobol_penetrator.knowledge import LearnedKnowledge

        knowledge = LearnedKnowledge()
        knowledge.successful_params["1000-MAIN"] = {
            "input_state": {"WS-STATUS": "00"},
            "stubs": {},
        }
        knowledge.stub_outcomes["READ-ACCOUNT"] = []

        entry_context.knowledge = knowledge
        prompt = strategy.build_user_prompt(entry_context)
        assert "Learned knowledge from prior executions" in prompt
        assert "Stub outcomes that produced coverage" in prompt

    def test_no_knowledge_no_section(
        self, strategy: EntryPointStrategy, entry_context: AgentContext
    ) -> None:
        entry_context.knowledge = None
        prompt = strategy.build_user_prompt(entry_context)
        assert "Learned knowledge from prior executions" not in prompt

    def test_empty_knowledge_no_section(
        self, strategy: EntryPointStrategy, entry_context: AgentContext
    ) -> None:
        from cobol_penetrator.knowledge import LearnedKnowledge

        entry_context.knowledge = LearnedKnowledge()
        prompt = strategy.build_user_prompt(entry_context)
        assert "Learned knowledge from prior executions" not in prompt
