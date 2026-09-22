"""Progress dialog for MarkItDown conversion."""

from pathlib import Path
from typing import List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QProgressBar, QLabel, QTextEdit, QPushButton, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class ProgressDialog(QWidget):
    """Dialog showing conversion progress."""
    
    finished = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Dialog)
        self.setWindowTitle("Conversion en cours")
        self.setMinimumSize(500, 300)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        
        layout = QVBoxLayout(self)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Current file label
        self.current_file_label = QLabel("En attente...")
        self.current_file_label.setWordWrap(True)
        layout.addWidget(self.current_file_label)
        
        # Log area
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setFont(QFont("Consolas", 9))
        layout.addWidget(self.log_area)
        
        # Cancel button
        self.cancel_btn = QPushButton("Annuler")
        self.cancel_btn.clicked.connect(self.cancel_conversion)
        layout.addWidget(self.cancel_btn)
        
        self.worker = None
        self.success_count = 0
        self.total_count = 0
    
    def start_conversion(self, input_paths: List[Path], output_dir: Path, recursive: bool, use_ocr: bool):
        from core.converter import ConversionWorker
        
        self.log_area.clear()
        self.progress_bar.setValue(0)
        self.current_file_label.setText("Démarrage...")
        self.cancel_btn.setEnabled(True)
        
        self.worker = ConversionWorker(input_paths, output_dir, recursive, use_ocr)
        self.worker.progress_updated.connect(self.on_progress)
        self.worker.file_completed.connect(self.on_file_completed)
        self.worker.finished_all.connect(self.on_finished)
        self.worker.start()
    
    def on_progress(self, percent: int, current_file: str):
        self.progress_bar.setValue(percent)
        self.current_file_label.setText(f"Traitement: {current_file}")
    
    def on_file_completed(self, file_path: str, success: bool, message: str):
        status = "✓" if success else "✗"
        self.log_area.append(f"{status} {Path(file_path).name}: {message}")
        # Auto-scroll to bottom
        self.log_area.verticalScrollBar().setValue(
            self.log_area.verticalScrollBar().maximum()
        )
    
    def on_finished(self, success_count: int, total_count: int):
        self.success_count = success_count
        self.total_count = total_count
        self.cancel_btn.setText("Fermer")
        self.cancel_btn.clicked.disconnect()
        self.cancel_btn.clicked.connect(self.close)
        self.current_file_label.setText(
            f"Terminé: {success_count}/{total_count} fichiers convertis avec succès"
        )
        if success_count < total_count:
            QMessageBox.warning(
                self, "Conversion terminée",
                f"{success_count}/{total_count} fichiers convertis.\n"
                f"{total_count - success_count} échec(s). Consultez le journal."
            )
        self.finished.emit()
    
    def cancel_conversion(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.cancel_btn.setEnabled(False)
            self.current_file_label.setText("Annulation en cours...")