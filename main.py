"""MarkItDown GUI & CLI - Universal document converter."""

import argparse
import sys
from pathlib import Path

from core.converter import (
    SUPPORTED_EXTENSIONS,
    check_ocr_availability,
    convert_file_content,
    resolve_output_path,
    scan_files_to_convert,
)


def _get_conflict_policy(args) -> str:
    """Determine conflict resolution policy from CLI arguments."""
    if getattr(args, "overwrite", False):
        return "overwrite"
    if getattr(args, "skip_existing", False):
        return "skip"
    return getattr(args, "conflict_policy", "rename") or "rename"


def run_cli(args) -> int:
    """Headless CLI batch conversion mode."""
    from markitdown import MarkItDown

    input_paths = [Path(p) for p in args.inputs]
    output_dir = Path(args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    recursive = not getattr(args, "no_recursive", False)
    preserve_structure = getattr(args, "preserve_structure", False)
    use_ocr = getattr(args, "ocr", False)
    ocr_lang = getattr(args, "ocr_lang", None)
    tesseract_cmd = getattr(args, "tesseract_cmd", None)
    conflict_policy = _get_conflict_policy(args)

    print(f"Scanning files in {len(input_paths)} source path(s)...")
    file_entries = scan_files_to_convert(
        input_paths,
        recursive=recursive,
        supported_extensions=SUPPORTED_EXTENSIONS,
    )

    total = len(file_entries)
    if total == 0:
        print("Aucun fichier compatible trouvé.")
        return 0

    print(f"{total} fichier(s) détecté(s). Début de la conversion vers: {output_dir}\n")

    # Initialize MarkItDown and check OCR once if requested
    markitdown = MarkItDown()
    ocr_info = None
    if use_ocr:
        ocr_info = check_ocr_availability(tesseract_cmd)
        ocr_avail, ocr_msg, _ = ocr_info
        if not ocr_avail:
            print(f"ATTENTION: {ocr_msg}. L'OCR sera ignoré.")
            use_ocr = False
        else:
            print(f"OCR activé: {ocr_msg}")

    success_count = 0
    for idx, (fpath, rel_subfolder) in enumerate(file_entries, 1):
        target_dir = (
            output_dir / rel_subfolder
            if (preserve_structure and rel_subfolder is not None)
            else output_dir
        )
        out_file = resolve_output_path(target_dir, fpath.stem, conflict_policy=conflict_policy)
        if out_file is None:
            print(f"[{idx}/{total}] Ignoré (existe déjà): {fpath.name} -> {fpath.stem}.md")
            success_count += 1
            continue

        print(f"[{idx}/{total}] Conversion: {fpath.name} -> {out_file.name}...", end=" ", flush=True)
        try:
            result_text = convert_file_content(
                fpath,
                markitdown_instance=markitdown,
                use_ocr=use_ocr,
                ocr_lang=ocr_lang,
                custom_tesseract_cmd=tesseract_cmd,
                ocr_info=ocr_info,
            )
            out_file.write_text(result_text, encoding="utf-8")
            print("OK")
            success_count += 1
        except Exception as e:
            print(f"ERREUR: {e}")

    print(f"\nTerminé: {success_count}/{total} fichier(s) traité(s) avec succès.")
    return 0 if success_count == total else 1


def main():
    parser = argparse.ArgumentParser(
        description="MarkItDown GUI / CLI - Convertir des documents (PDF, Word, Excel, Images, PPTX...) en Markdown."
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        help="Chemins vers les fichiers ou dossiers à convertir. Si omis, l'interface graphique (GUI) est lancée.",
    )
    parser.add_argument(
        "-o", "--output",
        default=str(Path.home() / "Documents" / "Markitdown"),
        help="Dossier de destination pour les fichiers Markdown générés.",
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Désactive la recherche récursive dans les sous-dossiers.",
    )
    parser.add_argument(
        "--preserve-structure",
        action="store_true",
        help="Reproduit l'arborescence des dossiers source dans le dossier de sortie.",
    )
    parser.add_argument(
        "--ocr",
        action="store_true",
        help="Active l'OCR pour les images via Tesseract.",
    )
    parser.add_argument(
        "--ocr-lang",
        default=None,
        help="Langues pour Tesseract (ex: 'fra', 'eng', 'fra+eng').",
    )
    parser.add_argument(
        "--tesseract-cmd",
        default=None,
        help="Chemin personnalisé vers tesseract.exe.",
    )

    conflict_group = parser.add_mutually_exclusive_group()
    conflict_group.add_argument(
        "--overwrite",
        action="store_true",
        help="Écrase les fichiers Markdown existants au lieu de les renommer (_1, _2...).",
    )
    conflict_group.add_argument(
        "--skip-existing",
        action="store_true",
        help="Ignore la conversion si le fichier Markdown cible existe déjà.",
    )

    parser.add_argument(
        "--gui",
        action="store_true",
        help="Forcer le lancement de l'interface graphique.",
    )

    args = parser.parse_args()

    # If input files are specified and --gui is not requested, run CLI
    if args.inputs and not args.gui:
        sys.exit(run_cli(args))
    else:
        from gui.main_window import main as gui_main
        gui_main()


if __name__ == "__main__":
    main()
