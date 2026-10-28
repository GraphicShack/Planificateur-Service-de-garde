"""Single-date selection with readable, accessible 44+ pixel day targets."""
from PySide6.QtCore import Qt, QDate, QEvent, QLocale, QSize, QRectF, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialog, QGridLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QSpinBox, QVBoxLayout, QWidget, QSizePolicy,
)

from .theme import FOREST, TEXT, SECONDARY, BORDER, SURFACE, SOFT, HOVER, FOCUS, DATE_STYLE
from .visuals import icon
from .flow_layout import FlowLayout

LOCALE = QLocale(QLocale.Language.French, QLocale.Country.Canada)


def full_date(value):
    result = LOCALE.toString(value, "dddd d MMMM yyyy")
    return result[:1].upper()+result[1:]


class DayCell(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.value = QDate()
        self.current_month = self.selected = self.today = False
        self.setCheckable(True)
        self.setAutoDefault(False)
        self.setMinimumSize(44, 44)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(56)
        font = self.font()
        font.setPixelSize(16)
        self.setFont(font)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)

    def sizeHint(self):
        return QSize(48, 56)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        background = FOREST if self.selected else HOVER if self.underMouse() and self.isEnabled() else SURFACE if self.current_month else SOFT
        foreground = "#FFFFFF" if self.selected else TEXT if self.current_month else SECONDARY
        painter.setBrush(QColor(background))
        painter.setPen(QPen(QColor(FOREST if self.today else BORDER), 2 if self.today else 1))
        painter.drawRoundedRect(rect, 7, 7)
        if self.today:
            painter.setPen(QPen(QColor("#FFFFFF" if self.selected else FOREST), 1.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect.adjusted(3, 3, -3, -3), 4, 4)
        font = QFont(self.font())
        font.setBold(self.selected or self.today)
        painter.setFont(font)
        painter.setPen(QColor(foreground))
        if self.current_month:
            painter.drawText(rect.adjusted(0, -2 if self.today else 0, 0, -2 if self.today else 0), Qt.AlignmentFlag.AlignCenter, self.text())
        else:
            painter.drawText(QRectF(rect.left(), rect.top()+1, rect.width(), 24), Qt.AlignmentFlag.AlignCenter, self.text())
            painter.drawText(QRectF(rect.left(), rect.top()+23, rect.width(), 22), Qt.AlignmentFlag.AlignCenter, LOCALE.monthName(self.value.month(), QLocale.FormatType.ShortFormat))
        if self.today:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(foreground))
            painter.drawEllipse(QRectF(rect.center().x()-2, rect.bottom()-8, 4, 4))
        if not self.isEnabled():
            painter.setPen(QPen(QColor(SECONDARY), 2))
            painter.drawLine(int(rect.left()+10), int(rect.bottom()-10), int(rect.right()-10), int(rect.top()+10))
        if self.hasFocus():
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(FOCUS), 2, Qt.PenStyle.DashLine))
            painter.drawRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 8, 8)


class DayPicker(QDialog):
    dateChosen = Signal(QDate)

    def __init__(self, selected, parent=None, *, minimum=None, maximum=None, unavailable=(), today=None):
        super().__init__(parent)
        self.setObjectName("dayPicker")
        self.setWindowTitle("Choisir une journée")
        self.setStyleSheet(DATE_STYLE)
        self.selected = QDate(selected)
        self.cursor = QDate(selected)
        self.shown = QDate(selected.year(), selected.month(), 1)
        self.minimum = minimum or QDate(1752, 9, 14)
        self.maximum = maximum or QDate(9999, 12, 31)
        self.unavailable = {value.toJulianDay() for value in unavailable}
        self.today = today or QDate.currentDate()
        self._updating = False
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        content = QWidget()
        content.setStyleSheet("background:white;")
        body = QVBoxLayout(content)
        body.setContentsMargins(12, 12, 12, 12)
        body.setSpacing(12)
        heading = QHBoxLayout()
        heading.setSpacing(8)
        self.previous = self._arrow("chevron-left", "Mois précédent", lambda: self.change_month(-1))
        self.next = self._arrow("chevron-right", "Mois suivant", lambda: self.change_month(1))
        heading.addWidget(self.previous)
        self.month = QComboBox()
        self.month.setAccessibleName("Mois")
        self.month.setMinimumWidth(140)
        for index in range(1, 13):
            self.month.addItem(LOCALE.monthName(index), index)
        self.month.currentIndexChanged.connect(self._header_changed)
        self.year = QSpinBox()
        self.year.setRange(self.minimum.year(), self.maximum.year())
        self.year.setButtonSymbols(QSpinBox.ButtonSymbols.UpDownArrows)
        self.year.setAccessibleName("Année")
        self.year.setMinimumWidth(92)
        self.year.valueChanged.connect(self._header_changed)
        month_year = QWidget()
        fields = FlowLayout(month_year, spacing=8)
        fields.addWidget(self.month)
        fields.addWidget(self.year)
        heading.addWidget(month_year, 1)
        heading.addWidget(self.next)
        root.addLayout(heading)
        grid = QGridLayout()
        grid.setHorizontalSpacing(4)
        grid.setVerticalSpacing(4)
        for column, name in enumerate(("Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim")):
            label = QLabel(name)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setMinimumWidth(44)
            label.setStyleSheet("font-size:16px;font-weight:600;color:"+TEXT)
            grid.addWidget(label, 0, column)
        self.cells = []
        for index in range(42):
            cell = DayCell()
            cell.clicked.connect(lambda checked=False, index=index: self.choose(self.cells[index].value))
            cell.installEventFilter(self)
            self.cells.append(cell)
            grid.addWidget(cell, index//7+1, index % 7)
        body.addLayout(grid)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setAccessibleName("Journée choisie")
        body.addWidget(self.summary)
        legend = QLabel("Aujourd’hui : contour et point.\nJour barré : indisponible.\nFlèches : se déplacer · Entrée : choisir\nPage préc./suiv. : mois · Ctrl + Page : année")
        legend.setWordWrap(True)
        body.addWidget(legend)
        footer = QHBoxLayout()
        self.close_button = QPushButton("Fermer")
        self.close_button.setMinimumHeight(44)
        self.close_button.setAutoDefault(False)
        self.close_button.clicked.connect(self.reject)
        footer.addStretch()
        footer.addWidget(self.close_button)
        body.addStretch()
        scroll.setWidget(content)
        root.addWidget(scroll, 1)
        root.addLayout(footer)
        self.scroll = scroll
        screen = QApplication.primaryScreen()
        available = screen.availableGeometry() if screen else None
        self.resize(min(540, available.width()-24) if available else 540,
                    min(700, available.height()-32) if available else 700)
        self.refresh()
        self.focus_timer = QTimer(self)
        self.focus_timer.setSingleShot(True)
        self.focus_timer.timeout.connect(self.focus_cursor)

    def showEvent(self, event):
        super().showEvent(event)
        self.focus_timer.start(0)

    def _arrow(self, name, label, callback):
        button = QPushButton()
        button.setIcon(icon(name, size=24, color=TEXT))
        button.setIconSize(QSize(24, 24))
        button.setFixedSize(48, 48)
        button.setAccessibleName(label)
        button.setToolTip(label)
        button.setAutoDefault(False)
        button.clicked.connect(callback)
        return button

    def available(self, value):
        return value.isValid() and self.minimum <= value <= self.maximum and value.toJulianDay() not in self.unavailable

    def refresh(self):
        self._updating = True
        self.month.setCurrentIndex(self.shown.month()-1)
        self.year.setValue(self.shown.year())
        self._updating = False
        if not self.available(self.cursor):
            for day in range(1, self.shown.daysInMonth()+1):
                candidate = QDate(self.shown.year(), self.shown.month(), day)
                if self.available(candidate):
                    self.cursor = candidate
                    break
        self.summary.setText("Journée choisie : "+full_date(self.selected))
        self.previous.setEnabled(self.shown.addMonths(-1).daysTo(self.maximum) >= 0 and self.shown.addDays(-1) >= self.minimum)
        self.next.setEnabled(self.shown.addMonths(1) <= self.maximum)
        start = self.shown.addDays(1-self.shown.dayOfWeek())
        for index, cell in enumerate(self.cells):
            value = start.addDays(index)
            cell.value = value
            cell.setText(str(value.day()))
            cell.current_month = value.month() == self.shown.month()
            cell.selected = value == self.selected
            cell.today = value == self.today
            cell.setChecked(cell.selected)
            cell.setEnabled(self.available(value))
            cell.setFocusPolicy(Qt.FocusPolicy.StrongFocus if value == self.cursor else Qt.FocusPolicy.ClickFocus)
            description = (" · journée choisie" if cell.selected else "")+(" · aujourd’hui" if cell.today else "")+(" · indisponible" if not cell.isEnabled() else "")
            cell.setAccessibleName(full_date(value)+description)
            cell.update()

    def focus_cursor(self):
        for cell in self.cells:
            if cell.value == self.cursor and cell.isEnabled():
                cell.setFocus(Qt.FocusReason.OtherFocusReason)
                self.scroll.ensureWidgetVisible(cell)
                return

    def _header_changed(self, *args):
        if not self._updating:
            month = QDate(self.year.value(), self.month.currentIndex()+1, 1)
            self.shown = month
            self.cursor = QDate(month.year(), month.month(), min(self.cursor.day(), month.daysInMonth()))
            self.refresh()

    def change_month(self, amount):
        target = self.shown.addMonths(amount)
        if target.addMonths(1).addDays(-1) < self.minimum or target > self.maximum:
            return
        self.shown = target
        self.cursor = QDate(target.year(), target.month(), min(self.cursor.day(), target.daysInMonth()))
        self.refresh()

    def choose(self, value):
        if self.available(value):
            self.selected = QDate(value)
            self.refresh()
            self.dateChosen.emit(self.selected)
            self.accept()

    def eventFilter(self, watched, event):
        if watched in self.cells and event.type() == QEvent.Type.KeyPress:
            key = event.key()
            steps = {Qt.Key.Key_Left: -1, Qt.Key.Key_Right: 1, Qt.Key.Key_Up: -7, Qt.Key.Key_Down: 7}
            target = None
            if key in steps:
                target = watched.value.addDays(steps[key])
            elif key in (Qt.Key.Key_PageUp, Qt.Key.Key_PageDown):
                direction = -1 if key == Qt.Key.Key_PageUp else 1
                target = watched.value.addYears(direction) if event.modifiers() & Qt.KeyboardModifier.ControlModifier else watched.value.addMonths(direction)
            elif key == Qt.Key.Key_Home:
                target = watched.value.addDays(1-watched.value.dayOfWeek())
            elif key == Qt.Key.Key_End:
                target = watched.value.addDays(7-watched.value.dayOfWeek())
            elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
                self.choose(watched.value)
                return True
            if target is not None:
                direction = 1 if target >= watched.value else -1
                while self.minimum <= target <= self.maximum and not self.available(target):
                    target = target.addDays(direction)
                if self.available(target):
                    self.cursor = target
                    self.shown = QDate(target.year(), target.month(), 1)
                    self.refresh()
                    self.focus_cursor()
                return True
        return super().eventFilter(watched, event)


class DaySelector(QPushButton):
    dateChanged = Signal(QDate)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._date = QDate.currentDate()
        self._minimum, self._maximum = QDate(1752, 9, 14), QDate(9999, 12, 31)
        self.unavailable = []
        self.setObjectName("dateSelector")
        self.setStyleSheet(DATE_STYLE)
        self.setMinimumHeight(48)
        self.setIcon(icon("calendar", size=22, color=TEXT))
        self.setIconSize(QSize(22, 22))
        self.setAccessibleName("Choisir la journée du planning")
        self.clicked.connect(self.open_picker)
        self._update_text()

    def _update_text(self):
        self.setText(full_date(self._date))
        self.ensurePolished()
        self.setAccessibleDescription("Journée choisie : "+self.text()+". Entrée ou espace pour ouvrir le calendrier.")
        # Reserve the full French date instead of eliding or shrinking it.
        self.setMinimumWidth(self.fontMetrics().horizontalAdvance(self.text())+62)
        self.updateGeometry()

    def date(self):
        return QDate(self._date)

    def displayFormat(self):
        return "dddd d MMMM yyyy"

    def minimumDate(self):
        return QDate(self._minimum)

    def maximumDate(self):
        return QDate(self._maximum)

    def isDateAvailable(self, value):
        return value.isValid() and self._minimum <= value <= self._maximum and value not in self.unavailable

    def setDate(self, value):
        if not self.isDateAvailable(value):
            return False
        if value != self._date:
            self._date = QDate(value)
            self._update_text()
            self.dateChanged.emit(self.date())
        return True

    def setDateRange(self, minimum, maximum):
        if minimum > maximum:
            raise ValueError("La date minimale doit précéder la date maximale.")
        self._minimum, self._maximum = minimum, maximum
        self.setDate(max(minimum, min(self._date, maximum)))

    def open_picker(self):
        picker = DayPicker(self._date, self, minimum=self._minimum, maximum=self._maximum, unavailable=self.unavailable)
        picker.dateChosen.connect(self.setDate)
        picker.exec()
        picker.deleteLater()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_F4) or (
                event.key() == Qt.Key.Key_Down and event.modifiers() & Qt.KeyboardModifier.AltModifier):
            self.open_picker()
            event.accept()
        else:
            super().keyPressEvent(event)
