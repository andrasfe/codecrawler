"""Strategy system for COBOL coverage penetration."""

from .base import Strategy
from .branch_flip import BranchFlipStrategy
from .call_chain import CallChainStrategy
from .entry_point import EntryPointStrategy

__all__ = [
    "BranchFlipStrategy",
    "CallChainStrategy",
    "EntryPointStrategy",
    "Strategy",
]
