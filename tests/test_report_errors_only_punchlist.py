from pathlib import Path

from srt_translator.eval.report import render_consolidated_punchlist


def test_consolidated_punchlist_includes_only_errors(tmp_path: Path):
    # Minimal rollup structure with one file and one missing_translation error
    languages = {
        "es": {
            "files": [
                {
                    "target_file": "Module.srt",
                    "source_file": "Module-en.srt",
                    "issues": {
                        "missing_translation": [{"cue": 104, "src": "Text.", "tgt": ""}],
                        # Noise that should NOT render in MD:
                        "timing_fail": [],  # non-blocking list form
                    },
                    "metrics": {"parity_ok": True},
                }
            ]
        }
    }
    md = render_consolidated_punchlist(languages, batch_root=tmp_path, source_lang_name="English")
    assert "Some files need attention" in md
    assert "cue 104" in md
    assert "Everything looks great" not in md
