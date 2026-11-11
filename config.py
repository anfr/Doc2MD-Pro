import re
from pathlib import Path

# Extensions
EXTENSIONS_VALIDES = {'.pdf', '.xlsx', '.xls', '.docx'}

# Limites
MAX_LIGNES_EXCEL = 500
MAX_COLONNES_EXCEL = 30
AVERTISSEMENT_MO = 50
AVERTISSEMENT_FICHIERS = 100
APERCU_MAX_CHARS = 3000
CHARS_PAR_TOKEN = 4

# Chemins
PREF_FILE = Path.home() / ".doc2md" / "prefs.json"

# Regex
RE_PUCE = re.compile(r"^[\s]*[●•▪◦‣⁃]\s+", re.MULTILINE)
RE_NUM_PAGE = re.compile(r"^\s*\d{1,3}\s*$", re.MULTILINE)
RE_SEP = re.compile(r"^[-=*_]{3,}\s*$", re.MULTILINE)
RE_ESPACE_FIN = re.compile(r"[ \t]+$", re.MULTILINE)
RE_LIGNES_VIDES = re.compile(r"\n{3,}")
RE_TITRE = re.compile(r"^(#{1,6})([^\s#])", re.MULTILINE)
RE_IMG_MD = re.compile(r"!\[([^\]]*)\]\([^)]+\)")
RE_IMG_HTML = re.compile(r"<img[^>]+>", re.IGNORECASE)
# Chunking RAG
CHUNK_SIZE_DEFAULT = 1500  # Taille approximative en caractères
CHUNK_OVERLAP_DEFAULT = 200 # Chevauchement entre les chunks