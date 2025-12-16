import os
import shutil
from whisper import _MODELS as WHISPER_MODELS
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QMessageBox, 
    QGroupBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QTextEdit
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from worker import Worker

# Standard Whisper cache path
WHISPER_CACHE_DIR = os.path.expanduser("~/.cache/whisper")

class ModelsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.refresh_model_table()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Title is removed as the sidebar/header context is sufficient, or we can add a specific header
        
        # --- Model List Table ---
        model_group = QGroupBox("Available Models")
        model_layout = QVBoxLayout()
        
        self.model_table = QTableWidget()
        self.model_table.setColumnCount(4)
        self.model_table.setHorizontalHeaderLabels(["Model Name", "Status", "URL", "Action"])
        self.model_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # Name
        self.model_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents) # Status
        self.model_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch) # URL
        self.model_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed) # Action
        self.model_table.setColumnWidth(3, 120)
        self.model_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.model_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        
        model_layout.addWidget(self.model_table)
        model_group.setLayout(model_layout)
        layout.addWidget(model_group)

        # Log output for download status
        self.log_output = QTextEdit()
        self.log_output.setFixedHeight(100)
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText("Download logs will appear here...")
        layout.addWidget(self.log_output)

    def refresh_model_table(self):
        self.model_table.setRowCount(0)
        
        # Sort models: tiny, base, small, medium, large...
        order = ['tiny.en', 'tiny', 'base.en', 'base', 'small.en', 'small', 'medium.en', 'medium', 'large-v1', 'large-v2', 'large-v3', 'large', 'turbo']
        models = sorted(WHISPER_MODELS.keys(), key=lambda x: order.index(x) if x in order else 99)

        for row, model_name in enumerate(models):
            self.model_table.insertRow(row)
            
            # 1. Name
            name_item = QTableWidgetItem(model_name)
            name_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.model_table.setItem(row, 0, name_item)
            
            # Check existence
            found = False
            file_size_mb = 0
            if os.path.exists(WHISPER_CACHE_DIR):
                for f in os.listdir(WHISPER_CACHE_DIR):
                    if f.startswith(model_name) and f.endswith(".pt"):
                        found = True
                        file_size_mb = os.path.getsize(os.path.join(WHISPER_CACHE_DIR, f)) / (1024 * 1024)
                        break
            
            # 2. Status
            status_text = f"✅ Present ({file_size_mb:.1f} MB)" if found else "❌ Not Downloaded"
            status_item = QTableWidgetItem(status_text)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if found:
                status_item.setForeground(Qt.GlobalColor.green)
            else:
                status_item.setForeground(Qt.GlobalColor.gray)
            self.model_table.setItem(row, 1, status_item)

            # 3. URL
            url = WHISPER_MODELS.get(model_name, "")
            url_item = QTableWidgetItem(url)
            self.model_table.setItem(row, 2, url_item)
            
            # 4. Action Button
            btn = QPushButton()
            if found:
                btn.setText("Delete")
                btn.setObjectName("deleteBtn")
                btn.clicked.connect(lambda checked, m=model_name: self.delete_model(m))
            else:
                btn.setText("Download")
                btn.setObjectName("downloadBtn")
                btn.clicked.connect(lambda checked, m=model_name: self.download_model(m))
            
            self.model_table.setCellWidget(row, 3, btn)

    def download_model(self, model_name):
        self.model_table.setEnabled(False)
        self.worker = Worker('download', model_name)
        self.worker.log.connect(self.log_output.append)
        self.worker.finished.connect(self.handle_finished)
        self.worker.error.connect(self.handle_error)
        self.worker.start()

    def delete_model(self, model_name):
        confirm = QMessageBox.question(
            self, "Confirm Delete", 
            f"Are you sure you want to delete the '{model_name}' model?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            deleted = False
            if os.path.exists(WHISPER_CACHE_DIR):
                for f in os.listdir(WHISPER_CACHE_DIR):
                    if f.startswith(model_name) and f.endswith(".pt"):
                        path = os.path.join(WHISPER_CACHE_DIR, f)
                        try:
                            os.remove(path)
                            deleted = True
                        except Exception as e:
                            QMessageBox.warning(self, "Error", f"Could not delete: {e}")
            
            if deleted:
                self.log_output.append(f"Model '{model_name}' deleted.")
                self.refresh_model_table()
            else:
                 QMessageBox.information(self, "Info", "Model file not found to delete.")

    def handle_finished(self, result):
        self.model_table.setEnabled(True)
        self.refresh_model_table()
        QMessageBox.information(self, "Success", "Model download completed!")

    def handle_error(self, error_msg):
        self.model_table.setEnabled(True)
        self.refresh_model_table()
        QMessageBox.critical(self, "Error", f"An error occurred:\n{error_msg}")
