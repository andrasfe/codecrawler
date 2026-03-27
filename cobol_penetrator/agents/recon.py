"""ReconAgent for entry point parameter discovery.

Uses EntryPointStrategy to analyze the program's entry paragraph
and determine initial input variables and stub outcomes.
"""

from __future__ import annotations

import logging
from pathlib import Path

from cobol_penetrator.agents.base import AgentContext, BaseAgent
from cobol_penetrator.llm_providers.protocol import LLMProvider
from cobol_penetrator.mock_reader import ProgramStructure
from cobol_penetrator.strategies.entry_point import EntryPointStrategy
from cobol_penetrator.tickets.models import Ticket

logger = logging.getLogger(__name__)


class ReconAgent(BaseAgent):
    """Agent that discovers initial parameters for the program entry point.

    The ReconAgent reads the entry paragraph code, identifies stubs
    referenced in the program, and uses an LLM via EntryPointStrategy
    to determine what input state and stub configurations are needed
    to begin program execution.
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
        model: str | None = None,
        temperature: float = 0.7,
    ) -> None:
        super().__init__(
            llm_provider=llm_provider,
            model=model,
            temperature=temperature,
        )
        self.strategy = EntryPointStrategy()

    async def build_context(
        self,
        ticket: Ticket,
        structure: ProgramStructure,
        mock_cbl_path: Path,
    ) -> AgentContext:
        """Build context for entry point analysis.

        Reads the entry paragraph source code and collects stubs
        referenced throughout the program structure.

        Args:
            ticket: The paragraph ticket for the entry point.
            structure: Parsed program structure from the .mock.cbl file.
            mock_cbl_path: Path to the instrumented .mock.cbl file.

        Returns:
            An AgentContext with the entry paragraph code and stub list.
        """
        entry_code = structure.get_paragraph_code(structure.entry_paragraph)

        # Collect all stubs: paragraphs that are PERFORMed but have
        # no definition in the structure (external calls / mocked).
        # Also include any stubs from the ticket's required_stubs.
        stubs: list[str] = []
        for para_name, para_info in structure.paragraphs.items():
            for performed in para_info.performs:
                if performed not in structure.paragraphs:
                    if performed not in stubs:
                        stubs.append(performed)

        logger.debug(
            "ReconAgent: entry=%s, stubs=%s",
            structure.entry_paragraph,
            stubs,
        )

        return AgentContext(
            ticket=ticket,
            structure=structure,
            paragraph_code=entry_code,
            extra={"stubs": stubs},
        )

    async def generate_params(self, context: AgentContext) -> dict:
        """Generate initial parameters using LLM analysis.

        Uses EntryPointStrategy to build prompts and sends them
        to the LLM for analysis.

        Args:
            context: The agent context built by build_context.

        Returns:
            A dict with ``"input_state"`` and ``"stubs"`` keys, or
            an empty dict if the LLM response cannot be parsed.
        """
        system_prompt = self.strategy.build_system_prompt(context)
        user_prompt = self.strategy.build_user_prompt(context)
        messages = self._build_messages(system_prompt, user_prompt)

        logger.debug("ReconAgent: sending %d messages to LLM", len(messages))
        raw_response = await self._complete(messages)

        params = self._parse_json_response(raw_response)
        if not params:
            logger.warning(
                "ReconAgent: LLM returned unparseable response: %.200s",
                raw_response,
            )
            return {"input_state": {}, "stubs": {}}

        # Ensure required keys exist
        params.setdefault("input_state", {})
        params.setdefault("stubs", {})
        return params
