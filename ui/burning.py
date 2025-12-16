from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFileDialog, QProgressBar, 
    QMessageBox, QGroupBox, QSpinBox, QColorDialog, QLineEdit,
    QFontComboBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QFont
import signal
import os
import subprocess
import shutil
import tempfile

class BurningWorker(QThread):
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, video_path, subtitle_path, output_path, font_size, font_color, font_family):
        super().__init__()
        self.video_path = video_path
        self.subtitle_path = subtitle_path
        self.output_path = output_path
        self.font_size = font_size
        self.font_color = font_color # QColor object
        self.font_family = font_family
        self.is_running = True

    def run(self):
        try:
            self.log.emit("Starting subtitle burning...")
            
            # Convert color to FFmpeg format: &HBBGGRR&
            ffmpeg_color = f"&H{self.font_color.blue():02X}{self.font_color.green():02X}{self.font_color.red():02X}&"
            
            # Escape paths for FFmpeg filter
            srt_path_escaped = self.subtitle_path.replace(":", "\\:").replace("'", "'\\''")
            
            # Escape font name for FFmpeg/libass
            # We strictly escape spaces and colons which are special in filter strings
            font_family_safe = self.font_family.replace(":", "\\:").replace("'", "")
            
            # Construct Filter string
            # We strictly quote the FontName value to handle spaces correctly in libass style string
            # Enclose the whole style value in a way that respects the outer quoting
            style = f"FontName={font_family_safe},FontSize={self.font_size},PrimaryColour={ffmpeg_color},Alignment=2,Outline=1,Shadow=1"
            
            # Use strict quoting for the force_style option
            vf_string = f"subtitles='{srt_path_escaped}':force_style='{style}'"
            
            self.log.emit(f"Using Font: {self.font_family}")
            
            cmd = [
                "ffmpeg",
                "-y", # Overwrite output
                "-i", self.video_path,
                "-vf", vf_string,
                "-c:v", "h264_videotoolbox", # HW encoder
                "-b:v", "6000k",
                "-pix_fmt", "yuv420p", # Essential for compatibility
                "-c:a", "aac", # Re-encode audio to AAC to ensure container compatibility
                self.output_path
            ]
            
            self.log.emit(f"Executing FFmpeg command: {' '.join(cmd)}")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            
            # Monitor process
            self.process = process
            for line in process.stdout:
                if not self.is_running:
                    # Kill gracefully then forceful
                    process.terminate()
                    try:
                        process.wait(timeout=1)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    self.log.emit("Process stopped by user.")
                    return # Exit run()

                if "frame=" in line or "time=" in line:
                    self.log.emit(line.strip())
                
            ret_code = process.wait()
            if ret_code == 0:
                self.finished.emit()
            elif ret_code != -15 and ret_code != -9: # != SIGTERM/SIGKILL (user stop)
                self.error.emit(f"FFmpeg finished with error code {ret_code}")

        except Exception as e:
            if self.is_running: # Only emit error if not manually stopped
                self.error.emit(str(e))

    def stop(self):
        self.is_running = False
        # If waiting on IO, we might need to kill from here too if thread is blocked
        if hasattr(self, 'process') and self.process.poll() is None:
             self.process.terminate()

class SubtitleBurningPage(QWidget):
    def __init__(self):
        super().__init__()
        self.font_color = QColor(255, 255, 255) # Default White
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = QLabel("Burn Subtitles to Video")
        title.setObjectName("header")
        layout.addWidget(title)

        # --- Inputs ---
        input_group = QGroupBox("Input Files")
        input_layout = QVBoxLayout()
        
        # Video File
        video_layout = QHBoxLayout()
        self.video_label = QLabel("No video selected")
        self.video_label.setStyleSheet("color: #888;")
        video_btn = QPushButton("Select Video")
        video_btn.clicked.connect(self.select_video)
        video_layout.addWidget(video_btn)
        video_layout.addWidget(self.video_label)
        input_layout.addLayout(video_layout)
        
        # Subtitle File
        sub_layout = QHBoxLayout()
        self.sub_label = QLabel("No subtitle selected")
        self.sub_label.setStyleSheet("color: #888;")
        sub_btn = QPushButton("Select Subtitle")
        sub_btn.clicked.connect(self.select_subtitle)
        sub_layout.addWidget(sub_btn)
        sub_layout.addWidget(self.sub_label)
        input_layout.addLayout(sub_layout)
        
        input_group.setLayout(input_layout)
        layout.addWidget(input_group)

        # --- Styling ---
        style_group = QGroupBox("Subtitle Style")
        style_layout = QHBoxLayout()
        
        # Font Family
        style_layout.addWidget(QLabel("Font:"))
        self.font_combo = QFontComboBox()
        self.font_combo.setFixedWidth(200)
        # Try to set a good default for Chinese users on Mac
        default_font = QFont("PingFang SC")
        if default_font.exactMatch():
            self.font_combo.setCurrentFont(default_font)
        else:
            # Fallback for other systems or if PingFang not found
            self.font_combo.setCurrentFont(QFont("Arial Unicode MS"))
            
        style_layout.addWidget(self.font_combo)
        
        # Font Size
        style_layout.addWidget(QLabel("Size:"))
        self.font_spin = QSpinBox()
        self.font_spin.setRange(10, 100)
        self.font_spin.setValue(24)
        style_layout.addWidget(self.font_spin)
        
        # Color
        style_layout.addWidget(QLabel("Color:"))
        self.color_sample = QLabel("   ")
        self.color_sample.setFixedSize(30, 20)
        self.color_sample.setStyleSheet(f"background-color: {self.font_color.name()}; border: 1px solid #555;")
        style_layout.addWidget(self.color_sample)
        
        color_btn = QPushButton("Pick")
        color_btn.clicked.connect(self.pick_color)
        style_layout.addWidget(color_btn)
        
        style_layout.addStretch()
        style_group.setLayout(style_layout)
        layout.addWidget(style_group)

        # --- Actions ---
        action_layout = QHBoxLayout()
        
        self.burn_btn = QPushButton("Start Burning")
        self.burn_btn.setObjectName("primaryButton")
        self.burn_btn.clicked.connect(self.start_burning)
        self.burn_btn.setEnabled(False)
        action_layout.addWidget(self.burn_btn)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.stop_burning)
        self.cancel_btn.setEnabled(False)
        action_layout.addWidget(self.cancel_btn)
        
        self.save_btn = QPushButton("Save Video")
        self.save_btn.setObjectName("downloadBtn")
        self.save_btn.clicked.connect(self.save_video)
        self.save_btn.setEnabled(False)
        action_layout.addWidget(self.save_btn)
        
        layout.addLayout(action_layout)
        
        # Progress & Status
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)
        layout.addWidget(self.progress_bar)
        
        self.log_output = QLineEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText("Ready...")
        layout.addWidget(self.log_output)

    def select_video(self):
        f, _ = QFileDialog.getOpenFileName(self, "Select Video", "", "Video Files (*.mp4 *.mov *.mkv *.avi)")
        if f:
            self.video_path = f
            self.video_label.setText(os.path.basename(f))
            self.check_ready()

    def select_subtitle(self):
        f, _ = QFileDialog.getOpenFileName(self, "Select Subtitle", "", "Subtitle Files (*.srt *.ass *.vtt)")
        if f:
            self.subtitle_path = f
            self.sub_label.setText(os.path.basename(f))
            self.check_ready()

    def check_ready(self):
        if hasattr(self, 'video_path') and hasattr(self, 'subtitle_path'):
            self.burn_btn.setEnabled(True)

    def pick_color(self):
        color = QColorDialog.getColor(self.font_color, self, "Choose Subtitle Color")
        if color.isValid():
            self.font_color = color
            self.color_sample.setStyleSheet(f"background-color: {color.name()}; border: 1px solid #555;")

    def start_burning(self):
        # Use temp dir for intermediate file
        _, ext = os.path.splitext(self.video_path)
        self.temp_output = os.path.join(tempfile.gettempdir(), f"macwhisper_burn_{os.getpid()}{ext}")
        
        self.progress_bar.setVisible(True)
        self.burn_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.save_btn.setEnabled(False)
        self.log_output.setText("Burning in progress...")
        
        font_family = self.font_combo.currentFont().family()
        
        self.worker = BurningWorker(
            self.video_path, 
            self.subtitle_path, 
            self.temp_output, 
            self.font_spin.value(),
            self.font_color,
            font_family
        )
        self.worker.log.connect(self.log_output.setText)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def stop_burning(self):
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.stop()
            self.worker.quit()
            self.log_output.setText("Stopping...")
            self.cancel_btn.setEnabled(False)
            self.burn_btn.setEnabled(True)
            self.progress_bar.setVisible(False)

    def on_finished(self):
        self.progress_bar.setVisible(False)
        self.burn_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.save_btn.setEnabled(True)
        self.log_output.setText("Processing Complete!")
        QMessageBox.information(self, "Success", "Burning complete. Click 'Save Video' to save the file.")

    def on_error(self, msg):
        self.progress_bar.setVisible(False)
        self.burn_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        QMessageBox.critical(self, "Error", f"Burning failed:\n{msg}")

    def save_video(self):
        if not hasattr(self, 'temp_output') or not os.path.exists(self.temp_output):
             return
        
        default_name = os.path.splitext(os.path.basename(self.video_path))[0] + "_subbed" + os.path.splitext(self.video_path)[1]
        target_path, _ = QFileDialog.getSaveFileName(self, "Save Video", default_name, "Video Files (*.mp4 *.mov *.mkv *.avi)")
        
        if target_path:
            try:
                shutil.copy2(self.temp_output, target_path)
                QMessageBox.information(self, "Saved", f"Video saved to:\n{target_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not save file: {e}")
