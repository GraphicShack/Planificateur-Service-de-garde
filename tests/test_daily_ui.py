"""The visible daily editor must drive independent persisted schedules."""
from copy import deepcopy
from datetime import date

import pytest
from PySide6.QtWidgets import QPushButton, QMessageBox, QFileDialog

from gardeplan.storage import Repository
from gardeplan.ui.main_window import MainWindow
from gardeplan.ui.forms import EducatorDialog, GroupDialog, ShiftDialog
from test_daily import prepared_day


@pytest.fixture
def day_window(tmp_path, qapp, monkeypatch):
    for name in ("warning", "information", "critical"):
        monkeypatch.setattr(QMessageBox, name, lambda *args: None)
    repo = Repository(tmp_path / "journees.sqlite")
    plan = prepared_day()
    repo.save(plan)
    window = MainWindow(repo, plan)
    yield window
    window.autosave.stop()
    window.hide()
    window.deleteLater()
    qapp.processEvents()


def test_daily_screen_has_no_week_selector_or_week_commands(day_window, qapp):
    window = day_window
    window.show()
    qapp.processEvents()
    assert not window.week_mode.isVisible()
    assert not window.day_combo.isVisible()
    assert not any("semaine" in button.text().lower() for button in window.findChildren(QPushButton) if button.isVisible())
    assert "Semaine" not in window.week_date.displayFormat()
    assert "journée" in window.menu_actions["duplicate"].text()
    window.set_mode("Semaine")
    assert window.calendar.mode == "Jour"


def test_day_navigation_saves_then_reopens_same_date_exactly(day_window):
    window = day_window
    window.change_block("shift", "0", 0, 433, 1078, "g1")
    expected = deepcopy(window.week)
    window.navigate_day(1)
    assert window.week.planning_date == "2026-10-29"
    assert window.week.shifts == [] and window.week.groups == []
    window.switch_day(date(2026, 10, 28))
    assert window.week == expected
    assert window.calendar.day == 0
    assert window.week_date.date().toPython() == date(2026, 10, 28)


def test_daily_forms_only_offer_selected_date_and_daily_hours(day_window):
    window = day_window
    person = EducatorDialog(window.week)
    assert person.target.value() == 0
    assert person.maximum.value() == 720
    person.availability.add_row()
    assert person.availability.table.cellWidget(0, 0).count() == 1
    assert person.availability.table.isColumnHidden(0)
    assert not any("semaine" in button.text().lower() for button in person.findChildren(QPushButton) if button.isVisible())
    shift = ShiftDialog(window.week)
    assert shift.day.count() == 1
    assert "Mercredi" in shift.day.currentText()
    for dialog in (person, shift):
        dialog.deleteLater()


def test_creation_assigns_distinct_colours_and_edit_preserves_manual_colour(day_window):
    plan = day_window.week
    forms = []
    for index, rank in enumerate((1, 4, 9)):
        dialog = EducatorDialog(plan)
        forms.append(dialog)
        dialog.name.setText(f"Nouvelle éducatrice {index}")
        assert dialog.seniority.minimum() == 1
        assert dialog.seniority.maximum() == 11
        dialog.seniority.setValue(rank)
        created = dialog.build_item()
        assert created.color not in [e.color for e in plan.educators]
        assert created.seniority == rank
        plan.educators.append(created)
    original = plan.educators[-1]
    edit = EducatorDialog(plan, original)
    edit.color.color = "#123ABC"
    changed = edit.build_item()
    assert changed.color == "#123ABC" and changed.seniority == 9
    again = EducatorDialog(plan, changed)
    assert again.color.color == "#123ABC"
    for dialog in forms + [edit, again]:
        dialog.deleteLater()


def test_publication_and_archive_of_one_date_do_not_change_another(day_window, monkeypatch):
    window = day_window
    second = prepared_day("2026-10-29")
    second.status = "archived"
    window.repo.save(second)
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Yes)
    window._status_selected(window.status_combo.findData("published"))
    assert window.week.status == "published"
    window.commit(lambda plan: plan.day_names.__setitem__(0, "Modifié"))
    window.save_week(manual=False)
    assert window.repo.load_day("2026-10-29") == second


def test_import_weekly_backup_opens_actual_planned_day_when_monday_is_empty(day_window, tmp_path, monkeypatch):
    from gardeplan.models import Week, Group, GroupPeriod, Educator, Shift
    source = Repository(tmp_path / "ancienne.sqlite")
    legacy = Week("2026-10-26", educators=[Educator("e", "Camille Roy")],
                  groups=[Group("g", "Groupe A", periods=[GroupPeriod(2, 420, 1050, 20)])],
                  shifts=[Shift("s", "e", "g", 2, 433, 535)], day_names={2: "Mercredi pédagogique"})
    source.save(legacy)
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args: (str(source.path), ""))
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Yes)
    day_window.import_backup()
    assert day_window.week.planning_date == "2026-10-28"
    assert day_window.week.day_names[0] == "Mercredi pédagogique"
    assert day_window.week.shifts[0].start == 433
    assert day_window.repo.load_week("2026-10-26") == legacy
