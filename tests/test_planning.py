from copy import deepcopy
import pytest
from gardeplan.models import Group, GroupPeriod, required_educators
from gardeplan.planning import plan_pedagogical_day
from gardeplan.validation import validate


def _periods(week, day):
    return [(group, period) for group in week.groups for period in group.periods if period.day == day]


def test_daily_registrations_create_groups_without_touching_other_days(valid_week):
    before = deepcopy(valid_week)
    result = plan_pedagogical_day(valid_week, 1, 41, 20, "Pédagogique — Halloween")
    periods = _periods(result, 1)
    assert len(periods) == 3
    assert [p.students for _, p in periods] == [20, 20, 1]
    assert all((p.start, p.end) == (420, 1050) for _, p in periods)
    assert result.day_names[1] == "Pédagogique — Halloween"
    assert [(g.id, p) for g, p in _periods(result, 0)] == [(g.id, p) for g, p in _periods(before, 0)]
    assert result.shifts == before.shifts
    assert result.activities == before.activities
    assert valid_week == before
    assert len({g.id for g in result.groups}) == 3
    assert len({g.name for g in result.groups}) == 3


def test_group_size_is_independent_of_staffing_ratio(valid_week):
    result = plan_pedagogical_day(valid_week, 0, 41, 50)
    [(group, period)] = _periods(result, 0)
    assert period.students == 41
    assert group.ratio == 20
    assert required_educators(group, period.students) == 3
    assert any(issue.code == 'ratio' for issue in validate(result))


def test_lower_registration_closes_surplus_groups_but_keeps_other_days(valid_week):
    valid_week.groups.append(Group('g2', 'Les papillons', periods=[
        GroupPeriod(0, 420, 1050, 10), GroupPeriod(1, 420, 1050, 20)
    ]))
    result = plan_pedagogical_day(valid_week, 0, 18, 20)
    assert len(_periods(result, 0)) == 1
    assert _periods(result, 0)[0][1].students == 18
    assert result.groups[1].name == 'Les papillons'
    assert result.groups[1].periods == [GroupPeriod(1, 420, 1050, 20)]
    assert result.shifts == valid_week.shifts


def test_zero_registration_closes_day_without_deleting_quarts(valid_week):
    result = plan_pedagogical_day(valid_week, 0, 0)
    assert not _periods(result, 0)
    assert result.shifts == valid_week.shifts
    issues = validate(result)
    assert any(issue.code == 'closed_group_shift' and issue.severity == 'warning' for issue in issues)
    assert not any(issue.code in {'opening', 'closing', 'school_coverage', 'coverage'} for issue in issues)


def test_optional_name_preserved_changed_and_cleared(valid_week):
    assert plan_pedagogical_day(valid_week, 0, 30).day_names == valid_week.day_names
    assert plan_pedagogical_day(valid_week, 0, 30, name=' Fête ').day_names[0] == 'Fête'
    assert 0 not in plan_pedagogical_day(valid_week, 0, 30, name='').day_names


def test_replanning_published_week_creates_draft(valid_week):
    valid_week.status = 'published'
    result = plan_pedagogical_day(valid_week, 0, 30)
    assert result.status == 'draft'
    assert valid_week.status == 'published'


@pytest.mark.parametrize('day, registrations, size', [
    (-1, 20, 20), (5, 20, 20), (True, 20, 20),
    (0, -1, 20), (0, 20.5, 20), (0, True, 20),
    (0, 20, 0), (0, 20, -2), (0, 20, 20.5),
])
def test_invalid_inputs_rejected(valid_week, day, registrations, size):
    with pytest.raises(ValueError):
        plan_pedagogical_day(valid_week, day, registrations, size)
