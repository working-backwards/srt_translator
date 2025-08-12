"""
Tests for the configuration policy enforcement.

This module tests that the configuration system follows the established policy:
- No environment mutation
- API key precedence: OS env > .env > error
- Other settings: .env only (OS env ignored)
"""

import os
import pytest
from unittest.mock import patch, Mock
from srt_translator.core.config.collect import collect_cli_config


class TestNoEnvironmentMutation:
    """Test that no environment mutation occurs during configuration collection."""

    def test_environment_unchanged_after_config_collection(self):
        """Test that os.environ is not modified during config collection."""
        # Capture initial environment state
        initial_env = dict(os.environ)
        
        # Mock the dotenv loading to avoid file system dependencies
        with patch('srt_translator.core.config.collect.find_dotenv') as mock_find_dotenv, \
             patch('srt_translator.core.config.collect.dotenv_values') as mock_dotenv_values:
            
            mock_find_dotenv.return_value = '.env'
            mock_dotenv_values.return_value = {
                'OPENAI_API_KEY': 'test_key_from_env_file',
                'TARGET_LANGUAGES': '{"Spanish": "es"}',
                'OPENAI_MODEL': 'gpt-4o-mini',
                'BATCH_SIZE': '5',
                'AGGRESSIVENESS': '0.75',
                'LOG_MODE': 'Standard',
                'OUTPUT_DIRECTORY': 'translated_srt_files',
                'TERMBASE_PATH': 'termbase.json'
            }
            
            # Set OS environment variable for API key
            os.environ['OPENAI_API_KEY'] = 'test_key_from_os'
            
            try:
                # Collect configuration
                config = collect_cli_config()
                
                # Verify environment is unchanged
                assert dict(os.environ) == initial_env
                
                # Verify API key precedence (OS env should win)
                assert config['api_key'] == 'test_key_from_os'
                assert config['api_key_source'] == 'env'
                
            finally:
                # Clean up
                if 'OPENAI_API_KEY' in os.environ:
                    del os.environ['OPENAI_API_KEY']

    def test_no_load_dotenv_calls(self):
        """Test that load_dotenv() is never called to populate os.environ."""
        with patch('srt_translator.core.config.collect.load_dotenv') as mock_load_dotenv, \
             patch('srt_translator.core.config.collect.find_dotenv') as mock_find_dotenv, \
             patch('srt_translator.core.config.collect.dotenv_values') as mock_dotenv_values:
            
            mock_find_dotenv.return_value = '.env'
            mock_dotenv_values.return_value = {'OPENAI_API_KEY': 'test_key'}
            
            collect_cli_config()
            
            # load_dotenv should never be called
            mock_load_dotenv.assert_not_called()

    def test_no_environment_setdefault_calls(self):
        """Test that os.environ.setdefault() is never called."""
        with patch('os.environ.setdefault') as mock_setdefault, \
             patch('srt_translator.core.config.collect.find_dotenv') as mock_find_dotenv, \
             patch('srt_translator.core.config.collect.dotenv_values') as mock_dotenv_values:
            
            mock_find_dotenv.return_value = '.env'
            mock_dotenv_values.return_value = {'OPENAI_API_KEY': 'test_key'}
            
            collect_cli_config()
            
            # setdefault should never be called
            mock_setdefault.assert_not_called()


class TestApiKeyPrecedence:
    """Test API key precedence rules."""

    def test_os_env_overrides_dotenv_for_api_key(self):
        """Test that OS environment API key overrides .env file."""
        with patch('srt_translator.core.config.collect.find_dotenv') as mock_find_dotenv, \
             patch('srt_translator.core.config.collect.dotenv_values') as mock_dotenv_values:
            
            mock_find_dotenv.return_value = '.env'
            mock_dotenv_values.return_value = {'OPENAI_API_KEY': 'key_from_dotenv'}
            
            # Set OS environment variable
            os.environ['OPENAI_API_KEY'] = 'key_from_os'
            
            try:
                config = collect_cli_config()
                
                # OS env should win
                assert config['api_key'] == 'key_from_os'
                assert config['api_key_source'] == 'env'
                
            finally:
                del os.environ['OPENAI_API_KEY']

    def test_dotenv_api_key_when_no_os_env(self):
        """Test that .env API key is used when no OS environment variable."""
        with patch('srt_translator.core.config.collect.find_dotenv') as mock_find_dotenv, \
             patch('srt_translator.core.config.collect.dotenv_values') as mock_dotenv_values:
            
            mock_find_dotenv.return_value = '.env'
            mock_dotenv_values.return_value = {'OPENAI_API_KEY': 'key_from_dotenv'}
            
            # Ensure no OS environment variable
            if 'OPENAI_API_KEY' in os.environ:
                del os.environ['OPENAI_API_KEY']
            
            config = collect_cli_config()
            
            # .env should be used
            assert config['api_key'] == 'key_from_dotenv'
            assert config['api_key_source'] == '.env'

    def test_legacy_open_ai_key_alias(self):
        """Test that legacy OPEN_AI_KEY alias is supported."""
        with patch('srt_translator.core.config.collect.find_dotenv') as mock_find_dotenv, \
             patch('srt_translator.core.config.collect.dotenv_values') as mock_dotenv_values:
            
            mock_find_dotenv.return_value = '.env'
            mock_dotenv_values.return_value = {'OPEN_AI_KEY': 'legacy_key_from_dotenv'}
            
            # Ensure no OS environment variables
            for key in ['OPENAI_API_KEY', 'OPEN_AI_KEY']:
                if key in os.environ:
                    del os.environ[key]
            
            config = collect_cli_config()
            
            # Legacy alias should work
            assert config['api_key'] == 'legacy_key_from_dotenv'
            assert config['api_key_source'] == '.env'

    def test_error_when_no_api_key(self):
        """Test that error is raised when no API key is available."""
        with patch('srt_translator.core.config.collect.find_dotenv') as mock_find_dotenv, \
             patch('srt_translator.core.config.collect.dotenv_values') as mock_dotenv_values:
            
            mock_find_dotenv.return_value = '.env'
            mock_dotenv_values.return_value = {}  # No API key
            
            # Ensure no OS environment variables
            for key in ['OPENAI_API_KEY', 'OPEN_AI_KEY']:
                if key in os.environ:
                    del os.environ[key]
            
            with pytest.raises(ValueError, match="OPENAI_API_KEY is required"):
                collect_cli_config()


class TestOtherSettingsIgnoredFromOS:
    """Test that other settings are ignored from OS environment."""

    def test_os_env_ignored_for_non_api_settings(self):
        """Test that OS environment variables are ignored for non-API key settings."""
        with patch('srt_translator.core.config.collect.find_dotenv') as mock_find_dotenv, \
             patch('srt_translator.core.config.collect.dotenv_values') as mock_dotenv_values:
            
            mock_find_dotenv.return_value = '.env'
            mock_dotenv_values.return_value = {
                'OPENAI_API_KEY': 'test_key',
                'OPENAI_MODEL': 'gpt-4o-mini',
                'BATCH_SIZE': '5'
            }
            
            # Set conflicting OS environment variables
            os.environ['OPENAI_API_KEY'] = 'test_key'  # This should work
            os.environ['OPENAI_MODEL'] = 'gpt-3.5-turbo'  # This should be ignored
            os.environ['BATCH_SIZE'] = '10'  # This should be ignored
            
            try:
                config = collect_cli_config()
                
                # API key should come from OS env
                assert config['api_key'] == 'test_key'
                assert config['api_key_source'] == 'env'
                
                # Other settings should come from .env (OS env ignored)
                assert config['openai_model'] == 'gpt-4o-mini'
                assert config['batch_size'] == '5'
                
            finally:
                # Clean up
                for key in ['OPENAI_API_KEY', 'OPENAI_MODEL', 'BATCH_SIZE']:
                    if key in os.environ:
                        del os.environ[key]


class TestConfigurationCompleteness:
    """Test that configuration is complete and properly structured."""

    def test_all_required_config_keys_present(self):
        """Test that all required configuration keys are present."""
        with patch('srt_translator.core.config.collect.find_dotenv') as mock_find_dotenv, \
             patch('srt_translator.core.config.collect.dotenv_values') as mock_dotenv_values:
            
            mock_find_dotenv.return_value = '.env'
            mock_dotenv_values.return_value = {'OPENAI_API_KEY': 'test_key'}
            
            config = collect_cli_config()
            
            # Check that all expected keys are present
            expected_keys = [
                'target_languages', 'dnt_terms', 'openai_model', 'batch_size',
                'aggressiveness', 'log_mode', 'output_directory', 'termbase_path',
                'api_key', 'api_key_source'
            ]
            
            for key in expected_keys:
                assert key in config, f"Missing configuration key: {key}"

    def test_default_values_used_when_not_in_dotenv(self):
        """Test that sensible defaults are used when values are not in .env."""
        with patch('srt_translator.core.config.collect.find_dotenv') as mock_find_dotenv, \
             patch('srt_translator.core.config.collect.dotenv_values') as mock_dotenv_values:
            
            mock_find_dotenv.return_value = '.env'
            mock_dotenv_values.return_value = {'OPENAI_API_KEY': 'test_key'}
            
            config = collect_cli_config()
            
            # Check default values
            assert config['openai_model'] == 'gpt-4o-mini'
            assert config['batch_size'] == '5'
            assert config['aggressiveness'] == '0.75'
            assert config['log_mode'] == 'Standard'
            assert config['output_directory'] == 'translated_srt_files'
            assert config['termbase_path'] == 'termbase.json'


if __name__ == "__main__":
    pytest.main([__file__])
