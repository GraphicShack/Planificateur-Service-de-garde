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


def test_export_button_writes_one_pdf_without_format_selection(day_window, tmp_path, monkeypatch):
    from pypdf import PdfReader
    destination = tmp_path / "journee.pdf"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (str(destination), ""))
    day_window.export_button.click()
    reader = PdfReader(destination)
    assert len(reader.pages) == 1
    assert tuple(float(v) for v in reader.pages[0].mediabox) == (0, 0, 792, 612)
    assert "Nom de l’éducateur" in reader.pages[0].extract_text()
    assert day_window.menu_actions["pdf_preview"].isEnabled()


def test_folder_menu_has_real_save_open_duplicate_history_and_backup_commands(day_window, monkeypatch):
    assert day_window.folder_button.menu() is day_window.file_menu
    assert day_window.folder_button.parentWidget() is day_window.navigation_rail
    called = []
    monkeypatch.setattr(day_window, "save_week", lambda manual=True: called.append("save"))
    monkeypatch.setattr(day_window, "choose_week", lambda: called.append("open"))
    monkeypatch.setattr(day_window, "duplicate_week", lambda: called.append("duplicate"))
    monkeypatch.setattr(day_window, "show_history", lambda: called.append("history"))
    monkeypatch.setattr(day_window, "backup", lambda: called.append("backup"))
    monkeypatch.setattr(day_window, "import_backup", lambda: called.append("import"))
    for key in ("save", "choose_week", "duplicate", "history", "backup", "import"):
        action = day_window.menu_actions[key]
        assert action in day_window.file_menu.actions()
        action.trigger()
    assert called == ["save", "open", "duplicate", "history", "backup", "import"]


def test_sidebar_add_opens_one_readable_form_and_persists_full_profile(day_window, monkeypatch, qapp):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QDialog, QDialogButtonBox, QTabWidget
    from gardeplan.models import Window
    existing = deepcopy(day_window.week)

    def complete(dialog):
        assert not dialog.findChildren(QTabWidget)
        dialog.name.setText("Élodie Gagnon")
        dialog.seniority.setValue(4)
        dialog.seniority_date.setText("2020-08-24")
        dialog.target.setValue(433)
        dialog.guaranteed.setValue(300)
        dialog.maximum.setValue(645)
        dialog.availability.add_row(0, 410, 1055)
        dialog.absences.add_row(0, 540, 555)
        dialog.restrictions.setPlainText("Préférence pour le groupe A")
        dialog.show()
        qapp.processEvents()
        save = next(button for button in dialog.buttons.buttons()
                    if dialog.buttons.buttonRole(button) == QDialogButtonBox.ButtonRole.AcceptRole)
        save.click()
        assert dialog.result() == QDialog.DialogCode.Accepted
        return dialog.result()

    monkeypatch.setattr(EducatorDialog, "exec", complete)
    day_window.add_educator_button.click()
    created = day_window.week.educators[-1]
    assert created.name == "Élodie Gagnon" and created.seniority == 4
    assert created.seniority_date == "2020-08-24"
    assert (created.target_minutes, created.guaranteed_minutes, created.max_minutes) == (433, 300, 645)
    assert created.availability == [Window(0, 410, 1055)]
    assert created.absences == [Window(0, 540, 555)]
    assert created.preferred_groups == []
    assert created.color not in {ed.color for ed in existing.educators}
    assert created.restrictions == "Préférence pour le groupe A"
    assert day_window.week.shifts == existing.shifts
    assert day_window.save_week(manual=False)
    assert day_window.repo.load_day(day_window.week.planning_date).educators[-1] == created


def test_planner_has_no_today_button(day_window):
    assert not any(button.text() == "Aujourd’hui" for button in day_window.findChildren(QPushButton))


def test_activities_and_rooms_are_not_exposed_and_do_not_block_schedules(day_window):
    from gardeplan.models import Activity, Room
    from gardeplan.validation import validate
    plan = deepcopy(day_window.week)
    plan.activities = [Activity("a", "Ancienne activité", "g1", 0, 600, 700, "lieu-absent")]
    plan.rooms = [Room("r", "", capacity=-1)]
    day_window._load(plan)
    assert day_window.week.activities == plan.activities
    assert not [issue for issue in validate(day_window.week) if issue.severity == "error"]
    assert all(block.kind == "shift" for block in day_window.calendar.canvas.blocks)
    assert "add_activity" not in day_window.menu_actions and "rooms" not in day_window.menu_actions
    assert not any("activité" in action.text().lower() for action in day_window.add_menu.actions())
    assert (day_window.calendar.start_minute, day_window.calendar.end_minute) == (360, 1080)
