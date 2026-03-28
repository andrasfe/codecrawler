"""EntryPointStrategy for ReconAgent.

Builds LLM prompts to discover initial parameters needed to reach
the program entry point paragraph.
"""

from __future__ import annotations

from cobol_penetrator.agents.base import AgentContext
from cobol_penetrator.strategies.base import Strategy
from cobol_penetrator.strategies.prompt_enrichment import (
    format_condition_hints,
    format_execution_history,
    format_variable_metadata,
)


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
        variable metadata from the field report (if available), and
        asks for a JSON response with input_state and stubs.

        Args:
            context: The agent context with paragraph code and structure.

        Returns:
            A user prompt containing the entry paragraph code and
            a request for JSON-formatted parameters.
        """
        stubs = context.extra.get("stubs", [])
        stubs_text = ", ".join(stubs) if stubs else "None found"

        prompt = (
            f"I need to execute the entry paragraph of a COBOL program.\n\n"
            f"Entry paragraph code:\n"
            f"```cobol\n{context.paragraph_code}\n```\n\n"
            f"Stubs found in the program: {stubs_text}\n\n"
            f"What initial input variables and stub outcomes should I set "
            f"to execute this paragraph?\n"
            f'Return as JSON: {{"input_state": {{}}, "stubs": {{}}}}'
        )

        # Enrich with variable metadata when field report is available
        if context.field_report:
            # For entry point, include the first 20 fields by relevance
            # (status and flag fields first, then others)
            relevant_vars = _select_relevant_vars(context.field_report, 20)

            metadata = format_variable_metadata(
                context.field_report, relevant_vars
            )
            if metadata:
                prompt += (
                    f"\n\nVariable definitions from DATA DIVISION:\n"
                    f"{metadata}\n"
                )

            hints = format_condition_hints(
                context.field_report, relevant_vars
            )
            if hints:
                prompt += (
                    f"\nCondition values found in program:\n{hints}\n"
                )

        if context.execution_history:
            history = format_execution_history(context.execution_history)
            prompt += f"\nPrior attempts:\n{history}\n"

        if context.knowledge:
            from cobol_penetrator.strategies.prompt_enrichment import (
                format_knowledge_context,
            )

            knowledge_text = format_knowledge_context(
                context.knowledge, context.ticket, context.field_report
            )
            if knowledge_text:
                prompt += (
                    f"\n\nLearned knowledge from prior executions:\n"
                    f"{knowledge_text}\n"
                )

        if context.evoskill_text:
            prompt += f"\n\n{context.evoskill_text}"

        return prompt


def _select_relevant_vars(
    field_report: object, max_vars: int
) -> list[str]:
    """Select the most relevant variables for entry point prompts.

    Prioritizes status and flag variables (which control program flow)
    over internal variables.

    Args:
        field_report: The FieldReport with a ``fields`` dict.
        max_vars: Maximum number of variable names to return.

    Returns:
        A list of variable names, most relevant first.
    """
    fields = getattr(field_report, "fields", {})
    if not fields:
        return []

    priority_order = {"status": 0, "flag": 1, "input": 2, "internal": 3}
    sorted_names = sorted(
        fields.keys(),
        key=lambda n: (
            priority_order.get(fields[n].classification, 4),
            n,
        ),
    )
    return sorted_names[:max_vars]
