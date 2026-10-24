"""Démarrage local : aucune connexion, aucun compte, aucun serveur."""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import date, timedelta, datetime
from pathlib import Path
import sys
import traceback

from PySide6.QtCore import QLocale, QLockFile, QStandardPaths
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QMessageBox

from gardeplan import __version__
from gardeplan.branding import DISPLAY_NAME, STORAGE_APPLICATION, STORAGE_ORGANIZATION
from gardeplan.models import Week
from gardeplan.storage import Repository

STYLE = """
QWidget { font-family: 'Segoe UI', 'Noto Sans', sans-serif; font-size: 13px; color:#263D45; }
QMainWindow, QDialog { background:#F5F7F6; }
QLabel#title { font-size:25px; font-weight:700; color:#183F3A; }
QLabel#subtitle { color:#6C7D79; font-size:12px; }
QPushButton, QToolButton { background:white; border:1px solid #DCE4E0; border-radius:7px;
    padding:8px 12px; font-weight:500; }
QPushButton:hover, QToolButton:hover { background:#EAF1EE; border-color:#93B7AC; }
QPushButton:pressed { background:#DCEBE4; }
QPushButton:disabled { color:#98A6A0; background:#F0F3F1; }
QPushButton#primary { background:#246C59; color:white; border-color:#246C59; font-weight:600; }
QPushButton#primary:hover { background:#1C5747; }
QPushButton:checked, QToolButton:checked { background:#DDEDE5; color:#205F4E; border-color:#A1C4B4; }
QLineEdit, QSpinBox, QComboBox, QDateEdit, QTextEdit { background:white; border:1px solid #D9E2DD;
    border-radius:6px; padding:6px; selection-background-color:#347F68; }
QListWidget, QTableWidget, QTreeWidget { background:white; border:1px solid #E0E7E3; border-radius:8px; }
QListWidget::item { padding:6px; border-bottom:1px solid #EDF1EF; }
QListWidget::item:selected { background:#E1EFE8; color:#235F4E; }
QHeaderView::section { background:#EDF3EF; border:0; padding:8px; font-weight:600; }
QProgressBar { background:#E8EFEB; border:0; border-radius:3px; max-height:6px; }
QProgressBar::chunk { background:#5C9D87; border-radius:3px; }
QTabWidget::pane { border:1px solid #DDE5DF; background:white; border-radius:7px; }
QTabBar::tab { padding:10px 16px; background:#EAF0EC; }
QTabBar::tab:selected { background:white; color:#235F4E; }
QScrollBar:vertical { background:#F2F5F3; width:10px; }
QScrollBar::handle:vertical { background:#BFCEC6; border-radius:4px; min-height:30px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
QStatusBar { background:#EAF1EC; color:#5D7468; }
QSplitter::handle { background:#E4EBE6; }
QToolTip { background:#203D32; color:white; padding:8px; border:0; }
"""


def main(argv=None):
    parser = argparse.ArgumentParser(description=f"{DISPLAY_NAME} — planification hors ligne")
    parser.add_argument("--database", type=Path, help="Chemin de la base SQLite locale")
    parser.add_argument("--example", action="store_true", help="Créer un exemple dans une base distincte")
    parser.add_argument("--check-installation", type=Path, metavar="RESULTAT_JSON",
                        help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.example and args.database:
        parser.error("--example utilise une base distincte ; ne pas combiner avec --database.")
    if args.check_installation is not None:
        if args.example or args.database:
            parser.error("Le contrôle d'installation utilise uniquement des données temporaires.")
        from gardeplan.installation_check import check_installation
        return check_installation(args.check_installation)
    app = QApplication.instance() or QApplication(sys.argv[:1])
    app.setApplicationName(STORAGE_APPLICATION)
    app.setOrganizationName(STORAGE_ORGANIZATION)
    app.setApplicationDisplayName(DISPLAY_NAME)
    app.setApplicationVersion(__version__)
    QLocale.setDefault(QLocale(QLocale.Language.French, QLocale.Country.Canada))
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(STYLE)
    location = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation))
    database = args.database or location / ("exemple.sqlite" if args.example else "gardeplan.sqlite")
    database = database.expanduser().resolve()
    try:
        database.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        QMessageBox.critical(None, "Dossier inaccessible", f"Choisissez un dossier accessible avec --database.\n\n{exc}")
        return 1
    lock = QLockFile(str(database) + ".lock")
    lock.setStaleLockTime(30000)
    if not lock.tryLock(100):
        QMessageBox.warning(None, "Base déjà ouverte", f"{DISPLAY_NAME} utilise déjà cette base. Revenez à sa fenêtre ouverte.")
        return 1
    try:
        repo = Repository(database)
        # Une copie journalière complète protège également l'historique.
        if repo.latest_week() is not None:
            backup = database.parent / "backups" / f"{database.stem}-{date.today().isoformat()}.sqlite"
            if not backup.exists():
                try:
                    repo.backup(backup)
                except (ValueError, OSError) as exc:
                    QMessageBox.warning(None, "Copie de sécurité non créée",
                                        f"La base peut être ouverte. Choisissez ensuite un autre dossier pour une sauvegarde.\n\n{exc}")
        today = date.today()
        monday = (today - timedelta(days=today.weekday())).isoformat()
        week = repo.load_week(monday)
        if week is None:
            if args.example:
                from gardeplan.sample import example_week
                week = example_week(monday)
            else:
                previous = repo.latest_week()
                week = Week(monday)
                if previous:
                    week.educators, week.groups, week.rooms, week.settings = deepcopy((
                        previous.educators, previous.groups, previous.rooms, previous.settings))
                    for educator in week.educators:
                        educator.absences = []
            repo.save(week)
        from gardeplan.ui.main_window import MainWindow
        window = MainWindow(repo, week)
    except Exception as exc:
        QMessageBox.critical(None, "Ouverture impossible", f"Vos données sont conservées.\n\n{exc}")
        lock.unlock()
        return 1

    def exception_hook(kind, value, tb):
        log = database.parent / "erreurs.log"
        try:
            with log.open("a", encoding="utf-8") as handle:
                handle.write(f"\n{datetime.now().isoformat()}\n")
                traceback.print_exception(kind, value, tb, file=handle)
        except OSError:
            pass
        QMessageBox.critical(window, "Action interrompue", f"L'action n'a pas pu être terminée.\n{value}\n\nVos versions sauvegardées restent disponibles.")
    sys.excepthook = exception_hook
    window.show()
    result = app.exec()
    lock.unlock()
    return result
