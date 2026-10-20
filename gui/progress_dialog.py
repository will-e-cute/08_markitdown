"""Progress dialog for MarkItDown conversion."""

import os
from pathlib import Path
from typing import List, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QProgressBar, QLabel,
    QTextEdit, QPushButton, QMessageBox, QApplication
)
from PySide6.QtCore import Qt, Signal, QUrl
from PySide6.QtGui import QFont, QDesktopServices, QCloseEvent

from core.converter import ConversionWorker
from gui.markdown_viewer import MarkdownViewerDialog


class ProgressDialog(QDialog):
    """Modal dialog displaying conversion progress with logs and post-conversion actions."""
    
    finished = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Conversion en cours...")
        self.resize(600, 380)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)
        
        # Current status label
        self.status_label = QLabel("Préparation...")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        
        # Detailed log area
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setFont(QFont("Consolas", 9))
        layout.addWidget(self.log_area)
        
        # Bottom controls
        bottom_layout = QHBoxLayout()
        
        # Log copy button
        self.copy_log_btn = QPushButton("📋 Copier le journal")
        self.copy_log_btn.clicked.connect(self.copy_log)
        bottom_layout.addWidget(self.copy_log_btn)
        
        # Open output folder button
        self.open_folder_btn = QPushButton("📂 Ouvrir le dossier")
        self.open_folder_btn.setEnabled(False)
        self.open_folder_btn.clicked.connect(self.open_output_dir)
        bottom_layout.addWidget(self.open_folder_btn)
        
        # Preview generated markdown button
        self.preview_btn = QPushButton("👁️ Aperçu Markdown")
        self.preview_btn.setEnabled(False)
        self.preview_btn.clicked.connect(self.show_markdown_preview)
        bottom_layout.addWidget(self.preview_btn)
        
        bottom_layout.addStretch()
        
        # Cancel / Close action button
        self.action_btn = QPushButton("Annuler")
        self.action_btn.clicked.connect(self.on_action_clicked)
        bottom_layout.addWidget(self.action_btn)
        
        layout.addLayout(bottom_layout)
        
        self.worker: Optional[ConversionWorker] = None
        self.output_dir: Optional[Path] = None
        self.converted_files: List[Path] = []
        self.is_converting = False
        self.was_cancelled = False
    
    def start_conversion(
        self,
        input_paths: List[Path],
        output_dir: Path,
        recursive: bool = True,
        preserve_structure: bool = False,
        use_ocr: bool = False,
        ocr_lang: Optional[str] = None,
        custom_tesseract_cmd: Optional[str] = None,
    ):
        """Configure and start the conversion worker thread."""
        self.output_dir = Path(output_dir)
        self.converted_files = []
        self.is_converting = True
        self.was_cancelled = False
        
        self.log_area.clear()
        self.progress_bar.setValue(0)
        self.status_label.setText("Scan des fichiers à convertir...")
        self.action_btn.setText("Annuler")
        self.action_btn.setEnabled(True)
        self.open_folder_btn.setEnabled(False)
        self.preview_btn.setEnabled(False)
        
        self.worker = ConversionWorker(
            input_paths=input_paths,
            output_dir=self.output_dir,
            recursive=recursive,
            preserve_structure=preserve_structure,
            use_ocr=use_ocr,
            ocr_lang=ocr_lang,
            custom_tesseract_cmd=custom_tesseract_cmd,
        )
        self.worker.progress_updated.connect(self.on_progress)
        self.worker.file_completed.connect(self.on_file_completed)
        self.worker.finished_all.connect(self.on_finished)
        self.worker.conversion_cancelled.connect(self.on_cancelled)
        self.worker.converted_files_ready.connect(self.on_files_ready)
        self.worker.start()

    def on_progress(self, percent: int, current_file: str):
        self.progress_bar.setValue(percent)
        self.status_label.setText(f"Traitement : {current_file}")

    def on_file_completed(self, file_path: str, success: bool, message: str):
        status_icon = "✓" if success else "✗"
        fname = Path(file_path).name
        self.log_area.append(f"{status_icon} {fname}: {message}")
        # Scroll to latest entry
        sb = self.log_area.verticalScrollBar()
        sb.setValue(sb.maximum())

    def on_files_ready(self, files: list):
        self.converted_files = [Path(f) for f in files]
        if self.converted_files:
            self.preview_btn.setEnabled(True)

    def on_finished(self, success_count: int, total_count: int):
        self.is_converting = False
        self.progress_bar.setValue(100)
        self.action_btn.setText("Fermer")
        self.open_folder_btn.setEnabled(True)
        
        if total_count == 0:
            self.status_label.setText("Aucun fichier compatible trouvé à convertir.")
        else:
            self.status_label.setText(
                f"Terminé : {success_count}/{total_count} fichier(s) converti(s) avec succès."
            )
            if success_count < total_count:
                QMessageBox.warning(
                    self,
                    "Conversion terminée avec des erreurs",
                    f"{success_count}/{total_count} fichier(s) converti(s).\n"
                    f"{total_count - success_count} échec(s). Consultez le journal ci-dessous pour plus de détails."
                )
        self.finished.emit()

    def on_cancelled(self, success_count: int, total_count: int):
        self.is_converting = False
        self.was_cancelled = True
        self.action_btn.setText("Fermer")
        self.open_folder_btn.setEnabled(True)
        self.status_label.setText(
            f"Conversion annulée : {success_count}/{total_count} fichier(s) converti(s) avant l'arrêt."
        )
        self.log_area.append("\n⚠️ Conversion interrompue par l'utilisateur.")
        self.finished.emit()

    def on_action_clicked(self):
        if self.is_converting and self.worker and self.worker.isRunning():
            self.cancel_conversion()
        else:
            self.accept()

    def cancel_conversion(self):
        if self.worker and self.worker.isRunning():
            self.action_btn.setEnabled(False)
            self.status_label.setText("Annulation en cours...")
            self.worker.cancel()

    def copy_log(self):
        QApplication.clipboard().setText(self.log_area.toPlainText())
        self.copy_log_btn.setText("✓ Journal copié !")

    def open_output_dir(self):
        if self.output_dir and self.output_dir.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.output_dir)))

    def show_markdown_preview(self):
        if self.converted_files:
            dlg = MarkdownViewerDialog(self.converted_files, parent=self)
            dlg.exec()

    def closeEvent(self, event: QCloseEvent):
        if self.is_converting and self.worker and self.worker.isRunning():
            res = QMessageBox.question(
                self,
                "Interrompre la conversion ?",
                "Une conversion est en cours d'exécution. Voulez-vous l'annuler et fermer ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if res == QMessageBox.StandardButton.Yes:
                self.cancel_conversion()
                self.worker.wait(3000)
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()