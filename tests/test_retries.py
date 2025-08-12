"""
Tests for the exponential backoff retry functionality.

This module tests the retry logic, decorators, and various retry scenarios.
"""

import logging
import pytest
import time
from unittest.mock import Mock, patch
from srt_translator.core.utils.retries import (
    with_backoff,
    retry_on_network_error,
    retry_on_openai_error,
)


class TestWithBackoff:
    """Test the core with_backoff function."""

    def test_successful_execution(self):
        """Test that successful execution returns the result immediately."""
        mock_func = Mock(return_value="success")
        result = with_backoff(mock_func, retries=3)
        
        assert result == "success"
        mock_func.assert_called_once()

    def test_retry_on_failure_then_success(self):
        """Test that retries work and eventually succeed."""
        mock_func = Mock(side_effect=[ValueError("fail"), ValueError("fail"), "success"])
        
        start_time = time.time()
        result = with_backoff(mock_func, retries=3, base_delay=0.1, max_delay=0.5)
        end_time = time.time()
        
        assert result == "success"
        assert mock_func.call_count == 3
        # Should have taken at least some time due to delays
        assert end_time - start_time > 0.1

    def test_exhaust_retries_and_fail(self):
        """Test that function fails after exhausting all retries."""
        mock_func = Mock(side_effect=ValueError("persistent failure"))
        
        with pytest.raises(ValueError, match="persistent failure"):
            with_backoff(mock_func, retries=2, base_delay=0.01)
        
        assert mock_func.call_count == 3  # Initial + 2 retries

    def test_custom_exceptions(self):
        """Test that only specified exceptions trigger retries."""
        mock_func = Mock(side_effect=[ValueError("value error"), TypeError("type error")])
        
        # Should retry on ValueError but not TypeError
        with pytest.raises(TypeError, match="type error"):
            with_backoff(mock_func, retries=3, exceptions=(ValueError,))
        
        assert mock_func.call_count == 2  # Initial + 1 retry

    def test_exponential_backoff_timing(self):
        """Test that delays increase exponentially."""
        mock_func = Mock(side_effect=[ValueError("fail")] * 4)
        
        start_time = time.time()
        with pytest.raises(ValueError):
            with_backoff(mock_func, retries=3, base_delay=0.1, max_delay=1.0)
        end_time = time.time()
        
        # Should have delays: 0.1, 0.2, 0.4 (exponential)
        # Total time should be at least the sum of delays
        expected_min_time = 0.1 + 0.2 + 0.4
        assert end_time - start_time >= expected_min_time

    def test_max_delay_cap(self):
        """Test that delays are capped at max_delay."""
        mock_func = Mock(side_effect=[ValueError("fail")] * 6)
        
        start_time = time.time()
        with pytest.raises(ValueError):
            with_backoff(mock_func, retries=5, base_delay=0.1, max_delay=0.2)
        end_time = time.time()
        
        # Delays should be: 0.1, 0.2, 0.2, 0.2, 0.2 (capped)
        expected_min_time = 0.1 + 0.2 + 0.2 + 0.2 + 0.2
        assert end_time - start_time >= expected_min_time

    def test_logging_disabled(self):
        """Test that logging can be disabled."""
        mock_func = Mock(side_effect=[ValueError("fail"), "success"])
        
        with patch('srt_translator.core.utils.retries.logger') as mock_logger:
            result = with_backoff(mock_func, retries=2, base_delay=0.01, log_retries=False)
            
            assert result == "success"
            # No logging should occur
            mock_logger.warning.assert_not_called()
            mock_logger.error.assert_not_called()


class TestRetryOnNetworkError:
    """Test the retry_on_network_error decorator."""

    def test_network_error_retry_then_success(self):
        """Test that network errors trigger retries."""
        mock_func = Mock(side_effect=[ConnectionError("network down"), "success"])
        
        decorated_func = retry_on_network_error(retries=2, base_delay=0.01)(mock_func)
        result = decorated_func()
        
        assert result == "success"
        assert mock_func.call_count == 2

    def test_network_error_exhaust_retries(self):
        """Test that network errors exhaust retries."""
        mock_func = Mock(side_effect=ConnectionError("persistent network issue"))
        
        decorated_func = retry_on_network_error(retries=2, base_delay=0.01)(mock_func)
        
        with pytest.raises(ConnectionError, match="persistent network issue"):
            decorated_func()
        
        assert mock_func.call_count == 3

    def test_non_network_error_no_retry(self):
        """Test that non-network errors don't trigger retries."""
        mock_func = Mock(side_effect=ValueError("not a network error"))
        
        decorated_func = retry_on_network_error(retries=3, base_delay=0.01)(mock_func)
        
        with pytest.raises(ValueError, match="not a network error"):
            decorated_func()
        
        assert mock_func.call_count == 1  # No retries

    def test_decorator_preserves_function_metadata(self):
        """Test that decorator preserves function metadata."""
        @retry_on_network_error()
        def test_function():
            """Test function docstring."""
            pass
        
        assert test_function.__name__ == "test_function"
        assert test_function.__doc__ == "Test function docstring."


class TestRetryOnOpenAIError:
    """Test the retry_on_openai_error decorator."""

    def test_openai_error_retry_then_success(self):
        """Test that OpenAI errors trigger retries."""
        mock_func = Mock(side_effect=[ConnectionError("openai down"), "success"])
        
        decorated_func = retry_on_openai_error(retries=2, base_delay=0.01)(mock_func)
        result = decorated_func()
        
        assert result == "success"
        assert mock_func.call_count == 2

    def test_openai_error_exhaust_retries(self):
        """Test that OpenAI errors exhaust retries."""
        mock_func = Mock(side_effect=TimeoutError("openai timeout"))
        
        decorated_func = retry_on_openai_error(retries=2, base_delay=0.01)(mock_func)
        
        with pytest.raises(TimeoutError, match="openai timeout"):
            decorated_func()
        
        assert mock_func.call_count == 3

    def test_non_openai_error_no_retry(self):
        """Test that non-OpenAI errors don't trigger retries."""
        mock_func = Mock(side_effect=ValueError("not an openai error"))
        
        decorated_func = retry_on_openai_error(retries=3, base_delay=0.01)(mock_func)
        
        with pytest.raises(ValueError, match="not an openai error"):
            decorated_func()
        
        assert mock_func.call_count == 1  # No retries

    def test_openai_specific_retryable_exceptions(self):
        """Test that OpenAI-specific exceptions are retryable."""
        # Test all the exceptions that should trigger retries
        for exception_class in [ConnectionError, TimeoutError, OSError]:
            mock_func = Mock(side_effect=[exception_class("test"), "success"])
            
            decorated_func = retry_on_openai_error(retries=2, base_delay=0.01)(mock_func)
            result = decorated_func()
            
            assert result == "success"
            assert mock_func.call_count == 2


class TestRetryIntegration:
    """Integration tests for retry functionality."""

    def test_retry_with_real_function(self):
        """Test retry with a real function that has side effects."""
        call_count = 0
        
        def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError(f"Attempt {call_count} failed")
            return "success"
        
        result = with_backoff(failing_function, retries=3, base_delay=0.01)
        
        assert result == "success"
        assert call_count == 3

    def test_retry_decorator_with_arguments(self):
        """Test that retry decorators work with functions that take arguments."""
        mock_func = Mock(side_effect=[ConnectionError("fail"), "success"])
        
        @retry_on_network_error(retries=2, base_delay=0.01)
        def test_function(arg1, arg2, kwarg1=None):
            return mock_func(arg1, arg2, kwarg1=kwarg1)
        
        result = test_function("arg1", "arg2", kwarg1="kwarg1")
        
        assert result == "success"
        mock_func.assert_called_with("arg1", "arg2", kwarg1="kwarg1")
        assert mock_func.call_count == 2

    def test_retry_logging_integration(self):
        """Test that retry logging integrates properly with the logging system."""
        mock_func = Mock(side_effect=[ConnectionError("network error"), "success"])
        
        with patch('srt_translator.core.utils.retries.logger') as mock_logger:
            result = with_backoff(mock_func, retries=2, base_delay=0.01)
            
            assert result == "success"
            # Should log the retry attempt
            mock_logger.warning.assert_called_once()
            assert "Attempt 1 failed" in mock_logger.warning.call_args[0][0]


if __name__ == "__main__":
    pytest.main([__file__])
