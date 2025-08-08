"""Configuration resolver for CLI mode - centralizes all environment variable lookups"""

import json
import logging
import os
from typing import Dict, List, Optional
from dataclasses import dataclass

from .translation_config import TranslationConfig


@dataclass
class CLIConfig:
    """Configuration for CLI mode loaded from environment variables"""
    target_languages: Dict[str, str]
    dnt_terms: List[str]
    termbase: Dict[str, Dict[str, str]]
    api_key: str
    output_directory: str
    source_lang: str
    source_dir: str
    
    @classmethod
    def from_environment(cls) -> 'CLIConfig':
        """Load configuration from environment variables (CLI mode only)"""
        # Validate required environment variables
        required_vars = ['OPENAI_API_KEY', 'TARGET_LANGUAGES', 'SOURCE_LANG']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {missing_vars}")
        
        # Load target languages from environment
        target_languages_str = os.getenv('TARGET_LANGUAGES', '{}')
        try:
            target_languages = json.loads(target_languages_str)
        except json.JSONDecodeError:
            raise ValueError(f"Invalid TARGET_LANGUAGES format: {target_languages_str}")
        
        # Load DNT terms from environment
        dnt_terms_str = os.getenv('DNT_TERMS', '[]')
        try:
            dnt_terms = json.loads(dnt_terms_str)
        except json.JSONDecodeError:
            logging.warning(f"Invalid DNT_TERMS format, using empty list: {dnt_terms_str}")
            dnt_terms = []
        
        # Load termbase from environment (if available)
        termbase_str = os.getenv('TERMBASE', '{}')
        try:
            termbase = json.loads(termbase_str)
        except json.JSONDecodeError:
            logging.warning(f"Invalid TERMBASE format, using empty dict: {termbase_str}")
            termbase = {}
        
        return cls(
            target_languages=target_languages,
            dnt_terms=dnt_terms,
            termbase=termbase,
            api_key=os.getenv('OPENAI_API_KEY'),
            output_directory=os.getenv('OUTPUT_DIRECTORY', 'translated_srt_files'),
            source_lang=os.getenv('SOURCE_LANG', 'en'),
            source_dir=os.getenv('SOURCE_DIR', 'original_captions')
        )


class ConfigResolver:
    """Resolves configuration for different modes (CLI vs GUI)"""
    
    @staticmethod
    def get_cli_config() -> CLIConfig:
        """Get configuration for CLI mode from environment variables"""
        return CLIConfig.from_environment()
    
    @staticmethod
    def is_cli_mode() -> bool:
        """Determine if running in CLI mode"""
        return os.getenv('GUI_MODE') != 'true'
    
    @staticmethod
    def validate_cli_config(config: CLIConfig) -> List[str]:
        """Validate CLI configuration and return list of issues"""
        issues = []
        
        if not config.target_languages:
            issues.append("No target languages configured")
        
        if not config.api_key:
            issues.append("No OpenAI API key configured")
        
        if not os.path.exists(config.source_dir):
            issues.append(f"Source directory does not exist: {config.source_dir}")
        
        return issues
    
    @staticmethod
    def get_translation_config_for_cli() -> TranslationConfig:
        """Get TranslationConfig for CLI mode"""
        cli_config = ConfigResolver.get_cli_config()
        
        # Validate configuration
        issues = ConfigResolver.validate_cli_config(cli_config)
        if issues:
            raise ValueError(f"CLI configuration issues: {', '.join(issues)}")
        
        # Convert to TranslationConfig
        return TranslationConfig(
            target_languages=cli_config.target_languages,
            dnt_terms=cli_config.dnt_terms,
            termbase=cli_config.termbase,
            source_lang=cli_config.source_lang,
            output_directory=cli_config.output_directory,
            api_key=cli_config.api_key
        )
    
    @staticmethod
    def get_translation_config_for_gui(settings_manager) -> TranslationConfig:
        """Get TranslationConfig for GUI mode"""
        from .translation_config import build_config_from_gui
        return build_config_from_gui(settings_manager)
    
    @staticmethod
    def get_translation_config(
        settings_manager=None,
        target_languages: Optional[Dict[str, str]] = None,
        dnt_terms: Optional[List[str]] = None,
        termbase: Optional[Dict[str, Dict[str, str]]] = None,
        source_lang: str = 'en',
        output_directory: Optional[str] = None,
        api_key: Optional[str] = None,
        logger: Optional[logging.Logger] = None
    ) -> TranslationConfig:
        """Get TranslationConfig based on available parameters and mode"""
        
        # If explicit parameters are provided, use them
        if target_languages is not None:
            from .translation_config import build_config_from_parameters
            return build_config_from_parameters(
                target_languages=target_languages,
                dnt_terms=dnt_terms,
                termbase=termbase,
                source_lang=source_lang,
                output_directory=output_directory,
                api_key=api_key,
                logger=logger
            )
        
        # Determine mode and get appropriate configuration
        if ConfigResolver.is_cli_mode():
            return ConfigResolver.get_translation_config_for_cli()
        elif settings_manager:
            return ConfigResolver.get_translation_config_for_gui(settings_manager)
        else:
            raise ValueError("Cannot determine configuration source. Provide explicit parameters or ensure proper mode detection.")
