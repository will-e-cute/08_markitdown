"""MarkItDown GUI & CLI - Universal document converter."""

import argparse
import sys
from pathlib import Path

from core.converter import (
    IMAGE_EXTENSIONS,
    SUPPORTED_EXTENSIONS,
    check_ocr_availability,
    find_tesseract_cmd,
    get_unique_output_path,
    scan_files_to_convert,
)


def run_cli(args):
    """Headless CLI batch conversion mode."""
    from markitdown import MarkItDown
    
    input_paths = [Path(p) for p in args.inputs]
    output_dir = Path(args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    
    recursive = not args.no_recursive
    preserve_structure = args.preserve_structure
    use_ocr = args.ocr
    
    print(f"Scanning files in {len(input_paths)} source path(s)...")
    file_entries = scan_files_to_convert(
        input_paths,
        recursive=recursive,
        supported_extensions=SUPPORTED_EXTENSIONS
    )
    
    total = len(file_entries)
    if total == 0:
        print("Aucun fichier compatible trouvé.")
        return 0
        
    print(f"{total} fichier(s) détecté(s). Début de la conversion vers: {output_dir}\n")
    
    # Initialize MarkItDown and OCR if needed
    markitdown = MarkItDown()
    ocr_avail, ocr_msg, ocr_langs = check_ocr_availability(args.tesseract_cmd)
    
    if use_ocr:
        if not ocr_avail:
            print(f"ATTENTION: {ocr_msg}. L'OCR sera ignoré.")
            use_ocr = False
        else:
            print(f"OCR activé: {ocr_msg}")
            
    success_count = 0
    for idx, (fpath, rel_subfolder) in enumerate(file_entries, 1):
        target_dir = output_dir / rel_subfolder if (preserve_structure and rel_subfolder is not None) else output_dir
        out_file = get_unique_output_path(target_dir, fpath.stem)
        
        print(f"[{idx}/{total}] Conversion: {fpath.name} -> {out_file.name}...", end=" ", flush=True)
        try:
            if use_ocr and fpath.suffix.lower() in IMAGE_EXTENSIONS:
                import pytesseract
                from PIL import Image
                cmd = find_tesseract_cmd(args.tesseract_cmd)
                if cmd:
                    pytesseract.pytesseract.tesseract_cmd = cmd
                
                lang = args.ocr_lang or ("fra+eng" if "fra" in ocr_langs and "eng" in ocr_langs else "eng")
                with Image.open(fpath) as img:
                    if img.mode not in ("RGB", "L"):
                        img = img.convert("RGB")
                    text = pytesseract.image_to_string(img, lang=lang).strip()
                result_text = f"# {fpath.name}\n\n{text}"
            else:
                res = markitdown.convert(str(fpath))
                result_text = res.text_content
                
            out_file.write_text(result_text, encoding="utf-8")
            print("OK")
            success_count += 1
        except Exception as e:
            print(f"ERREUR: {e}")
            
    print(f"\nTerminé: {success_count}/{total} fichier(s) converti(s) avec succès.")
    return 0 if success_count == total else 1


def main():
    parser = argparse.ArgumentParser(
        description="MarkItDown GUI / CLI - Convertir des documents (PDF, Word, Excel, Images, PPTX...) en Markdown."
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        help="Chemins vers les fichiers ou dossiers à convertir. Si omis, l'interface graphique (GUI) est lancée."
    )
    parser.add_argument(
        "-o", "--output",
        default=str(Path.home() / "Documents" / "Markitdown"),
        help="Dossier de destination pour les fichiers Markdown générés."
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Désactive la recherche récursive dans les sous-dossiers."
    )
    parser.add_argument(
        "--preserve-structure",
        action="store_true",
        help="Reproduit l'arborescence des dossiers source dans le dossier de sortie."
    )
    parser.add_argument(
        "--ocr",
        action="store_true",
        help="Active l'OCR pour les images via Tesseract."
    )
    parser.add_argument(
        "--ocr-lang",
        default=None,
        help="Langues pour Tesseract (ex: 'fra', 'eng', 'fra+eng')."
    )
    parser.add_argument(
        "--tesseract-cmd",
        default=None,
        help="Chemin personnalisé vers tesseract.exe."
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Forcer le lancement de l'interface graphique."
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