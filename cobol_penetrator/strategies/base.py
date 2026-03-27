"""Strategy ABC for parameter generation.

Strategies encapsulate the prompt-building logic for different kinds of
coverage targets (entry points, call chains, branch flips).  A Strategy
is stateless -- it receives an AgentContext and produces system and user
prompts that an agent feeds to the LLM.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from cobol_penetrator.agents.base import AgentContext


class Strategy(ABC):
    """Abstract base class for parameter generation strategies.

    Each concrete Strategy knows how to build LLM prompts for a
    particular class of ticket (e.g., reaching an entry paragraph,
    following a call chain, or flipping a branch direction).
    """

    @abstractmethod
    def build_system_prompt(self, context: AgentContext) -> str:
        """Build the system prompt for the LLM.

        Args:
            context: The agent context carrying ticket and structure data.

        Returns:
            A system prompt string instructing the LLM on how to respond.
        """
        ...

    @abstractmethod
    def build_user_prompt(self, context: AgentContext) -> str:
        """Build the user prompt with ticket-specific details.

        Args:
            context: The agent context carrying ticket and structure data.

        Returns:
            A user prompt string with the concrete analysis request.
        """
        ...
