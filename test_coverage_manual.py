#!/usr/bin/env python3
"""Manual test to verify separate coverage functionality."""

import json
import tempfile
from pathlib import Path

# Import the classes directly
from cobol_penetrator.mock_reader import BranchInfo, ParagraphInfo, ProgramStructure
from cobol_penetrator.reports.coverage import CoverageTracker
from cobol_penetrator.trace_parser import ExecutionResult


def create_test_structure():
    """Create a test structure with paragraphs and branches."""
    paragraphs = {
        "1000-MAIN": ParagraphInfo(
            name="1000-MAIN",
            line_start=1,
            line_end=10,
            source_code="1000-MAIN.\n   ...",
            branches=["1"],
            performs=["2000-VALIDATE"],
        ),
        "2000-VALIDATE": ParagraphInfo(
            name="2000-VALIDATE",
            line_start=11,
            line_end=20,
            source_code="2000-VALIDATE.\n   ...",
            branches=["2"],
            performs=[],
        ),
        "3000-PROCESS": ParagraphInfo(
            name="3000-PROCESS",
            line_start=21,
            line_end=30,
            source_code="3000-PROCESS.\n   ...",
        ),
    }
    
    branches = {
        "1": BranchInfo(
            id="1",
            paragraph="1000-MAIN",
            condition_text="WS-STATUS = '00'",
            condition_vars=["WS-STATUS"],
            directions=["T", "F"],
        ),
        "2": BranchInfo(
            id="2",
            paragraph="2000-VALIDATE",
            condition_text="WS-FLAG = 'Y'",
            condition_vars=["WS-FLAG"],
            directions=["T", "F"],
        ),
    }
    
    return ProgramStructure(
        entry_paragraph="1000-MAIN",
        paragraphs=paragraphs,
        branches=branches,
        call_graph={name: info.performs for name, info in paragraphs.items()},
    )


def test_separate_coverage():
    """Test the separate coverage functionality."""
    print("Testing separate coverage functionality...")
    
    # Create test structure
    structure = create_test_structure()
    tracker = CoverageTracker(structure)
    
    print(f"Total paragraphs: {tracker.state.total_paragraphs}")
    print(f"Total branches: {tracker.state.total_branches}")
    
    # Hit 2 paragraphs and 1 branch direction
    result = ExecutionResult(
        paragraphs_hit=["1000-MAIN", "2000-VALIDATE"],
        branches_hit={"1": "T"},
    )
    tracker.update(result)
    
    print(f"Combined coverage: {tracker.coverage_pct}%")
    print(f"Paragraph coverage: {tracker._calculate_paragraph_pct()}%")
    print(f"Branch coverage: {tracker._calculate_branch_pct()}%")
    
    # Test saving to JSON
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = Path(f.name)
    
    tracker.save(temp_path)
    
    # Read back the JSON
    data = json.loads(temp_path.read_text())
    print("\nSaved JSON structure:")
    for key, value in data.items():
        if key != "history":  # Skip history for brevity
            print(f"  {key}: {value}")
    
    # Verify the new fields are present
    assert "paragraph_coverage_pct" in data
    assert "branch_coverage_pct" in data
    assert data["paragraph_coverage_pct"] == 66.67  # 2/3 paragraphs
    assert data["branch_coverage_pct"] == 25.0      # 1/4 branch directions
    
    print("\n✅ All tests passed!")
    
    # Clean up
    temp_path.unlink()


if __name__ == "__main__":
    test_separate_coverage()