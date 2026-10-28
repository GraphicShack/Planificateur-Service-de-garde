from PySide6.QtCore import QDate,Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QWidget,QVBoxLayout
from gardeplan.app import STYLE
from gardeplan.ui.date_field import DateField


def test_styled_date_remains_visible_and_editable_without_monthly_calendar(qapp):
    parent=QWidget();parent.setStyleSheet(STYLE)
    field=DateField();layout=QVBoxLayout(parent);layout.addWidget(field)
    field.setDate(QDate(2026,10,28));parent.show();qapp.processEvents()
    try:
        assert field.lineEdit().width()>150
        assert '28 octobre 2026' in field.text()
        assert not field.calendarPopup() and field.height()>=44
        field.setCurrentSection(field.Section.DaySection)
        QTest.keyClick(field,Qt.Key.Key_Up);qapp.processEvents()
        assert field.date()==QDate(2026,10,29)
        assert '29 octobre 2026' in field.text()
    finally:parent.close();parent.deleteLater();qapp.processEvents()
