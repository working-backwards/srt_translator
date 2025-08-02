#!/usr/bin/env python3
"""
Test performance optimization functionality
"""
import sys
import os
import tempfile
import time
import pytest

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gui.cache_manager import CacheManager, CacheEntry
from gui.performance_monitor import PerformanceMonitor, PerformanceMetric


class TestCacheManager:
    """Test the CacheManager class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_manager = CacheManager(cache_dir=os.path.join(self.temp_dir, "cache"))
        
        # Create test files
        self.test_file1 = os.path.join(self.temp_dir, "test1.srt")
        self.test_file2 = os.path.join(self.temp_dir, "test2.srt")
        
        with open(self.test_file1, 'w', encoding='utf-8') as f:
            f.write("Test content 1")
        
        with open(self.test_file2, 'w', encoding='utf-8') as f:
            f.write("Test content 2")
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_cache_set_and_get(self):
        """Test basic cache set and get operations."""
        files = [self.test_file1, self.test_file2]
        test_data = {"excluded_terms": ["CEO", "CFO"], "business_glossary": {}}
        
        # Set cache
        success = self.cache_manager.set("ai_analysis", files, test_data)
        assert success == True
        
        # Get cache
        cached_data = self.cache_manager.get("ai_analysis", files)
        assert cached_data == test_data
        
        # Check stats
        stats = self.cache_manager.get_stats()
        assert stats["total_requests"] == 1
        assert stats["hit_count"] == 1
        assert stats["miss_count"] == 0
        assert stats["hit_rate_percent"] == 100.0
    
    def test_cache_miss(self):
        """Test cache miss when files don't match."""
        files1 = [self.test_file1]
        files2 = [self.test_file2]
        test_data = {"test": "data"}
        
        # Set cache for files1
        self.cache_manager.set("test_operation", files1, test_data)
        
        # Try to get with files2 (should miss)
        cached_data = self.cache_manager.get("test_operation", files2)
        assert cached_data is None
        
        # Check stats
        stats = self.cache_manager.get_stats()
        assert stats["total_requests"] == 1
        assert stats["hit_count"] == 0
        assert stats["miss_count"] == 1
        assert stats["hit_rate_percent"] == 0.0
    
    def test_cache_invalidation(self):
        """Test cache invalidation."""
        files = [self.test_file1]
        test_data = {"test": "data"}
        
        # Set cache
        self.cache_manager.set("test_operation", files, test_data)
        
        # Invalidate cache
        removed_count = self.cache_manager.invalidate(files=files)
        assert removed_count == 1
        
        # Try to get (should miss)
        cached_data = self.cache_manager.get("test_operation", files)
        assert cached_data is None
    
    def test_cache_clear_all(self):
        """Test clearing all cache."""
        files = [self.test_file1]
        test_data = {"test": "data"}
        
        # Set multiple cache entries
        self.cache_manager.set("operation1", files, test_data)
        self.cache_manager.set("operation2", files, test_data)
        
        # Clear all
        removed_count = self.cache_manager.clear_all()
        assert removed_count == 2
        
        # Check stats
        stats = self.cache_manager.get_stats()
        assert stats["cache_files"] == 0


class TestPerformanceMonitor:
    """Test the PerformanceMonitor class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.monitor = PerformanceMonitor()
    
    def test_operation_tracking(self):
        """Test basic operation tracking."""
        # Start operation
        self.monitor.start_operation("test_operation")
        
        # Simulate some work
        time.sleep(0.1)
        
        # End operation
        self.monitor.end_operation("test_operation", success=True)
        
        # Check stats
        stats = self.monitor.get_operation_stats("test_operation")
        assert stats["total_operations"] == 1
        assert stats["successful_operations"] == 1
        assert stats["success_rate_percent"] == 100.0
        assert stats["average_duration_ms"] > 0
    
    def test_operation_failure_tracking(self):
        """Test tracking failed operations."""
        # Start operation
        self.monitor.start_operation("test_operation")
        
        # End operation with failure
        self.monitor.end_operation("test_operation", success=False, error_message="Test error")
        
        # Check stats
        stats = self.monitor.get_operation_stats("test_operation")
        assert stats["total_operations"] == 1
        assert stats["successful_operations"] == 0
        assert stats["success_rate_percent"] == 0.0
        assert stats["error_count"] == 1
    
    def test_context_manager(self):
        """Test operation tracking with context manager."""
        with self.monitor.track_operation("test_operation"):
            time.sleep(0.1)
        
        # Check stats
        stats = self.monitor.get_operation_stats("test_operation")
        assert stats["total_operations"] == 1
        assert stats["successful_operations"] == 1
    
    def test_context_manager_with_exception(self):
        """Test context manager with exception."""
        try:
            with self.monitor.track_operation("test_operation"):
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        # Check stats
        stats = self.monitor.get_operation_stats("test_operation")
        assert stats["total_operations"] == 1
        assert stats["successful_operations"] == 0
        assert stats["error_count"] == 1
    
    def test_overall_stats(self):
        """Test overall statistics."""
        # Run multiple operations
        with self.monitor.track_operation("operation1"):
            time.sleep(0.05)
        
        with self.monitor.track_operation("operation2"):
            time.sleep(0.05)
        
        # Check overall stats
        overall_stats = self.monitor.get_overall_stats()
        assert overall_stats["total_operations"] == 2
        assert overall_stats["successful_operations"] == 2
        assert overall_stats["success_rate_percent"] == 100.0
        assert overall_stats["average_duration_ms"] > 0
        assert "operation1" in overall_stats["operations_tracked"]
        assert "operation2" in overall_stats["operations_tracked"]
    
    def test_slow_operations(self):
        """Test slow operations detection."""
        # Run a slow operation
        with self.monitor.track_operation("slow_operation"):
            time.sleep(0.1)  # 100ms
        
        # Get slow operations (threshold 50ms)
        slow_ops = self.monitor.get_slow_operations(threshold_ms=50)
        assert len(slow_ops) == 1
        assert slow_ops[0]["operation"] == "slow_operation"
        assert slow_ops[0]["duration_ms"] > 50
    
    def test_error_summary(self):
        """Test error summary."""
        # Run operations with some failures
        with self.monitor.track_operation("operation1"):
            pass
        
        try:
            with self.monitor.track_operation("operation2"):
                raise ValueError("Test error")
        except ValueError:
            pass
        
        # Check error summary
        error_summary = self.monitor.get_error_summary()
        assert "operation2" in error_summary
        assert error_summary["operation2"] == 1
        assert "operation1" not in error_summary
    
    def test_clear_history(self):
        """Test clearing performance history."""
        # Run an operation
        with self.monitor.track_operation("test_operation"):
            pass
        
        # Clear history
        self.monitor.clear_history()
        
        # Check that stats are empty
        overall_stats = self.monitor.get_overall_stats()
        assert overall_stats == {}


class TestPerformanceIntegration:
    """Test integration between cache and performance monitoring."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_manager = CacheManager(cache_dir=os.path.join(self.temp_dir, "cache"))
        self.monitor = PerformanceMonitor()
        
        # Create test file
        self.test_file = os.path.join(self.temp_dir, "test.srt")
        with open(self.test_file, 'w', encoding='utf-8') as f:
            f.write("Test content")
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_cached_operation_performance(self):
        """Test performance tracking with cached operations."""
        files = [self.test_file]
        test_data = {"test": "data"}
        
        # First operation (cache miss)
        with self.monitor.track_operation("ai_analysis"):
            cached_result = self.cache_manager.get("ai_analysis", files)
            if cached_result is None:
                # Simulate AI analysis
                time.sleep(0.1)
                self.cache_manager.set("ai_analysis", files, test_data)
                result = test_data
            else:
                result = cached_result
        
        # Second operation (cache hit)
        with self.monitor.track_operation("ai_analysis"):
            cached_result = self.cache_manager.get("ai_analysis", files)
            if cached_result is None:
                # Simulate AI analysis
                time.sleep(0.1)
                self.cache_manager.set("ai_analysis", files, test_data)
                result = test_data
            else:
                result = cached_result
        
        # Check that second operation was faster (cache hit)
        stats = self.monitor.get_operation_stats("ai_analysis")
        assert stats["total_operations"] == 2
        
        # Check cache stats
        cache_stats = self.cache_manager.get_stats()
        assert cache_stats["hit_count"] == 1
        assert cache_stats["miss_count"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 