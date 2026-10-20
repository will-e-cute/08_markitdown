# MarkItDown GUI & CLI

Une application moderne en **PySide6** (avec support **CLI**) pour convertir rapidement tous vos documents (PDF, Office, Tableurs, Présentations, Web, Audio, Images) en **Markdown** propre grâce à [MarkItDown](https://github.com/microsoft/markitdown) et support OCR via [Tesseract](https://github.com/tesseract-ocr/tesseract).

---

## 🌟 Fonctionnalités Clés

- **Glisser-Déposer (Drag & Drop)** : Déposez directement vos fichiers ou dossiers dans l'application.
- **Sélection multiple** : Sélectionnez plusieurs fichiers ou dossiers simultanément.
- **Support étendu de formats** : PDF, Word, Excel, PowerPoint, HTML, Notebooks Jupyter, E-books, Emails Outlook, Audio, et Données tabulaires.
- **Respect de l'arborescence** : Option pour conserver la hiérarchie des sous-dossiers dans le dossier de sortie ou regrouper à plat.
- **OCR Intelligent** : Détection automatique de Tesseract (PATH système et répertoires standards Windows), configuration possible du chemin et sélection automatique des langues disponibles.
- **Visionneuse Markdown intégrée** : Prévisualisation immédiate avec rendu visuel et code source brut, avec bouton de copie et ouverture dans l'éditeur système.
- **Sécurité & Annulation propre** : Annulation réactive et fermeture sécurisée évitant tout crash de thread en arrière-plan.
- **Persistance des préférences** : Mémorisation automatique du dossier de sortie et des options via `QSettings`.
- **Mode Ligne de Commande (CLI)** : Conversion par lots sans interface graphique pour les scripts et pipelines d'automatisation.

---

## 📁 Formats Supportés

| Catégorie | Extensions | Méthode de conversion |
| :--- | :--- | :--- |
| **Documents & PDF** | `.pdf`, `.docx`, `.doc` | MarkItDown (extraction texte & structure) |
| **Tableurs & Données** | `.xlsx`, `.xls`, `.csv`, `.json`, `.xml` | MarkItDown (tableaux Markdown) |
| **Présentations** | `.pptx`, `.ppt` | MarkItDown (sections et diapositives) |
| **Web & E-books** | `.html`, `.htm`, `.xhtml`, `.epub`, `.ipynb` | MarkItDown (HTML vers Markdown) |
| **Messagerie & Archives** | `.msg`, `.zip` | MarkItDown |
| **Images** | `.jpg`, `.jpeg`, `.png`, `.bmp`, `.webp`, `.tiff` | Métadonnées ou OCR complet (Tesseract) |
| **Audio** | `.wav`, `.mp3` | Transcription audio MarkItDown |

---

## 💻 Installation

### 1. Prérequis
- **Python 3.10+** (testé sur Python 3.12)
- **Tesseract OCR** (optionnel, pour l'OCR d'images) :
  - Windows : Télécharger depuis [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki).
  - Détecté automatiquement dans le `PATH` ou `C:\Program Files\Tesseract-OCR\tesseract.exe`.

### 2. Installation des dépendances
```bash
pip install -r requirements.txt
```

---

## 🚀 Utilisation

### Mode Interface Graphique (GUI)

Lancez l'interface simplement avec :
```bash
python main.py
```
*(ou double-cliquez sur `main.pyw` sous Windows pour lancer sans fenêtre de terminal)*

1. Glissez-déposez des fichiers/dossiers ou utilisez **« Ajouter des fichiers »** / **« Ajouter un dossier »**.
2. Ajustez vos options :
   - *Inclure les sous-dossiers (récursif)*
   - *Conserver l'arborescence des sous-dossiers*
   - *Activer l'OCR pour les images*
3. Choisissez le dossier de destination (ou conservez celui par défaut).
4. Cliquez sur **« 🚀 Lancer la conversion »**.
5. À la fin, consultez le journal, ouvrez le dossier généré ou cliquez sur **« 👁️ Aperçu Markdown »**.

---

### Mode Ligne de Commande (CLI)

Vous pouvez convertir des fichiers directement sans ouvrir la fenêtre graphique :

```bash
# Convertir un fichier unique
python main.py document.pdf -o ./output

# Convertir un dossier récursivement en conservant l'arborescence
python main.py ./documents -o ./output --preserve-structure

# Convertir avec OCR activé
python main.py scan.png -o ./output --ocr --ocr-lang fra+eng

# Voir toutes les options
python main.py --help
```

---

## 🏗️ Structure du Projet

```
08_markitdown/
├── main.py                # Point d'entrée principal (GUI et CLI)
├── main.pyw               # Lanceur GUI silencieux (sans console Windows)
├── requirements.txt       # Dépendances du projet
├── pytest.ini             # Configuration de la suite de tests
├── .gitignore             # Exclusion des fichiers temporaires et caches
├── core/                  # Moteur métier
│   ├── __init__.py
│   └── converter.py       # Scan O(N), ConversionWorker (QThread), gestion OCR
├── gui/                   # Interface utilisateur PySide6
│   ├── __init__.py
│   ├── main_window.py     # Fenêtre principale (Drag&Drop, options, QSettings)
│   ├── progress_dialog.py # Dialogue modal de progression et actions post-conversion
│   └── markdown_viewer.py # Visionneuse de fichiers Markdown
└── tests/                 # Suite de tests unitaires (pytest)
    ├── test_scanner.py
    ├── test_converter.py
    └── test_cli.py
```

---

## 🧪 Tests Automatisés

Pour exécuter la suite de tests :
```bash
pytest -v
```

---

## 📄 Licence

MIT License