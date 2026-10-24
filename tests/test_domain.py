from copy import deepcopy
from dataclasses import replace
import pytest
from gardeplan.models import (
    Week, Shift, Break, Window, Room, Activity, Group, GroupPeriod,
    Educator, paid_minutes, presence_minutes, coverage_intervals, move_shift, totals,
)
from gardeplan.validation import validate


def errors(week, code=None):
    return [issue for issue in validate(week)
            if issue.severity == 'error' and (code is None or issue.code == code)]


def test_valid_continuous_day_with_two_educators(valid_week):
    assert not errors(valid_week)
    assert totals(valid_week) == {'e1': 645, 'e2': 645}


def test_shift_one_hour_forty_two_minutes():
    shift = Shift(id='s', educator_id='e', group_id='g', day=0,
                  start=433, end=535)
    assert presence_minutes(shift) == 102
    assert paid_minutes(shift) == 102
    assert coverage_intervals(shift) == [(433, 535)]


def test_move_preserves_exact_duration_and_break_position():
    shift = Shift(id='s', educator_id='e', group_id='g', day=0,
                  start=433, end=535, breaks=[Break(start=470, end=480)])
    moved = move_shift(shift, day=1, start=677, group_id='other')
    # Accept helpers that mutate and return the object, or only mutate.
    moved = shift if moved is None else moved
    assert (moved.day, moved.start, moved.end, moved.group_id) == (1, 677, 779, 'other')
    assert (moved.breaks[0].start, moved.breaks[0].end) == (714, 724)
    assert paid_minutes(moved) == 92


def test_resize_to_arbitrary_minute():
    shift = Shift(id='s', educator_id='e', group_id='g', day=0,
                  start=433, end=535)
    shift.end = 536
    assert paid_minutes(shift) == 103
    shift.start = 434
    assert paid_minutes(shift) == 102


def test_one_educator_is_blocking(valid_week):
    valid_week.shifts.pop()
    issues = errors(valid_week, 'coverage')
    assert issues
    assert any(issue.start == 420 and issue.end == 1050 for issue in issues)


def test_ratio_twenty_requires_third_educator_at_41(valid_week):
    valid_week.groups[0].periods[0].students = 41
    assert errors(valid_week, 'ratio')
    valid_week.groups[0].periods[0].students = 40
    assert not errors(valid_week, 'ratio')


def test_closed_group_requires_no_staff():
    week = Week(monday='2026-10-26', groups=[Group(id='g', name='Fermé', color='#111111')])
    assert not errors(week, 'coverage')
    assert not errors(week, 'opening')


def test_paid_preparation_is_not_pupil_coverage(valid_week):
    shift = valid_week.shifts[0]
    shift.buffer_before = 25
    assert paid_minutes(shift) == 645
    assert coverage_intervals(shift)[0][0] == 435
    assert errors(valid_week, 'coverage')


def test_unpaid_buffer_and_break_are_not_double_subtracted():
    shift = Shift(id='s', educator_id='e', group_id='g', day=0,
                  start=410, end=535, buffer_before=10, before_paid=False,
                  breaks=[Break(start=410, end=425, paid=False)])
    assert paid_minutes(shift) == 110


def test_pause_creates_coverage_gap(valid_week):
    valid_week.shifts[0].breaks = [Break(start=720, end=750, paid=False)]
    assert totals(valid_week)['e1'] == 615
    assert any(i.start == 720 and i.end == 750 for i in errors(valid_week, 'coverage'))


def test_opening_and_closing_require_two(valid_week):
    valid_week.shifts[0].start = 420
    valid_week.shifts[0].buffer_before = 0
    assert errors(valid_week, 'opening')
    valid_week.shifts[0].start = 410
    valid_week.shifts[0].buffer_before = 10
    valid_week.shifts[0].end = 1050
    valid_week.shifts[0].buffer_after = 0
    assert errors(valid_week, 'closing')


def test_no_school_coverage_hole(valid_week):
    valid_week.groups[0].periods = [
        GroupPeriod(day=0, start=420, end=720, students=30),
        GroupPeriod(day=0, start=730, end=1050, students=30),
    ]
    morning = [replace(s, end=720, buffer_after=0) for s in valid_week.shifts]
    afternoon = [replace(s, id=s.id + '-pm', start=730, buffer_before=0)
                 for s in valid_week.shifts]
    valid_week.shifts = morning + afternoon
    assert errors(valid_week, 'school_coverage')


def test_replacement_needs_fifteen_minutes_shared_presence(valid_week):
    replacement = deepcopy(valid_week.educators[0])
    replacement.id = 'e3'
    replacement.name = 'Sophie Gagnon'
    valid_week.educators.append(replacement)
    outgoing = valid_week.shifts[0]
    outgoing.end = 750
    outgoing.buffer_after = 0
    incoming = Shift(id='s3', educator_id='e3', group_id='g1', day=0,
                     start=750, end=1055, buffer_after=5)
    valid_week.shifts.append(incoming)
    assert errors(valid_week, 'handover')
    incoming.start = 735
    incoming.buffer_before = 15
    assert not errors(valid_week, 'handover')
    assert not errors(valid_week, 'coverage')


def test_overlapping_groups_for_same_person_blocking(valid_week):
    valid_week.groups.append(Group(id='g2', name='B', color='#777777'))
    valid_week.shifts.append(Shift(id='s3', educator_id='e1', group_id='g2',
                                   day=0, start=700, end=800))
    assert errors(valid_week, 'overlap')


def test_absence_and_weekly_max_are_mandatory(valid_week):
    valid_week.educators[0].absences = [Window(day=0, start=700, end=750)]
    valid_week.educators[0].max_minutes = 600
    assert errors(valid_week, 'absence')
    assert errors(valid_week, 'max_hours')


def test_room_conflict_capacity_and_unavailable(valid_week):
    valid_week.rooms = [Room(id='r', name='Gymnase', capacity=20, shared=False,
                            availability=[Window(day=0, start=800, end=1000)])]
    valid_week.activities = [
        Activity(id='a1', name='Sports', group_id='g1', day=0,
                 start=700, end=850, room_id='r'),
        Activity(id='a2', name='Jeux', group_id='g1', day=0,
                 start=750, end=900, room_id='r'),
    ]
    assert errors(valid_week, 'room_conflict')
    assert errors(valid_week, 'room_capacity')
    assert errors(valid_week, 'room_unavailable')


def test_outdoor_activity_location_changes_leave_shifts_exact(valid_week):
    valid_week.rooms = [Room(id='yard', name='Cour extérieure', capacity=100, outdoor=True),
                        Room(id='park', name='Parc', capacity=100, outdoor=True)]
    valid_week.activities = [Activity(id='a', name='Jeux extérieurs', group_id='g1',
                                     day=0, start=840, end=960, room_id='yard')]
    before = [(s.start, s.end, paid_minutes(s)) for s in valid_week.shifts]
    valid_week.activities[0].room_id = 'park'
    assert not errors(valid_week)
    assert before == [(s.start, s.end, paid_minutes(s)) for s in valid_week.shifts]


def test_named_day_roundtrip(valid_week):
    restored = Week.from_dict(valid_week.to_dict())
    assert restored.day_names == valid_week.day_names
    assert restored.shifts[0].start == 410


@pytest.mark.parametrize('value', [420.5, True, '07:00'])
def test_non_integer_minutes_rejected_on_import(valid_week, value):
    data = valid_week.to_dict()
    data['shifts'][0]['start'] = value
    with pytest.raises((ValueError, TypeError)):
        Week.from_dict(data)


def test_compatible_activities_of_one_group_can_use_nonshared_room(valid_week):
    valid_week.rooms = [Room(id='r', name='Local 101', capacity=40, shared=False)]
    valid_week.activities = [
        Activity(id='a1', name='Dessin', group_id='g1', day=0,
                 start=700, end=800, room_id='r', compatible=True),
        Activity(id='a2', name='Musique', group_id='g1', day=0,
                 start=750, end=850, room_id='r', compatible=True),
    ]
    assert not errors(valid_week, 'room_conflict')
    assert not errors(valid_week, 'activity_overlap')
    assert not errors(valid_week, 'room_capacity'), 'Les mêmes enfants ne sont pas comptés deux fois.'
    valid_week.activities[1].compatible = False
    assert errors(valid_week, 'room_conflict')
    assert errors(valid_week, 'activity_overlap')


def test_imported_settings_cannot_disable_required_open_close_and_handover(valid_week):
    valid_week.settings.opening_buffer = 0
    valid_week.settings.closing_buffer = 0
    valid_week.settings.handover_minutes = 0
    for shift in valid_week.shifts:
        shift.start, shift.end = 420, 1050
        shift.buffer_before = shift.buffer_after = 0
    assert errors(valid_week, 'missing_data')


@pytest.mark.parametrize('value', [True, '1.0', float('nan'), float('inf'), 0, 10])
def test_invalid_zoom_rejected_without_accepting_malformed_backup(valid_week, value):
    data = valid_week.to_dict()
    data['settings']['zoom'] = value
    with pytest.raises((ValueError, TypeError)):
        Week.from_dict(data)


@pytest.mark.parametrize('names', [{True: 'Mardi'}, {1.5: 'Mardi'}, {'01': 'Mardi'}, {1: 'Mardi', '1': 'Doublon'}])
def test_invalid_or_duplicated_day_name_keys_rejected(valid_week, names):
    data = valid_week.to_dict()
    data['day_names'] = names
    with pytest.raises((ValueError, TypeError)):
        Week.from_dict(data)
