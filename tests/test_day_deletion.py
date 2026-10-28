from copy import deepcopy
from gardeplan.storage import Repository
from gardeplan.models import Week,Shift,Educator
from test_home_data import planned_day


def test_format_two_is_backed_up_before_migration_and_history_stays_intact(tmp_path):
    import sqlite3
    from contextlib import closing
    repo=Repository(tmp_path/'data.sqlite');plan=planned_day();identifier=repo.save(plan)
    with closing(sqlite3.connect(repo.path)) as conn,conn:
        conn.execute("UPDATE metadata SET value='2' WHERE key='schema_version'")
        conn.execute('DROP TABLE day_deletions')
    upgraded=Repository(repo.path)
    assert upgraded.load_version(identifier)==plan
    backups=list(tmp_path.glob('data-avant-format3-*.sqlite3'))
    assert len(backups)==1
    with closing(sqlite3.connect(backups[0])) as conn:
        assert conn.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()[0]=='2'
    upgraded.delete_day(plan.planning_date)
    assert upgraded.list_days()==[]


def test_deletion_hides_the_date_and_keeps_history_other_days_and_profiles(tmp_path):
    repo=Repository(tmp_path/'data.sqlite')
    plan=planned_day();identifier=repo.save(plan)
    other=planned_day('2026-10-29');repo.save(other)
    history=repo.history(plan.storage_key)
    repo.delete_day(plan.planning_date)
    assert repo.load_day(plan.planning_date) is None
    assert [row['date'] for row in repo.list_days()]==['2026-10-29']
    assert repo.history(plan.storage_key)==history
    assert repo.load_version(identifier)==plan
    assert repo.load_day(other.planning_date)==other
    assert repo.latest_week().educators==other.educators
    reopened=Repository(repo.path)
    assert reopened.load_day(plan.planning_date) is None
    assert reopened.restore(identifier)==plan
    assert reopened.load_day(plan.planning_date)==plan


def test_deleted_legacy_date_does_not_reappear_and_backups_keep_deletions(tmp_path):
    repo=Repository(tmp_path/'data.sqlite')
    old=Week('2026-10-26',educators=[Educator('e','Profil')],
             shifts=[Shift('s','e','g',2,600,700)],day_names={2:'Ancienne journée'})
    repo.save(old);repo.delete_day('2026-10-28')
    assert repo.list_days()==[] and repo.load_day('2026-10-28') is None
    backup=repo.backup(tmp_path/'backup.sqlite')
    other=Repository(tmp_path/'other.sqlite');other.import_backup(backup)
    assert other.list_days()==[] and other.load_day('2026-10-28') is None
    assert other.latest_week().educators==old.educators
    # An explicit new save of that date recreates it, keeping the old versions.
    plan=planned_day();other.save(plan)
    assert other.load_day(plan.planning_date)==plan


def test_home_delete_button_can_cancel_then_delete_and_recreate(tmp_path,qapp,monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    from gardeplan.ui.main_window import MainWindow
    repo=Repository(tmp_path/'data.sqlite');plan=planned_day();repo.save(plan)
    window=MainWindow(repo,plan);window.show();qapp.processEvents()
    try:
        monkeypatch.setattr(QMessageBox,'question',lambda *args:QMessageBox.StandardButton.Cancel)
        window.home_page.day_delete_buttons[0].click()
        assert repo.load_day(plan.planning_date) is not None
        monkeypatch.setattr(QMessageBox,'question',lambda *args:QMessageBox.StandardButton.Yes)
        window.home_page.day_delete_buttons[0].click();qapp.processEvents()
        assert not window.home_page.days and repo.load_day(plan.planning_date) is None
        assert len(window._home_roster().educators)==len(plan.educators)
        assert window.create_home_day(plan.planning_date)
        assert repo.load_day(plan.planning_date).shifts==[]
        assert len(repo.history(plan.storage_key))>=2
    finally:
        window.autosave.stop();window.dirty=False;window.close();window.deleteLater();qapp.processEvents()


def test_editing_a_profile_does_not_resurrect_a_deleted_last_day(tmp_path,qapp,monkeypatch):
    from PySide6.QtWidgets import QDialog
    from gardeplan.ui.forms import EducatorDialog
    from gardeplan.ui.main_window import MainWindow
    repo=Repository(tmp_path/'data.sqlite');plan=planned_day();repo.save(plan);repo.delete_day(plan.planning_date)
    from gardeplan.daily import day_plan
    window=MainWindow(repo,day_plan(plan.planning_date,plan))
    def accept(dialog):
        dialog.name.setText('Profil conservé')
        dialog.target.setValue(0);dialog.maximum.setValue(480)
        dialog._item=dialog.build_item()
        return QDialog.DialogCode.Accepted
    monkeypatch.setattr(EducatorDialog,'exec',accept)
    try:
        window.edit_home_educator(plan.educators[0].id)
        assert repo.list_days()==[]
        assert repo.is_day_deleted(plan.planning_date)
        assert repo.latest_week().educators[0].name=='Profil conservé'
    finally:
        window.autosave.stop();window.dirty=False;window.close();window.deleteLater();qapp.processEvents()
