"""Unit tests for LanguageConfig.closest_supported_code.

The method maps an LLM's BCP-47 guess to whatever code the loaded
catalog actually uses, so language_detection.py can delegate
normalization instead of duplicating ad-hoc lookup logic.
"""

from srt_translator.core.config.language_config import LanguageConfig


def _cfg(*codes):
    """Build a minimal LanguageConfig with the given codes registered."""
    return LanguageConfig({"languages": {c: {"name": c.upper()} for c in codes}})


def test_returns_exact_match_unchanged():
    cfg = _cfg("en", "es", "fr")
    assert cfg.closest_supported_code("en") == "en"


def test_returns_canonical_casing_for_case_insensitive_match():
    """Catalog uses zh-Hans (Pascal-style) but the model often returns
    zh-hans or ZH-HANS. The catalog's canonical casing must be returned."""
    cfg = _cfg("zh-Hans", "pt-BR")
    assert cfg.closest_supported_code("zh-hans") == "zh-Hans"
    assert cfg.closest_supported_code("ZH-HANS") == "zh-Hans"
    assert cfg.closest_supported_code("pt-br") == "pt-BR"


def test_uses_alias_normalizer_for_short_codes():
    """The class normalizer maps zh -> zh-Hans, pt -> pt-BR. If the
    model returns the short form and the catalog has the expanded
    form, we resolve to the catalog's expanded form."""
    cfg = _cfg("zh-Hans", "pt-BR")
    assert cfg.closest_supported_code("zh") == "zh-Hans"
    assert cfg.closest_supported_code("pt") == "pt-BR"


def test_falls_back_to_base_when_region_variant_missing():
    """Catalog only has 'en'; model returns 'en-GB'. Should fall back to 'en'."""
    cfg = _cfg("en", "es")
    assert cfg.closest_supported_code("en-GB") == "en"
    assert cfg.closest_supported_code("es-MX") == "es"


def test_returns_none_when_no_path_resolves():
    cfg = _cfg("en", "es", "fr")
    assert cfg.closest_supported_code("xx") is None
    assert cfg.closest_supported_code("klingon") is None


def test_returns_none_for_empty_input():
    cfg = _cfg("en", "es")
    assert cfg.closest_supported_code("") is None
    assert cfg.closest_supported_code(None) is None  # type: ignore[arg-type]


def test_does_not_invent_codes_not_in_catalog():
    """If alias normalization would point to a code the catalog lacks,
    we must NOT return that code — we return the actual catalog match
    or None. zh -> zh-Hans, but if the catalog only has zh-Hant, we
    should match nothing (the bug would be returning 'zh-Hans' that
    isn't in the catalog)."""
    cfg = _cfg("zh-Hant", "ja", "ko")
    # 'zh' alias-normalizes to 'zh-Hans', which is NOT in this catalog.
    # Base fallback then tries 'zh', which is ALSO not in this catalog.
    # Expected: None.
    assert cfg.closest_supported_code("zh") is None
    # 'zh-CN' alias-normalizes to 'zh-Hans' (also not present); base 'zh' also absent.
    assert cfg.closest_supported_code("zh-CN") is None


def test_real_world_catalog_shape_matches_production():
    """Smoke test against a catalog shape resembling the loaded
    languages.json. Detection returning 'en' on this catalog should
    resolve to 'en' (no normalization warning)."""
    cfg = LanguageConfig(
        {
            "languages": {
                "en": {"name": "English"},
                "es": {"name": "Spanish"},
                "zh-Hans": {"name": "Chinese (Simplified)"},
                "pt-BR": {"name": "Portuguese (Brazil)"},
                "ja": {"name": "Japanese"},
            }
        }
    )
    assert cfg.closest_supported_code("en") == "en"
    assert cfg.closest_supported_code("ja") == "ja"
    assert cfg.closest_supported_code("zh-Hans") == "zh-Hans"
    # Model variations:
    assert cfg.closest_supported_code("EN") == "en"
    assert cfg.closest_supported_code("zh-cn") == "zh-Hans"
