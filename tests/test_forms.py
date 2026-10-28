"""Functional Qt editors: real widgets and acceptance, without mutating sources."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from copy import deepcopy
import pytest
pytest.importorskip('PySide6')
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QColor, QPalette, QValidator
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QDialogButtonBox, QMessageBox, QTabWidget, QWidget
from gardeplan.models import Activity, Break, GroupPeriod, Room, Window, paid_minutes
from gardeplan.ui.forms import (
    MinuteEdit, IntervalsEditor, BreaksEditor, EducatorDialog, GroupDialog,
    RoomDialog, ShiftDialog, ActivityDialog, SettingsDialog,
)


@pytest.fixture
def track_dialog(qapp):
    widgets = []
    def track(widget):
        widgets.append(widget)
        return widget
    yield track
    for widget in widgets:
        widget.close()
        widget.deleteLater()
    qapp.processEvents()


def save(dialog):
    """Press the actual save button and assert the public result contract."""
    dialog.show()
    QApplication.processEvents()
    buttons = dialog.findChild(QDialogButtonBox)
    button = next(b for b in buttons.buttons()
                  if buttons.buttonRole(b) == QDialogButtonBox.ButtonRole.AcceptRole)
    QTest.mouseClick(button, Qt.MouseButton.LeftButton)
    assert dialog.result() == QDialog.DialogCode.Accepted
    assert dialog.result_item() is not None
    return dialog.result_item()


def test_minute_editor_preserves_713_and_long_weekly_duration(qapp, track_dialog):
    clock = track_dialog(MinuteEdit(0))
    clock.lineEdit().setText('07:13')
    clock.interpretText()
    assert clock.value() == 433
    assert clock.text() == '07:13'
    duration = track_dialog(MinuteEdit(0, duration=True))
    duration.lineEdit().setText('35:42')
    duration.interpretText()
    assert duration.value() == 2142
    assert duration.text() == '35:42'
    assert clock.validate('07:60', 5)[0] == QValidator.State.Invalid
    assert clock.validate('24:01', 5)[0] == QValidator.State.Invalid


def test_educator_dialog_all_profile_fields_and_source_unchanged(valid_week, track_dialog):
    original = deepcopy(valid_week.educators[0])
    dialog = track_dialog(EducatorDialog(valid_week, valid_week.educators[0]))
    dialog.name.setText('Sophie Gagnon')
    dialog.seniority.setValue(3)
    dialog.seniority_date.setText('2015-08-24')
    dialog.target.setValue(1857)
    dialog.guaranteed.setValue(1500)
    dialog.maximum.setValue(2200)
    dialog.color.color = '#123456'
    dialog.active.setChecked(False)
    dialog.preferences.item(0).setCheckState(Qt.CheckState.Checked)
    dialog.restrictions.setPlainText('Préférence pour les activités extérieures')
    dialog.absences.add_row(2, 433, 535)
    result = save(dialog)
    assert (result.name, result.seniority, result.seniority_date) == ('Sophie Gagnon', 3, '2015-08-24')
    assert (result.target_minutes, result.guaranteed_minutes, result.max_minutes) == (1857, 1500, 2200)
    assert result.color == '#123456'
    assert not result.active
    assert result.preferred_groups == ['g1']
    assert result.absences == [Window(2, 433, 535)]
    assert valid_week.educators[0] == original


def test_invalid_educator_stays_open_with_simple_warning(valid_week, track_dialog, monkeypatch):
    warnings = []
    monkeypatch.setattr(QMessageBox, 'warning', lambda *args: warnings.append(args[2]))
    dialog = track_dialog(EducatorDialog(valid_week))
    dialog.name.setText('')
    dialog.try_accept()
    assert warnings and 'obligatoire' in warnings[-1]
    assert dialog.result() != QDialog.DialogCode.Accepted
    dialog.name.setText('Sophie')
    dialog.guaranteed.setValue(3000)
    dialog.maximum.setValue(2400)
    dialog.try_accept()
    assert 'maximum' in warnings[-1]
    assert dialog.result_item() is None


def test_profile_stays_light_with_a_dark_parent(valid_week, track_dialog, qapp):
    from gardeplan.ui.theme import contrast
    parent = track_dialog(QWidget())
    dark = QPalette()
    for role in (QPalette.ColorRole.Window, QPalette.ColorRole.Base, QPalette.ColorRole.Button):
        dark.setColor(role, QColor("#111111"))
    dark.setColor(QPalette.ColorRole.Text, QColor("white"))
    parent.setPalette(dark)
    dialog = track_dialog(EducatorDialog(valid_week, parent=parent))
    dialog.show()
    qapp.processEvents()
    for widget in (dialog.name, dialog.target, dialog.restrictions, dialog.availability.table):
        palette = widget.palette()
        text = palette.color(QPalette.ColorRole.Text).name()
        base = palette.color(QPalette.ColorRole.Base).name()
        assert QColor(base).lightness() >= 240
        assert contrast(text, base) >= 4.5
        assert widget.font().pixelSize() >= 16
    assert not dialog.findChildren(QTabWidget)


def test_profile_sections_share_one_window_and_stack_on_small_screens(valid_week, track_dialog, qapp):
    dialog = track_dialog(EducatorDialog(valid_week))
    dialog.show()
    dialog.resize(1120, 960)
    for _ in range(3):
        qapp.processEvents()
    assert not dialog.profile_columns.stacked
    assert dialog.scroll.verticalScrollBar().maximum() == 0, (
        dialog.size(), dialog.scroll.viewport().size(), dialog.body.size(),
        dialog.profile_columns.left.size(), dialog.profile_columns.right.size())
    for widget in (dialog.name, dialog.seniority, dialog.target, dialog.maximum,
                   dialog.availability, dialog.absences, dialog.preferences, dialog.restrictions):
        assert widget.isVisible() and widget.window() is dialog
        position = widget.mapTo(dialog.scroll.viewport(), QPoint())
        assert position.y() >= 0
        assert position.y()+widget.height() <= dialog.scroll.viewport().height()
    dialog.resize(540, 600)
    for _ in range(3):
        qapp.processEvents()
    assert dialog.profile_columns.stacked
    assert dialog.scroll.horizontalScrollBar().maximum() == 0, (
        dialog.size(), dialog.body.size(), dialog.profile_columns.right.minimumSizeHint())
    assert dialog.scroll.verticalScrollBar().maximum() > 0
    dialog.scroll.ensureWidgetVisible(dialog.preferences)
    qapp.processEvents()
    assert dialog.buttons.isVisible()
    assert dialog.preferences.font().pixelSize() >= 16
    assert dialog.name.font().pixelSize() >= 16


def test_group_dialog_variable_daily_enrolment(valid_week, track_dialog):
    original = deepcopy(valid_week.groups[0])
    dialog = track_dialog(GroupDialog(valid_week, valid_week.groups[0]))
    dialog.name.setText('Les explorateurs')
    dialog.ratio.setValue(20)
    dialog.minimum.setValue(2)
    dialog.periods.add_row(1, 420, 720, 41)
    dialog.periods.add_row(1, 720, 1050, 25)
    result = save(dialog)
    assert result.name == 'Les explorateurs'
    assert result.periods[-2:] == [GroupPeriod(1, 420, 720, 41), GroupPeriod(1, 720, 1050, 25)]
    assert valid_week.groups[0] == original
    # The UI cannot reduce the compulsory minimum below two.
    dialog.minimum.setValue(1)
    assert dialog.minimum.value() == 2


def test_intervals_editor_copies_monday_and_rejects_overlap(qapp, track_dialog):
    editor = track_dialog(IntervalsEditor([Window(0, 433, 535)]))
    editor.copy_monday()
    assert editor.values() == [Window(d, 433, 535) for d in range(5)]
    editor.add_row(0, 500, 600)
    with pytest.raises(ValueError, match='chevauchent'):
        editor.values()


def test_room_dialog_capacity_sharing_and_outdoors(valid_week, track_dialog):
    dialog = track_dialog(RoomDialog(valid_week))
    dialog.name.setText('Cour extérieure')
    dialog.capacity.setValue(100)
    dialog.shared.setChecked(True)
    dialog.outdoor.setChecked(True)
    dialog.availability.add_row(0, 420, 1050)
    result = save(dialog)
    assert (result.name, result.capacity, result.shared, result.outdoor) == ('Cour extérieure', 100, True, True)
    assert result.availability == [Window(0, 420, 1050)]
    assert valid_week.rooms == []


def test_shift_dialog_buffers_breaks_lock_and_exact_hours(valid_week, track_dialog):
    original = deepcopy(valid_week.shifts[0])
    dialog = track_dialog(ShiftDialog(valid_week, valid_week.shifts[0]))
    dialog.start.setValue(433)
    dialog.end.setValue(535)
    dialog.before.setValue(10)
    dialog.after.setValue(5)
    dialog.before_paid.setChecked(True)
    dialog.after_paid.setChecked(False)
    dialog.breaks.add_row(470, 480, False)
    dialog.locked.setChecked(True)
    result = save(dialog)
    assert (result.start, result.end) == (433, 535)
    assert (result.coverage_start, result.coverage_end) == (443, 530)
    assert result.breaks == [Break(470, 480, False)]
    assert paid_minutes(result) == 87
    assert result.locked
    assert valid_week.shifts[0] == original


def test_shift_dialog_rejects_missing_assignment_and_invalid_buffers(valid_week, track_dialog, monkeypatch):
    warnings = []
    monkeypatch.setattr(QMessageBox, 'warning', lambda *args: warnings.append(args[2]))
    dialog = track_dialog(ShiftDialog(valid_week))
    dialog.try_accept()
    assert 'éducatrice et un groupe' in warnings[-1]
    dialog.educator.setCurrentIndex(dialog.educator.findData('e1'))
    dialog.group.setCurrentIndex(dialog.group.findData('g1'))
    dialog.start.setValue(500)
    dialog.end.setValue(510)
    dialog.before.setValue(15)
    dialog.try_accept()
    assert 'buffers' in warnings[-1]
    assert dialog.result_item() is None


def test_breaks_editor_rejects_outside_quart_and_overlap(qapp, track_dialog):
    editor = track_dialog(BreaksEditor())
    editor.add_row(400, 450)
    with pytest.raises(ValueError, match='présence'):
        editor.values(420, 600)
    editor.table.setRowCount(0)
    editor.add_row(450, 480)
    editor.add_row(470, 500)
    with pytest.raises(ValueError, match='chevauchent'):
        editor.values(420, 600)


def test_activity_dialog_uses_explicit_responsible_without_changing_work(valid_week, track_dialog):
    valid_week.rooms = [Room(id='yard', name='Cour extérieure', capacity=100, outdoor=True)]
    before = deepcopy(valid_week.shifts)
    dialog = track_dialog(ActivityDialog(valid_week, day=0, start=847, group_id='g1'))
    dialog.name.setText('Jeux extérieurs')
    dialog.end.setValue(1002)
    dialog.room.setCurrentIndex(dialog.room.findData('yard'))
    dialog.notes.setPlainText('Apporter les ballons')
    dialog.responsibles.item(0).setCheckState(Qt.CheckState.Checked)
    dialog.compatible.setChecked(True)
    result = save(dialog)
    assert (result.start, result.end, result.room_id) == (847, 1002, 'yard')
    assert result.responsible_ids == ['e1']
    assert result.notes == 'Apporter les ballons'
    assert result.compatible
    assert valid_week.shifts == before


def test_activity_without_room_stays_open(valid_week, track_dialog, monkeypatch):
    warnings = []
    monkeypatch.setattr(QMessageBox, 'warning', lambda *args: warnings.append(args[2]))
    dialog = track_dialog(ActivityDialog(valid_week, group_id='g1'))
    dialog.name.setText('Bricolage')
    dialog.try_accept()
    assert 'lieu' in warnings[-1]
    assert dialog.result_item() is None


def test_settings_dialog_preserves_required_buffers_and_preferences(valid_week, track_dialog):
    original = deepcopy(valid_week.settings)
    dialog = track_dialog(SettingsDialog(valid_week))
    dialog.opening_buffer.setValue(0)
    dialog.closing_buffer.setValue(0)
    dialog.handover.setValue(0)
    assert (dialog.opening_buffer.value(), dialog.closing_buffer.value(), dialog.handover.value()) == (10, 5, 15)
    dialog.break_after.setValue(300)
    dialog.break_minutes.setValue(30)
    dialog.break_paid.setChecked(True)
    dialog.seniority_weight.setValue(100)
    dialog.preference_weight.setValue(25)
    dialog.target_weight.setValue(50)
    dialog.snap.setCurrentIndex(dialog.snap.findData(0))
    result = save(dialog)
    assert (result.open_minute, result.close_minute) == (420, 1050)
    assert (result.break_after_minutes, result.break_minutes, result.break_paid) == (300, 30, True)
    assert (result.seniority_weight, result.preference_weight, result.target_weight) == (100, 25, 50)
    assert result.snap_minutes == 0
    assert valid_week.settings == original


def test_settings_reject_impossible_day(valid_week, track_dialog, monkeypatch):
    warnings = []
    monkeypatch.setattr(QMessageBox, 'warning', lambda *args: warnings.append(args[2]))
    dialog = track_dialog(SettingsDialog(valid_week))
    dialog.close_time.setValue(400)
    dialog.try_accept()
    assert warnings
    assert dialog.result_item() is None


def test_delete_accepts_only_after_confirmation(valid_week, track_dialog, monkeypatch):
    dialog = track_dialog(ShiftDialog(valid_week, valid_week.shifts[0]))
    monkeypatch.setattr(QMessageBox, 'question', lambda *args: QMessageBox.StandardButton.No)
    dialog.delete_item()
    assert not dialog.delete_requested
    monkeypatch.setattr(QMessageBox, 'question', lambda *args: QMessageBox.StandardButton.Yes)
    dialog.delete_item()
    assert dialog.delete_requested
    assert dialog.result() == QDialog.DialogCode.Accepted


def test_cancel_leaves_source_intact(valid_week, track_dialog):
    original = deepcopy(valid_week.educators[0])
    dialog = track_dialog(EducatorDialog(valid_week, valid_week.educators[0]))
    dialog.name.setText('Modification annulée')
    dialog.reject()
    assert dialog.result() == QDialog.DialogCode.Rejected
    assert dialog.result_item() is None
    assert valid_week.educators[0] == original
