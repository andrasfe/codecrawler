"""BranchAgent for flipping branches to specific directions.

Uses BranchFlipStrategy to analyze branch conditions and determine
what parameters are needed to make a branch take a target direction.
"""

from __future__ import annotations

import logging
from pathlib import Path

from cobol_penetrator.agents.base import AgentContext, BaseAgent
from cobol_penetrator.llm_providers.protocol import LLMProvider
from cobol_penetrator.mock_reader import ProgramStructure
from cobol_penetrator.strategies.branch_flip import BranchFlipStrategy
from cobol_penetrator.tickets.models import BranchTicket, Ticket

logger = logging.getLogger(__name__)


class BranchAgent(BaseAgent):
    """Agent that determines parameters to flip a branch direction.

    The BranchAgent reads the containing paragraph's code, retrieves
    the branch condition and variables from the program structure,
    includes variable snapshots from prior executions, and uses an
    LLM via BranchFlipStrategy to determine what input changes will
    cause the branch to take the desired direction.
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
        self.strategy = BranchFlipStrategy()

    async def build_context(
        self,
        ticket: Ticket,
        structure: ProgramStructure,
        mock_cbl_path: Path,
        **extra: object,
    ) -> AgentContext:
        """Build context for branch flip analysis.

        Reads the containing paragraph's source code, extracts the
        branch condition and condition variables, and includes any
        variable snapshots from prior runs.

        Args:
            ticket: The branch ticket specifying the target branch
                and direction.
            structure: Parsed program structure from the .mock.cbl file.
            mock_cbl_path: Path to the instrumented .mock.cbl file.
            **extra: Additional keyword arguments. Expected keys:
                - ``variable_snapshots``: dict mapping branch IDs to
                  variable name/value dicts (optional).

        Returns:
            An AgentContext with the containing paragraph code, branch
            condition details, and variable snapshots.
        """
        assert isinstance(ticket, BranchTicket), (
            f"BranchAgent requires a BranchTicket, got {type(ticket).__name__}"
        )

        # Get the containing paragraph's code
        paragraph_code = structure.get_paragraph_code(ticket.paragraph)

        # Get the branch condition info from the structure
        branch_info = structure.branches.get(ticket.branch_id)
        condition_text = branch_info.condition_text if branch_info else ""
        condition_vars = (
            list(branch_info.condition_vars) if branch_info else []
        )

        # Get variable snapshots from extra kwargs or ticket
        variable_snapshots: dict[str, dict[str, str]] = extra.get(  # type: ignore[assignment]
            "variable_snapshots", {}
        ) or {}

        # Also incorporate the ticket's own variable_snapshot if present
        if ticket.variable_snapshot and ticket.branch_id:
            variable_snapshots.setdefault(
                ticket.branch_id, {}
            ).update(ticket.variable_snapshot)

        logger.debug(
            "BranchAgent: branch=%s, direction=%s, paragraph=%s, "
            "condition=%s, vars=%s",
            ticket.branch_id,
            ticket.direction,
            ticket.paragraph,
            condition_text,
            condition_vars,
        )

        return AgentContext(
            ticket=ticket,
            structure=structure,
            paragraph_code=paragraph_code,
            variable_snapshots=variable_snapshots,
            extra={
                "branch_id": ticket.branch_id,
                "target_direction": ticket.direction,
                "condition_text": condition_text,
                "condition_vars": condition_vars,
                "containing_paragraph": ticket.paragraph,
            },
        )

    async def generate_params(self, context: AgentContext) -> dict:
        """Generate parameters to flip the branch direction.

        Uses BranchFlipStrategy to build prompts and sends them
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
            "BranchAgent: sending %d messages to LLM", len(messages)
        )
        raw_response = await self._complete(messages)

        params = self._parse_json_response(raw_response)
        if not params:
            logger.warning(
                "BranchAgent: LLM returned unparseable response: %.200s",
                raw_response,
            )
            return {"input_state": {}, "stubs": {}}

        # Ensure required keys exist
        params.setdefault("input_state", {})
        params.setdefault("stubs", {})
        return params
