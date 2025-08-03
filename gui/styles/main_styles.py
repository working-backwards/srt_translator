"""
Main Application Styles
Contains all CSS styling for the SRT Translator GUI
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
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    
    /* Main Content Container */
    #contentContainer {
        background-color: #FFFFFF;
        border-radius: 8px;
        border: 1px solid #E5E7EB;
        margin: 10px;
    }
    
    /* Section Headers */
    QGroupBox {
        font-size: 16px;
        font-weight: 600;
        color: #1E293B;
        border: 1px solid #E5E7EB;
        border-radius: 6px;
        margin-top: 10px;
        padding-top: 10px;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 5px 0 5px;
        color: #1E293B;
        font-size: 16px;
        font-weight: 600;
    }
    
    /* Sub-headers */
    #subHeaderLabel {
        font-size: 14px;
        font-weight: 600;
        color: #374151;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    
    /* Body Text */
    QLabel {
        color: #374151;
        font-size: 13px;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    
    /* Input Fields */
    #apiKeyInput, #searchInput {
        background-color: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 6px;
        padding: 8px 12px;
        font-size: 13px;
        height: 40px;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
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
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    
    #mainActionButton {
        height: 50px;
        font-size: 14px;
        font-weight: 600;
    }
    
    #primaryButton:hover, #mainActionButton:hover {
        background-color: #1D4ED8;
    }
    
    #primaryButton:pressed, #mainActionButton:pressed {
        background-color: #1E40AF;
    }
    
    /* Secondary Buttons */
    #secondaryButton {
        background-color: #F3F4F6;
        color: #374151;
        border: 1px solid #D1D5DB;
        border-radius: 6px;
        padding: 8px 16px;
        font-size: 13px;
        font-weight: 500;
        height: 36px;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    
    #secondaryButton:hover {
        background-color: #E5E7EB;
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
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
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
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
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
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        color: #374151;
        min-height: 100px;
        max-height: 120px;
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
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
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
    
    #fileCountLabel, #languageCountLabel {
        font-size: 12px;
        color: #6B7280;
        font-style: italic;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
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
"""
