"""MarkItDown GUI - Convert documents to Markdown using PySide6."""

import sys
import os
from pathlib import Path
from typing import List, Optional

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QFileDialog, QProgressBar,
    QTextEdit, QMessageBox, QGroupBox, QGridLayout, QCheckBox
)
from PySide6.QtCore import Qt, QThread, Signal, QDir
from PySide6.QtGui import QFont

from markitdown import MarkItDown

# OCR support
try:
    import pytesseract
    from PIL import Image

    # Set tesseract path for Windows
    tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.exists(tesseract_path):
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


class ConversionWorker(QThread):
    """Worker thread for file conversion."""

    progress_updated = Signal(int, str)  # progress percent, current file
    file_completed = Signal(str, bool, str)  # file path, success, message
    finished_all = Signal(int, int)  # success count, total count

    def __init__(self, input_paths: List[Path], output_dir: Path, recursive: bool = True, use_ocr: bool = False):
        super().__init__()
        self.input_paths = input_paths
        self.output_dir = output_dir
        self.recursive = recursive
        self.use_ocr = use_ocr
        self._is_cancelled = False
        self.markitdown = MarkItDown()

        # Supported extensions
        self.supported_extensions = {
            '.pdf', '.docx', '.doc', '.jpg', '.jpeg', '.png',
            '.bmp', '.gif', '.tiff', '.webp'
        }
        # Image extensions for OCR
        self.image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp'}

    def cancel(self):
        self._is_cancelled = True

    def get_files_to_convert(self) -> List[Path]:
        """Get all files to convert from input paths."""
        files = []
        seen = set()
        for path in self.input_paths:
            if path.is_file():
                if path.suffix.lower() in self.supported_extensions:
                    if path not in seen:
                        files.append(path)
                        seen.add(path)
            elif path.is_dir():
                if self.recursive:
                    for ext in self.supported_extensions:
                        for f in path.rglob(f'*{ext}'):
                            if f not in seen:
                                files.append(f)
                                seen.add(f)
                        for f in path.rglob(f'*{ext.upper()}'):
                            if f not in seen:
                                files.append(f)
                                seen.add(f)
                else:
                    # Non-recursive: only files directly in the folder
                    for ext in self.supported_extensions:
                        for f in path.glob(f'*{ext}'):
                            if f not in seen:
                                files.append(f)
                                seen.add(f)
                        for f in path.glob(f'*{ext.upper()}'):
                            if f not in seen:
                                files.append(f)
                                seen.add(f)
        return files

    def convert_image_with_ocr(self, file_path: Path) -> str:
        """Convert image to text using OCR."""
        if not OCR_AVAILABLE:
            return "[OCR non disponible - installez pytesseract et Tesseract-OCR]"

        try:
            with Image.open(file_path) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                # Run OCR with French and English
                text = pytesseract.image_to_string(img, lang='fra+eng')
                return text.strip()
        except Exception as e:
            return f"[Erreur OCR: {str(e)}]"

    def run(self):
        files = self.get_files_to_convert()
        total = len(files)
        success_count = 0

        if total == 0:
            self.finished_all.emit(0, 0)
            return

        for i, file_path in enumerate(files):
            if self._is_cancelled:
                break

            progress = int((i / total) * 100)
            self.progress_updated.emit(progress, file_path.name)

            try:
                # Check if it's an image file for OCR
                if self.use_ocr and file_path.suffix.lower() in self.image_extensions:
                    # Use OCR for images
                    text_content = self.convert_image_with_ocr(file_path)
                    result_text = f"# {file_path.name}\n\n{text_content}"
                else:
                    # Use markitdown for PDF, Word, and images without OCR
                    result = self.markitdown.convert(str(file_path))
                    result_text = result.text_content

                # Determine output path - use just filename, no subdirectories
                output_filename = file_path.stem + '.md'
                output_path = self.output_dir / output_filename

                # Handle duplicate filenames
                counter = 1
                while output_path.exists():
                    output_filename = f"{file_path.stem}_{counter}.md"
                    output_path = self.output_dir / output_filename
                    counter += 1

                output_path.parent.mkdir(parents=True, exist_ok=True)

                # Write markdown
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(result_text)

                self.file_completed.emit(str(file_path), True, f"Converti: {output_path.name}")
                success_count += 1

            except Exception as e:
                self.file_completed.emit(str(file_path), False, f"Erreur: {str(e)}")

        self.progress_updated.emit(100, "Terminé")
        self.finished_all.emit(success_count, total)


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

        self.worker: Optional[ConversionWorker] = None
        self.success_count = 0
        self.total_count = 0

    def start_conversion(self, input_paths: List[Path], output_dir: Path, recursive: bool, use_ocr: bool):
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