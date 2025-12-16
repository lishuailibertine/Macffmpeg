import os
import whisper
from PyQt6.QtCore import QThread, pyqtSignal

class Worker(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    log = pyqtSignal(str)

    def __init__(self, task_type, model_name, file_path=None):
        super().__init__()
        self.task_type = task_type # 'download' or 'transcribe'
        self.model_name = model_name
        self.file_path = file_path

    def run(self):
        try:
            if self.task_type == 'download':
                self.log.emit(f"Downloading model '{self.model_name}'...")
                # This triggers the download if not present
                whisper.load_model(self.model_name)
                self.log.emit(f"Model '{self.model_name}' is ready.")
                self.finished.emit(None)
            
            elif self.task_type == 'transcribe':
                self.log.emit(f"Loading model '{self.model_name}'...")
                model = whisper.load_model(self.model_name)
                
                if not self.file_path:
                    raise ValueError("No file path provided for transcription.")
                
                self.log.emit(f"Starting transcription for: {os.path.basename(self.file_path)}")
                result = model.transcribe(self.file_path)
                self.log.emit("Transcription complete.")
                self.finished.emit(result)

        except Exception as e:
            self.error.emit(str(e))
