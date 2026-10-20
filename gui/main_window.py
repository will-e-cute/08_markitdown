"""Main window for MarkItDown GUI."""

import sys
from pathlib import Path
from typing import List, Optional

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QFileDialog, QGroupBox, QCheckBox,
    QListWidget, QListWidgetItem, QMessageBox, QInputDialog, QDialog
)
from PySide6.QtCore import Qt, QSettings, QUrl
from PySide6.QtGui import QFont, QCloseEvent, QDesktopServices, QDragEnterEvent, QDropEvent

from core.converter import (
    SUPPORTED_EXTENSIONS, OCR_AVAILABLE, OCR_MESSAGE, OCR_LANGUAGES,
    check_ocr_availability
)
from gui.progress_dialog import ProgressDialog
from gui.markdown_viewer import MarkdownViewerDialog


class MainWindow(QMainWindow):
    """Main application window with drag-and-drop, multi-format and settings persistence."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("MarkItDown GUI - Convertisseur de documents")
        self.setMinimumSize(680, 560)
        self.setAcceptDrops(True)

        self.settings = QSettings("MarkItDownGUI", "ConverterApp")
        self.custom_tesseract_path = self.settings.value("custom_tesseract_path", "")
        
        # Check OCR availability with custom path if any
        self.ocr_available, self.ocr_status_msg, self.ocr_langs = check_ocr_availability(
            self.custom_tesseract_path if self.custom_tesseract_path else None
        )

        # Default output directory
        saved_output = self.settings.value("output_dir", "")
        if saved_output and Path(saved_output).exists():
            self.default_output = Path(saved_output)
        else:
            self.default_output = Path.home() / "Documents" / "Markitdown"
        self.default_output.mkdir(parents=True, exist_ok=True)

        self.input_paths: List[Path] = []
        self.progress_dialog: Optional[ProgressDialog] = None
        self.last_converted_files: List[Path] = []

        self.setup_ui()
        self.restore_settings()

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(12)
        layout.setContentsMargins(18, 16, 18, 16)

        # Title
        title_layout = QHBoxLayout()
        title = QLabel("MarkItDown - Convertisseur universel")
        title.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        title_layout.addWidget(title)
        title_layout.addStretch()
        layout.addLayout(title_layout)

        # File selection group
        input_group = QGroupBox("Documents et dossiers à convertir (Glisser-déposer supporté)")
        input_layout = QVBoxLayout(input_group)
        input_layout.setSpacing(8)

        # Buttons to add files / folders
        btns_layout = QHBoxLayout()
        self.add_files_btn = QPushButton("📄 Ajouter des fichiers...")
        self.add_files_btn.setMinimumHeight(34)
        self.add_files_btn.clicked.connect(self.select_files)
        btns_layout.addWidget(self.add_files_btn)

        self.add_folder_btn = QPushButton("📁 Ajouter un dossier...")
        self.add_folder_btn.setMinimumHeight(34)
        self.add_folder_btn.clicked.connect(self.select_folder)
        btns_layout.addWidget(self.add_folder_btn)

        self.clear_list_btn = QPushButton("🗑️ Vider la liste")
        self.clear_list_btn.setMinimumHeight(34)
        self.clear_list_btn.clicked.connect(self.clear_selection)
        btns_layout.addWidget(self.clear_list_btn)

        input_layout.addLayout(btns_layout)

        # Input List Widget
        self.input_list = QListWidget()
        self.input_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.input_list.setMinimumHeight(110)
        self.input_list.setToolTip("Fichiers et dossiers en attente. Sélectionnez un élément et appuyez sur Suppr pour le retirer.")
        self.input_list.keyPressEvent = self.list_key_press_event
        input_layout.addWidget(self.input_list)

        self.count_label = QLabel("Aucun élément sélectionné. Glissez-déposez vos fichiers ici.")
        self.count_label.setStyleSheet("color: #666; font-size: 11px;")
        input_layout.addWidget(self.count_label)

        layout.addWidget(input_group)

        # Conversion Options Group
        options_group = QGroupBox("Options de conversion")
        options_layout = QVBoxLayout(options_group)
        options_layout.setSpacing(6)

        self.recursive_check = QCheckBox("Inclure les sous-dossiers lors de l'ajout d'un dossier (récursif)")
        self.recursive_check.setChecked(True)
        options_layout.addWidget(self.recursive_check)

        self.preserve_structure_check = QCheckBox("Conserver l'arborescence des sous-dossiers dans le dossier de sortie")
        self.preserve_structure_check.setChecked(True)
        self.preserve_structure_check.setToolTip(
            "Si coché, les fichiers conservent leur arborescence relative au lieu d'être tous regroupés à plat."
        )
        options_layout.addWidget(self.preserve_structure_check)

        # OCR row
        ocr_row = QHBoxLayout()
        self.ocr_check = QCheckBox("Activer l'OCR pour les images (Tesseract)")
        self.ocr_check.setChecked(False)
        self.ocr_check.setEnabled(self.ocr_available)
        ocr_row.addWidget(self.ocr_check)

        self.ocr_config_btn = QPushButton("⚙️ Configurer Tesseract...")
        self.ocr_config_btn.clicked.connect(self.configure_tesseract)
        ocr_row.addWidget(self.ocr_config_btn)
        options_layout.addLayout(ocr_row)

        self.ocr_status_label = QLabel(self.ocr_status_msg)
        self.ocr_status_label.setStyleSheet("color: #2e7d32;" if self.ocr_available else "color: #c62828;")
        options_layout.addWidget(self.ocr_status_label)

        layout.addWidget(options_group)

        # Output directory group
        output_group = QGroupBox("Dossier de destination")
        output_layout = QHBoxLayout(output_group)

        self.output_edit = QLineEdit(str(self.default_output))
        output_layout.addWidget(self.output_edit, 1)

        self.output_btn = QPushButton("Parcourir...")
        self.output_btn.clicked.connect(self.select_output_dir)
        output_layout.addWidget(self.output_btn)

        self.open_output_btn = QPushButton("📂 Ouvrir")
        self.open_output_btn.clicked.connect(self.open_current_output_dir)
        output_layout.addWidget(self.open_output_btn)

        layout.addWidget(output_group)

        # Supported formats footer
        formats_text = (
            "<b>Formats supportés :</b> PDF, Word (.docx), Excel (.xlsx, .xls, .csv), "
            "PowerPoint (.pptx), Web (.html), E-books (.epub), Notebooks (.ipynb), "
            "Messages (.msg), Audio (.mp3, .wav), Images (.png, .jpg, .webp...)"
        )
        formats_label = QLabel(formats_text)
        formats_label.setWordWrap(True)
        formats_label.setStyleSheet("color: #555; font-size: 11px;")
        layout.addWidget(formats_label)

        # Convert and Preview buttons
        action_layout = QHBoxLayout()
        self.convert_btn = QPushButton("🚀 Lancer la conversion")
        self.convert_btn.setMinimumHeight(44)
        self.convert_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.convert_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border-radius: 4px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.convert_btn.clicked.connect(self.start_conversion)
        action_layout.addWidget(self.convert_btn, 2)

        self.view_last_btn = QPushButton("👁️ Dernier aperçu")
        self.view_last_btn.setMinimumHeight(44)
        self.view_last_btn.setEnabled(False)
        self.view_last_btn.clicked.connect(self.show_last_preview)
        action_layout.addWidget(self.view_last_btn, 1)

        layout.addLayout(action_layout)

        # Status
        self.status_label = QLabel("Prêt")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        self.update_convert_button()

    # --- Drag & Drop Support ---
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        paths_to_add = []
        for url in event.mimeData().urls():
            local_path = Path(url.toLocalFile())
            if local_path.exists():
                paths_to_add.append(local_path)
        if paths_to_add:
            self.add_paths(paths_to_add)
            event.acceptProposedAction()

    # --- File & Folder Selection ---
    def select_files(self):
        extensions_filter = (
            "Tous documents compatibles (*.pdf *.docx *.pptx *.xlsx *.xls *.csv *.html *.htm "
            "*.ipynb *.epub *.msg *.zip *.txt *.json *.xml *.jpg *.jpeg *.png *.bmp *.webp *.wav *.mp3);;"
            "Documents PDF (*.pdf);;"
            "Documents Word (*.docx *.doc);;"
            "Tableurs Excel / CSV (*.xlsx *.xls *.csv);;"
            "Présentations PowerPoint (*.pptx);;"
            "Images (*.jpg *.jpeg *.png *.bmp *.gif *.tiff *.webp);;"
            "Tous les fichiers (*.*)"
        )
        files, _ = QFileDialog.getOpenFileNames(
            self, "Sélectionner un ou plusieurs fichiers à convertir", "", extensions_filter
        )
        if files:
            self.add_paths([Path(f) for f in files])

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Sélectionner un dossier à convertir", str(Path.home())
        )
        if folder:
            self.add_paths([Path(folder)])

    def add_paths(self, new_paths: List[Path]):
        for p in new_paths:
            if p not in self.input_paths:
                self.input_paths.append(p)
                prefix = "📁 [Dossier] " if p.is_dir() else "📄 [Fichier] "
                item = QListWidgetItem(f"{prefix}{p}")
                item.setData(Qt.ItemDataRole.UserRole, str(p))
                self.input_list.addItem(item)
        self.update_ui_state()

    def list_key_press_event(self, event):
        if event.key() == Qt.Key.Key_Delete:
            self.remove_selected_items()
        else:
            QListWidget.keyPressEvent(self.input_list, event)

    def remove_selected_items(self):
        selected_items = self.input_list.selectedItems()
        for item in selected_items:
            path_str = item.data(Qt.ItemDataRole.UserRole)
            if path_str:
                p = Path(path_str)
                if p in self.input_paths:
                    self.input_paths.remove(p)
            self.input_list.takeItem(self.input_list.row(item))
        self.update_ui_state()

    def clear_selection(self):
        self.input_paths.clear()
        self.input_list.clear()
        self.update_ui_state()

    def update_ui_state(self):
        count = len(self.input_paths)
        if count == 0:
            self.count_label.setText("Aucun élément sélectionné. Glissez-déposez vos fichiers ici.")
        elif count == 1:
            p = self.input_paths[0]
            self.count_label.setText(f"1 élément sélectionné : {p.name}")
        else:
            self.count_label.setText(f"{count} éléments sélectionnés.")
        self.update_convert_button()

    def select_output_dir(self):
        current_text = self.output_edit.text()
        start_dir = current_text if Path(current_text).exists() else str(self.default_output)
        folder = QFileDialog.getExistingDirectory(self, "Sélectionner le dossier de destination", start_dir)
        if folder:
            self.output_edit.setText(folder)
            self.settings.setValue("output_dir", folder)

    def open_current_output_dir(self):
        out_dir = Path(self.output_edit.text())
        out_dir.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(out_dir)))

    def update_convert_button(self):
        self.convert_btn.setEnabled(len(self.input_paths) > 0)

    # --- Tesseract Configuration ---
    def configure_tesseract(self):
        path, ok = QInputDialog.getText(
            self,
            "Configuration de Tesseract-OCR",
            "Chemin complet vers tesseract.exe (laisser vide pour la détection automatique) :",
            QLineEdit.EchoMode.Normal,
            self.custom_tesseract_path
        )
        if ok:
            self.custom_tesseract_path = path.strip()
            self.settings.setValue("custom_tesseract_path", self.custom_tesseract_path)
            self.ocr_available, self.ocr_status_msg, self.ocr_langs = check_ocr_availability(
                self.custom_tesseract_path if self.custom_tesseract_path else None
            )
            self.ocr_status_label.setText(self.ocr_status_msg)
            self.ocr_status_label.setStyleSheet("color: #2e7d32;" if self.ocr_available else "color: #c62828;")
            self.ocr_check.setEnabled(self.ocr_available)

    # --- Conversion Execution ---
    def start_conversion(self):
        if not self.input_paths:
            QMessageBox.warning(self, "Attention", "Veuillez sélectionner au moins un fichier ou dossier à convertir.")
            return

        output_dir = Path(self.output_edit.text().strip())
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Impossible d'accéder au dossier de destination:\n{e}")
            return

        # Save settings
        self.save_settings()

        self.convert_btn.setEnabled(False)
        self.status_label.setText("Conversion en cours...")

        self.progress_dialog = ProgressDialog(self)
        self.progress_dialog.start_conversion(
            input_paths=self.input_paths,
            output_dir=output_dir,
            recursive=self.recursive_check.isChecked(),
            preserve_structure=self.preserve_structure_check.isChecked(),
            use_ocr=self.ocr_check.isChecked(),
            custom_tesseract_cmd=self.custom_tesseract_path if self.custom_tesseract_path else None,
        )
        self.progress_dialog.finished.connect(self.on_conversion_finished)
        self.progress_dialog.show()

    def on_conversion_finished(self):
        self.convert_btn.setEnabled(True)
        self.status_label.setText("Prêt")
        if self.progress_dialog and self.progress_dialog.converted_files:
            self.last_converted_files = list(self.progress_dialog.converted_files)
            self.view_last_btn.setEnabled(True)

    def show_last_preview(self):
        if self.last_converted_files:
            dlg = MarkdownViewerDialog(self.last_converted_files, parent=self)
            dlg.exec()

    # --- Settings Persistence ---
    def save_settings(self):
        self.settings.setValue("output_dir", self.output_edit.text())
        self.settings.setValue("recursive", self.recursive_check.isChecked())
        self.settings.setValue("preserve_structure", self.preserve_structure_check.isChecked())
        self.settings.setValue("use_ocr", self.ocr_check.isChecked())
        self.settings.setValue("geometry", self.saveGeometry())

    def restore_settings(self):
        geom = self.settings.value("geometry")
        if geom:
            self.restoreGeometry(geom)
        if self.settings.contains("recursive"):
            self.recursive_check.setChecked(self.settings.value("recursive", type=bool))
        if self.settings.contains("preserve_structure"):
            self.preserve_structure_check.setChecked(self.settings.value("preserve_structure", type=bool))
        if self.settings.contains("use_ocr") and self.ocr_available:
            self.ocr_check.setChecked(self.settings.value("use_ocr", type=bool))

    def closeEvent(self, event: QCloseEvent):
        if self.progress_dialog and self.progress_dialog.is_converting:
            res = QMessageBox.question(
                self,
                "Quitter pendant la conversion ?",
                "Une conversion est en cours d'exécution. Voulez-vous l'annuler et quitter ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if res == QMessageBox.StandardButton.Yes:
                self.progress_dialog.cancel_conversion()
                if self.progress_dialog.worker:
                    self.progress_dialog.worker.wait(3000)
                self.save_settings()
                event.accept()
            else:
                event.ignore()
                return

        self.save_settings()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()