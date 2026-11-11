# ⚡ Doc2MD Pro — AI Document Optimizer

> Convertissez vos PDF, Excel et Word en Markdown ultra-propre, prêt pour les LLM (ChatGPT, Claude) et les bases vectorielles (RAG).

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.10+-yellow)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)

**Doc2MD Pro** est une application de bureau (Windows) 100% locale qui transforme vos documents en données exploitables par l'Intelligence Artificielle. Conçu avec une approche "Haute Performance" et "RAG-First", il résout les problèmes que les convertisseurs classiques ignorent.

## ✨ Fonctionnalités clés

- 🚀 **Multiprocessing** : Convertissez des centaines de fichiers simultanément en utilisant tous les cœurs de votre processeur.
- 🖨️ **OCR Intégré** : Récupérez le texte même sur les PDF scannés ou avec des polices corrompues (via Tesseract).
- 🧠 **Smart Chunking (RAG)** : Découpez intelligemment vos documents en morceaux (chunks) avec chevauchement, prêts pour Pinecone, Qdrant ou LangChain.
- 🧹 **Nettoyage Markdown** : Supprime les artefacts de conversion (ligatures, numéros de page, puces cassées).
- 📦 **Export JSONL** : Format standard pour nourrir les bases de données vectorielles.
- 🌙 **Interface Dark Pro** : Design moderne, fluide et intuitif.

## 🚀 Installation rapide

### Option 1 : Télécharger l'exécutable (Windows)
Téléchargez la dernière version dans l'onglet [Releases](lien_vers_tes_releases) et lancez `main.exe`. Aucune installation de Python requise.

### Option 2 : Lancer depuis le code source (Développeurs)
```bash
git clone https://github.com/ton-pseudo/Doc2MD-Pro.git
cd Doc2MD-Pro
pip install -r requirements.txt
python main.py


## 🧠 Comment ça marche ?
Extraction : MarkItDown (ou Tesseract si l'OCR est activé) extrait le texte brut.

Nettoyage : Le texte est passé dans un optimiseur (normalisation Unicode, suppression des pages).

Enrichissement : Ajout d'un front-matter YAML (métadonnées).

Découpage : Si demandé, le texte est découpé en chunks logiques avec overlap pour le RAG.

🤝 Contribution
Les contributions sont les bienvenues ! (N'hésitez pas à ouvrir une Issue ou une Pull Request).

📄 Licence
Distribué sous licence MIT. Voir le fichier LICENSE pour plus d'informations.