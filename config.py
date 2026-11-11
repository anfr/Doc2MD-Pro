import re
from pathlib import Path

# Extensions supportées
EXTENSIONS_VALIDES = {'.pdf', '.xlsx', '.xls', '.docx'}

# Limites d'extraction Excel
MAX_LIGNES_EXCEL = 500
MAX_COLONNES_EXCEL = 30

# Avertissements et UI
AVERTISSEMENT_MO = 50
AVERTISSEMENT_FICHIERS = 100
APERCU_MAX_CHARS = 3000

# Tokens et Chunking
CHARS_PAR_TOKEN = 4
CHUNK_SIZE_DEFAULT = 1500
CHUNK_OVERLAP_DEFAULT = 200

# --- Paramètres pour l'Heuristique Excel ---
EXCEL_MODE_AUTO = "Automatique"
EXCEL_MODE_VISUEL = "Visuel (Conserver la mise en page)"
EXCEL_MODE_DATA = "Données (Base de données)"
EXCEL_MODE_SEMANTIQUE = "Sémantique (Optimisé IA)" # <-- NOUVEAU

EXCEL_SEUIL_DENSITE = 0.45       
EXCEL_SEUIL_VERTICAL = 3         
EXCEL_SEUIL_ENTETE_VIDE = 0.2    

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