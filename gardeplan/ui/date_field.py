"""A plain French date field: editable sections, without a monthly calendar."""
from PySide6.QtCore import QDate, QLocale
from PySide6.QtWidgets import QDateEdit, QAbstractSpinBox
from .theme import DATE_STYLE


class DateField(QDateEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._unavailable = set()
        self._last_valid = self.date()
        self.setObjectName("dateSelector")
        self.setLocale(QLocale(QLocale.Language.French, QLocale.Country.Canada))
        self.setDisplayFormat("dddd d MMMM yyyy")
        self.setCalendarPopup(False)
        # Qt 6.12 collapses the styled edit field to one pixel with NoButtons.
        # Keep the native edit geometry and hide its arrows through the style.
        self.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.UpDownArrows)
        self.setMinimumHeight(48)
        self.setAccessibleName("Date de la journée. Modifier le jour, le mois ou l’année au clavier.")
        self.setStyleSheet(DATE_STYLE+"QDateEdit#dateSelector{font-size:16px;color:#203D32;background:white;border:1px solid #64786D;border-radius:8px;padding:8px 12px;} QDateEdit#dateSelector:focus{border:2px solid #173F32;padding:7px 11px;}")
        self.setStyleSheet(self.styleSheet()+"QDateEdit#dateSelector::up-button,QDateEdit#dateSelector::down-button{width:0;height:0;} QDateEdit#dateSelector::up-arrow,QDateEdit#dateSelector::down-arrow{image:none;}")
        self.lineEdit().setTextMargins(12,0,12,0)
        self.dateChanged.connect(self._check_date)
        self.ensurePolished()
        self._fit_text()

    def _fit_text(self):
        width = max(self.fontMetrics().horizontalAdvance(self.locale().toString(QDate(2026, month, day), self.displayFormat())) for month in range(1, 13) for day in range(21, 28))
        self.setMinimumWidth(width+56)

    def isDateAvailable(self, value):
        return value.isValid() and self.minimumDate() <= value <= self.maximumDate() and value.toJulianDay() not in self._unavailable

    def setUnavailableDates(self, values):
        self._unavailable = {v.toJulianDay() for v in values}

    def setDate(self, value):
        if not self.isDateAvailable(value):
            return False
        super().setDate(value)
        self._last_valid = self.date()
        return True

    def _check_date(self, value):
        if not self.isDateAvailable(value):
            self.blockSignals(True)
            super().setDate(self._last_valid)
            self.blockSignals(False)
            return
        self._last_valid = value

    def textFromDateTime(self, value):
        text = self.locale().toString(value.date(), self.displayFormat())
        return text[:1].upper()+text[1:]
