from copy import deepcopy
from gardeplan.attendance import is_absent, set_day_absence
from gardeplan.coverage import coverage_timeline
from gardeplan.daily import day_plan, duplicate_day
from gardeplan.models import Shift, Week
from gardeplan.storage import Repository
from gardeplan.validation import validate


def test_day_absence_removes_only_unlocked_assignments_and_preserves_the_profile():
    from test_group_generation import grouped_day
    plan=grouped_day()
    plan.shifts=[Shift('remove','0','A',0,600,700),Shift('keep','0','A',0,800,900,locked=True),Shift('other','1','A',0,600,900)]
    before=deepcopy(plan)
    result=set_day_absence(plan,'0',True)
    assert plan==before and result.educators==before.educators
    assert {s.id for s in result.shifts}=={'keep','other'}
    assert is_absent(result,'0') and result.educators[0].active
    assert any(i.code=='absence' and 'keep' in i.shift_ids for i in validate(result))
    assert next(p for p in coverage_timeline(result) if p.start<=820<p.end).actual==1
    assert not is_absent(set_day_absence(result,'0',False),'0')


def test_absence_is_saved_and_does_not_propagate_to_other_dates(tmp_path):
    from test_group_generation import grouped_day
    plan=set_day_absence(grouped_day(),'0',True)
    repo=Repository(tmp_path/'absence.sqlite');version=repo.save(plan)
    assert repo.load_day(plan.planning_date).absent_educator_ids==['0']
    assert repo.load_version(version).absent_educator_ids==['0']
    assert not day_plan('2026-10-29',plan).absent_educator_ids
    assert not duplicate_day(plan,'2026-10-29').absent_educator_ids
    assert Week.from_dict(plan.to_dict())==plan


def test_older_snapshots_load_with_optional_fields_missing():
    from test_group_generation import grouped_day
    raw=grouped_day().to_dict()
    raw.pop('absent_educator_ids')
    for person in raw['educators']:
        for key in ('shift_preference','avoid_split','preferred_end'):person.pop(key)
    loaded=Week.from_dict(raw)
    assert not loaded.absent_educator_ids
    assert all(e.shift_preference=='none' and not e.avoid_split and e.preferred_end is None for e in loaded.educators)


def test_absent_guarantees_and_targets_do_not_force_hours_or_warnings():
    from test_generation_priorities import short_day
    from gardeplan.optimizer import generate
    plan=short_day();plan.educators[0].guaranteed_minutes=120;plan.educators[0].target_minutes=240
    plan=set_day_absence(plan,'0',True)
    assert not [i for i in validate(plan) if i.code in {'guarantee','target','seniority'}]
    result=generate(plan,6)
    assert result.success,result.message+str(result.diagnostics)
    assert not any(s.educator_id=='0' for s in result.proposal.shifts)
    assert not [i for i in validate(result.proposal) if i.severity=='error']


def test_absence_card_is_keyboard_operable_and_undo_restores_assignments(tmp_path,qapp):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from gardeplan.ui.main_window import MainWindow
    from test_home_data import planned_day
    plan=planned_day();repo=Repository(tmp_path/'ui.sqlite');repo.save(plan)
    window=MainWindow(repo,plan,start_home=False);window.show();qapp.processEvents()
    before=deepcopy(window.week)
    try:
        button=window.absence_buttons[plan.educators[0].id]
        assert button.height()>=44
        button.setFocus();QTest.keyClick(button,Qt.Key.Key_Space)
        assert is_absent(window.week,plan.educators[0].id)
        assert not any(s.educator_id==plan.educators[0].id and not s.locked for s in window.week.shifts)
        window.undo();assert window.week==before
        window.redo();assert is_absent(window.week,plan.educators[0].id)
    finally:
        window.autosave.stop();window.dirty=False;window.close();window.deleteLater();qapp.processEvents()
