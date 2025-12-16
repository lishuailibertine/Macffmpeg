import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, 
    QListWidget, QStackedWidget
)
from PyQt6.QtCore import QSettings

# Import module classes
from ui.extraction import ExtractionPage
from ui.settings import SettingsPage
from ui.models import ModelsPage
from ui.translation import TranslationPage
from ui.apikeys import APIKeysPage
from ui.burning import SubtitleBurningPage

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MacWhisper - Subtitle Extractor & Translator")
        self.resize(1000, 750)
        self.settings = QSettings("MacWhisper", "Config")
        
        # Main Layout container
        main_container = QWidget()
        self.setCentralWidget(main_container)
        self.main_layout = QHBoxLayout(main_container)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Initialize UI Components
        self.init_sidebar()
        self.init_content_area()
        self.apply_styles()
        
        # Connect signals
        self.sidebar.currentRowChanged.connect(self.change_page)
        self.sidebar.setCurrentRow(0)

    def init_sidebar(self):
        # Sidebar
        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(200)
        self.sidebar.addItem("Extraction")
        self.sidebar.addItem("Translation")
        self.sidebar.addItem("Burn Subtitles")
        self.sidebar.addItem("Models")
        self.sidebar.addItem("API Keys")
        self.sidebar.addItem("Settings")
        
        self.main_layout.addWidget(self.sidebar)

    def init_content_area(self):
        self.pages = QStackedWidget()
        self.main_layout.addWidget(self.pages)
        
        # Page 1: Extraction
        self.page_extraction = ExtractionPage()
        self.pages.addWidget(self.page_extraction)
        
        # Page 2: Translation
        self.page_translation = TranslationPage()
        self.pages.addWidget(self.page_translation)
        
        # Page 3: Burn Subtitles
        self.page_burning = SubtitleBurningPage()
        self.pages.addWidget(self.page_burning)
        
        # Page 4: Models
        self.page_models = ModelsPage()
        self.pages.addWidget(self.page_models)
        
        # Page 5: API Keys
        self.page_apikeys = APIKeysPage()
        self.pages.addWidget(self.page_apikeys)
        
        # Page 6: Settings
        self.page_settings = SettingsPage()
        self.page_settings.style_changed.connect(self.apply_styles) # Re-apply styles
        self.pages.addWidget(self.page_settings)

    def change_page(self, index):
        self.pages.setCurrentIndex(index)

    def apply_styles(self):
        # Load theme/font from settings
        # This is basic. A full theme engine would be more complex.
        theme = self.settings.value("app_theme", "Dark")
        font_size = int(self.settings.value("app_font_size", 14))
        
        bg_color = "#1e1e1e"
        fg_color = "#f0f0f0"
        comp_bg = "#252526"
        comp_border = "#3e3e3e"
        
        if theme == "Light":
            bg_color = "#f5f5f5"
            fg_color = "#333333"
            comp_bg = "#ffffff"
            comp_border = "#cccccc"

        self.setStyleSheet(f"""
            QMainWindow {{ background-color: {bg_color}; }}
            QWidget {{ color: {fg_color}; font-size: {font_size}px; }}
            
            QListWidget {{
                background-color: {comp_bg};
                border: none;
                outline: none;
                font-size: {font_size + 1}px;
            }}
            QListWidget::item {{
                padding: 15px;
                color: {fg_color};
            }}
            QListWidget::item:selected {{
                background-color: #37373d;
                color: white;
                border-left: 2px solid #007bff;
            }}
            
            QGroupBox {{
                border: 1px solid {comp_border};
                border-radius: 6px;
                margin-top: 10px;
                font-weight: bold;
                padding-top: 15px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}

            QTableWidget {{
                background-color: {comp_bg};
                border: 1px solid {comp_border};
                gridline-color: {comp_border};
            }}
            QHeaderView::section {{
                background-color: {comp_bg};
                padding: 5px;
                border: 1px solid {comp_border};
                color: {fg_color};
            }}

            QLabel#header {{
                font-size: {font_size + 10}px;
                font-weight: bold;
                color: #4CAF50;
                margin-bottom: 10px;
            }}

            QLineEdit, QComboBox, QSpinBox {{
                padding: 6px;
                border: 1px solid {comp_border};
                border-radius: 4px;
                background-color: {comp_bg};
                color: {fg_color};
            }}
            
            QPushButton {{
                background-color: #007bff;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
            }}
            QPushButton:hover {{ background-color: #0069d9; }}
            QPushButton:disabled {{ background-color: #444; color: #888; }}
            
            QPushButton#primaryButton {{
                background-color: #28a745; 
                font-weight: bold;
                padding: 10px 20px;
            }}
            QPushButton#primaryButton:hover {{ background-color: #218838; }}

            QPushButton#downloadBtn {{
                background-color: #17a2b8;
            }}
            QPushButton#downloadBtn:hover {{ background-color: #138496; }}

            QPushButton#deleteBtn {{
                background-color: #dc3545;
            }}
            QPushButton#deleteBtn:hover {{ background-color: #c82333; }}

            QTextEdit {{
                background-color: {bg_color};
                border: 1px solid {comp_border};
                border-radius: 4px;
                font-family: monospace;
            }}
            QProgressBar {{
                background-color: #333;
                border-radius: 4px;
                text-align: center;
            }}
            QProgressBar::chunk {{ background-color: #4CAF50; }}
        """)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
