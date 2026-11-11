import multiprocessing
from ui.app import MarkdownConverterApp

if __name__ == "__main__":
     # Cette ligne est OBLIGATOIRE pour PyInstaller + Multiprocessing
    multiprocessing.freeze_support() 

    app = MarkdownConverterApp()
    app.mainloop()