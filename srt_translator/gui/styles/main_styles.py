#!/usr/bin/env python3
"""
Main styles for the SRT Translator GUI — dark theme.
"""

MAIN_STYLESHEET = """
    /*  Main Window */
    QMainWindow {
        background-color: #12141C;
    }

    /*  Title Bar  */
    #titleBar {
        background-color: #12141C;
        border-bottom: 1px solid #2A2D38;
        height: 52px;
    }

    #titleLabel {
        color: #E5E7EB;
        font-size: 15px;
        font-weight: 600;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        letter-spacing: 0.2px;
    }

    #versionBadge {
        color: #6B7280;
        font-size: 11px;
        font-weight: 500;
        background-color: #1E2028;
        border: 1px solid #2A2D38;
        border-radius: 8px;
        padding: 2px 8px;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    /*  Main Content Container  */
    #contentContainer {
        background-color: #12141C;
        border-radius: 0px;
        margin: 0px;
        padding: 12px;
    }

    /*  Section / Group Boxes  */
    QGroupBox {
        background-color: #1E2028;
        font-size: 14px;
        font-weight: 600;
        color: #E5E7EB;
        border: 1px solid #2A2D38;
        border-radius: 14px;
        margin-top: 14px;
        padding-top: 14px;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    QGroupBox::title {
        subcontrol-origin: margin;
        left: 14px;
        padding: 0 6px;
        color: #E5E7EB;
        font-size: 14px;
        font-weight: 600;
        background-color: #1E2028;
    }

    /* Sub-headers  */
    #subHeaderLabel {
        font-size: 13px;
        font-weight: 600;
        color: #D1D5DB;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    /*  Generic Labels  */
    QLabel {
        color: #9CA3AF;
        font-size: 13px;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        background-color: transparent;
    }

    /*  Input Fields  */
    #apiKeyInput,
    #searchInput {
        background-color: #252830;
        border: 1px solid #2A2D38;
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 13px;
        height: 38px;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        color: #E5E7EB;
        selection-background-color: #2563EB;
    }

    #searchInput {
        height: 26px;
        padding: 4px 10px;
    }

    #apiKeyInput:focus,
    #searchInput:focus {
        border-color: #2563EB;
        background-color: #2A2D38;
        outline: none;
    }

    #apiKeyInput::placeholder,
    #searchInput::placeholder {
        color: #4B5068;
        font-size: 13px;
    }

    /*  Primary Buttons */
    #primaryButton {
        background-color: #2563EB;
        color: #FFFFFF;
        border: none;
        border-radius: 8px;
        padding: 0px 18px;
        font-size: 13px;
        font-weight: 500;
        height: 38px;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    #primaryButton:hover {
        background-color: #1D4ED8;
    }

    #primaryButton:pressed {
        background-color: #1E40AF;
    }

    #primaryButton:disabled {
        background-color: #1A1D26;
        color: #4B5068;
    }

    /*  Main Action Button (Translate / Report) */
    #mainActionButton {
        background-color: #252830;
        color: #D1D5DB;
        border: 1px solid #2A2D38;
        border-radius: 10px;
        padding: 0px 18px;
        font-size: 14px;
        font-weight: 500;
        height: 46px;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    #mainActionButton:hover {
        background-color: #2E3140;
        border-color: #4B5068;
        color: #FFFFFF;
    }

    #mainActionButton:pressed {
        background-color: #1E2028;
    }

    #mainActionButton:disabled {
        background-color: #1A1D26;
        color: #3B3F52;
        border-color: #252830;
    }

    /* Translate button — blue-tinted variant */
    #translateButton {
        background-color: #1E3A5F;
        color: #93C5FD;
        border: 1px solid #2563EB;
        border-radius: 10px;
        padding: 0px 18px;
        font-size: 14px;
        font-weight: 600;
        height: 46px;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    #translateButton:hover {
        background-color: #1D4ED8;
        color: #FFFFFF;
        border-color: #3B82F6;
    }

    #translateButton:pressed {
        background-color: #1E40AF;
    }

    #translateButton:disabled {
        background-color: #1A1D26;
        color: #3B3F52;
        border-color: #252830;
    }

    /* Advanced Settings title match */
    QLabel {
        font-size: 14px;
        font-weight: 600;
        color: #E5E7EB;
    }

    /*  Secondary Buttons  */
    #secondaryButton {
        background-color: #252830;
        color: #93C5FD;
        border: 1px solid #2A2D38;
        border-radius: 10px;
        padding: 10px 14px;
        font-size: 13px;
        font-weight: 500;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    #secondaryButton:hover {
        background-color: #2E3140;
        border-color: #4B5068;
        color: #BFDBFE;
    }

    #secondaryButton:pressed {
        background-color: #1E2028;
    }

    #secondaryButton:disabled {
        color: #3B3F52;
        border-color: #252830;
    }

    /*  Toggle Button  */
    #toggleButton {
        background-color: #252830;
        color: #9CA3AF;
        border: 1px solid #2A2D38;
        border-radius: 6px;
        padding: 4px;
        font-size: 16px;
        font-weight: bold;
        height: 28px;
        width: 28px;
        text-align: center;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    #toggleButton:hover {
        background-color: #2E3140;
        color: #E5E7EB;
    }

    #toggleButton:pressed {
        background-color: #1E2028;
    }

    /*  Help Button  */
    #helpButton {
        background-color: #1E2A3A;
        color: #60A5FA;
        border: 1px solid #2A3A52;
        border-radius: 14px;
        font-size: 13px;
        font-weight: 600;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    #helpButton:hover {
        background-color: #253348;
        border-color: #3B82F6;
        color: #93C5FD;
    }

    #helpButton:pressed {
        background-color: #1A2535;
    }

    /*  File List / Language List */
    #fileList,
    #languageList {
        background-color: #252830;
        border: 1px solid #2A2D38;
        border-radius: 8px;
        padding: 5px;
        font-size: 13px;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        color: #D1D5DB;
        min-height: 90px;
        max-height: 120px;
    }

    #fileList:hover {
        background-color: #1E2A3A;
    }

    #fileList::item,
    #languageList::item {
        padding: 8px;
        border-radius: 4px;
        margin: 2px;
        color: #D1D5DB;
    }

    #fileList::item:selected,
    #languageList::item:selected {
        background-color: #1E3A5F;
        color: #BFDBFE;
    }

    #fileList::item:hover,
    #languageList::item:hover {
        background-color: #2A2D38;
    }

    /* Language Checkboxes  */
    #languageCheckbox {
        background-color: #252830;
        border: 1px solid #2A2D38;
        border-radius: 8px;
        padding: 2px 10px;
        font-size: 13px;
        color: #D1D5DB;
        spacing: 8px;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    #languageCheckbox:hover {
        background-color: #2E3140;
        border-color: #3B82F6;
    }

    #languageCheckbox:checked {
        background-color: #1E3A5F;
        border: 1px solid #2563EB;
        color: #BFDBFE;
    }

    #languageCheckbox::indicator {
        width: 16px;
        height: 16px;
    }

    #languageCheckbox::indicator:unchecked {
        border: 2px solid #3B3F52;
        border-radius: 4px;
        background-color: #252830;
    }

    #languageCheckbox::indicator:checked {
        border: 2px solid #2563EB;
        border-radius: 4px;
        background-color: #2563EB;
    }

    #languageCheckbox::indicator:hover {
        border-color: #3B82F6;
    }

    /*  General QCheckBox  */
    QCheckBox {
        background-color: #252830;
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 13px;
        color: #D1D5DB;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    QCheckBox:hover {
        background-color: #2E3140;
    }

    /* Radio Buttons */
    QRadioButton {
        color: #D1D5DB;
        font-size: 13px;
        spacing: 6px;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        background-color: transparent;
    }

    QRadioButton::indicator {
        width: 15px;
        height: 15px;
        border-radius: 8px;
        border: 2px solid #3B3F52;
        background-color: #252830;
    }

    QRadioButton::indicator:checked {
        border: 2px solid #2563EB;
        background-color: #2563EB;
    }

    QRadioButton::indicator:hover {
        border-color: #3B82F6;
    }

    /* Tone radio pill buttons */
    #toneRadio {
        background-color: #252830;
        border: 1px solid #2A2D38;
        border-radius: 8px;
        padding: 8px 18px;
        color: #9CA3AF;
        font-size: 13px;
        font-weight: 500;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    #toneRadio:hover {
        background-color: #2E3140;
        color: #D1D5DB;
    }

    #toneRadio:checked {
        background-color: #1E3A5F;
        border-color: #2563EB;
        color: #BFDBFE;
    }

    /*  Progress Bar  */
    #progressBar {
        border: 1px solid #2A2D38;
        border-radius: 6px;
        background-color: #252830;
        text-align: center;
        color: #9CA3AF;
        font-size: 11px;
        height: 18px;
    }

    #progressBar::chunk {
        background-color: #2563EB;
        border-radius: 5px;
    }

    /*  Log Output  */
    #logOutput {
        background-color: #14161E;
        border: 1px solid #2A2D38;
        border-radius: 8px;
        padding: 10px 12px;
        font-family: "JetBrains Mono", "Fira Code", "Consolas", "Monaco", monospace;
        font-size: 12px;
        color: #9CA3AF;
        selection-background-color: #2563EB;
        min-height: 80px;
    }

    /*  Status Labels */
    #statusLabel {
        font-size: 12px;
        color: #6B7280;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    #statusIcon {
        font-size: 14px;
        font-weight: bold;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    #apiStatusText {
        font-size: 12px;
        font-weight: 500;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    #fileCountLabel,
    #languageCountLabel {
        font-size: 12px;
        color: #4B5068;
        font-style: italic;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    /*  Cost Display  */
    #costRow {
        background-color: #252830;
        border: 1px solid #2A2D38;
        border-radius: 10px;
        padding: 10px 14px;
    }

    #costLabel {
        color: #9CA3AF;
        font-size: 13px;
        font-weight: 500;
    }

    #costMeta {
        color: #4B5068;
        font-size: 11px;
        font-weight: 400;
    }

    #costEstimate {
        color: #34D399;
        font-size: 20px;
        font-weight: 700;
        letter-spacing: -0.5px;
    }

    /* ── AI Config Section */
    #aiConfigSection {
        background-color: #1A2535;
        border: 1px solid #2A3A52;
        border-radius: 8px;
    }

    #aiTermsDisplay,
    #termbaseDisplay {
        background-color: #14161E;
        border: 1px solid #2A2D38;
        border-radius: 6px;
        padding: 8px;
        font-family: "JetBrains Mono", "Fira Code", "Consolas", "Monaco", monospace;
        font-size: 12px;
        color: #9CA3AF;
    }

    /* ── Dropdowns  */
    QComboBox {
        color: #D1D5DB;
        background-color: #252830;
        border: 1px solid #2A2D38;
        border-radius: 8px;
        padding: 4px 10px;
        font-size: 13px;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        min-width: 160px;
        height: 36px;
    }

    QComboBox:hover {
        border-color: #3B3F52;
        background-color: #2E3140;
    }

    QComboBox:focus {
        border-color: #2563EB;
    }

    QComboBox::drop-down {
        border: none;
        width: 22px;
    }

    QComboBox QAbstractItemView {
        color: #D1D5DB;
        background-color: #252830;
        border: 1px solid #2A2D38;
        selection-background-color: #1E3A5F;
        selection-color: #BFDBFE;
        font-size: 13px;
        padding: 4px;
    }

    /* Settings Button (gear icon in title bar) */
    #settingsButton {
        background-color: transparent;
        color: #9CA3AF;
        border: 1px solid #2A2D38;
        border-radius: 6px;
        padding: 4px 10px;
        font-size: 18px;
        height: 34px;
        width: 34px;
    }

    #settingsButton:hover {
        background-color: #252830;
        border-color: #3B3F52;
        color: #E5E7EB;
    }

    #settingsButton:pressed {
        background-color: #1E2028;
    }

    /* Next / Back navigation buttons */
    #nextButton {
        background-color: #2563EB;
        color: #FFFFFF;
        border: none;
        border-radius: 6px;
        padding: 6px 20px;
        font-size: 13px;
        font-weight: 600;
        height: 32px;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    #nextButton:hover {
        background-color: #1D4ED8;
    }

    #nextButton:pressed {
        background-color: #1E40AF;
    }

    #backButton {
        background-color: #252830;
        color: #D1D5DB;
        border: 1px solid #2A2D38;
        border-radius: 6px;
        padding: 6px 20px;
        font-size: 13px;
        font-weight: 500;
        height: 32px;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    #backButton:hover {
        background-color: #2E3140;
        border-color: #4B5068;
        color: #FFFFFF;
    }

    #backButton:pressed {
        background-color: #1E2028;
    }

    /* ── Scroll Bars */
    QScrollArea {
        border: none;
        background-color: transparent;
    }

    QScrollBar:vertical {
        background-color: #1E2028;
        width: 10px;
        border-radius: 5px;
        margin: 0px;
    }

    QScrollBar::handle:vertical {
        background-color: #2A2D38;
        border-radius: 5px;
        min-height: 24px;
    }

    QScrollBar::handle:vertical:hover {
        background-color: #3B3F52;
    }

    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {
        height: 0px;
    }

    QScrollBar:horizontal {
        background-color: #1E2028;
        height: 10px;
        border-radius: 5px;
    }

    QScrollBar::handle:horizontal {
        background-color: #2A2D38;
        border-radius: 5px;
        min-width: 24px;
    }

    QScrollBar::handle:horizontal:hover {
        background-color: #3B3F52;
    }

    QScrollBar::add-line:horizontal,
    QScrollBar::sub-line:horizontal {
        width: 0px;
    }

    /* Separators*/
    QFrame[frameShape="4"],
    QFrame[frameShape="5"] {
        color: #2A2D38;
        background-color: #2A2D38;
    }

    /* ── Tab Widget  */
    QTabWidget::pane {
        border: 1px solid #2A2D38;
        border-radius: 8px;
        background-color: #1E2028;
    }

    QTabBar::tab {
        background-color: #252830;
        color: #9CA3AF;
        border: 1px solid #2A2D38;
        border-bottom: none;
        border-radius: 6px 6px 0px 0px;
        padding: 8px 18px;
        font-size: 13px;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    QTabBar::tab:selected {
        background-color: #1E2028;
        color: #E5E7EB;
        border-color: #2A2D38;
    }

    QTabBar::tab:hover:!selected {
        background-color: #2E3140;
        color: #D1D5DB;
    }

    QTabBar::tab:disabled {
        color: #3B3F52;
        background-color: #1A1D26;
    }

    QTabBar::tab:first {
        border-top-left-radius: 6px;
    }

    QTabBar::tab:last {
        border-top-right-radius: 6px;
    }

    /* ── Dialog / Message Box*/
    QDialog {
        background-color: #1E2028;
    }

    QMessageBox {
        background-color: #1E2028;
        color: #E5E7EB;
    }

    QDialogButtonBox QPushButton {
        background-color: #252830;
        color: #D1D5DB;
        border: 1px solid #2A2D38;
        border-radius: 8px;
        padding: 6px 18px;
        font-size: 13px;
        min-width: 80px;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    QDialogButtonBox QPushButton:hover {
        background-color: #2E3140;
        border-color: #4B5068;
        color: #FFFFFF;
    }

    QDialogButtonBox QPushButton:pressed {
        background-color: #1E2028;
    }

    /* ── Tooltip */
    QToolTip {
        background-color: #252830;
        color: #E5E7EB;
        border: 1px solid #3B3F52;
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 12px;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    /* Success / Error semantic colours */
    .success { color: #34D399; }
    .error   { color: #F87171; }
    .warning { color: #FBBF24; }
"""
