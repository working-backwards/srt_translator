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
        cost_label.setObjectName("costLabel")
        self.cost_estimate = QLabel("$0.00")
        self.cost_estimate.setObjectName("costEstimate")
        self.cost_estimate.setStyleSheet("color: #2563EB; font-weight: 600;")

        cost_layout.addWidget(cost_label)
        cost_layout.addWidget(self.cost_estimate)
        cost_layout.addStretch()

        # Translate button
        self.translate_btn = QPushButton("Translate All Files")
        self.translate_btn.setObjectName("mainActionButton")
        self.translate_btn.setFixedHeight(50)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setObjectName("progressBar")

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
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.log_output)

    def connect_signals(self, translate_callback):
        """Connect button signals to callbacks"""
        self.translate_btn.clicked.connect(translate_callback)

    def start_translation(self):
        """Start translation mode - disable UI and show progress"""
        self.translate_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.log_output.clear()

    def finish_translation(self):
        """Finish translation mode - enable UI and hide progress"""
        self.progress_bar.setVisible(False)
        self.translate_btn.setEnabled(True)

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
