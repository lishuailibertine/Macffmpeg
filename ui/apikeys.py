import json
import time
import requests
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, 
    QStackedWidget, QLineEdit, QGroupBox, QPushButton, QFormLayout, 
    QScrollArea, QFrame, QMessageBox, QCheckBox, QInputDialog,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
)
from PyQt6.QtCore import Qt, QSettings, QSize
from PyQt6.QtGui import QIcon, QFont
import time

class APIKeysPage(QWidget):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("MacWhisper", "Config")
        self.service_configs = self.load_configs()
        # Load custom services list: [{"name": "MyService", "key": "custom_myservice"}]
        self.custom_services = self.load_custom_services()
        self.init_ui()

    def load_configs(self):
        # 1. Try loading new config format
        json_str = self.settings.value("service_configs", "{}")
        new_configs = {}
        try:
            new_configs = json.loads(json_str)
        except:
            new_configs = {}

        # 2. If new config is empty, check for migration from old format
        if not new_configs:
            old_json = self.settings.value("api_keys_list", "[]")
            try:
                old_keys = json.loads(old_json)
                if old_keys:
                    print("Migrating legacy API keys...", old_keys)
                    for entry in old_keys:
                        provider = entry.get("provider", "").lower()
                        key = entry.get("key", "")
                        model = entry.get("model", "")
                        base_url = entry.get("base_url", "")
                        
                        # Map old provider names to new keys
                        service_key = provider
                        if provider == "deepseek":
                            service_key = "deepseek"
                            new_configs[service_key] = {"api_key": key, "model": model}
                        elif provider == "openai":
                            service_key = "openai"
                            new_configs[service_key] = {"api_key": key, "model": model, "base_url": base_url}
                        
                    # Save migrated config
                    self.settings.setValue("service_configs", json.dumps(new_configs))
            except Exception as e:
                print(f"Migration failed: {e}")

        return new_configs

    def load_custom_services(self):
        json_str = self.settings.value("custom_services_list", "[]")
        try:
            return json.loads(json_str)
        except:
            return []

    def save_configs(self):
        self.settings.setValue("service_configs", json.dumps(self.service_configs))
    
    def save_custom_services(self):
        self.settings.setValue("custom_services_list", json.dumps(self.custom_services))

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Left Sidebar (Service List) ---
        sidebar_container = QWidget()
        sidebar_container.setFixedWidth(220)
        sidebar_container.setObjectName("sidebar_container")
        sidebar_layout = QVBoxLayout(sidebar_container)
        sidebar_layout.setContentsMargins(10, 20, 10, 20)
        sidebar_layout.setSpacing(10)

        # Title
        sidebar_title = QLabel("翻译服务")
        sidebar_title.setStyleSheet("color: white; font-weight: bold; font-size: 14px;")
        sidebar_layout.addWidget(sidebar_title)

        # Add Custom Service Button
        self.add_btn = QPushButton("+ 添加自定义服务")
        self.add_btn.setObjectName("addServiceBtn")
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.clicked.connect(self.add_custom_service)
        sidebar_layout.addWidget(self.add_btn)

        # Service List
        self.service_list = QListWidget()
        self.service_list.setObjectName("serviceList")
        self.service_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        sidebar_layout.addWidget(self.service_list)
        
        # Add "Overview" Item FIRST
        overview_item = QListWidgetItem("  我的服务 (已配置)")
        overview_item.setData(Qt.ItemDataRole.UserRole, "overview")
        overview_item.setSizeHint(QSize(0, 40))
        # Add icon if possible, or simple text indent
        self.service_list.addItem(overview_item)

        # Defined Default Services
        self.default_services = [
            ("DeepSeek", "deepseek"),
            ("OpenAI", "openai")
        ]
        
        # Combine Default + Custom for display
        self.all_services_display = self.default_services + [(s["name"], s["key"]) for s in self.custom_services]

        for name, key in self.all_services_display:
            item = QListWidgetItem(f"  {name}")
            item.setData(Qt.ItemDataRole.UserRole, key)
            item.setSizeHint(QSize(0, 40))
            self.service_list.addItem(item)

        main_layout.addWidget(sidebar_container)

        # --- Right Content Area ---
        self.content_area = QStackedWidget()
        self.content_area.setObjectName("contentArea")
        main_layout.addWidget(self.content_area)

        # 1. Create Overview Page (Index 0)
        self.overview_page = self.create_overview_page()
        self.content_area.addWidget(self.overview_page)

        # 2. Create Service Pages
        self.init_service_pages()

        # Event Listeners
        self.service_list.currentRowChanged.connect(self.on_tab_changed)
        
        # Select Overview by default
        self.service_list.setCurrentRow(0)

        # Style matches the screenshot
        self.setStyleSheet("""
            QWidget#sidebar_container {
                background-color: #181818; 
                border-right: 1px solid #333;
            }
            QWidget#contentArea {
                background-color: #1e1e1e;
            }
            QPushButton#addServiceBtn {
                background-color: #1e2a38;
                color: #5aaaf8;
                border: 1px solid #2b3b4f;
                padding: 8px;
                border-radius: 4px;
                text-align: center;
            }
            QPushButton#addServiceBtn:hover {
                background-color: #253345;
            }
            QListWidget#serviceList {
                background-color: transparent;
                border: none;
                outline: none;
                color: #a0a0a0;
                 font-size: 13px;
            }
            QListWidget#serviceList::item {
                border-radius: 6px;
                padding-left: 5px;
                margin-bottom: 2px;
            }
            QListWidget#serviceList::item:selected {
                background-color: white;
                color: black;
                font-weight: bold;
            }
            QListWidget#serviceList::item:hover:!selected {
                background-color: #2a2a2a;
            }
            QTableWidget {
                background-color: #12161f;
                border: 1px solid #333;
                border-radius: 6px;
                gridline-color: #333;
                color: #ddd;
            }
            QHeaderView::section {
                background-color: #181818;
                padding: 5px;
                border: 1px solid #333;
                color: #aaa;
            }
        """)

    def init_service_pages(self):
        # Create pages for all current services
        for name, key in self.all_services_display:
            page = self.create_service_page(name, key)
            self.content_area.addWidget(page)

    def add_custom_service(self):
        name, ok = QInputDialog.getText(self, "添加服务", "请输入自定义服务商名称:")
        if ok and name.strip():
            # Generate a unique key
            key = f"custom_{int(time.time())}"
            
            # Save to custom list
            self.custom_services.append({"name": name, "key": key})
            self.save_custom_services()
            
            # Update UI list
            item = QListWidgetItem(f"  {name}")
            item.setData(Qt.ItemDataRole.UserRole, key)
            item.setSizeHint(QSize(0, 40))
            self.service_list.addItem(item)
            
            # Add to internal list and create page
            self.all_services_display.append((name, key))
            page = self.create_service_page(name, key)
            self.content_area.addWidget(page)
            
            # Select the new item
            self.service_list.setCurrentRow(self.service_list.count() - 1)

    def on_tab_changed(self, index):
        self.content_area.setCurrentIndex(index)
        if index == 0:
            self.refresh_overview()

    def create_overview_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        
        title = QLabel("已配置的服务")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: white; margin-bottom: 20px;")
        layout.addWidget(title)
        
        self.overview_table = QTableWidget()
        self.overview_table.setColumnCount(3)
        self.overview_table.setHorizontalHeaderLabels(["服务名称", "配置概要", "操作"])
        self.overview_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.overview_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.overview_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.overview_table.setColumnWidth(2, 100)
        self.overview_table.verticalHeader().setVisible(False)
        self.overview_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.overview_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        
        layout.addWidget(self.overview_table)
        
        self.refresh_overview()
        return page

    def refresh_overview(self):
        self.overview_table.setRowCount(0)
        
        # Helper to map key to name
        name_map = {k: n for n, k in self.all_services_display}

        for service_key, config in self.service_configs.items():
            # Check if basically configured (has at least one field set)
            if not config or not any(config.values()):
                continue
            
            row = self.overview_table.rowCount()
            self.overview_table.insertRow(row)
            
            # Name
            name = name_map.get(service_key, service_key.replace("custom_", "").capitalize())
            self.overview_table.setItem(row, 0, QTableWidgetItem(name))
            
            # Summary (Show masked key or URL)
            summary = ""
            if "api_key" in config:
                k = config["api_key"]
                summary = f"Key: {k[:3]}...{k[-4:]}" if len(k) > 7 else "***"
            elif "app_id" in config:
                summary = f"AppID: {config['app_id']}"
            elif "access_key" in config:
                summary = f"AK: {config['access_key'][:4]}..."
            elif "endpoint" in config:
                summary = f"URL: {config['endpoint']}"
            elif "base_url" in config:
                summary = f"URL: {config['base_url']}"
            
            self.overview_table.setItem(row, 1, QTableWidgetItem(summary))
            
            # Action Button
            del_btn = QPushButton("清除")
            del_btn.setStyleSheet("""
                QPushButton { background-color: #c82333; color: white; border-radius: 4px; padding: 4px; border:none;}
                QPushButton:hover { background-color: #bd2130; }
            """)
            del_btn.clicked.connect(lambda ch, k=service_key: self.clear_config(k))
            self.overview_table.setCellWidget(row, 2, del_btn)

    def clear_config(self, key):
        if QMessageBox.question(self, "确认清除", "确定要清除此服务的配置信息吗？") == QMessageBox.StandardButton.Yes:
            if key in self.service_configs:
                del self.service_configs[key]
                self.save_configs()
                self.refresh_overview()
                # Also define how to clear form fields if needed (omitted for simplicity, 
                # fields will update next time they are loaded or if we trigger a signal)

    def create_service_page(self, name, key):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # --- Header ---
        header_layout = QHBoxLayout()
        header_title = QLabel(f" {name}")  # Placeholder for Icon
        header_title.setStyleSheet("font-size: 20px; font-weight: bold; color: white;")
        header_layout.addWidget(header_title)
        
        header_layout.addStretch()
        
        test_btn = QPushButton("测试翻译")
        test_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        test_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e2a38;
                color: #ccc;
                border: 1px solid #333;
                padding: 6px 15px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #253345; color: white; }
        """)
        test_btn.clicked.connect(lambda: self.test_service(key))
        header_layout.addWidget(test_btn)
        layout.addLayout(header_layout)

        # --- Config Form Container ---
        form_container = QFrame()
        form_container.setStyleSheet("""
            QFrame {
                background-color: #12161f; 
                border: 1px solid #333;
                border-radius: 8px;
            }
             QLabel {
                color: #ccc;
                font-weight: bold;
                border: none;
            }
            QLineEdit {
                background-color: #0d1117;
                border: 1px solid #30363d;
                color: white;
                padding: 10px;
                border-radius: 6px;
                selection-background-color: #005cc5;
            }
            QLineEdit:focus {
                border: 1px solid #58a6ff;
            }
        """)
        form_layout = QVBoxLayout(form_container)
        form_layout.setContentsMargins(30, 30, 30, 30)
        form_layout.setSpacing(20)

        # Determine fields based on service key
        fields = self.get_fields_for_service(key)
        
        for field_key, field_label, is_password in fields:
            field_layout = QVBoxLayout()
            field_layout.setSpacing(8)
            
            label = QLabel(field_label)
            field_layout.addWidget(label)
            
            input_field = QLineEdit()
            if is_password:
                input_field.setEchoMode(QLineEdit.EchoMode.Password)
            
            # Load saved value
            saved_val = self.service_configs.get(key, {}).get(field_key, "")
            input_field.setText(saved_val)
            
            # Save on change
            input_field.textChanged.connect(
                lambda val, s=key, k=field_key: self.update_config(s, k, val)
            )
            
            field_layout.addWidget(input_field)
            form_layout.addLayout(field_layout)

        # Batch Size Field (Common to all, as per screenshot)
        batch_layout = QVBoxLayout()
        batch_layout.setSpacing(8)
        batch_label = QLabel("批量翻译数量*")
        batch_input = QLineEdit()
        batch_input.setPlaceholderText("18")
        batch_input.setText(self.service_configs.get(key, {}).get("batch_size", "18"))
        batch_input.textChanged.connect(
            lambda val, s=key: self.update_config(s, "batch_size", val)
        )
        # Helper text
        helper_label = QLabel("批量翻译数量是每次翻译的句子数量。如果数量过大，可能会导致翻译失败。")
        helper_label.setStyleSheet("color: #666; font-size: 11px; font-weight: normal; border: none;")
        
        batch_layout.addWidget(batch_label)
        batch_layout.addWidget(batch_input)
        batch_layout.addWidget(helper_label)
        
        form_layout.addLayout(batch_layout)

        # Explicit Save Button (Optional but reassuring)
        save_btn_layout = QHBoxLayout()
        save_btn_layout.addStretch()
        start_save_btn = QPushButton("保存配置")
        start_save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        start_save_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #218838; }
        """)
        start_save_btn.clicked.connect(self.save_configs_manual)
        save_btn_layout.addWidget(start_save_btn)
        
        form_layout.addLayout(save_btn_layout)
        
        layout.addWidget(form_container)
        layout.addStretch()

        return page

    def save_configs_manual(self):
        self.save_configs()
        QMessageBox.information(self, "保存成功", "配置已保存！")

    def test_service(self, key):
        config = self.service_configs.get(key, {})
        if not config:
            QMessageBox.warning(self, "错误", "请先填写配置信息！")
            return

        # Ensure we check the correct keys for generic OpenAI/DeepSeek types
        api_key = config.get("api_key", "")
        base_url = config.get("base_url", "")
        model = config.get("model", "gpt-3.5-turbo")

        if key == "deepseek":
            if not base_url: base_url = "https://api.deepseek.com"
        
        if not api_key:
             QMessageBox.warning(self, "错误", "缺少 API Key！")
             return

        # Generic OpenAI-compatible test
        try:
            # Clean up base URL
            url = base_url.rstrip('/')
            if not url:
                url = "https://api.openai.com/v1"  # Default fallback
            elif not url.endswith("/v1"):
                url += "/v1"
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": model,
                "messages": [{"role": "user", "content": "Hello, translate this word to Chinese: Testing."}],
                "max_tokens": 10
            }
            
            QMessageBox.information(self, "测试中", f"正在连接服务器测试...\nURL: {url}/chat/completions")
            
            response = requests.post(f"{url}/chat/completions", headers=headers, json=data, timeout=10)
            
            if response.status_code == 200:
                res_json = response.json()
                content = res_json['choices'][0]['message']['content']
                QMessageBox.information(self, "测试成功", f"连接成功！\n服务器返回: {content}")
            else:
                 QMessageBox.critical(self, "测试失败", f"HTTP错误: {response.status_code}\n{response.text}")

        except Exception as e:
            QMessageBox.critical(self, "测试出错", f"发生异常: {str(e)}")

    def get_fields_for_service(self, key):
        # Return list of (config_key, Label, IsPassword)
        common_fields = {
            "baidu": [("app_id", "APP ID*", False), ("secret_key", "Secret Key*", True)],
            "aliyun": [("access_key_id", "AccessKey ID*", False), ("access_key_secret", "AccessKey Secret*", True)],
            "volcengine": [("access_key", "Access Key*", False), ("secret_key", "Secret Key*", True)],
            "deeplx": [("endpoint", "DeepLX Endpoint*", False), ("token", "Token (Optional)", True)],
            "deepseek": [("api_key", "API Key*", True), ("model", "Model*", False)],
            "openai": [("api_key", "API Key*", True), ("base_url", "Base URL (Optional)", False), ("model", "Model*", False)],
        }
        
        # Default fallback (and for Custom services) -> OpenAI compatible fields
        return common_fields.get(key, [
            ("api_key", "API Key*", True), 
            ("base_url", "Base URL*", False), 
            ("model", "Model*", False)
        ])

    def update_config(self, service_key, field_key, value):
        if service_key not in self.service_configs:
            self.service_configs[service_key] = {}
        self.service_configs[service_key][field_key] = value
        self.settings.sync()  # Force save to disk
        self.save_configs()
