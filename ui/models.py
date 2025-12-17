import os
import shutil
from whisper import _MODELS as WHISPER_MODELS
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QMessageBox, 
    QGroupBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QTextEdit, QInputDialog
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

        # --- Import / Download Buttons ---
        import_layout = QHBoxLayout()
        
        # Local Import
        import_btn = QPushButton("Import Local Model (.pt)")
        import_btn.setToolTip("Import a manually downloaded Whisper model file")
        import_btn.clicked.connect(self.import_local_model)
        import_layout.addWidget(import_btn)
        
        # URL Download
        url_btn = QPushButton("Download from URL")
        url_btn.setToolTip("Download a model file from a direct URL source")
        url_btn.setStyleSheet("""
            QPushButton {
                background-color: #2da44e;
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #2c974b; }
        """)
        url_btn.clicked.connect(self.download_from_url)
        import_layout.addWidget(url_btn)

        import_layout.addStretch()
        layout.addLayout(import_layout)
        
        # --- Model List Table ---
        model_group = QGroupBox("Available Models")
        model_layout = QVBoxLayout()
        
        self.model_table = QTableWidget()
        self.model_table.setColumnCount(4)
        self.model_table.setHorizontalHeaderLabels(["Model Name", "Status", "URL / Type", "Action"])
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

    def download_from_url(self):
        url, ok = QInputDialog.getText(self, "Download Model", "Enter direct URL to .pt file:")
        if ok and url.strip():
            url = url.strip()
            
            # Cleanup filename
            # Use part after last slash, and remove query params if any
            filename = url.split("/")[-1].split("?")[0]
            
            if not filename.endswith(".pt"):
                # Try prompt user for name? For now, strict check to avoid garbage
                QMessageBox.warning(self, "Invalid URL", "The URL must point to a file with a .pt extension.")
                return

            target_path = os.path.join(WHISPER_CACHE_DIR, filename)
            
            if os.path.exists(target_path):
                overwrite = QMessageBox.question(
                    self, "File Exists", 
                    f"Model '{filename}' already exists. Overwrite?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if overwrite != QMessageBox.StandardButton.Yes:
                    return

            self.model_table.setEnabled(False)
            self.log_output.clear()
            self.log_output.append(f"Starting download from URL: {url}")
            
            # Start Worker with new task type
            self.worker = Worker('download_custom', filename, download_url=url)
            self.worker.log.connect(self.log_output.append)
            self.worker.finished.connect(self.handle_finished)
            self.worker.error.connect(self.handle_error)
            self.worker.start()

    def import_local_model(self):
        from PyQt6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Whisper Model", "", "Whisper Models (*.pt);;All Files (*)"
        )
        
        if file_path:
            try:
                if not os.path.exists(WHISPER_CACHE_DIR):
                    os.makedirs(WHISPER_CACHE_DIR)
                
                filename = os.path.basename(file_path)
                target_path = os.path.join(WHISPER_CACHE_DIR, filename)
                
                if os.path.exists(target_path):
                    overwrite = QMessageBox.question(
                        self, "File Exists", 
                        f"Model '{filename}' already exists. Overwrite?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    if overwrite != QMessageBox.StandardButton.Yes:
                        return

                shutil.copy2(file_path, target_path)
                self.log_output.append(f"Imported model: {filename}")
                QMessageBox.information(self, "Success", f"Model '{filename}' imported successfully.")
                self.refresh_model_table()
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to import model: {e}")

    def refresh_model_table(self):
        self.model_table.setRowCount(0)
        
        # 1. Standard Models
        order = ['tiny.en', 'tiny', 'base.en', 'base', 'small.en', 'small', 'medium.en', 'medium', 'large-v1', 'large-v2', 'large-v3', 'large', 'turbo']
        models = sorted(WHISPER_MODELS.keys(), key=lambda x: order.index(x) if x in order else 99)

        # Track processed filenames to identify custom ones later
        processed_filenames = set()

        for model_name in models:
            row = self.model_table.rowCount()
            self.model_table.insertRow(row)
            
            # Name
            name_item = QTableWidgetItem(model_name)
            name_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.model_table.setItem(row, 0, name_item)
            
            # Check existence
            found = False
            file_size_mb = 0
            if os.path.exists(WHISPER_CACHE_DIR):
                for f in os.listdir(WHISPER_CACHE_DIR):
                    # Whisper heuristics: starts with model name and .pt
                    # But wait, standard models usually have hash. simplify check:
                    if f.startswith(model_name) and f.endswith(".pt"):
                        found = True
                        file_size_mb = os.path.getsize(os.path.join(WHISPER_CACHE_DIR, f)) / (1024 * 1024)
                        processed_filenames.add(f)
                        break
            
            # Status
            status_text = f"✅ Present ({file_size_mb:.1f} MB)" if found else "❌ Not Downloaded"
            status_item = QTableWidgetItem(status_text)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if found:
                status_item.setForeground(Qt.GlobalColor.green)
            else:
                status_item.setForeground(Qt.GlobalColor.gray)
            self.model_table.setItem(row, 1, status_item)

            # URL
            url = WHISPER_MODELS.get(model_name, "")
            url_item = QTableWidgetItem(url)
            self.model_table.setItem(row, 2, url_item)
            
            # Action Button
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

        # 2. Custom/Local Models (Any .pt file in cache not matched above)
        if os.path.exists(WHISPER_CACHE_DIR):
            for f in os.listdir(WHISPER_CACHE_DIR):
                if f.endswith(".pt") and f not in processed_filenames:
                    # Found a custom model
                    row = self.model_table.rowCount()
                    self.model_table.insertRow(row)
                    
                    # Name (Filename)
                    name_item = QTableWidgetItem(f)
                    name_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.model_table.setItem(row, 0, name_item)
                    
                    # Status
                    size_mb = os.path.getsize(os.path.join(WHISPER_CACHE_DIR, f)) / (1024 * 1024)
                    status_item = QTableWidgetItem(f"✅ Local ({size_mb:.1f} MB)")
                    status_item.setForeground(Qt.GlobalColor.blue)
                    status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.model_table.setItem(row, 1, status_item)
                    
                    # Type
                    self.model_table.setItem(row, 2, QTableWidgetItem("Custom / Imported"))
                    
                    # Action (Delete only)
                    btn = QPushButton("Delete")
                    btn.setObjectName("deleteBtn")
                    btn.clicked.connect(lambda checked, filename=f: self.delete_custom_model(filename))
                    self.model_table.setCellWidget(row, 3, btn)

    def download_model(self, model_name):
        self.model_table.setEnabled(False)
        self.worker = Worker('download', model_name)
        self.worker.log.connect(self.log_output.append)
        self.worker.finished.connect(self.handle_finished)
        self.worker.error.connect(self.handle_error)
        self.worker.start()

    def delete_model(self, model_name):
        self._delete_file_logic(model_name, is_standard=True)

    def delete_custom_model(self, filename):
        self._delete_file_logic(filename, is_standard=False)

    def _delete_file_logic(self, identifier, is_standard=True):
        confirm = QMessageBox.question(
            self, "Confirm Delete", 
            f"Are you sure you want to delete '{identifier}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            deleted = False
            if os.path.exists(WHISPER_CACHE_DIR):
                if is_standard:
                    # Fuzzy match for standard models
                    for f in os.listdir(WHISPER_CACHE_DIR):
                        if f.startswith(identifier) and f.endswith(".pt"):
                            path = os.path.join(WHISPER_CACHE_DIR, f)
                            try:
                                os.remove(path)
                                deleted = True
                            except Exception: pass
                else:
                    # Exact match for custom files
                    path = os.path.join(WHISPER_CACHE_DIR, identifier)
                    if os.path.exists(path):
                         try:
                            os.remove(path)
                            deleted = True
                         except Exception: pass

            if deleted:
                self.log_output.append(f"Model '{identifier}' deleted.")
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
