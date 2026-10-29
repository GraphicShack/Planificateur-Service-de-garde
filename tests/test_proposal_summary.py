from copy import deepcopy
from gardeplan.models import Break,Educator,Shift
from gardeplan.proposal_summary import assess,proposal_summary


def test_report_counts_real_gaps_preferences_and_excludes_absences():
    from test_home_data import planned_day
    plan=planned_day()
    person=plan.educators[0];person.avoid_split=True;person.shift_preference='closing';person.preferred_end=800
    plan.educators.extend([Educator('free','Sans heures',seniority=3,target_minutes=0),
                           Educator('absent','Absente',seniority=4,target_minutes=0)])
    plan.absent_educator_ids=['absent']
    plan.shifts[0].end=600;plan.shifts[0].buffer_after=0
    plan.shifts.append(Shift('late',person.id,'g',0,630,855,0,5))
    data=assess(plan)
    assert data.split_names==(person.name,) and data.interruptions==1
    assert data.preferences_total==3 and data.preferences_met==1
    assert len(data.preference_messages)==2
    assert data.without_hours==('Sans heures',)


def test_lunch_and_adjacent_assignments_are_not_counted_as_split_schedules():
    from test_home_data import planned_day
    plan=planned_day();plan.shifts[0].breaks=[Break(600,630)]
    assert not assess(plan).split_names
    plan.shifts[0].breaks=[];plan.shifts[0].end=600;plan.shifts[0].buffer_after=0
    plan.shifts.append(Shift('next',plan.educators[0].id,'g',0,600,855,0,5))
    assert assess(plan).interruptions==0


def test_changed_locked_assignment_is_identified_and_cannot_be_applied(qapp):
    from test_home_data import planned_day
    from gardeplan.optimizer import GenerationResult
    from gardeplan.ui.proposal import ProposalDialog
    before=planned_day();before.shifts[0].locked=True
    after=deepcopy(before);after.shifts[0].start+=1
    report=proposal_summary(before,after)
    assert report['locks_total']==1 and report['locks_preserved']==0
    dialog=ProposalDialog(before,GenerationResult(True,after,'À vérifier','feasible'))
    try:
        assert not dialog.apply_button.isEnabled()
        assert dialog.tabs.tabText(0)=='Bilan'
        assert dialog.tabs.currentWidget() is dialog.calendars[1]
    finally:dialog.close();dialog.deleteLater();qapp.processEvents()


def test_no_preferences_and_closed_day_have_explicit_states():
    from gardeplan.daily import day_plan
    from gardeplan.models import Group
    plan=day_plan('2026-10-28');plan.groups=[Group('g','Groupe A')]
    data=assess(plan)
    assert data.coverage=='Journée fermée' and data.preferences_total==0
    plan.groups=[];assert assess(plan).coverage=='À renseigner'
