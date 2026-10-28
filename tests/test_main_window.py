"""Dashboard transactions: the visible editor drives persisted, undoable models."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from copy import deepcopy
from datetime import date, timedelta

import pytest
pytest.importorskip("PySide6")
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QInputDialog, QMessageBox

from gardeplan.models import Break, Window, paid_minutes
from gardeplan.optimizer import GenerationResult
from gardeplan.storage import Repository
from gardeplan.ui.main_window import MainWindow


@pytest.fixture
def dashboard(valid_week, tmp_path, qapp, monkeypatch):
    messages = []
    for name in ("warning", "information", "critical"):
        monkeypatch.setattr(QMessageBox, name, lambda *args: messages.append(args[2]))
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Yes)
    repository = Repository(tmp_path / "gardeplan.sqlite3")
    repository.save(valid_week)
    window = MainWindow(repository, valid_week)
    window._test_messages = messages
    yield window
    window.autosave.stop()
    window.dirty = False
    window.close()
    window.deleteLater()
    qapp.processEvents()


def test_dashboard_move_preserves_break_offset_paid_minutes_and_undo_redo(dashboard):
    window = dashboard
    source = deepcopy(window.week)
    source.shifts[0].breaks = [Break(600, 615)]
    window._load(source)
    before = deepcopy(window.week)
    original_minutes = paid_minutes(before.shifts[0])
    window.change_block("shift", "s1", 1, 433, 1078, "g1")
    moved = window.week.shifts[0]
    assert (moved.day, moved.start, moved.end) == (1, 433, 1078)
    assert moved.breaks == [Break(623, 638)]
    assert paid_minutes(moved) == original_minutes
    assert window.dirty
    assert window.undo_button.isEnabled()
    window.undo()
    assert window.week.to_dict() == before.to_dict()
    window.redo()
    assert window.week.shifts[0].breaks == [Break(623, 638)]
    assert window.save_week(manual=False)
    assert not window.dirty
    assert window.repo.load_week(window.week.monday).shifts[0] == window.week.shifts[0]


def test_dashboard_resize_keeps_exact_minutes_and_refuses_to_cut_pause(dashboard):
    window = dashboard
    window.week.shifts[0].breaks = [Break(600, 615)]
    window.change_block("shift", "s1", 0, 433, 1002, "g1")
    assert (window.week.shifts[0].start, window.week.shifts[0].end) == (433, 1002)
    before = deepcopy(window.week)
    window.change_block("shift", "s1", 0, 433, 610, "g1")
    assert window.week == before
    assert any("pause" in message.lower() for message in window._test_messages)


def test_published_edits_create_draft_and_retain_original_snapshot(dashboard):
    window = dashboard
    published = deepcopy(window.week)
    published.status = "published"
    version_id = window.repo.save(published)
    window._load(published)
    window.commit(lambda week: week.day_names.__setitem__(0, "Pédagogique — Sports"))
    assert window.week.status == "draft"
    assert window.save_week(manual=False)
    original = window.repo.load_version(version_id)
    assert original.status == "published"
    assert original.day_names[0] == "Journée pédagogique — Halloween"
    assert window.repo.load_week(published.monday).day_names[0] == "Pédagogique — Sports"


def test_custom_day_name_autosaves_and_can_be_cleared(dashboard, monkeypatch):
    window = dashboard
    window.name_day()
    window.day_title.editor.setText("  Pédagogique — Halloween  ")
    window.day_title.finish_editing()
    assert window.week.day_names[0] == "Pédagogique — Halloween"
    assert "Pédagogique — Halloween" in window.day_combo.currentText()
    window.autosave.timeout.emit()
    assert not window.dirty
    assert window.repo.load_week(window.week.monday).day_names[0] == "Pédagogique — Halloween"
    window.name_day()
    window.day_title.editor.clear()
    window.day_title.finish_editing()
    assert window.week.day_names[0] == ""
    assert window.week.day_label(0) == "Lundi 26/10"


def test_archive_and_historical_versions_disable_calendar_mutations(dashboard):
    window = dashboard
    archived = deepcopy(window.week)
    archived.status = "archived"
    window.repo.save(archived)
    window._load(archived)
    assert window.read_only and window.calendar.read_only
    assert not window.add_shift_button.isEnabled()
    before = window.week.to_dict()
    window.change_block("shift", "s1", 0, 433, 1078, "g1")
    assert window.week.to_dict() == before
    assert not window.dirty
    window._load(deepcopy(archived), version=1)
    assert window.read_only and not window.save_button.isEnabled()


def test_new_week_copies_profiles_but_clears_weekly_absences_and_assignments(dashboard):
    window = dashboard
    window.week.educators[0].absences = [Window(0, 600, 660)]
    window.dirty = True
    next_monday = date.fromisoformat(window.week.monday) + timedelta(days=7)
    window.switch_week(next_monday)
    assert window.week.monday == next_monday.isoformat()
    assert window.week.educators[0].name == "Marie Tremblay"
    assert window.week.educators[0].availability == [Window(day=d, start=0, end=1440) for d in range(5)]
    assert window.week.educators[0].absences == []
    assert window.week.shifts == [] and window.week.activities == []
    assert window.week.day_names == {}


def test_save_failure_keeps_dirty_data_and_blocks_navigation(dashboard, monkeypatch):
    window = dashboard
    window.commit(lambda week: week.day_names.__setitem__(0, "À conserver"))
    before = deepcopy(window.week)
    def fail(week):
        raise OSError("Disque plein")
    monkeypatch.setattr(window.repo, "save", fail)
    assert not window.save_week(manual=False)
    assert window.dirty
    window.switch_week(date.fromisoformat(window.week.monday) + timedelta(days=7))
    assert window.week == before
    assert window.dirty
    assert "Échec" in window.save_label.text()
    assert any("Disque plein" in message for message in window._test_messages)


def test_impossible_generation_preserves_current_schedule(dashboard):
    window = dashboard
    before = deepcopy(window.week)
    result = GenerationResult(False, None, "Aucune solution", "INFEASIBLE", ["Deux éducatrices indisponibles."])
    window._generation_result(result)
    assert window.week == before
    assert not window.dirty
    assert any("indisponibles" in message for message in window._test_messages)


def test_declining_generated_proposal_preserves_current_schedule(dashboard, monkeypatch):
    window = dashboard
    before = deepcopy(window.week)
    proposal = deepcopy(window.week)
    proposal.day_names[0] = "Proposition à refuser"
    window._pending_proposal = GenerationResult(True, proposal, "Proposition valide", "OPTIMAL")
    monkeypatch.setattr(QDialog, "exec", lambda dialog: QDialog.DialogCode.Rejected)
    window._generation_finished()
    assert window.week == before
    assert not window.dirty


def test_accepting_generated_proposal_is_undoable(dashboard, monkeypatch):
    window = dashboard
    original = deepcopy(window.week)
    proposal = deepcopy(window.week)
    proposal.day_names[0] = "Proposition acceptée"
    window._pending_proposal = GenerationResult(True, proposal, "Proposition valide", "OPTIMAL")
    monkeypatch.setattr(QDialog, "exec", lambda dialog: QDialog.DialogCode.Accepted)
    window._generation_finished()
    assert window.week.day_names[0] == "Proposition acceptée"
    assert window.dirty
    window.undo()
    assert window.week == original


def test_fit_entire_day_includes_opening_and_closing_buffers(dashboard, qapp):
    window = dashboard
    original = deepcopy(window.week)
    window.show()
    qapp.processEvents()
    window.fit_day()
    qapp.processEvents()
    calendar = window.calendar
    offset = calendar.scroll.verticalScrollBar().value()
    assert calendar.y(410) - offset >= -2
    assert calendar.y(1055) - offset <= calendar.scroll.viewport().height() + 2
    assert window.week == original
    assert not window.dirty


def test_educator_search_filters_accents_and_preserves_week(dashboard):
    window = dashboard
    window.week.educators[0].name = "Élodie Tremblay"
    window.refresh()
    original = deepcopy(window.week)
    window.educator_search.setText("elodie")
    assert window.educator_list.count() == 1
    assert window.educator_list.item(0).data(Qt.ItemDataRole.UserRole) == "e1"
    assert window.edit_educator_button.isEnabled()
    window.educator_search.setText("nom absent")
    assert not window.edit_educator_button.isEnabled()
    assert window.educator_list.item(0).data(Qt.ItemDataRole.UserRole) is None
    window.educator_search.clear()
    assert window.educator_list.count() == 2
    assert window.week == original and not window.dirty


def test_profile_shortcut_opens_selected_educator(dashboard, monkeypatch):
    window = dashboard
    selected = []
    monkeypatch.setattr(window, "edit_educator", lambda identifier: selected.append(identifier))
    window.educator_list.setCurrentRow(1)
    window.edit_selected_educator()
    assert selected == ["e2"]


def test_top_alert_summary_reopens_collapsed_details(dashboard):
    window = dashboard
    window.alert_toggle.setChecked(False)
    window.toggle_alerts()
    assert window.alert_panel.isHidden()
    window.top_alert_button.click()
    assert not window.alert_panel.isHidden()
    assert window.alert_toggle.isChecked()
    assert "0 erreur" in window.top_alert_button.toolTip()


def test_alerts_start_closed_and_close_button_keeps_schedule(dashboard):
    window = dashboard
    original = deepcopy(window.week)
    assert window.alert_panel.isHidden()
    assert not window.alert_toggle.isChecked()
    window.top_alert_button.click()
    assert not window.alert_panel.isHidden()
    assert window.alert_toggle.isChecked()
    window.close_alerts_button.click()
    assert window.alert_panel.isHidden()
    assert not window.alert_toggle.isChecked()
    assert window.week == original and not window.dirty


def test_named_menus_call_existing_commands(dashboard, monkeypatch):
    window = dashboard
    called = []
    monkeypatch.setattr(window, "name_day", lambda: called.append("name"))
    monkeypatch.setattr(window, "edit_educator", lambda: called.append("educator"))
    monkeypatch.setattr(window, "manage_entities", lambda collection: called.append(collection))
    monkeypatch.setattr(window, "new_shift", lambda: called.append("shift"))
    monkeypatch.setattr(window, "new_activity", lambda: called.append("activity"))
    monkeypatch.setattr(window, "save_week", lambda manual=True: called.append("save"))
    for key in ("name_day", "add_educator", "add_shift", "save"):
        action = window.menu_actions[key]
        assert action.text().strip()
        action.trigger()
    assert called == ["name", "educator", "shift", "save"]
    assert "Menu" in window.more_button.toolTip()
    assert window.more_button.menu() is window.command_menu


def test_display_options_use_live_calendar_controls(dashboard, monkeypatch):
    window = dashboard
    snap, zoom = window.snap_combo, window.zoom
    captured = []
    def inspect(dialog):
        assert snap.parent() is dialog
        assert zoom.parent() is dialog
        if captured:
            assert snap.currentData() == 5
            assert zoom.value() == 70
        index = snap.findData(5)
        snap.setCurrentIndex(index)
        snap.activated.emit(index)
        zoom.setValue(70)
        captured.append(dialog.windowTitle())
        return QDialog.DialogCode.Accepted
    monkeypatch.setattr(QDialog, "exec", inspect)
    window.menu_actions["display"].trigger()
    window.menu_actions["display"].trigger()
    assert captured == ["Affichage du calendrier", "Affichage du calendrier"]
    assert window.week.settings.snap_minutes == 5
    assert window.calendar.snap_minutes == 5
    assert window.calendar.scale == pytest.approx(1.65 * .7)
    assert snap.parent() is window._hidden_controls
    assert zoom.parent() is window._hidden_controls
    assert window.snap_combo is snap and window.zoom is zoom
    assert window.dirty


def test_menu_respects_archive_and_running_generation(dashboard):
    window = dashboard
    archived = deepcopy(window.week)
    archived.status = "archived"
    window._load(archived)
    for key in ("add_shift", "name_day", "enrolment", "add_educator", "edit_educator", "settings", "status_published"):
        assert not window.menu_actions[key].isEnabled()
    assert window.menu_actions["history"].isEnabled()
    window._load(deepcopy(dashboard.repo.load_version(1)))
    worker_sentinel = object()
    window._worker = worker_sentinel
    try:
        window.refresh()
        for key in ("save", "add_shift", "duplicate", "history", "import"):
            assert not window.menu_actions[key].isEnabled()
    finally:
        window._worker = None
        window.refresh()
