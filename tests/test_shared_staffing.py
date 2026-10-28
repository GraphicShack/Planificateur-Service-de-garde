from copy import deepcopy
from gardeplan.models import Break,Week,Window,Shift
from gardeplan.coverage import coverage_timeline,merged_coverage,coverage_counts
from gardeplan.validation import validate
from gardeplan.alerts import visible_alerts,alert_text
from gardeplan.staffing import adopt_current_draft_rules
from test_two_per_group import covered_groups


def shared_day():
    plan=covered_groups()
    adopt_current_draft_rules(plan)
    for i in (1,3):
        plan.shifts[i].start=420;plan.shifts[i].buffer_before=0
    for i in (5,7):
        plan.shifts[i].end=1020;plan.shifts[i].buffer_after=0
    return plan


def test_two_total_from_650_to_700_and_1700_to_1735():
    plan=shared_day()
    assert not [i for i in validate(plan) if i.severity=='error']
    parts=coverage_timeline(plan)
    for minute in (410,419,1020,1049,1050,1054):
        part=next(p for p in parts if p.start<=minute<p.end)
        assert (part.actual,part.required,part.shared,part.complete)==(2,2,True,True)
    for minute in (420,1019):
        part=next(p for p in parts if p.start<=minute<p.end)
        assert part.required==4 and not part.shared
    assert any(p.start==1020 for p in merged_coverage(plan))
    assert 'Tous les groupes' in coverage_counts(parts[0])


def test_one_person_in_the_pool_is_reported_once_in_plain_language():
    plan=shared_day();plan.shifts[4].breaks=[Break(1033,1034,True)]
    issues=[i for i in visible_alerts(plan) if i.code=='shared_coverage']
    assert len(issues)==1 and (issues[0].start,issues[0].end)==(1033,1034)
    assert 'Tous les groupes' in alert_text(plan,issues[0],global_scope=True)
    assert '1 éducatrice au lieu de 2' in alert_text(plan,issues[0],global_scope=True)
    assert not any(i.group_id=='B' and i.start is not None and i.start>=1020 for i in validate(plan))


def test_one_per_group_before_1700_is_still_invalid_to_the_minute():
    plan=shared_day();plan.shifts[5].end=1019
    errors=[i for i in validate(plan) if i.code=='coverage' and i.group_id=='B']
    assert any((i.start,i.end)==(1019,1020) for i in errors)


def test_all_children_keep_their_ratio_during_shared_care_and_buffers_do_not_cover():
    plan=shared_day();plan.groups[0].periods[0].students=40
    part=next(p for p in coverage_timeline(plan) if p.start==1020)
    assert (part.actual,part.required,part.complete)==(2,3,False)
    assert any(i.code=='shared_coverage' and i.start==1020 for i in validate(plan))
    plan=shared_day();plan.shifts[4].buffer_after=40
    assert any(p.actual==1 and p.required==2 for p in coverage_timeline(plan) if p.start==1020)


def test_strict_archived_versions_stay_frozen_and_drafts_adopt_shared_care():
    plan=covered_groups();plan.status='archived';before=deepcopy(plan)
    assert not adopt_current_draft_rules(plan) and plan==before
    assert next(p for p in coverage_timeline(plan) if p.start<=1020<p.end).required==4
    plan.status='draft';assert adopt_current_draft_rules(plan)
    assert plan.settings.staffing_policy==4
    assert next(p for p in coverage_timeline(plan) if p.start<=1020<p.end).required==2
    assert Week.from_dict(plan.to_dict()).settings.staffing_policy==4


def test_shared_handover_can_use_a_predecessor_from_another_group():
    plan=shared_day()
    for i in (4,6):plan.shifts[i].end=1035;plan.shifts[i].buffer_after=0
    # B has no staff after 17 h. Two B educators arrive at 17 h and start
    # covering at 17 h 15, after 15 minutes with the A closing team.
    for i in (1,3):
        plan.shifts.append(Shift('late'+str(i),str(i),'B',0,1020,1055,15,5))
    assert not [i for i in validate(plan) if i.severity=='error']
    assert all(p.complete for p in coverage_timeline(plan))


def test_generation_preserves_two_total_and_can_release_one_whole_group_at_1700():
    from gardeplan.optimizer import generate
    from test_group_generation import grouped_day
    plan=grouped_day(8)
    # All the B closers can leave at 17 h; the A pair can close the whole school.
    for i in (5,7):plan.educators[i].availability=[Window(0,420,1020)]
    result=generate(plan,25)
    assert result.success,result.message+str(result.diagnostics)
    assert all(part.complete for part in coverage_timeline(result.proposal))
    assert not [i for i in validate(result.proposal) if i.severity=='error']
