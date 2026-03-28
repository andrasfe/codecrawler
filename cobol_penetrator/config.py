"""Configuration for the COBOL Penetrator system."""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class AgentConfig:
    """Per-agent LLM configuration."""

    model: str | None = None
    temperature: float = 0.7
    max_attempts: int = 5


@dataclass
class PenetratorConfig:
    """Top-level configuration for a penetration run."""

    executable: Path = field(default_factory=lambda: Path("."))
    mock_cbl: Path = field(default_factory=lambda: Path("."))
    budget: int = 10000
    timeout: int = 3600
    resume: bool = False
    tickets_path: Path = field(default_factory=lambda: Path(".tickets.json"))
    coverage_path: Path = field(default_factory=lambda: Path("reports/coverage.json"))
    params_dir: Path = field(default_factory=lambda: Path("reports/successful_params"))
    max_attempts: int = 5
    max_turns_per_ticket: int = 10
    knowledge_path: Path = field(default_factory=lambda: Path(".knowledge.json"))

    # EvoSkill settings
    evoskill_enabled: bool = True
    evoskill_path: Path = field(default_factory=lambda: Path("./evoskill_data"))

    # LLM settings (loaded from .env)
    llm_provider: str = "openrouter"
    llm_default_model: str | None = None
    llm_timeout: int = 600

    # Heuristic mode: "llm_only", "heuristic_only", or "hybrid"
    heuristic_mode: str = "hybrid"

    # Agent-specific configs
    recon_agent: AgentConfig = field(default_factory=AgentConfig)
    paragraph_agent: AgentConfig = field(default_factory=AgentConfig)
    branch_agent: AgentConfig = field(default_factory=AgentConfig)


def load_config(args: list[str] | None = None) -> PenetratorConfig:
    """Load configuration from .env file and CLI arguments."""
    load_dotenv()

    parser = argparse.ArgumentParser(
        prog="cobol-penetrator",
        description="Multi-agent COBOL coverage penetration system",
    )
    parser.add_argument("--executable", type=Path, help="Path to compiled COBOL executable")
    parser.add_argument("--mock-cbl", type=Path, help="Path to instrumented .mock.cbl source")
    parser.add_argument("--budget", type=int, default=10000, help="Max execution attempts")
    parser.add_argument("--timeout", type=int, default=3600, help="Total timeout in seconds")
    parser.add_argument("--resume", action="store_true", help="Resume from prior run")
    parser.add_argument("--status", action="store_true", help="Show status report and exit")
    parser.add_argument("--tickets-path", type=Path, default=Path(".tickets.json"))
    parser.add_argument("--coverage-path", type=Path, default=Path("reports/coverage.json"))
    parser.add_argument("--max-attempts", type=int, default=5, help="Max attempts per ticket")

    parsed = parser.parse_args(args)

    config = PenetratorConfig(
        budget=parsed.budget,
        timeout=parsed.timeout,
        resume=parsed.resume,
        tickets_path=parsed.tickets_path,
        coverage_path=parsed.coverage_path,
        max_attempts=parsed.max_attempts,
        llm_provider=os.getenv("LLM_PROVIDER", "openrouter"),
        llm_default_model=os.getenv("LLM_DEFAULT_MODEL"),
        llm_timeout=int(os.getenv("LLM_TIMEOUT", "600")),
        evoskill_enabled=os.getenv("EVOSKILL_ENABLED", "1") not in ("0", "false", "no"),
        evoskill_path=Path(os.getenv("EVOSKILL_STORAGE_PATH", "./evoskill_data")),
    )

    if parsed.executable:
        config.executable = parsed.executable
    if parsed.mock_cbl:
        config.mock_cbl = parsed.mock_cbl

    return config
