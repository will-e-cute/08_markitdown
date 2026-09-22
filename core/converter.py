"""Core conversion logic for MarkItDown."""

import os
from pathlib import Path
from typing import List

from PySide6.QtCore import QThread, Signal

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