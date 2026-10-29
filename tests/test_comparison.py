from copy import deepcopy
from gardeplan.comparison import compare
from gardeplan.models import Break,new_id


def test_comparison_ignores_generated_ids_but_reports_real_changes():
    from test_home_data import planned_day
    before=planned_day();after=deepcopy(before)
    for shift in after.shifts:shift.id=new_id()
    assert not compare(before,after)
    after.shifts[0].start+=7
    changes=compare(before,after)
    assert len(changes)==1 and changes[0].label=='Modifié' and changes[0].delta==-7
    after.shifts[0].breaks=[Break(after.shifts[0].start+30,after.shifts[0].start+60)]
    assert compare(before,after)[0].delta==-37
    assert before.shifts[0].start!=after.shifts[0].start


def test_comparison_lists_added_and_removed_assignments():
    from test_home_data import planned_day
    before=planned_day();after=deepcopy(before)
    after.shifts=[]
    assert all(change.label=='Retiré' and change.delta<0 for change in compare(before,after))
    assert all(change.label=='Ajouté' and change.delta>0 for change in compare(after,before))


def test_proposal_displays_hours_changes_and_keyboard_location_without_modifying_data(qapp):
    from gardeplan.optimizer import GenerationResult
    from gardeplan.ui.proposal import ProposalDialog
    from test_home_data import planned_day
    before=planned_day();original=deepcopy(before);after=deepcopy(before)
    after.shifts[0].start+=7
    dialog=ProposalDialog(before,GenerationResult(True,after,'Proposition à vérifier','feasible'))
    dialog.show();qapp.processEvents()
    try:
        assert dialog.changes_table.rowCount()==1
        assert dialog.changes_table.item(0,1).text().startswith('Modifié')
        assert dialog.hours_table.rowCount()==len(after.educators)
        dialog.locate_change(0);qapp.processEvents()
        shift=after.shifts[0]
        assert dialog.tabs.currentWidget() is dialog.calendars[1]
        assert dialog.calendars[1].highlighted_interval==(shift.day,shift.start,shift.end)
        assert before==original
        dialog.reject();assert before==original
    finally:dialog.close();dialog.deleteLater();qapp.processEvents()
