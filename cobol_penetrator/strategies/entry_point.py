"""EntryPointStrategy for ReconAgent.

Builds LLM prompts to discover initial parameters needed to reach
the program entry point paragraph.
"""

from __future__ import annotations

from cobol_penetrator.agents.base import AgentContext
from cobol_penetrator.strategies.base import Strategy


class EntryPointStrategy(Strategy):
    """Strategy for discovering initial input variables and stub outcomes.

    Used by ReconAgent to analyze the program's entry paragraph and
    determine what input state and stub configurations are needed
    to execute the entry point successfully.
    """

    def build_system_prompt(self, context: AgentContext) -> str:
        """Build the system prompt for entry point analysis.

        Args:
            context: The agent context carrying ticket and structure data.

        Returns:
            A system prompt instructing the LLM to analyze the program
            structure and determine initial parameters.
        """
        return (
            "You are a COBOL program analyst. Analyze the program structure "
            "and determine what initial input variables and stub outcomes "
            "are needed to execute the entry paragraph."
        )

    def build_user_prompt(self, context: AgentContext) -> str:
        """Build the user prompt with entry paragraph details.

        Includes the entry paragraph source code, discovered stubs,
        and asks for a JSON response with input_state and stubs.

        Args:
            context: The agent context with paragraph code and structure.

        Returns:
            A user prompt containing the entry paragraph code and
            a request for JSON-formatted parameters.
        """
        stubs = context.extra.get("stubs", [])
        stubs_text = ", ".join(stubs) if stubs else "None found"

        return (
            f"I need to execute the entry paragraph of a COBOL program.\n\n"
            f"Entry paragraph code:\n"
            f"```cobol\n{context.paragraph_code}\n```\n\n"
            f"Stubs found in the program: {stubs_text}\n\n"
            f"What initial input variables and stub outcomes should I set "
            f"to execute this paragraph?\n"
            f'Return as JSON: {{"input_state": {{}}, "stubs": {{}}}}'
        )
