"""Tableau de bord local : orchestration des éditeurs et des services métier."""
from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path
import tempfile

from PySide6.QtCore import Qt, QDate, QMimeData, QThread, QTimer, Signal, QSize
from PySide6.QtGui import QAction, QColor, QDrag, QKeySequence, QPainter
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDateEdit, QDialog,
    QDialogButtonBox, QFileDialog, QFormLayout, QFrame, QHBoxLayout,
    QInputDialog, QLabel, QListWidget, QListWidgetItem, QMainWindow,
    QMenu, QMessageBox, QProgressBar, QProgressDialog, QPushButton,
    QSlider, QSpinBox, QSplitter, QVBoxLayout, QWidget,
)

from ..branding import DISPLAY_NAME, SHORT_NAME
from ..models import (
    Week, Shift, Activity, STATUS_LABELS, DAYS, new_id, totals,
    format_duration, format_time, move_shift,
)
from ..validation import validate
from ..optimizer import generate
from ..pdf import export_general, export_individual, export_combined, export_all_individual
from .calendar import CalendarWidget, EDUCATOR_MIME
from .forms import EducatorDialog, GroupDialog, RoomDialog, ShiftDialog, ActivityDialog, SettingsDialog, integer, note


class EducatorList(QListWidget):
    def __init__(self):
        super().__init__()
        self.setDragEnabled(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setSpacing(7)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet("QListWidget {background:transparent;} QListWidget::item:selected {background:#e3eee8;border-radius:8px;}")
        self.setAccessibleName("Éducatrices à glisser dans le calendrier")

    def startDrag(self, supported_actions):
        item = self.currentItem()
        if not item or not item.data(Qt.ItemDataRole.UserRole + 1):
            return
        mime = QMimeData()
        mime.setData(EDUCATOR_MIME, item.data(Qt.ItemDataRole.UserRole).encode("utf-8"))
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.CopyAction)


class GenerationThread(QThread):
    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, week, parent=None):
        super().__init__(parent)
        self.snapshot = deepcopy(week)

    def run(self):
        try:
            self.completed.emit(generate(self.snapshot, time_limit=20))
        except Exception as error:
            self.failed.emit(f"La génération a échoué : {error}")


class MainWindow(QMainWindow):
    def __init__(self, repo, week, parent=None):
        super().__init__(parent)
        self.repo, self.week = repo, deepcopy(week)
        self.day = 0
        self.issues = []
        self.dirty = False
        self._history_version = None
        self._undo, self._redo = [], []
        self._worker = None
        self._progress = None
        self._save_error_shown = False
        self._updating = False
        self._children = []
        self.autosave = QTimer(self)
        self.autosave.setSingleShot(True)
        self.autosave.setInterval(1400)
        self.autosave.timeout.connect(lambda: self.save_week(manual=False))
        self.setWindowTitle(DISPLAY_NAME)
        self.resize(1480, 940)
        self.setMinimumSize(1080, 720)
        self._build_ui()
        self.refresh()
        QTimer.singleShot(0, lambda: self.calendar.scroll_to(390))

    @property
    def read_only(self):
        return self.week.status == "archived" or self._history_version is not None or self._worker is not None

    def _button(self, text, slot, tooltip="", primary=False):
        button = QPushButton(text)
        button.clicked.connect(slot)
        if tooltip:
            button.setToolTip(tooltip)
        if primary:
            button.setObjectName("primary")
        return button

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(22, 18, 22, 12)
        root.setSpacing(12)
        self.top_controls = QWidget()
        top = QVBoxLayout(self.top_controls)
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(12)
        heading = QHBoxLayout()
        brand = QLabel(DISPLAY_NAME.split(" — ", 1)[0])
        brand.setStyleSheet("font-size:25px;font-weight:700;color:#214d3d;")
        heading.addWidget(brand)
        heading.addWidget(note("SERVICE DE GARDE"))
        heading.addStretch()
        heading.addWidget(self._button("‹", lambda: self.navigate_week(-1), "Semaine précédente"))
        self.week_date = QDateEdit()
        self.week_date.setCalendarPopup(True)
        self.week_date.setDisplayFormat("'Semaine du' dd MMMM yyyy")
        self.week_date.setMinimumWidth(245)
        self.week_date.dateChanged.connect(self._date_changed)
        heading.addWidget(self.week_date)
        heading.addWidget(self._button("›", lambda: self.navigate_week(1), "Semaine suivante"))
        self.status_combo = QComboBox()
        for value, label in STATUS_LABELS.items():
            self.status_combo.addItem(label, value)
        self.status_combo.setToolTip("Les erreurs bloquent la validation et la publication, jamais le brouillon.")
        self.status_combo.activated.connect(self._status_selected)
        heading.addWidget(self.status_combo)
        self.more_button = QPushButton("Plus  ⋯")
        menu = QMenu(self)
        for label, callback in [
            ("Consulter une autre semaine…", self.choose_week),
            ("Dupliquer cette semaine…", self.duplicate_week),
            ("Historique des versions…", self.show_history),
            ("Exporter une sauvegarde locale…", self.backup),
            ("Importer une sauvegarde locale…", self.import_backup),
        ]:
            action = menu.addAction(label)
            action.triggered.connect(callback)
        self.more_button.setMenu(menu)
        heading.addWidget(self.more_button)
        top.addLayout(heading)
        commands = QHBoxLayout()
        self.sidebar_toggle = self._button("☰ Éducatrices", self.toggle_sidebar, "Réduire ou afficher le panneau des éducatrices")
        commands.addWidget(self.sidebar_toggle)
        self.day_mode = self._button("Jour", lambda: self.set_mode("Jour"))
        self.week_mode = self._button("Semaine", lambda: self.set_mode("Semaine"))
        for button in (self.day_mode, self.week_mode):
            button.setCheckable(True)
            commands.addWidget(button)
        self.day_mode.setChecked(True)
        self.undo_button = self._button("Annuler", self.undo, "Annuler la dernière modification — Ctrl+Z")
        self.redo_button = self._button("Rétablir", self.redo, "Rétablir — Ctrl+Maj+Z")
        commands.addWidget(self.undo_button)
        commands.addWidget(self.redo_button)
        commands.addStretch()
        self.generate_button = self._button("Générer automatiquement", self.start_generation, primary=True)
        self.verify_button = self._button("Vérifier l'horaire", self.verify)
        self.save_button = self._button("Sauvegarder", lambda: self.save_week(manual=True))
        self.export_button = self._button("Exporter PDF", self.export_pdf)
        for button in (self.generate_button, self.verify_button, self.save_button, self.export_button):
            commands.addWidget(button)
        top.addLayout(commands)
        root.addWidget(self.top_controls)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        root.addWidget(self.splitter, 1)
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setMinimumWidth(255)
        sidebar = QVBoxLayout(self.sidebar)
        sidebar.setContentsMargins(13, 14, 13, 14)
        side_head = QHBoxLayout()
        title = QLabel("Éducatrices")
        title.setStyleSheet("font-size:18px;font-weight:650;")
        side_head.addWidget(title)
        side_head.addStretch()
        self.add_educator_button = self._button("+ Ajouter", lambda: self.edit_educator())
        side_head.addWidget(self.add_educator_button)
        sidebar.addLayout(side_head)
        sidebar.addWidget(note("Glissez un nom dans un groupe.\nDouble-cliquez pour modifier son profil."))
        self.show_inactive = QCheckBox("Afficher les éducatrices inactives")
        self.show_inactive.toggled.connect(self.refresh_educators)
        sidebar.addWidget(self.show_inactive)
        self.educator_list = EducatorList()
        self.educator_list.itemDoubleClicked.connect(lambda item: self.edit_educator(item.data(Qt.ItemDataRole.UserRole)))
        sidebar.addWidget(self.educator_list, 1)
        settings_row = QHBoxLayout()
        self.groups_button = self._button("Groupes", lambda: self.manage_entities("groups"))
        self.rooms_button = self._button("Locaux", lambda: self.manage_entities("rooms"))
        self.settings_button = self._button("Paramètres", self.edit_settings)
        for button in (self.groups_button, self.rooms_button, self.settings_button):
            settings_row.addWidget(button)
        sidebar.addLayout(settings_row)
        self.splitter.addWidget(self.sidebar)
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)
        day_row = QHBoxLayout()
        self.day_combo = QComboBox()
        self.day_combo.setMinimumWidth(190)
        self.day_combo.activated.connect(self.select_day)
        day_row.addWidget(self.day_combo)
        self.name_day_button = self._button("Nommer la journée", self.name_day)
        self.enrolment_button = self._button("Inscriptions", self.enrolment)
        day_row.addWidget(self.name_day_button)
        day_row.addWidget(self.enrolment_button)
        day_row.addStretch()
        self.add_shift_button = self._button("+ Quart", self.new_shift)
        self.add_activity_button = self._button("+ Activité", self.new_activity)
        day_row.addWidget(self.add_shift_button)
        day_row.addWidget(self.add_activity_button)
        right_layout.addLayout(day_row)
        self.version_banner = QLabel()
        self.version_banner.setWordWrap(True)
        self.version_banner.setStyleSheet("background:#fff4d4;color:#6b531b;padding:9px;border-radius:6px;")
        right_layout.addWidget(self.version_banner)
        self.calendar = CalendarWidget()
        self.calendar.edit_requested.connect(self.edit_block)
        self.calendar.change_requested.connect(self.change_block)
        self.calendar.educator_dropped.connect(self.educator_drop)
        self.calendar.day_selected.connect(self.expand_day)
        self.calendar.create_requested.connect(self.calendar_create)
        right_layout.addWidget(self.calendar, 1)
        calendar_tools = QHBoxLayout()
        calendar_tools.addWidget(note("Magnétisme"))
        self.snap_combo = QComboBox()
        for label, value in [("Libre · minute", 0), ("1 min", 1), ("5 min", 5), ("15 min", 15)]:
            self.snap_combo.addItem(label, value)
        self.snap_combo.activated.connect(self._snap_changed)
        calendar_tools.addWidget(self.snap_combo)
        calendar_tools.addSpacing(14)
        calendar_tools.addWidget(note("Zoom"))
        self.zoom = QSlider(Qt.Orientation.Horizontal)
        self.zoom.setRange(15, 200)
        self.zoom.setValue(100)
        self.zoom.setMaximumWidth(125)
        self.zoom.valueChanged.connect(lambda value: self.calendar.set_zoom(value / 100))
        calendar_tools.addWidget(self.zoom)
        calendar_tools.addWidget(self._button("Journée entière", self.fit_day, "Afficher toute la journée, préparation et fermeture incluses"))
        calendar_tools.addStretch()
        self.alert_toggle = self._button("Alertes", self.toggle_alerts)
        self.alert_toggle.setCheckable(True)
        self.alert_toggle.setChecked(True)
        calendar_tools.addWidget(self.alert_toggle)
        right_layout.addLayout(calendar_tools)
        self.alert_list = QListWidget()
        self.alert_list.setMaximumHeight(155)
        self.alert_list.setMinimumHeight(85)
        self.alert_list.setWordWrap(True)
        self.alert_list.itemClicked.connect(self.navigate_issue)
        right_layout.addWidget(self.alert_list)
        self.splitter.addWidget(right)
        self.splitter.setSizes([310, 1110])
        self.save_label = QLabel("Toutes les données restent sur cet ordinateur.")
        self.statusBar().addWidget(self.save_label, 1)
        self.statusBar().addPermanentWidget(note("Hors ligne · aucune donnée nominative d'élève"))
        for shortcut, callback in [("Ctrl+S", lambda: self.save_week(manual=True)), ("Ctrl+Z", self.undo), ("Ctrl+Shift+Z", self.redo), ("Ctrl+Y", self.redo)]:
            action = QAction(self)
            action.setShortcut(QKeySequence(shortcut))
            action.triggered.connect(callback)
            self.addAction(action)

    def refresh(self):
        self._updating = True
        self.issues = validate(self.week)
        self.week_date.setDate(QDate.fromString(self.week.monday, "yyyy-MM-dd"))
        self.status_combo.setCurrentIndex(max(0, self.status_combo.findData(self.week.status)))
        self.day_combo.clear()
        self.day_combo.addItems([self.week.day_label(day) for day in range(5)])
        self.day_combo.setCurrentIndex(self.day)
        self.snap_combo.setCurrentIndex(max(0, self.snap_combo.findData(self.week.settings.snap_minutes)))
        self.calendar.set_snap(self.week.settings.snap_minutes)
        self.calendar.set_week(self.week, self.day, self.issues)
        self.calendar.set_read_only(self.read_only)
        self.refresh_educators()
        self.refresh_alerts()
        self.undo_button.setEnabled(bool(self._undo) and not self.read_only)
        self.redo_button.setEnabled(bool(self._redo) and not self.read_only)
        for widget in (self.generate_button, self.add_educator_button, self.add_shift_button, self.add_activity_button, self.name_day_button, self.enrolment_button, self.settings_button):
            widget.setEnabled(not self.read_only)
        self.status_combo.setEnabled(not self.read_only)
        self.save_button.setEnabled(self._history_version is None and self._worker is None)
        self.snap_combo.setEnabled(not self.read_only)
        banner = ""
        if self._history_version is not None:
            banner = f"Version {self._history_version} en consultation. L'historique permet de la restaurer comme nouveau brouillon."
        elif self.week.status == "archived":
            banner = "Semaine archivée : consultation uniquement. Dupliquez-la ou restaurez une version pour la modifier."
        elif self.week.status == "published":
            banner = "Version publiée conservée dans l'historique. Toute modification créera un nouveau brouillon."
        self.version_banner.setText(banner)
        self.version_banner.setVisible(bool(banner))
        self._updating = False

    def refresh_educators(self):
        selected = self.educator_list.currentItem()
        selected_id = selected.data(Qt.ItemDataRole.UserRole) if selected else None
        self.educator_list.clear()
        planned = totals(self.week)
        for educator in sorted(self.week.educators, key=lambda item: (not item.active, item.seniority, item.name)):
            if not educator.active and not self.show_inactive.isChecked():
                continue
            minutes = planned.get(educator.id, 0)
            remaining = educator.target_minutes - minutes
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, educator.id)
            item.setData(Qt.ItemDataRole.UserRole + 1, educator.active and not self.read_only)
            item.setSizeHint(QSize(250, 127))
            card = QFrame()
            card.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            card.setStyleSheet(f"QFrame {{background:white;border:1px solid #e4e9e6;border-left:5px solid {educator.color};border-radius:8px;}} QLabel {{border:0;background:transparent;}}")
            layout = QVBoxLayout(card)
            layout.setContentsMargins(11, 9, 10, 9)
            layout.setSpacing(4)
            name = QLabel(educator.name + (" · inactive" if not educator.active else ""))
            name.setStyleSheet("font-weight:650;font-size:14px;color:#203b31;")
            layout.addWidget(name)
            layout.addWidget(note(f"Ancienneté {educator.seniority} · objectif {format_duration(educator.target_minutes)}"))
            layout.addWidget(QLabel(f"Planifiées {format_duration(minutes)}"))
            label = QLabel(f"{'Restantes' if remaining >= 0 else 'Au-delà de la cible'} : {format_duration(abs(remaining))}")
            label.setStyleSheet("color:#975619;" if remaining < 0 else "color:#5f7267;")
            layout.addWidget(label)
            progress = QProgressBar()
            progress.setRange(0, max(1, educator.target_minutes))
            progress.setValue(min(minutes, max(1, educator.target_minutes)))
            progress.setTextVisible(False)
            progress.setFixedHeight(5)
            progress.setStyleSheet(f"QProgressBar {{border:0;background:#edf1ee;border-radius:2px;}} QProgressBar::chunk {{background:{educator.color};border-radius:2px;}}")
            layout.addWidget(progress)
            self.educator_list.addItem(item)
            self.educator_list.setItemWidget(item, card)
            if educator.id == selected_id:
                self.educator_list.setCurrentItem(item)
        if not self.week.educators:
            empty = QListWidgetItem("Ajoutez vos éducatrices pour commencer.")
            empty.setFlags(Qt.ItemFlag.NoItemFlags)
            self.educator_list.addItem(empty)

    def refresh_alerts(self):
        self.alert_list.clear()
        errors = sum(issue.severity == "error" for issue in self.issues)
        warnings = len(self.issues) - errors
        self.alert_toggle.setText(f"{errors} erreur{'s' if errors != 1 else ''} · {warnings} avertissement{'s' if warnings != 1 else ''}")
        self.verify_button.setText(f"Vérifier ({errors})" if errors else "Vérifier l'horaire")
        for issue in sorted(self.issues, key=lambda item: (item.severity != "error", item.day if item.day is not None else 9, item.start or 0)):
            item = QListWidgetItem(("● " if issue.severity == "error" else "△ ") + issue.message)
            item.setForeground(QColor("#a33c32" if issue.severity == "error" else "#8a651a"))
            item.setData(Qt.ItemDataRole.UserRole, issue)
            item.setToolTip(issue.suggestion or issue.message)
            self.alert_list.addItem(item)
        if not self.issues:
            self.alert_list.addItem("✓ Aucune erreur détectée. La couverture et les heures ont été vérifiées.")

    def _can_edit(self):
        if self.read_only:
            QMessageBox.information(self, "Consultation", "Cette version est en lecture seule. Dupliquez la semaine ou restaurez une version depuis l'historique pour la modifier.")
            return False
        return True

    def commit(self, mutation):
        if not self._can_edit():
            return False
        before = deepcopy(self.week)
        candidate = deepcopy(self.week)
        try:
            changed = mutation(candidate)
            if isinstance(changed, Week):
                candidate = changed
            candidate.status = "draft"
            # Round-trip asserts basic types; business-invalid drafts remain editable.
            candidate = Week.from_dict(candidate.to_dict())
        except Exception as error:
            QMessageBox.warning(self, "Modification impossible", str(error))
            return False
        if before.to_dict() == candidate.to_dict():
            return False
        self._undo.append(before)
        self._undo = self._undo[-80:]
        self._redo.clear()
        self.week = candidate
        self._modified()
        return True

    def _modified(self):
        self.dirty = True
        self.save_label.setText("Modifications en cours de sauvegarde…")
        self.refresh()
        self.autosave.start()

    def undo(self):
        if not self._undo or self.read_only:
            return
        self._redo.append(deepcopy(self.week))
        self.week = self._undo.pop()
        self.week.status = "draft"
        self._modified()

    def redo(self):
        if not self._redo or self.read_only:
            return
        self._undo.append(deepcopy(self.week))
        self.week = self._redo.pop()
        self.week.status = "draft"
        self._modified()

    def save_week(self, manual=True):
        if self._history_version is not None:
            return True
        self.autosave.stop()
        try:
            self.repo.save(self.week)
            self.dirty = False
            self._save_error_shown = False
            self.save_label.setText("✓ Sauvegardé sur cet ordinateur" + (" — brouillon avec alertes" if any(i.severity == "error" for i in self.issues) else ""))
            if manual:
                self.statusBar().showMessage("L'horaire est sauvegardé.", 4000)
            return True
        except Exception as error:
            self.dirty = True
            self.save_label.setText("Échec de sauvegarde — modifications conservées en mémoire")
            if manual or not self._save_error_shown:
                QMessageBox.critical(self, "Sauvegarde impossible", f"{error}\n\nGardez l'application ouverte et choisissez un dossier accessible ou libérez de l'espace avant de réessayer.")
                self._save_error_shown = True
            return False

    def _load(self, week, version=None):
        self.autosave.stop()
        self.week = deepcopy(week)
        self._history_version = version
        self._undo.clear()
        self._redo.clear()
        self.dirty = False
        self.save_label.setText("Version consultée" if version else "Semaine chargée depuis cet ordinateur")
        self.refresh()

    def _date_changed(self, selected):
        if not self._updating:
            self.switch_week(selected.toPython())

    def navigate_week(self, direction):
        self.switch_week(date.fromisoformat(self.week.monday) + timedelta(days=direction * 7))

    def switch_week(self, selected):
        if self._worker is not None:
            return
        monday = selected - timedelta(days=selected.weekday())
        monday_text = monday.isoformat()
        if monday_text == self.week.monday and self._history_version is None:
            return
        if self.dirty and not self.save_week():
            self.refresh()
            return
        try:
            week = self.repo.load_week(monday_text)
            if week is None:
                template = self.repo.latest_week() or self.week
                week = Week(monday_text, educators=deepcopy(template.educators), groups=deepcopy(template.groups), rooms=deepcopy(template.rooms), settings=deepcopy(template.settings))
                for educator in week.educators:
                    educator.absences = []
                self.repo.save(week)
            self._load(week)
        except Exception as error:
            QMessageBox.warning(self, "Semaine indisponible", str(error))
            self.refresh()

    def select_day(self, day):
        self.day = max(0, min(4, day))
        self.day_combo.setCurrentIndex(self.day)
        self.calendar.set_week(self.week, self.day, self.issues)

    def expand_day(self, day):
        self.select_day(day)
        self.set_mode("Jour")

    def set_mode(self, mode):
        self.calendar.set_mode(mode)
        self.day_mode.setChecked(mode == "Jour")
        self.week_mode.setChecked(mode == "Semaine")

    def toggle_sidebar(self):
        self.sidebar.setVisible(not self.sidebar.isVisible())

    def toggle_alerts(self):
        self.alert_list.setVisible(self.alert_toggle.isChecked())

    def fit_day(self):
        first = max(0, self.week.settings.open_minute - self.week.settings.opening_buffer)
        last = min(1440, self.week.settings.close_minute + self.week.settings.closing_buffer)
        height = max(120, self.calendar.scroll.viewport().height() - 14)
        factor = max(.15, min(2.0, height / max(1, last - first) / 1.65))
        self.zoom.setValue(round(factor * 100))
        self.calendar.set_zoom(factor)
        self.calendar.scroll_to(first)

    def _snap_changed(self, index):
        if not self._updating:
            value = self.snap_combo.itemData(index)
            self.commit(lambda week: setattr(week.settings, "snap_minutes", value))

    def navigate_issue(self, item):
        issue = item.data(Qt.ItemDataRole.UserRole)
        if issue is not None and issue.day is not None:
            self.expand_day(issue.day)
            if issue.start is not None:
                self.calendar.scroll_to(max(0, issue.start - 20))
        if issue is not None and issue.suggestion:
            self.statusBar().showMessage(issue.suggestion, 12000)

    def verify(self):
        self.refresh()
        self.alert_toggle.setChecked(True)
        self.alert_list.show()
        errors = sum(item.severity == "error" for item in self.issues)
        self.statusBar().showMessage(f"Vérification terminée : {errors} erreur(s) bloquante(s), {len(self.issues) - errors} avertissement(s).", 8000)

    def _status_selected(self, index):
        if self._updating or not self._can_edit():
            return
        status = self.status_combo.itemData(index)
        if status == self.week.status:
            return
        errors = [issue for issue in validate(self.week) if issue.severity == "error"]
        if status in {"validated", "published"} and errors:
            QMessageBox.warning(self, "Horaire à corriger", f"{len(errors)} erreur(s) bloquent ce statut. Corrigez les alertes ou conservez un brouillon.\n\n" + errors[0].message)
            self.refresh()
            return
        if status in {"published", "archived"}:
            text = "Conserver une version publiée figée de cet horaire ?" if status == "published" else "Archiver cette semaine ? Elle restera consultable dans l'historique."
            if QMessageBox.question(self, STATUS_LABELS[status], text) != QMessageBox.StandardButton.Yes:
                self.refresh()
                return
        previous = self.week.status
        self.week.status = status
        if not self.save_week():
            self.week.status = previous
        self.refresh()

    def name_day(self):
        if not self._can_edit():
            return
        name, accepted = QInputDialog.getText(self, "Nommer la journée", f"Nom facultatif pour {DAYS[self.day].lower()} (160 caractères maximum) :", text=self.week.day_names.get(self.day, ""))
        if accepted:
            name = name.strip()
            if len(name) > 160:
                QMessageBox.warning(self, "Nom trop long", "Choisissez un nom de 160 caractères maximum.")
                return
            self.commit(lambda week: week.day_names.__setitem__(self.day, name))

    def enrolment(self):
        if not self._can_edit():
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Inscriptions de la journée pédagogique")
        layout = QFormLayout(dialog)
        count = integer(0, 0, 10000, " enfants")
        for group in self.week.groups:
            count.setValue(count.value() + max([p.students for p in group.periods if p.day == self.day] or [0]))
        size = integer(20, 1, 1000, " enfants / groupe")
        from PySide6.QtWidgets import QLineEdit
        day_name = QLineEdit(self.week.day_names.get(self.day, ""))
        day_name.setPlaceholderText("Ex. Journée pédagogique — Halloween")
        preview = QLabel()
        preview.setWordWrap(True)
        def update():
            groups = (count.value() + size.value() - 1) // size.value()
            full, remainder = divmod(count.value(), size.value())
            needed = full * max(2, (size.value() + 19) // 20) + (max(2, (remainder + 19) // 20) if remainder else 0)
            preview.setText(f"{groups} groupe(s), au moins {needed} éducatrices simultanément au ratio initial 1/20.\nLes groupes existants gardent leur ratio configuré ; les besoins exacts seront vérifiés après application.")
        count.valueChanged.connect(update)
        size.valueChanged.connect(update)
        update()
        layout.addRow(note(self.week.day_label(self.day)))
        layout.addRow("Nombre d'inscriptions", count)
        layout.addRow("Taille souhaitée d'un groupe", size)
        layout.addRow("Nom de la journée", day_name)
        layout.addRow(preview)
        layout.addRow(note("Cette action répartit les enfants entre les groupes et ouvre ceux-ci sur toute la journée. Les quarts et les activités existants sont conservés ; vérifiez les alertes ou générez une proposition ensuite."))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Appliquer les inscriptions")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Annuler")
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            from ..planning import plan_pedagogical_day
            self.commit(lambda week: plan_pedagogical_day(week, self.day, count.value(), size.value(), day_name.text().strip()))

    def edit_educator(self, identifier=None):
        if not self._can_edit():
            return
        educator = next((item for item in self.week.educators if item.id == identifier), None)
        dialog = EducatorDialog(self.week, educator, self)
        self._entity_dialog(dialog, "educators", educator)

    def _entity_dialog(self, dialog, collection, original):
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        if dialog.delete_requested:
            if collection in {"educators", "groups", "rooms"}:
                if collection == "educators" and any(s.educator_id == original.id for s in self.week.shifts):
                    QMessageBox.information(self, "Éducatrice affectée", "Cette éducatrice possède des quarts. Désactivez son profil pour conserver ses affectations, ou retirez ses quarts avant de supprimer le profil.")
                    return
                if collection == "groups" and (any(s.group_id == original.id for s in self.week.shifts) or any(a.group_id == original.id for a in self.week.activities)):
                    QMessageBox.information(self, "Groupe utilisé", "Retirez les quarts et activités du groupe avant de le supprimer, ou fermez ses périodes d'ouverture.")
                    return
                if collection == "rooms" and any(a.room_id == original.id for a in self.week.activities):
                    QMessageBox.information(self, "Lieu utilisé", "Changez le lieu des activités concernées avant de supprimer ce lieu.")
                    return
            self.commit(lambda week: setattr(week, collection, [item for item in getattr(week, collection) if item.id != original.id]))
        else:
            result = dialog.result_item()
            def replace(week):
                items = getattr(week, collection)
                index = next((index for index, value in enumerate(items) if value.id == result.id), None)
                if index is None:
                    items.append(result)
                else:
                    items[index] = result
            self.commit(replace)

    def manage_entities(self, collection):
        title = "Groupes" if collection == "groups" else "Locaux et extérieur"
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.resize(520, 420)
        layout = QVBoxLayout(dialog)
        layout.addWidget(note("Les modifications s'appliquent à cette semaine et aux nouvelles semaines. Les versions déjà archivées gardent leurs données."))
        listing = QListWidget()
        layout.addWidget(listing)
        def reload_items():
            listing.clear()
            for entity in getattr(self.week, collection):
                item = QListWidgetItem(entity.name)
                item.setData(Qt.ItemDataRole.UserRole, entity.id)
                listing.addItem(item)
        def edit(new=False):
            if not self._can_edit():
                return
            item = listing.currentItem()
            identifier = item.data(Qt.ItemDataRole.UserRole) if item and not new else None
            existing = next((value for value in getattr(self.week, collection) if value.id == identifier), None)
            if not new and existing is None:
                return
            factory = GroupDialog if collection == "groups" else RoomDialog
            editor = factory(self.week, existing, self)
            self._entity_dialog(editor, collection, existing)
            reload_items()
        listing.itemDoubleClicked.connect(lambda item: edit())
        actions = QHBoxLayout()
        add = self._button("+ Ajouter", lambda: edit(True))
        modify = self._button("Modifier", lambda: edit(False))
        add.setEnabled(not self.read_only)
        modify.setEnabled(not self.read_only)
        actions.addWidget(add)
        actions.addWidget(modify)
        actions.addStretch()
        actions.addWidget(self._button("Fermer", dialog.accept))
        layout.addLayout(actions)
        reload_items()
        dialog.exec()

    def edit_settings(self):
        if not self._can_edit():
            return
        dialog = SettingsDialog(self.week, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.commit(lambda week: setattr(week, "settings", dialog.result_item()))

    def new_shift(self, checked=False, *, day=None, start=None, group_id="", educator_id=""):
        if not self._can_edit():
            return
        if not self.week.educators or not self.week.groups:
            QMessageBox.information(self, "Préparer le calendrier", "Ajoutez une éducatrice et un groupe avant de créer un quart.")
            return
        dialog = ShiftDialog(self.week, day=self.day if day is None else day, start=self.week.settings.open_minute if start is None else start, group_id=group_id, educator_id=educator_id, parent=self)
        self._entity_dialog(dialog, "shifts", None)

    def new_activity(self, checked=False, *, day=None, start=None, group_id=""):
        if not self._can_edit():
            return
        if not self.week.groups or not self.week.rooms:
            QMessageBox.information(self, "Préparer une activité", "Ajoutez un groupe et un lieu (intérieur ou extérieur) avant de créer une activité.")
            return
        dialog = ActivityDialog(self.week, day=self.day if day is None else day, start=self.week.settings.open_minute if start is None else start, group_id=group_id, parent=self)
        self._entity_dialog(dialog, "activities", None)

    def calendar_create(self, day, start, group_id):
        self.new_shift(day=day, start=start, group_id=group_id)

    def educator_drop(self, educator_id, day, start, group_id):
        self.new_shift(day=day, start=start, group_id=group_id, educator_id=educator_id)

    def edit_block(self, kind, identifier):
        if not self._can_edit():
            return
        if kind == "shift":
            entity = next((value for value in self.week.shifts if value.id == identifier), None)
            if entity:
                self._entity_dialog(ShiftDialog(self.week, entity, parent=self), "shifts", entity)
        else:
            entity = next((value for value in self.week.activities if value.id == identifier), None)
            if entity:
                self._entity_dialog(ActivityDialog(self.week, entity, parent=self), "activities", entity)

    def change_block(self, kind, identifier, day, start, end, group_id):
        collection = "shifts" if kind == "shift" else "activities"
        def change(week):
            entities = getattr(week, collection)
            entity = next((value for value in entities if value.id == identifier), None)
            if not entity:
                raise ValueError("Ce bloc n'existe plus.")
            if kind == "shift" and entity.locked:
                raise ValueError("Déverrouillez ce quart dans sa fiche avant de le déplacer.")
            if not 0 <= start < end <= 1440:
                raise ValueError("Le bloc doit rester compris dans la journée.")
            if kind == "shift":
                if end - start == entity.end - entity.start:
                    replacement = move_shift(entity, day, start, group_id)
                    entities[entities.index(entity)] = replacement
                else:
                    if any(pause.start < start or pause.end > end for pause in entity.breaks):
                        raise ValueError("Une pause dépasserait le quart redimensionné. Ajustez-la dans la fiche du quart.")
                    if start + entity.buffer_before >= end - entity.buffer_after:
                        raise ValueError("Les buffers occupent toute la durée. Ajustez-les dans la fiche du quart.")
                    entity.day, entity.start, entity.end, entity.group_id = day, start, end, group_id
            else:
                entity.day, entity.start, entity.end, entity.group_id = day, start, end, group_id
        self.commit(change)

    def start_generation(self):
        if not self._can_edit():
            return
        if not self.week.educators or not self.week.groups:
            QMessageBox.information(self, "Générer l'horaire", "Ajoutez vos éducatrices et les périodes d'ouverture des groupes avant la génération.")
            return
        if self.dirty and not self.save_week(manual=False):
            return
        self.autosave.stop()
        self._worker = GenerationThread(self.week, self)
        self._progress = QProgressDialog("Recherche d'une proposition respectant les contraintes…", "", 0, 0, self)
        self._progress.setWindowTitle("Génération locale")
        self._progress.setCancelButton(None)
        self._progress.setWindowModality(Qt.WindowModality.WindowModal)
        self._progress.setMinimumDuration(0)
        self._progress.show()
        self._worker.completed.connect(self._generation_result)
        self._worker.failed.connect(self._generation_error)
        self._worker.finished.connect(self._generation_finished)
        self.refresh()
        self._worker.start()

    def _generation_error(self, message):
        if self._progress:
            self._progress.close()
        QMessageBox.warning(self, "Génération", message)

    def _generation_result(self, result):
        if self._progress:
            self._progress.close()
        if not result.success or result.proposal is None:
            details = "\n".join(result.diagnostics[:20])
            QMessageBox.information(self, "Aucune proposition appliquée", result.message + ("\n\n" + details if details else ""))
            return
        # The result waits for the worker to finish before it can be applied.
        self._pending_proposal = result

    def _generation_finished(self):
        worker = self._worker
        self._worker = None
        if worker:
            worker.deleteLater()
        if self._progress:
            self._progress.close()
            self._progress.deleteLater()
            self._progress = None
        self.refresh()
        result = getattr(self, "_pending_proposal", None)
        self._pending_proposal = None
        if result is None:
            if self.dirty:
                self.autosave.start()
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Vérifier la proposition avant de l'appliquer")
        dialog.resize(1160, 770)
        layout = QVBoxLayout(dialog)
        summary = note(result.message + "\nLes quarts verrouillés sont conservés. Fermez cette fenêtre pour garder votre horaire actuel.")
        layout.addWidget(summary)
        preview_controls = QHBoxLayout()
        preview_day = QComboBox()
        preview_day.addItems([result.proposal.day_label(day) for day in range(5)])
        preview_day.setCurrentIndex(self.day)
        preview_controls.addWidget(preview_day)
        calendar = CalendarWidget()
        preview_issues = validate(result.proposal)
        def open_proposal_day(day):
            calendar.set_week(result.proposal, day, preview_issues)
            calendar.set_mode("Jour")
        preview_day.activated.connect(open_proposal_day)
        calendar.day_selected.connect(open_proposal_day)
        preview_controls.addWidget(self._button("Jour", lambda: open_proposal_day(preview_day.currentIndex())))
        preview_controls.addWidget(self._button("Semaine", lambda: calendar.set_mode("Semaine")))
        preview_controls.addStretch()
        layout.addLayout(preview_controls)
        calendar.set_week(result.proposal, self.day, preview_issues)
        calendar.set_mode("Semaine")
        calendar.set_read_only(True)
        layout.addWidget(calendar, 1)
        totals_list = QListWidget()
        totals_list.addItems([f"{ed.name} : {format_duration(totals(result.proposal).get(ed.id, 0))}" for ed in result.proposal.educators if ed.active])
        totals_list.setMaximumHeight(120)
        layout.addWidget(totals_list)
        buttons = QDialogButtonBox()
        buttons.addButton("Conserver l'horaire actuel", QDialogButtonBox.ButtonRole.RejectRole)
        buttons.addButton("Appliquer cette proposition", QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.commit(lambda week: deepcopy(result.proposal))
        elif self.dirty:
            self.autosave.start()

    def choose_week(self):
        try:
            weeks = self.repo.list_weeks()
        except Exception as error:
            QMessageBox.warning(self, "Semaines", str(error))
            return
        if not weeks:
            QMessageBox.information(self, "Semaines", "Aucune autre semaine sauvegardée.")
            return
        labels = [f"{row['monday']} — {STATUS_LABELS.get(row['status'], row['status'])}" for row in weeks]
        choice, accepted = QInputDialog.getItem(self, "Consulter une semaine", "Semaines sauvegardées", labels, 0, False)
        if accepted:
            self.switch_week(date.fromisoformat(weeks[labels.index(choice)]["monday"]))

    def duplicate_week(self):
        if self._worker is not None or (self.dirty and not self.save_week()):
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Dupliquer la semaine")
        layout = QFormLayout(dialog)
        selected = QDateEdit(QDate.fromString(self.week.monday, "yyyy-MM-dd").addDays(7))
        selected.setCalendarPopup(True)
        selected.setDisplayFormat("dd MMMM yyyy")
        layout.addRow("Vers la semaine contenant le", selected)
        layout.addRow(note("Les quarts, activités et noms des journées sont copiés. Une semaine existante n'est jamais remplacée."))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Dupliquer")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Annuler")
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            day = selected.date().toPython()
            monday = (day - timedelta(days=day.weekday())).isoformat()
            try:
                self._load(self.repo.duplicate(self.week, monday))
            except Exception as error:
                QMessageBox.warning(self, "Duplication impossible", str(error))

    def show_history(self):
        if self._worker is not None or (self.dirty and not self.save_week()):
            return
        try:
            versions = self.repo.history(self.week.monday)
        except Exception as error:
            QMessageBox.warning(self, "Historique", str(error))
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Historique des versions")
        dialog.resize(650, 440)
        layout = QVBoxLayout(dialog)
        layout.addWidget(note("Chaque version conserve les profils, effectifs et paramètres utilisés. Restaurer crée un nouveau brouillon et préserve les versions antérieures."))
        listing = QListWidget()
        for version in versions:
            item = QListWidgetItem(f"Version {version['id']} · {STATUS_LABELS.get(version['status'], version['status'])} · {version['created_at'][:19].replace('T', ' ')} UTC")
            item.setData(Qt.ItemDataRole.UserRole, version["id"])
            listing.addItem(item)
        listing.setCurrentRow(0)
        layout.addWidget(listing)
        actions = QHBoxLayout()
        def chosen(restore=False):
            selected = listing.currentItem()
            if not selected:
                return
            identifier = selected.data(Qt.ItemDataRole.UserRole)
            if restore and QMessageBox.question(dialog, "Restaurer", "Restaurer cette version comme nouveau brouillon ? L'historique actuel sera conservé.") != QMessageBox.StandardButton.Yes:
                return
            try:
                self._load(self.repo.restore(identifier) if restore else self.repo.load_version(identifier), None if restore else identifier)
                dialog.accept()
            except Exception as error:
                QMessageBox.warning(dialog, "Historique", str(error))
        actions.addWidget(self._button("Consulter", lambda: chosen(False)))
        actions.addWidget(self._button("Restaurer en brouillon", lambda: chosen(True)))
        actions.addStretch()
        actions.addWidget(self._button("Fermer", dialog.reject))
        layout.addLayout(actions)
        layout.addWidget(self._button("Revenir à la version courante", lambda: (dialog.accept(), self.switch_week(date.fromisoformat(self.week.monday)))))
        dialog.exec()

    def backup(self):
        if self.dirty and not self.save_week():
            return
        destination, _ = QFileDialog.getSaveFileName(self, "Exporter une sauvegarde", f"{SHORT_NAME.replace(' ', '-')}-{date.today().isoformat()}.sqlite3", "Sauvegarde SQLite (*.sqlite3)")
        if destination:
            try:
                self.repo.backup(destination)
                self.statusBar().showMessage(f"Sauvegarde créée : {destination}", 10000)
            except Exception as error:
                QMessageBox.warning(self, "Sauvegarde", str(error))

    def import_backup(self):
        if self._worker is not None or (self.dirty and not self.save_week()):
            return
        source, _ = QFileDialog.getOpenFileName(self, "Importer une sauvegarde", "", "Sauvegarde SQLite (*.sqlite3 *.db)")
        if not source:
            return
        if QMessageBox.question(self, "Importer la sauvegarde", "Remplacer la base locale par cette sauvegarde ? Une copie de sécurité de la base actuelle sera conservée automatiquement.") != QMessageBox.StandardButton.Yes:
            return
        try:
            safety = self.repo.import_backup(source)
            week = self.repo.latest_week()
            if week is None:
                today = date.today()
                week = Week((today - timedelta(days=today.weekday())).isoformat())
            self._load(week)
            QMessageBox.information(self, "Importation terminée", f"Sauvegarde importée. La copie de sécurité précédente est conservée ici :\n{safety}")
        except Exception as error:
            QMessageBox.warning(self, "Importation impossible", str(error))

    def export_pdf(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Exporter les horaires en PDF")
        dialog.resize(520, 280)
        layout = QFormLayout(dialog)
        kind = QComboBox()
        for label, value in [("Horaire général", "general"), ("Tous les horaires dans un PDF regroupé", "combined"), ("Horaire d'une éducatrice", "individual"), ("Un PDF par éducatrice", "all")]:
            kind.addItem(label, value)
        educator = QComboBox()
        for person in self.week.educators:
            educator.addItem(person.name, person.id)
        educator.setEnabled(False)
        kind.currentIndexChanged.connect(lambda _: educator.setEnabled(kind.currentData() == "individual"))
        layout.addRow("Contenu", kind)
        layout.addRow("Éducatrice", educator)
        layout.addRow(note("Les noms des journées, heures exactes, pauses, buffers, activités et lieux sont conservés. Les PDF se lisent aussi en noir et blanc."))
        layout.addRow(self._button("Aperçu avant impression", lambda: self._preview_pdf(kind.currentData(), educator.currentData())))
        buttons = QDialogButtonBox()
        buttons.addButton("Annuler", QDialogButtonBox.ButtonRole.RejectRole)
        buttons.addButton("Exporter", QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        selected, identifier = kind.currentData(), educator.currentData()
        if selected == "individual" and not identifier:
            QMessageBox.information(self, "Export PDF", "Ajoutez une éducatrice avant d'exporter son horaire.")
            return
        if selected == "all":
            destination = QFileDialog.getExistingDirectory(self, "Dossier pour les horaires individuels")
        else:
            destination, _ = QFileDialog.getSaveFileName(self, "Exporter PDF", f"Horaire-{self.week.monday}.pdf", "PDF (*.pdf)")
        if not destination:
            return
        try:
            if selected == "general":
                export_general(self.week, destination)
            elif selected == "individual":
                export_individual(self.week, identifier, destination)
            elif selected == "combined":
                export_combined(self.week, destination)
            else:
                export_all_individual(self.week, destination)
            self.statusBar().showMessage(f"PDF exporté : {destination}", 10000)
        except Exception as error:
            QMessageBox.warning(self, "Export impossible", str(error))

    def _preview_pdf(self, kind, identifier):
        if kind == "individual" and not identifier:
            QMessageBox.information(self, "Aperçu", "Choisissez une éducatrice.")
            return
        try:
            from PySide6.QtPdf import QPdfDocument
            from PySide6.QtPdfWidgets import QPdfView
            from PySide6.QtPrintSupport import QPrintPreviewDialog, QPrinter
            with tempfile.TemporaryDirectory(prefix="gardeplan-apercu-") as directory:
                path = Path(directory) / "apercu.pdf"
                if kind == "general":
                    export_general(self.week, path)
                elif kind == "individual":
                    export_individual(self.week, identifier, path)
                else:
                    export_combined(self.week, path)
                dialog = QDialog(self)
                dialog.setWindowTitle("Aperçu PDF")
                dialog.resize(1000, 800)
                layout = QVBoxLayout(dialog)
                document = QPdfDocument(dialog)
                document.load(str(path))
                view = QPdfView(dialog)
                view.setDocument(document)
                view.setPageMode(QPdfView.PageMode.MultiPage)
                view.setZoomMode(QPdfView.ZoomMode.FitInView)
                layout.addWidget(view, 1)
                def print_preview():
                    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
                    preview = QPrintPreviewDialog(printer, dialog)
                    def paint(device):
                        painter = QPainter(device)
                        rect = device.pageLayout().paintRectPixels(device.resolution())
                        for page in range(document.pageCount()):
                            if page:
                                device.newPage()
                            size = document.pagePointSize(page)
                            # Render at a useful print resolution without huge raster allocations.
                            image = document.render(page, QSize(int(size.width() * 2), int(size.height() * 2)))
                            target = image.size().scaled(rect.size(), Qt.AspectRatioMode.KeepAspectRatio)
                            painter.drawImage(rect.x(), rect.y(), image.scaled(target, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                        painter.end()
                    preview.paintRequested.connect(paint)
                    preview.exec()
                actions = QHBoxLayout()
                actions.addWidget(self._button("Imprimer…", print_preview))
                actions.addStretch()
                actions.addWidget(self._button("Fermer", dialog.accept))
                layout.addLayout(actions)
                dialog.exec()
                document.close()
        except Exception as error:
            QMessageBox.warning(self, "Aperçu indisponible", str(error))

    def closeEvent(self, event):
        if self._worker is not None:
            QMessageBox.information(self, "Génération en cours", "La recherche se termine dans quelques instants. Attendez la proposition avant de fermer l'application.")
            event.ignore()
            return
        if self.dirty and not self.save_week():
            event.ignore()
            return
        self.autosave.stop()
        try:
            if self._history_version is None:
                backup_dir = Path(self.repo.path).parent / "sauvegardes"
                self.repo.backup(backup_dir / f"securite-{date.today().isoformat()}.sqlite3")
        except Exception as error:
            response = QMessageBox.question(self, "Copie de sécurité", f"L'horaire est sauvegardé, mais la copie de sécurité n'a pas pu être créée :\n{error}\n\nFermer quand même ?")
            if response != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
        event.accept()
