"""Core conversion logic for MarkItDown GUI."""

import os
import shutil
from pathlib import Path
from typing import List, Optional, Tuple, Set

from PySide6.QtCore import QThread, Signal


# Supported file formats
DOCUMENT_EXTENSIONS: Set[str] = {
    # Documents
    '.pdf', '.docx', '.doc', '.pptx', '.ppt',
    # Tableurs & données
    '.xlsx', '.xls', '.csv', '.json', '.xml',
    # Web & texte
    '.html', '.htm', '.xhtml', '.txt', '.text', '.ipynb', '.epub', '.msg', '.zip',
}

IMAGE_EXTENSIONS: Set[str] = {
    '.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp'
}

AUDIO_EXTENSIONS: Set[str] = {
    '.wav', '.mp3'
}

SUPPORTED_EXTENSIONS: Set[str] = DOCUMENT_EXTENSIONS | IMAGE_EXTENSIONS | AUDIO_EXTENSIONS


def find_tesseract_cmd(custom_path: Optional[str] = None) -> Optional[str]:
    """Find the path to the Tesseract executable."""
    if custom_path and os.path.isfile(custom_path):
        return custom_path
    
    # Check system PATH
    path_bin = shutil.which("tesseract")
    if path_bin:
        return path_bin
        
    # Check standard Windows paths
    candidates = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
            
    return None


def check_ocr_availability(custom_path: Optional[str] = None) -> Tuple[bool, str, List[str]]:
    """
    Check if OCR is fully functional (both python package and tesseract executable).
    
    Returns:
        (is_available, status_message, list_of_languages)
    """
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        return False, "Bibliothèques pytesseract ou Pillow non installées", []
        
    tesseract_cmd = find_tesseract_cmd(custom_path)
    if not tesseract_cmd:
        return False, "Exécutable Tesseract-OCR introuvable (installez-le ou spécifiez son chemin)", []
        
    try:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        version = pytesseract.get_tesseract_version()
        languages = pytesseract.get_languages()
        return True, f"Tesseract {version} détecté ({', '.join(languages)})", languages
    except Exception as e:
        return False, f"Erreur lors de l'appel à Tesseract: {e}", []


# Global cached status at module load
OCR_AVAILABLE, OCR_MESSAGE, OCR_LANGUAGES = check_ocr_availability()


def scan_files_to_convert(
    input_paths: List[Path],
    recursive: bool = True,
    supported_extensions: Optional[Set[str]] = None,
) -> List[Tuple[Path, Optional[Path]]]:
    """
    Scan input paths (files and directories) in a single pass O(N) per folder.
    
    Returns:
        List of (file_path, relative_subfolder_path) tuples.
        relative_subfolder_path is relative to the root scanned directory,
        or None if the file was specified individually.
    """
    if supported_extensions is None:
        supported_extensions = SUPPORTED_EXTENSIONS

    files: List[Tuple[Path, Optional[Path]]] = []
    seen: Set[Path] = set()

    for path in input_paths:
        if not path.exists():
            continue

        if path.is_file():
            if path.suffix.lower() in supported_extensions:
                resolved = path.resolve()
                if resolved not in seen:
                    seen.add(resolved)
                    files.append((path, None))
        elif path.is_dir():
            if recursive:
                for root, _, filenames in os.walk(path):
                    root_path = Path(root)
                    try:
                        rel_dir = root_path.relative_to(path)
                    except ValueError:
                        rel_dir = Path("")
                    for fname in filenames:
                        fpath = root_path / fname
                        if fpath.suffix.lower() in supported_extensions:
                            resolved = fpath.resolve()
                            if resolved not in seen:
                                seen.add(resolved)
                                files.append((fpath, rel_dir))
            else:
                for entry in path.iterdir():
                    if entry.is_file() and entry.suffix.lower() in supported_extensions:
                        resolved = entry.resolve()
                        if resolved not in seen:
                            seen.add(resolved)
                            files.append((entry, Path("")))

    return files


def get_unique_output_path(target_dir: Path, original_stem: str) -> Path:
    """Generate a non-colliding file path in target_dir by appending _1, _2... if needed."""
    target_dir.mkdir(parents=True, exist_ok=True)
    out = target_dir / f"{original_stem}.md"
    counter = 1
    while out.exists():
        out = target_dir / f"{original_stem}_{counter}.md"
        counter += 1
    return out


class ConversionWorker(QThread):
    """Worker thread for background document conversion."""
    
    progress_updated = Signal(int, str)  # percent, current file/status
    file_completed = Signal(str, bool, str)  # file path, success, message
    finished_all = Signal(int, int)  # success count, total count
    conversion_cancelled = Signal(int, int)  # success count, total count
    converted_files_ready = Signal(list)  # list of Path for generated .md files
    
    def __init__(
        self,
        input_paths: List[Path],
        output_dir: Path,
        recursive: bool = True,
        preserve_structure: bool = False,
        use_ocr: bool = False,
        ocr_lang: Optional[str] = None,
        custom_tesseract_cmd: Optional[str] = None,
    ):
        super().__init__()
        self.input_paths = [Path(p) for p in input_paths]
        self.output_dir = Path(output_dir)
        self.recursive = recursive
        self.preserve_structure = preserve_structure
        self.use_ocr = use_ocr
        self.ocr_lang = ocr_lang
        self.custom_tesseract_cmd = custom_tesseract_cmd
        self._is_cancelled = False
        self.created_files: List[Path] = []
        
        self.supported_extensions = SUPPORTED_EXTENSIONS
        self.image_extensions = IMAGE_EXTENSIONS
    
    def cancel(self):
        """Request worker cancellation."""
        self._is_cancelled = True
    
    def get_files_to_convert(self) -> List[Tuple[Path, Optional[Path]]]:
        """Get all files to convert with their relative subfolder paths."""
        return scan_files_to_convert(
            self.input_paths,
            recursive=self.recursive,
            supported_extensions=self.supported_extensions,
        )
    
    def convert_image_with_ocr(self, file_path: Path) -> str:
        """Convert image to text using OCR with optimal language fallback."""
        is_avail, msg, languages = check_ocr_availability(self.custom_tesseract_cmd)
        if not is_avail:
            return f"[OCR non disponible: {msg}]"
        
        try:
            import pytesseract
            from PIL import Image
            
            cmd = find_tesseract_cmd(self.custom_tesseract_cmd)
            if cmd:
                pytesseract.pytesseract.tesseract_cmd = cmd
            
            chosen_lang = self.ocr_lang
            if not chosen_lang:
                if "fra" in languages and "eng" in languages:
                    chosen_lang = "fra+eng"
                elif "fra" in languages:
                    chosen_lang = "fra"
                elif "eng" in languages:
                    chosen_lang = "eng"
                elif languages:
                    chosen_lang = languages[0]
                else:
                    chosen_lang = "eng"

            with Image.open(file_path) as img:
                if img.mode not in ("RGB", "L"):
                    img = img.convert("RGB")
                text = pytesseract.image_to_string(img, lang=chosen_lang)
                return text.strip()
        except Exception as e:
            return f"[Erreur OCR: {str(e)}]"
    
    def run(self):
        """Main worker execution loop."""
        from markitdown import MarkItDown
        markitdown = MarkItDown()
        
        self.created_files = []
        
        file_entries = self.get_files_to_convert()
        total = len(file_entries)
        success_count = 0
        
        if total == 0:
            self.finished_all.emit(0, 0)
            return
            
        if self._is_cancelled:
            self.progress_updated.emit(0, "Conversion interrompue")
            self.conversion_cancelled.emit(0, total)
            self.converted_files_ready.emit(self.created_files)
            return
        
        for i, (file_path, rel_subfolder) in enumerate(file_entries):
            if self._is_cancelled:
                self.progress_updated.emit(int((i / total) * 100), "Conversion interrompue")
                self.conversion_cancelled.emit(success_count, total)
                self.converted_files_ready.emit(self.created_files)
                return
            
            progress = int((i / total) * 100)
            self.progress_updated.emit(progress, file_path.name)
            
            try:
                # Determine target folder
                if self.preserve_structure and rel_subfolder is not None:
                    target_dir = self.output_dir / rel_subfolder
                else:
                    target_dir = self.output_dir
                
                output_path = get_unique_output_path(target_dir, file_path.stem)
                
                # Convert content
                if self.use_ocr and file_path.suffix.lower() in self.image_extensions:
                    text_content = self.convert_image_with_ocr(file_path)
                    result_text = f"# {file_path.name}\n\n{text_content}"
                else:
                    result = markitdown.convert(str(file_path))
                    result_text = result.text_content
                
                output_path.write_text(result_text, encoding="utf-8")
                self.created_files.append(output_path)
                success_count += 1
                self.file_completed.emit(str(file_path), True, f"Converti: {output_path.name}")
                
            except Exception as e:
                self.file_completed.emit(str(file_path), False, f"Erreur: {str(e)}")
        
        self.progress_updated.emit(100, "Terminé")
        self.finished_all.emit(success_count, total)
        self.converted_files_ready.emit(self.created_files)