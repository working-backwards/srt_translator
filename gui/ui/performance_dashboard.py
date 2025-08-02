#!/usr/bin/env python3
"""
Performance Dashboard Widget

Displays real-time performance metrics including:
- Operation timing
- Memory usage
- Cache performance
- Error rates
- Performance trends
"""

import logging
from typing import Dict, List, Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import (
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..cache_manager import CacheManager
from ..performance_monitor import PerformanceMonitor


class PerformanceDashboard(QWidget):
    """Widget for displaying performance metrics and statistics."""

    def __init__(
        self,
        performance_monitor: PerformanceMonitor,
        cache_manager: CacheManager,
        parent=None,
    ):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.performance_monitor = performance_monitor
        self.cache_manager = cache_manager

        # Update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(2000)  # Update every 2 seconds

        self.setup_ui()
        self.connect_signals()
        self.update_display()

    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel("Performance Dashboard")
        title_label.setObjectName("sectionTitle")
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setObjectName("secondaryButton")
        self.export_btn = QPushButton("Export Metrics")
        self.export_btn.setObjectName("secondaryButton")
        self.clear_btn = QPushButton("Clear History")
        self.clear_btn.setObjectName("dangerButton")

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.refresh_btn)
        header_layout.addWidget(self.export_btn)
        header_layout.addWidget(self.clear_btn)
        layout.addLayout(header_layout)

        # Main content splitter
        main_splitter = QSplitter(Qt.Horizontal)

        # Left panel - Overall stats
        left_panel = QFrame()
        left_layout = QVBoxLayout(left_panel)

        # Overall performance
        overall_group = QGroupBox("Overall Performance")
        overall_layout = QVBoxLayout(overall_group)

        self.overall_stats_text = QTextEdit()
        self.overall_stats_text.setMaximumHeight(150)
        self.overall_stats_text.setReadOnly(True)
        overall_layout.addWidget(self.overall_stats_text)

        left_layout.addWidget(overall_group)

        # Memory usage
        memory_group = QGroupBox("Memory Usage")
        memory_layout = QVBoxLayout(memory_group)

        self.memory_label = QLabel("Current Memory: ")
        self.memory_label.setObjectName("subHeaderLabel")
        self.memory_bar = QProgressBar()
        self.memory_bar.setRange(0, 100)
        self.memory_bar.setFormat("%.1f MB")

        memory_layout.addWidget(self.memory_label)
        memory_layout.addWidget(self.memory_bar)

        left_layout.addWidget(memory_group)

        # Cache performance
        cache_group = QGroupBox("Cache Performance")
        cache_layout = QVBoxLayout(cache_group)

        self.cache_stats_text = QTextEdit()
        self.cache_stats_text.setMaximumHeight(120)
        self.cache_stats_text.setReadOnly(True)
        cache_layout.addWidget(self.cache_stats_text)

        left_layout.addWidget(cache_group)

        main_splitter.addWidget(left_panel)

        # Right panel - Operation details
        right_panel = QFrame()
        right_layout = QVBoxLayout(right_panel)

        # Operation statistics table
        operations_group = QGroupBox("Operation Statistics")
        operations_layout = QVBoxLayout(operations_group)

        self.operations_table = QTableWidget()
        self.operations_table.setColumnCount(7)
        self.operations_table.setHorizontalHeaderLabels(
            [
                "Operation",
                "Count",
                "Success Rate",
                "Avg Time (ms)",
                "Min Time (ms)",
                "Max Time (ms)",
                "Errors",
            ]
        )

        # Set table properties
        header = self.operations_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 7):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)

        operations_layout.addWidget(self.operations_table)
        right_layout.addWidget(operations_group)

        # Error summary
        errors_group = QGroupBox("Error Summary")
        errors_layout = QVBoxLayout(errors_group)

        self.errors_text = QTextEdit()
        self.errors_text.setMaximumHeight(100)
        self.errors_text.setReadOnly(True)
        errors_layout.addWidget(self.errors_text)

        right_layout.addWidget(errors_group)

        main_splitter.addWidget(right_panel)
        main_splitter.setSizes([400, 600])

        layout.addWidget(main_splitter)

    def connect_signals(self):
        """Connect widget signals."""
        self.refresh_btn.clicked.connect(self.update_display)
        self.export_btn.clicked.connect(self.export_metrics)
        self.clear_btn.clicked.connect(self.clear_history)

        # Connect performance monitor signals
        self.performance_monitor.operation_completed.connect(
            self.on_operation_completed
        )
        self.performance_monitor.operation_failed.connect(self.on_operation_failed)

    def update_display(self):
        """Update the performance display."""
        try:
            # Update overall stats
            overall_stats = self.performance_monitor.get_overall_stats()
            if overall_stats:
                stats_text = f"""Total Operations: {overall_stats.get('total_operations', 0)}
Successful Operations: {overall_stats.get('successful_operations', 0)}
Success Rate: {overall_stats.get('success_rate_percent', 0)}%
Average Duration: {overall_stats.get('average_duration_ms', 0)} ms
Total Duration: {overall_stats.get('total_duration_minutes', 0)} minutes
Average Memory: {overall_stats.get('average_memory_mb', 0)} MB
Current Memory: {overall_stats.get('current_memory_mb', 0)} MB
Operations Tracked: {', '.join(overall_stats.get('operations_tracked', []))}"""
            else:
                stats_text = "No performance data available"

            self.overall_stats_text.setText(stats_text)

            # Update memory display
            current_memory = overall_stats.get("current_memory_mb", 0)
            self.memory_label.setText(f"Current Memory: {current_memory:.1f} MB")

            # Set memory bar (assuming 1GB as max for display purposes)
            memory_percent = min(current_memory / 1024 * 100, 100)
            self.memory_bar.setValue(int(memory_percent))
            self.memory_bar.setFormat(f"{current_memory:.1f} MB")

            # Color code memory bar
            if memory_percent > 80:
                self.memory_bar.setStyleSheet(
                    "QProgressBar::chunk { background-color: red; }"
                )
            elif memory_percent > 60:
                self.memory_bar.setStyleSheet(
                    "QProgressBar::chunk { background-color: orange; }"
                )
            else:
                self.memory_bar.setStyleSheet(
                    "QProgressBar::chunk { background-color: green; }"
                )

            # Update cache stats
            cache_stats = self.cache_manager.get_stats()
            if cache_stats:
                cache_text = f"""Cache Files: {cache_stats.get('cache_files', 0)}
Cache Size: {cache_stats.get('cache_size_mb', 0)} MB
Hit Rate: {cache_stats.get('hit_rate_percent', 0)}%
Total Requests: {cache_stats.get('total_requests', 0)}
Hits: {cache_stats.get('hit_count', 0)}
Misses: {cache_stats.get('miss_count', 0)}"""
            else:
                cache_text = "No cache data available"

            self.cache_stats_text.setText(cache_text)

            # Update operations table
            self.update_operations_table()

            # Update error summary
            self.update_error_summary()

        except Exception as e:
            self.logger.error(f"Error updating performance display: {e}")

    def update_operations_table(self):
        """Update the operations statistics table."""
        try:
            operation_stats = self.performance_monitor.get_operation_stats()

            self.operations_table.setRowCount(len(operation_stats))

            for row, (operation, stats) in enumerate(operation_stats.items()):
                # Operation name
                self.operations_table.setItem(row, 0, QTableWidgetItem(operation))

                # Total count
                self.operations_table.setItem(
                    row, 1, QTableWidgetItem(str(stats.get("total_operations", 0)))
                )

                # Success rate
                success_rate = stats.get("success_rate_percent", 0)
                success_item = QTableWidgetItem(f"{success_rate}%")
                if success_rate < 80:
                    success_item.setBackground(QColor(255, 200, 200))  # Light red
                self.operations_table.setItem(row, 2, success_item)

                # Average time
                avg_time = stats.get("average_duration_ms", 0)
                avg_item = QTableWidgetItem(f"{avg_time:.1f}")
                if avg_time > 5000:  # 5 seconds
                    avg_item.setBackground(QColor(255, 200, 200))  # Light red
                elif avg_time > 2000:  # 2 seconds
                    avg_item.setBackground(QColor(255, 255, 200))  # Light yellow
                self.operations_table.setItem(row, 3, avg_item)

                # Min time
                min_time = stats.get("min_duration_ms", 0)
                self.operations_table.setItem(
                    row, 4, QTableWidgetItem(f"{min_time:.1f}")
                )

                # Max time
                max_time = stats.get("max_duration_ms", 0)
                max_item = QTableWidgetItem(f"{max_time:.1f}")
                if max_time > 10000:  # 10 seconds
                    max_item.setBackground(QColor(255, 200, 200))  # Light red
                self.operations_table.setItem(row, 5, max_item)

                # Error count
                error_count = stats.get("error_count", 0)
                error_item = QTableWidgetItem(str(error_count))
                if error_count > 0:
                    error_item.setBackground(QColor(255, 200, 200))  # Light red
                self.operations_table.setItem(row, 6, error_item)

        except Exception as e:
            self.logger.error(f"Error updating operations table: {e}")

    def update_error_summary(self):
        """Update the error summary display."""
        try:
            error_summary = self.performance_monitor.get_error_summary()

            if error_summary:
                error_text = "Errors by Operation:\n"
                for operation, count in error_summary.items():
                    error_text += f"• {operation}: {count} errors\n"
            else:
                error_text = "No errors recorded"

            self.errors_text.setText(error_text)

        except Exception as e:
            self.logger.error(f"Error updating error summary: {e}")

    def on_operation_completed(self, operation: str, duration_ms: float):
        """Handle operation completion."""
        self.logger.info(f"Operation completed: {operation} ({duration_ms:.1f}ms)")
        # The display will be updated by the timer

    def on_operation_failed(self, operation: str, error_message: str):
        """Handle operation failure."""
        self.logger.warning(f"Operation failed: {operation} - {error_message}")
        # The display will be updated by the timer

    def export_metrics(self):
        """Export performance metrics to file."""
        try:
            from PySide6.QtWidgets import QFileDialog

            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Performance Metrics",
                "performance_metrics.json",
                "JSON Files (*.json)",
            )

            if file_path:
                self.performance_monitor.export_metrics(file_path)
                QMessageBox.information(
                    self,
                    "Export Successful",
                    f"Performance metrics exported to:\n{file_path}",
                )

        except Exception as e:
            self.logger.error(f"Error exporting metrics: {e}")
            QMessageBox.warning(
                self, "Export Failed", f"Failed to export metrics: {str(e)}"
            )

    def clear_history(self):
        """Clear performance history."""
        try:
            reply = QMessageBox.question(
                self,
                "Clear History",
                "Are you sure you want to clear all performance history?",
                QMessageBox.Yes | QMessageBox.No,
            )

            if reply == QMessageBox.Yes:
                self.performance_monitor.clear_history()
                self.cache_manager.clear_all()
                self.update_display()
                QMessageBox.information(
                    self, "History Cleared", "Performance history has been cleared."
                )

        except Exception as e:
            self.logger.error(f"Error clearing history: {e}")
            QMessageBox.warning(
                self, "Clear Failed", f"Failed to clear history: {str(e)}"
            )

    def closeEvent(self, event):
        """Handle widget close event."""
        self.update_timer.stop()
        super().closeEvent(event)
