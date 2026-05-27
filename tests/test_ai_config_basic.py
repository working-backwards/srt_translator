from srt_translator.core.config.language_config import LanguageConfig
from srt_translator.core.constants import DEFAULT_GENERATION_MODEL
from srt_translator.gui.settings_manager import SettingsManager


def test_settings_manager_round_trip_and_defaults():
    """Basic smoke test for SettingsManager and config defaults."""
    language_config = LanguageConfig({"languages": {}})
    settings_manager = SettingsManager(language_config)

    # Test saving and loading AI config
    test_dnt_terms = ["API", "CEO", "CFO", "Amazon"]
    test_termbase = {
        "es": {
            "operating plan": "plan operativo",
            "business review": "revisión de negocio",
        },
        "fr": {
            "operating plan": "plan opérationnel",
            "business review": "revue d'affaires",
        },
    }

    settings_manager.save_ai_config(test_dnt_terms, test_termbase)
    loaded_terms, loaded_termbase, _ = settings_manager.load_ai_config()

    assert loaded_terms == test_dnt_terms
    assert loaded_termbase == test_termbase

    # Test default generation model name uses constant
    settings_manager.settings.remove("generation_model_name")
    assert settings_manager.load_generation_model_name() == DEFAULT_GENERATION_MODEL
