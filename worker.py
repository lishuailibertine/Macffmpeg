import os
import whisper
import requests # Added
from PyQt6.QtCore import QThread, pyqtSignal

WHISPER_CACHE_DIR = os.path.expanduser("~/.cache/whisper")

class Worker(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    log = pyqtSignal(str)

    def __init__(self, task_type, model_name, file_path=None, download_url=None):
        super().__init__()
        self.task_type = task_type # 'download', 'transcribe', or 'download_custom'
        self.model_name = model_name
        self.file_path = file_path
        self.download_url = download_url

    def run(self):
        try:
            if self.task_type == 'download':
                self.log.emit(f"Downloading standard model '{self.model_name}'...")
                # This triggers the standard whisper download
                whisper.load_model(self.model_name)
                self.log.emit(f"Model '{self.model_name}' is ready.")
                self.finished.emit(None)

            elif self.task_type == 'download_custom':
                if not self.download_url:
                    raise ValueError("No URL provided for custom download.")
                
                self.log.emit(f"Connecting to {self.download_url}...")
                
                if not os.path.exists(WHISPER_CACHE_DIR):
                    os.makedirs(WHISPER_CACHE_DIR)
                
                target_path = os.path.join(WHISPER_CACHE_DIR, self.model_name)
                
                response = requests.get(self.download_url, stream=True)
                response.raise_for_status()
                
                total_size = int(response.headers.get('content-length', 0))
                downloaded_size = 0
                
                with open(target_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded_size += len(chunk)
                            # Log progress periodically (e.g. every 5MB to avoid spam)
                            if total_size > 0:
                                percent = int((downloaded_size / total_size) * 100)
                                if percent % 10 == 0 and percent > 0:
                                     # Simple dedup logic or just emit - UI log usually appends
                                     pass 
                
                self.log.emit(f"Custom model '{self.model_name}' downloaded successfully ({downloaded_size/1024/1024:.1f} MB).")
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
