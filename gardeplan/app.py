"""Démarrage local : aucune connexion, aucun compte, aucun serveur."""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import date, timedelta, datetime
from pathlib import Path
import sys
import traceback

from PySide6.QtCore import QLockFile, QStandardPaths
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QMessageBox

from gardeplan import __version__
from gardeplan.branding import DISPLAY_NAME, STORAGE_APPLICATION, STORAGE_ORGANIZATION
from gardeplan.models import Week
from gardeplan.storage import Repository
from gardeplan.data_paths import database_path, portable_root
from gardeplan.ui.localization import install_french_translations

STYLE = """
QWidget { font-family:'Segoe UI','SF Pro Text','Noto Sans',sans-serif; font-size:13px; color:#293D34; }
QMainWindow, QDialog, QWidget#workspace { background:#F6F8F5; }
QLabel { background:transparent; }
QLabel#brandTitle { font-size:24px; font-weight:700; color:#203F30; }
QLabel#brandSubtitle { font-size:10px; font-weight:600; color:#7F9385; }
QLabel#sectionTitle { font-size:17px; font-weight:650; color:#2D4435; }
QLabel#muted { color:#7A8B7F; font-size:12px; }
QLabel#smallMuted { color:#7C8C80; font-size:11px; }
QFrame#weekNavigation { background:#FFFFFF; border:1px solid #E1E8DF; border-radius:12px; }
QDateEdit#weekDate { background:transparent; border:0; font-weight:600; color:#38533F; padding:4px 5px; }
QDateEdit#weekDate::drop-down { border:0; width:20px; }
QComboBox#statusBadge { background:#ECEEE7; color:#6D7862; border:0; border-radius:15px; padding:9px 15px; font-weight:600; }
QComboBox#statusBadge[status='validated'] { background:#E2EEDF; color:#426B41; }
QComboBox#statusBadge[status='published'] { background:#DDEDE4; color:#2D704C; }
QComboBox#statusBadge[status='archived'] { background:#E9EDEB; color:#718079; }
QComboBox#statusBadge::drop-down { border:0; width:20px; }
QPushButton, QToolButton { background:#FFFFFF; border:1px solid #DEE7DD; border-radius:9px; padding:9px 13px; font-weight:500; }
QPushButton:hover, QToolButton:hover { background:#EEF4EC; border-color:#A9BFA9; }
QPushButton:pressed, QToolButton:pressed { background:#E2EDDF; }
QPushButton:disabled { color:#A3AEA3; border-color:#E8EDE6; background:#F3F6F1; }
QPushButton#primary { background:#355C42; color:#FFFFFF; border:1px solid #355C42; font-weight:600; padding:10px 17px; }
QPushButton#primary:hover { background:#284B35; border-color:#284B35; }
QPushButton#primary:disabled { background:#AABDAC; color:#F4F7F2; border-color:#AABDAC; }
QPushButton#iconButton { background:transparent; border:0; border-radius:9px; padding:8px; }
QPushButton#iconButton:hover { background:#E8EFE5; }
QPushButton#iconButton:disabled { background:transparent; }
QPushButton#subtleButton { background:transparent; border:0; color:#5D7761; padding:7px 9px; }
QPushButton#subtleButton:hover { background:#EAF1E6; }
QPushButton#subtleButton:checked { background:#EBF2E8; color:#436A48; }
QPushButton#subtleButton:disabled { color:#ABB6AB; background:transparent; }
QFrame#segmentedControl { background:#EAF0E6; border:0; border-radius:10px; }
QPushButton#segment { background:transparent; color:#758671; border:0; border-radius:7px; padding:7px 15px; }
QPushButton#segment:checked { background:#FFFFFF; color:#355C3F; font-weight:600; }
QPushButton#segment:hover:!checked { background:#DFE9DA; }
QPushButton#alertBadge { background:#EBF2E7; color:#5E7E54; border:0; border-radius:14px; padding:7px 12px; font-size:12px; }
QPushButton#alertBadge[hasErrors='true'] { background:#FCF0E1; color:#9D6B2F; }
QFrame#sidebar { background:#F0F4ED; border:1px solid #E4EBDD; border-radius:15px; }
QFrame#divider { background:#DFE8DA; border:0; }
QLineEdit#educatorSearch { background:#FFFFFF; border:1px solid #E3EADF; border-radius:9px; padding:9px 7px; }
QCheckBox#quietCheckbox { color:#7C8B79; font-size:11px; }
QListWidget#educatorList { background:transparent; border:0; }
QListWidget#educatorList::item { border:1px solid transparent; border-radius:11px; padding:0; }
QListWidget#educatorList::item:selected { border-color:#A3BCA0; background:#E5EEDC; }
QListWidget#educatorList::item:hover { border-color:#CEDDC6; }
QFrame#educatorCard { background:#FFFFFF; border:1px solid #E3EADD; border-radius:11px; }
QLabel#educatorName { font-weight:600; font-size:13px; color:#354D3B; }
QLabel#educatorHours { font-size:17px; font-weight:650; color:#385442; }
QFrame#calendarSurface { background:#FFFFFF; border:1px solid #DFE7DC; border-radius:15px; }
QWidget#calendarToolbar { background:transparent; border-bottom:1px solid #E9EEE5; }
QComboBox#daySelector { background:transparent; border:0; color:#35513D; font-size:14px; font-weight:600; padding:8px 2px; }
QWidget#calendarTools { background:#FCFDFB; border-top:1px solid #EAF0E6; }
QComboBox#compactCombo { padding:5px 8px; min-height:20px; border-radius:7px; font-size:12px; }
QLabel#versionBanner { background:#FAF3DE; color:#846F32; padding:9px 14px; }
QFrame#alertPanel { background:#FEFEFC; border:1px solid #E4E9DF; border-radius:12px; }
QLabel#alertTitle { color:#596C55; font-size:12px; font-weight:600; }
QListWidget#alertList { background:transparent; border:0; border-radius:0; font-size:12px; }
QListWidget#alertList::item { border:0; padding:5px 0; }
QListWidget#alertList::item:selected { background:#F0F4E9; color:#576F4A; border-radius:6px; }
QLineEdit, QSpinBox, QComboBox, QDateEdit, QTextEdit { background:#FFFFFF; border:1px solid #DCE5D7; border-radius:8px; padding:7px; selection-background-color:#537C58; }
QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QDateEdit:focus, QTextEdit:focus { border-color:#8CA780; }
QComboBox QAbstractItemView { background:#FFFFFF; border:1px solid #DEE7D7; selection-background-color:#E6EFDF; selection-color:#35583B; outline:0; }
QListWidget, QTableWidget, QTreeWidget { background:#FFFFFF; border:1px solid #DFE7DB; border-radius:9px; outline:0; }
QListWidget::item { padding:7px; border-bottom:1px solid #F0F3ED; }
QListWidget::item:selected { background:#E8F0E2; color:#3C6040; }
QHeaderView::section { background:#F0F5EC; border:0; padding:9px; font-weight:600; color:#5A7453; }
QProgressBar { background:#EAF0E6; border:0; border-radius:3px; max-height:6px; }
QProgressBar::chunk { background:#7D9E70; border-radius:3px; }
QTabWidget::pane { border:1px solid #DFE7D8; background:#FFFFFF; border-radius:9px; }
QTabBar::tab { padding:11px 16px; background:#EDF3E7; color:#72856A; }
QTabBar::tab:selected { background:#FFFFFF; color:#3D6443; }
QCheckBox::indicator { width:14px; height:14px; border:1px solid #B7C7AF; background:#FFFFFF; border-radius:4px; }
QCheckBox::indicator:checked { background:#6D8B60; border-color:#6D8B60; }
QSlider::groove:horizontal { height:4px; background:#E1EADB; border-radius:2px; }
QSlider::handle:horizontal { background:#75926A; width:12px; height:12px; margin:-4px 0; border-radius:6px; }
QScrollBar:vertical { background:transparent; width:9px; margin:2px; }
QScrollBar::handle:vertical { background:#CDDAC6; border-radius:4px; min-height:28px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
QScrollBar:horizontal { background:#F3F6EF; height:9px; }
QScrollBar::handle:horizontal { background:#CDDAC6; border-radius:4px; min-width:28px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width:0; }
QStatusBar { background:#F6F8F5; color:#7A8F78; border-top:1px solid #E6ECE0; }
QStatusBar::item { border:0; }
QSplitter::handle { background:transparent; }
QMenu { background:#FFFFFF; border:1px solid #E0E8D9; border-radius:10px; padding:6px; }
QMenu::item { padding:8px 18px; border-radius:6px; }
QMenu::item:selected { background:#ECF3E6; color:#3B6543; }
QToolTip { background:#2F4C36; color:#FFFFFF; padding:8px; border:0; }
"""


def main(argv=None):
    parser = argparse.ArgumentParser(description=f"{DISPLAY_NAME} — planification hors ligne")
    parser.add_argument("--database", type=Path, help="Chemin de la base SQLite locale")
    parser.add_argument("--example", action="store_true", help="Créer un exemple dans une base distincte")
    parser.add_argument("--portable", action="store_true", help="Conserver les données à côté du logiciel")
    parser.add_argument("--check-installation", type=Path, metavar="RESULTAT_JSON",
                        help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.example and args.database:
        parser.error("--example utilise une base distincte ; ne pas combiner avec --database.")
    if args.check_installation is not None:
        if args.example or args.database or args.portable:
            parser.error("Le contrôle d'installation utilise uniquement des données temporaires.")
        from gardeplan.installation_check import check_installation
        return check_installation(args.check_installation)
    app = QApplication.instance() or QApplication(sys.argv[:1])
    app.setApplicationName(STORAGE_APPLICATION)
    app.setOrganizationName(STORAGE_ORGANIZATION)
    app.setApplicationDisplayName(DISPLAY_NAME)
    app.setApplicationVersion(__version__)
    from gardeplan.ui.visuals import logo_icon
    app.setWindowIcon(logo_icon())
    install_french_translations(app)
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(STYLE)
    location = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation))
    portable = portable_root(force=args.portable) is not None and args.database is None
    app.setProperty("portableMode", portable)
    database = database_path(location, database=args.database, example=args.example,
                             force_portable=args.portable)
    try:
        database.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        action = ("Déplacez le dossier complet du logiciel vers un emplacement où vous pouvez enregistrer des fichiers, puis réessayez."
                  if portable else "Le dossier des données n'est pas accessible. Vérifiez les droits d'accès à ce dossier.")
        QMessageBox.critical(None, "Dossier inaccessible", f"{action}\n\n{exc}")
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
        if portable:
            window.setWindowTitle(f"{DISPLAY_NAME} — Portable")
            window.save_label.setText("Mode portable · les données restent dans le dossier du logiciel.")
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
