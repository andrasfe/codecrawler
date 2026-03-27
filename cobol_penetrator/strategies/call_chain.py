"""CallChainStrategy for ParagraphAgent.

Builds LLM prompts to reach a specific paragraph by following
the PERFORM call chain from the entry point.
"""

from __future__ import annotations

from cobol_penetrator.agents.base import AgentContext
from cobol_penetrator.strategies.base import Strategy


class CallChainStrategy(Strategy):
    """Strategy for reaching a specific paragraph via a PERFORM chain.

    Used by ParagraphAgent to analyze the target paragraph's code,
    the call path leading to it, and the parent's successful parameters
    to determine what input state and stubs are needed.
    """

    def build_system_prompt(self, context: AgentContext) -> str:
        """Build the system prompt for call chain analysis.

        Args:
            context: The agent context carrying ticket and structure data.

        Returns:
            A system prompt instructing the LLM to determine parameters
            for reaching a target paragraph via PERFORM chain.
        """
        return (
            "You are a COBOL program analyst. Your task is to determine "
            "what input variables and stub outcomes are needed to reach "
            "a specific target paragraph via a PERFORM call chain. "
            "Analyze the call path, the parent paragraph's successful "
            "parameters, and the target paragraph's code to produce "
            "the correct parameter set."
        )

    def build_user_prompt(self, context: AgentContext) -> str:
        """Build the user prompt with call chain details.

        Includes the target paragraph code, the call path from entry
        to target, the parent's successful parameters, and known stubs.

        Args:
            context: The agent context with paragraph code, call path,
                parent params, and structure data.

        Returns:
            A user prompt requesting JSON-formatted parameters.
        """
        call_path_text = (
            " -> ".join(context.call_path) if context.call_path else "N/A"
        )

        parent_params_text = (
            str(context.parent_params) if context.parent_params else "None"
        )

        stubs = context.extra.get("stubs", [])
        stubs_text = ", ".join(stubs) if stubs else "None found"

        target_paragraph = context.extra.get("target_paragraph", "unknown")

        return (
            f"I need to reach paragraph {target_paragraph} "
            f"in a COBOL program.\n\n"
            f"Call path: {call_path_text}\n\n"
            f"Target paragraph code:\n"
            f"```cobol\n{context.paragraph_code}\n```\n\n"
            f"Parent's successful parameters: {parent_params_text}\n\n"
            f"Known stubs: {stubs_text}\n\n"
            f"What input variables and stub outcomes should I set "
            f"to reach this paragraph?\n"
            f'Return as JSON: {{"input_state": {{}}, "stubs": {{}}}}'
        )
