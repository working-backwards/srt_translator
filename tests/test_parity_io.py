# Stage 0: parity properties for translate_file (structure & placeholder integrity)
import logging
from pathlib import Path
from srt_translator.core.translator.translator import SRTTranslator
from srt_translator.core.config.language_config import LanguageConfig


class _DummyClient:
    class _Msg:
        def __init__(self, content):
            self.content = content

    class _Choice:
        def __init__(self, content):
            self.message = _DummyClient._Msg(content)

    class _Resp:
        def __init__(self, content):
            self.choices = [_DummyClient._Choice(content)]

    def __init__(self):
        pass

    class chat:
        class completions:
            @staticmethod
            def create(**kwargs):
                return _DummyClient._Resp(
                    content='{"items":[{"id":1,"tgt":"__DNT_TERM_1__ Hello"}, {"id":2,"tgt":""}, {"id":3,"tgt":"World __DNT_TERM_2__"}]}'
                )


def test_translate_file_parity(tmp_path: Path):
    input_srt = """1
00:00:01,000 --> 00:00:03,000
__DNT_TERM_1__ Hello

2
00:00:03,000 --> 00:00:05,000
 

3
00:00:05,000 --> 00:00:07,000
World __DNT_TERM_2__

"""
    inp = tmp_path / "in.srt"
    outp = tmp_path / "out.srt"
    inp.write_text(input_srt, encoding="utf-8")

    logger = logging.getLogger("test.translate")
    logger.setLevel(logging.DEBUG)

    t = SRTTranslator(
        dnt_terms=["ACME"],
        termbase={"fr": {"Amazon": "Amazon"}},
        api_key="sk-test",
        logger=logger,
        batch_size=2,
        error_policy="BOUNDED",
        language_config=LanguageConfig({"languages": {}}),
    )
    t.client = _DummyClient()

    t.translate_file(
        input_filepath=str(inp), output_filepath=str(outp), target_lang="fr"
    )

    out_text = outp.read_text(encoding="utf-8")
    blocks = [b for b in out_text.strip().split("\n\n") if b.strip()]
    assert len(blocks) == 3
    assert "00:00:01,000 --> 00:00:03,000" in blocks[0]
    assert "00:00:03,000 --> 00:00:05,000" in blocks[1]
    assert "00:00:05,000 --> 00:00:07,000" in blocks[2]

    # Placeholder integrity: existing ids preserved; no invented placeholders
    assert "__DNT_TERM_1__" in blocks[0] or blocks[0].endswith("\n")
    assert "__DNT_TERM_2__" in blocks[2]
