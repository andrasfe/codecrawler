"""ParagraphAgent for reaching specific paragraphs via call chains.

Uses CallChainStrategy to analyze the target paragraph and determine
what parameters are needed to reach it through the PERFORM chain.
"""

from __future__ import annotations

import logging
from pathlib import Path

from cobol_penetrator.agents.base import AgentContext, BaseAgent
from cobol_penetrator.llm_providers.protocol import LLMProvider
from cobol_penetrator.mock_reader import ProgramStructure
from cobol_penetrator.strategies.call_chain import CallChainStrategy
from cobol_penetrator.tickets.models import ParagraphTicket, Ticket

logger = logging.getLogger(__name__)


class ParagraphAgent(BaseAgent):
    """Agent that determines parameters to reach a specific paragraph.

    The ParagraphAgent reads the target paragraph's code, obtains
    the parent ticket's successful parameters, and uses an LLM via
    CallChainStrategy to determine what input state and stubs are
    needed to navigate the PERFORM call chain to the target.
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
        self.strategy = CallChainStrategy()

    async def build_context(
        self,
        ticket: Ticket,
        structure: ProgramStructure,
        mock_cbl_path: Path,
        **extra: object,
    ) -> AgentContext:
        """Build context for call chain analysis.

        Reads the target paragraph source code and resolves the parent
        ticket's successful parameters from the extra kwargs.

        Args:
            ticket: The paragraph ticket for the target paragraph.
            structure: Parsed program structure from the .mock.cbl file.
            mock_cbl_path: Path to the instrumented .mock.cbl file.
            **extra: Additional keyword arguments. Expected keys:
                - ``parent_params``: dict of successful params from
                  the parent ticket (optional).

        Returns:
            An AgentContext with the target paragraph code, call path,
            parent parameters, and stub list.
        """
        assert isinstance(ticket, ParagraphTicket), (
            f"ParagraphAgent requires a ParagraphTicket, got {type(ticket).__name__}"
        )

        paragraph_code = structure.get_paragraph_code(ticket.paragraph)

        # Get parent params from extra kwargs
        parent_params: dict | None = extra.get("parent_params")  # type: ignore[assignment]

        # Collect stubs referenced in the target paragraph
        stubs: list[str] = []
        para_info = structure.paragraphs[ticket.paragraph]
        for performed in para_info.performs:
            if performed not in structure.paragraphs:
                if performed not in stubs:
                    stubs.append(performed)

        call_path = list(ticket.call_path) if ticket.call_path else []

        logger.debug(
            "ParagraphAgent: target=%s, call_path=%s, parent_params=%s",
            ticket.paragraph,
            call_path,
            parent_params,
        )

        return AgentContext(
            ticket=ticket,
            structure=structure,
            paragraph_code=paragraph_code,
            parent_params=parent_params,
            call_path=call_path,
            extra={
                "target_paragraph": ticket.paragraph,
                "stubs": stubs,
            },
        )

    async def generate_params(self, context: AgentContext) -> dict:
        """Generate parameters to reach the target paragraph.

        Uses CallChainStrategy to build prompts and sends them
        to the LLM for analysis.

        Args:
            context: The agent context built by build_context.

        Returns:
            A dict with ``"input_state"`` and ``"stubs"`` keys, or
            a default empty dict if the LLM response cannot be parsed.
        """
        system_prompt = self.strategy.build_system_prompt(context)
        user_prompt = self.strategy.build_user_prompt(context)
        messages = self._build_messages(system_prompt, user_prompt)

        logger.debug(
            "ParagraphAgent: sending %d messages to LLM", len(messages)
        )
        raw_response = await self._complete(messages)

        params = self._parse_json_response(raw_response)
        if not params:
            logger.warning(
                "ParagraphAgent: LLM returned unparseable response: %.200s",
                raw_response,
            )
            return {"input_state": {}, "stubs": {}}

        # Ensure required keys exist
        params.setdefault("input_state", {})
        params.setdefault("stubs", {})
        return params
