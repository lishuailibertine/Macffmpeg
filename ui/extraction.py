import os
import shutil
from whisper import _MODELS as WHISPER_MODELS
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QPushButton, QFileDialog, QTextEdit, QProgressBar, 
    QMessageBox, QGroupBox
)
from PyQt6.QtCore import Qt
from worker import Worker

class ExtractionPage(QWidget):
    def __init__(self):
        super().__init__()
        self.result_data = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Title
        title = QLabel("Video Subtitle Extractor")
        title.setObjectName("header")
        layout.addWidget(title)

        # --- Extraction Control ---
        extract_group = QGroupBox("Extraction Task")
        extract_layout = QVBoxLayout()
        
        # Row 1: File & Model Selection
        row1 = QHBoxLayout()
        
        self.file_path_label = QLabel("No file selected")
        self.file_path_label.setStyleSheet("color: #888; font-style: italic;")
        browse_btn = QPushButton("Select Video File")
        browse_btn.clicked.connect(self.browse_file)
        
        row1.addWidget(browse_btn)
        row1.addWidget(self.file_path_label)
        row1.addStretch()
        
        row1.addWidget(QLabel("Use Model:"))
        self.extract_model_combo = QComboBox()
        self.extract_model_combo.addItems(list(WHISPER_MODELS.keys()))
        # Set default to 'base' if possible
        idx = self.extract_model_combo.findText("base")
        if idx >= 0: self.extract_model_combo.setCurrentIndex(idx)
            
        row1.addWidget(self.extract_model_combo)
        
        extract_layout.addLayout(row1)
        
        # Row 2: Action
        self.extract_btn = QPushButton("Start Extraction")
        self.extract_btn.setObjectName("primaryButton")
        self.extract_btn.clicked.connect(self.start_extraction)
        self.extract_btn.setEnabled(False)
        extract_layout.addWidget(self.extract_btn)
        
        extract_group.setLayout(extract_layout)
        layout.addWidget(extract_group)

        # Progress & Logs
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText("Logs will appear here...")
        layout.addWidget(self.log_output, stretch=1)

        # Save Buttons
        save_layout = QHBoxLayout()
        self.save_srt_btn = QPushButton("Save as .SRT")
        self.save_txt_btn = QPushButton("Save as .TXT")
        self.save_srt_btn.clicked.connect(lambda: self.save_file('srt'))
        self.save_txt_btn.clicked.connect(lambda: self.save_file('txt'))
        self.save_srt_btn.setEnabled(False)
        self.save_txt_btn.setEnabled(False)
        
        save_layout.addWidget(self.save_srt_btn)
        save_layout.addWidget(self.save_txt_btn)
        layout.addLayout(save_layout)

    def browse_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Select Video File", "", "Video Files (*.mp4 *.mkv *.mov *.avi *.mp3 *.wav);;All Files (*)")
        if file_name:
            self.file_path = file_name
            self.file_path_label.setText(os.path.basename(file_name))
            self.extract_btn.setEnabled(True)
            self.log_output.append(f"Selected file: {file_name}")

    def start_extraction(self):
        if not hasattr(self, 'file_path'):
            return
        model_name = self.extract_model_combo.currentText()
        self.start_worker('transcribe', model_name, self.file_path)

    def start_worker(self, task_type, model_name, file_path=None):
        self.set_ui_busy(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        
        self.worker = Worker(task_type, model_name, file_path)
        self.worker.log.connect(self.log_output.append)
        self.worker.error.connect(self.handle_error)
        self.worker.finished.connect(self.handle_finished)
        self.worker.start()

    def set_ui_busy(self, busy):
        self.extract_btn.setEnabled(not busy)
        self.extract_model_combo.setEnabled(not busy)
        
        if busy:
            self.save_srt_btn.setEnabled(False)
            self.save_txt_btn.setEnabled(False)

    def handle_error(self, error_msg):
        self.set_ui_busy(False)
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Error", f"An error occurred:\n{error_msg}")
        self.log_output.append(f"Error: {error_msg}")

    def handle_finished(self, result):
        self.set_ui_busy(False)
        self.progress_bar.setVisible(False)
        
        if result:
            self.result_data = result
            self.save_srt_btn.setEnabled(True)
            self.save_txt_btn.setEnabled(True)
            self.log_output.append("\n--- Extraction Complete! ---\n")
            QMessageBox.information(self, "Success", "Subtitle extraction completed successfully!")

    def save_file(self, format_type):
        if not self.result_data:
            return

        default_name = os.path.splitext(os.path.basename(self.file_path))[0]
        if format_type == 'srt':
            file_name, _ = QFileDialog.getSaveFileName(self, "Save SRT", f"{default_name}.srt", "SubRip Subtitle (*.srt)")
            if file_name:
                self.write_srt(self.result_data['segments'], file_name)
        elif format_type == 'txt':
            file_name, _ = QFileDialog.getSaveFileName(self, "Save Text", f"{default_name}.txt", "Text File (*.txt)")
            if file_name:
                with open(file_name, 'w', encoding='utf-8') as f:
                    f.write(self.result_data['text'])
        
        if file_name:
            self.log_output.append(f"Saved to: {file_name}")

    def write_srt(self, segments, file_name):
        def format_time(seconds):
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            millis = int((seconds - int(seconds)) * 1000)
            return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"

        with open(file_name, 'w', encoding='utf-8') as f:
            for i, segment in enumerate(segments, start=1):
                start = format_time(segment['start'])
                end = format_time(segment['end'])
                text = segment['text'].strip()
                f.write(f"{i}\n{start} --> {end}\n{text}\n\n")
