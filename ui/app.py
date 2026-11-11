import os
import subprocess
import sys
import threading
from pathlib import Path

import customtkinter as ctk
from tkinter import filedialog, messagebox

from utils import Preferences
from core.processor import BatchProcessor
from config import AVERTISSEMENT_MO, AVERTISSEMENT_FICHIERS, APERCU_MAX_CHARS
from version import __version__

# =====================================================================
# DESIGN SYSTEM : "Dark Pro"
# =====================================================================
COLOR_BG = "#0F111A"          
COLOR_SURFACE = "#181B26"     
COLOR_SURFACE_HOVER = "#1F2333" 
COLOR_BORDER = "#2A2E42"      
COLOR_TEXT = "#E2E8F0"        
COLOR_TEXT_MUTED = "#94A3B8"  
COLOR_PRIMARY = "#6366F1"     
COLOR_SUCCESS = "#10B981"     
COLOR_DANGER = "#EF4444"      
COLOR_DISABLED = "#334155"    

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class MarkdownConverterApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Doc2MD Pro — AI Document Optimizer")
        self.geometry("1200x850")
        self.minsize(1000, 750)
        self.configure(fg_color=COLOR_BG)

        # --- État ---
        self.mode_conversion = "fichier"
        self.source_path = None
        self.dest_folder = None
        self.btn_enabled = False

        # --- Dépendances ---
        self.prefs = Preferences()
        self.processor = BatchProcessor({
            'log': self._log,
            'progress': self._set_progress,
            'finish': self._afficher_bilan,
        })

        # --- Interface ---
        self._creer_interface()
        self._restaurer_preferences()
        self._log(f"⚡ Doc2MD Pro v{__version__} initialisé.", clear=True)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ======================================================================
    #   CONSTRUCTION DE L'INTERFACE (2 zones : Toolbar + Corps)
    # ======================================================================
    def _creer_interface(self):
        self.grid_rowconfigure(0, weight=0)  # Toolbar
        self.grid_rowconfigure(1, weight=1)  # Corps principal
        self.grid_columnconfigure(0, weight=1)

        self._creer_toolbar()
        self._creer_corps()

    # ----------------------------------------------------------------------
    # TOOLBAR (Haut de fenêtre)
    # ----------------------------------------------------------------------
    def _creer_toolbar(self):
        self.toolbar = ctk.CTkFrame(self, height=64, corner_radius=0, fg_color=COLOR_SURFACE)
        self.toolbar.grid(row=0, column=0, sticky="ew")
        self.toolbar.pack_propagate(False)

        # --- Section gauche : Identité ---
        brand_frame = ctk.CTkFrame(self.toolbar, fg_color="transparent")
        brand_frame.pack(side="left", padx=25, pady=10)

        ctk.CTkLabel(
            brand_frame, text="⚡ Doc2MD Pro", 
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"), 
            text_color=COLOR_TEXT
        ).pack(side="left")

        ctk.CTkLabel(
            brand_frame, text=f"v{__version__}", 
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLOR_TEXT_MUTED
        ).pack(side="left", padx=(10, 0), pady=(4, 0))

        # --- Section droite : Actions globales ---
        actions_frame = ctk.CTkFrame(self.toolbar, fg_color="transparent")
        actions_frame.pack(side="right", padx=25, pady=10)

        self.btn_open_output = ctk.CTkButton(
            actions_frame, text="📁 Sortie", command=self._ouvrir_dossier_sortie,
            fg_color="transparent", border_width=1, border_color=COLOR_BORDER,
            text_color=COLOR_TEXT_MUTED, hover_color=COLOR_SURFACE_HOVER,
            font=ctk.CTkFont(family="Segoe UI", size=12), height=34, width=90
        )
        self.btn_open_output.pack(side="left", padx=4)

        self.btn_help = ctk.CTkButton(
            actions_frame, text="❓ Aide", command=self._ouvrir_aide,
            fg_color="transparent", border_width=1, border_color=COLOR_BORDER,
            text_color=COLOR_TEXT_MUTED, hover_color=COLOR_SURFACE_HOVER,
            font=ctk.CTkFont(family="Segoe UI", size=12), height=34, width=90
        )
        self.btn_help.pack(side="left", padx=4)

        self.btn_about = ctk.CTkButton(
            actions_frame, text="ℹ À propos", command=self._ouvrir_a_propos,
            fg_color="transparent", border_width=1, border_color=COLOR_BORDER,
            text_color=COLOR_TEXT_MUTED, hover_color=COLOR_SURFACE_HOVER,
            font=ctk.CTkFont(family="Segoe UI", size=12), height=34, width=100
        )
        self.btn_about.pack(side="left", padx=4)

        # Ligne de séparation visuelle
        ctk.CTkFrame(self, height=1, fg_color=COLOR_BORDER).grid(row=0, column=0, sticky="sew")

    # ----------------------------------------------------------------------
    # CORPS PRINCIPAL (Sidebar + Zone de travail)
    # ----------------------------------------------------------------------
    def _creer_corps(self):
        self.corps = ctk.CTkFrame(self, fg_color=COLOR_BG, corner_radius=0)
        self.corps.grid(row=1, column=0, sticky="nsew")
        self.corps.grid_rowconfigure(0, weight=1)
        self.corps.grid_columnconfigure(0, weight=0)
        self.corps.grid_columnconfigure(1, weight=1)

        self._creer_sidebar()
        self._creer_zone_travail()

    # ----------------------------------------------------------------------
    # SIDEBAR (Gauche)
    # ----------------------------------------------------------------------
    def _creer_sidebar(self):
        self.sidebar = ctk.CTkScrollableFrame(
            self.corps, width=400, corner_radius=0, fg_color=COLOR_SURFACE,
            scrollbar_button_color=COLOR_BORDER, scrollbar_button_hover_color=COLOR_PRIMARY
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_columnconfigure(0, weight=1)

        self._creer_sidebar_fichiers()
        self._creer_sidebar_options()
        self._creer_sidebar_performance()
        self._creer_sidebar_rag()

    def _creer_sidebar_fichiers(self):
        self._creer_section_titre("📂 Source & Destination")
        
        self.segment_mode = ctk.CTkSegmentedButton(
            self.sidebar, values=["Fichier unique", "Dossier complet"], command=self._changer_mode,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            selected_color=COLOR_PRIMARY, selected_hover_color="#4F46E5", 
            unselected_color=COLOR_BORDER, unselected_hover_color=COLOR_SURFACE_HOVER
        )
        self.segment_mode.set("Fichier unique")
        self.segment_mode.pack(fill="x", padx=25, pady=(0, 10))

        self.var_recursif = ctk.BooleanVar(value=False)
        self.chk_recursif = ctk.CTkCheckBox(
            self.sidebar, text="Inclure les sous-dossiers", variable=self.var_recursif, state="disabled",
            font=ctk.CTkFont(family="Segoe UI", size=12), text_color=COLOR_TEXT_MUTED,
            checkbox_width=20, checkbox_height=20, corner_radius=6, border_color=COLOR_BORDER, fg_color=COLOR_PRIMARY
        )
        self.chk_recursif.pack(anchor="w", padx=25, pady=(0, 15))

        self.btn_select_source = ctk.CTkButton(
            self.sidebar, text="Parcourir...", command=self._choisir_source,
            fg_color=COLOR_PRIMARY, hover_color="#4F46E5", height=38, corner_radius=8,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
        )
        self.btn_select_source.pack(fill="x", padx=25, pady=5)

        self.lbl_path_source = ctk.CTkLabel(
            self.sidebar, text="Aucune source choisie", font=ctk.CTkFont(family="Segoe UI", size=11), 
            text_color=COLOR_TEXT_MUTED, wraplength=320, justify="left"
        )
        self.lbl_path_source.pack(anchor="w", padx=25, pady=(0, 15))

        self.btn_select_dest = ctk.CTkButton(
            self.sidebar, text="Dossier de destination...", command=self._choisir_destination,
            fg_color="transparent", border_width=1, border_color=COLOR_BORDER, text_color=COLOR_TEXT, 
            hover_color=COLOR_SURFACE_HOVER, height=38, corner_radius=8, font=ctk.CTkFont(family="Segoe UI", size=12)
        )
        self.btn_select_dest.pack(fill="x", padx=25, pady=5)

        self.lbl_path_dest = ctk.CTkLabel(
            self.sidebar, text="Par défaut : même dossier que la source", font=ctk.CTkFont(family="Segoe UI", size=11), 
            text_color=COLOR_TEXT_MUTED, wraplength=320, justify="left"
        )
        self.lbl_path_dest.pack(anchor="w", padx=25, pady=(0, 25))

    def _creer_sidebar_options(self):
        self._creer_section_titre("⚙️ Traitement Markdown")

        self.var_nettoyage = ctk.BooleanVar(value=True)
        self.var_metadonnees = ctk.BooleanVar(value=True)
        self.var_retirer_images = ctk.BooleanVar(value=True)
        self.var_ocr = ctk.BooleanVar(value=False)

        for var, txt in [
            (self.var_nettoyage, "Nettoyer le Markdown (ligatures, puces)"),
            (self.var_metadonnees, "Ajouter les métadonnées (front-matter)"),
            (self.var_retirer_images, "Retirer les images (DOCX)"),
        ]:
            ctk.CTkCheckBox(
                self.sidebar, text=txt, variable=var, font=ctk.CTkFont(family="Segoe UI", size=12),
                text_color=COLOR_TEXT, checkbox_width=20, checkbox_height=20, corner_radius=6,
                border_color=COLOR_BORDER, fg_color=COLOR_PRIMARY
            ).pack(anchor="w", padx=25, pady=4)

        ctk.CTkCheckBox(
            self.sidebar, text="Activer l'OCR (PDF scannés)", variable=self.var_ocr, 
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color=COLOR_TEXT, 
            checkbox_width=20, checkbox_height=20, corner_radius=6, border_color=COLOR_BORDER, fg_color=COLOR_PRIMARY
        ).pack(anchor="w", padx=25, pady=(10, 0))
        ctk.CTkLabel(
            self.sidebar, text="Lit le texte à partir des images (plus lent).\nNécessite l'installation de Tesseract.", 
            font=ctk.CTkFont(family="Segoe UI", size=11), text_color=COLOR_TEXT_MUTED, justify="left"
        ).pack(anchor="w", padx=50, pady=(0, 10))

    def _creer_sidebar_performance(self):
        ctk.CTkFrame(self.sidebar, height=1, fg_color=COLOR_BORDER).pack(fill="x", padx=25, pady=15)
        self._creer_section_titre("🚀 Performance")

        self.var_workers = ctk.StringVar(value="Auto (Max)")
        options_workers = ["1 (Séquentiel)", "2", "4", "8", "Auto (Max)"]
        
        self.combo_workers = ctk.CTkComboBox(
            self.sidebar, values=options_workers, variable=self.var_workers,
            fg_color=COLOR_BG, border_color=COLOR_BORDER, button_color=COLOR_BORDER,
            button_hover_color=COLOR_SURFACE_HOVER, dropdown_fg_color=COLOR_SURFACE,
            text_color=COLOR_TEXT, font=ctk.CTkFont(family="Segoe UI", size=12)
        )
        self.combo_workers.pack(fill="x", padx=25, pady=(0, 5))
        
        ctk.CTkLabel(
            self.sidebar, text="'Auto' utilise 100% des cœurs de votre processeur.", 
            font=ctk.CTkFont(family="Segoe UI", size=10), text_color=COLOR_TEXT_MUTED
        ).pack(anchor="w", padx=25, pady=(0, 10))

    def _creer_sidebar_rag(self):
        ctk.CTkFrame(self.sidebar, height=1, fg_color=COLOR_BORDER).pack(fill="x", padx=25, pady=15)
        self._creer_section_titre("📦 Format de sortie IA")

        self.var_sortie_combinee = ctk.BooleanVar(value=False)
        self.var_sortie_jsonl = ctk.BooleanVar(value=False)
        self.var_chunking = ctk.BooleanVar(value=True)
        self.var_chunk_size = ctk.StringVar(value="1500")

        # Option Fusion
        ctk.CTkCheckBox(
            self.sidebar, text="Fusionner en un seul document (.md)", variable=self.var_sortie_combinee, 
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color=COLOR_TEXT, 
            checkbox_width=20, checkbox_height=20, corner_radius=6, border_color=COLOR_BORDER, fg_color=COLOR_PRIMARY
        ).pack(anchor="w", padx=25, pady=(5, 0))
        ctk.CTkLabel(
            self.sidebar, text="Regroupe tous les fichiers convertis dans un seul fichier géant.", 
            font=ctk.CTkFont(family="Segoe UI", size=11), text_color=COLOR_TEXT_MUTED, justify="left"
        ).pack(anchor="w", padx=50, pady=(0, 15))

        # Option JSONL
        ctk.CTkCheckBox(
            self.sidebar, text="Générer un corpus JSONL (RAG)", variable=self.var_sortie_jsonl, 
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color=COLOR_TEXT, 
            checkbox_width=20, checkbox_height=20, corner_radius=6, border_color=COLOR_BORDER, fg_color=COLOR_PRIMARY
        ).pack(anchor="w", padx=25, pady=(5, 0))
        ctk.CTkLabel(
            self.sidebar, text="Un document par ligne avec ses métadonnées.", 
            font=ctk.CTkFont(family="Segoe UI", size=11), text_color=COLOR_TEXT_MUTED, justify="left"
        ).pack(anchor="w", padx=50, pady=(0, 10))

        # Sous-option Chunking
        chunk_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        chunk_frame.pack(fill="x", padx=45, pady=(0, 25))
        
        ctk.CTkCheckBox(
            chunk_frame, text="Découper en morceaux (Chunking)", variable=self.var_chunking, 
            font=ctk.CTkFont(family="Segoe UI", size=12), text_color=COLOR_TEXT, 
            checkbox_width=18, checkbox_height=18, corner_radius=6, border_color=COLOR_BORDER, fg_color=COLOR_PRIMARY
        ).pack(anchor="w")

        size_frame = ctk.CTkFrame(chunk_frame, fg_color="transparent")
        size_frame.pack(fill="x", pady=(5, 0))
        
        ctk.CTkLabel(size_frame, text="Taille max (caractères) :", font=ctk.CTkFont(family="Segoe UI", size=11), text_color=COLOR_TEXT_MUTED).pack(side="left")
        
        self.entry_chunk_size = ctk.CTkEntry(
            size_frame, textvariable=self.var_chunk_size, width=60, height=24,
            fg_color=COLOR_BG, border_color=COLOR_BORDER, text_color=COLOR_TEXT
        )
        self.entry_chunk_size.pack(side="left", padx=5)
        ctk.CTkLabel(size_frame, text="(~375 mots)", font=ctk.CTkFont(family="Segoe UI", size=10), text_color=COLOR_TEXT_MUTED).pack(side="left")

    # ----------------------------------------------------------------------
    # ZONE DE TRAVAIL (Droite)
    # ----------------------------------------------------------------------
    def _creer_zone_travail(self):
        self.main_frame = ctk.CTkFrame(self.corps, fg_color=COLOR_BG, corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        # Onglets
        self.tabview = ctk.CTkTabview(
            self.main_frame, fg_color="transparent", 
            segmented_button_selected_color=COLOR_PRIMARY, segmented_button_selected_hover_color="#4F46E5",
            text_color=COLOR_TEXT, border_width=0
        )
        self.tabview.grid(row=0, column=0, sticky="nsew")
        self.tabview.add("Console d'exécution")
        self.tabview.add("Aperçu du fichier")

        self.text_journal = ctk.CTkTextbox(
            self.tabview.tab("Console d'exécution"), wrap="word", font=ctk.CTkFont(family="Consolas", size=13),
            fg_color=COLOR_SURFACE, text_color=COLOR_TEXT, border_width=1, border_color=COLOR_BORDER, corner_radius=10
        )
        self.text_journal.pack(fill="both", expand=True, pady=(10, 0))
        self.text_journal.insert("1.0", "Système prêt.\nEn attente d'une source...\n")
        self.text_journal.configure(state="disabled")

        self.text_preview = ctk.CTkTextbox(
            self.tabview.tab("Aperçu du fichier"), wrap="word", font=ctk.CTkFont(family="Consolas", size=13),
            fg_color=COLOR_SURFACE, text_color=COLOR_TEXT, border_width=1, border_color=COLOR_BORDER, corner_radius=10
        )
        self.text_preview.pack(fill="both", expand=True, pady=(10, 0))
        self.text_preview.insert("1.0", "L'aperçu apparaîtra ici.\n")
        self.text_preview.configure(state="disabled")

        # Barre d'action (Bottom)
        self.action_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.action_frame.grid(row=1, column=0, sticky="ew", pady=(15, 0))

        self.lbl_progress = ctk.CTkLabel(
            self.action_frame, text="Prêt à convertir", 
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color=COLOR_TEXT_MUTED
        )
        self.lbl_progress.pack(side="left", padx=10)

        self.progress_bar = ctk.CTkProgressBar(
            self.action_frame, mode="determinate", height=8, width=200, corner_radius=4, 
            progress_color=COLOR_SUCCESS, fg_color=COLOR_BORDER
        )
        self.progress_bar.pack(side="left", padx=20)
        self.progress_bar.set(0)

        self.btn_convert = ctk.CTkButton(
            self.action_frame, text="Lancer la conversion", command=self._lancer_conversion_thread,
            fg_color=COLOR_DISABLED, hover_color=COLOR_DISABLED, 
            text_color="#FFFFFF", height=45, width=250, corner_radius=8,
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold")
        )
        self.btn_convert.pack(side="right")

    def _creer_section_titre(self, titre):
        ctk.CTkLabel(
            self.sidebar, text=titre, 
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), text_color=COLOR_PRIMARY
        ).pack(anchor="w", padx=25, pady=(15, 8))

    # ======================================================================
    #   ACTIONS GLOBALES (Toolbar)
    # ======================================================================
    def _ouvrir_dossier_sortie(self):
        """Ouvre le dossier de destination dans l'explorateur système."""
        dossier = self.dest_folder if self.dest_folder else (
            self.source_path.parent if self.source_path else None
        )
        if not dossier or not dossier.exists():
            messagebox.showinfo("Information", "Aucun dossier de sortie n'est défini pour le moment.")
            return
        try:
            if sys.platform == "win32":
                os.startfile(dossier)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(dossier)])
            else:
                subprocess.Popen(["xdg-open", str(dossier)])
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible d'ouvrir le dossier :\n{e}")

    def _ouvrir_a_propos(self):
        """Affiche une fenêtre À propos avec les infos de version."""
        w = ctk.CTkToplevel(self)
        w.title("À propos")
        w.geometry("450x320")
        w.configure(fg_color=COLOR_BG)
        w.transient(self)
        w.resizable(False, False)
        
        self.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - 225
        y = self.winfo_y() + (self.winfo_height() // 2) - 160
        w.geometry(f"+{x}+{y}")

        ctk.CTkLabel(
            w, text="⚡ Doc2MD Pro", 
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"), text_color=COLOR_TEXT
        ).pack(pady=(30, 5))
        
        ctk.CTkLabel(
            w, text=f"Version {__version__}", 
            font=ctk.CTkFont(family="Segoe UI", size=13), text_color=COLOR_PRIMARY
        ).pack()

        ctk.CTkLabel(
            w, text="Optimiseur de documents pour l'IA.\n\n"
                    "Convertit PDF, Word et Excel en Markdown\n"
                    "prêt pour le RAG et les LLM.\n\n"
                    "100% local, sans envoi de données.",
            font=ctk.CTkFont(family="Segoe UI", size=12), 
            text_color=COLOR_TEXT_MUTED, justify="center"
        ).pack(pady=(20, 20))

        ctk.CTkButton(
            w, text="Fermer", command=w.destroy,
            fg_color=COLOR_PRIMARY, hover_color="#4F46E5", height=36, width=120,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
        ).pack(pady=(0, 20))

    def _ouvrir_aide(self):
        """Ouvre la fenêtre d'aide / guide utilisateur."""
        aide_window = ctk.CTkToplevel(self)
        aide_window.title("Guide d'utilisation - Doc2MD Pro")
        aide_window.geometry("800x650")
        aide_window.configure(fg_color=COLOR_BG)
        aide_window.transient(self)
        
        self.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - 400
        y = self.winfo_y() + (self.winfo_height() // 2) - 325
        aide_window.geometry(f"+{x}+{y}")

        textbox = ctk.CTkTextbox(
            aide_window, wrap="word", font=ctk.CTkFont(family="Segoe UI", size=13),
            fg_color=COLOR_SURFACE, text_color=COLOR_TEXT, 
            border_width=1, border_color=COLOR_BORDER, corner_radius=10
        )
        textbox.pack(fill="both", expand=True, padx=20, pady=20)

        aide_texte = """
# 👋 Bienvenue sur Doc2MD Pro

Cette application transforme vos documents (PDF, Excel, Word) en fichiers **Markdown**, le format préféré des Intelligences Artificielles (ChatGPT, Claude, etc.) et des bases de données spécialisées.

---

## 🚀 Démarrage Rapide

1. **Choisissez votre Source** : Cliquez sur "Parcourir..." pour un fichier, ou passez en mode "Dossier complet" pour convertir plusieurs fichiers d'un coup.
2. **Cochez vos options** (voir le dictionnaire ci-dessous).
3. **Cliquez sur "Lancer la conversion"**. Vos fichiers `.md` seront générés dans le dossier de votre choix.

---

## 📖 Le Dictionnaire de l'IA (Explications simples)

Vous avez vu des termes techniques ? Voici ce qu'ils veulent dire :

### 📄 Markdown (.md)
C'est un langage de mise en forme très simple (avec des `#` pour les titres). C'est le format idéal pour l'IA car il ne contient pas de "code informatique invisible".

### 🧠 RAG (Retrieval-Augmented Generation)
C'est une technique pour créer des chatbots qui répondent en se basant sur **VOS** documents. Pour que ça marche, l'IA a besoin que vos documents soient propres et bien découpés.

### ✂️ Chunking (Découpage)
Les IA ont une mémoire limitée. Le "Chunking" consiste à découper votre document en petits morceaux (ex: 1500 caractères) avec un peu de répétition, pour que l'IA comprenne bien le contexte.

### 📦 JSONL (Le format des bases de données IA)
C'est un fichier où chaque ligne est un morceau de votre document. C'est le format standard pour "nourrir" une base de données vectorielle.

### 🖨️ OCR (Reconnaissance de caractères)
Un PDF scanné, c'est une photo. Sans OCR, l'application ne voit que des pixels vides. En cochant l'OCR, l'application "lit" l'image comme un humain.
*À utiliser si :* Votre PDF est vieux, scanné, ou si vous voyez que la conversion est vide.

### ⚡ Performance (Multiprocessing)
C'est la vitesse de traitement. En mode "Auto (Max)", l'application utilise tous les cœurs de votre processeur pour convertir 4, 8 ou 16 fichiers simultanément.

---

## ❓ Foire Aux Questions (FAQ)

**"Ma conversion est vide ou illisible, pourquoi ?"**
Le PDF est probablement une image scannée. Cochez **"Activer l'OCR"** et relancez.

**"À quoi servent les métadonnées ?"**
C'est un petit bloc en haut du fichier qui indique le nom du fichier source, le nombre de mots, etc. C'est pratique pour classer les documents.

**"Que choisir : Fusionner ou JSONL ?"**
- *Fusionner* : Un seul gros fichier. Idéal pour copier-coller dans ChatGPT.
- *JSONL* : Des milliers de lignes prêtes à être ingérées par un logiciel de base de données IA.

**"Est-ce que mes fichiers sont envoyés sur Internet ?"**
Non ! Doc2MD Pro fonctionne à 100% sur votre ordinateur. Vos documents restent privés.
"""

        textbox.insert("1.0", aide_texte)
        textbox.configure(state="disabled")
        
        ctk.CTkButton(
            aide_window, text="J'ai compris", command=aide_window.destroy,
            fg_color=COLOR_PRIMARY, hover_color="#4F46E5", height=40,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold")
        ).pack(pady=(0, 20), padx=20, fill="x")

    # ======================================================================
    #   PRÉFÉRENCES & LOGIQUE
    # ======================================================================
    def _restaurer_preferences(self):
        if self.prefs.get("mode", "fichier") == "dossier":
            self.segment_mode.set("Dossier complet")
            self._changer_mode("Dossier complet")

        dest = self.prefs.get("dest_folder")
        if dest and Path(dest).is_dir():
            self.dest_folder = Path(dest)
            self.lbl_path_dest.configure(text=str(dest), text_color=COLOR_TEXT)

        self.var_recursif.set(self.prefs.get("recursif", False))
        self.var_nettoyage.set(self.prefs.get("nettoyage", True))
        self.var_metadonnees.set(self.prefs.get("metadonnees", True))
        self.var_retirer_images.set(self.prefs.get("retirer_images", True))
        self.var_sortie_combinee.set(self.prefs.get("sortie_combinee", False))
        self.var_sortie_jsonl.set(self.prefs.get("jsonl", False))

    def _on_close(self):
        self.prefs.set("mode", self.mode_conversion)
        self.prefs.set("dest_folder", str(self.dest_folder) if self.dest_folder else None)
        self.prefs.set("recursif", self.var_recursif.get())
        self.prefs.set("nettoyage", self.var_nettoyage.get())
        self.prefs.set("metadonnees", self.var_metadonnees.get())
        self.prefs.set("retirer_images", self.var_retirer_images.get())
        self.prefs.set("sortie_combinee", self.var_sortie_combinee.get())
        self.prefs.set("jsonl", self.var_sortie_jsonl.get())
        self.prefs.sauvegarder()
        self.destroy()

    def _log(self, message, clear=False):
        def _do():
            self.text_journal.configure(state="normal")
            if clear: self.text_journal.delete("1.0", "end")
            self.text_journal.insert("end", message + "\n")
            self.text_journal.see("end")
            self.text_journal.configure(state="disabled")
        self.after(0, _do)

    def _set_progress(self, value, label=""):
        def _do():
            self.progress_bar.set(value)
            self.lbl_progress.configure(text=label)
        self.after(0, _do)

    def _set_converting_state(self, converting):
        def _do():
            if converting:
                self.btn_convert.configure(text="⏹ Annuler", command=self._annuler_conversion, fg_color=COLOR_DANGER, hover_color="#B91C1C")
                self.btn_enabled = False
                for w in [self.btn_select_source, self.btn_select_dest, self.segment_mode, 
                          self.chk_recursif, self.combo_workers, self.entry_chunk_size]:
                    w.configure(state="disabled")
            else:
                if self.source_path:
                    self.btn_convert.configure(text="Lancer la conversion", command=self._lancer_conversion_thread, fg_color=COLOR_SUCCESS, hover_color="#059669")
                    self.btn_enabled = True
                else:
                    self.btn_convert.configure(text="Lancer la conversion", command=self._lancer_conversion_thread, fg_color=COLOR_DISABLED, hover_color=COLOR_DISABLED)
                    self.btn_enabled = False
                
                for w in [self.btn_select_source, self.btn_select_dest, self.segment_mode, 
                          self.combo_workers, self.entry_chunk_size]:
                    w.configure(state="normal")
                if self.mode_conversion == "dossier":
                    self.chk_recursif.configure(state="normal")
        self.after(0, _do)

    def _set_preview(self, texte):
        def _do():
            apercu = texte[:APERCU_MAX_CHARS]
            if len(texte) > APERCU_MAX_CHARS: apercu += "\n\n... [Tronqué]"
            self.text_preview.configure(state="normal")
            self.text_preview.delete("1.0", "end")
            self.text_preview.insert("1.0", apercu)
            self.text_preview.configure(state="disabled")
            self.tabview.set("Aperçu du fichier")
        self.after(0, _do)

    def _changer_mode(self, mode):
        self.mode_conversion = "fichier" if mode == "Fichier unique" else "dossier"
        self.source_path = None
        self.lbl_path_source.configure(text="Aucune source choisie", text_color=COLOR_TEXT_MUTED)
        self.btn_select_source.configure(text="Parcourir..." if self.mode_conversion == "fichier" else "Choisir un dossier...")
        self.btn_convert.configure(fg_color=COLOR_DISABLED, hover_color=COLOR_DISABLED)
        self.btn_enabled = False
        if self.mode_conversion == "fichier":
            self.var_recursif.set(False)
            self.chk_recursif.configure(state="disabled")
        else:
            self.chk_recursif.configure(state="normal")

    def _choisir_source(self):
        if self.mode_conversion == "fichier":
            types = [("Documents", "*.pdf *.xlsx *.xls *.docx"), ("PDF", "*.pdf"), ("Excel", "*.xlsx *.xls"), ("Word", "*.docx")]
            chemin = filedialog.askopenfilename(title="Choisir un fichier", filetypes=types)
        else:
            chemin = filedialog.askdirectory(title="Choisir un dossier")
        if not chemin: return
        self.source_path = Path(chemin)
        self.lbl_path_source.configure(text=str(self.source_path), text_color=COLOR_TEXT)
        self.btn_convert.configure(fg_color=COLOR_SUCCESS, hover_color="#059669")
        self.btn_enabled = True
        self._log(f"✅ Source définie : {self.source_path}", clear=True)

    def _choisir_destination(self):
        dossier = filedialog.askdirectory(title="Dossier de sauvegarde")
        if dossier:
            self.dest_folder = Path(dossier)
            self.lbl_path_dest.configure(text=str(self.dest_folder), text_color=COLOR_TEXT)

    def _lancer_conversion_thread(self):
        if not self.btn_enabled or not self.source_path: return
        fichiers = self.processor.collecter_fichiers(self.source_path, self.mode_conversion, self.var_recursif.get())
        if not fichiers:
            messagebox.showwarning("Aucun fichier", "Aucun fichier compatible trouvé.")
            return

        val = self.var_workers.get()
        workers = (os.cpu_count() or 4) if val == "Auto (Max)" else (1 if val == "1 (Séquentiel)" else int(val))
        try: chunk_size = int(self.var_chunk_size.get())
        except ValueError: chunk_size = 1500

        options = {
            'nettoyage': self.var_nettoyage.get(), 'metadonnees': self.var_metadonnees.get(),
            'retirer_images': self.var_retirer_images.get(), 'sortie_combinee': self.var_sortie_combinee.get(),
            'sortie_jsonl': self.var_sortie_jsonl.get(), 'chunking': self.var_chunking.get(),
            'chunk_size': chunk_size, 'ocr': self.var_ocr.get(),
        }

        self.processor.stop_event.clear()
        self._set_converting_state(True)
        self.progress_bar.set(0)
        self.lbl_progress.configure(text="Conversion en cours...")

        threading.Thread(target=self.processor.traiter, args=(fichiers, options, self.dest_folder, workers), daemon=True).start()

    def _annuler_conversion(self):
        self.processor.stop_event.set()
        self.btn_convert.configure(state="disabled", text="Annulation...")
        self._log("\n⏹ Annulation demandée...")

    def _afficher_bilan(self, reussis, total, echoues, avertissements, dernier_md="", est_annule=False):
        self._set_converting_state(False)
        if dernier_md: self._set_preview(dernier_md)

        def _show():
            if est_annule: messagebox.showwarning("Annulé", f"Conversion interrompue. {reussis}/{total}.")
            elif total == 0: messagebox.showwarning("Aucun fichier", "Aucun fichier trouvé.")
            elif reussis == 0: messagebox.showerror("Échec", f"Aucun fichier converti ({len(echoues)} erreurs).")
            elif echoues: messagebox.showwarning("Partiel", f"{reussis}/{total} converti(s), {len(echoues)} erreurs.")
            elif avertissements: messagebox.showinfo("Terminé", f"{reussis}/{total} converti(s).\n{len(avertissements)} alertes.")
            else: messagebox.showinfo("Succès", f"{reussis}/{total} converti(s) avec succès !")
        self.after(0, _show)