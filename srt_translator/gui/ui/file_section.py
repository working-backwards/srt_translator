#!/usr/bin/env python3
"""
File Selection Section for the SRT Translator GUI.
"""

import logging
import os
from typing import List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)


class FileSection(QGroupBox):
    """File selection section with multi-select capabilities and output directory selection"""

    def __init__(self, settings_manager):
        super().__init__("Original Language SRT Files")
        self.settings_manager = settings_manager
        self.setObjectName("fileSection")
        self.selected_files = []
        self.output_directory = ""

        self.setup_ui()

    def setup_ui(self):
        """Set up the file section UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # File selection buttons
        button_layout = QHBoxLayout()
        self.browse_files_btn = QPushButton("Browse Files")
        self.browse_files_btn.setObjectName("secondaryButton")

        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.setObjectName("secondaryButton")

        self.clear_all_btn = QPushButton("Clear All")
        self.clear_all_btn.setObjectName("secondaryButton")

        button_layout.addWidget(self.browse_files_btn)
        button_layout.addWidget(self.select_all_btn)
        button_layout.addWidget(self.clear_all_btn)
        button_layout.addStretch()
        button_layout.setSpacing(10)  # 10px horizontal gaps as per style guide

        # File list
        self.file_list = QListWidget()
        self.file_list.setObjectName("fileList")
        self.file_list.setSelectionMode(QListWidget.MultiSelection)
        self.file_list.setMinimumHeight(100)  # 100-120px as per style guide
        self.file_list.setMaximumHeight(120)

        # File count label
        self.file_count_label = QLabel("No files selected")
        self.file_count_label.setObjectName("fileCountLabel")

        # Output directory section
        output_layout = QHBoxLayout()
        output_label = QLabel("Output Directory:")
        output_label.setObjectName("outputLabel")

        self.output_path_label = QLabel("translated_srt_files")
        self.output_path_label.setObjectName("outputPathLabel")
        self.output_path_label.setStyleSheet("color: #666; font-style: italic;")

        self.browse_output_btn = QPushButton("Browse")
        self.browse_output_btn.setObjectName("secondaryButton")

        output_layout.addWidget(output_label)
        output_layout.addWidget(self.output_path_label, 1)  # Stretch to fill space
        output_layout.addWidget(self.browse_output_btn)
        output_layout.setSpacing(10)

        layout.addLayout(button_layout)
        layout.addWidget(self.file_list)
        layout.addWidget(self.file_count_label)
        layout.addLayout(output_layout)

    def connect_signals(
        self,
        browse_callback,
        select_all_callback,
        clear_all_callback,
        selection_changed_callback,
        browse_output_callback,
    ):
        """Connect button signals to callbacks"""
        self.browse_files_btn.clicked.connect(browse_callback)
        self.select_all_btn.clicked.connect(select_all_callback)
        self.clear_all_btn.clicked.connect(clear_all_callback)
        self.file_list.itemSelectionChanged.connect(selection_changed_callback)
        self.browse_output_btn.clicked.connect(browse_output_callback)

    def get_selected_files(self) -> List[str]:
        """Get list of currently selected file paths"""
        selected_files = []
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if item.isSelected():
                file_path = item.data(Qt.UserRole)
                selected_files.append(file_path)
        return selected_files

    def add_file(self, file_path: str):
        """Add a file to the list"""
        if file_path not in self.selected_files:
            self.selected_files.append(file_path)
            self.add_file_to_list(file_path)
            logging.debug(f"Added file to selection: {file_path}")
        else:
            logging.debug(f"File already selected: {file_path}")

    def add_file_to_list(self, file_path: str):
        """Add a file to the file list widget"""
        item = QListWidgetItem(os.path.basename(file_path))
        item.setData(Qt.UserRole, file_path)
        self.file_list.addItem(item)

    def select_all_files(self):
        """Select all files in the list"""
        for i in range(self.file_list.count()):
            self.file_list.item(i).setSelected(True)

    def clear_all_files(self):
        """Clear all selected files"""
        self.selected_files.clear()
        self.file_list.clear()
        self.update_file_count()
        self.settings_manager.save_selected_files([])

    def update_file_count(self):
        """Update the file count label based on selected_files list"""
        count = len(self.selected_files)
        if count == 0:
            self.file_count_label.setText("No files selected")
        elif count == 1:
            self.file_count_label.setText("1 file selected")
        else:
            self.file_count_label.setText(f"{count} files selected")

    def update_file_count_from_selection(self):
        """Update the file count label based on visual selection in list widget"""
        count = 0
        for i in range(self.file_list.count()):
            if self.file_list.item(i).isSelected():
                count += 1

        if count == 0:
            self.file_count_label.setText("No files selected")
        elif count == 1:
            self.file_count_label.setText("1 file selected")
        else:
            self.file_count_label.setText(f"{count} files selected")

    def load_saved_files(self):
        """Load previously selected files"""
        saved_files = self.settings_manager.load_selected_files()
        for file_path in saved_files:
            if os.path.exists(file_path):
                self.selected_files.append(file_path)
                self.add_file_to_list(file_path)

        self.update_file_count()

    def sync_selection_with_visual(self):
        """Sync internal selected_files list with visual selection"""
        self.selected_files = self.get_selected_files()
        self.settings_manager.save_selected_files(self.selected_files)

    def get_output_directory(self) -> str:
        """Get the currently selected output directory"""
        return (
            self.output_directory if self.output_directory else "translated_srt_files"
        )

    def set_output_directory(self, directory: str):
        """Set the output directory and update the display"""
        self.output_directory = directory
        if directory:
            self.output_path_label.setText(directory)
            self.output_path_label.setStyleSheet("color: #333; font-style: normal;")
        else:
            self.output_path_label.setText("translated_srt_files")
            self.output_path_label.setStyleSheet("color: #666; font-style: italic;")

    def browse_output_directory(self):
        """Open directory dialog to select output directory"""
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.Directory)
        dialog.setOption(QFileDialog.ShowDirsOnly, True)

        # Set initial directory
        last_dir = self.settings_manager.load_last_output_directory()
        if last_dir and os.path.exists(last_dir):
            dialog.setDirectory(last_dir)
        else:
            dialog.setDirectory(os.getcwd())

        if dialog.exec():
            selected_dir = dialog.selectedFiles()[0]
            self.set_output_directory(selected_dir)
            self.settings_manager.save_last_output_directory(selected_dir)
            logging.debug(f"Selected output directory: {selected_dir}")

    def load_saved_output_directory(self):
        """Load previously saved output directory"""
        saved_dir = self.settings_manager.load_last_output_directory()
        if saved_dir and os.path.exists(saved_dir):
            self.set_output_directory(saved_dir)
        else:
            # Use default
            self.set_output_directory("")
