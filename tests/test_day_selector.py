"""Readable date controls, keyboard interaction and planner integration."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
from PySide6.QtCore import Qt, QDate, QPoint
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QPushButton

from gardeplan.ui.day_selector import DayPicker, DaySelector, full_date
from gardeplan.ui.theme import TEXT, SECONDARY, SURFACE, SOFT, FOREST, HOVER, contrast
from test_daily_ui import day_window


@pytest.fixture
def picker(qapp):
    dialog = DayPicker(QDate(2026, 10, 26), today=QDate(2026, 10, 26))
    dialog.resize(540, 720)
    dialog.show()
    qapp.processEvents()
    yield dialog
    dialog.close()
    dialog.deleteLater()
    qapp.processEvents()


def cell_for(picker, value):
    return next(cell for cell in picker.cells if cell.value == value)


def test_all_date_text_contrasts_exceed_aa():
    for foreground, background in ((TEXT, SURFACE), (TEXT, HOVER), (SECONDARY, SURFACE),
                                  (SECONDARY, SOFT), ("#FFFFFF", FOREST)):
        assert contrast(foreground, background) >= 4.5


def test_grid_is_monday_first_aligned_large_and_readable(picker):
    assert len(picker.cells) == 42
    assert picker.cells[0].value.dayOfWeek() == 1
    for row in range(6):
        cells = picker.cells[row*7:(row+1)*7]
        assert len({cell.y() for cell in cells}) == 1
        assert max(cell.width() for cell in cells)-min(cell.width() for cell in cells) <= 1
        assert all(cell.width() >= 44 and cell.height() >= 44 for cell in cells)
        assert all(cell.font().pixelSize() >= 16 for cell in cells)
    assert picker.month.font().pixelSize() > 16
    assert picker.year.font().pixelSize() > 16
    assert picker.previous.width() >= 44 and picker.next.width() >= 44


def test_selected_today_keeps_its_point_and_accessible_identity(picker, qapp):
    cell = cell_for(picker, QDate(2026, 10, 26))
    picker.month.setFocus()
    qapp.processEvents()
    image = cell.grab().toImage()
    ratio = image.devicePixelRatio()
    assert image.pixelColor(round(cell.width()/2*ratio), round((cell.height()-8)*ratio)).name() == "#ffffff"
    assert cell.isChecked()
    assert "aujourd’hui" in cell.accessibleName()
    assert sum(c.isChecked() for c in picker.cells) == 1


def test_unavailable_day_is_barred_and_cannot_be_chosen(qapp):
    dialog = DayPicker(QDate(2026, 10, 26), unavailable=[QDate(2026, 10, 29)])
    dialog.show()
    qapp.processEvents()
    cell = cell_for(dialog, QDate(2026, 10, 29))
    assert not cell.isEnabled()
    assert "indisponible" in cell.accessibleName()
    barred = cell.grab().toImage()
    cell.setEnabled(True)
    plain = cell.grab().toImage()
    assert barred != plain
    chosen = []
    dialog.dateChosen.connect(chosen.append)
    dialog.choose(QDate(2026, 10, 29))
    assert chosen == []
    dialog.close()
    dialog.deleteLater()


def test_keyboard_crosses_month_and_year_then_selects_once(qapp):
    dialog = DayPicker(QDate(2026, 12, 31))
    dialog.show()
    qapp.processEvents()
    chosen = []
    dialog.dateChosen.connect(chosen.append)
    QTest.keyClick(cell_for(dialog, QDate(2026, 12, 31)), Qt.Key.Key_Right)
    assert dialog.cursor == QDate(2027, 1, 1)
    assert dialog.shown == QDate(2027, 1, 1)
    assert dialog.selected == QDate(2026, 12, 31)
    QTest.keyClick(cell_for(dialog, dialog.cursor), Qt.Key.Key_Return)
    assert chosen == [QDate(2027, 1, 1)]
    dialog.deleteLater()


def test_page_keys_and_year_field_handle_leap_year(picker):
    QTest.keyClick(cell_for(picker, picker.cursor), Qt.Key.Key_PageDown,
                   Qt.KeyboardModifier.ControlModifier)
    assert picker.shown.year() == 2027
    picker.year.setValue(2028)
    picker.month.setCurrentIndex(1)
    assert cell_for(picker, QDate(2028, 2, 29)).isEnabled()
    picker.year.setValue(2027)
    assert not any(c.current_month and c.value.day() == 29 for c in picker.cells)


def test_date_click_and_cancel_preserve_single_selection_without_today_button(qapp):
    dialog = DayPicker(QDate(2026, 10, 26), today=QDate(2026, 10, 28))
    chosen = []
    dialog.dateChosen.connect(chosen.append)
    assert not any(button.text() == "Aujourd’hui" for button in dialog.findChildren(QPushButton))
    cell_for(dialog, QDate(2026, 10, 28)).click()
    assert chosen == [QDate(2026, 10, 28)]
    dialog.deleteLater()
    dialog = DayPicker(QDate(2026, 10, 26))
    dialog.dateChosen.connect(chosen.append)
    dialog.reject()
    assert chosen == [QDate(2026, 10, 28)]
    dialog.deleteLater()


def test_selector_preserves_date_limits_and_full_french_date(qapp):
    field = DaySelector()
    field.setDate(QDate(2026, 10, 26))
    field.setDateRange(QDate(2026, 10, 20), QDate(2026, 10, 30))
    assert not field.setDate(QDate(2026, 10, 31))
    assert field.date() == QDate(2026, 10, 26)
    assert field.text() == "Lundi 26 octobre 2026"
    field.show()
    QApplication.processEvents()
    assert field.width() >= field.fontMetrics().horizontalAdvance(field.text())+40
    assert field.font().pixelSize() >= 16
    field.close()
    field.deleteLater()


def test_hover_and_keyboard_focus_are_visible(picker, qapp):
    cell = cell_for(picker, QDate(2026, 10, 27))
    picker.month.setFocus()
    QTest.mouseMove(picker.previous, picker.previous.rect().center())
    qapp.processEvents()
    before = cell.grab().toImage()
    QTest.mouseMove(cell, cell.rect().center())
    qapp.processEvents()
    hover = cell.grab().toImage()
    assert hover != before
    cell.setFocus()
    qapp.processEvents()
    assert cell.grab().toImage() != hover


def test_popup_small_size_scrolls_without_shrinking_targets(picker, qapp):
    picker.resize(360, 330)
    qapp.processEvents()
    assert picker.width() <= 360 and picker.height() <= 330
    assert all(cell.width() >= 44 and cell.height() >= 44 for cell in picker.cells)
    assert all(cell.font().pixelSize() >= 16 for cell in picker.cells)
    assert picker.scroll.verticalScrollBar().maximum() > 0
    assert picker.close_button.isVisible()


def test_popup_date_updates_planning_and_reopens_saved_day(day_window, monkeypatch):
    original = day_window.week.to_dict()
    assert not day_window.week_date.calendarPopup()
    day_window.week_date.setDate(QDate(2026, 10, 29))
    assert day_window.week.planning_date == "2026-10-29"
    assert day_window.calendar.week.planning_date == "2026-10-29"
    day_window.week_date.setDate(QDate(2026, 10, 28))
    assert day_window.week.to_dict() == original


def test_enter_opens_date_picker_and_escape_closes_without_change(qapp, monkeypatch):
    field = DaySelector()
    field.setDate(QDate(2026, 10, 26))
    opened = []
    def inspect(dialog):
        opened.append(dialog.selected)
        return QDialog.DialogCode.Rejected
    monkeypatch.setattr(DayPicker, "exec", inspect)
    QTest.keyClick(field, Qt.Key.Key_Return)
    assert opened == [QDate(2026, 10, 26)]
    assert field.date() == QDate(2026, 10, 26)
    field.deleteLater()
    dialog = DayPicker(QDate(2026, 10, 26))
    dialog.show()
    qapp.processEvents()
    QTest.keyClick(cell_for(dialog, dialog.cursor), Qt.Key.Key_Escape)
    assert not dialog.isVisible()
    assert dialog.selected == QDate(2026, 10, 26)
    dialog.deleteLater()


def test_save_failure_reverts_date_label_and_preserves_unsaved_plan(day_window, monkeypatch):
    day_window.commit(lambda plan: plan.day_names.__setitem__(0, "À garder"))
    def fail(*args):
        raise OSError("Disque plein")
    monkeypatch.setattr(day_window.repo, "save", fail)
    day_window.week_date.setDate(QDate(2026, 10, 29))
    assert day_window.week_date.date() == QDate(2026, 10, 28)
    assert day_window.week.planning_date == "2026-10-28"
    assert day_window.week.day_names[0] == "À garder" and day_window.dirty


def test_small_planner_wraps_controls_and_keeps_date_untruncated(day_window, qapp):
    day_window.resize(720, 600)
    day_window.show()
    qapp.processEvents()
    assert day_window.width() <= 720
    assert day_window.sidebar.isHidden()
    assert day_window.week_date.text() == full_date(day_window.week_date.date())
    assert day_window.week_date.width() >= day_window.week_date.fontMetrics().horizontalAdvance(day_window.week_date.text())+40
    for widget in (day_window.week_date, day_window.previous_day_button,
                   day_window.next_day_button, day_window.folder_button):
        top = widget.mapTo(day_window, QPoint())
        assert top.x() >= 0 and top.x()+widget.width() <= day_window.width()
        assert widget.height() >= 44


def test_scale_200_percent_keeps_readable_targets_in_small_panel():
    code = """
import json
from PySide6.QtWidgets import QApplication, QDialog
from PySide6.QtCore import QDate
from gardeplan.ui.day_selector import DayPicker
app=QApplication([])
picker=DayPicker(QDate(2026,10,26))
picker.resize(360,330)
picker.show()
for _ in range(4): app.processEvents()
assert picker.width() <= 360 and picker.height() <= 330
assert min(c.width() for c in picker.cells) >= 44
assert min(c.height() for c in picker.cells) >= 44
assert min(c.font().pixelSize() for c in picker.cells) >= 16
assert picker.devicePixelRatioF() >= 1.9
print(json.dumps({'dpr':picker.devicePixelRatioF(),'width':picker.width()}))
picker.close()
"""
    environment = dict(os.environ, QT_QPA_PLATFORM="offscreen", QT_SCALE_FACTOR="2")
    result = subprocess.run([sys.executable, "-c", code], cwd=Path(__file__).resolve().parents[1],
                            env=environment, text=True, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stdout+result.stderr
    assert json.loads(result.stdout.splitlines()[-1])["dpr"] >= 1.9
