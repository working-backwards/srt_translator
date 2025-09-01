import json
import logging
from pathlib import Path

import pytest

from srt_translator.core.translator.translator import SRTTranslator
from srt_translator.core.config.language_config import (
    LanguageConfig,
)  # required (fail-fast enabled)

# --- Utilities ---


def _read_srt_blocks(text: str):
    """
    Naive SRT block reader for tests:
    Returns list of dicts: {"idx": int, "ts": "00:.. --> 00:..", "text": "...\n..."}
    """
    blocks = []
    for raw_block in text.strip().split("\n\n"):
        lines = [l for l in raw_block.splitlines()]
        if len(lines) < 2:
            continue
        try:
            idx = int(lines[0].strip())
        except ValueError:
            continue
        ts = lines[1].strip()
        txt = "\n".join(lines[2:]) if len(lines) > 2 else ""
        blocks.append({"idx": idx, "ts": ts, "text": txt})
    return blocks


class _DummyClient:
    """
    Minimal stand-in for the OpenAI client. It parses the user prompt to reconstruct
    the INPUT ITEMS section and returns a JSON payload that echoes those items as targets.
    This keeps tests deterministic and model-agnostic.
    """

    class _Msg:
        def __init__(self, content):
            self.content = content

    class _Choice:
        def __init__(self, content):
            self.message = _DummyClient._Msg(content)

    class _Resp:
        def __init__(self, content):
            self.choices = [_DummyClient._Choice(content)]

    class chat:
        class completions:
            @staticmethod
            def create(**kwargs):
                # Parse INPUT ITEMS from user message to recover items and ids
                messages = kwargs.get("messages", [])
                user = messages[1]["content"] if len(messages) > 1 else ""
                # Find the "INPUT ITEMS:" section; then parse lines like "n) text"
                items = []
                if "INPUT ITEMS:" in user:
                    after = user.split("INPUT ITEMS:")[-1].strip()
                    for line in after.splitlines():
                        line = line.strip()
                        if not line or not line[0].isdigit():
                            continue
                        # Expect "n) text..."
                        try:
                            n_str, rest = line.split(")", 1)
                            n = int(n_str)
                            text = rest.strip()
                            # For empty text, return the original text (preserves empty blocks)
                            items.append({"id": n, "tgt": text})
                        except Exception:
                            continue
                # Fallback: return empty list if parsing fails
                payload = {"items": items}
                return _DummyClient._Resp(content=json.dumps(payload))


# Global defaults for goldens
GOLDEN_INPUT_DIR = Path("tests/fixtures/golden/inputs")
GLOBAL_DNT = ["API", "CEO"]
TERMS_ES = {"Hello": "Hola", "test": "prueba"}  # only used where relevant

# Define the test matrix: (filename, languages, overrides)
CASES = [
    ("golden_dnt_acronyms.srt", ["es", "zh-Hans", "fr"], {"dnt_terms": GLOBAL_DNT}),
    ("golden_numbers_currency.srt", ["es", "zh-Hans", "fr"], {"dnt_terms": []}),
    (
        "golden_empty_block.srt",
        ["es", "zh-Hans", "fr"],
        {"dnt_terms": [], "error_policy": "BOUNDED"},
    ),
    ("golden_cps_warn_only.srt", ["es", "zh-Hans", "fr"], {"dnt_terms": []}),
    (
        "golden_multi_batch.srt",
        ["es", "zh-Hans", "fr"],
        {"dnt_terms": [], "batch_size": 4},
    ),
    ("golden_placeholder_apostrophe.srt", ["fr"], {"dnt_terms": ["API"]}),
]


@pytest.mark.parametrize("filename,languages,overrides", CASES)
def test_golden_structure_and_invariants(
    tmp_path: Path, caplog, filename, languages, overrides
):
    # Read input and basic structure
    input_path = GOLDEN_INPUT_DIR / filename
    src_text = input_path.read_text(encoding="utf-8")
    src_blocks = _read_srt_blocks(src_text)
    assert src_blocks, f"Invalid SRT fixture: {filename}"

    # Common config
    language_config = LanguageConfig(
        {"languages": {}}
    )  # use your real config loader in app; tests use minimal stub
    termbase = {"es": TERMS_ES}  # non-ES languages may have empty mappings

    for target_lang in languages:
        # Translator with overrides
        t = SRTTranslator(
            dnt_terms=overrides.get("dnt_terms", []),
            termbase=termbase,
            api_key="sk-test",
            logger=logging.getLogger(f"test.golden.{filename}.{target_lang}"),
            batch_size=overrides.get("batch_size", 8),
            error_policy=overrides.get("error_policy", "STRICT"),
            language_config=language_config,
        )
        # Inject dummy client
        t.client = _DummyClient()

        # Translate to temp output
        out_path = tmp_path / f"{filename}.{target_lang}.out.srt"
        t.translate_file(
            input_filepath=str(input_path),
            output_filepath=str(out_path),
            target_lang=target_lang,
        )

        # Read output and compare structure
        out_text = out_path.read_text(encoding="utf-8")
        out_blocks = _read_srt_blocks(out_text)
        assert len(out_blocks) == len(src_blocks)
        for sb, ob in zip(src_blocks, out_blocks):
            assert sb["idx"] == ob["idx"]
            assert sb["ts"] == ob["ts"]

        # Placeholder integrity: no internal placeholder artifacts in final SRT
        assert "__DNT_TERM_" not in out_text

        # DNT acronyms preserved literally in DNT test
        if filename == "golden_dnt_acronyms.srt":
            assert "API" in out_text
            assert "CEO" in out_text

        # CPS: warn-only policy — text must remain unchanged in the CPS case
        if filename == "golden_cps_warn_only.srt":
            # Single-cue file; text equality check
            assert src_blocks[0]["text"] == out_blocks[0]["text"]

        # Multi-batch: just structural assertions already done above
        # Apostrophe-after-placeholder: covered structurally by integrity + literal 'API's'
        if filename == "golden_placeholder_apostrophe.srt":
            assert "API's" in out_text

    # --- Fixer golden guard: Fixer must be a no-op on goldens (dry-run) ---
    from srt_translator.core.translator.fixer import SRTFixer

    # Create a temporary batch directory structure for the fixer test
    batch_dir = tmp_path / "golden_batch_test"
    batch_dir.mkdir(exist_ok=True)

    # Create ai_config.json with the DNT terms used in this test
    ai_config = {
        "version": "1.0.0",
        "dnt_terms": overrides.get("dnt_terms", []),
    }
    (batch_dir / "ai_config.json").write_text(
        json.dumps(ai_config, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Copy the translated outputs to the batch structure (simulating what main.py does)
    for target_lang in languages:
        lang_dir = batch_dir / target_lang
        lang_dir.mkdir(exist_ok=True)
        out_path = tmp_path / f"{filename}.{target_lang}.out.srt"
        if out_path.exists():
            (lang_dir / f"{filename}.{target_lang}.srt").write_text(
                out_path.read_text(encoding="utf-8"), encoding="utf-8"
            )

    # Run fixer in dry-run mode
    fixer = SRTFixer(
        log_file=str(batch_dir / "fixer_golden.log"), translations_dir=str(batch_dir)
    )
    summary = fixer.scan_and_fix_placeholders(
        batch_dir=batch_dir, dnt_terms=ai_config["dnt_terms"], dry_run=True
    )

    # No backups on dry-run
    assert not list(batch_dir.rglob("*.srt.bak"))

    # No placeholder tokens should remain in any translated SRT
    for p in batch_dir.rglob("*.srt"):
        text = p.read_text(encoding="utf-8", errors="ignore")
        assert "__DNT_TERM_" not in text, f"Placeholder token leaked in {p}"

    # If summary includes counters, assert zero changes
    changes = sum(
        summary.get(k, 0)
        for k in ("tokens_replaced", "tokens_removed", "files_changed")
    )
    assert changes == 0
    # --- end Fixer golden guard ---
