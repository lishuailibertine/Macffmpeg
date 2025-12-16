import os
import re
import time
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QPushButton, QFileDialog, QTextEdit, QProgressBar, 
    QMessageBox, QGroupBox, QLineEdit, QSplitter, QFormLayout
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSettings
from openai import OpenAI

class TranslationWorker(QThread):
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    finished = pyqtSignal(str) # Emits the full translated content
    error = pyqtSignal(str)

    def __init__(self, api_key, file_path, target_lang, model="gpt-3.5-turbo", base_url=None):
        super().__init__()
        self.api_key = api_key
        self.file_path = file_path
        self.target_lang = target_lang
        self.model = model
        self.base_url = base_url
        self.is_running = True

    def run(self):
        try:
            self.log.emit("Starting translation...")
            
            if not self.api_key:
                raise ValueError("API Key is missing.")

            # Configure Client
            client_args = {"api_key": self.api_key}
            if self.base_url and self.base_url.strip():
                client_args["base_url"] = self.base_url.strip()
                
            client = OpenAI(**client_args)
            
            # Read file
            with open(self.file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            blocks = re.split(r'\n\s*\n', content.strip())
            
            translated_blocks = []
            total_blocks = len(blocks)
            
            batch_size = 10 
            current_batch = []
            current_batch_indices = []
            
            for i, block in enumerate(blocks):
                if not self.is_running: break
                
                lines = block.strip().split('\n')
                if len(lines) >= 3:
                    text_lines = " ".join(lines[2:])
                    current_batch.append(text_lines)
                    current_batch_indices.append(i)
                else:
                    translated_blocks.append(block)
                    continue

                if len(current_batch) >= batch_size or i == total_blocks - 1:
                    # Translate batch
                    self.log.emit(f"Translating batch {i - len(current_batch) + 2} to {i + 1}...")
                    
                    combined_text = "\n---\n".join(current_batch)
                    system_msg = f"You are a professional subtitle translator. Translate the following subtitle segments to {self.target_lang}. The segments are separated by '---'. Output ONLY the translated segments separated by '---'. Do not include original text, line numbers, or timestamps in your output, just the translated text."
                    
                    max_retries = 3
                    success = False
                    
                    for attempt in range(max_retries):
                        if not self.is_running: break
                        
                        try:
                            response = client.chat.completions.create(
                                model=self.model,
                                messages=[
                                    {"role": "system", "content": system_msg},
                                    {"role": "user", "content": combined_text}
                                ],
                                temperature=0.3
                            )
                            translated_text_combined = response.choices[0].message.content.strip()
                            translations = translated_text_combined.split('---')
                            
                            len_diff = len(current_batch) - len(translations)
                            if len_diff > 0:
                                 translations.extend(["[Error: Translation missing]"] * len_diff)
                            
                            for idx, trans_text in enumerate(translations[:len(current_batch)]):
                                original_idx_in_blocks = current_batch_indices[idx]
                                original_block_lines = blocks[original_idx_in_blocks].strip().split('\n')
                                new_block = f"{original_block_lines[0]}\n{original_block_lines[1]}\n{trans_text.strip()}"
                                translated_blocks.append(new_block)
                            
                            success = True
                            break # Success, exit retry loop

                        except Exception as e:
                            err_str = str(e)
                            
                            # Check for fatal errors causing immediate stop (No Retry)
                            if "insufficient_quota" in err_str:
                                 raise Exception("Quota exceeded (429). Please check your API billing.")
                            if "401" in err_str:
                                 raise Exception("Authentication failed (401). Check your API Key.")
                            
                            self.log.emit(f"Batch failed (Attempt {attempt+1}/{max_retries}): {err_str}")
                            
                            # Wait before retrying (backoff: 2s, 4s, etc or just fixed 2s)
                            if attempt < max_retries - 1:
                                time.sleep(2)
                    
                    if not success:
                        self.log.emit("Skipping batch after max retries.")
                        # Fallback for non-fatal errors after retries exhausted
                        for idx_in_batch in current_batch_indices:
                             translated_blocks.append(blocks[idx_in_batch])

                    current_batch = []
                    current_batch_indices = []
                    
                    progress_pct = int((i + 1) / total_blocks * 100)
                    self.progress.emit(progress_pct)

            if self.is_running:
                full_translated_srt = "\n\n".join(translated_blocks)
                self.finished.emit(full_translated_srt)
                self.log.emit("Translation completed.")
            else:
                self.log.emit("Translation stopped by user.")

        except Exception as e:
            self.error.emit(str(e))

    def stop(self):
        self.is_running = False

class TranslationPage(QWidget):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("MacWhisper", "Config")
        self.translated_content = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = QLabel("Subtitle Translator")
        title.setObjectName("header")
        layout.addWidget(title)

        # --- Controls ---
        control_group = QGroupBox("Configuration")
        control_layout = QFormLayout()

        # Files
        file_layout = QHBoxLayout()
        self.file_path_label = QLabel("No file selected")
        self.file_path_label.setStyleSheet("color: #888; font-style: italic;")
        browse_btn = QPushButton("Select .SRT File")
        browse_btn.clicked.connect(self.browse_file)
        file_layout.addWidget(browse_btn)
        file_layout.addWidget(self.file_path_label)
        control_layout.addRow("Source File:", file_layout)

        # Provider Selection
        self.provider_combo = QComboBox()
        self.provider_combo.currentIndexChanged.connect(self.update_key_tooltip)
        control_layout.addRow("API Key:", self.provider_combo)

        # Language
        self.lang_combo = QComboBox()
        self.lang_combo.addItems([
            "Simplified Chinese", "Traditional Chinese", "English", 
            "Japanese", "Korean", "Spanish", "French", "German", "Russian"
        ])
        self.lang_combo.setEditable(True)
        control_layout.addRow("Target Language:", self.lang_combo)
        
        # Advanced: Model & Base URL
        self.model_input = QLineEdit("gpt-3.5-turbo")
        self.model_input.setPlaceholderText("e.g. gpt-4, gpt-3.5-turbo, deepseek-chat")
        control_layout.addRow("Model Name:", self.model_input)
        
        self.base_url_input = QLineEdit()
        self.base_url_input.setPlaceholderText("Optional (e.g. https://api.deepseek.com/v1)")
        control_layout.addRow("Base URL:", self.base_url_input)

        control_group.setLayout(control_layout)
        layout.addWidget(control_group)

        # Action
        self.translate_btn = QPushButton("Start Translation")
        self.translate_btn.setObjectName("primaryButton")
        self.translate_btn.clicked.connect(self.start_translation)
        self.translate_btn.setEnabled(False)
        layout.addWidget(self.translate_btn)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Logs & Output
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText("Translation progress and preview will appear here...")
        layout.addWidget(self.log_output)

        # Save
        save_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save Translated SRT")
        self.save_btn.clicked.connect(self.save_file)
        self.save_btn.setEnabled(False)
        save_layout.addWidget(self.save_btn)
        layout.addLayout(save_layout)
        
        # Refresh providers on load
        self.refresh_providers()

    def refresh_providers(self):
        self.provider_combo.clear()
        import json
        keys_list_str = self.settings.value("api_keys_list", "[]")
        try:
            self.keys_list = json.loads(keys_list_str)
        except:
            self.keys_list = []
            
        for i, item in enumerate(self.keys_list):
            provider = item.get("provider", "Unknown")
            key_preview = item.get("key", "")[:4] + "..."
            # Store full item dict as userData
            self.provider_combo.addItem(f"{provider} - {key_preview}", userData=item)
            
        if not self.keys_list:
             self.provider_combo.addItem("No Keys Found (Add in API Keys Tab)")
             
        # Trigger update for initial selection
        self.update_key_tooltip()

    def update_key_tooltip(self):
        data = self.provider_combo.currentData()
        if not data or not isinstance(data, dict):
            return
            
        # Auto-fill from stored config
        model = data.get("model", "")
        base_url = data.get("base_url", "")
        
        self.model_input.setText(model)
        self.base_url_input.setText(base_url)
        
    def showEvent(self, event):
        # Refresh providers whenever tab is shown
        self.refresh_providers()
        super().showEvent(event)

    def browse_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Select Subtitle File", "", "Subtitle Files (*.srt);;All Files (*)")
        if file_name:
            self.file_path = file_name
            self.file_path_label.setText(os.path.basename(file_name))
            self.translate_btn.setEnabled(True)
            self.log_output.append(f"Selected file: {file_name}")

    def start_translation(self):
        # Get selected Data
        data = self.provider_combo.currentData()
        
        if not data or not isinstance(data, dict):
            QMessageBox.warning(self, "Missing API Key", "Please select a valid API Key from the list.")
            return

        api_key = data.get("key")

        target_lang = self.lang_combo.currentText()
        model_name = self.model_input.text().strip()
        base_url = self.base_url_input.text().strip() or None
        
        self.translate_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.log_output.clear()
        
        self.worker = TranslationWorker(api_key, self.file_path, target_lang, model=model_name, base_url=base_url)
        self.worker.log.connect(self.log_output.append)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.finished.connect(self.handle_finished)
        self.worker.error.connect(self.handle_error)
        self.worker.start()

    def handle_finished(self, content):
        self.translated_content = content
        self.translate_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.save_btn.setEnabled(True)
        self.log_output.append("\n--- Preview of Translation (Last 500 chars) ---\n")
        self.log_output.append(content[-500:])
        QMessageBox.information(self, "Success", "Translation completed successfully!")

    def handle_error(self, msg):
        self.translate_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Error", f"Translation failed: {msg}")
        self.log_output.append(f"Error: {msg}")

    def save_file(self):
        if not self.translated_content:
            return
            
        default_name = os.path.splitext(os.path.basename(self.file_path))[0] + f"_{self.lang_combo.currentText()}"
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Translated SRT", f"{default_name}.srt", "Subtitle Files (*.srt)")
        
        if file_name:
            try:
                with open(file_name, 'w', encoding='utf-8') as f:
                    f.write(self.translated_content)
                self.log_output.append(f"Saved to: {file_name}")
                QMessageBox.information(self, "Saved", "File saved successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not save file: {e}")
