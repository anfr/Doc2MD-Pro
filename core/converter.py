import io
import logging
from pathlib import Path
from typing import Optional

import pandas as pd

from config import MAX_LIGNES_EXCEL, MAX_COLONNES_EXCEL

# --- Initialisation des moteurs (lazy loading) ---
try:
    from markitdown import MarkItDown
    _MARKITDOWN_OK = True
except ImportError:
    _MARKITDOWN_OK = False

try:
    import pymupdf
    import pytesseract
    from PIL import Image
    _OCR_OK = True
except ImportError:
    _OCR_OK = False


class ConversionError(Exception):
    """Exception personnalisée pour les erreurs de conversion."""
    pass


class DocumentConverter:
    """Gère l'extraction de texte brut à partir de fichiers (PDF, Word, Excel)."""

    def __init__(self) -> None:
        self.md_converter = MarkItDown() if _MARKITDOWN_OK else None

    def convertir(self, path_fichier: Path, use_ocr: bool = False) -> str:
        """Convertit un fichier en texte brut.
        
        Args:
            path_fichier: Le chemin vers le fichier source.
            use_ocr: Si True, utilise l'OCR pour les PDF (plus lent).
            
        Returns:
            Le texte brut extrait.
            
        Raises:
            ConversionError: Si la conversion échoue.
        """
        ext = path_fichier.suffix.lower()

        if ext == '.pdf' and use_ocr:
            if not _OCR_OK:
                raise ConversionError("L'OCR est coché, mais les dépendances (pymupdf, pytesseract, Pillow) ne sont pas installées.")
            return self._convertir_pdf_ocr(path_fichier)

        if ext in ('.xlsx', '.xls'):
            return self._convertir_excel(path_fichier)

        if self.md_converter is None:
            raise ConversionError("markitdown non installé. Exécutez : pip install markitdown")

        try:
            return self.md_converter.convert(str(path_fichier)).text_content
        except Exception as e:
            raise ConversionError(f"Erreur markitdown : {e}") from e

    def _convertir_pdf_ocr(self, path_fichier: Path) -> str:
        """Extrait le texte d'un PDF via OCR (Tesseract)."""
        doc = pymupdf.open(path_fichier)
        texte_total = f"# Document (OCR) : {path_fichier.name}\n\n"

        for page in doc:
            pix = page.get_pixmap(dpi=300)
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            texte_page = pytesseract.image_to_string(img, lang="fra+eng")
            texte_total += texte_page + "\n\n"

        doc.close()
        return texte_total

    def _convertir_excel(self, path_fichier: Path) -> str:
        """Convertit un fichier Excel en tableaux Markdown."""
        md = f"# Document Excel : {path_fichier.name}\n\n"
        try:
            excel_file = pd.ExcelFile(path_fichier)
        except Exception as e:
            raise ConversionError(f"Impossible d'ouvrir l'Excel (xlrd manquant ?) : {e}") from e

        for sheet in excel_file.sheet_names:
            try:
                df = pd.read_excel(excel_file, sheet_name=sheet)
            except Exception as e:
                md += f"## Onglet : {sheet}\n\n[Erreur : {e}]\n\n"
                continue

            df = self._preparer_dataframe(df)
            if df.empty:
                continue

            md += f"## Onglet : {sheet}\n\n"
            if len(df.columns) > MAX_COLONNES_EXCEL:
                df = df.iloc[:, :MAX_COLONNES_EXCEL]
            if len(df) > MAX_LIGNES_EXCEL:
                df = df.head(MAX_LIGNES_EXCEL)

            md += self._dataframe_to_markdown(df) + "\n\n" + "-" * 40 + "\n\n"

        return md

    @staticmethod
    def _preparer_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """Nettoie le DataFrame (supprime lignes/colonnes vides, renomme colonnes)."""
        df = df.dropna(how="all").dropna(axis=1, how="all")
        df.columns = [
            str(c).strip() if not str(c).strip().startswith("Unnamed") else f"colonne_{i+1}"
            for i, c in enumerate(df.columns)
        ]
        return df

    @staticmethod
    def _dataframe_to_markdown(df: pd.DataFrame) -> str:
        """Génère un tableau Markdown, avec fallback manuel si tabulate manque."""
        try:
            return df.to_markdown(index=False)
        except Exception:
            def _fmt(val) -> str:
                return "" if pd.isna(val) else str(val).replace("\n", " ").replace("|", "\\|").strip()

            colonnes = [str(c).replace("|", "\\|") for c in df.columns]
            lignes = ["| " + " | ".join(colonnes) + " |", "|" + "|".join(["---"] * len(colonnes)) + "|"]
            for _, row in df.iterrows():
                lignes.append("| " + " | ".join(_fmt(v) for v in row) + " |")
            return "\n".join(lignes)