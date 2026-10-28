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
    assert planner.top_alert_button.accessibleName().startswith("Vérifier (")
    assert planner.alert_badge.text() == str(planner.alert_list.count())


def test_valid_day_explicitly_reports_no_alert(planner):
    planner.top_alert_button.click()
    assert planner.top_alert_button.accessibleName() == "Vérifier (0)"
    assert planner.alert_badge.text() == "0"
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


def test_dinner_duration_editor_and_paid_hours_are_real(planner, qapp):
    from gardeplan.ui.forms import ShiftDialog
    from gardeplan.models import paid_minutes
    dialog = ShiftDialog(planner.week, planner.week.shifts[0])
    dialog.breaks.add_row(720, 750, False, "dinner")
    dialog.breaks.table.cellWidget(0, 4).setValue(45)
    result = dialog.build_item()
    assert result.breaks[0] == Break(720, 765, False, "dinner")
    assert paid_minutes(result) == 600
    assert "10 h 00" in dialog.summary.text()
    dialog.deleteLater()


def test_fifty_action_history_buttons_redo_and_branching(planner):
    for index in range(60):
        planner.commit(lambda plan, i=index: plan.day_names.__setitem__(0, f"Journée {i}"))
    assert len(planner._undo) == 50
    assert planner.undo_button.isVisible() and planner.redo_button.isVisible()
    for _ in range(50):
        planner.undo_button.click()
    assert planner.week.day_names[0] == "Journée 9"
    assert not planner.undo_button.isEnabled()
    for _ in range(50):
        planner.redo_button.click()
    assert planner.week.day_names[0] == "Journée 59"
    planner.undo()
    planner.commit(lambda plan: plan.day_names.__setitem__(0, "Autre choix"))
    assert not planner._redo and not planner.redo_button.isEnabled()


def test_platform_undo_redo_keyboard_shortcuts(planner, qapp):
    from PySide6.QtGui import QKeySequence
    from PySide6.QtTest import QTest
    planner.activateWindow()
    planner.calendar.canvas.setFocus()
    planner.commit(lambda plan: plan.day_names.__setitem__(0, "Au clavier"))
    QTest.keySequence(planner, QKeySequence(QKeySequence.StandardKey.Undo))
    qapp.processEvents()
    assert planner.week.day_names.get(0) != "Au clavier"
    QTest.keySequence(planner, QKeySequence("Ctrl+Shift+Z"))
    qapp.processEvents()
    assert planner.week.day_names[0] == "Au clavier"


def test_registrations_replace_the_visible_add_shift_button(planner):
    from PySide6.QtWidgets import QPushButton
    assert planner.enrolment_button.isVisible()
    assert not planner.add_button.isVisible()
    assert not any("Ajouter un quart" == button.text() for button in planner.findChildren(QPushButton) if button.isVisible())
    assert "double-cliquez" in planner.calendar.canvas.accessibleDescription()


def test_day_name_enter_escape_blur_and_pdf(planner, qapp, tmp_path):
    from PySide6.QtTest import QTest
    from gardeplan.pdf import export_general
    from pypdf import PdfReader
    name = planner.day_title
    name.button.click()
    name.editor.setText("Journée des sciences")
    QTest.keyClick(name.editor, Qt.Key.Key_Return)
    assert planner.week.day_names[0] == "Journée des sciences"
    name.button.click()
    name.editor.setText("À annuler")
    QTest.keyClick(name.editor, Qt.Key.Key_Escape)
    assert planner.week.day_names[0] == "Journée des sciences"
    name.button.click()
    name.editor.setText("Journée sportive")
    planner.enrolment_button.setFocus()
    qapp.processEvents()
    assert planner.week.day_names[0] == "Journée sportive"
    target = tmp_path / "nom.pdf"
    export_general(planner.week, target)
    assert "Journée sportive" in PdfReader(target).pages[0].extract_text()


def test_registration_preview_is_live_and_has_no_day_name_field(planner):
    from gardeplan.ui.enrolment import EnrolmentDialog
    from PySide6.QtWidgets import QLineEdit
    dialog = EnrolmentDialog(planner.week)
    dialog.count.setValue(5)
    assert dialog.preview.text() == "5 enfants → ratio 1/20 → minimum 2 éducatrices simultanées"
    dialog.count.setValue(41)
    assert "minimum 3" in dialog.preview.text()
    dialog.count.setValue(0)
    assert "fermée" in dialog.preview.text()
    assert not any(field.accessibleName() == "Nom de la journée" for field in dialog.findChildren(QLineEdit))
    dialog.deleteLater()


def test_single_service_screen_has_no_groups_preferences_or_monthly_popup(planner):
    from gardeplan.ui.forms import EducatorDialog
    from gardeplan.ui.date_field import DateField
    assert len(planner.calendar.columns()) == 1
    assert "Groupe" not in planner.calendar.columns()[0][0]
    assert "groups" in planner.menu_actions
    assert isinstance(planner.week_date, DateField)
    assert not planner.week_date.calendarPopup()
    dialog = EducatorDialog(planner.week)
    dialog.show()
    assert dialog.preferences.isHidden()
    dialog.close()
    dialog.deleteLater()


def test_profile_defaults_use_free_rank_and_empty_unset_hours(planner):
    from gardeplan.ui.forms import EducatorDialog, ClockEdit
    from PySide6.QtWidgets import QDateTimeEdit
    dialog = EducatorDialog(planner.week)
    assert dialog.seniority.value() == 3
    assert not dialog.target.text() and not dialog.guaranteed.text()
    assert dialog.target_note.text() == "Aucun objectif défini"
    assert "minimum obligatoire" in dialog.guaranteed.toolTip()
    dialog.name.setText("Nouvelle personne")
    dialog.seniority.setValue(1)
    with pytest.raises(ValueError, match="déjà utilisé"):
        dialog.build_item()
    dialog.seniority.setValue(4)
    assert dialog.build_item().seniority == 4
    clock = ClockEdit(433)
    assert isinstance(clock, QDateTimeEdit)
    assert clock.value() == 433
    clock.setValue(1440)
    assert clock.value() == 1440
    clock.lineEdit().setText("6 h 50")
    clock.interpretText()
    assert clock.value() == 410
    clock.deleteLater()
    dialog.deleteLater()


def test_one_save_indicator_reports_local_changes_then_real_save(planner):
    assert planner.save_label.text() == "Enregistré"
    assert not planner.week_status_label.isVisible()
    planner.commit(lambda plan: plan.day_names.__setitem__(0, "Nouvelle journée"))
    assert planner.save_label.text() == "Hors ligne – modifications locales"
    assert planner.save_week(manual=False)
    assert planner.save_label.text() == "Enregistré"


def test_resize_handles_work_without_hover_and_keyboard_resizes_exact_minutes(planner, qapp):
    from PySide6.QtTest import QTest
    from PySide6.QtCore import QPoint
    from gardeplan.ui.calendar import resize_handles
    canvas = planner.calendar.canvas
    planner.calendar.set_zoom(2)
    qapp.processEvents()
    canvas.hover = canvas.selection = None
    block = canvas.blocks[0]
    top, bottom = resize_handles(block)
    assert canvas._hit(top.center()) is block
    assert canvas._hit(bottom.center()) is block
    before = planner.week.shifts[0].start
    point = QPoint(round(top.center().x()), round(top.center().y()))
    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, point)
    QTest.mouseMove(canvas, point+QPoint(0, round(planner.calendar.scale)))
    QTest.mouseRelease(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, point+QPoint(0, round(planner.calendar.scale)))
    assert planner.week.shifts[0].start == before+1
    canvas.selection = ("shift", planner.week.shifts[0].id)
    end = planner.week.shifts[0].end
    QTest.keyClick(canvas, Qt.Key.Key_Down, Qt.KeyboardModifier.ShiftModifier)
    assert planner.week.shifts[0].end == end+1
    assert "Entrée" in canvas.accessibleDescription()


def test_management_pages_replace_team_and_keep_the_calendar_width(planner, qapp):
    original_width = planner.calendar.width()
    assert planner.management_stack.currentWidget() is planner.team_page
    planner.enrolment_button.click()
    qapp.processEvents()
    assert planner.management_stack.currentWidget() is planner.enrolment_panel
    assert not planner.educator_list.isVisible()
    assert planner.calendar.width() == original_width
    planner.enrolment_panel.count.setValue(41)
    planner.enrolment_panel.save_button.click()
    assert sum(p.students for g in planner.week.groups for p in g.periods) == 41
    planner.top_alert_button.click()
    qapp.processEvents()
    assert planner.management_stack.currentWidget() is planner.alert_panel
    assert planner.calendar.width() == original_width
    assert not planner.enrolment_panel.isVisible()
    planner.close_alerts_button.click()
    assert planner.management_stack.currentWidget() is planner.team_page
    assert planner.educator_list.isVisible()
    assert planner.alert_badge.text() != "0"


def test_hidden_dinner_still_removes_coverage_and_unpaid_minutes(planner, qapp):
    from gardeplan.coverage import coverage_timeline
    from gardeplan.models import paid_minutes
    planner.commit(lambda plan: plan.shifts[0].breaks.append(Break(720,750,False,"dinner")))
    qapp.processEvents()
    shift = planner.week.shifts[0]
    block = next(b for b in planner.calendar.canvas.blocks if b.value.id == shift.id)
    assert "Dîner" not in planner.calendar.canvas._tip(block)
    assert paid_minutes(shift) == 615
    assert next(p for p in coverage_timeline(planner.week) if p.start == 720).actual == 1
