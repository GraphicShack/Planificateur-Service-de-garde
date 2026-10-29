from copy import deepcopy
import pytest
from gardeplan.models import Educator,Shift,Week
from gardeplan.preferences import preference_cost,unmet_preferences
from gardeplan.validation import validate


@pytest.mark.parametrize('preference,expected',[('none','early'),('opening','early'),('closing','late')])
def test_rank_objective_uses_preferences_only_after_equal_hours_and_continuity(preference,expected):
    from ortools.sat.python import cp_model
    from gardeplan.optimizer import _Candidate
    from gardeplan.optimizer_priorities import solve_daily
    from gardeplan.daily import day_plan
    plan=day_plan('2026-10-28');person=Educator('p','Camille',max_minutes=240,shift_preference=preference)
    plan.educators=[person]
    choices=[_Candidate(Shift('early','p','g',0,410,650),240),_Candidate(Shift('late','p','g',0,815,1055),240)]
    model=cp_model.CpModel()
    for c in choices:c.variable=model.new_bool_var(c.shift.id)
    model.add(sum(c.variable for c in choices)==1)
    total=model.new_int_var(0,240,'paid');model.add(total==sum(c.paid*c.variable for c in choices))
    solver,status,_,_=solve_daily(model,choices,{'p':choices},{'p':total},plan,2)
    assert status in (cp_model.OPTIMAL,cp_model.FEASIBLE)
    assert next(c.shift.id for c in choices if solver.boolean_value(c.variable))==expected


def test_preferences_are_optional_warnings_and_exact_departure_is_serialized(tmp_path):
    from test_home_data import planned_day
    from gardeplan.storage import Repository
    plan=planned_day();person=plan.educators[0]
    person.shift_preference='closing';person.avoid_split=True;person.preferred_end=777
    before=deepcopy(plan)
    issues=validate(plan)
    assert any(i.code=='shift_preference' and i.severity=='warning' and '12 h 57' in i.message for i in issues)
    assert not any(i.code=='shift_preference' and i.severity=='error' for i in issues)
    repo=Repository(tmp_path/'prefs.sqlite');repo.save(plan)
    assert repo.load_day(plan.planning_date).educators[0].preferred_end==777
    assert Week.from_dict(plan.to_dict())==before
    raw=plan.to_dict();raw['educators'][0]['preferred_end']=12.5
    with pytest.raises(ValueError):Week.from_dict(raw)


def test_split_preference_counts_real_interruptions_not_adjacent_group_changes_or_lunch():
    from gardeplan.daily import day_plan
    from gardeplan.models import Break
    plan=day_plan('2026-10-28');person=Educator('p','Camille',avoid_split=True)
    adjacent=[Shift('a','p','A',0,500,600),Shift('b','p','B',0,600,700)]
    assert preference_cost(plan,person,adjacent)==0
    assert not unmet_preferences(plan,person,adjacent)
    adjacent[1].start=615
    assert preference_cost(plan,person,adjacent)==1456
    assert unmet_preferences(plan,person,adjacent)
    assert not unmet_preferences(plan,person,[Shift('c','p','A',0,500,700,breaks=[Break(600,630)])])


def test_profile_edits_structured_preferences_in_the_existing_window(qapp):
    from test_home_data import planned_day
    from gardeplan.ui.forms import EducatorDialog
    plan=planned_day();dialog=EducatorDialog(plan,plan.educators[0])
    try:
        dialog.shift_preference.setCurrentIndex(dialog.shift_preference.findData('closing'))
        dialog.avoid_split.setChecked(True)
        dialog.preferred_end_enabled.setChecked(True)
        dialog.preferred_end.setValue(917)
        person=dialog.build_item()
        assert (person.shift_preference,person.avoid_split,person.preferred_end)==('closing',True,917)
        assert dialog.preferred_end.isEnabled()
        assert not hasattr(dialog,'tabs')
    finally:dialog.close();dialog.deleteLater();qapp.processEvents()
