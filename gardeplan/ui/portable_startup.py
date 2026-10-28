"""User-selected fallback when macOS cannot disclose the original portable path."""
from pathlib import Path
import tempfile

from PySide6.QtCore import QStandardPaths
from PySide6.QtWidgets import QFileDialog, QMessageBox

from gardeplan.data_paths import PORTABLE_MARKER
from gardeplan.macos_paths import is_translocated_path


def choose_portable_folder() -> Path | None:
    QMessageBox.information(
        None, "Retrouver le dossier du logiciel",
        "macOS a ouvert une copie temporaire du logiciel.\n\n"
        "Choisissez le dossier Planificateur-SDG que vous avez extrait du ZIP. "
        "Il contient l’application, le fichier portable.mode et vos données.\n\n"
        "Vos horaires seront conservés dans le sous-dossier donnees de ce dossier.")
    initial = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation)
    while True:
        selected = QFileDialog.getExistingDirectory(
            None, "Choisir le dossier Planificateur-SDG extrait du ZIP", initial)
        if not selected:
            return None
        folder = Path(selected).resolve()
        if (is_translocated_path(folder) or not (folder / PORTABLE_MARKER).is_file()
                or not (folder / "Planificateur-SDG.app").is_dir()):
            QMessageBox.warning(None, "Choisissez le dossier complet",
                                "Choisissez le dossier qui contient Planificateur-SDG.app et portable.mode. "
                                "Si nécessaire, décompressez à nouveau le ZIP dans Documents.")
            initial = str(folder)
            continue
        try:
            with tempfile.TemporaryFile(prefix=".planificateur-acces-", dir=folder) as probe:
                probe.write(b"portable")
                probe.flush()
        except OSError:
            QMessageBox.warning(None, "Dossier en lecture seule",
                                "Ce dossier ne permet pas d’enregistrer vos horaires. "
                                "Déplacez le dossier complet vers Documents ou une clé USB où vous pouvez écrire.")
            initial = str(folder)
            continue
        return folder
