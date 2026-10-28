from gardeplan.models import Window,totals
from gardeplan.optimizer import generate
from gardeplan.validation import validate
from test_group_generation import grouped_day


def short_day():
    plan=grouped_day()
    plan.settings.close_minute=660
    for group in plan.groups:group.periods[0].end=660
    for person,rank in zip(plan.educators,(1,4,8,11)):person.seniority=rank
    return plan


def quality(plan,person):
    shifts=[s for s in plan.shifts if s.educator_id==person.id]
    return (-len(shifts),totals(plan).get(person.id,0),-max((s.end for s in shifts),default=0))


def test_everyone_gets_hours_and_sparse_ranks_receive_the_best_schedules_first():
    plan=short_day()
    result=generate(plan,12)
    assert result.success,result.message+str(result.diagnostics)
    proposal=result.proposal
    assert all(totals(proposal).get(e.id,0)>0 for e in plan.educators)
    scores=[quality(proposal,e) for e in plan.educators]
    assert scores==sorted(scores,reverse=True)
    assert all(len([s for s in proposal.shifts if s.educator_id==e.id])==1 for e in plan.educators)
    assert not [i for i in validate(proposal) if i.severity=='error']


def test_unavailable_senior_is_named_without_blocking_available_staff():
    plan=short_day();plan.educators[0].absences=[Window(0,0,1440)]
    result=generate(plan,12)
    assert result.success,result.message+str(result.diagnostics)
    assert totals(result.proposal).get('0',0)==0
    assert all(totals(result.proposal).get(e.id,0)>0 for e in plan.educators[1:])
    assert any('Sans heures' in text and plan.educators[0].name in text for text in result.diagnostics)


def test_eight_hour_capacity_failure_is_explained_without_a_partial_proposal():
    result=generate(grouped_day(2),3)
    assert not result.success and result.proposal is None
    assert any('8 h 00' in text and 'équipe' in text for text in result.diagnostics)
