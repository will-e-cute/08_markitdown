# MarkItDown GUI

Une interface graphique PySide6 pour convertir des documents (PDF, Word, Images) en Markdown en utilisant [MarkItDown](https://github.com/microsoft/markitdown) avec support OCR optionnel via Tesseract.

## Fonctionnalités

- **Sélection de fichier unique** ou **dossier complet** pour la conversion
- **Option récursive** pour inclure les sous-dossiers
- **Dossier de sortie personnalisable** (par défaut: `%USER%\Documents\Markitdown`)
- **OCR optionnel** pour les images (JPG, PNG, BMP, GIF, TIFF, WebP) via Tesseract (français + anglais)
- **Fenêtre de progression** avec barre de progression, fichier en cours et journal détaillé
- **Annulation possible** pendant la conversion
- **Gestion des doublons** : `fichier.md` → `fichier_1.md` → `fichier_2.md`...

## Formats supportés

| Format | Méthode |
|--------|---------|
| PDF | MarkItDown |
| Word (.docx, .doc) | MarkItDown |
| Images (.jpg, .jpeg, .png, .bmp, .gif, .tiff, .webp) | MarkItDown (métadonnées) ou OCR (texte) |

## Installation

### Prérequis

1. **Python 3.10+**
2. **Tesseract OCR** (optionnel, pour l'OCR sur images) :
   - Windows : Télécharger depuis [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki)
   - Chemin par défaut attendu : `C:\Program Files\Tesseract-OCR\tesseract.exe`

### Installation des dépendances Python

```bash
pip install -r requirements.txt
```

Ou manuellement :
```bash
pip install markitdown PySide6 pytesseract Pillow
```

## Utilisation

```bash
python main.py
```

### Interface

1. **Sélectionner un fichier** : Choisir un fichier unique à convertir
2. **Sélectionner un dossier** : Choisir un dossier (tous les fichiers supportés seront convertis)
3. **Inclure les sous-dossiers** : Coché par défaut pour parcours récursif
4. **Activer l'OCR** : Décoché par défaut, active l'extraction de texte sur les images
5. **Dossier de sortie** : Modifier si nécessaire (bouton "Changer")
6. **Lancer la conversion** : Démarre le traitement dans une fenêtre modale

## Structure du projet

```
markitdown-gui/
├── main.py              # Point d'entrée
├── requirements.txt     # Dépendances Python
├── core/                # Logique de conversion
│   ├── __init__.py
│   └── converter.py     # ConversionWorker (thread + OCR)
└── gui/                 # Interface utilisateur
    ├── __init__.py
    ├── main_window.py   # Fenêtre principale
    └── progress_dialog.py # Fenêtre de progression
```

## Développement

### Lancer en mode développement

```bash
python main.py
```

### Tester sans interface graphique (headless)

```bash
QT_QPA_PLATFORM=offscreen python -c "from gui.main_window import MainWindow; print('OK')"
```

## Dépannage

### OCR non disponible
- Vérifiez que Tesseract est installé à `C:\Program Files\Tesseract-OCR\tesseract.exe`
- Ou modifiez le chemin dans `core/converter.py`

### Erreur de police Qt
```
QFontDatabase: Cannot find font directory...
```
C'est un avertissement benign, l'application fonctionne normalement.

## Licence

MIT