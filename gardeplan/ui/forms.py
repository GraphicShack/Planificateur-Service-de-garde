"""Éditeurs locaux en français. Les dialogues ne modifient jamais leur semaine source."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import re

from PySide6.QtCore import Qt, QEvent, Signal
from PySide6.QtGui import QColor, QValidator
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QColorDialog, QComboBox, QDialog,
    QApplication, QDialogButtonBox, QFormLayout, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMessageBox, QPushButton, QSpinBox,
    QTabWidget, QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout,
    QWidget, QHeaderView, QScrollArea,
)
from gardeplan.models import (
    Activity, Break, Educator, Group, GroupPeriod, Room, Settings, Shift,
    Window, new_id, format_duration, format_time, paid_minutes,
)
from gardeplan.identity import next_educator_color
from .theme import EDITOR_STYLE, light_palette
from .flow_layout import FlowLayout

DAYS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi"]


class MinuteEdit(QSpinBox):
    """Heure ou durée entière, sans conversion en nombres flottants."""
    def __init__(self, value=0, *, duration=False, parent=None):
        super().__init__(parent)
        self.duration = duration
        self.setRange(0, 10080 if duration else 1440)
        self.setKeyboardTracking(False)
        self.setAccelerated(True)
        self.setMinimumWidth(112)
        self.setValue(value)
        self.setToolTip("Saisir heures:minutes, par exemple 07:13. Les flèches ajustent d'une minute.")

    def textFromValue(self, value):
        return f"{value // 60:02d}:{value % 60:02d}"

    def valueFromText(self, text):
        match = re.fullmatch(r"\s*(\d{1,3})\s*[:h]\s*(\d{1,2})\s*", text)
        if match:
            return min(self.maximum(), int(match[1]) * 60 + int(match[2]))
        return self.value()

    def validate(self, text, pos):
        match = re.fullmatch(r"\s*(\d{1,3})\s*[:h]\s*(\d{1,2})\s*", text)
        if match:
            total = int(match[1]) * 60 + int(match[2])
            if int(match[2]) < 60 and total <= self.maximum():
                return QValidator.State.Acceptable, text, pos
            return QValidator.State.Invalid, text, pos
        if re.fullmatch(r"[\d\sh:]{0,8}", text):
            return QValidator.State.Intermediate, text, pos
        return QValidator.State.Invalid, text, pos


def integer(value=0, minimum=0, maximum=10000, suffix=""):
    widget = QSpinBox()
    widget.setRange(minimum, maximum)
    widget.setValue(value)
    widget.setSuffix(suffix)
    return widget


def check(text, checked=False):
    widget = QCheckBox(text)
    widget.setChecked(checked)
    return widget


def note(text):
    label = QLabel(text)
    label.setWordWrap(True)
    label.setObjectName("formHint")
    label.setStyleSheet("color: #52655E; font-size: 14px;")
    return label


def page():
    widget = QWidget()
    layout = QFormLayout(widget)
    layout.setContentsMargins(18, 16, 18, 16)
    layout.setSpacing(12)
    layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
    return widget, layout


class ColorButton(QPushButton):
    def __init__(self, color):
        super().__init__()
        self.color = color
        self.clicked.connect(self.pick)
        self.refresh()

    def refresh(self):
        self.setText("Modifier la couleur")
        self.setAccessibleName("Couleur d'identification")
        self.setToolTip(self.color)
        self.setStyleSheet(f"border-left: 16px solid {self.color}; text-align: left; padding: 8px;")

    def pick(self):
        chosen = QColorDialog.getColor(QColor(self.color), self, "Couleur d'identification")
        if chosen.isValid():
            self.color = chosen.name()
            self.refresh()


class IntervalsEditor(QWidget):
    """Périodes hebdomadaires éditées par jour, heure exacte et effectif éventuel."""
    def __init__(self, periods=(), *, students=False, parent=None, daily_label="", compact=False):
        super().__init__(parent)
        self.students = students
        self.day_labels = [daily_label] if daily_label else DAYS
        self.daily_label = daily_label
        self.compact = compact
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.table = QTableWidget(0, 4 if students else 3)
        self.table.setHorizontalHeaderLabels(["Jour", "Début", "Fin"] + (["Élèves"] if students else []))
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().hide()
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setMinimumHeight(112 if compact else 220)
        if compact:
            self.table.setMaximumHeight(112)
        layout.addWidget(self.table)
        row = FlowLayout(spacing=8) if compact else QHBoxLayout()
        add = QPushButton("+ Ajouter" if compact else "+ Ajouter une période")
        remove = QPushButton("Retirer" if compact else "Retirer la sélection")
        add.setAccessibleName("Ajouter une période")
        remove.setAccessibleName("Retirer la période sélectionnée")
        copy_days = QPushButton("Copier lundi → semaine")
        add.clicked.connect(lambda: self.add_row())
        remove.clicked.connect(self.remove_selected)
        copy_days.clicked.connect(self.copy_monday)
        row.addWidget(add)
        row.addWidget(remove)
        row.addWidget(copy_days)
        copy_days.setVisible(not bool(daily_label))
        if daily_label:
            self.table.setColumnHidden(0, True)
        layout.addLayout(row)
        for p in periods:
            self.add_row(p.day, p.start, p.end, getattr(p, "students", 20))

    def add_row(self, day=0, start=420, end=1050, students=20):
        row = self.table.rowCount()
        self.table.insertRow(row)
        day_input = QComboBox()
        day_input.addItems(self.day_labels)
        day_input.setCurrentIndex(day)
        self.table.setCellWidget(row, 0, day_input)
        self.table.setCellWidget(row, 1, MinuteEdit(start))
        self.table.setCellWidget(row, 2, MinuteEdit(end))
        if self.students:
            self.table.setCellWidget(row, 3, integer(students, 0, 10000))
        self.table.setRowHeight(row, 48 if self.compact else 40)

    def remove_selected(self):
        rows = {i.row() for i in self.table.selectedIndexes()}
        if not rows and self.table.currentRow() >= 0:
            rows.add(self.table.currentRow())
        for row in sorted(rows, reverse=True):
            self.table.removeRow(row)

    def values(self):
        result = []
        for row in range(self.table.rowCount()):
            day = self.table.cellWidget(row, 0).currentIndex()
            start_widget = self.table.cellWidget(row, 1)
            end_widget = self.table.cellWidget(row, 2)
            start_widget.interpretText()
            end_widget.interpretText()
            start, end = start_widget.value(), end_widget.value()
            if start >= end:
                raise ValueError(f"{self.day_labels[day]}, ligne {row + 1} : la fin doit être après le début.")
            if self.students:
                result.append(GroupPeriod(day, start, end, self.table.cellWidget(row, 3).value()))
            else:
                result.append(Window(day, start, end))
        ordered = sorted(result, key=lambda p: (p.day, p.start, p.end))
        for previous, current in zip(ordered, ordered[1:]):
            if previous.day == current.day and current.start < previous.end:
                raise ValueError(f"{self.day_labels[current.day]} : deux périodes se chevauchent. Ajustez leurs heures.")
        return ordered

    def copy_monday(self):
        try:
            monday = [p for p in self.values() if p.day == 0]
            if not monday:
                raise ValueError("Ajoutez d'abord au moins une période le lundi.")
        except ValueError as error:
            QMessageBox.warning(self, "Périodes", str(error))
            return
        if self.table.rowCount() > len(monday):
            response = QMessageBox.question(self, "Copier les périodes", "Remplacer les périodes du mardi au vendredi par celles du lundi ?")
            if response != QMessageBox.StandardButton.Yes:
                return
        self.table.setRowCount(0)
        for day in range(5):
            for period in monday:
                self.add_row(day, period.start, period.end, getattr(period, "students", 20))


class BreaksEditor(QWidget):
    changed = Signal()
    def __init__(self, breaks=()):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Début", "Fin", "Payée", "Type", "Durée"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().hide()
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setMinimumHeight(155)
        layout.addWidget(self.table)
        actions = QHBoxLayout()
        add = QPushButton("+ Ajouter une pause")
        remove = QPushButton("Retirer la sélection")
        add.clicked.connect(lambda: self.add_row())
        remove.clicked.connect(self.remove_selected)
        actions.addWidget(add)
        actions.addWidget(remove)
        layout.addLayout(actions)
        for b in breaks:
            self.add_row(b.start, b.end, b.paid, b.kind)

    def add_row(self, start=720, end=750, paid=False, kind="pause"):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setCellWidget(row, 0, MinuteEdit(start))
        self.table.setCellWidget(row, 1, MinuteEdit(end))
        self.table.setCellWidget(row, 2, check("Oui", paid))
        category = QComboBox()
        category.addItem("Pause", "pause")
        category.addItem("Dîner", "dinner")
        category.setCurrentIndex(max(0, category.findData(kind)))
        self.table.setCellWidget(row, 3, category)
        duration = MinuteEdit(max(1, end-start), duration=True)
        duration.setMinimum(1)
        self.table.setCellWidget(row, 4, duration)
        self.table.setRowHeight(row, 48)
        first, last = self.table.cellWidget(row, 0), self.table.cellWidget(row, 1)
        def update_duration():
            duration.blockSignals(True)
            duration.setValue(max(1, last.value()-first.value()))
            duration.blockSignals(False)
            self.changed.emit()
        def update_end():
            last.setValue(min(1440, first.value()+duration.value()))
            self.changed.emit()
        first.valueChanged.connect(update_duration)
        last.valueChanged.connect(update_duration)
        duration.valueChanged.connect(update_end)
        self.table.cellWidget(row, 2).toggled.connect(lambda _: self.changed.emit())
        category.currentIndexChanged.connect(lambda _: self.changed.emit())
        self.changed.emit()

    def remove_selected(self):
        rows = {i.row() for i in self.table.selectedIndexes()}
        if not rows and self.table.currentRow() >= 0:
            rows.add(self.table.currentRow())
        for row in sorted(rows, reverse=True):
            self.table.removeRow(row)
        self.changed.emit()

    def values(self, start, end):
        result = []
        for row in range(self.table.rowCount()):
            first = self.table.cellWidget(row, 0)
            last = self.table.cellWidget(row, 1)
            first.interpretText()
            last.interpretText()
            if not start <= first.value() < last.value() <= end:
                raise ValueError(f"Pause {row + 1} : choisissez des heures comprises dans la présence du quart.")
            result.append(Break(first.value(), last.value(), self.table.cellWidget(row, 2).isChecked(), self.table.cellWidget(row, 3).currentData()))
        result.sort(key=lambda b: b.start)
        if any(a.end > b.start for a, b in zip(result, result[1:])):
            raise ValueError("Deux pauses se chevauchent. Corrigez leurs heures.")
        return result


class EditorDialog(QDialog):
    def __init__(self, title, *, existing=False, parent=None, tabbed=True):
        super().__init__(parent)
        self.setObjectName("editorDialog")
        self.setPalette(light_palette())
        self.setAutoFillBackground(True)
        self.setStyleSheet(EDITOR_STYLE)
        self.setWindowTitle(title)
        self.setMinimumWidth(620)
        self.resize(720, 680)
        self.delete_requested = False
        self._item = None
        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(18, 18, 18, 18)
        heading = QLabel(title)
        heading.setObjectName("editorHeading")
        heading.setWordWrap(True)
        self.root.addWidget(heading)
        if tabbed:
            self.tabs = QTabWidget()
            self.root.addWidget(self.tabs, 1)
        else:
            self.scroll = QScrollArea()
            self.scroll.setWidgetResizable(True)
            self.scroll.setFrameShape(QFrame.Shape.NoFrame)
            self.body = QWidget()
            self.body.setObjectName("editorBody")
            self.body_layout = QVBoxLayout(self.body)
            self.body_layout.setContentsMargins(0, 0, 8, 0)
            self.body_layout.setSpacing(12)
            self.scroll.setWidget(self.body)
            self.root.addWidget(self.scroll, 1)
        buttons = QDialogButtonBox()
        buttons.addButton("Annuler", QDialogButtonBox.ButtonRole.RejectRole)
        save = buttons.addButton("Enregistrer", QDialogButtonBox.ButtonRole.AcceptRole)
        save.setObjectName("editorSave")
        save.setDefault(True)
        buttons.accepted.connect(self.try_accept)
        buttons.rejected.connect(self.reject)
        if existing:
            delete = buttons.addButton("Supprimer", QDialogButtonBox.ButtonRole.DestructiveRole)
            delete.setStyleSheet("color: #b42318;")
            delete.clicked.connect(self.delete_item)
        self.root.addWidget(buttons)
        self.buttons = buttons

    def add_page(self, title):
        widget, layout = page()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(widget)
        self.tabs.addTab(scroll, title)
        return layout

    def try_accept(self):
        try:
            # Commit any pending text in spin boxes before collecting values.
            for spin in self.findChildren(QSpinBox):
                spin.interpretText()
            self._item = self.build_item()
        except (ValueError, TypeError) as error:
            QMessageBox.warning(self, "À vérifier", str(error))
            return
        self.accept()

    def delete_item(self):
        response = QMessageBox.question(self, "Supprimer", "Supprimer cet élément ? Vous pourrez annuler cette action depuis le calendrier.")
        if response == QMessageBox.StandardButton.Yes:
            self.delete_requested = True
            self.accept()

    def result_item(self):
        return self._item

    @staticmethod
    def require_name(widget, label="Le nom"):
        name = widget.text().strip()
        if not name:
            raise ValueError(f"{label} est obligatoire.")
        return name


class ProfileColumns(QWidget):
    """One continuous form, with two columns only when they fit comfortably."""
    def __init__(self, viewport, parent=None):
        super().__init__(parent)
        self.viewport = viewport
        self.columns = QGridLayout(self)
        self.columns.setContentsMargins(0, 0, 0, 0)
        self.columns.setSpacing(12)
        self.left, self.right = QWidget(), QWidget()
        self.left_layout = QVBoxLayout(self.left)
        self.right_layout = QVBoxLayout(self.right)
        for layout in (self.left_layout, self.right_layout):
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(12)
        self.columns.addWidget(self.left, 0, 0)
        self.columns.addWidget(self.right, 0, 1)
        self.columns.setColumnStretch(0, 1)
        self.columns.setColumnStretch(1, 1)
        self.stacked = False
        viewport.installEventFilter(self)

    def eventFilter(self, watched, event):
        if watched is self.viewport and event.type() == QEvent.Type.Resize:
            self.arrange(self.viewport.width())
        return super().eventFilter(watched, event)

    def arrange(self, available_width):
        # The content's minimum width can exceed the viewport before stacking.
        # Using its own width would then prevent the narrow layout from running.
        stacked = available_width < 920
        for form in self.left.findChildren(QFormLayout):
            form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows if stacked
                                  else QFormLayout.RowWrapPolicy.DontWrapRows)
        if stacked != self.stacked:
            self.stacked = stacked
            self.columns.removeWidget(self.right)
            self.columns.addWidget(self.right, 1 if stacked else 0, 0 if stacked else 1)
            self.columns.setColumnStretch(1, 0 if stacked else 1)


def profile_section(title):
    frame = QFrame()
    frame.setObjectName("formSection")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(14, 12, 14, 12)
    layout.setSpacing(8)
    heading = QLabel(title)
    heading.setObjectName("formSectionTitle")
    layout.addWidget(heading)
    return frame, layout


class EducatorDialog(EditorDialog):
    def __init__(self, week, educator=None, parent=None):
        super().__init__("Modifier le profil" if educator else "Ajouter un éducateur ou une éducatrice",
                         existing=educator is not None, parent=parent, tabbed=False)
        self.setMinimumSize(480, 420)
        screen = self.screen() or QApplication.primaryScreen()
        available = screen.availableGeometry() if screen else None
        self.resize(min(1120, available.width()-32) if available else 1120,
                    min(900, available.height()-48) if available else 900)
        self.week = week
        self.source = deepcopy(educator) if educator else Educator(id=new_id(), name="", target_minutes=0 if week.planning_date else 2100, max_minutes=(week.settings.max_daily_minutes or 1440) if week.planning_date else 2400)
        if educator is None:
            self.source.color = next_educator_color(week.educators)
            self.source.seniority = min(11, max((person.seniority for person in week.educators), default=0) + 1)
        ed = self.source
        self.body_layout.addWidget(note("Le nom est obligatoire. Les disponibilités et les préférences sont facultatives."))
        self.profile_columns = ProfileColumns(self.scroll.viewport())
        self.body_layout.addWidget(self.profile_columns)
        identity, identity_layout = profile_section("Profil et ancienneté")
        form = QFormLayout()
        form.setSpacing(8)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.DontWrapRows)
        identity_layout.addLayout(form)
        self.profile_columns.left_layout.addWidget(identity)
        self.name = QLineEdit(ed.name)
        self.name.setPlaceholderText("Ex. : Camille Roy")
        self.name.setAccessibleName("Nom et prénom")
        self.color = ColorButton(ed.color)
        self.seniority = integer(ed.seniority, 1, 11)
        self.seniority.setPrefix("Rang ")
        self.seniority.setToolTip("Choisissez un rang de 1 à 11. Les rangs intermédiaires peuvent rester libres.")
        self.seniority_date = QLineEdit(ed.seniority_date)
        self.seniority_date.setPlaceholderText("Facultative — AAAA-MM-JJ")
        self.active = check("Profil actif", ed.active)
        self.target = MinuteEdit(ed.target_minutes, duration=True)
        self.guaranteed = MinuteEdit(ed.guaranteed_minutes, duration=True)
        self.maximum = MinuteEdit(ed.max_minutes, duration=True)
        for field in (self.name, self.color, self.seniority, self.seniority_date,
                      self.target, self.guaranteed, self.maximum):
            field.setFixedHeight(44)
        form.addRow("Nom et prénom", self.name)
        form.addRow("Couleur", self.color)
        form.addRow("Rang d'ancienneté", self.seniority)
        form.addRow("Date d'ancienneté", self.seniority_date)
        form.addRow(self.active)
        identity_layout.addWidget(note("Rangs 1 à 11, avec des rangs libres. Le rang 1 est le plus ancien."))
        hours, hours_layout = profile_section("Heures pour la journée" if week.planning_date else "Heures hebdomadaires")
        form = QFormLayout()
        form.setSpacing(8)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.DontWrapRows)
        hours_layout.addLayout(form)
        form.addRow("Objectif (h:min)", self.target)
        form.addRow("Heures garanties (h:min)", self.guaranteed)
        form.addRow("Maximum obligatoire (h:min)", self.maximum)
        hours_layout.addWidget(note("Un objectif de 00:00 reste à définir."))
        self.profile_columns.left_layout.addWidget(hours)
        availability, availability_layout = profile_section("Disponibilités et absences")
        self.availability = IntervalsEditor(ed.availability, daily_label=week.day_label(0) if week.planning_date else "", compact=True)
        self.absences = IntervalsEditor(ed.absences, daily_label=week.day_label(0) if week.planning_date else "", compact=True)
        availability_layout.addWidget(note("Sans période, le profil est disponible toute la journée."))
        for title, editor in (("Disponibilités", self.availability), ("Absences et congés", self.absences)):
            availability_layout.addWidget(QLabel(title))
            availability_layout.addWidget(editor)
            editor.table.setAccessibleName(title)
            for action in editor.findChildren(QPushButton):
                action.setAutoDefault(False)
            editor.table.setSizeAdjustPolicy(QAbstractItemView.SizeAdjustPolicy.AdjustIgnored)
        self.profile_columns.right_layout.addWidget(availability)
        self.preferences = QListWidget()
        self.preferences.setMinimumHeight(80)
        self.preferences.setMaximumHeight(112)
        self.preferences.setAccessibleName("Groupes préférés")
        for group in week.groups:
            item = QListWidgetItem(group.name)
            item.setData(Qt.ItemDataRole.UserRole, group.id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if group.id in ed.preferred_groups else Qt.CheckState.Unchecked)
            self.preferences.addItem(item)
        notes, notes_layout = profile_section("Notes et restrictions")
        self.restrictions = QTextEdit(ed.restrictions)
        self.restrictions.setFixedHeight(72)
        self.restrictions.setAccessibleName("Notes et restrictions")
        self.restrictions.setPlaceholderText("Notes pour la responsable…")
        self.preferences.setParent(self)
        self.preferences.hide()
        notes_layout.addWidget(self.restrictions)
        notes_layout.addWidget(note("Notes informatives, sans contrainte automatique."))
        self.profile_columns.left_layout.addWidget(notes)
        self.profile_columns.left_layout.addStretch()
        self.profile_columns.right_layout.addStretch()
        self.body_layout.addStretch()
        self.name.setFocus()

    def build_item(self):
        ed = deepcopy(self.source)
        ed.name = self.require_name(self.name)
        ed.color = self.color.color
        ed.seniority = self.seniority.value()
        ed.seniority_date = self.seniority_date.text().strip()
        if ed.seniority_date:
            try:
                date.fromisoformat(ed.seniority_date)
            except ValueError:
                raise ValueError("La date d'ancienneté doit respecter le format AAAA-MM-JJ.")
        ed.target_minutes = self.target.value()
        ed.guaranteed_minutes = self.guaranteed.value()
        ed.max_minutes = self.maximum.value()
        if max(ed.guaranteed_minutes, ed.target_minutes) > ed.max_minutes:
            raise ValueError("Les heures garanties et l'objectif ne peuvent pas dépasser le maximum configuré.")
        ed.active = self.active.isChecked()
        ed.availability = self.availability.values()
        ed.absences = self.absences.values()
        ed.preferred_groups = [self.preferences.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.preferences.count()) if self.preferences.item(i).checkState() == Qt.CheckState.Checked]
        ed.restrictions = self.restrictions.toPlainText().strip()
        return ed


class GroupDialog(EditorDialog):
    def __init__(self, week, group=None, parent=None):
        super().__init__("Modifier le groupe" if group else "Créer un groupe", existing=group is not None, parent=parent)
        self.source = deepcopy(group) if group else Group(id=new_id(), name="")
        group = self.source
        form = self.add_page("Groupe et effectifs")
        self.name = QLineEdit(group.name)
        self.color = ColorButton(group.color)
        self.ratio = integer(group.ratio, 1, 1000, " élèves / éducatrice")
        self.minimum = integer(group.min_educators, 2, 100, " éducatrices")
        self.periods = IntervalsEditor(group.periods, students=True, daily_label=week.day_label(0) if week.planning_date else "")
        form.addRow("Nom du groupe", self.name)
        form.addRow("Couleur", self.color)
        form.addRow("Ratio maximal", self.ratio)
        form.addRow("Minimum simultané", self.minimum)
        form.addRow(note("Le besoin est le plus grand de ces deux nombres : le minimum simultané, ou l'effectif divisé par le ratio, arrondi au nombre entier supérieur. Le ratio initial est de 1 pour 20."))
        form.addRow("Ouverture et inscriptions", self.periods)
        form.addRow(note("Une période représente une ouverture du groupe. Ajoutez plusieurs périodes si l'effectif change. Sans période, le groupe reste fermé."))

    def build_item(self):
        group = deepcopy(self.source)
        group.name = self.require_name(self.name)
        group.color = self.color.color
        group.ratio = self.ratio.value()
        group.min_educators = self.minimum.value()
        group.periods = self.periods.values()
        return group


class RoomDialog(EditorDialog):
    def __init__(self, week, room=None, parent=None):
        super().__init__("Modifier le lieu" if room else "Ajouter un lieu", existing=room is not None, parent=parent)
        self.source = deepcopy(room) if room else Room(id=new_id(), name="")
        room = self.source
        form = self.add_page("Lieu")
        self.name = QLineEdit(room.name)
        self.capacity = integer(room.capacity, 0, 10000)
        self.capacity.setSpecialValueText("Sans limite configurée")
        self.shared = check("Autoriser plusieurs groupes simultanément", room.shared)
        self.outdoor = check("Lieu extérieur", room.outdoor)
        self.availability = IntervalsEditor(room.availability, daily_label=week.day_label(0) if week.planning_date else "")
        form.addRow("Nom du lieu", self.name)
        form.addRow("Capacité maximale", self.capacity)
        form.addRow(self.shared)
        form.addRow(self.outdoor)
        form.addRow("Disponibilités", self.availability)
        form.addRow(note("Sans période, le lieu est disponible pendant toute la journée. Pour un lieu partagé, la capacité s'applique à la somme des élèves présents."))

    def build_item(self):
        room = deepcopy(self.source)
        room.name = self.require_name(self.name)
        room.capacity = self.capacity.value()
        room.shared = self.shared.isChecked()
        room.outdoor = self.outdoor.isChecked()
        room.availability = self.availability.values()
        return room


class ShiftDialog(EditorDialog):
    def __init__(self, week, shift=None, day=0, start=420, group_id="", educator_id="", parent=None):
        super().__init__("Modifier le quart" if shift else "Ajouter un quart", existing=shift is not None, parent=parent)
        self.week = week
        self.source = deepcopy(shift) if shift else Shift(id=new_id(), educator_id=educator_id, group_id=group_id, day=day, start=start, end=min(start + 120, 1440))
        shift = self.source
        form = self.add_page("Quart de travail")
        self.educator = QComboBox()
        self.educator.addItem("Choisir une éducatrice", "")
        for ed in sorted(week.educators, key=lambda ed: (not ed.active, ed.seniority, ed.name)):
            if ed.active or ed.id == shift.educator_id:
                self.educator.addItem(ed.name + (" (inactive)" if not ed.active else ""), ed.id)
        self.educator.setCurrentIndex(max(0, self.educator.findData(shift.educator_id)))
        self.group = QComboBox()
        self.group.addItem("Choisir un groupe", "")
        for group in week.groups:
            self.group.addItem(group.name, group.id)
        self.group.setCurrentIndex(max(0, self.group.findData(shift.group_id)))
        self.day = QComboBox()
        self.day.addItems([week.day_label(0)] if week.planning_date else DAYS)
        self.day.setCurrentIndex(shift.day)
        self.start = MinuteEdit(shift.start)
        self.end = MinuteEdit(shift.end)
        self.before = integer(shift.buffer_before, 0, 240, " min")
        self.after = integer(shift.buffer_after, 0, 240, " min")
        self.before_paid = check("Rémunéré", shift.before_paid)
        self.after_paid = check("Rémunéré", shift.after_paid)
        self.locked = check("Verrouiller ce quart pendant la génération automatique", shift.locked)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setStyleSheet("background: #eef7f2; color: #245b46; border-radius: 7px; padding: 10px;")
        form.addRow("Éducatrice", self.educator)
        if week.planning_date:
            if not self.group.currentData() and week.groups:
                self.group.setCurrentIndex(1)
            self.group.setParent(self)
            self.group.hide()
        else:
            form.addRow("Groupe", self.group)
        form.addRow("Journée", self.day)
        form.addRow("Début de présence", self.start)
        form.addRow("Fin de présence", self.end)
        before_row = QHBoxLayout()
        before_row.addWidget(self.before)
        before_row.addWidget(self.before_paid)
        after_row = QHBoxLayout()
        after_row.addWidget(self.after)
        after_row.addWidget(self.after_paid)
        form.addRow("Préparation avant la couverture", before_row)
        form.addRow("Fermeture après la couverture", after_row)
        form.addRow(self.summary)
        form.addRow(self.locked)
        form.addRow(note("Les heures de présence incluent les buffers. Exemple : présence 06:50–12:00 et préparation 10 min donnent une couverture à partir de 07:00. Les pauses ne couvrent jamais les élèves."))
        form = self.add_page("Pauses et dîner")
        self.breaks = BreaksEditor(shift.breaks)
        self.breaks.changed.connect(self.refresh_summary)
        form.addRow(self.breaks)
        form.addRow(note("Saisissez les heures exactes de chaque pause. Une pause rémunérée compte dans les heures travaillées, mais pas dans la couverture du groupe."))
        for spin in (self.start, self.end, self.before, self.after):
            spin.valueChanged.connect(self.refresh_summary)
        self.before_paid.toggled.connect(self.refresh_summary)
        self.after_paid.toggled.connect(self.refresh_summary)
        self.refresh_summary()

    def refresh_summary(self):
        first = self.start.value() + self.before.value()
        last = self.end.value() - self.after.value()
        if first >= last:
            self.summary.setText("Aucune couverture : ajustez les heures de présence ou les buffers.")
        else:
            self.summary.setText(f"Couverture avant déduction des pauses : {format_time(first)} à {format_time(last)}\nPrésence totale : {format_duration(max(0, self.end.value() - self.start.value()))}")
            try:
                candidate = deepcopy(self.source)
                candidate.start, candidate.end = self.start.value(), self.end.value()
                candidate.buffer_before, candidate.buffer_after = self.before.value(), self.after.value()
                candidate.before_paid, candidate.after_paid = self.before_paid.isChecked(), self.after_paid.isChecked()
                candidate.breaks = self.breaks.values(candidate.start, candidate.end)
                self.summary.setText(self.summary.text()+f"\nHeures rémunérées : {format_duration(paid_minutes(candidate))}")
            except ValueError as error:
                self.summary.setText(str(error))

    def build_item(self):
        shift = deepcopy(self.source)
        shift.educator_id = self.educator.currentData()
        shift.group_id = self.group.currentData()
        if not shift.educator_id or not shift.group_id:
            raise ValueError("Choisissez une éducatrice pour ce quart.")
        shift.day = self.day.currentIndex()
        shift.start, shift.end = self.start.value(), self.end.value()
        shift.buffer_before, shift.buffer_after = self.before.value(), self.after.value()
        if shift.start + shift.buffer_before >= shift.end - shift.buffer_after:
            raise ValueError("La fin de couverture doit être après son début. Vérifiez les heures et les buffers.")
        shift.before_paid, shift.after_paid = self.before_paid.isChecked(), self.after_paid.isChecked()
        shift.breaks = self.breaks.values(shift.start, shift.end)
        shift.locked = self.locked.isChecked()
        return shift


class ActivityDialog(EditorDialog):
    def __init__(self, week, activity=None, day=0, start=420, group_id="", parent=None):
        super().__init__("Modifier l'activité" if activity else "Ajouter une activité", existing=activity is not None, parent=parent)
        self.source = deepcopy(activity) if activity else Activity(id=new_id(), name="", group_id=group_id, day=day, start=start, end=min(start + 60, 1440))
        activity = self.source
        form = self.add_page("Activité")
        self.name = QLineEdit(activity.name)
        self.name.setPlaceholderText("Ex. Jeux libres, Dîner, Bricolage…")
        self.group = QComboBox()
        self.group.addItem("Choisir un groupe", "")
        for group in week.groups:
            self.group.addItem(group.name, group.id)
        self.group.setCurrentIndex(max(0, self.group.findData(activity.group_id)))
        self.day = QComboBox()
        self.day.addItems([week.day_label(0)] if week.planning_date else DAYS)
        self.day.setCurrentIndex(activity.day)
        self.start, self.end = MinuteEdit(activity.start), MinuteEdit(activity.end)
        self.room = QComboBox()
        self.room.addItem("Choisir un lieu", "")
        for room in week.rooms:
            self.room.addItem(room.name + (" · extérieur" if room.outdoor else ""), room.id)
        self.room.setCurrentIndex(max(0, self.room.findData(activity.room_id)))
        self.notes = QTextEdit(activity.notes)
        self.notes.setMaximumHeight(130)
        self.compatible = check("Peut se superposer à une autre activité compatible du groupe", activity.compatible)
        form.addRow("Nom de l'activité", self.name)
        form.addRow("Groupe", self.group)
        form.addRow("Journée", self.day)
        form.addRow("Début", self.start)
        form.addRow("Fin", self.end)
        form.addRow("Lieu", self.room)
        form.addRow("Notes", self.notes)
        form.addRow(self.compatible)
        form.addRow(note("Déplacer cette activité ou changer son lieu conserve les heures des éducatrices. La couverture est calculée à partir de leurs quarts exacts."))
        form = self.add_page("Responsables")
        self.responsibles = QListWidget()
        for ed in week.educators:
            if ed.active or ed.id in activity.responsible_ids:
                item = QListWidgetItem(ed.name)
                item.setData(Qt.ItemDataRole.UserRole, ed.id)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked if ed.id in activity.responsible_ids else Qt.CheckState.Unchecked)
                self.responsibles.addItem(item)
        form.addRow(note("Ne cochez personne pour déterminer automatiquement les responsables selon les affectations du groupe. Si vous choisissez des responsables, leurs présences réelles seront vérifiées."))
        form.addRow(self.responsibles)

    def build_item(self):
        activity = deepcopy(self.source)
        activity.name = self.require_name(self.name, "Le nom de l'activité")
        activity.group_id = self.group.currentData()
        activity.room_id = self.room.currentData()
        if not activity.group_id:
            raise ValueError("Choisissez le groupe de l'activité.")
        if not activity.room_id:
            raise ValueError("Choisissez un lieu. Vous pouvez créer un lieu extérieur dans la gestion des locaux.")
        activity.day = self.day.currentIndex()
        activity.start, activity.end = self.start.value(), self.end.value()
        if activity.start >= activity.end:
            raise ValueError("La fin de l'activité doit être après son début.")
        activity.notes = self.notes.toPlainText().strip()
        activity.compatible = self.compatible.isChecked()
        activity.responsible_ids = [self.responsibles.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.responsibles.count()) if self.responsibles.item(i).checkState() == Qt.CheckState.Checked]
        return activity


class SettingsDialog(EditorDialog):
    def __init__(self, week, parent=None):
        super().__init__("Paramètres de planification", parent=parent)
        self.source = deepcopy(week.settings)
        settings = self.source
        form = self.add_page("Ouverture et relèves")
        self.open_time = MinuteEdit(settings.open_minute)
        self.close_time = MinuteEdit(settings.close_minute)
        self.opening_buffer = integer(settings.opening_buffer, 10, 240, " min")
        self.closing_buffer = integer(settings.closing_buffer, 5, 240, " min")
        self.handover = integer(settings.handover_minutes, 15, 240, " min")
        from ..planning import service_ratio
        self.staff_ratio = integer(service_ratio(week), 1, 1000, " enfants / éducatrice")
        form.addRow("Ratio d’encadrement", self.staff_ratio)
        form.addRow("Ouverture aux enfants", self.open_time)
        form.addRow("Fermeture aux enfants", self.close_time)
        form.addRow("Préparation avant ouverture", self.opening_buffer)
        form.addRow("Fermeture après le départ", self.closing_buffer)
        form.addRow("Chevauchement de relève", self.handover)
        form.addRow(note("Règles initiales : accueil de 07:00 à 17:30, deux éducatrices dès 06:50 et jusqu'à 17:35. Le service de garde conserve au moins deux éducatrices simultanément pendant l’accueil. La relève nécessite au moins 15 minutes de présence commune."))
        form = self.add_page("Pauses automatiques")
        self.break_after = MinuteEdit(getattr(settings, "break_after_minutes", 0), duration=True)
        self.break_minutes = integer(getattr(settings, "break_minutes", 0), 0, 180, " min")
        self.break_paid = check("Les pauses générées sont rémunérées", getattr(settings, "break_paid", False))
        form.addRow("Couverture continue avant pause (h:min)", self.break_after)
        form.addRow("Durée de la pause", self.break_minutes)
        form.addRow(self.break_paid)
        form.addRow(note("Une durée de pause à zéro désactive la règle automatique. Sinon, chaque séquence de couverture entre les pauses doit respecter le délai choisi. Les buffers sont exclus de ce calcul."))
        form = self.add_page("Priorités et calendrier")
        self.seniority_weight = integer(settings.seniority_weight, 0, 1000)
        self.preference_weight = integer(settings.preference_weight, 0, 1000)
        self.target_weight = integer(settings.target_weight, 0, 1000)
        self.max_daily = MinuteEdit(getattr(settings, "max_daily_minutes", 720), duration=True)
        self.snap = QComboBox()
        for label, value in [("Sans magnétisme (précision à la minute)", 0), ("1 minute", 1), ("5 minutes", 5), ("15 minutes", 15)]:
            self.snap.addItem(label, value)
        self.snap.setCurrentIndex(max(0, self.snap.findData(settings.snap_minutes)))
        form.addRow("Poids de l'ancienneté", self.seniority_weight)
        if not week.planning_date:
            form.addRow("Poids des groupes préférés", self.preference_weight)
        else:
            self.preference_weight.setParent(self)
            self.preference_weight.hide()
        form.addRow("Poids des objectifs d'heures", self.target_weight)
        form.addRow("Présence quotidienne maximale (h:min)", self.max_daily)
        form.addRow("Magnétisme du calendrier", self.snap)
        form.addRow(note("Ces poids règlent les préférences de génération. Une valeur plus élevée donne davantage de priorité. Les contraintes obligatoires restent prioritaires dans tous les cas."))

    def build_item(self):
        settings = deepcopy(self.source)
        settings.open_minute, settings.close_minute = self.open_time.value(), self.close_time.value()
        settings.opening_buffer = self.opening_buffer.value()
        settings.closing_buffer = self.closing_buffer.value()
        settings.handover_minutes = self.handover.value()
        if not settings.opening_buffer <= settings.open_minute < settings.close_minute <= 1440 - settings.closing_buffer:
            raise ValueError("Vérifiez les heures d'ouverture et de fermeture : les buffers doivent rester dans la même journée.")
        settings.break_after_minutes = self.break_after.value()
        settings.break_minutes = self.break_minutes.value()
        settings.break_paid = self.break_paid.isChecked()
        if settings.break_minutes > 0 and settings.break_after_minutes <= 0:
            raise ValueError("Renseignez un délai avant pause supérieur à zéro, ou mettez la durée de pause à zéro pour désactiver la règle.")
        settings.seniority_weight = self.seniority_weight.value()
        settings.preference_weight = self.preference_weight.value()
        settings.target_weight = self.target_weight.value()
        settings.max_daily_minutes = self.max_daily.value()
        if settings.max_daily_minutes <= 0:
            raise ValueError("La présence quotidienne maximale doit être supérieure à zéro.")
        settings.snap_minutes = self.snap.currentData()
        return settings
