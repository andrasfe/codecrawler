"""Bridge between codecrawler's LLMProvider and EvoSkill's LLMCallable.

Provides adapters that wrap the async ``LLMProvider`` protocol into the
sync and async callables that EvoSkill expects for skill synthesis.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from cobol_penetrator.llm_providers.protocol import Message

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from cobol_penetrator.llm_providers.protocol import LLMProvider


def make_async_evoskill_llm(
    provider: LLMProvider,
) -> Callable[[list[dict[str, str]]], Awaitable[str]]:
    """Wrap an ``LLMProvider`` into an async callable for EvoSkill.

    Returns an async function with signature
    ``(messages: list[dict[str, str]]) -> str`` that EvoSkill's
    ``alearn_from_feedback`` and ``asynthesize_skill_*`` functions accept.

    Args:
        provider: A codecrawler LLMProvider instance.

    Returns:
        An async callable suitable for EvoSkill's ``llm`` parameter.
    """

    async def _llm(messages: list[dict[str, str]]) -> str:
        typed_messages = [
            Message(role=m["role"], content=m["content"]) for m in messages
        ]
        response = await provider.complete(typed_messages, temperature=0.3)
        return response.content

    return _llm


def make_sync_evoskill_llm(
    provider: LLMProvider,
) -> Callable[[list[dict[str, str]]], str]:
    """Wrap an ``LLMProvider`` into a sync callable for EvoSkill.

    Uses ``asyncio.run`` to bridge from sync to the provider's async
    ``complete`` method.  Intended for EvoSkill's sync-only APIs like
    ``consolidate()``.

    Args:
        provider: A codecrawler LLMProvider instance.

    Returns:
        A sync callable suitable for EvoSkill's ``llm`` parameter.
    """
    import asyncio

    def _llm(messages: list[dict[str, str]]) -> str:
        typed_messages = [
            Message(role=m["role"], content=m["content"]) for m in messages
        ]

        async def _call() -> str:
            response = await provider.complete(
                typed_messages, temperature=0.3
            )
            return response.content

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(_call())
        else:
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, _call()).result()

    return _llm


def agent_to_evoskill_role(agent: object) -> str:
    """Map a codecrawler agent instance to its EvoSkill role name.

    Args:
        agent: A ``BaseAgent`` subclass instance.

    Returns:
        One of ``"recon"``, ``"paragraph"``, or ``"branch"``.
    """
    from cobol_penetrator.agents.branch import BranchAgent
    from cobol_penetrator.agents.paragraph import ParagraphAgent
    from cobol_penetrator.agents.recon import ReconAgent

    if isinstance(agent, ReconAgent):
        return "recon"
    if isinstance(agent, ParagraphAgent):
        return "paragraph"
    if isinstance(agent, BranchAgent):
        return "branch"
    return "unknown"
