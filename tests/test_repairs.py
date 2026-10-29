from copy import deepcopy
import pytest
from gardeplan.comparison import compare
from gardeplan.models import Break,Educator
from gardeplan.repairs import repair
from gardeplan.validation import validate


def gap_day():
    from test_home_data import planned_day
    plan=planned_day()
    # The shared test day is already valid, within the daily cap.
    plan.shifts[0].breaks=[Break(600,630)]
    plan.educators.extend([Educator('reserve','Camille',seniority=3,target_minutes=0,max_minutes=480),
                           Educator('reserve2','Sophie',seniority=4,target_minutes=0,max_minutes=480)])
    return plan


def gap_issue(plan):
    return next(i for i in validate(plan) if i.code in {'coverage','ratio'} and i.start==600)


def test_local_repair_fixes_the_selected_gap_keeps_existing_shifts_and_respects_rank():
    plan=gap_day();before=deepcopy(plan)
    result=repair(plan,gap_issue(plan))
    assert result.success,result.message
    assert plan==before
    assert not [i for i in validate(result.proposal) if i.severity=='error']
    assert all(s in result.proposal.shifts for s in before.shifts)
    changes=compare(before,result.proposal)
    assert len(changes)==1 and changes[0].after.educator_id=='reserve'
    assert changes[0].after.start==585 and changes[0].after.end==630


def test_local_repair_leaves_an_unrelated_existing_gap_untouched():
    plan=gap_day();plan.shifts[1].breaks=[Break(700,715)]
    result=repair(plan,gap_issue(plan))
    assert result.success,result.message
    assert any(i.start==700 and i.severity=='error' for i in validate(result.proposal))
    assert not any(i.start==600 and i.code in {'coverage','ratio'} for i in validate(result.proposal))
    assert all(s in result.proposal.shifts for s in plan.shifts)


def test_impossible_local_repair_has_no_partial_result_or_mutation():
    plan=gap_day();plan.educators=plan.educators[:2]
    before=deepcopy(plan)
    result=repair(plan,gap_issue(plan))
    assert not result.success and result.proposal is None
    assert plan==before
    assert 'Aucun quart' in result.message


def test_local_repair_preserves_locks_and_never_exceeds_a_daily_maximum():
    plan=gap_day();plan.shifts[0].locked=True
    plan.educators[2].max_minutes=10
    result=repair(plan,gap_issue(plan))
    assert result.success,result.message
    assert next(s for s in result.proposal.shifts if s.id==plan.shifts[0].id)==plan.shifts[0]
    assert any(s.educator_id=='reserve2' for s in result.proposal.shifts)
    assert not any(s.educator_id=='reserve' for s in result.proposal.shifts)


def test_repair_can_extend_a_nearby_unlocked_shift_instead_of_adding_one():
    from gardeplan.models import Shift
    plan=gap_day();plan.shifts.append(Shift('nearby','reserve','g',0,500,600,15))
    result=repair(plan,gap_issue(plan))
    assert result.success,result.message
    changes=compare(plan,result.proposal)
    assert len(changes)==1 and changes[0].label=='Modifié'
    assert changes[0].after.id=='nearby' and changes[0].after.end==630


def test_repair_can_add_two_people_to_fix_a_ratio_deficit_without_hiding_other_errors():
    plan=gap_day();plan.groups[0].periods[0].students=60
    result=repair(plan,gap_issue(plan))
    assert result.success,result.message
    assert len(compare(plan,result.proposal))==2
    assert not any(i.start==600 and i.code in {'coverage','ratio'} for i in validate(result.proposal))
    assert any(i.code=='ratio' for i in validate(result.proposal))


@pytest.mark.parametrize('accept',[False,True])
def test_correction_button_uses_real_background_worker_and_preview_before_apply(qapp,tmp_path,monkeypatch,accept):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QDialog
    from PySide6.QtTest import QTest
    from gardeplan.storage import Repository
    from gardeplan.ui.main_window import MainWindow
    plan=gap_day();repo=Repository(tmp_path/'repair.sqlite');repo.save(plan)
    window=MainWindow(repo,plan,start_home=False);window.show();qapp.processEvents()
    before=deepcopy(window.week)
    seen=[]
    def decline(dialog):
        seen.append(dialog.changes_table.rowCount())
        return QDialog.DialogCode.Accepted if accept else QDialog.DialogCode.Rejected
    monkeypatch.setattr('gardeplan.ui.proposal.ProposalDialog.exec',decline)
    try:
        window.verify()
        for row in range(window.alert_list.count()):
            item=window.alert_list.item(row);issue=item.data(Qt.ItemDataRole.UserRole)
            if issue and issue.start==600:
                window.alert_list.setCurrentItem(item);break
        assert window.repair_button.isEnabled()
        window.repair_button.click()
        assert window._worker is not None and window._progress.isVisible()
        for _ in range(600):
            if window._worker is None:break
            QTest.qWait(20)
        assert window._worker is None and seen==[1]
        if accept:
            assert len(compare(before,window.week))==1
            window.undo()
        assert window.week==before
    finally:
        if window._worker is not None:
            window._worker.wait(15000)
            qapp.processEvents()
        window.autosave.stop();window.dirty=False;window.close();window.deleteLater();qapp.processEvents()
