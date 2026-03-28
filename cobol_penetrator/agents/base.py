"""Base agent ABC for the COBOL penetration agent system.

Defines AgentContext (shared context dataclass) and BaseAgent (abstract base
class).  Agents use the llm_providers Protocol directly -- no LangChain
dependency.
"""

from __future__ import annotations

import json
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from cobol_penetrator.llm_providers.protocol import LLMProvider, Message
from cobol_penetrator.mock_reader import ProgramStructure
from cobol_penetrator.tickets.models import Ticket

if TYPE_CHECKING:
    from cobol_penetrator.analysis.field_report import FieldReport
    from cobol_penetrator.knowledge import LearnedKnowledge

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# AgentContext
# ---------------------------------------------------------------------------


@dataclass
class AgentContext:
    """Context built by an agent for parameter generation.

    Carries everything a Strategy needs to formulate LLM prompts:
    the ticket under investigation, the program structure, extracted
    source code, and any prior knowledge from parent tickets.

    Attributes:
        ticket: The ticket being worked on.
        structure: Parsed program structure from the .mock.cbl file.
        paragraph_code: Source code of the target paragraph.
        parent_params: Successful parameters from a parent ticket, if any.
        variable_snapshots: ``@@V:`` snapshots keyed by branch ID.
        call_path: Ordered list of paragraphs from entry to target.
        extra: Arbitrary additional data for strategy-specific needs.
        field_report: Optional FieldReport from DATA DIVISION analysis.
        execution_history: Prior execution attempts for this ticket.
        knowledge: Shared knowledge accumulated across all tickets in
            the current penetration run. ``None`` for backward compat.
    """

    ticket: Ticket
    structure: ProgramStructure
    paragraph_code: str = ""
    parent_params: dict | None = None
    variable_snapshots: dict[str, dict[str, str]] = field(default_factory=dict)
    call_path: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)
    field_report: FieldReport | None = None
    execution_history: list[dict] = field(default_factory=list)
    knowledge: LearnedKnowledge | None = None


# ---------------------------------------------------------------------------
# BaseAgent ABC
# ---------------------------------------------------------------------------


class BaseAgent(ABC):
    """Abstract base class for penetration agents.

    Simplified from war_rig's pattern -- no LangChain dependency.
    Uses llm_providers Protocol directly.

    Subclasses must implement :meth:`build_context` and
    :meth:`generate_params`.  Helper methods :meth:`_complete`,
    :meth:`_build_messages`, and :meth:`_parse_json_response` are
    provided for common LLM interaction patterns.
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
        model: str | None = None,
        temperature: float = 0.7,
    ) -> None:
        self.llm = llm_provider
        self.model = model
        self.temperature = temperature
        self.name = self.__class__.__name__

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    async def build_context(
        self,
        ticket: Ticket,
        structure: ProgramStructure,
        mock_cbl_path: Path,
    ) -> AgentContext:
        """Build the context needed for parameter generation.

        Args:
            ticket: The ticket being worked on.
            structure: Parsed program structure.
            mock_cbl_path: Path to the instrumented .mock.cbl file.

        Returns:
            An AgentContext populated with ticket-relevant information.
        """
        ...

    @abstractmethod
    async def generate_params(self, context: AgentContext) -> dict:
        """Generate test parameters using LLM analysis.

        Args:
            context: The agent context built by :meth:`build_context`.

        Returns:
            A dict with ``"input_state"`` and ``"stubs"`` keys describing
            the parameters to pass to the COBOL executable.
        """
        ...

    # ------------------------------------------------------------------
    # LLM helpers
    # ------------------------------------------------------------------

    async def _complete(self, messages: list[Message]) -> str:
        """Call the LLM and return the content string.

        Args:
            messages: Conversation messages to send.

        Returns:
            The text content of the completion response.
        """
        response = await self.llm.complete(
            messages, model=self.model, temperature=self.temperature
        )
        return response.content

    def _build_messages(
        self, system_prompt: str, user_prompt: str
    ) -> list[Message]:
        """Build a standard system + user message list.

        Args:
            system_prompt: Instructions for the model.
            user_prompt: The specific request.

        Returns:
            A two-element list of Message objects.
        """
        return [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_prompt),
        ]

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_json_response(text: str) -> dict:
        """Extract a JSON dict from LLM response text.

        Handles three common formats:
        1. Raw JSON string
        2. JSON inside markdown code blocks (````` ```json ... ``` `````)
        3. JSON embedded in natural language (first ``{`` to last ``}``)

        Args:
            text: Raw text from the LLM response.

        Returns:
            Parsed dict, or an empty dict on parse failure.
        """
        text = text.strip()

        # Try direct parse
        try:
            result = json.loads(text)
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown code blocks
        code_block = re.search(
            r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL
        )
        if code_block:
            try:
                result = json.loads(code_block.group(1).strip())
                if isinstance(result, dict):
                    return result
            except json.JSONDecodeError:
                pass

        # Try finding first { to last }
        first_brace = text.find("{")
        last_brace = text.rfind("}")
        if first_brace != -1 and last_brace > first_brace:
            try:
                result = json.loads(text[first_brace : last_brace + 1])
                if isinstance(result, dict):
                    return result
            except json.JSONDecodeError:
                pass

        logger.warning("Failed to parse JSON from LLM response: %.200s", text)
        return {}
