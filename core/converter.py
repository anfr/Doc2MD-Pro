import io
import re
from pathlib import Path
import pandas as pd

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

try:
    import openpyxl
    _OPENPYXL_OK = True
except ImportError:
    _OPENPYXL_OK = False

from config import (
    MAX_LIGNES_EXCEL, MAX_COLONNES_EXCEL, EXCEL_MODE_AUTO, EXCEL_MODE_VISUEL, 
    EXCEL_MODE_DATA, EXCEL_MODE_SEMANTIQUE, EXCEL_SEUIL_DENSITE, 
    EXCEL_SEUIL_VERTICAL, EXCEL_SEUIL_ENTETE_VIDE
)


class ConversionError(Exception):
    pass


class DocumentConverter:
    def __init__(self) -> None:
        self.md_converter = MarkItDown() if _MARKITDOWN_OK else None

    def convertir(self, path_fichier: Path, use_ocr: bool = False, excel_mode: str = EXCEL_MODE_AUTO) -> str:
        ext = path_fichier.suffix.lower()

        if ext == '.pdf' and use_ocr:
            if not _OCR_OK:
                raise ConversionError("L'OCR est coché, mais les dépendances ne sont pas installées.")
            return self._convertir_pdf_ocr(path_fichier)

        if ext in ('.xlsx', '.xls'):
            return self._convertir_excel(path_fichier, excel_mode)

        if self.md_converter is None:
            raise ConversionError("markitdown non installé. Exécutez : pip install markitdown")

        try:
            return self.md_converter.convert(str(path_fichier)).text_content
        except Exception as e:
            raise ConversionError(f"Erreur markitdown : {e}") from e

    def _convertir_pdf_ocr(self, path_fichier: Path) -> str:
        doc = pymupdf.open(path_fichier)
        texte_total = f"# Document (OCR) : {path_fichier.name}\n\n"
        for page in doc:
            pix = page.get_pixmap(dpi=300)
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            texte_total += pytesseract.image_to_string(img, lang="fra+eng") + "\n\n"
        doc.close()
        return texte_total

    # ======================================================================
    # MOTEUR EXCEL AVEC HEURISTIQUE & EXTRACTION SÉMANTIQUE
    # ======================================================================
    def _convertir_excel(self, path_fichier: Path, mode_force: str = EXCEL_MODE_AUTO) -> str:
        md = f"# Document Excel : {path_fichier.name}\n\n"
        try:
            excel_file = pd.ExcelFile(path_fichier)
        except Exception as e:
            raise ConversionError(f"Impossible d'ouvrir l'Excel : {e}") from e

        for sheet in excel_file.sheet_names:
            try:
                df_brut = pd.read_excel(excel_file, sheet_name=sheet, header=None)
            except Exception as e:
                md += f"## Onglet : {sheet}\n\n[Erreur : {e}]\n\n"
                continue

            if df_brut.empty:
                continue

            if mode_force == EXCEL_MODE_AUTO:
                mode_retenu = self._detecter_mode_excel(df_brut, path_fichier, sheet)
            else:
                mode_retenu = mode_force

            md += f"## Onglet : {sheet} (Mode : {mode_retenu.split(' ')[0]})\n\n"

            if mode_retenu == EXCEL_MODE_SEMANTIQUE:
                md += self._extraire_semantique_excel(df_brut)
            elif mode_retenu == EXCEL_MODE_VISUEL:
                df = df_brut.fillna("")
                df = df.replace('\n', '<br>', regex=True)
                if len(df.columns) > MAX_COLONNES_EXCEL:
                    df = df.iloc[:, :MAX_COLONNES_EXCEL]
                if len(df) > MAX_LIGNES_EXCEL:
                    df = df.head(MAX_LIGNES_EXCEL)
                md += self._dataframe_to_markdown(df, has_header=False)
            else:
                try:
                    df = pd.read_excel(excel_file, sheet_name=sheet)
                except Exception:
                    df = df_brut
                df = self._preparer_dataframe(df)
                if not df.empty:
                    if len(df.columns) > MAX_COLONNES_EXCEL:
                        df = df.iloc[:, :MAX_COLONNES_EXCEL]
                    if len(df) > MAX_LIGNES_EXCEL:
                        df = df.head(MAX_LIGNES_EXCEL)
                    md += self._dataframe_to_markdown(df, has_header=True)

            md += "\n\n" + "-" * 40 + "\n\n"

        return md

    def _detecter_mode_excel(self, df: pd.DataFrame, path_fichier: Path, sheet_name: str) -> str:
        score_visuel = 0

        total_cellules = df.size
        cellules_remplies = df.notna().sum().sum()
        densite = cellules_remplies / total_cellules if total_cellules > 0 else 0
        if densite < EXCEL_SEUIL_DENSITE:
            score_visuel += 1

        premiere_ligne = df.iloc[0]
        taux_vides_entete = premiere_ligne.isna().sum() / len(premiere_ligne)
        if taux_vides_entete > EXCEL_SEUIL_ENTETE_VIDE:
            score_visuel += 1

        if path_fichier.suffix.lower() == ".xlsx" and _OPENPYXL_OK:
            try:
                wb = openpyxl.load_workbook(path_fichier, read_only=True)
                ws = wb[sheet_name]
                cellules_verticales = 0
                for row in ws.iter_rows():
                    for cell in row:
                        if cell.alignment and cell.alignment.textRotation in (90, 180, 270):
                            cellules_verticales += 1
                        if cellules_verticales > EXCEL_SEUIL_VERTICAL:
                            break
                    if cellules_verticales > EXCEL_SEUIL_VERTICAL:
                        break
                wb.close()
                if cellules_verticales > EXCEL_SEUIL_VERTICAL:
                    score_visuel += 2
            except Exception:
                pass

        if score_visuel >= 2:
            return EXCEL_MODE_VISUEL
        return EXCEL_MODE_DATA

    # ----------------------------------------------------------------------
    # L'EXTRACTION SÉMANTIQUE (Version 3 : Pauses + Footer + Nettoyage)
    # ----------------------------------------------------------------------
    @staticmethod
    def _extraire_semantique_excel(df: pd.DataFrame) -> str:
        """Transforme une grille visuelle en un texte hiérarchique lisible par un LLM."""
        df = df.fillna("")

        # 1. Trouver la ligne d'en-tête
        header_idx = -1
        for i in range(min(15, len(df))):
            row_str = df.iloc[i].astype(str).tolist()
            non_empty = [s.strip() for s in row_str if s.strip()]
            if len(non_empty) >= 2 and sum(1 for s in non_empty if not re.match(r'^\d', s)) >= len(non_empty) / 2:
                header_idx = i
                break

        if header_idx == -1:
            return "*(Impossible d'extraire l'en-tête. Tableau non structuré.)*\n\n" + df.to_markdown(index=False, headers=None)

        # 2. Fusion intelligente des en-têtes
        primary_headers = df.iloc[header_idx].tolist()
        secondary_headers = df.iloc[header_idx + 1].tolist() if header_idx + 1 < len(df) else [""] * len(df.columns)

        merged_headers = []
        current_primary = ""
        for i in range(len(df.columns)):
            p = str(primary_headers[i]).strip()
            s = str(secondary_headers[i]).strip()
            if p:
                current_primary = p
            if current_primary:
                header_name = current_primary
                if s and not re.match(r'^\d{1,2}:\d{2}', s):
                    header_name += f" ({s})"
                merged_headers.append(header_name)
            else:
                merged_headers.append("")

        # 3. Identifier la colonne des heures
        time_col = -1
        max_times = 0
        for c in range(len(df.columns)):
            count = df[c].astype(str).str.contains(r'\d{1,2}:\d{2}').sum()
            if count > max_times:
                max_times = count
                time_col = c

        context_col = 0

        # 4. Forward Fill
        df[context_col] = df[context_col].replace("", pd.NA).ffill().fillna("")
        if time_col != -1:
            df[time_col] = df[time_col].replace("", pd.NA).ffill().fillna("")

        # 5. Générer le Markdown
        md = "*(Format linéaire optimisé pour le RAG)*\n\n"

        current_block = None
        footer_notes = []
        seen_pauses = set()

        for r in range(header_idx + 2, len(df)):
            # --- CORRECTION FINALE : Détection du Footer dans TOUTES les colonnes ---
            footer_parts = []
            for c in range(len(df.columns)):
                val = str(df.iloc[r, c]).strip()
                # On garde le texte, sauf s'il s'agit d'une heure ou d'un contexte
                if val and not re.match(r'^\d{1,2}:\d{2}', val) and val not in ["Matinée", "Après-midi"]:
                    footer_parts.append(val)
            
            row_text = " ".join(footer_parts)
            mots_cles_footer = ["Professeure", "Directeur", "Inspecteur", "Signature"]
            
            if any(mot in row_text for mot in mots_cles_footer):
                footer_notes.append(row_text)
                continue

            context = str(df.iloc[r, context_col]).strip()
            time_val = str(df.iloc[r, time_col]).strip() if time_col != -1 else ""

            # Détection des pauses
            if time_val and not re.search(r'\d{1,2}:\d{2}', time_val):
                if time_val not in seen_pauses:
                    md += f"\n### 🕒 {time_val}\n"
                    seen_pauses.add(time_val)
                continue

            subjects = []
            for c in range(len(df.columns)):
                if c in [context_col, time_col]:
                    continue
                cell_text = str(df.iloc[r, c]).replace('\n', ' ').replace('<br>', ' ').strip()
                cell_text = re.sub(r'\s+', ' ', cell_text)

                if cell_text:
                    day_name = merged_headers[c]
                    if day_name:
                        subjects.append(f"  - **{day_name}** : {cell_text}")

            if subjects:
                block_title = f"{context} - {time_val}" if time_val else context

                if block_title != current_block:
                    md += f"\n### {block_title}\n"
                    current_block = block_title

                md += "\n".join(subjects) + "\n"

        if footer_notes:
            md += "\n### 📝 Informations complémentaires\n"
            for note in footer_notes:
                md += f"- {re.sub(r'\s+', ' ', note)}\n"

        return md

    @staticmethod
    def _preparer_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        df = df.dropna(how="all").dropna(axis=1, how="all")
        df.columns = [
            str(c).strip() if not str(c).strip().startswith("Unnamed") else f"colonne_{i+1}"
            for i, c in enumerate(df.columns)
        ]
        return df

    @staticmethod
    def _dataframe_to_markdown(df: pd.DataFrame, has_header: bool = True) -> str:
        try:
            return df.to_markdown(index=False, headers="keys" if has_header else None)
        except Exception:
            def _fmt(val):
                return "" if pd.isna(val) else str(val).replace("|", "\\|").strip()

            colonnes = [str(c).replace("|", "\\|") for c in df.columns] if has_header else [f"Col {i+1}" for i in range(len(df.columns))]
            lignes = []
            if has_header:
                lignes.append("| " + " | ".join(colonnes) + " |")
                lignes.append("|" + "|".join(["---"] * len(colonnes)) + "|")
            for _, row in df.iterrows():
                lignes.append("| " + " | ".join(_fmt(v) for v in row) + " |")
            return "\n".join(lignes)