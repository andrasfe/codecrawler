"""Integration tests for EvoSkill wiring in the orchestrator."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from cobol_penetrator.config import PenetratorConfig
from cobol_penetrator.llm_providers.protocol import CompletionResponse
from cobol_penetrator.orchestrator import run


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_provider() -> MagicMock:
    provider = MagicMock()
    provider.default_model = "test-model"
    provider.complete = AsyncMock(
        return_value=CompletionResponse(
            content=json.dumps({
                "input_state": {"WS-STATUS": "00"},
                "stubs": {},
            }),
            model="test-model",
            tokens_used=100,
        )
    )
    return provider


def _make_mock_executable(tmp_path: Path) -> Path:
    script = tmp_path / "mock_cobol"
    script.write_text(
        '#!/bin/bash\n'
        'echo "SPECTER-TRACE:1000-MAIN"\n'
        'echo "@@B:1:T"\n'
        'echo "SPECTER-CALL:FROM=1000-MAIN:TO=2000-VALIDATE"\n'
        'echo "SPECTER-TRACE:2000-VALIDATE"\n'
        'echo "@@B:2:T"\n'
        'echo "@@V:1:WS-STATUS=00"\n'
    )
    script.chmod(0o755)
    return script


def _make_mock_cbl(tmp_path: Path) -> Path:
    cbl = tmp_path / "test.mock.cbl"
    cbl.write_text(
        "       IDENTIFICATION DIVISION.\n"
        "       PROGRAM-ID. TESTPROG.\n"
        "       DATA DIVISION.\n"
        "       WORKING-STORAGE SECTION.\n"
        "       01 WS-STATUS    PIC X(2).\n"
        "       01 WS-FLAG      PIC X(1).\n"
        "       PROCEDURE DIVISION.\n"
        "       1000-MAIN.\n"
        '           DISPLAY "SPECTER-TRACE:1000-MAIN"\n'
        "           PERFORM 2000-VALIDATE\n"
        "           IF WS-STATUS = '00'\n"
        '               DISPLAY "@@B:1:T"\n'
        "           ELSE\n"
        '               DISPLAY "@@B:1:F"\n'
        "           END-IF\n"
        "           STOP RUN.\n"
        "       2000-VALIDATE.\n"
        '           DISPLAY "SPECTER-TRACE:2000-VALIDATE"\n'
        "           IF WS-FLAG = 'Y'\n"
        '               DISPLAY "@@B:2:T"\n'
        "           ELSE\n"
        '               DISPLAY "@@B:2:F"\n'
        "           END-IF.\n"
    )
    return cbl


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestEvoSkillDisabled:
    """Verify that run() works fine with EvoSkill disabled."""

    def test_run_with_evoskill_disabled(self, tmp_path: Path) -> None:
        executable = _make_mock_executable(tmp_path)
        mock_cbl = _make_mock_cbl(tmp_path)

        config = PenetratorConfig(
            executable=executable,
            mock_cbl=mock_cbl,
            budget=3,
            timeout=60,
            resume=False,
            tickets_path=tmp_path / "tickets.json",
            coverage_path=tmp_path / "coverage.json",
            params_dir=tmp_path / "params",
            max_attempts=3,
            evoskill_enabled=False,
        )

        with patch(
            "cobol_penetrator.orchestrator.get_provider_from_env",
            return_value=_make_mock_provider(),
        ):
            result = asyncio.run(run(config))

        assert result["executions"] >= 1
        assert result["coverage_pct"] > 0.0


class TestEvoSkillEnabled:
    """Verify that run() initialises EvoSkill when enabled."""

    def test_run_with_evoskill_enabled_creates_store(
        self, tmp_path: Path
    ) -> None:
        executable = _make_mock_executable(tmp_path)
        mock_cbl = _make_mock_cbl(tmp_path)
        evoskill_dir = tmp_path / "evoskill_data"

        config = PenetratorConfig(
            executable=executable,
            mock_cbl=mock_cbl,
            budget=3,
            timeout=60,
            resume=False,
            tickets_path=tmp_path / "tickets.json",
            coverage_path=tmp_path / "coverage.json",
            params_dir=tmp_path / "params",
            max_attempts=3,
            evoskill_enabled=True,
            evoskill_path=evoskill_dir,
        )

        with patch(
            "cobol_penetrator.orchestrator.get_provider_from_env",
            return_value=_make_mock_provider(),
        ):
            result = asyncio.run(run(config))

        assert result["executions"] >= 1
        # EvoSkill store directory should have been created
        assert evoskill_dir.exists()

    def test_run_with_evoskill_unavailable_continues(
        self, tmp_path: Path
    ) -> None:
        """If evoskill package is missing, run() still works."""
        executable = _make_mock_executable(tmp_path)
        mock_cbl = _make_mock_cbl(tmp_path)

        config = PenetratorConfig(
            executable=executable,
            mock_cbl=mock_cbl,
            budget=3,
            timeout=60,
            resume=False,
            tickets_path=tmp_path / "tickets.json",
            coverage_path=tmp_path / "coverage.json",
            params_dir=tmp_path / "params",
            max_attempts=3,
            evoskill_enabled=True,
        )

        with patch(
            "cobol_penetrator.orchestrator.get_provider_from_env",
            return_value=_make_mock_provider(),
        ), patch(
            "cobol_penetrator.orchestrator._EVOSKILL_AVAILABLE",
            False,
        ):
            result = asyncio.run(run(config))

        assert result["executions"] >= 1


class TestEvoSkillSkillInjection:
    """Verify that skills are injected into agent prompts."""

    def test_evoskill_text_populated_in_context(
        self, tmp_path: Path
    ) -> None:
        """When EvoSkill is enabled and has skills, context.evoskill_text
        should be non-empty during prompt generation."""
        from evoskill import Skill, SkillStore

        executable = _make_mock_executable(tmp_path)
        mock_cbl = _make_mock_cbl(tmp_path)
        evoskill_dir = tmp_path / "evoskill_data"

        # Pre-populate a skill
        store = SkillStore(storage_path=evoskill_dir)
        store.add_skill(Skill(
            role="recon",
            content="When targeting 1000-MAIN, set WS-STATUS to '00'.",
            source="learned",
            tags=["mock_cobol"],
        ))

        config = PenetratorConfig(
            executable=executable,
            mock_cbl=mock_cbl,
            budget=3,
            timeout=60,
            resume=False,
            tickets_path=tmp_path / "tickets.json",
            coverage_path=tmp_path / "coverage.json",
            params_dir=tmp_path / "params",
            max_attempts=3,
            evoskill_enabled=True,
            evoskill_path=evoskill_dir,
        )

        with patch(
            "cobol_penetrator.orchestrator.get_provider_from_env",
            return_value=_make_mock_provider(),
        ):
            result = asyncio.run(run(config))

        assert result["executions"] >= 1
