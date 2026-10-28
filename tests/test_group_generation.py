from copy import deepcopy
from gardeplan.daily import day_plan
from gardeplan.models import Educator,Group,GroupPeriod,Shift,Window,Break,totals
from gardeplan.coverage import coverage_timeline,merged_coverage,coverage_state
from gardeplan.validation import validate
from gardeplan.alerts import visible_alerts,alert_text
from gardeplan.optimizer import generate


def grouped_day(people=4):
    plan=day_plan('2026-10-28')
    plan.groups=[Group(g,'Groupe '+g,periods=[GroupPeriod(0,420,1050,20)]) for g in ('A','B')]
    plan.educators=[Educator(str(i),f'Éducatrice {i}',seniority=i+1,target_minutes=0,max_minutes=480) for i in range(people)]
    return plan


def test_other_groups_surplus_cannot_hide_an_empty_group():
    plan=grouped_day()
    plan.shifts=[Shift(str(i),str(i),'A',0,600,800) for i in range(2)]
    part=next(p for p in coverage_timeline(plan) if p.start==600)
    assert (part.actual,part.required,part.missing,part.complete)==(2,2,1,False)
    assert coverage_state(part)==('shortage','Manque 1')
    assert any(p.missing==1 for p in merged_coverage(plan))
    issues=[i for i in visible_alerts(plan) if i.group_id=='B' and i.code=='coverage']
    assert issues and 'Groupe B' in alert_text(plan,issues[0],global_scope=True)
    assert '0 éducatrices au lieu de 1' in alert_text(plan,issues[0],global_scope=True)


def test_paid_break_removes_coverage_from_the_correct_group():
    plan=grouped_day()
    plan.shifts=[Shift(str(i),str(i),g,0,600,800) for i,g in enumerate(('A','B'))]
    plan.shifts[1].breaks=[Break(733,734,True)]
    part=next(p for p in coverage_timeline(plan) if p.start==733)
    assert part.missing==1 and not part.complete


def test_generate_covers_both_groups_without_modifying_the_source():
    plan=grouped_day();before=deepcopy(plan)
    result=generate(plan,20)
    assert result.success,result.message+str(result.diagnostics)
    assert plan==before
    assert {s.group_id for s in result.proposal.shifts}=={'A','B'}
    assert all(part.complete for group in plan.groups for part in coverage_timeline(result.proposal,group_id=group.id) if 420<=part.start<1050)
    assert all(m<=480 for m in totals(result.proposal).values())
    assert not [i for i in validate(result.proposal) if i.severity=='error']


def test_locked_group_and_hours_are_preserved_and_impossible_capacity_is_reported():
    plan=grouped_day();fixed=Shift('fixed','0','B',0,410,890,10,locked=True)
    plan.shifts=[fixed]
    result=generate(plan,20)
    assert result.success,result.message+str(result.diagnostics)
    assert next(s for s in result.proposal.shifts if s.id=='fixed')==fixed
    impossible=grouped_day(2)
    result=generate(impossible,5)
    assert not result.success and result.proposal is None
