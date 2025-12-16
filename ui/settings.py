from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QComboBox, 
    QPushButton, QFormLayout, QSpinBox, QMessageBox
)
from PyQt6.QtCore import Qt, QSettings, pyqtSignal

class SettingsPage(QWidget):
    # Signal to notify main window to update styles
    style_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.settings = QSettings("MacWhisper", "Config")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title = QLabel("App Settings")
        title.setObjectName("header")
        layout.addWidget(title)

        form_layout = QFormLayout()
        
        # Theme
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light"])
        current_theme = self.settings.value("app_theme", "Dark")
        self.theme_combo.setCurrentText(current_theme)
        form_layout.addRow("Theme:", self.theme_combo)
        
        # Font Size
        self.font_spin = QSpinBox()
        self.font_spin.setRange(10, 24)
        current_font = int(self.settings.value("app_font_size", 14))
        self.font_spin.setValue(current_font)
        form_layout.addRow("Font Size:", self.font_spin)

        layout.addLayout(form_layout)

        save_btn = QPushButton("Apply & Save")
        save_btn.setObjectName("primaryButton")
        save_btn.setFixedWidth(150)
        save_btn.clicked.connect(self.save_settings)
        layout.addWidget(save_btn)

    def save_settings(self):
        theme = self.theme_combo.currentText()
        font_size = self.font_spin.value()
        
        self.settings.setValue("app_theme", theme)
        self.settings.setValue("app_font_size", font_size)
        
        self.style_changed.emit()
        QMessageBox.information(self, "Settings Saved", "Application appearance updated.")
