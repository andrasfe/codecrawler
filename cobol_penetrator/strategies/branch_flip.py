"""BranchFlipStrategy for BranchAgent.

Builds LLM prompts to flip a branch to a specific direction
(T/F/W1/WO) by analyzing condition variables and prior run data.
"""

from __future__ import annotations

from cobol_penetrator.agents.base import AgentContext
from cobol_penetrator.strategies.base import Strategy
from cobol_penetrator.strategies.prompt_enrichment import (
    format_condition_hints,
    format_execution_history,
    format_variable_metadata,
)


class BranchFlipStrategy(Strategy):
    """Strategy for making a branch take a particular direction.

    Used by BranchAgent to analyze the branch condition, the variables
    involved, variable snapshots from prior executions, and the
    containing paragraph's code to determine what parameter changes
    will flip the branch to the desired direction.
    """

    def build_system_prompt(self, context: AgentContext) -> str:
        """Build the system prompt for branch flip analysis.

        Args:
            context: The agent context carrying ticket and structure data.

        Returns:
            A system prompt instructing the LLM to determine parameters
            for flipping a branch to a target direction.
        """
        return (
            "You are a COBOL program analyst. Your task is to determine "
            "what input variables and stub outcomes are needed to make "
            "a specific branch take a particular direction (T for true, "
            "F for false, W1 for WHEN clause 1, WO for WHEN OTHER). "
            "Analyze the branch condition, the variable snapshots from "
            "prior runs, and the containing paragraph's code to produce "
            "the correct parameter set."
        )

    def build_user_prompt(self, context: AgentContext) -> str:
        """Build the user prompt with branch flip details.

        Includes the branch condition text, condition variables, variable
        snapshots from prior executions, the containing paragraph code,
        variable metadata from the field report (if available), and
        asks for JSON with input_state and stubs.

        Args:
            context: The agent context with branch information, variable
                snapshots, paragraph code, and structure data.

        Returns:
            A user prompt requesting JSON-formatted parameters.
        """
        condition_text = context.extra.get("condition_text", "")
        condition_vars = context.extra.get("condition_vars", [])
        target_direction = context.extra.get("target_direction", "unknown")
        branch_id = context.extra.get("branch_id", "unknown")
        containing_paragraph = context.extra.get(
            "containing_paragraph", "unknown"
        )

        condition_vars_text = (
            ", ".join(condition_vars) if condition_vars else "None identified"
        )

        # Format variable snapshots from prior runs
        snapshots_lines: list[str] = []
        for snap_branch_id, snap_vars in context.variable_snapshots.items():
            for var_name, var_value in snap_vars.items():
                snapshots_lines.append(
                    f"  Branch {snap_branch_id}: {var_name} = {var_value}"
                )
        snapshots_text = (
            "\n".join(snapshots_lines)
            if snapshots_lines
            else "  No snapshots available"
        )

        prompt = (
            f"I need branch {branch_id} in paragraph "
            f"{containing_paragraph} to take direction "
            f"{target_direction}.\n\n"
            f"Branch condition: {condition_text}\n"
            f"Condition variables: {condition_vars_text}\n\n"
            f"Variable snapshots from prior runs:\n{snapshots_text}\n\n"
            f"Containing paragraph code:\n"
            f"```cobol\n{context.paragraph_code}\n```\n\n"
            f"What input variables and stub outcomes should I set "
            f"to make this branch take direction {target_direction}?\n"
            f'Return as JSON: {{"input_state": {{}}, "stubs": {{}}}}'
        )

        # Enrich with variable metadata when field report is available
        if context.field_report:
            # For branch flips, use the condition_vars specifically
            relevant_vars = list(condition_vars) if condition_vars else None

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

        return prompt
