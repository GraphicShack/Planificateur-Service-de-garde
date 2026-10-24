"""Actual Qt event tests, run with QT_QPA_PLATFORM=offscreen."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import pytest
pytest.importorskip('PySide6')
from PySide6.QtCore import Qt, QPoint, QPointF, QMimeData, QByteArray
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from gardeplan.models import Shift, Activity
from gardeplan.ui.calendar import CalendarWidget, EDUCATOR_MIME


@pytest.fixture
def calendar(qapp, valid_week):
    valid_week.shifts = [Shift(id='precise', educator_id='e1', group_id='g1',
                              day=0, start=433, end=535)]
    widget = CalendarWidget()
    widget.resize(900, 700)
    widget.set_week(valid_week, 0, [])
    widget.set_zoom(2)
    widget.set_snap(1)
    widget.show()
    qapp.processEvents()
    yield widget
    widget.close()
    widget.deleteLater()
    qapp.processEvents()


def drag(widget, start, end):
    QTest.mousePress(widget, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
    QTest.mouseMove(widget, end, delay=5)
    QTest.mouseRelease(widget, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, end)


def test_resize_top_by_one_minute_emits_exact_change(calendar):
    requests = []
    calendar.change_requested.connect(lambda *args: requests.append(args))
    block = calendar.canvas.blocks[0]
    point = QPoint(round(block.rect.center().x()), round(block.rect.top() + 3))
    drag(calendar.canvas, point, point + QPoint(0, round(calendar.scale)))
    assert requests[-1] == ('shift', 'precise', 0, 434, 535, 'g1')
    assert calendar.week.shifts[0].start == 433, 'Le contrôleur doit approuver la modification.'


def test_move_exact_minutes_keeps_duration(calendar):
    requests = []
    calendar.change_requested.connect(lambda *args: requests.append(args))
    block = calendar.canvas.blocks[0]
    point = QPoint(round(block.rect.center().x()), round(block.rect.top() + 30))
    drag(calendar.canvas, point, point + QPoint(0, round(7 * calendar.scale)))
    assert requests[-1] == ('shift', 'precise', 0, 440, 542, 'g1')
    assert calendar.week.shifts[0].end - calendar.week.shifts[0].start == 102


def test_educator_drop_emits_group_day_and_exact_minute(calendar, qapp):
    requests = []
    calendar.educator_dropped.connect(lambda *args: requests.append(args))
    data = QMimeData()
    data.setData(EDUCATOR_MIME, QByteArray(b'e2'))
    position = QPoint(90, round(calendar.y(517)))
    enter = QDragEnterEvent(position, Qt.DropAction.CopyAction, data,
                            Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    QApplication.sendEvent(calendar.canvas, enter)
    assert enter.isAccepted()
    drop = QDropEvent(QPointF(position), Qt.DropAction.CopyAction, data,
                      Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    QApplication.sendEvent(calendar.canvas, drop)
    assert requests[-1] == ('e2', 0, 517, 'g1')


def test_locked_and_archived_quarts_do_not_move(calendar):
    requests = []
    calendar.change_requested.connect(lambda *args: requests.append(args))
    calendar.week.shifts[0].locked = True
    calendar.set_week(calendar.week)
    block = calendar.canvas.blocks[0]
    point = QPoint(round(block.rect.center().x()), round(block.rect.top() + 30))
    drag(calendar.canvas, point, point + QPoint(0, 33))
    assert requests == []
    calendar.week.shifts[0].locked = False
    calendar.set_read_only(True)
    drag(calendar.canvas, point, point + QPoint(0, 33))
    assert requests == []


def test_activity_move_is_independent(calendar):
    calendar.week.activities = [Activity(id='a', name='Bricolage', group_id='g1',
                                         day=0, start=433, end=535)]
    calendar.set_week(calendar.week)
    before = calendar.week.shifts[0].start, calendar.week.shifts[0].end
    requests = []
    calendar.change_requested.connect(lambda *args: requests.append(args))
    block = next(b for b in calendar.canvas.blocks if b.kind == 'activity')
    point = QPoint(round(block.rect.center().x()), round(block.rect.top() + 30))
    drag(calendar.canvas, point, point + QPoint(0, round(3 * calendar.scale)))
    assert requests[-1] == ('activity', 'a', 0, 436, 538, 'g1')
    assert before == (calendar.week.shifts[0].start, calendar.week.shifts[0].end)


def test_week_header_selects_day_and_shows_custom_name(calendar):
    requests = []
    calendar.day_selected.connect(requests.append)
    calendar.set_mode('Semaine')
    assert 'Halloween' in calendar.columns()[0][1]
    QTest.mouseClick(calendar.header, Qt.MouseButton.LeftButton,
                     Qt.KeyboardModifier.NoModifier,
                     QPoint(round(calendar.column_width + 20), 25))
    assert requests == [1]
