"""Tests for the main CLI entry point."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from cobol_penetrator.__main__ import restart_clean
from cobol_penetrator.config import PenetratorConfig, load_config


def test_restart_clean_removes_state_files():
    """Test that restart_clean removes all state files and directories."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create mock state files and directories
        tickets_file = temp_path / ".tickets.json"
        knowledge_file = temp_path / ".knowledge.json"
        reports_dir = temp_path / "reports"
        evoskill_dir = temp_path / "evoskill_data"
        
        # Create the files and directories
        tickets_file.write_text('{"tickets": []}')
        knowledge_file.write_text('{"knowledge": {}}')
        reports_dir.mkdir()
        (reports_dir / "coverage.json").write_text('{"coverage": 0.0}')
        evoskill_dir.mkdir()
        (evoskill_dir / "test.json").write_text('{"data": "test"}')
        
        # Create config pointing to our temp files
        config = PenetratorConfig(
            tickets_path=tickets_file,
            knowledge_path=knowledge_file,
            coverage_path=reports_dir / "coverage.json",
            evoskill_path=evoskill_dir,
        )
        
        # Verify files exist before restart
        assert tickets_file.exists()
        assert knowledge_file.exists()
        assert reports_dir.exists()
        assert evoskill_dir.exists()
        
        # Call restart_clean
        with patch('builtins.print'):  # Suppress output for test
            restart_clean(config)
        
        # Verify files are gone after restart
        assert not tickets_file.exists()
        assert not knowledge_file.exists()
        assert not reports_dir.exists()
        assert not evoskill_dir.exists()


def test_restart_clean_handles_missing_files():
    """Test that restart_clean handles gracefully when files don't exist."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create config pointing to non-existent files
        config = PenetratorConfig(
            tickets_path=temp_path / ".tickets.json",
            knowledge_path=temp_path / ".knowledge.json",
            coverage_path=temp_path / "reports" / "coverage.json",
            evoskill_path=temp_path / "evoskill_data",
        )
        
        # Call restart_clean with missing files - should not raise
        with patch('builtins.print'):  # Suppress output for test
            restart_clean(config)


def test_load_config_includes_restart_option():
    """Test that load_config includes the restart option."""
    with patch('sys.argv', ['cobol_penetrator', '--restart']):
        config = load_config(['--restart'])
        assert config.restart is True
    
    config = load_config([])
    assert config.restart is False


def test_restart_arg_parsing():
    """Test that --restart argument is parsed correctly."""
    # Test with --restart
    config = load_config(['--restart'])
    assert config.restart is True
    
    # Test without --restart
    config = load_config([])
    assert config.restart is False


def test_restart_with_other_args():
    """Test that --restart can be used with other arguments."""
    # Test --restart with executable and mock-cbl
    config = load_config([
        '--restart',
        '--executable', 'test.exe',
        '--mock-cbl', 'test.mock.cbl',
        '--budget', '100',
        '--timeout', '300'
    ])
    assert config.restart is True
    assert str(config.executable) == 'test.exe'
    assert str(config.mock_cbl) == 'test.mock.cbl'
    assert config.budget == 100
    assert config.timeout == 300


@patch('cobol_penetrator.__main__.restart_clean')
@patch('cobol_penetrator.__main__.asyncio.run')
def test_main_with_restart_continues_processing(mock_asyncio_run, mock_restart_clean):
    """Test that main() with --restart calls restart_clean and continues with processing."""
    from cobol_penetrator.__main__ import main

    # Create temporary executable and mock files
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        exe_file = temp_path / "test.exe"
        mock_file = temp_path / "test.mock.cbl"
        exe_file.write_text("dummy executable")
        mock_file.write_text("dummy mock cobol")

        mock_asyncio_run.return_value = {"executions": 0, "coverage_pct": 0.0}

        with patch('sys.argv', [
            'cobol_penetrator',
            '--restart',
            '--executable', str(exe_file),
            '--mock-cbl', str(mock_file),
        ]):
            with patch('cobol_penetrator.__main__.load_config') as mock_load_config:
                mock_config = PenetratorConfig(
                    executable=exe_file,
                    mock_cbl=mock_file,
                    restart=True,
                )
                mock_load_config.return_value = mock_config

                main()

                mock_restart_clean.assert_called_once_with(mock_config)
                mock_asyncio_run.assert_called_once()