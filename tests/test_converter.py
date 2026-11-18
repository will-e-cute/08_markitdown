"""Unit tests for ConversionWorker and OCR helpers."""

from pathlib import Path
import pytest
from PySide6.QtCore import QCoreApplication

from core.converter import (
    ConversionWorker,
    find_tesseract_cmd,
    check_ocr_availability,
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
        preserve_structure=True,
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
        preserve_structure=True,
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
        recursive=True,
    )
    worker.cancel()  # cancel immediately

    cancelled_called = []
    worker.conversion_cancelled.connect(lambda s, t: cancelled_called.append((s, t)))
    worker.run()

    assert len(cancelled_called) == 1
    assert cancelled_called[0][0] == 0  # 0 succeeded because cancelled before item 0


def test_conversion_worker_ocr_failure_reported_as_error(tmp_path: Path, qapp, monkeypatch):
    """Verify that an OCR failure reports success=False and does not write a corrupt .md file."""
    img_file = tmp_path / "scan.png"
    img_file.write_bytes(b"not a valid png image")
    out_dir = tmp_path / "out_ocr"

    # Force OCR availability to False
    monkeypatch.setattr(
        "core.converter.check_ocr_availability",
        lambda custom_path=None: (False, "Tesseract introuvable", []),
    )

    worker = ConversionWorker(
        input_paths=[img_file],
        output_dir=out_dir,
        use_ocr=True,
    )

    completed_events = []
    finished_events = []
    worker.file_completed.connect(lambda p, s, m: completed_events.append((p, s, m)))
    worker.finished_all.connect(lambda s, t: finished_events.append((s, t)))

    worker.run()

    assert len(completed_events) == 1
    assert completed_events[0][1] is False
    assert "OCR non disponible" in completed_events[0][2]
    assert finished_events == [(0, 1)]
    assert not (out_dir / "scan.md").exists()


def test_conversion_worker_conflict_policies(tmp_path: Path, qapp):
    """Verify overwrite and skip policies in ConversionWorker."""
    src_file = tmp_path / "note.txt"
    src_file.write_text("Nouveau contenu", encoding="utf-8")
    out_dir = tmp_path / "out_policy"
    out_dir.mkdir()
    existing_md = out_dir / "note.md"
    existing_md.write_text("Ancien contenu", encoding="utf-8")

    # 1. Skip policy should leave existing_md untouched
    worker_skip = ConversionWorker(
        input_paths=[src_file],
        output_dir=out_dir,
        conflict_policy="skip",
    )
    worker_skip.run()
    assert existing_md.read_text(encoding="utf-8") == "Ancien contenu"
    assert not (out_dir / "note_1.md").exists()

    # 2. Overwrite policy should replace existing_md without creating note_1.md
    worker_overwrite = ConversionWorker(
        input_paths=[src_file],
        output_dir=out_dir,
        conflict_policy="overwrite",
    )
    worker_overwrite.run()
    assert "Nouveau contenu" in existing_md.read_text(encoding="utf-8")
    assert not (out_dir / "note_1.md").exists()
