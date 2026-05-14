#!/usr/bin/env python3
"""
Translation Section for the SRT Translator GUI.
"""

from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)


class TranslationSection(QGroupBox):
    """Translation section with controls and progress display"""

    def __init__(self):
        super().__init__("Translation")
        self.setObjectName("translationSection")

        self.setup_ui()

    def setup_ui(self):
        """Set up the translation section UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Cost estimation
        cost_layout = QHBoxLayout()
        cost_label = QLabel("Estimated Cost:")
        cost_label.setToolTip(
            "Estimated cost is approximate value."
        )
        cost_label.setObjectName("costLabel")
        self.cost_estimate = QLabel("$0.00")
        self.cost_estimate.setObjectName("costEstimate")
        self.cost_estimate.setStyleSheet("color: #2563EB; font-weight: 600;")

        cost_layout.addWidget(cost_label)
        cost_layout.addWidget(self.cost_estimate)
        cost_layout.addStretch()

        # Translate button
        self.translate_btn = QPushButton("Translate All Files")
        self.retry_failed_btn = QPushButton("Retry Failed Languages")
        self.retry_failed_btn.setObjectName("secondaryActionButton")
        self.retry_failed_btn.setFixedHeight(44)
        self.retry_failed_btn.hide()
        self.translate_btn.setObjectName("mainActionButton")
        self.translate_btn.setFixedHeight(50)

        # Open HTML Report button
        self.open_html_btn = QPushButton("Open HTML Report")
        self.open_html_btn.setObjectName("mainActionButton")
        self.open_html_btn.setFixedHeight(50)
        self.open_html_btn.setEnabled(False)  # Disabled by default

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setObjectName("progressBar")

        self.retry_status_label = QLabel("")
        self.retry_status_label.setObjectName("retryStatus")
        self.retry_status_label.hide()

        self.cancel_btn = QPushButton("Cancel Translation")
        self.cancel_btn.setObjectName("secondaryActionButton")
        self.cancel_btn.setFixedHeight(44)
        self.cancel_btn.hide()

        # Log output
        self.log_output = QTextEdit()
        self.log_output.setObjectName("logOutput")
        self.log_output.setMinimumHeight(80)  # Minimum height as per style guide
        self.log_output.setMaximumHeight(200)
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText("Translation progress will appear here...")

        # Cap log widget to prevent unbounded growth
        self.log_output.document().setMaximumBlockCount(2000)

        layout.addLayout(cost_layout)
        layout.addWidget(self.translate_btn)
        layout.addWidget(self.retry_failed_btn)
        layout.addWidget(self.cancel_btn)
        layout.addWidget(self.open_html_btn)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.retry_status_label)
        layout.addWidget(self.log_output)

    def show_cancel_button(self):
        self.cancel_btn.show()

    def hide_cancel_button(self):
        self.cancel_btn.hide()

    def connect_signals(
        self,
        translate_callback,
        retry_failed_callback=None,
        open_html_callback=None,
        cancel_callback=None,
    ):
        """Connect button signals to callbacks"""
        self.translate_btn.clicked.connect(translate_callback)
        if retry_failed_callback:
            self.retry_failed_btn.clicked.connect(
                retry_failed_callback
            )
        if cancel_callback:
            self.cancel_btn.clicked.connect(cancel_callback)
        if open_html_callback:
            self.open_html_btn.clicked.connect(open_html_callback)

    def show_retry_failed_button(self):
        self.retry_failed_btn.show()

    def hide_retry_failed_button(self):
        self.retry_failed_btn.hide()

    def show_retry_status(self, message: str):
        """Show or hide retry status message"""

        # Empty message means clear/hide the banner
        if not message:
            self.retry_status_label.clear()
            self.retry_status_label.hide()
            return

        self.retry_status_label.setText(message)
        self.retry_status_label.show()

    def clear_retry_status(self):
        self.retry_status_label.clear()
        self.retry_status_label.hide()

    def start_translation(self):
        """Start translation mode - disable UI and show progress"""
        self.translate_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.log_output.clear()

    def finish_translation(self, has_report: bool = False):
        """Finish translation mode - enable UI and hide progress"""
        self.progress_bar.setVisible(False)
        self.translate_btn.setEnabled(True)
        if has_report:
            self.open_html_btn.setEnabled(True)

    def reset_progress_bar(self):
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("")
        self.progress_bar.setVisible(False)

    def show_translate_button(self):
        self.translate_btn.setEnabled(True)
        self.translate_btn.setText("Translate All Files")

    def update_log_output(self, message: str):
        """Update the log output with a message"""
        self.log_output.append(message)
        # Auto-scroll to bottom
        scrollbar = self.log_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear_log_output(self):
        """Clear the log output"""
        self.log_output.clear()

    def update_cost_estimate(self, cost: str):
        """Update the cost estimate display"""
        self.cost_estimate.setText(cost)
        self.cost_estimate.setVisible(True)
