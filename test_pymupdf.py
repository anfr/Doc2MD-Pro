"""
Script de test comparatif : markitdown vs PyMuPDF.
Usage : python test_pymupdf.py "chemin/vers/fichier.pdf"

Dépendance : pip install pymupdf markitdown
"""

import sys
import time
from pathlib import Path

try:
    import fitz  # PyMuPDF
    _PYMUPDF_OK = True
except ImportError:
    _PYMUPDF_OK = False

try:
    from markitdown import MarkItDown
    _MARKITDOWN_OK = True
except ImportError:
    _MARKITDOWN_OK = False


# Artefacts typiques d'une police custom mal encodée
ARTEFACTS = ["prtnt", "prlnt", "prin.t", "pritnt", "■", "w*h*i*l*e", "*p*r*i*n*t"]


def extraire_markitdown(path: Path) -> tuple[str, float]:
    if not _MARKITDOWN_OK:
        return "[markitdown non installé]", 0.0
    t0 = time.perf_counter()
    md = MarkItDown().convert(str(path)).text_content
    return md, time.perf_counter() - t0


def extraire_pymupdf(path: Path) -> tuple[str, float]:
    if not _PYMUPDF_OK:
        return "[pymupdf non installé]", 0.0
    t0 = time.perf_counter()
    doc = fitz.open(path)
    texte = "\n\n".join(page.get_text("text") for page in doc)
    doc.close()
    return texte, time.perf_counter() - t0


def analyser(nom: str, texte: str, duree: float):
    print(f"\n{'=' * 60}")
    print(f"  {nom}")
    print(f"{'=' * 60}")
    print(f"  Durée       : {duree:.2f} s")
    print(f"  Caractères  : {len(texte):,}")
    print(f"  Mots        : {len(texte.split()):,}")
    print(f"  Lignes      : {texte.count(chr(10)) + 1:,}")

    print(f"\n  Artefacts détectés :")
    total = 0
    for a in ARTEFACTS:
        n = texte.count(a)
        if n:
            total += n
            print(f"    {a!r:20} → {n:>5} occurrences")
    if total == 0:
        print(f"    (aucun) ✓")
    print(f"    TOTAL artefacts : {total}")

    # Extrait significatif : chercher le print("Hello, World!")
    print(f"\n  Extrait (recherche 'Hello, World') :")
    idx = texte.find("Hello, World")
    if idx >= 0:
        extrait = texte[max(0, idx - 60):idx + 60].replace("\n", " ⏎ ")
        print(f"    …{extrait}…")
    else:
        print("    [non trouvé]")
    print()


def main():
    if len(sys.argv) != 2:
        print("Usage : python test_pymupdf.py chemin/vers/fichier.pdf")
        sys.exit(1)

    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"Fichier introuvable : {path}")
        sys.exit(1)

    if not _PYMUPDF_OK:
        print("⚠️  PyMuPDF non installé. Exécute : pip install pymupdf")
    if not _MARKITDOWN_OK:
        print("⚠️  markitdown non installé.")

    print(f"Fichier : {path.name}")
    print(f"Taille  : {path.stat().st_size / (1024 * 1024):.1f} Mo")

    # Test 1 : markitdown
    if _MARKITDOWN_OK:
        md_txt, md_time = extraire_markitdown(path)
        analyser("MARKITDOWN", md_txt, md_time)
    else:
        md_txt, md_time = "", 0.0

    # Test 2 : PyMuPDF
    if _PYMUPDF_OK:
        mu_txt, mu_time = extraire_pymupdf(path)
        analyser("PYMUPDF", mu_txt, mu_time)
    else:
        mu_txt, mu_time = "", 0.0

    # Verdict comparatif
    if md_txt and mu_txt:
        print(f"\n{'=' * 60}")
        print(f"  VERDICT")
        print(f"{'=' * 60}")
        md_art = sum(md_txt.count(a) for a in ARTEFACTS)
        mu_art = sum(mu_txt.count(a) for a in ARTEFACTS)
        print(f"  Vitesse   : ", end="")
        if mu_time < md_time:
            print(f"PyMuPDF gagne ({mu_time:.1f}s vs {md_time:.1f}s)")
        else:
            print(f"markitdown gagne ({md_time:.1f}s vs {mu_time:.1f}s)")
        print(f"  Artefacts : ", end="")
        if mu_art < md_art:
            print(f"PyMuPDF gagne ({mu_art} vs {md_art}) ✓")
        elif md_art < mu_art:
            print(f"markitdown gagne ({md_art} vs {mu_art})")
        else:
            print(f"Égalité ({md_art} chacun)")

    # Sauvegarde des deux sorties pour inspection manuelle
    dossier = path.parent
    if md_txt:
        (dossier / f"{path.stem}_MARKITDOWN.txt").write_text(md_txt, encoding="utf-8")
        print(f"\n  Sortie markitdown : {path.stem}_MARKITDOWN.txt")
    if mu_txt:
        (dossier / f"{path.stem}_PYMUPDF.txt").write_text(mu_txt, encoding="utf-8")
        print(f"  Sortie PyMuPDF    : {path.stem}_PYMUPDF.txt")


if __name__ == "__main__":
    main()