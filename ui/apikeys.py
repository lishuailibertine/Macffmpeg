import json
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QLineEdit, QGroupBox, QMessageBox
)
from PyQt6.QtCore import Qt, QSettings

class APIKeysPage(QWidget):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("MacWhisper", "Config")
        self.init_ui()
        self.load_keys()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = QLabel("API Key Management")
        title.setObjectName("header")
        layout.addWidget(title)
        
        # --- Add New Key Section ---
        add_group = QGroupBox("Add New API Key")
        # Use simple layout for fields
        form_layout = QHBoxLayout()
        
        # Provider
        form_layout.addWidget(QLabel("Provider:"))
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["OpenAI", "DeepSeek", "Anthropic", "Custom"])
        self.provider_combo.currentTextChanged.connect(self.on_provider_changed)
        form_layout.addWidget(self.provider_combo)
        
        # Key
        form_layout.addWidget(QLabel("Key:"))
        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_input.setPlaceholderText("sk-...")
        form_layout.addWidget(self.key_input)
        
        # Model
        form_layout.addWidget(QLabel("Model:"))
        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText("gpt-3.5-turbo")
        self.model_input.setFixedWidth(120)
        form_layout.addWidget(self.model_input)
        
        # Base URL
        form_layout.addWidget(QLabel("Base URL:"))
        self.base_url_input = QLineEdit()
        self.base_url_input.setPlaceholderText("Optional")
        form_layout.addWidget(self.base_url_input)
        
        self.add_btn = QPushButton("Add")
        self.add_btn.setObjectName("primaryButton")
        self.add_btn.clicked.connect(self.add_key)
        form_layout.addWidget(self.add_btn)
        
        add_group.setLayout(form_layout)
        layout.addWidget(add_group)

        # --- Keys List ---
        self.keys_table = QTableWidget()
        self.keys_table.setColumnCount(5) # Provider, Key, Model, URL, Action
        self.keys_table.setHorizontalHeaderLabels(["Provider", "API Key (Masked)", "Default Model", "Base URL", "Action"])
        self.keys_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.keys_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.keys_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.keys_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.keys_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.keys_table.setColumnWidth(4, 80)
        self.keys_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.keys_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        
        layout.addWidget(self.keys_table)

    def on_provider_changed(self, text):
        if text == "DeepSeek":
            self.model_input.setText("deepseek-chat")
            self.base_url_input.setText("https://api.deepseek.com")
        elif text == "OpenAI":
            self.model_input.setText("gpt-3.5-turbo")
            self.base_url_input.clear()
        else:
             self.model_input.clear()
             self.base_url_input.clear()

    def load_keys(self):
        json_str = self.settings.value("api_keys_list", "[]")
        try:
            self.keys = json.loads(json_str)
        except:
            self.keys = []
        self.refresh_table()

    def refresh_table(self):
        self.keys_table.setRowCount(0)
        for i, entry in enumerate(self.keys):
            self.keys_table.insertRow(i)
            
            self.keys_table.setItem(i, 0, QTableWidgetItem(entry.get("provider", "Unknown")))
            
            # Masked key
            raw_key = entry.get("key", "")
            masked = f"{raw_key[:3]}...{raw_key[-4:]}" if len(raw_key) > 7 else "***"
            self.keys_table.setItem(i, 1, QTableWidgetItem(masked))
            
            self.keys_table.setItem(i, 2, QTableWidgetItem(entry.get("model", "")))
            self.keys_table.setItem(i, 3, QTableWidgetItem(entry.get("base_url", "")))
            
            delete_btn = QPushButton("Delete")
            delete_btn.setObjectName("deleteBtn")
            delete_btn.clicked.connect(lambda checked, idx=i: self.delete_key(idx))
            self.keys_table.setCellWidget(i, 4, delete_btn)

    def add_key(self):
        provider = self.provider_combo.currentText()
        key = self.key_input.text().strip()
        model = self.model_input.text().strip()
        base_url = self.base_url_input.text().strip()
        
        if not key:
            QMessageBox.warning(self, "Input Error", "Please enter an API Key.")
            return
            
        self.keys.append({
            "provider": provider, 
            "key": key,
            "model": model,
            "base_url": base_url
        })
        self.save_keys()
        
        self.key_input.clear()
        # Keep model args maybe? or clear?
        # self.model_input.clear() 
        self.refresh_table()

    def delete_key(self, index):
        if 0 <= index < len(self.keys):
            confirm = QMessageBox.question(
                self, "Confirm Delete", "Remove this API Key configuration?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if confirm == QMessageBox.StandardButton.Yes:
                self.keys.pop(index)
                self.save_keys()
                self.refresh_table()

    def save_keys(self):
        self.settings.setValue("api_keys_list", json.dumps(self.keys))
