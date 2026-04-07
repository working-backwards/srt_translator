#!/usr/bin/env python3
"""
Main styles for the SRT Translator GUI.
"""

MAIN_STYLESHEET = """
    /* Main Window */
    QMainWindow {
        background-color: #F8FAFC;
    }

    /* Title Bar */
    #titleBar {
        background-color: #2563EB;
        border-radius: 0px;
        height: 60px;
    }

    #titleLabel {
        color: white;
        font-size: 20px;
        font-weight: bold;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
            sans-serif;
    }

    /* Main Content Container */
    #contentContainer {
        background-color: #FFFFFF;
        border-radius: 12px;
        border: 1px solid #E5E7EB;
        margin: 10px;
        padding: 10px;
    }

    /* Section Headers */
    QGroupBox {
        background-color: #FFFFFF;
        font-size: 16px;
        font-weight: 600;
        color: #1E293B;
        border: 1px solid #E5E7EB;
        border-bottom: 2px solid #E5E7EB;
        border-radius: 12px;
        margin-top: 16px;
        padding-top: 16px;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
            sans-serif;
    }
    QCheckBox {
        background-color: #F3F4F6;
        border-radius: 10px;
        padding: 10px 14px;
        font-size: 14px;
    }

    QCheckBox:hover {
        background-color: #E5E7EB;
    }

    QGroupBox::title {
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 6px;
        color: #111827;
        font-size: 16px;
        font-weight: 600;
        background-color: #FFFFFF;
    }

    /* Sub-headers */
    #subHeaderLabel {
        font-size: 14px;
        font-weight: 600;
        color: #374151;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
            sans-serif;
    }

    /* Body Text */
    QLabel {
        color: #374151;
        font-size: 13px;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
            sans-serif;
    }

    /* Input Fields */
    #apiKeyInput, #searchInput {
        background-color: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 6px;
        padding: 8px 12px;
        font-size: 13px;
        height: 40px;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
            sans-serif;
        color: #374151;
    }

    #apiKeyInput:focus, #searchInput:focus {
        border-color: #2563EB;
        outline: none;
    }

    #apiKeyInput::placeholder, #searchInput::placeholder {
        color: #9CA3AF;
        font-size: 13px;
    }

    /* Primary Buttons */
    #primaryButton, #mainActionButton {
        background-color: #2563EB;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 10px 20px;
        font-size: 13px;
        font-weight: 500;
        height: 40px;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
            sans-serif;
    }

    #mainActionButton {
        background-color: #2563EB;
        border-radius: 10px;
        height: 48px;
        font-size: 15px;
        font-weight: 600;
    }

    #primaryButton:hover, #mainActionButton:hover {
        background-color: #1D4ED8;
    }

    #primaryButton:pressed, #mainActionButton:pressed {
        background-color: #1E40AF;
    }
    
    #mainActionButton {
      background-color: #2563EB;
}

    /* Secondary Buttons */
    #secondaryButton {
        background-color: #FFFFFF;
        color: #2563EB;
        border: 1px solid #2563EB;
        border-radius: 8px;
        padding: 8px 16px;
        font-size: 13px;
        font-weight: 500;
        height: 36px;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
            sans-serif;
    }

    #secondaryButton:hover {
        background-color: #F9FAFB;
    }

    #secondaryButton:pressed {
        background-color: #D1D5DB;
    }

    /* Toggle Button with Chevron Animation */
    #toggleButton {
        background-color: #F3F4F6;
        color: #374151;
        border: 1px solid #D1D5DB;
        border-radius: 6px;
        padding: 4px;
        font-size: 18px;
        font-weight: bold;
        height: 30px;
        width: 30px;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
            sans-serif;
        text-align: center;
    }

    #toggleButton:hover {
        background-color: #E5E7EB;
    }

    #toggleButton:pressed {
        background-color: #D1D5DB;
    }

    /* Help Button */
    #helpButton {
        background-color: #EFF6FF;
        color: #2563EB;
        border: 1px solid #DBEAFE;
        border-radius: 15px;
        font-size: 14px;
        font-weight: 600;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
            sans-serif;
    }

    #helpButton:hover {
        background-color: #DBEAFE;
        border-color: #93C5FD;
    }

    #helpButton:pressed {
        background-color: #BFDBFE;
    }

    /* File List Areas */
    #fileList, #languageList {
        background-color: #F9FAFB;
        border: 1px solid #E5E7EB;
        border-radius: 6px;
        padding: 5px;
        font-size: 13px;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
            sans-serif;
        color: #374151;
        min-height: 100px;
        max-height: 120px;
    }

    #fileList:hover {
        border: 2px dashed #2563EB;
        background-color: #F0F7FF;
    }  

    #fileList::item, #languageList::item {
        padding: 8px;
        border-radius: 4px;
        margin: 2px;
    }

    #fileList::item:selected, #languageList::item:selected {
        background-color: #DBEAFE;
        color: #1E293B;
    }

    #fileList::item:hover, #languageList::item:hover {
        background-color: #EFF6FF;
    }

    /* Language Checkboxes */
    #languageCheckbox {
        font-size: 13px;
        color: #374151;
        spacing: 8px;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
            sans-serif;
    }

    #languageCheckbox::indicator {
        width: 16px;
        height: 16px;
    }

    #languageCheckbox::indicator:unchecked {
        border: 2px solid #D1D5DB;
        border-radius: 3px;
        background-color: white;
    }

    #languageCheckbox::indicator:checked {
        border: 2px solid #2563EB;
        border-radius: 3px;
        background-color: #2563EB;
    }

    #languageCheckbox::indicator:hover {
        border-color: #2563EB;
    }

    /* Progress Bar */
    #progressBar {
        border: 1px solid #E5E7EB;
        border-radius: 6px;
        text-align: center;
        background-color: #F9FAFB;
        height: 20px;
    }

    #progressBar::chunk {
        background-color: #2563EB;
        border-radius: 5px;
    }

    /* Log Output */
    #logOutput {
        background-color: #F9FAFB;
        border: 1px solid #E5E7EB;
        border-radius: 6px;
        padding: 10px;
        font-family: "Consolas", "Monaco", "Courier New", monospace;
        font-size: 12px;
        color: #374151;
        min-height: 80px;
    }

    /* Status Labels */
    #statusLabel {
        font-size: 12px;
        color: #6B7280;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
            sans-serif;
    }

    #statusIcon {
        font-size: 14px;
        font-weight: bold;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
            sans-serif;
    }

    #apiStatusText {
        font-size: 12px;
        font-weight: 500;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
            sans-serif;
    }

    #fileCountLabel, #languageCountLabel {
        font-size: 12px;
        color: #6B7280;
        font-style: italic;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
            sans-serif;
    }

    /* AI Configuration Section */
    #aiConfigSection {
        background-color: #EFF6FF;
        border: 1px solid #DBEAFE;
        border-radius: 6px;
    }

    #aiTermsDisplay, #termbaseDisplay {
        background-color: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 6px;
        padding: 8px;
        font-family: "Consolas", "Monaco", "Courier New", monospace;
        font-size: 12px;
        color: #374151;
    }

    /* Success/Error Colors */
    .success {
        color: #065F46;
    }

    .error {
        color: #DC2626;
    }

    /* Scroll Areas */
    QScrollArea {
        border: none;
        background-color: transparent;
    }

    QScrollBar:vertical {
        background-color: #F3F4F6;
        width: 12px;
        border-radius: 6px;
    }

    QScrollBar::handle:vertical {
        background-color: #D1D5DB;
        border-radius: 6px;
        min-height: 20px;
    }

    QScrollBar::handle:vertical:hover {
        background-color: #9CA3AF;
    }

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
    
    /* Tone radio buttons */
    QRadioButton {
        color: #111827;          
        font-size: 13px;
        spacing: 6px;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    
    QRadioButton::indicator {
        width: 14px;
        height: 14px;
    }
    
    
    /* Generation Model Dropdown */
    QComboBox {
        color: #374151;
        background-color: #FFFFFF;
        border: 1px solid #000000;    /* changed to black */
        border-radius: 6px;
        padding: 4px 8px;
        font-size: 13px;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        min-width: 160px;
    }

    QComboBox::drop-down {
        border: none;
        width: 20px;
    }

    QComboBox QAbstractItemView {
        color: #374151;
        background-color: #FFFFFF;
        border: 1px solid #D1D5DB;
        selection-background-color: #DBEAFE;
        selection-color: #1E293B;
        font-size: 13px;
    }
    
    #translationSection {
        background-color: #FFFFFF;
        border-radius: 14px;
        padding: 20px;
        border: 1px solid #E5E7EB;
   }
   
   
   #languageCheckbox {
        background-color: #F3F4F6;
        border-radius: 10px;
        padding: 10px;
    }
    
    #languageCheckbox:hover {
        background-color: #E5E7EB;
    }
    
    #languageCheckbox:checked {
        background-color: #DBEAFE;
        border: 1px solid #2563EB;
    }
    
    #secondaryButton {
        background-color: #FFFFFF;
        color: #2563EB;
        border: 1px solid #2563EB;
        border-radius: 10px;
        padding: 10px;
    }
    
    #secondaryButton:hover {
        background-color: #EFF6FF;
    }
    
    #header {
        background-color: #2563EB;
        padding: 18px;
        font-size: 20px;
        font-weight: 700;
        color: white;
    }
"""
