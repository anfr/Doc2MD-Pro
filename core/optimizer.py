import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict
from version import __version__

from config import (
    RE_PUCE, RE_NUM_PAGE, RE_SEP, RE_ESPACE_FIN, RE_LIGNES_VIDES, RE_TITRE, 
    RE_IMG_MD, RE_IMG_HTML, CHUNK_OVERLAP_DEFAULT
)
from utils import estimer_tokens


def optimiser_markdown(md: str) -> str:
    """Nettoie le Markdown des artefacts de conversion (PDF/Word).
    
    Corrige les ligatures, les puces, les numéros de page isolés,
    et compresse les lignes vides multiples.
    """
    if not md:
        return ""

    md = unicodedata.normalize("NFKC", md)
    md = md.replace("\u00a0", " ").replace("\u200b", "").replace("\u00ad", "")
    md = RE_PUCE.sub("- ", md)

    lignes = md.split("\n")
    resultat = []
    dans_bloc_code = False

    for ligne in lignes:
        strip = ligne.strip()
        if strip.startswith("```"):
            dans_bloc_code = not dans_bloc_code
            resultat.append(ligne)
            continue
        if dans_bloc_code:
            resultat.append(ligne)
            continue
        if RE_NUM_PAGE.match(ligne) or RE_SEP.match(ligne):
            continue
        resultat.append(RE_ESPACE_FIN.sub("", ligne))

    md = "\n".join(resultat)
    md = RE_LIGNES_VIDES.sub("\n\n", md)
    md = RE_TITRE.sub(r"\1 \2", md)
    
    return md.strip() + "\n"


def ajouter_metadonnees(md: str, source: Path) -> str:
    """Ajoute un front-matter YAML exploitable par un LLM."""
    entete = (
        f"---\n"
        f"source: \"{source.name}\"\n"
        f"type: {source.suffix.lstrip('.').lower()}\n"
        f"doc2md_version: {__version__}\n"
        f"converti_le: {datetime.now().isoformat(timespec='seconds')}\n"
        f"mots: {len(md.split())}\n"
        f"tokens_estimes: {estimer_tokens(md)}\n"
        f"---\n\n"
    )
    return entete + md


def verifier_qualite(md: str, source: Path) -> Optional[str]:
    """Détecte les sorties suspectes et retourne un avertissement ou None."""
    taille = len(md.strip())
    if taille == 0:
        return "⚠️ Aucun texte extrait."
    if source.suffix.lower() == ".pdf" and taille < 500:
        return "⚠️ Sortie courte — PDF probablement scanné (essayez l'OCR)."
    return None


def retirer_images(md: str) -> str:
    """Supprime les références d'images Markdown et HTML."""
    return RE_IMG_HTML.sub("", RE_IMG_MD.sub("", md))


def decouper_markdown(md: str, max_chars: int = 1500, overlap: int = CHUNK_OVERLAP_DEFAULT) -> List[Dict[str, str]]:
    """Découpe intelligemment un Markdown en chunks pour une base vectorielle (RAG).
    
    Args:
        md: Le texte Markdown complet.
        max_chars: Taille maximale d'un chunk.
        overlap: Nombre de caractères de chevauchement entre deux chunks.
        
    Returns:
        Une liste de dictionnaires contenant 'header' et 'text'.
    """
    if not md.strip():
        return []

    chunks = []
    sections = re.split(r'(?=\n#{1,3} )', "\n" + md)
    current_chunk = ""
    current_header = "Introduction"

    for section in sections:
        if not section.strip():
            continue

        match = re.match(r'\n(#{1,3})\s+(.+)', section)
        if match:
            current_header = match.group(2).strip()

        if len(current_chunk) + len(section) > max_chars:
            if current_chunk.strip():
                chunks.append({"header": current_header, "text": current_chunk.strip()})

            if len(section) > max_chars:
                paragraphes = section.split('\n\n')
                temp_chunk = ""
                for p in paragraphes:
                    if len(temp_chunk) + len(p) > max_chars:
                        if temp_chunk.strip():
                            chunks.append({"header": current_header, "text": temp_chunk.strip()})
                        overlap_text = temp_chunk[-overlap:] if len(temp_chunk) > overlap else ""
                        temp_chunk = overlap_text + "\n\n" + p
                    else:
                        temp_chunk += "\n\n" + p if temp_chunk else p
                current_chunk = temp_chunk
            else:
                overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else ""
                current_chunk = overlap_text + "\n" + section
        else:
            current_chunk += "\n" + section

    if current_chunk.strip():
        chunks.append({"header": current_header, "text": current_chunk.strip()})

    return chunks