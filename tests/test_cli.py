"""Tests for CLI batch conversion."""

from pathlib import Path
from types import SimpleNamespace
from main import run_cli


def test_cli_execution(tmp_path: Path):
    in_file = tmp_path / "data.csv"
    in_file.write_text("item,qty\napple,5\n", encoding="utf-8")
    out_dir = tmp_path / "cli_out"

    args = SimpleNamespace(
        inputs=[str(in_file)],
        output=str(out_dir),
        no_recursive=False,
        preserve_structure=False,
        ocr=False,
        ocr_lang=None,
        tesseract_cmd=None,
    )

    exit_code = run_cli(args)
    assert exit_code == 0
    assert (out_dir / "data.md").exists()
    content = (out_dir / "data.md").read_text(encoding="utf-8")
    assert "apple" in content


def test_cli_overwrite_and_skip(tmp_path: Path):
    in_file = tmp_path / "info.txt"
    in_file.write_text("version 2", encoding="utf-8")
    out_dir = tmp_path / "cli_policy"
    out_dir.mkdir()
    target_md = out_dir / "info.md"
    target_md.write_text("version 1", encoding="utf-8")

    # Skip existing
    args_skip = SimpleNamespace(
        inputs=[str(in_file)],
        output=str(out_dir),
        no_recursive=False,
        preserve_structure=False,
        ocr=False,
        ocr_lang=None,
        tesseract_cmd=None,
        overwrite=False,
        skip_existing=True,
    )
    assert run_cli(args_skip) == 0
    assert target_md.read_text(encoding="utf-8") == "version 1"
    assert not (out_dir / "info_1.md").exists()

    # Overwrite existing
    args_overwrite = SimpleNamespace(
        inputs=[str(in_file)],
        output=str(out_dir),
        no_recursive=False,
        preserve_structure=False,
        ocr=False,
        ocr_lang=None,
        tesseract_cmd=None,
        overwrite=True,
        skip_existing=False,
    )
    assert run_cli(args_overwrite) == 0
    assert "version 2" in target_md.read_text(encoding="utf-8")
    assert not (out_dir / "info_1.md").exists()


def test_cli_failure_returns_nonzero(tmp_path: Path, monkeypatch):
    in_file = tmp_path / "broken.csv"
    in_file.write_text("a,b\n1,2\n", encoding="utf-8")
    out_dir = tmp_path / "cli_fail"

    def raise_err(*_args, **_kwargs):
        raise RuntimeError("Simulated conversion failure")

    monkeypatch.setattr("main.convert_file_content", raise_err)

    args = SimpleNamespace(
        inputs=[str(in_file)],
        output=str(out_dir),
        no_recursive=False,
        preserve_structure=False,
        ocr=False,
        ocr_lang=None,
        tesseract_cmd=None,
    )
    assert run_cli(args) == 1

