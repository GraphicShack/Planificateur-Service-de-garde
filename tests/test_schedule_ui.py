"""Functional checks for the simplified single-day scheduling interface."""
from copy import deepcopy
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox
from gardeplan.storage import Repository
from gardeplan.ui.main_window import MainWindow
from gardeplan.models import Break
from test_coverage import covered_day


@pytest.fixture
def planner(tmp_path, qapp, monkeypatch):
    for name in ("warning", "critical", "information"):
        monkeypatch.setattr(QMessageBox, name, lambda *args: None)
    plan = covered_day()
    for person in plan.educators:
        person.target_minutes = 645
    repo = Repository(tmp_path / "journee.sqlite3")
    repo.save(plan)
    window = MainWindow(repo, plan)
    window.show()
    qapp.processEvents()
    yield window
    window.autosave.stop()
    window.dirty = False
    window.close()
    window.deleteLater()
    qapp.processEvents()


def test_verification_opens_alert_and_selects_exact_gap(planner, qapp):
    planner.commit(lambda plan: plan.shifts[0].breaks.append(Break(720, 795)))
    planner.top_alert_button.click()
    assert planner.alert_panel.isVisible()
    matches = [planner.alert_list.item(i) for i in range(planner.alert_list.count())
               if "1 éducatrice au lieu de 2" in planner.alert_list.item(i).text()]
    assert matches
    planner.alert_list.itemActivated.emit(matches[0])
    assert planner.calendar.highlighted_interval == (0, 720, 795)
    assert planner.calendar.scroll.verticalScrollBar().value() >= 0
    assert planner.top_alert_button.text().startswith("Vérifier (")


def test_valid_day_explicitly_reports_no_alert(planner):
    planner.top_alert_button.click()
    assert planner.top_alert_button.text() == "Vérifier (0)"
    assert planner.alert_heading_label.text() == "Aucune alerte"
    assert planner.alert_list.item(0).text() == "Aucune alerte"


def test_opening_shift_is_visible_from_the_first_hour(planner, qapp):
    planner.fit_day()
    qapp.processEvents()
    assert planner.calendar.start_minute == 360
    assert planner.calendar.scroll.verticalScrollBar().value() == 0
    block = planner.calendar.canvas.blocks[0]
    assert block.rect.top() > 0
    assert planner.calendar.y(410) >= 0
    planner.calendar.scroll_to(900)
    planner.navigate_day(1)
    assert planner.calendar.scroll.verticalScrollBar().value() == 0


def test_shift_colours_have_readable_text_for_arbitrary_educator_colours(planner):
    from gardeplan.ui.calendar import shift_palette, _pixel_font
    from gardeplan.ui.theme import contrast
    person = deepcopy(planner.week.educators[0])
    for color in ("#000000", "#FFFFFF", "#FF0000", "#214F40", "#FFEE00"):
        person.color = color
        fill, edge, text = shift_palette(person)
        assert edge.name() == color.lower()
        assert contrast(text.name(), fill.name()) >= 4.5
    assert _pixel_font(12).pixelSize() >= 12
    assert all(block.rect.width() >= 140 for block in planner.calendar.canvas.blocks)
