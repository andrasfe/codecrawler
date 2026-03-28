"""Tests for cobol_penetrator.strategies.branch_flip."""

from __future__ import annotations

from pathlib import Path

import pytest

from cobol_penetrator.agents.base import AgentContext
from cobol_penetrator.analysis.variable_domain import VariableDomain
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


class TestBranchFlipStrategyEnrichedPrompt:
    """Verify prompts include metadata when field_report is present."""

    def test_prompt_includes_condition_var_metadata(
        self, strategy: BranchFlipStrategy, branch_context: AgentContext
    ) -> None:
        """Condition variables should have their metadata included."""
        fields = {
            "WS-STATUS": _make_domain(
                "WS-STATUS",
                condition_literals=["00", "10", "23"],
            ),
        }
        branch_context.field_report = _FakeFieldReport(fields=fields)
        prompt = strategy.build_user_prompt(branch_context)
        assert "Variable definitions from DATA DIVISION:" in prompt
        assert "WS-STATUS" in prompt
        assert "type=alpha" in prompt

    def test_prompt_includes_condition_hints_for_condition_vars(
        self, strategy: BranchFlipStrategy, branch_context: AgentContext
    ) -> None:
        fields = {"WS-STATUS": _make_domain("WS-STATUS")}
        hints = {"WS-STATUS": ["00", "10"]}
        branch_context.field_report = _FakeFieldReport(
            fields=fields, condition_hints=hints
        )
        prompt = strategy.build_user_prompt(branch_context)
        assert "Condition values found in program:" in prompt
        assert "WS-STATUS is compared to:" in prompt

    def test_prompt_includes_execution_history(
        self, strategy: BranchFlipStrategy, branch_context: AgentContext
    ) -> None:
        branch_context.execution_history = [
            {
                "input_state": {"WS-STATUS": "00"},
                "stubs": {},
                "paragraphs_hit": ["1000-MAIN"],
                "branches_hit": {"1": "F"},
            }
        ]
        prompt = strategy.build_user_prompt(branch_context)
        assert "Prior attempts" in prompt
        assert "Attempt 1:" in prompt

    def test_no_field_report_no_enrichment(
        self, strategy: BranchFlipStrategy, branch_context: AgentContext
    ) -> None:
        branch_context.field_report = None
        prompt = strategy.build_user_prompt(branch_context)
        assert "Variable definitions from DATA DIVISION:" not in prompt
        assert "Condition values found in program:" not in prompt

    def test_uses_condition_vars_as_relevant_vars(
        self, strategy: BranchFlipStrategy, branch_context: AgentContext
    ) -> None:
        """Only condition_vars should appear in the enrichment, not all fields."""
        fields = {
            "WS-STATUS": _make_domain("WS-STATUS"),
            "WS-UNRELATED": _make_domain("WS-UNRELATED"),
        }
        branch_context.field_report = _FakeFieldReport(fields=fields)
        prompt = strategy.build_user_prompt(branch_context)
        # WS-STATUS is a condition var; WS-UNRELATED is not
        assert "WS-STATUS" in prompt
        # The enrichment section should not include WS-UNRELATED
        enrichment_start = prompt.find(
            "Variable definitions from DATA DIVISION:"
        )
        if enrichment_start >= 0:
            enrichment_section = prompt[enrichment_start:]
            assert "WS-UNRELATED" not in enrichment_section

    def test_no_condition_vars_includes_all_field_metadata(
        self, strategy: BranchFlipStrategy, branch_context: AgentContext
    ) -> None:
        """If condition_vars is empty, relevant_vars is None -> all fields."""
        branch_context.extra["condition_vars"] = []
        fields = {
            "WS-STATUS": _make_domain("WS-STATUS"),
            "WS-FLAG": _make_domain("WS-FLAG"),
        }
        branch_context.field_report = _FakeFieldReport(fields=fields)
        prompt = strategy.build_user_prompt(branch_context)
        assert "Variable definitions from DATA DIVISION:" in prompt


# ---------------------------------------------------------------------------
# Tests: Knowledge context in prompts
# ---------------------------------------------------------------------------


class TestBranchFlipStrategyKnowledgeContext:
    """Verify prompts include knowledge context when available."""

    def test_prompt_includes_containing_paragraph_params(
        self, strategy: BranchFlipStrategy, branch_context: AgentContext
    ) -> None:
        from cobol_penetrator.knowledge import LearnedKnowledge

        knowledge = LearnedKnowledge()
        knowledge.successful_params["1000-MAIN"] = {
            "input_state": {"WS-STATUS": "00"},
            "stubs": {},
        }
        branch_context.knowledge = knowledge
        prompt = strategy.build_user_prompt(branch_context)
        assert "Learned knowledge from prior executions" in prompt
        assert "Containing paragraph reached with" in prompt

    def test_no_knowledge_no_section(
        self, strategy: BranchFlipStrategy, branch_context: AgentContext
    ) -> None:
        branch_context.knowledge = None
        prompt = strategy.build_user_prompt(branch_context)
        assert "Learned knowledge from prior executions" not in prompt

    def test_empty_knowledge_no_section(
        self, strategy: BranchFlipStrategy, branch_context: AgentContext
    ) -> None:
        from cobol_penetrator.knowledge import LearnedKnowledge

        branch_context.knowledge = LearnedKnowledge()
        prompt = strategy.build_user_prompt(branch_context)
        assert "Learned knowledge from prior executions" not in prompt

    def test_failed_attempts_appear(
        self, strategy: BranchFlipStrategy, branch_context: AgentContext
    ) -> None:
        from cobol_penetrator.knowledge import LearnedKnowledge

        knowledge = LearnedKnowledge()
        knowledge.failed_attempts["BRANCH-1-T"] = [
            {"input_state": {}, "stubs": {}},
            {"input_state": {"WS-STATUS": "10"}, "stubs": {}},
        ]
        branch_context.knowledge = knowledge
        prompt = strategy.build_user_prompt(branch_context)
        assert "Prior failed attempts (2 total)" in prompt
