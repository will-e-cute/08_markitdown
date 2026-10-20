"""Unit tests for file scanner and path utilities."""

import os
from pathlib import Path
import pytest

from core.converter import (
    scan_files_to_convert,
    get_unique_output_path,
    SUPPORTED_EXTENSIONS,
    IMAGE_EXTENSIONS
)


def test_supported_extensions_membership():
    """Verify standard extensions are recognized."""
    assert '.pdf' in SUPPORTED_EXTENSIONS
    assert '.docx' in SUPPORTED_EXTENSIONS
    assert '.xlsx' in SUPPORTED_EXTENSIONS
    assert '.pptx' in SUPPORTED_EXTENSIONS
    assert '.csv' in SUPPORTED_EXTENSIONS
    assert '.html' in SUPPORTED_EXTENSIONS
    assert '.png' in IMAGE_EXTENSIONS
    assert '.jpg' in IMAGE_EXTENSIONS


def test_unique_output_path(tmp_path: Path):
    """Test non-colliding duplicate file naming."""
    target_dir = tmp_path / "output"
    target_dir.mkdir()

    p1 = get_unique_output_path(target_dir, "document")
    assert p1.name == "document.md"
    p1.touch()

    p2 = get_unique_output_path(target_dir, "document")
    assert p2.name == "document_1.md"
    p2.touch()

    p3 = get_unique_output_path(target_dir, "document")
    assert p3.name == "document_2.md"


def test_scan_single_files(tmp_path: Path):
    """Test scanning standalone files with case variations and unsupported filter."""
    f1 = tmp_path / "report.PDF"
    f1.touch()
    f2 = tmp_path / "data.XLSX"
    f2.touch()
    f3 = tmp_path / "unsupported.xyz"
    f3.touch()

    results = scan_files_to_convert([f1, f2, f3])
    scanned_paths = [r[0] for r in results]

    assert f1 in scanned_paths
    assert f2 in scanned_paths
    assert f3 not in scanned_paths
    assert len(results) == 2
    # Standalone files should have rel_dir=None
    assert results[0][1] is None
    assert results[1][1] is None


def test_scan_recursive_and_preservation(tmp_path: Path):
    """Test recursive directory walk and relative directory calculation."""
    src = tmp_path / "source"
    src.mkdir()
    
    sub1 = src / "sub1"
    sub1.mkdir()
    f_sub1 = sub1 / "doc1.docx"
    f_sub1.touch()

    sub2 = src / "sub1" / "nested"
    sub2.mkdir()
    f_nested = sub2 / "table.csv"
    f_nested.touch()

    root_file = src / "readme.txt"
    root_file.touch()

    # Recursive scan
    results_rec = scan_files_to_convert([src], recursive=True)
    paths_rec = {r[0].name: r[1] for r in results_rec}

    assert "doc1.docx" in paths_rec
    assert "table.csv" in paths_rec
    assert "readme.txt" in paths_rec

    # Relative paths verification
    assert paths_rec["doc1.docx"] == Path("sub1")
    assert paths_rec["table.csv"] == Path("sub1") / "nested"
    assert paths_rec["readme.txt"] == Path("")

    # Non-recursive scan
    results_nonrec = scan_files_to_convert([src], recursive=False)
    paths_nonrec = [r[0].name for r in results_nonrec]

    assert "readme.txt" in paths_nonrec
    assert "doc1.docx" not in paths_nonrec
    assert "table.csv" not in paths_nonrec
