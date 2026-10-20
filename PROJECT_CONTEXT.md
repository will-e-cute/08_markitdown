# MarkItDown GUI & CLI - Project Context

## Overview
MarkItDown GUI & CLI is a modern PySide6-based graphical interface and command-line tool for converting documents (PDF, Word, Excel, PowerPoint, HTML, Audio, Images, etc.) into clean Markdown format using the Microsoft MarkItDown library with optional OCR support via Tesseract.

## Architecture

### Project Structure
```
08_markitdown/
├── main.py                # Dual entry point: CLI batch processing or GUI launcher
├── main.pyw               # Windows windowed GUI launcher (no console)
├── requirements.txt       # Python dependencies
├── pytest.ini             # Pytest configuration
├── .gitignore             # Git ignore file
├── core/
│   ├── __init__.py        # Public core API exports
│   └── converter.py       # Scan O(N), ConversionWorker (QThread), OCR helpers
├── gui/
│   ├── __init__.py        # Public GUI exports
│   ├── main_window.py     # Main application window (Drag&Drop, options, QSettings)
│   ├── progress_dialog.py # QDialog progress modal with cancellation & post-actions
│   └── markdown_viewer.py # Integrated Markdown previewer (rendered & raw views)
└── tests/
    ├── test_scanner.py    # Scanner & path preservation tests
    ├── test_converter.py  # Worker execution, signal & cancellation tests
    └── test_cli.py        # CLI mode test suite
```

## Key Capabilities & Technical Highlights

### 1. High Performance Single-Pass Scanning
- Implements `scan_files_to_convert` running in a single filesystem pass ($O(N)$) per directory.
- Case-insensitive extension matching (`.pdf`, `.PDF`, `.Pdf`).
- Computes relative subfolder paths to support preserving input hierarchy in the output folder.

### 2. Robust Multi-threaded Conversion Engine
- Inherits `QThread` (`ConversionWorker`), keeping Qt UI responsive.
- MarkItDown instance is created inside `run()` to guarantee thread affinity.
- Responsive cancellation: gracefully stops between files without reporting false completion.
- Non-colliding output renaming (`doc.md`, `doc_1.md`...).

### 3. Extended Format Support
- **Documents**: PDF, Word (`.docx`), Presentations (`.pptx`), Spreadsheets (`.xlsx`, `.xls`, `.csv`).
- **Web & Markup**: HTML (`.html`, `.htm`), Jupyter Notebooks (`.ipynb`), E-books (`.epub`).
- **Audio & Media**: Audio transcription (`.mp3`, `.wav`), Images with OCR.
- **Data & Text**: `.txt`, `.json`, `.xml`, `.msg`, `.zip`.

### 4. Smart OCR Detection & Fallback
- Searches executable in `PATH` and standard Windows directories.
- Verifies executable capability and dynamically lists installed languages (`pytesseract.get_languages()`).
- Auto-fallback to installed languages (e.g., `fra+eng`, `eng`, or user-specified).
- User can configure custom path via GUI or CLI.

### 5. Modern UI / UX
- Full Drag-and-Drop support on the main window.
- Multi-file and multi-folder selection.
- List view with item removal (Delete key).
- Output directory quick open button.
- Markdown viewer dialog (`MarkdownViewerDialog`) displaying rendered HTML preview and raw Markdown.
- State persistence using `QSettings`.