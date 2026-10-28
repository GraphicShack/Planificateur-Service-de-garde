from gardeplan.models import Shift,Break
from gardeplan.validation import validate
from gardeplan.coverage import coverage_timeline
from test_group_generation import grouped_day


def covered_groups():
    plan=grouped_day(8)
    plan.settings.staffing_policy=3
    plan.shifts=[Shift(str(i),str(i),'A' if i%2==0 else 'B',0,
                      410 if i<4 else 720,735 if i<4 else 1055,
                      10 if i<4 else 15,0 if i<4 else 5) for i in range(8)]
    return plan


def test_two_per_group_through_opening_closing_breaks_and_handovers():
    plan=covered_groups()
    assert not [i for i in validate(plan) if i.severity=='error']
    for group in plan.groups:
        assert all(p.complete and p.required==2 for p in coverage_timeline(plan,group_id=group.id))
    assert coverage_timeline(plan)[0].required==4
    assert coverage_timeline(plan)[-1].required==4
    plan.shifts[0].breaks=[Break(600,630,True)]
    assert any(i.code=='coverage' and i.group_id=='A' and (i.start,i.end)==(600,630) for i in validate(plan))


def test_one_per_group_is_an_error_even_in_the_last_fifteen_minutes():
    plan=covered_groups()
    # One closer from each group leaves at 17 h 20.
    for i in (6,7):plan.shifts[i].end=1040;plan.shifts[i].buffer_after=0
    parts=coverage_timeline(plan)
    late=next(p for p in parts if p.start==1040)
    assert (late.actual,late.required,late.complete)==(2,4,False)
    for group in ('A','B'):
        assert any(i.code=='coverage' and i.group_id==group and i.start==1040 for i in validate(plan))


def test_school_preparation_and_closing_require_two_in_each_group():
    plan=covered_groups()
    plan.shifts[0].start=420;plan.shifts[0].buffer_before=0
    plan.shifts[4].end=1050;plan.shifts[4].buffer_after=0
    issues=validate(plan)
    assert any(i.code=='opening' and i.group_id=='A' and (i.start,i.end)==(410,420) for i in issues)
    assert any(i.code=='closing' and i.group_id=='A' and (i.start,i.end)==(1050,1055) for i in issues)


def test_registration_preview_sums_groups_and_keeps_the_configured_ratio(qapp):
    from gardeplan.ui.enrolment import EnrolmentPanel
    plan=grouped_day()
    panel=EnrolmentPanel(plan)
    try:
        for count,minimum in ((5,2),(40,4),(41,6)):
            panel.count.setValue(count)
            assert f'minimum {minimum} éducatrices' in panel.preview.text()
        for group in plan.groups:group.ratio=5
        panel.load_week(plan);panel.count.setValue(41)
        assert 'minimum 10 éducatrices' in panel.preview.text()
    finally:panel.deleteLater();qapp.processEvents()
