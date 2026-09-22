"""Main window for MarkItDown GUI."""

import sys
from pathlib import Path
from typing import List, Optional

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QFileDialog, QGroupBox, QCheckBox, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from core.converter import OCR_AVAILABLE
from gui.progress_dialog import ProgressDialog


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MarkItDown GUI")
        self.setMinimumSize(600, 400)
        
        # Default output directory
        self.default_output = Path.home() / "Documents" / "Markitdown"
        self.default_output.mkdir(parents=True, exist_ok=True)
        
        self.setup_ui()
    
    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("MarkItDown - Convertisseur de documents")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Input selection group
        input_group = QGroupBox("Sélection des fichiers à convertir")
        input_layout = QVBoxLayout(input_group)
        
        # File button
        file_layout = QHBoxLayout()
        self.file_btn = QPushButton("📄 Sélectionner un fichier")
        self.file_btn.setMinimumHeight(40)
        self.file_btn.clicked.connect(self.select_file)
        file_layout.addWidget(self.file_btn)
        
        self.file_label = QLabel("Aucun fichier sélectionné")
        self.file_label.setWordWrap(True)
        self.file_label.setStyleSheet("color: gray;")
        file_layout.addWidget(self.file_label, 1)
        input_layout.addLayout(file_layout)
        
        # Folder button
        folder_layout = QHBoxLayout()
        self.folder_btn = QPushButton("📁 Sélectionner un dossier")
        self.folder_btn.setMinimumHeight(40)
        self.folder_btn.clicked.connect(self.select_folder)
        folder_layout.addWidget(self.folder_btn)
        
        self.folder_label = QLabel("Aucun dossier sélectionné")
        self.folder_label.setWordWrap(True)
        self.folder_label.setStyleSheet("color: gray;")
        folder_layout.addWidget(self.folder_label, 1)
        input_layout.addLayout(folder_layout)
        
        # Recursive checkbox
        self.recursive_check = QCheckBox("Inclure les sous-dossiers (récursif)")
        self.recursive_check.setChecked(True)
        input_layout.addWidget(self.recursive_check)
        
        # OCR checkbox
        self.ocr_check = QCheckBox("Activer l'OCR pour les images (Tesseract)")
        self.ocr_check.setChecked(False)
        self.ocr_check.setEnabled(OCR_AVAILABLE)
        if not OCR_AVAILABLE:
            self.ocr_check.setToolTip("Installez pytesseract et Tesseract-OCR pour activer cette option")
        input_layout.addWidget(self.ocr_check)
        
        layout.addWidget(input_group)
        
        # Output directory group
        output_group = QGroupBox("Dossier de sortie")
        output_layout = QHBoxLayout(output_group)
        
        self.output_edit = QLineEdit(str(self.default_output))
        self.output_edit.setReadOnly(True)
        output_layout.addWidget(self.output_edit)
        
        self.output_btn = QPushButton("Changer")
        self.output_btn.clicked.connect(self.select_output_dir)
        output_layout.addWidget(self.output_btn)
        
        layout.addWidget(output_group)
        
        # Supported formats info
        ocr_status = "✓ OCR disponible (Tesseract)" if OCR_AVAILABLE else "✗ OCR non disponible (installez pytesseract + Tesseract-OCR)"
        formats_label = QLabel(
            f"Formats supportés: PDF, Word (.docx, .doc), Images (.jpg, .jpeg, .png, .bmp, .gif, .tiff, .webp)\n{ocr_status}"
        )
        formats_label.setWordWrap(True)
        formats_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(formats_label)
        
        # Convert button
        self.convert_btn = QPushButton("🚀 Lancer la conversion")
        self.convert_btn.setMinimumHeight(50)
        self.convert_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.convert_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:disabled {
                background-color: #ccc;
            }
        """)
        self.convert_btn.clicked.connect(self.start_conversion)
        layout.addWidget(self.convert_btn)
        
        # Status
        self.status_label = QLabel("Prêt")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
        # State
        self.input_paths: List[Path] = []
        self.progress_dialog: Optional[ProgressDialog] = None
    
    def select_file(self):
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        file_dialog.setNameFilter(
            "Documents supportés (*.pdf *.docx *.doc *.jpg *.jpeg *.png *.bmp *.gif *.tiff *.webp);;"
            "Tous les fichiers (*.*)"
        )
        if file_dialog.exec():
            files = file_dialog.selectedFiles()
            if files:
                self.input_paths = [Path(files[0])]
                self.file_label.setText(files[0])
                self.file_label.setStyleSheet("color: black;")
                self.folder_label.setText("Aucun dossier sélectionné")
                self.folder_label.setStyleSheet("color: gray;")
                self.update_convert_button()
    
    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Sélectionner un dossier", str(Path.home())
        )
        if folder:
            self.input_paths = [Path(folder)]
            self.folder_label.setText(folder)
            self.folder_label.setStyleSheet("color: black;")
            self.file_label.setText("Aucun fichier sélectionné")
            self.file_label.setStyleSheet("color: gray;")
            self.update_convert_button()
    
    def select_output_dir(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Sélectionner le dossier de sortie", str(self.default_output)
        )
        if folder:
            self.default_output = Path(folder)
            self.output_edit.setText(folder)
    
    def update_convert_button(self):
        self.convert_btn.setEnabled(len(self.input_paths) > 0)
    
    def start_conversion(self):
        if not self.input_paths:
            QMessageBox.warning(self, "Attention", "Veuillez sélectionner un fichier ou un dossier.")
            return
        
        output_dir = Path(self.output_edit.text())
        output_dir.mkdir(parents=True, exist_ok=True)
        
        self.convert_btn.setEnabled(False)
        self.status_label.setText("Conversion en cours...")
        
        self.progress_dialog = ProgressDialog(self)
        self.progress_dialog.start_conversion(
            self.input_paths, output_dir, self.recursive_check.isChecked(), self.ocr_check.isChecked()
        )
        self.progress_dialog.finished.connect(self.on_conversion_finished)
        self.progress_dialog.show()

    def on_conversion_finished(self):
        self.convert_btn.setEnabled(True)
        self.status_label.setText("Prêt")
        self.progress_dialog = None


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()