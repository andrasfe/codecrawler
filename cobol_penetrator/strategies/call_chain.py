"""CallChainStrategy for ParagraphAgent.

Builds LLM prompts to reach a specific paragraph by following
the PERFORM call chain from the entry point.
"""

from __future__ import annotations

import re

from cobol_penetrator.agents.base import AgentContext
from cobol_penetrator.strategies.base import Strategy
from cobol_penetrator.strategies.prompt_enrichment import (
    format_condition_hints,
    format_execution_history,
    format_variable_metadata,
)


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
        to target, the parent's successful parameters, known stubs,
        and variable metadata from the field report (if available).

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

        prompt = (
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

        # Enrich with variable metadata when field report is available
        if context.field_report:
            # Extract variable names referenced in the paragraph code
            relevant_vars = _extract_vars_from_code(
                context.paragraph_code, context.field_report
            )

            metadata = format_variable_metadata(
                context.field_report, relevant_vars or None
            )
            if metadata:
                prompt += (
                    f"\n\nVariable definitions from DATA DIVISION:\n"
                    f"{metadata}\n"
                )

            hints = format_condition_hints(
                context.field_report, relevant_vars or None
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


# Regex to find COBOL variable references (uppercase, hyphen-separated tokens)
_RE_COBOL_VAR = re.compile(r"\b([A-Z][A-Z0-9](?:[A-Z0-9-]*[A-Z0-9])?)\b")


def _extract_vars_from_code(
    code: str, field_report: object
) -> list[str]:
    """Extract variable names from paragraph code that exist in the field report.

    Scans the COBOL source code for tokens that match known field names
    from the field report.

    Args:
        code: The paragraph's COBOL source code.
        field_report: The FieldReport with a ``fields`` dict.

    Returns:
        A deduplicated list of variable names found in both the code
        and the field report, preserving first-occurrence order.
    """
    fields = getattr(field_report, "fields", {})
    if not fields or not code:
        return []

    found: list[str] = []
    seen: set[str] = set()
    for match in _RE_COBOL_VAR.finditer(code):
        name = match.group(1)
        if name in fields and name not in seen:
            seen.add(name)
            found.append(name)

    return found
