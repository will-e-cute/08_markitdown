"""Markdown viewer dialog to inspect converted files."""

from pathlib import Path
from typing import List, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QTabWidget, QTextBrowser, QTextEdit, QPushButton, QApplication
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QFont, QDesktopServices


class MarkdownViewerDialog(QDialog):
    """Dialog displaying converted Markdown content with preview and raw view."""

    def __init__(self, markdown_files: List[Path], initial_file: Optional[Path] = None, parent=None):
        super().__init__(parent)
        self.markdown_files = [Path(f) for f in markdown_files if Path(f).exists()]
        self.setWindowTitle("Aperçu Markdown - MarkItDown")
        self.resize(750, 550)

        layout = QVBoxLayout(self)

        # Top file selector
        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("Fichier :"))

        self.file_combo = QComboBox()
        for f in self.markdown_files:
            self.file_combo.addItem(f.name, str(f))
        
        # Select initial file if provided
        if initial_file and Path(initial_file) in self.markdown_files:
            idx = self.markdown_files.index(Path(initial_file))
            self.file_combo.setCurrentIndex(idx)
        elif self.markdown_files:
            self.file_combo.setCurrentIndex(0)

        self.file_combo.currentIndexChanged.connect(self.load_selected_file)
        top_layout.addWidget(self.file_combo, 1)

        self.open_ext_btn = QPushButton("Ouvrir dans l'éditeur système")
        self.open_ext_btn.clicked.connect(self.open_in_system_editor)
        top_layout.addWidget(self.open_ext_btn)

        layout.addLayout(top_layout)

        # Tabs: Formatted / Raw
        self.tabs = QTabWidget()

        # Tab 1: Rendered Markdown
        self.rendered_browser = QTextBrowser()
        self.rendered_browser.setOpenExternalLinks(True)
        self.tabs.addTab(self.rendered_browser, "Rendu visuel")

        # Tab 2: Raw Markdown
        self.raw_edit = QTextEdit()
        self.raw_edit.setReadOnly(True)
        self.raw_edit.setFont(QFont("Consolas", 10))
        self.tabs.addTab(self.raw_edit, "Code source (.md)")

        layout.addWidget(self.tabs)

        # Bottom buttons
        bottom_layout = QHBoxLayout()

        self.copy_btn = QPushButton("📋 Copier le Markdown")
        self.copy_btn.clicked.connect(self.copy_to_clipboard)
        bottom_layout.addWidget(self.copy_btn)

        bottom_layout.addStretch()

        self.close_btn = QPushButton("Fermer")
        self.close_btn.clicked.connect(self.accept)
        bottom_layout.addWidget(self.close_btn)

        layout.addLayout(bottom_layout)

        # Load file content initially
        self.load_selected_file()

    def get_current_file(self) -> Optional[Path]:
        current_data = self.file_combo.currentData()
        if current_data:
            p = Path(current_data)
            if p.exists():
                return p
        return None

    def load_selected_file(self):
        current_file = self.get_current_file()
        if not current_file:
            self.rendered_browser.setHtml("<i>Aucun fichier à afficher</i>")
            self.raw_edit.setPlainText("")
            return

        try:
            content = current_file.read_text(encoding="utf-8")
            self.rendered_browser.setMarkdown(content)
            self.raw_edit.setPlainText(content)
        except Exception as e:
            self.rendered_browser.setHtml(f"<b style='color:red;'>Erreur de lecture:</b> {e}")
            self.raw_edit.setPlainText(f"Erreur de lecture: {e}")

    def copy_to_clipboard(self):
        content = self.raw_edit.toPlainText()
        QApplication.clipboard().setText(content)
        self.copy_btn.setText("✓ Copié !")
        # Reset text after a short moment if dialog stays open
        self.copy_btn.setEnabled(False)
        self.copy_btn.setEnabled(True)

    def open_in_system_editor(self):
        current_file = self.get_current_file()
        if current_file:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(current_file)))
