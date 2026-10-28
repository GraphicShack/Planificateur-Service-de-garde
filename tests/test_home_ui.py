import faulthandler
import pytest
from datetime import date
from copy import deepcopy
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from gardeplan.daily import day_plan
from gardeplan.storage import Repository
from gardeplan.ui.main_window import MainWindow
from test_home_data import planned_day


@pytest.fixture(autouse=True)
def bounded_home_checks(monkeypatch):
    """Unexpected native message boxes fail with their text instead of waiting."""
    from PySide6.QtWidgets import QMessageBox
    messages=[]
    def record(parent,title,message,*args,**kwargs):
        messages.append(f"{title}: {message}")
        return QMessageBox.StandardButton.Ok
    for name in ("warning","critical","information"):
        monkeypatch.setattr(QMessageBox,name,record)
    faulthandler.dump_traceback_later(120,exit=True)
    try:
        yield
    finally:
        faulthandler.cancel_dump_traceback_later()
    assert not messages, "\n".join(messages)


def close(window,qapp):
    window.autosave.stop();window.dirty=False;window.close();window.deleteLater();qapp.processEvents()


def test_startup_home_empty_state_and_creation_of_today(tmp_path,qapp):
    repo=Repository(tmp_path/'home.sqlite')
    window=MainWindow(repo,day_plan(date.today().isoformat()));window.show();qapp.processEvents()
    try:
        home=window.home_page
        assert window.content_stack.currentWidget() is home
        assert not home.days and home.today_brief is None
        assert not home.previous_button.isEnabled()
        assert repo.latest_week() is None
        home.new_button.click();qapp.processEvents()
        assert window.week.planning_date==date.today().isoformat()
        assert repo.load_day(date.today().isoformat()) is not None
        assert window.content_stack.currentWidget() is window.planner_page
        assert window.management_stack.currentWidget() is window.enrolment_page
        window.enrolment_panel.count.setValue(5)
        window.enrolment_panel.save_button.click()
        window.home_button.click();qapp.processEvents()
        assert window.content_stack.currentWidget() is home
        assert home.today_brief.children==5
    finally:close(window,qapp)


def test_recent_buttons_open_the_correct_saved_day_and_match_alert_count(tmp_path,qapp):
    repo=Repository(tmp_path/'home.sqlite');first=planned_day('2026-10-23');second=planned_day('2026-10-28')
    first.day_names[0]='Bricolage';second.day_names[0]='Sciences'
    repo.save(second);repo.save(first)
    window=MainWindow(repo,first);window.show();qapp.processEvents()
    try:
        home=window.home_page
        assert [row.brief.date for row in home.day_buttons]==['2026-10-28','2026-10-23']
        home.day_buttons[0].setFocus();QTest.keyClick(home.day_buttons[0],Qt.Key.Key_Space);qapp.processEvents()
        assert window.week.planning_date=='2026-10-28'
        count=int(window.alert_badge.text())
        window.home_button.click();qapp.processEvents()
        assert home.day_buttons[0].brief.alerts==count
        window.open_home_day('2026-10-23');window._rename_day('Arts plastiques')
        window.home_button.click();qapp.processEvents()
        assert next(d for d in home.days if d.date=='2026-10-23').name=='Arts plastiques'
    finally:close(window,qapp)


def test_create_does_not_overwrite_an_existing_day(tmp_path,qapp):
    repo=Repository(tmp_path/'home.sqlite');plan=planned_day(date.today().isoformat());plan.day_names[0]='À conserver';repo.save(plan)
    before=deepcopy(plan.to_dict());window=MainWindow(repo,plan);window.show();qapp.processEvents()
    try:
        assert not window.create_home_day(plan.planning_date)
        assert repo.load_day(plan.planning_date).to_dict()==before
        assert window.week.day_names[0]=='À conserver'
        assert window.management_stack.currentWidget() is window.enrolment_page
    finally:close(window,qapp)


def test_home_stacks_cards_and_keeps_click_targets_on_a_small_window(tmp_path,qapp):
    repo=Repository(tmp_path/'home.sqlite');plan=planned_day();repo.save(plan)
    window=MainWindow(repo,plan);window.resize(720,600);window.show()
    for _ in range(4):qapp.processEvents()
    try:
        home=window.home_page
        assert home._narrow
        assert home.grid.getItemPosition(home.grid.indexOf(home.recent_card))[:2]==(0,0)
        assert home.grid.getItemPosition(home.grid.indexOf(home.today_card))[:2]==(1,0)
        assert home.new_button.height()>=44
        assert home.day_buttons[0].height()>=44
        assert home.horizontalScrollBar().maximum()==0
        assert window.home_button.height()>=44
    finally:close(window,qapp)


def test_home_add_and_edit_use_the_existing_profile_form(tmp_path,qapp,monkeypatch):
    from PySide6.QtWidgets import QDialog
    from gardeplan.ui.forms import EducatorDialog
    repo=Repository(tmp_path/'home.sqlite');plan=planned_day();repo.save(plan)
    window=MainWindow(repo,plan);window.show();qapp.processEvents()
    def accept(dialog):
        dialog.name.setText('Nouvelle éducatrice')
        dialog._item=dialog.build_item()
        return QDialog.DialogCode.Accepted
    monkeypatch.setattr(EducatorDialog,'exec',accept)
    try:
        window.home_page.add_button.click();qapp.processEvents()
        stored=repo.latest_week()
        added=next(e for e in stored.educators if e.name=='Nouvelle éducatrice')
        assert added.seniority==3
        def edit(dialog):
            dialog.name.setText('Nom modifié')
            dialog._item=dialog.build_item()
            return QDialog.DialogCode.Accepted
        monkeypatch.setattr(EducatorDialog,'exec',edit)
        window.home_page.edit_educator.emit(added.id);qapp.processEvents()
        assert next(e for e in repo.latest_week().educators if e.id==added.id).name=='Nom modifié'
        assert window.content_stack.currentWidget() is window.home_page
    finally:close(window,qapp)
