"""Tableau de bord local : orchestration des éditeurs et des services métier."""
from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path
import tempfile
import unicodedata

from PySide6.QtCore import Qt, QDate, QMimeData, QThread, QTimer, Signal, QSize
from PySide6.QtGui import QAction, QColor, QDrag, QKeySequence, QPainter
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDateEdit, QDialog,
    QDialogButtonBox, QFileDialog, QFormLayout, QFrame, QHBoxLayout,
    QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow,
    QMenu, QMessageBox, QProgressBar, QProgressDialog, QPushButton,
    QSlider, QSpinBox, QSplitter, QStackedWidget, QScrollArea, QVBoxLayout, QWidget,
)

from ..branding import DISPLAY_NAME, SHORT_NAME
from ..models import (
    Week, Shift, Activity, Group, STATUS_LABELS, DAYS, new_id, totals,
    format_duration, format_time, move_shift,
)
from ..daily import day_plan
from ..validation import validate
from ..alerts import alert_text, visible_alerts
from ..coverage import day_summary
from ..hours import educator_hour_state
from ..optimizer import generate
from ..pdf import export_general, export_individual, export_combined, export_all_individual
from .calendar import CalendarWidget, EDUCATOR_MIME
from .day_selector import full_date
from .date_field import DateField
from .flow_layout import FlowLayout
from .theme import DATE_STYLE
from .inline_name import InlineDayName
from .enrolment import EnrolmentPanel
from .visuals import icon, logo_icon, logo_pixmap
from .forms import EducatorDialog, GroupDialog, RoomDialog, ShiftDialog, ActivityDialog, SettingsDialog, integer, note


class EducatorList(QListWidget):
    create_shift = Signal(str)
    def __init__(self):
        super().__init__()
        self.setDragEnabled(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setSpacing(8)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet("QListWidget {background:transparent;} QListWidget::item:selected {background:#e3eee8;border-radius:8px;}")
        self.setAccessibleName("Éducatrices à glisser dans le calendrier")
        self.setAccessibleDescription("Glisser un nom ou appuyer sur Entrée pour créer son quart.")

    def keyPressEvent(self, event):
        item = self.currentItem()
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and item and item.data(Qt.ItemDataRole.UserRole + 1):
            self.create_shift.emit(item.data(Qt.ItemDataRole.UserRole))
            return
        super().keyPressEvent(event)

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
        if self.snapshot.planning_date:
            self.snapshot.settings.staffing_policy = 2

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
        self.setWindowIcon(logo_icon())
        self.resize(1480, 940)
        self.setMinimumSize(640, 480)
        self._auto_hidden_sidebar = False
        self._sidebar_manual_hidden = False
        self._build_ui()
        self._upgrade_working_rules()
        self.refresh()
        QTimer.singleShot(0, self.fit_day)

    @property
    def read_only(self):
        return self.week.status == "archived" or self._history_version is not None or self._worker is not None

    def _button(self, text, slot, tooltip="", primary=False, icon_name=None):
        button = QPushButton(text)
        button.clicked.connect(slot)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        if tooltip:
            button.setToolTip(tooltip)
            button.setAccessibleName(tooltip)
        if icon_name:
            button.setIcon(icon(icon_name, color="#FFFFFF" if primary else "#567266"))
            button.setIconSize(QSize(18, 18))
        if primary:
            button.setObjectName("primary")
        elif not text:
            button.setObjectName("iconButton")
            button.setFixedSize(36, 36)
        return button

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("workspace")
        self.setCentralWidget(central)
        shell = QHBoxLayout(central)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)
        rail = QFrame()
        rail.setObjectName("navigationRail")
        self.navigation_rail = rail
        rail.setFixedWidth(72)
        rail_layout = QVBoxLayout(rail)
        self.rail_layout = rail_layout
        rail_layout.setContentsMargins(10, 28, 10, 20)
        rail_layout.setSpacing(18)
        mark = QLabel()
        mark.setPixmap(logo_pixmap(38))
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rail_layout.addWidget(mark)
        rail_layout.addSpacing(12)
        self.rail_buttons = {}
        for name, tip, callback in (
                ("calendar", "Planification de la journée", lambda: self.calendar.setFocus()),
                ("users", "Afficher l’équipe", lambda: self.show_management("team"))):
            button = self._button("", callback, tip)
            button.setObjectName("railButton")
            button.setProperty("active", name == "calendar")
            button.setIcon(icon(name, color="#D5E3DD"))
            button.setIconSize(QSize(22, 22))
            button.setFixedSize(50, 50)
            rail_layout.addWidget(button)
            self.rail_buttons[name] = button
        self.folder_button = self._button("", lambda: None,
            "Dossier : enregistrer, ouvrir et sauvegarder les horaires", icon_name="folder")
        self.folder_button.setObjectName("railButton")
        self.folder_button.setIcon(icon("folder", color="#D5E3DD"))
        self.folder_button.setIconSize(QSize(22, 22))
        self.folder_button.setFixedSize(50, 50)
        rail_layout.addWidget(self.folder_button)
        rail_layout.addStretch()
        shell.addWidget(rail)
        content = QWidget()
        shell.addWidget(content, 1)
        root = QVBoxLayout(content)
        self.workspace_layout = root
        root.setContentsMargins(28, 20, 28, 10)
        root.setSpacing(14)
        # Less frequent controls keep their original connections and live here
        # until an options dialog needs them. They never create extra windows.
        self._hidden_controls = QWidget(central)
        self._hidden_controls.hide()
        self.top_controls = QWidget()
        heading = QHBoxLayout(self.top_controls)
        heading.setContentsMargins(0, 0, 0, 0)
        heading.setSpacing(12)
        brand_column = QVBoxLayout()
        brand_column.setSpacing(5)
        subtitle = QLabel("SERVICE DE GARDE")
        self.brand_subtitle = subtitle
        subtitle.setObjectName("brandSubtitle")
        brand_column.addWidget(subtitle)
        brand = QLabel("Planification")
        self.brand_label = brand
        brand.setObjectName("brandTitle")
        brand_column.addWidget(brand)
        heading.addLayout(brand_column)
        heading.addStretch()
        self.save_label = QLabel("Enregistré")
        self.save_label.setObjectName("saveStatus")
        self.save_label.setMinimumWidth(0)
        self.save_label.setMaximumWidth(440)
        self.save_label.setWordWrap(True)
        heading.addWidget(self.save_label)
        root.addWidget(self.top_controls)
        date_row = FlowLayout(push_last=2)
        date_row.setSpacing(12)
        week_navigation = QFrame()
        week_navigation.setObjectName("weekNavigation")
        navigation = QHBoxLayout(week_navigation)
        self.date_navigation_layout = navigation
        navigation.setContentsMargins(4, 3, 4, 3)
        navigation.setSpacing(2)
        self.previous_day_button = self._button("", lambda: self.navigate_day(-1), "Journée précédente", icon_name="chevron-left")
        navigation.addWidget(self.previous_day_button)
        self.week_date = DateField()
        self.week_date.dateChanged.connect(self._date_changed)
        navigation.addWidget(self.week_date)
        self.next_day_button = self._button("", lambda: self.navigate_day(1), "Journée suivante", icon_name="chevron-right")
        navigation.addWidget(self.next_day_button)
        for arrow in (self.previous_day_button, self.next_day_button):
            arrow.setObjectName("dateArrow")
            arrow.setIconSize(QSize(24, 24))
            arrow.setFixedSize(48, 48)
            arrow.setStyleSheet(DATE_STYLE)
        date_row.addWidget(week_navigation)
        self.generate_button = self._button("Générer l’horaire", self.start_generation, "Générer automatiquement une proposition d'horaire", primary=True, icon_name="sparkles")
        self.export_button = self._button("Exporter PDF", self.export_pdf, "Exporter ou imprimer les horaires en PDF", icon_name="download")
        for action_button in (self.export_button, self.generate_button):
            action_button.setStyleSheet("font-size:16px;min-height:30px;padding:8px 14px;")
            action_button.setMinimumHeight(48)
            date_row.addWidget(action_button)
        self.more_button = self._button("", lambda: None, "Menu : réglages, historique et sauvegardes", icon_name="settings")
        self.more_button.setObjectName("railButton")
        self.more_button.setIcon(icon("settings", color="#D5E3DD"))
        self.more_button.setFixedSize(50, 50)
        rail_layout.addWidget(self.more_button)
        root.addLayout(date_row)

        self.status_combo = QComboBox(self._hidden_controls)
        for value, label in STATUS_LABELS.items():
            self.status_combo.addItem(label, value)
        self.status_combo.activated.connect(self._status_selected)
        self.save_button = self._button("Sauvegarder", lambda: self.save_week(manual=True))
        self.undo_button = self._button("Annuler", self.undo)
        self.redo_button = self._button("Rétablir", self.redo)
        self.sidebar_toggle = self._button("Éducatrices", self.toggle_sidebar)
        self.name_day_button = self._button("Nommer la journée", self.name_day)
        self.groups_button = self._button("Groupes", lambda: self.manage_entities("groups"))
        self.rooms_button = self._button("Locaux", lambda: self.manage_entities("rooms"))
        self.settings_button = self._button("Règles de planification", self.edit_settings)
        self.add_shift_button = self._button("Quart", self.new_shift)
        self.add_activity_button = self._button("Activité", self.new_activity)
        self.edit_educator_button = self._button("Modifier le profil", self.edit_selected_educator)
        for widget in (self.save_button, self.undo_button, self.redo_button, self.sidebar_toggle,
                       self.name_day_button, self.groups_button, self.rooms_button,
                       self.settings_button, self.add_shift_button, self.add_activity_button,
                       self.edit_educator_button):
            widget.setParent(self._hidden_controls)
        self.show_inactive = QCheckBox("Afficher les profils inactifs", self._hidden_controls)
        self.show_inactive.toggled.connect(self.refresh_educators)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(16)
        self.splitter.setChildrenCollapsible(False)
        root.addWidget(self.splitter, 1)
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setMinimumWidth(250)
        side_outer = QVBoxLayout(self.sidebar)
        side_outer.setContentsMargins(0,0,0,0)
        self.management_stack = QStackedWidget()
        side_outer.addWidget(self.management_stack)
        self.team_page = QWidget()
        self.management_stack.addWidget(self.team_page)
        sidebar = QVBoxLayout(self.team_page)
        sidebar.setContentsMargins(0, 0, 5, 0)
        sidebar.setSpacing(10)
        side_head = QHBoxLayout()
        title = QLabel("L'équipe")
        title.setObjectName("sectionTitle")
        side_head.addWidget(title)
        help_text = "Glissez une éducatrice sur la grille ou double-cliquez sur une plage vide pour créer un quart. Au clavier, sélectionnez un nom et appuyez sur Entrée."
        self.planning_help = self._button("ⓘ", lambda: QMessageBox.information(self, "Créer un quart", help_text), help_text)
        self.planning_help.setObjectName("subtleButton")
        self.planning_help.setFixedSize(32,32)
        self.planning_help.setAccessibleName("Aide pour créer un quart")
        self.planning_help.setAccessibleDescription(help_text)
        side_head.addWidget(self.planning_help)
        side_head.addStretch()
        self.add_educator_button = self._button("", lambda: self.edit_educator(), "Ajouter une éducatrice", icon_name="plus")
        self.add_educator_button.setObjectName("subtleButton")
        side_head.addWidget(self.add_educator_button)
        sidebar.addLayout(side_head)
        self.team_summary = QLabel()
        self.team_summary.setObjectName("muted")
        sidebar.addWidget(self.team_summary)
        self.educator_search = QLineEdit()
        self.educator_search.setObjectName("educatorSearch")
        self.educator_search.setPlaceholderText("Rechercher une éducatrice…")
        self.educator_search.setClearButtonEnabled(True)
        self.educator_search.addAction(icon("search", size=16), QLineEdit.ActionPosition.LeadingPosition)
        self.educator_search.textChanged.connect(self.refresh_educators)
        sidebar.addWidget(self.educator_search)
        self.educator_list = EducatorList()
        self.educator_list.setObjectName("educatorList")
        self.educator_list.itemDoubleClicked.connect(lambda item: self.edit_educator(item.data(Qt.ItemDataRole.UserRole)))
        self.educator_list.itemSelectionChanged.connect(self._refresh_profile_button)
        self.educator_list.create_shift.connect(lambda identifier: self.new_shift(educator_id=identifier, group_id=self.week.groups[0].id if self.week.groups else ""))
        sidebar.addWidget(self.educator_list, 1)
        self.splitter.addWidget(self.sidebar)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)
        self.schedule_panes = QSplitter(Qt.Orientation.Horizontal)
        self.schedule_panes.setChildrenCollapsible(False)
        self.schedule_panes.setHandleWidth(8)
        right_layout.addWidget(self.schedule_panes,1)
        calendar_surface = QFrame()
        calendar_surface.setObjectName("calendarSurface")
        surface = QVBoxLayout(calendar_surface)
        surface.setContentsMargins(0, 0, 0, 0)
        surface.setSpacing(0)
        day_controls = QWidget()
        day_controls.setObjectName("calendarToolbar")
        day_row = QHBoxLayout(day_controls)
        self.day_controls_layout = day_row
        day_row.setContentsMargins(12, 6, 12, 6)
        day_row.setSpacing(8)
        self.day_combo = QComboBox(self._hidden_controls)
        self.day_combo.setObjectName("daySelector")
        self.day_combo.setMinimumWidth(170)
        self.day_combo.activated.connect(self.select_day)
        self.day_title = InlineDayName()
        self.day_title.setObjectName("dayTitle")
        self.day_title.changed.connect(self._rename_day)
        day_row.addWidget(self.day_title,1)
        day_row.addStretch()
        self.calendar_summary = QLabel()
        self.calendar_summary.setObjectName("muted")
        self.calendar_summary.setWordWrap(True)
        self.calendar_summary.setContentsMargins(14, 2, 14, 10)
        self.enrolment_button = self._button("", self.enrolment, "Inscriptions de la journée", icon_name="clipboard")
        self.enrolment_button.setObjectName("railButton")
        self.enrolment_button.setIcon(icon("clipboard", color="#D5E3DD"))
        self.enrolment_button.setIconSize(QSize(22,22))
        self.enrolment_button.setFixedSize(50,50)
        rail_layout.insertWidget(rail_layout.count()-2,self.enrolment_button)
        segmented = QFrame()
        segmented.setObjectName("segmentedControl")
        modes = QHBoxLayout(segmented)
        modes.setContentsMargins(3, 3, 3, 3)
        modes.setSpacing(1)
        self.day_mode = self._button("Jour", lambda: self.set_mode("Jour"))
        self.week_mode = self._button("Semaine", lambda: self.set_mode("Semaine"))
        for button in (self.day_mode, self.week_mode):
            button.setObjectName("segment")
            button.setCheckable(True)
            modes.addWidget(button)
        self.day_mode.setChecked(True)
        segmented.setParent(self._hidden_controls)
        self.add_button = self._button("Ajouter un quart", self.new_shift, "Ajouter un quart de travail", icon_name="plus")
        self.add_button.setObjectName("menuButton")
        self.add_menu = QMenu(self)
        self.add_button.setParent(self._hidden_controls)
        self.top_alert_button = self._button("Vérifier l'horaire", self.verify, "Vérifier la couverture, les relèves et les heures", icon_name="check")
        self.top_alert_button.setObjectName("subtleButton")
        self.verify_button = self.top_alert_button
        self.coverage_toggle = self._button("− Ratio", lambda: None,
            "Masquer la bande de ratio. Elle n’est jamais incluse dans le PDF.")
        self.coverage_toggle.setObjectName("subtleButton")
        self.coverage_toggle.setStyleSheet("font-size:16px;")
        self.coverage_toggle.setMinimumHeight(44)
        self.coverage_toggle.setCheckable(True)
        self.coverage_toggle.setChecked(True)
        self.coverage_toggle.setAccessibleName("Masquer la bande de ratio")
        self.coverage_toggle.setProperty("active", True)
        self.coverage_toggle.toggled.connect(self.toggle_coverage)
        for control, symbol in ((self.coverage_toggle, "panel"), (self.top_alert_button, "check")):
            control.setText("")
            control.setObjectName("railButton")
            control.setStyleSheet("")
            control.setIcon(icon(symbol, color="#D5E3DD"))
            control.setIconSize(QSize(22,22))
            control.setFixedSize(50,50)
            rail_layout.insertWidget(rail_layout.count()-2,control)
        self.alert_badge = QLabel("0", self.top_alert_button)
        self.alert_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.alert_badge.setFixedSize(24,20)
        self.alert_badge.move(26,0)
        self.alert_badge.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.alert_badge.setStyleSheet("background:#982D24;color:white;border-radius:9px;font-size:12px;font-weight:700;")
        for button, name in ((self.undo_button, "undo"), (self.redo_button, "redo")):
            button.setObjectName("subtleButton")
            button.setIcon(icon(name))
            button.setMinimumHeight(44)
            button.setMinimumWidth(44)
            button.setAccessibleName("Annuler" if name == "undo" else "Rétablir")
            button.setToolTip("Annuler" if name == "undo" else "Rétablir")
            button.setStyleSheet("font-size:16px;")
            day_row.addWidget(button)
            button.show()
        surface.addWidget(day_controls)
        self.version_banner = QLabel()
        self.version_banner.setObjectName("versionBanner")
        self.version_banner.setWordWrap(True)
        surface.addWidget(self.version_banner)
        self.calendar = CalendarWidget()
        self.calendar.single_service = True
        self.calendar.grouped_staff = True
        self.calendar.set_summary_widget(self.calendar_summary)
        self.calendar.show_activities = False
        self.calendar.canvas.setAccessibleName("Calendrier des horaires")
        self.calendar.edit_requested.connect(self.edit_block)
        self.calendar.change_requested.connect(self.change_block)
        self.calendar.educator_dropped.connect(self.educator_drop)
        self.calendar.day_selected.connect(self.expand_day)
        self.calendar.create_requested.connect(self.calendar_create)
        self.calendar.staff_create_requested.connect(lambda day,start,group,person: self.new_shift(day=day,start=start,group_id=group,educator_id=person))
        surface.addWidget(self.calendar, 1)
        self.schedule_panes.addWidget(calendar_surface)
        self.schedule_panes.setStretchFactor(0,1)

        self.snap_combo = QComboBox(self._hidden_controls)
        for label, value in [("Libre · minute", 0), ("1 min", 1), ("5 min", 5), ("15 min", 15)]:
            self.snap_combo.addItem(label, value)
        self.snap_combo.activated.connect(self._snap_changed)
        self.zoom = QSlider(Qt.Orientation.Horizontal, self._hidden_controls)
        self.zoom.setRange(15, 200)
        self.zoom.setValue(100)
        self.zoom.valueChanged.connect(lambda value: self.calendar.set_zoom(value / 100))
        self.full_day_button = self._button("Afficher la journée entière", self.fit_day, icon_name="clock")
        self.full_day_button.setParent(self._hidden_controls)
        self.alert_toggle = self._button("Afficher les alertes", self.toggle_alerts)
        self.alert_toggle.setParent(self._hidden_controls)
        self.alert_toggle.setCheckable(True)
        self.alert_toggle.setChecked(False)
        self.alert_panel = QFrame()
        self.alert_panel.setObjectName("alertPanel")
        alert_layout = QVBoxLayout(self.alert_panel)
        alert_layout.setContentsMargins(14, 10, 14, 10)
        alert_layout.setSpacing(6)
        alert_heading = QHBoxLayout()
        self.alert_heading_label = QLabel("Points à vérifier")
        self.alert_heading_label.setObjectName("alertTitle")
        self.alert_heading_label.setStyleSheet("font-size:16px;font-weight:600;")
        alert_heading.addWidget(self.alert_heading_label)
        alert_heading.addStretch()
        self.close_alerts_button = self._button("Fermer", self.close_alerts, "Fermer les détails des alertes")
        self.close_alerts_button.setObjectName("subtleButton")
        alert_heading.addWidget(self.close_alerts_button)
        alert_layout.addLayout(alert_heading)
        self.alert_list = QListWidget()
        self.alert_list.setObjectName("alertList")
        self.alert_list.setMaximumHeight(16777215)
        self.alert_list.setMinimumHeight(54)
        self.alert_list.setWordWrap(True)
        self.alert_list.setStyleSheet("font-size:14px;")
        self.alert_list.itemClicked.connect(self.navigate_issue)
        self.alert_list.itemActivated.connect(self.navigate_issue)
        alert_layout.addWidget(self.alert_list)
        self.alert_panel.setMinimumWidth(220)
        self.alert_panel.setMaximumWidth(320)
        self.management_stack.addWidget(self.alert_panel)
        self.enrolment_panel = EnrolmentPanel(self.week)
        self.enrolment_panel.accepted.connect(self.apply_enrolment)
        self.enrolment_panel.rejected.connect(lambda: self.show_management("team"))
        self.enrolment_page = QScrollArea()
        self.enrolment_page.setWidgetResizable(True)
        self.enrolment_page.setFrameShape(QFrame.Shape.NoFrame)
        self.enrolment_page.setMinimumSize(0,0)
        self.enrolment_page.setWidget(self.enrolment_panel)
        self.management_stack.addWidget(self.enrolment_page)
        self.management_stack.setCurrentWidget(self.team_page)
        self.splitter.addWidget(right)
        self.splitter.setSizes([265, 1100])

        self.week_status_label = QLabel(self._hidden_controls)
        self.week_status_label.setObjectName("muted")
        self.statusBar().hide()
        self.statusBar().messageChanged.connect(lambda message: self.statusBar().setVisible(bool(message)))
        rail_layout.removeWidget(self.folder_button)
        rail_layout.insertWidget(rail_layout.indexOf(self.more_button),self.folder_button)
        self._build_command_menus()

    def _add_menu_action(self, menu, key, text, callback, shortcut=None):
        action = menu.addAction(text)
        action.triggered.connect(lambda checked=False: callback())
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
            self.addAction(action)
        self.menu_actions[key] = action
        return action

    def _build_command_menus(self):
        self.command_menu = QMenu(self)
        self.more_button.setMenu(self.command_menu)
        self.menu_actions = {}
        add = self._add_menu_action
        add(self.add_menu, "add_shift", "Quart de travail…", lambda: self.new_shift())
        self.file_menu = QMenu(self)
        self.file_menu.setStyleSheet("QMenu {background:white;color:#203D32;font-size:16px;} QMenu::item {padding:12px 16px;} QMenu::item:selected {background:#DFEBE4;color:#203D32;}")
        self.folder_button.setMenu(self.file_menu)
        add(self.file_menu, "save", "Enregistrer l’horaire", lambda: self.save_week(manual=True), "Ctrl+S")
        undo = add(self.command_menu, "undo", "Annuler", lambda: self.undo(), "Ctrl+Z")
        undo.setShortcuts(QKeySequence.keyBindings(QKeySequence.StandardKey.Undo))
        redo = add(self.command_menu, "redo", "Rétablir", lambda: self.redo())
        keys = QKeySequence.keyBindings(QKeySequence.StandardKey.Redo) + [QKeySequence("Ctrl+Shift+Z"), QKeySequence("Ctrl+Y")]
        redo.setShortcuts(list({key.toString(): key for key in keys}.values()))
        self.addAction(redo)
        add(self.command_menu, "pdf_preview", "Aperçu avant impression…", lambda: self._preview_pdf("general", None))
        self.command_menu.addSeparator()
        day_menu = self.command_menu.addMenu("Journée")
        add(day_menu, "name_day", "Nommer la journée…", lambda: self.name_day())
        add(day_menu, "enrolment", "Inscriptions…", lambda: self.enrolment())
        organisation = self.command_menu.addMenu("Organisation")
        add(organisation, "add_educator", "Ajouter une éducatrice…", lambda: self.edit_educator())
        add(organisation, "edit_educator", "Modifier le profil sélectionné…", lambda: self.edit_selected_educator())
        inactive = add(organisation, "inactive", "Afficher les profils inactifs", lambda: self.show_inactive.setChecked(not self.show_inactive.isChecked()))
        inactive.setCheckable(True)
        organisation.addSeparator()
        add(organisation, "groups", "Groupes des affectations…", lambda: self.manage_entities("groups"))
        add(organisation, "settings", "Règles de planification…", lambda: self.edit_settings())
        status_menu = self.command_menu.addMenu("Statut de la journée")
        status_commands = {"draft": "Conserver en brouillon", "validated": "Valider l'horaire", "published": "Publier l'horaire", "archived": "Archiver la journée"}
        for status, label in status_commands.items():
            action = add(status_menu, "status_" + status, label, lambda value=status: self._status_selected(self.status_combo.findData(value)))
            action.setCheckable(True)
        self.file_menu.addSeparator()
        week_menu = self.file_menu
        add(week_menu, "choose_week", "Ouvrir une journée…", lambda: self.choose_week(), "Ctrl+O")
        add(week_menu, "duplicate", "Dupliquer cette journée…", lambda: self.duplicate_week())
        add(week_menu, "history", "Historique des versions…", lambda: self.show_history())
        self.file_menu.addSeparator()
        backups = self.file_menu
        add(backups, "backup", "Exporter une sauvegarde…", lambda: self.backup())
        add(backups, "import", "Importer une sauvegarde…", lambda: self.import_backup())
        self.command_menu.addSeparator()
        add(self.command_menu, "display", "Affichage…", lambda: self.show_display_options())
        self.command_menu.aboutToShow.connect(self._sync_menu_actions)
        self.add_menu.aboutToShow.connect(self._sync_menu_actions)
        self.file_menu.aboutToShow.connect(self._sync_menu_actions)

    def _sync_menu_actions(self):
        if not hasattr(self, "menu_actions"):
            return
        enabled = {
            "save": self.save_button.isEnabled(), "undo": self.undo_button.isEnabled(),
            "redo": self.redo_button.isEnabled(), "add_shift": not self.read_only,
            "name_day": not self.read_only,
            "enrolment": not self.read_only, "add_educator": not self.read_only,
            "edit_educator": self.edit_educator_button.isEnabled(),
            "settings": not self.read_only,
            "choose_week": self._worker is None,
            "duplicate": self._worker is None,
            "history": self._worker is None,
            "backup": self._worker is None,
            "import": self._worker is None,
        }
        for key, value in enabled.items():
            self.menu_actions[key].setEnabled(value)
        for status in STATUS_LABELS:
            action = self.menu_actions["status_" + status]
            action.setEnabled(not self.read_only)
            action.setChecked(status == self.week.status)
        self.menu_actions["inactive"].setChecked(self.show_inactive.isChecked())

    def show_display_options(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Affichage du calendrier")
        dialog.setObjectName("displayOptions")
        dialog.setMinimumWidth(390)
        layout = QFormLayout(dialog)
        layout.addRow("Magnétisme", self.snap_combo)
        layout.addRow("Zoom vertical", self.zoom)
        layout.addRow(self.full_day_button)
        sidebar = QCheckBox("Afficher le panneau des éducatrices")
        sidebar.setChecked(not self.sidebar.isHidden())
        sidebar.toggled.connect(self.sidebar.setVisible)
        layout.addRow(sidebar)
        layout.addRow(note("Les heures restent exactes à la minute, quel que soit le zoom. Le magnétisme aide uniquement au déplacement des blocs."))
        layout.addRow(note("Au clavier dans la grille : gauche/droite sélectionne un quart, haut/bas le déplace, Maj + haut/bas ajuste la fin et Alt + haut/bas ajuste le début. Entrée ouvre les heures exactes."))
        buttons = QDialogButtonBox()
        buttons.addButton("Fermer", QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.accepted.connect(dialog.accept)
        layout.addRow(buttons)
        for widget in (self.snap_combo, self.zoom, self.full_day_button):
            widget.show()
        try:
            dialog.exec()
        finally:
            for widget in (self.snap_combo, self.zoom, self.full_day_button):
                widget.setParent(self._hidden_controls)
            dialog.deleteLater()

    def close_alerts(self):
        self.statusBar().clearMessage()
        self.alert_toggle.setChecked(False)
        self.show_management("team")

    def refresh(self):
        self._updating = True
        self.issues = validate(self.week)
        self.week_date.setDate(QDate.fromString(self.week.planning_date or self.week.monday, "yyyy-MM-dd"))
        self.status_combo.setCurrentIndex(max(0, self.status_combo.findData(self.week.status)))
        self.status_combo.setProperty("status", self.week.status)
        self.status_combo.style().unpolish(self.status_combo)
        self.status_combo.style().polish(self.status_combo)
        self.day_combo.clear()
        self.day_combo.addItems([self.week.day_label(day) for day in self.week.active_days])
        full_title = self.week.day_names.get(self.day) or "Journée pédagogique"
        self.day_title.setText(self.week.day_names.get(self.day, ""))
        self.day_title.setEnabled(not self.read_only)
        self.day_title.setToolTip(full_title)
        summary, complete = day_summary(self.week, self.day)
        self._day_summary = summary
        self.calendar_summary.setText(("" if self.width() < 1000 else "Horaires des éducatrices · ")+summary)
        self.calendar_summary.setStyleSheet(f"font-size:14px;color:{'#214F40' if complete else '#952E28'};")
        self.day_combo.setCurrentIndex(self.day)
        self.snap_combo.setCurrentIndex(max(0, self.snap_combo.findData(self.week.settings.snap_minutes)))
        self.calendar.set_snap(self.week.settings.snap_minutes)
        self.calendar.set_week(self.week, self.day, self.issues)
        self.calendar.set_read_only(self.read_only)
        for control in (self.week_date, self.previous_day_button, self.next_day_button):
            control.setEnabled(self._worker is None)
        self.previous_day_button.setEnabled(self._worker is None and self.week_date.date() > self.week_date.minimumDate())
        self.next_day_button.setEnabled(self._worker is None and self.week_date.date() < self.week_date.maximumDate())
        self.refresh_educators()
        self.refresh_alerts()
        self.undo_button.setEnabled(bool(self._undo) and not self.read_only)
        self.redo_button.setEnabled(bool(self._redo) and not self.read_only)
        for widget in (self.generate_button, self.add_educator_button, self.add_shift_button, self.add_activity_button, self.name_day_button, self.settings_button):
            widget.setEnabled(not self.read_only)
        self.status_combo.setEnabled(not self.read_only)
        self.save_button.setEnabled(self._history_version is None and self._worker is None)
        self.snap_combo.setEnabled(not self.read_only)
        banner = ""
        if self._history_version is not None:
            banner = f"Version {self._history_version} en consultation. L'historique permet de la restaurer comme nouveau brouillon."
        elif self.week.status == "archived":
            banner = "Journée archivée : consultation uniquement. Dupliquez-la ou restaurez une version pour la modifier."
        elif self.week.status == "published":
            banner = "Version publiée conservée dans l'historique. Toute modification créera un nouveau brouillon."
        self.version_banner.setText(banner)
        self.version_banner.setVisible(bool(banner))
        if getattr(self,"_enrolment_key",None) != self.week.storage_key:
            self.enrolment_panel.load_week(self.week)
            self._enrolment_key = self.week.storage_key
        self.enrolment_panel.save_button.setEnabled(not self.read_only)
        self.add_button.setEnabled(not self.read_only)
        self._sync_menu_actions()
        self._updating = False

    @staticmethod
    def _search_key(text):
        return "".join(character for character in unicodedata.normalize("NFKD", text)
                       if not unicodedata.combining(character)).casefold()

    def _refresh_profile_button(self):
        current = self.educator_list.currentItem()
        self.edit_educator_button.setEnabled(bool(current and current.data(Qt.ItemDataRole.UserRole)) and not self.read_only)
        self._sync_menu_actions()

    def edit_selected_educator(self):
        current = self.educator_list.currentItem()
        if current and current.data(Qt.ItemDataRole.UserRole):
            self.edit_educator(current.data(Qt.ItemDataRole.UserRole))

    def refresh_educators(self):
        selected = self.educator_list.currentItem()
        selected_id = selected.data(Qt.ItemDataRole.UserRole) if selected else None
        self.educator_list.clear()
        planned = totals(self.week)
        active_count = sum(educator.active for educator in self.week.educators)
        self.team_summary.setText(f"{active_count} éducatrice{'s' if active_count != 1 else ''} active{'s' if active_count != 1 else ''} · {format_duration(sum(planned.values()))} planifiées")
        query = self._search_key(self.educator_search.text().strip())
        for educator in sorted(self.week.educators, key=lambda item: (not item.active, item.seniority, item.name)):
            if not educator.active and not self.show_inactive.isChecked():
                continue
            if query and query not in self._search_key(educator.name):
                continue
            minutes = planned.get(educator.id, 0)
            hour_status = educator_hour_state(self.week, educator)
            remaining = educator.target_minutes - minutes
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, educator.id)
            item.setData(Qt.ItemDataRole.UserRole + 1, educator.active and not self.read_only)
            item.setSizeHint(QSize(0, 134 if hour_status.code in {"target", "maximum"} else 108))
            item.setData(Qt.ItemDataRole.AccessibleTextRole, f"{educator.name}, {format_duration(minutes)} planifiées. {hour_status.label}")
            tooltip = f"{educator.name}\nAncienneté : {educator.seniority}\nPlanifiées : {format_duration(minutes)} · Cible : {format_duration(educator.target_minutes)}\nDouble-cliquez pour modifier le profil."
            item.setToolTip(tooltip)
            card = QFrame()
            card.setObjectName("educatorCard")
            card.setToolTip(tooltip)
            card.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            layout = QVBoxLayout(card)
            layout.setContentsMargins(13, 11, 13, 10)
            layout.setSpacing(4)
            heading = QHBoxLayout()
            heading.setSpacing(7)
            color = QColor(educator.color)
            if not color.isValid():
                color = QColor("#4e7b68")
            initials = "".join(word[0].upper() for word in educator.name.split()[:2])
            dot = QLabel(initials)
            dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
            dot.setFixedSize(36, 36)
            dot.setStyleSheet(f"background:{color.lighter(135).name()};color:{color.darker(135).name()};border-radius:18px;font-size:11px;font-weight:600;")
            heading.addWidget(dot)
            identity = QVBoxLayout()
            identity.setSpacing(2)
            name = QLabel(educator.name + (" · inactive" if not educator.active else ""))
            name.setObjectName("educatorName")
            name.setMinimumWidth(0)
            name.setText(name.fontMetrics().elidedText(name.text(), Qt.TextElideMode.ElideRight, 156))
            identity.addWidget(name)
            groups = {group.id: group.name for group in self.week.groups}
            detail = QLabel(f"Rang {educator.seniority} · Éducatrice")
            detail.setObjectName("smallMuted")
            identity.addWidget(detail)
            heading.addLayout(identity, 1)
            layout.addLayout(heading)
            stats = QHBoxLayout()
            hours = QLabel(format_duration(minutes))
            hours.setObjectName("educatorHours")
            hours.setToolTip("Heures rémunérées planifiées pour cette journée")
            stats.addWidget(hours)
            stats.addStretch()
            target = QLabel(f"/ {format_duration(educator.target_minutes)}" if educator.target_minutes else "")
            target.setObjectName("smallMuted")
            stats.addWidget(target)
            layout.addLayout(stats)
            progress = QProgressBar()
            progress.setRange(0, max(1, educator.target_minutes))
            progress.setValue(min(minutes, educator.target_minutes) if educator.target_minutes else 0)
            progress.setTextVisible(False)
            progress.setFixedHeight(3)
            progress_color = hour_status.color if hour_status.code in {"target", "maximum"} else color.name()
            progress.setStyleSheet(f"QProgressBar {{border:0;background:#edf2ee;border-radius:1px;}} QProgressBar::chunk {{background:{progress_color};border-radius:1px;}}")
            layout.addWidget(progress)
            balance = "Objectif atteint" if remaining == 0 else (f"Reste {format_duration(remaining)}" if remaining > 0 else f"Au-delà de la cible : {format_duration(-remaining)}")
            label = QLabel(hour_status.label)
            label.setWordWrap(True)
            label.setStyleSheet(f"color:{hour_status.color};font-size:12px;")
            card.setAccessibleName(f"{educator.name}. {format_duration(minutes)} planifiées. {hour_status.label}")
            layout.addWidget(label)
            self.educator_list.addItem(item)
            self.educator_list.setItemWidget(item, card)
            if educator.id == selected_id:
                self.educator_list.setCurrentItem(item)
        if not self.educator_list.count():
            message = "Aucun résultat pour cette recherche." if query else ("Aucune éducatrice active. Affichez les profils inactifs." if self.week.educators else "Ajoutez votre première éducatrice\npour commencer la planification.")
            empty = QListWidgetItem(message)
            empty.setFlags(Qt.ItemFlag.NoItemFlags)
            empty.setSizeHint(QSize(230, 74))
            self.educator_list.addItem(empty)
        elif self.educator_list.currentItem() is None:
            self.educator_list.setCurrentRow(0)
        self._refresh_profile_button()

    def refresh_alerts(self):
        self.alert_list.clear()
        displayed = visible_alerts(self.week,self.issues)
        errors = sum(issue.severity == "error" for issue in displayed)
        warnings = len(displayed) - errors
        self.alert_toggle.setText(f"{errors} erreur{'s' if errors != 1 else ''} · {warnings} avertissement{'s' if warnings != 1 else ''}")
        self.alert_badge.setText(str(len(displayed)))
        self.top_alert_button.setAccessibleName(f"Vérifier ({len(displayed)})")
        self.top_alert_button.setIcon(icon("alert" if self.issues else "check", size=16, color="#D5E3DD"))
        self.top_alert_button.setToolTip(f"{errors} erreur(s) bloquante(s) · {warnings} avertissement(s). Cliquer pour voir les détails.")
        ready = bool(self.week.educators and any(group.periods for group in self.week.groups))
        self.alert_heading_label.setText("Points à vérifier" if self.issues else "Aucune alerte")
        for issue in sorted(displayed, key=lambda item: (item.severity != "error", item.day if item.day is not None else 9, item.start or 0)):
            item = QListWidgetItem(("Erreur — " if issue.severity == "error" else "Attention — ") + alert_text(self.week, issue, global_scope=True))
            item.setForeground(QColor("#a33c32" if issue.severity == "error" else "#8a651a"))
            item.setData(Qt.ItemDataRole.UserRole, issue)
            item.setToolTip(issue.suggestion or issue.message)
            self.alert_list.addItem(item)
        if not self.issues:
            self.alert_list.addItem("Aucune alerte")

    def _can_edit(self):
        if self.read_only:
            QMessageBox.information(self, "Consultation", "Cette version est en lecture seule. Dupliquez la journée ou restaurez une version depuis l'historique pour la modifier.")
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
            if candidate.planning_date:
                candidate.settings.staffing_policy = 2
            # Round-trip asserts basic types; business-invalid drafts remain editable.
            candidate = Week.from_dict(candidate.to_dict())
        except Exception as error:
            QMessageBox.warning(self, "Modification impossible", str(error))
            return False
        if before.to_dict() == candidate.to_dict():
            return False
        self._undo.append(before)
        self._undo = self._undo[-50:]
        self._redo.clear()
        self.week = candidate
        self._modified()
        return True

    def _modified(self):
        self.dirty = True
        self._set_save_state(False)
        self.refresh()
        self.autosave.start()

    def _set_save_state(self, saved, error=False):
        text = "Enregistré" if saved else "Hors ligne – modifications locales"
        if error:
            text += " — sauvegarde impossible"
        self.save_label.setText(text)
        self.save_label.setAccessibleName("État de sauvegarde : " + text)

    def undo(self):
        if not self._undo or self.read_only:
            return
        self._redo.append(deepcopy(self.week))
        self._redo = self._redo[-50:]
        self.week = self._undo.pop()
        self.week.status = "draft"
        self._modified()

    def redo(self):
        if not self._redo or self.read_only:
            return
        self._undo.append(deepcopy(self.week))
        self._undo = self._undo[-50:]
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
            self._set_save_state(True)
            return True
        except Exception as error:
            self.dirty = True
            self._set_save_state(False, error=True)
            if manual or not self._save_error_shown:
                QMessageBox.critical(self, "Sauvegarde impossible", f"{error}\n\nGardez l'application ouverte et choisissez un dossier accessible ou libérez de l'espace avant de réessayer.")
                self._save_error_shown = True
            return False

    def _upgrade_working_rules(self):
        from ..staffing import adopt_current_draft_rules
        if self._history_version is None and adopt_current_draft_rules(self.week):
            self.dirty = True
            self._set_save_state(False)
            self.autosave.start()

    def _load(self, week, version=None):
        self.autosave.stop()
        self.week = deepcopy(week)
        if week.planning_date:
            self.day = 0
        self._history_version = version
        self._undo.clear()
        self._redo.clear()
        self.dirty = False
        self._set_save_state(True)
        self._upgrade_working_rules()
        self.refresh()

    def _date_changed(self, selected):
        if not self._updating and selected == self.week_date.date() and self.week_date.isDateAvailable(selected):
            self.switch_day(selected.toPython())

    def navigate_day(self, direction):
        current = QDate.fromString(self.week.planning_date or self.week.monday, "yyyy-MM-dd")
        target = current.addDays(direction)
        while self.week_date.minimumDate() <= target <= self.week_date.maximumDate():
            if self.week_date.isDateAvailable(target):
                self.switch_day(target.toPython())
                return
            target = target.addDays(1 if direction >= 0 else -1)

    def switch_day(self, selected):
        if self._worker is not None:
            self.refresh()
            return
        if selected.isoformat() == self.week.planning_date and self._history_version is None:
            return
        if self.dirty and not self.save_week():
            self.refresh()
            return
        try:
            plan = self.repo.load_day(selected.isoformat())
            if plan is None:
                plan = day_plan(selected.isoformat(), self.repo.latest_week() or self.week)
                self.repo.save(plan)
            self.day = 0
            self._load(plan)
            self.calendar.set_mode("Jour")
        except Exception as error:
            QMessageBox.warning(self, "Journée indisponible", str(error))
            self.refresh()

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
        self.day = 0 if self.week.planning_date else max(0, min(4, day))
        self.day_combo.setCurrentIndex(self.day)
        self.calendar.set_week(self.week, self.day, self.issues)

    def expand_day(self, day):
        self.select_day(day)
        self.set_mode("Jour")

    def set_mode(self, mode):
        if self.week.planning_date:
            mode = "Jour"
        self.calendar.set_mode(mode)
        self.day_mode.setChecked(mode == "Jour")
        self.week_mode.setChecked(mode == "Semaine")

    def toggle_sidebar(self):
        self._sidebar_manual_hidden = self.sidebar.isVisible()
        self._auto_hidden_sidebar = False
        self.sidebar.setVisible(not self._sidebar_manual_hidden)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "sidebar"):
            if self.width() < 960 and not self._sidebar_manual_hidden and self.management_stack.currentWidget() is self.team_page:
                self.sidebar.hide()
                self._auto_hidden_sidebar = True
            elif self.width() >= 960 and self._auto_hidden_sidebar:
                self.sidebar.show()
                self._auto_hidden_sidebar = False
        if hasattr(self,"workspace_layout") and hasattr(self,"day_controls_layout"):
            compact = self.height() < 800
            self.rail_layout.setSpacing(8 if compact else 18)
            self.rail_layout.setContentsMargins(10,12 if compact else 28,10,12 if compact else 20)
            narrow = self.width() < 1000
            self.workspace_layout.setSpacing(6 if compact else 14)
            self.workspace_layout.setContentsMargins(18 if compact else 28,8 if compact else 20,18 if compact else 28,8 if compact else 10)
            self.brand_subtitle.setVisible(not compact)
            self.brand_label.setStyleSheet("font-size:20px;font-weight:700;" if compact else "font-size:28px;font-weight:700;")
            self.date_navigation_layout.setContentsMargins(0,0,0,0) if compact else self.date_navigation_layout.setContentsMargins(4,3,4,3)
            self.day_controls_layout.setContentsMargins(12,2 if compact else 6,12,2 if compact else 6)
            self.day_title.setMaximumWidth(210 if narrow else 440)
            self.undo_button.setText("" if narrow else "Annuler")
            self.redo_button.setText("" if narrow else "Rétablir")
            self.export_button.setText("" if narrow else "Exporter PDF")
            self.generate_button.setText("" if narrow else "Générer l’horaire")
            self.export_button.setMinimumWidth(48)
            self.generate_button.setMinimumWidth(48)
            if hasattr(self,"_day_summary"):
                self.calendar_summary.setText(("" if narrow else "Horaires des éducatrices · ")+self._day_summary)
            if hasattr(self,"alert_panel"):
                self._position_alerts()


    def toggle_coverage(self, visible):
        self.calendar.set_coverage_visible(visible)
        action = "Masquer" if visible else "Afficher"
        self.coverage_toggle.setProperty("active", visible)
        self.coverage_toggle.style().unpolish(self.coverage_toggle)
        self.coverage_toggle.style().polish(self.coverage_toggle)
        self.coverage_toggle.setAccessibleName(action+" la bande de ratio")
        self.coverage_toggle.setToolTip(action+" la bande de ratio. Elle n’est jamais incluse dans le PDF.")

    def show_management(self, page):
        target = {"team": self.team_page, "enrolment": self.enrolment_page,
                  "alerts": self.alert_panel}[page]
        self.management_stack.setCurrentWidget(target)
        self.sidebar.show()
        self._sidebar_manual_hidden = False
        self._auto_hidden_sidebar = False
        self.alert_toggle.setChecked(page == "alerts")
        for button, active in ((self.enrolment_button,page == "enrolment"),
                               (self.top_alert_button,page == "alerts")):
            button.setProperty("active", active)
            button.style().unpolish(button)
            button.style().polish(button)
        {"team": self.educator_search, "enrolment": self.enrolment_panel.count,
         "alerts": self.alert_list}[page].setFocus()

    def toggle_alerts(self):
        self.show_management("alerts" if self.alert_toggle.isChecked() else "team")

    def _position_alerts(self):
        # Management pages share the left panel; they never shrink the calendar.
        pass

    def fit_day(self):
        first = self.calendar.start_minute
        last = self.calendar.end_minute
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
        if issue is not None and issue.day is not None and issue.start is not None:
            self.expand_day(issue.day)
            self.calendar.highlight_interval(issue.day, issue.start, issue.end or issue.start+1)
        elif issue is not None:
            related = [s for s in self.week.shifts if s.id in issue.shift_ids]
            if related:
                shift = min(related, key=lambda s: (s.day, s.start))
                self.expand_day(shift.day)
                self.calendar.highlight_interval(shift.day, min(s.start for s in related), max(s.end for s in related))
                self.calendar.canvas.selection = ("shift", shift.id)
            else:
                self.calendar.highlight_interval(self.day, self.week.settings.open_minute-self.week.settings.opening_buffer,
                                                  self.week.settings.close_minute+self.week.settings.closing_buffer)
        if issue is not None and issue.suggestion:
            self.statusBar().showMessage(issue.suggestion, 12000)

    def verify(self):
        self.refresh()
        self.show_management("alerts")
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
            text = "Conserver une version publiée figée de cet horaire ?" if status == "published" else "Archiver cette journée ? Elle restera consultable dans l'historique."
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
        self.day_title.start_editing()

    def _rename_day(self, name):
        self.commit(lambda week: week.day_names.__setitem__(self.day, name.strip()))

    def enrolment(self):
        self.enrolment_panel.load_week(self.week)
        self.enrolment_panel.save_button.setEnabled(not self.read_only)
        self.show_management("enrolment")

    def apply_enrolment(self):
        if not self._can_edit():
            return
        from ..planning import plan_pedagogical_day
        self.commit(lambda week: plan_pedagogical_day(week, 0, self.enrolment_panel.count.value()))
        self.statusBar().showMessage("Inscriptions enregistrées.", 4000)

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
                if collection == "groups" and (any(s.group_id == original.id for s in self.week.shifts) or (not self.week.planning_date and any(a.group_id == original.id for a in self.week.activities))):
                    QMessageBox.information(self, "Groupe utilisé", "Retirez les quarts du groupe avant de le supprimer, ou fermez ses périodes d'ouverture.")
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
        layout.addWidget(note("Les modifications s'appliquent à cette journée et aux nouvelles journées. Les versions déjà archivées gardent leurs données."))
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
            def apply(week):
                week.settings = dialog.result_item()
                if not week.groups:
                    week.groups.append(Group(new_id(), "Service de garde"))
                for group in week.groups:
                    group.ratio = dialog.staff_ratio.value()
            self.commit(apply)

    def new_shift(self, checked=False, *, day=None, start=None, group_id="", educator_id=""):
        if not self._can_edit():
            return
        if not self.week.educators or not self.week.groups:
            QMessageBox.information(self, "Préparer le calendrier", "Ajoutez une éducatrice et saisissez les inscriptions, puis glissez son nom sur le calendrier ou double-cliquez sur une plage vide.")
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
        preview_day.addItems([result.proposal.day_label(day) for day in result.proposal.active_days])
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

        preview_controls.addStretch()
        layout.addLayout(preview_controls)
        calendar.set_week(result.proposal, self.day, preview_issues)
        calendar.set_mode("Jour")
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
            weeks = self.repo.list_days()
        except Exception as error:
            QMessageBox.warning(self, "Journées", str(error))
            return
        if not weeks:
            QMessageBox.information(self, "Journées", "Aucune autre journée sauvegardée.")
            return
        labels = [f"{full_date(QDate.fromString(row['date'], 'yyyy-MM-dd'))} — {STATUS_LABELS.get(row['status'], row['status'])}" for row in weeks]
        choice, accepted = QInputDialog.getItem(self, "Consulter une journée", "Journées sauvegardées", labels, 0, False)
        if accepted:
            self.switch_day(date.fromisoformat(weeks[labels.index(choice)]["date"]))

    def duplicate_week(self):
        if self._worker is not None or (self.dirty and not self.save_week()):
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Dupliquer la journée")
        layout = QFormLayout(dialog)
        selected = DaySelector(dialog)
        selected.setDate(QDate.fromString(self.week.planning_date or self.week.monday, "yyyy-MM-dd").addDays(1))
        layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        layout.addRow("Date de la nouvelle journée", selected)
        layout.addRow(note("Les quarts et inscriptions sont copiés. Une journée existante n'est jamais remplacée."))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Dupliquer")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Annuler")
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            day = selected.date().toPython()
            try:
                self._load(self.repo.duplicate_day(self.week, day.isoformat()))
            except Exception as error:
                QMessageBox.warning(self, "Duplication impossible", str(error))

    def show_history(self):
        if self._worker is not None or (self.dirty and not self.save_week()):
            return
        try:
            versions = self.repo.history(self.week.storage_key)
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
        layout.addWidget(self._button("Revenir à la version courante", lambda: (dialog.accept(), self.switch_day(date.fromisoformat(self.week.planning_date or self.week.monday)))))
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
                week = day_plan(today.isoformat())
            if not week.planning_date:
                saved_days = self.repo.list_days()
                if saved_days:
                    week = self.repo.load_day(saved_days[0]["date"])
                else:
                    week = day_plan(date.today().isoformat(), week)
                    self.repo.save(week)
            self._load(week)
            QMessageBox.information(self, "Importation terminée", f"Sauvegarde importée. La copie de sécurité précédente est conservée ici :\n{safety}")
        except Exception as error:
            QMessageBox.warning(self, "Importation impossible", str(error))

    def export_pdf(self):
        destination, _ = QFileDialog.getSaveFileName(
            self, "Exporter l’horaire de la journée", f"Horaire-pedagogique-{self.week.planning_date or self.week.monday}.pdf", "PDF (*.pdf)")
        if not destination:
            return
        try:
            export_general(self.week, destination)
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
                    if self.week.planning_date and kind == "general":
                        from PySide6.QtGui import QPageLayout, QPageSize
                        printer.setPageSize(QPageSize(QPageSize.PageSizeId.Letter))
                        printer.setPageOrientation(QPageLayout.Orientation.Landscape)
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
