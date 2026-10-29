"""Do not save a few paid minutes by creating an unnecessary split schedule."""
import pytest
from ortools.sat.python import cp_model
from gardeplan.daily import day_plan
from gardeplan.models import Break,Educator,Shift,paid_minutes
from gardeplan.optimizer import _Candidate
from gardeplan.optimizer_priorities import solve_daily


def choose(*,cap=180,continuous=True,pause=False):
    plan=day_plan('2026-10-29')
    person=Educator('p','Camille',max_minutes=cap,avoid_split=False)
    plan.educators=[person]
    shifts=[Shift('debut','p','g',0,420,510,0,0),Shift('suite','p','g',0,525,600,0,0)]
    if continuous:
        shifts.append(Shift('continu','p','g',0,420,600,0,0,breaks=[Break(510,525)] if pause else []))
    choices=[_Candidate(s,paid_minutes(s)) for s in shifts]
    model=cp_model.CpModel()
    for c in choices:c.variable=model.new_bool_var(c.shift.id)
    model.add_no_overlap([model.new_optional_fixed_size_interval_var(c.shift.start,c.shift.end-c.shift.start,c.variable,c.shift.id) for c in choices])
    for required in (450,570):model.add(sum(c.variable for c in choices if c.shift.start<=required<c.shift.end)>=1)
    total=model.new_int_var(0,cap,'total');model.add(total==sum(c.paid*c.variable for c in choices))
    solver,status,_,_=solve_daily(model,choices,{'p':choices},{'p':total},plan,3)
    assert status in (cp_model.OPTIMAL,cp_model.FEASIBLE)
    return [c.shift for c in choices if solver.boolean_value(c.variable)]


def test_continuity_is_default_even_when_a_hole_would_save_fifteen_paid_minutes():
    chosen=choose()
    assert [s.id for s in chosen]==['continu']
    assert paid_minutes(chosen[0])==180


@pytest.mark.parametrize('settings',[{'cap':170},{'continuous':False}])
def test_required_gap_remains_when_limit_or_availability_prevents_continuity(settings):
    chosen=choose(**settings)
    assert [s.id for s in chosen]==['debut','suite']
    assert sum(paid_minutes(s) for s in chosen)==165


def test_unpaid_pause_remains_inside_the_continuous_shift():
    chosen=choose(pause=True)
    assert [s.id for s in chosen]==['continu']
    assert chosen[0].breaks==[Break(510,525)] and paid_minutes(chosen[0])==165


def test_touching_group_assignments_are_not_a_gap():
    from gardeplan.preferences import cp_interruptions
    model=cp_model.CpModel()
    choices=[_Candidate(Shift(str(i),'p',group,0,a,b,0,0),b-a) for i,(group,a,b) in enumerate([('a',420,510),('b',510,600)])]
    for c in choices:
        c.variable=model.new_bool_var(c.shift.id);model.add(c.variable==1)
    cut,gap=cp_interruptions(model,choices,600,'p')
    solver=cp_model.CpSolver();assert solver.solve(model)==cp_model.OPTIMAL
    assert solver.value(cut)==0 and solver.value(gap)==0
