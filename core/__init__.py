"""Core module for MarkItDown conversion logic."""

from .converter import (
    ConversionWorker,
    SUPPORTED_EXTENSIONS,
    IMAGE_EXTENSIONS,
    DOCUMENT_EXTENSIONS,
    AUDIO_EXTENSIONS,
    OCR_AVAILABLE,
    OCR_MESSAGE,
    OCR_LANGUAGES,
    check_ocr_availability,
    find_tesseract_cmd,
    scan_files_to_convert,
    get_unique_output_path,
)

__all__ = [
    'ConversionWorker',
    'SUPPORTED_EXTENSIONS',
    'IMAGE_EXTENSIONS',
    'DOCUMENT_EXTENSIONS',
    'AUDIO_EXTENSIONS',
    'OCR_AVAILABLE',
    'OCR_MESSAGE',
    'OCR_LANGUAGES',
    'check_ocr_availability',
    'find_tesseract_cmd',
    'scan_files_to_convert',
    'get_unique_output_path',
]