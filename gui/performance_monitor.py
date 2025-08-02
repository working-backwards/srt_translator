#!/usr/bin/env python3
"""
Performance Monitor for AI Configuration

Tracks performance metrics for:
- AI analysis operations
- File processing times
- Cache performance
- Memory usage
- User experience metrics
"""

import time
import psutil
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict
from contextlib import contextmanager
import os

from PySide6.QtCore import QObject, Signal


@dataclass
class PerformanceMetric:
    """A performance metric with timing and metadata."""
    operation: str
    duration_ms: float
    timestamp: float
    success: bool
    file_count: int = 0
    file_size_mb: float = 0.0
    memory_mb: float = 0.0
    error_message: str = ""


@dataclass
class PerformanceStats:
    """Aggregated performance statistics."""
    total_operations: int = 0
    successful_operations: int = 0
    total_duration_ms: float = 0.0
    average_duration_ms: float = 0.0
    min_duration_ms: float = float('inf')
    max_duration_ms: float = 0.0
    total_file_size_mb: float = 0.0
    average_memory_mb: float = 0.0
    error_count: int = 0
    recent_metrics: List[PerformanceMetric] = field(default_factory=list)


class PerformanceMonitor(QObject):
    """Monitors and tracks performance metrics."""
    
    # Signals for real-time updates
    operation_started = Signal(str)  # operation_name
    operation_completed = Signal(str, float)  # operation_name, duration_ms
    operation_failed = Signal(str, str)  # operation_name, error_message
    
    def __init__(self, max_history: int = 100):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # Performance tracking
        self.metrics: List[PerformanceMetric] = []
        self.operation_stats: Dict[str, PerformanceStats] = defaultdict(PerformanceStats)
        self.max_history = max_history
        
        # Current operation tracking
        self.current_operation: Optional[str] = None
        self.operation_start_time: Optional[float] = None
        
        # Memory tracking
        self.process = psutil.Process()
    
    def _get_memory_usage_mb(self) -> float:
        """Get current memory usage in MB."""
        try:
            memory_info = self.process.memory_info()
            return memory_info.rss / (1024 * 1024)
        except Exception as e:
            self.logger.warning(f"Could not get memory usage: {e}")
            return 0.0
    
    def _get_file_size_mb(self, file_paths: List[str]) -> float:
        """Calculate total file size in MB."""
        try:
            total_size = 0
            for file_path in file_paths:
                if os.path.exists(file_path):
                    total_size += os.path.getsize(file_path)
            return total_size / (1024 * 1024)
        except Exception as e:
            self.logger.warning(f"Could not calculate file size: {e}")
            return 0.0
    
    @contextmanager
    def track_operation(self, operation: str, file_paths: List[str] = None):
        """Context manager for tracking operation performance."""
        self.start_operation(operation, file_paths)
        try:
            yield
            self.end_operation(operation, success=True)
        except Exception as e:
            self.end_operation(operation, success=False, error_message=str(e))
            raise
    
    def start_operation(self, operation: str, file_paths: List[str] = None):
        """Start tracking an operation."""
        if self.current_operation:
            self.logger.warning(f"Starting operation '{operation}' while '{self.current_operation}' is still running")
        
        self.current_operation = operation
        self.operation_start_time = time.time()
        
        self.operation_started.emit(operation)
        self.logger.info(f"Started operation: {operation}")
    
    def end_operation(self, operation: str, success: bool = True, error_message: str = ""):
        """End tracking an operation."""
        if not self.operation_start_time or self.current_operation != operation:
            self.logger.warning(f"Ending operation '{operation}' that wasn't started")
            return
        
        duration_ms = (time.time() - self.operation_start_time) * 1000
        memory_mb = self._get_memory_usage_mb()
        
        # Create metric
        metric = PerformanceMetric(
            operation=operation,
            duration_ms=duration_ms,
            timestamp=time.time(),
            success=success,
            memory_mb=memory_mb,
            error_message=error_message
        )
        
        # Add to metrics list
        self.metrics.append(metric)
        
        # Keep only recent metrics
        if len(self.metrics) > self.max_history:
            self.metrics = self.metrics[-self.max_history:]
        
        # Update operation stats
        self._update_operation_stats(operation, metric)
        
        # Emit signals
        if success:
            self.operation_completed.emit(operation, duration_ms)
        else:
            self.operation_failed.emit(operation, error_message)
        
        # Reset current operation
        self.current_operation = None
        self.operation_start_time = None
        
        self.logger.info(f"Completed operation: {operation} ({duration_ms:.1f}ms, {'success' if success else 'failed'})")
    
    def _update_operation_stats(self, operation: str, metric: PerformanceMetric):
        """Update statistics for an operation."""
        stats = self.operation_stats[operation]
        
        stats.total_operations += 1
        stats.total_duration_ms += metric.duration_ms
        
        if metric.success:
            stats.successful_operations += 1
        else:
            stats.error_count += 1
        
        # Update min/max
        if metric.duration_ms < stats.min_duration_ms:
            stats.min_duration_ms = metric.duration_ms
        if metric.duration_ms > stats.max_duration_ms:
            stats.max_duration_ms = metric.duration_ms
        
        # Update averages
        stats.average_duration_ms = stats.total_duration_ms / stats.total_operations
        
        # Update memory average
        total_memory = sum(m.memory_mb for m in self.metrics if m.operation == operation)
        memory_count = len([m for m in self.metrics if m.operation == operation])
        stats.average_memory_mb = total_memory / memory_count if memory_count > 0 else 0
        
        # Add to recent metrics
        stats.recent_metrics.append(metric)
        if len(stats.recent_metrics) > 10:  # Keep last 10 metrics per operation
            stats.recent_metrics = stats.recent_metrics[-10:]
    
    def get_operation_stats(self, operation: str = None) -> Dict[str, Any]:
        """Get performance statistics for operations."""
        if operation:
            stats = self.operation_stats.get(operation)
            if not stats:
                return {}
            
            return {
                "operation": operation,
                "total_operations": stats.total_operations,
                "successful_operations": stats.successful_operations,
                "success_rate_percent": round(stats.successful_operations / stats.total_operations * 100, 1) if stats.total_operations > 0 else 0,
                "average_duration_ms": round(stats.average_duration_ms, 1),
                "min_duration_ms": round(stats.min_duration_ms, 1) if stats.min_duration_ms != float('inf') else 0,
                "max_duration_ms": round(stats.max_duration_ms, 1),
                "average_memory_mb": round(stats.average_memory_mb, 1),
                "error_count": stats.error_count,
                "recent_metrics_count": len(stats.recent_metrics)
            }
        else:
            # Return stats for all operations
            return {
                operation: self.get_operation_stats(operation)
                for operation in self.operation_stats.keys()
            }
    
    def get_overall_stats(self) -> Dict[str, Any]:
        """Get overall performance statistics."""
        if not self.metrics:
            return {}
        
        total_operations = len(self.metrics)
        successful_operations = len([m for m in self.metrics if m.success])
        total_duration = sum(m.duration_ms for m in self.metrics)
        average_memory = sum(m.memory_mb for m in self.metrics) / total_operations
        
        return {
            "total_operations": total_operations,
            "successful_operations": successful_operations,
            "success_rate_percent": round(successful_operations / total_operations * 100, 1),
            "average_duration_ms": round(total_duration / total_operations, 1),
            "total_duration_minutes": round(total_duration / 60000, 1),
            "average_memory_mb": round(average_memory, 1),
            "current_memory_mb": round(self._get_memory_usage_mb(), 1),
            "operations_tracked": list(self.operation_stats.keys())
        }
    
    def get_slow_operations(self, threshold_ms: float = 5000) -> List[Dict[str, Any]]:
        """Get operations that took longer than the threshold."""
        slow_operations = []
        
        for metric in self.metrics:
            if metric.duration_ms > threshold_ms:
                slow_operations.append({
                    "operation": metric.operation,
                    "duration_ms": round(metric.duration_ms, 1),
                    "timestamp": metric.timestamp,
                    "success": metric.success,
                    "error_message": metric.error_message
                })
        
        # Sort by duration (slowest first)
        slow_operations.sort(key=lambda x: x["duration_ms"], reverse=True)
        return slow_operations
    
    def get_error_summary(self) -> Dict[str, int]:
        """Get summary of errors by operation."""
        error_counts = defaultdict(int)
        
        for metric in self.metrics:
            if not metric.success:
                error_counts[metric.operation] += 1
        
        return dict(error_counts)
    
    def clear_history(self):
        """Clear performance history."""
        self.metrics.clear()
        self.operation_stats.clear()
        self.logger.info("Cleared performance history")
    
    def export_metrics(self, file_path: str):
        """Export metrics to JSON file."""
        try:
            import json
            from dataclasses import asdict
            
            export_data = {
                "overall_stats": self.get_overall_stats(),
                "operation_stats": self.get_operation_stats(),
                "metrics": [asdict(metric) for metric in self.metrics],
                "export_timestamp": time.time()
            }
            
            with open(file_path, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            self.logger.info(f"Exported metrics to {file_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to export metrics: {e}")
            raise 