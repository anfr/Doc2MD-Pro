import json
from pathlib import Path
from typing import Any, Dict
from config import PREF_FILE, CHARS_PAR_TOKEN


def est_fichier_ignorable(path: Path) -> bool:
    """Vérifie si un fichier est temporaire ou système (ex: ~$fichier.docx)."""
    return path.name.startswith(('.', '~$'))


def estimer_tokens(texte: str) -> int:
    """Estimation rapide du nombre de tokens (~4 caractères = 1 token).
    
    Args:
        texte: La chaîne de caractères à analyser.
        
    Returns:
        Le nombre de tokens estimés.
    """
    if not texte:
        return 0
    return max(1, len(texte) // CHARS_PAR_TOKEN)


class Preferences:
    """Gestionnaire de sauvegarde des préférences utilisateur (JSON local)."""

    def __init__(self) -> None:
        self.data: Dict[str, Any] = {}
        self._charger()

    def _charger(self) -> None:
        """Charge les préférences depuis le disque, ou initialise un dict vide."""
        try:
            if PREF_FILE.exists():
                self.data = json.loads(PREF_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, IOError):
            self.data = {}

    def get(self, key: str, default: Any = None) -> Any:
        """Récupère une valeur, avec valeur par défaut si absente."""
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Définit une valeur en mémoire."""
        self.data[key] = value

    def sauvegarder(self) -> None:
        """Écrit les préférences sur le disque de manière sécurisée."""
        try:
            PREF_FILE.parent.mkdir(parents=True, exist_ok=True)
            PREF_FILE.write_text(
                json.dumps(self.data, ensure_ascii=False, indent=2), 
                encoding="utf-8"
            )
        except IOError:
            pass  # On ignore silencieusement les erreurs d'écriture de préférences