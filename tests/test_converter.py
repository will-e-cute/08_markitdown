"""Unit tests for ConversionWorker and OCR helpers."""

from pathlib import Path
import pytest
from PySide6.QtCore import QCoreApplication

from core.converter import (
    ConversionWorker,
    find_tesseract_cmd,
    check_ocr_availability
)


@pytest.fixture(scope="session")
def qapp():
    """Ensure a QCoreApplication exists for QThread tests."""
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    return app


def test_ocr_availability_check():
    """Check that check_ocr_availability returns a valid tuple."""
    is_avail, msg, langs = check_ocr_availability()
    assert isinstance(is_avail, bool)
    assert isinstance(msg, str)
    assert isinstance(langs, list)


def test_find_tesseract_cmd_custom_path(tmp_path: Path):
    """Custom path should be respected if file exists."""
    fake_exe = tmp_path / "tesseract.exe"
    fake_exe.touch()
    found = find_tesseract_cmd(str(fake_exe))
    assert found == str(fake_exe)


def test_conversion_worker_basic(tmp_path: Path, qapp):
    """Test ConversionWorker executing on CSV and HTML files."""
    in_dir = tmp_path / "input"
    in_dir.mkdir()
    out_dir = tmp_path / "output"
    out_dir.mkdir()

    # Create dummy files
    csv_file = in_dir / "test.csv"
    csv_file.write_text("colA,colB\n10,20\n", encoding="utf-8")

    html_file = in_dir / "sample.html"
    html_file.write_text("<h1>Bonjour</h1><p>Test</p>", encoding="utf-8")

    worker = ConversionWorker(
        input_paths=[in_dir],
        output_dir=out_dir,
        recursive=True,
        preserve_structure=True
    )

    completed_events = []
    worker.file_completed.connect(lambda p, s, m: completed_events.append((p, s, m)))

    # Run synchronously
    worker.run()

    # Check results
    assert len(completed_events) == 2
    assert all(ev[1] is True for ev in completed_events)
    assert (out_dir / "test.md").exists()
    assert (out_dir / "sample.md").exists()

    content = (out_dir / "test.md").read_text(encoding="utf-8")
    assert "colA" in content


def test_conversion_worker_structure_preservation(tmp_path: Path, qapp):
    """Verify that preserve_structure reproduces subfolders."""
    src = tmp_path / "src"
    src.mkdir()
    sub = src / "nested" / "deep"
    sub.mkdir(parents=True)
    f = sub / "doc.txt"
    f.write_text("Contenu texte", encoding="utf-8")

    out = tmp_path / "out"

    worker = ConversionWorker(
        input_paths=[src],
        output_dir=out,
        recursive=True,
        preserve_structure=True
    )
    worker.run()

    expected_file = out / "nested" / "deep" / "doc.md"
    assert expected_file.exists()
    assert "Contenu texte" in expected_file.read_text(encoding="utf-8")


def test_conversion_worker_cancel(tmp_path: Path, qapp):
    """Verify cancel flag stops processing early."""
    src = tmp_path / "batch"
    src.mkdir()
    for i in range(5):
        (src / f"file_{i}.txt").write_text(f"text {i}", encoding="utf-8")

    out = tmp_path / "out_cancel"

    worker = ConversionWorker(
        input_paths=[src],
        output_dir=out,
        recursive=True
    )
    worker.cancel()  # cancel immediately

    cancelled_called = []
    worker.conversion_cancelled.connect(lambda s, t: cancelled_called.append((s, t)))
    worker.run()

    assert len(cancelled_called) == 1
    assert cancelled_called[0][0] == 0  # 0 succeeded because cancelled before item 0
