import json
import threading
import concurrent.futures
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

from config import EXTENSIONS_VALIDES
from utils import est_fichier_ignorable
from core.converter import DocumentConverter, ConversionError
from core.optimizer import (
    optimiser_markdown, ajouter_metadonnees, verifier_qualite, 
    retirer_images, decouper_markdown
)


def _worker_convertir(args: Tuple[Path, int, Dict[str, Any], Optional[Path], str]) -> Dict[str, Any]:
    """Fonction exécutée dans un processus séparé pour convertir un fichier.
    
    Args:
        args: Un tuple contenant (fichier, index, options, dest_folder, nom_sortie).
        
    Returns:
        Un dictionnaire contenant le statut de la conversion.
    """
    fichier, _, options, dest_folder, nom_sortie_unique = args

    try:
        converter = DocumentConverter()
        md_raw = converter.convertir(fichier, use_ocr=options.get('ocr', False))
        avert = verifier_qualite(md_raw, fichier)

        md = md_raw
        if fichier.suffix.lower() == ".docx" and options.get('retirer_images'):
            md = retirer_images(md)
        if options.get('nettoyage'):
            md = optimiser_markdown(md)
        if options.get('metadonnees'):
            md = ajouter_metadonnees(md, fichier)

        dossier_cible = dest_folder if dest_folder else fichier.parent
        dossier_cible.mkdir(parents=True, exist_ok=True)
        chemin_sortie = dossier_cible / nom_sortie_unique

        with open(chemin_sortie, "w", encoding="utf-8") as f:
            f.write(md)

        return {
            "success": True, 
            "fichier": fichier, 
            "sortie": chemin_sortie,
            "md": md, 
            "avertissement": avert, 
            "tokens": len(md) // 4, 
            "error": None
        }
    except ConversionError as e:
        return {"success": False, "fichier": fichier, "error": str(e)}
    except Exception as e:
        return {"success": False, "fichier": fichier, "error": f"Erreur inattendue: {e}"}


class BatchProcessor:
    """Orchestre le traitement par lots en utilisant le multiprocessing."""

    def __init__(self, callbacks: Dict[str, Any]) -> None:
        self.callbacks = callbacks
        self.stop_event = threading.Event()

    def collecter_fichiers(self, source: Path, mode: str, recursif: bool) -> List[Path]:
        """Retourne la liste des fichiers à traiter selon le mode."""
        if mode == "fichier":
            return [source] if (source.is_file() and source.suffix.lower() in EXTENSIONS_VALIDES) else []
        if not source.is_dir():
            return []

        iterateur = source.rglob("*") if recursif else source.glob("*")
        return [
            f for f in iterateur 
            if f.is_file() and f.suffix.lower() in EXTENSIONS_VALIDES and not est_fichier_ignorable(f)
        ]

    def traiter(self, fichiers: List[Path], options: Dict[str, Any], dest_folder: Optional[Path], max_workers: Optional[int] = None) -> None:
        """Traite une liste de fichiers en parallèle."""
        reussis, echoues, avertissements, corpus, dernier_md = 0, [], [], [], ""
        total = len(fichiers)
        
        self.callbacks['log'](f"\n--- Début du traitement ({total} fichier(s)) ---")
        
        # Préparation des tâches (gestion des collisions de noms)
        noms_utilises = set()
        taches = []
        for i, fichier in enumerate(fichiers, 1):
            base = f"{fichier.stem}_optimise"
            sortie = f"{base}.md"
            c = 2
            while sortie in noms_utilises:
                sortie = f"{base}_{c}.md"
                c += 1
            noms_utilises.add(sortie)
            taches.append((fichier, i, options, dest_folder, sortie))

        if max_workers is None:
            max_workers = min(4, total)
            
        self.callbacks['log'](f"Mode parallèle : {max_workers} processus simultanés.")

        traites = 0
        try:
            with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(_worker_convertir, tache): tache for tache in taches}
                
                for future in concurrent.futures.as_completed(futures):
                    if self.stop_event.is_set():
                        self.callbacks['log']("\n⏹ Annulation demandée...")
                        for f in futures:
                            f.cancel()
                        break

                    traites += 1
                    res = future.result()
                    self.callbacks['progress'](traites / total, f"Fichier {traites}/{total}")

                    if res["success"]:
                        reussis += 1
                        dernier_md = res["md"]
                        corpus.append((res["fichier"], res["md"]))
                        self.callbacks['log'](f"   ✅ {res['fichier'].name} ({res['tokens']} tokens)")
                        
                        if res["avertissement"]:
                            avertissements.append((res["fichier"].name, res["avertissement"]))
                            self.callbacks['log'](f"      ⚠️ {res['avertissement']}")
                    else:
                        echoues.append((res["fichier"], res["error"]))
                        self.callbacks['log'](f"   ❌ {res['fichier'].name} : {res['error']}")

        except Exception as e:
            self.callbacks['log'](f"\n[Erreur critique] : {e}")

        # Génération des fichiers de sortie globaux
        self._generer_sorties(corpus, options, dest_folder)

        # Bilan final
        est_annule = self.stop_event.is_set()
        progress_final = 1.0 if (not est_annule and total) else 0.0
        self.callbacks['progress'](progress_final, f"{reussis}/{total} converti(s)")
        
        self.callbacks['finish'](reussis, total, echoues, avertissements, dernier_md, est_annule)

    def _generer_sorties(self, corpus: List[Tuple[Path, str]], options: Dict[str, Any], dest_folder: Optional[Path]) -> None:
        """Génère les fichiers combinés (.md) et/ou JSONL si demandés."""
        if not corpus:
            return

        if options.get('sortie_combinee'):
            try:
                chemin = self._ecrire_corpus_md(corpus, dest_folder)
                self.callbacks['log'](f"\n📚 Corpus combiné : {chemin.name}")
            except Exception as e:
                self.callbacks['log'](f"\n[Erreur corpus .md] : {e}")

        if options.get('sortie_jsonl'):
            try:
                chemin = self._ecrire_corpus_jsonl(
                    corpus, dest_folder, 
                    chunking=options.get('chunking', False), 
                    chunk_size=options.get('chunk_size', 1500)
                )
                self.callbacks['log'](f"📚 Corpus JSONL : {chemin.name}")
            except Exception as e:
                self.callbacks['log'](f"\n[Erreur corpus JSONL] : {e}")

    def _ecrire_corpus_md(self, corpus: List[Tuple[Path, str]], dest: Optional[Path]) -> Path:
        """Écrit tous les Markdown dans un seul fichier géant."""
        dossier = dest if dest else corpus[0][0].parent
        chemin = dossier / f"_corpus_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(chemin, "w", encoding="utf-8") as f:
            for src, md in corpus:
                f.write(f"# ===== FICHIER : {src.name} =====\n\n{md}\n\n---\n\n")
        return chemin

    def _ecrire_corpus_jsonl(self, corpus: List[Tuple[Path, str]], dest: Optional[Path], chunking: bool, chunk_size: int) -> Path:
        """Écrit un fichier JSONL (avec ou sans Smart Chunking)."""
        dossier = dest if dest else corpus[0][0].parent
        chemin = dossier / f"_corpus_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        
        with open(chemin, "w", encoding="utf-8") as f:
            for src, md in corpus:
                if chunking:
                    chunks = decouper_markdown(md, max_chars=chunk_size)
                    for i, chunk in enumerate(chunks):
                        f.write(json.dumps({
                            "source": src.name, "type": src.suffix.lstrip(".").lower(),
                            "chunk_id": i + 1, "header": chunk["header"], "contenu": chunk["text"],
                            "tokens_estimes": len(chunk["text"]) // 4,
                        }, ensure_ascii=False) + "\n")
                else:
                    f.write(json.dumps({
                        "source": src.name, "type": src.suffix.lstrip(".").lower(),
                        "tokens_estimes": len(md) // 4, "contenu": md,
                    }, ensure_ascii=False) + "\n")
        return chemin