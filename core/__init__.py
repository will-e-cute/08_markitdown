"""Core module for MarkItDown conversion logic."""

from .converter import ConversionWorker, OCR_AVAILABLE

__all__ = ['ConversionWorker', 'OCR_AVAILABLE']