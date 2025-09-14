"""Test context attachment in the report pipeline."""

import json
import tempfile
from pathlib import Path

import pytest

from srt_translator.eval.runner import _attach_context_to_issues, _ctx_window
from srt_translator.report.compiler import compile_report


class MockCue:
    """Mock SRT cue for testing."""

    def __init__(self, index: int, text: str):
        self.index = index
        self.text = text


def test_dnt_violation_includes_context():
    """Test that DNT violations get proper context attachment."""
    # Create mock cues
    source_cues = [MockCue(i + 1, f"Source line {i + 1}") for i in range(5)]
    target_cues = [MockCue(i + 1, f"Target line {i + 1}") for i in range(5)]

    # Create DNT issue (standardized format)
    dnt_issue = {
        "idx": 3,  # Middle cue
        "src": "Source line 3",
        "tgt": "Target line 3",
    }

    # Attach context
    _attach_context_to_issues([dnt_issue], source_cues, target_cues)

    # Verify context was attached
    assert "context" in dnt_issue
    context = dnt_issue["context"]

    # Check source context
    source_ctx = context["source"]
    assert source_ctx["prev2"] == "Source line 1"
    assert source_ctx["prev1"] == "Source line 2"
    assert source_ctx["cur"] == "Source line 3"
    assert source_ctx["next1"] == "Source line 4"
    assert source_ctx["next2"] == "Source line 5"

    # Check target context
    target_ctx = context["target"]
    assert target_ctx["prev2"] == "Target line 1"
    assert target_ctx["prev1"] == "Target line 2"
    assert target_ctx["cur"] == "Target line 3"
    assert target_ctx["next1"] == "Target line 4"
    assert target_ctx["next2"] == "Target line 5"


def test_context_edges_first_last_cues():
    """Test context attachment for first and last cues (edge cases)."""
    # Create mock cues
    source_cues = [MockCue(i + 1, f"Source line {i + 1}") for i in range(3)]
    target_cues = [MockCue(i + 1, f"Target line {i + 1}") for i in range(3)]

    # Test first cue (index 1)
    first_issue = {"idx": 1, "src": "Source line 1", "tgt": "Target line 1"}
    _attach_context_to_issues([first_issue], source_cues, target_cues)

    first_context = first_issue["context"]
    assert first_context["source"]["prev2"] == ""  # Empty at bounds
    assert first_context["source"]["prev1"] == ""  # Empty at bounds
    assert first_context["source"]["cur"] == "Source line 1"
    assert first_context["source"]["next1"] == "Source line 2"
    assert first_context["source"]["next2"] == "Source line 3"

    # Test last cue (index 3)
    last_issue = {"idx": 3, "src": "Source line 3", "tgt": "Target line 3"}
    _attach_context_to_issues([last_issue], source_cues, target_cues)

    last_context = last_issue["context"]
    assert last_context["source"]["prev2"] == "Source line 1"
    assert last_context["source"]["prev1"] == "Source line 2"
    assert last_context["source"]["cur"] == "Source line 3"
    assert last_context["source"]["next1"] == ""  # Empty at bounds
    assert last_context["source"]["next2"] == ""  # Empty at bounds


def test_context_window_function():
    """Test the _ctx_window helper function directly."""
    cues = [MockCue(i + 1, f"Line {i + 1}") for i in range(5)]

    # Test middle cue (index 3)
    ctx = _ctx_window(cues, 3, 2)
    assert len(ctx) == 5  # prev2, prev1, cur, next1, next2
    assert ctx[0] == (1, "Line 1")  # prev2
    assert ctx[1] == (2, "Line 2")  # prev1
    assert ctx[2] == (3, "Line 3")  # cur
    assert ctx[3] == (4, "Line 4")  # next1
    assert ctx[4] == (5, "Line 5")  # next2

    # Test first cue (index 1)
    ctx = _ctx_window(cues, 1, 2)
    assert len(ctx) == 3  # cur, next1, next2 (prev2, prev1 are out of bounds)
    assert ctx[0] == (1, "Line 1")  # cur
    assert ctx[1] == (2, "Line 2")  # next1
    assert ctx[2] == (3, "Line 3")  # next2

    # Test last cue (index 5)
    ctx = _ctx_window(cues, 5, 2)
    assert len(ctx) == 3  # prev2, prev1, cur (next1, next2 are out of bounds)
    assert ctx[0] == (3, "Line 3")  # prev2
    assert ctx[1] == (4, "Line 4")  # prev1
    assert ctx[2] == (5, "Line 5")  # cur


def test_standardized_issue_schema_validation():
    """Test that context attachment enforces standardized schema."""
    cues = [MockCue(i + 1, f"Line {i + 1}") for i in range(3)]

    # Test missing 'idx' key
    with pytest.raises(ValueError, match="missing required 'idx' key"):
        _attach_context_to_issues([{"src": "test", "tgt": "test"}], cues, cues)

    # Test non-integer 'idx'
    with pytest.raises(ValueError, match="must be int"):
        _attach_context_to_issues([{"idx": "not_int", "src": "test", "tgt": "test"}], cues, cues)

    # Test valid schema
    valid_issue = {"idx": 2, "src": "test", "tgt": "test"}
    _attach_context_to_issues([valid_issue], cues, cues)
    assert "context" in valid_issue


def test_compiler_passes_through_context():
    """Test that compiler passes context through from eval_report.json to report_v1.json."""
    # Create a minimal eval_report.json with context
    eval_data = {
        "version": "2.0.0",
        "timestamp": "2024-01-01T00:00:00Z",
        "totals": {"files_total": 1, "languages_total": 1, "issues_total": 1},
        "per_language": {
            "es": {
                "files": {
                    "test.srt": {
                        "issues_counts": {"timing_fail": 1},
                        "issues_detail": {
                            "timing_fail": [
                                {
                                    "cue_index": 2,
                                    "source_text": "Test source",
                                    "target_text": "Test target",
                                    "context": {
                                        "source": {
                                            "prev2": "",
                                            "prev1": "Prev line",
                                            "cur": "Test source",
                                            "next1": "Next line",
                                            "next2": "",
                                        },
                                        "target": {
                                            "prev2": "",
                                            "prev1": "Prev target",
                                            "cur": "Test target",
                                            "next1": "Next target",
                                            "next2": "",
                                        },
                                    },
                                }
                            ]
                        },
                    }
                }
            }
        },
    }

    # Write eval_report.json and ai_config.json
    with tempfile.TemporaryDirectory() as temp_dir:
        artifacts_dir = Path(temp_dir)
        eval_report_path = artifacts_dir / "eval_report.json"
        with open(eval_report_path, "w", encoding="utf-8") as f:
            json.dump(eval_data, f, indent=2)

        # Create minimal ai_config.json
        ai_config = {
            "version": "1.0.0",
            "timestamp": "2024-01-01T00:00:00Z",
            "target_languages": ["es"],
            "dnt_terms": [],
            "termbase": {},
        }
        ai_config_path = artifacts_dir / "ai_config.json"
        with open(ai_config_path, "w", encoding="utf-8") as f:
            json.dump(ai_config, f, indent=2)

        # Compile to report_v1.json
        report_v1_path = compile_report(artifacts_dir)

        # Load and verify context was passed through
        with open(report_v1_path, encoding="utf-8") as f:
            report_v1 = json.load(f)

        # Check that context is in the punch list
        errors = report_v1["punch_list"]["errors"]
        assert len(errors) == 1

        error = errors[0]
        assert "context" in error
        context = error["context"]

        # Verify context structure
        assert context["source"]["cur"] == "Test source"
        assert context["source"]["prev1"] == "Prev line"
        assert context["source"]["next1"] == "Next line"
        assert context["target"]["cur"] == "Test target"
        assert context["target"]["prev1"] == "Prev target"
        assert context["target"]["next1"] == "Next target"
