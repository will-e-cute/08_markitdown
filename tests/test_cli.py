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
        tesseract_cmd=None
    )

    exit_code = run_cli(args)
    assert exit_code == 0
    assert (out_dir / "data.md").exists()
    content = (out_dir / "data.md").read_text(encoding="utf-8")
    assert "apple" in content
