"""Tests de la génération réelle, sans substituer un faux solveur."""
from copy import deepcopy

import pytest

pytest.importorskip("ortools")

from gardeplan.models import (
    Break, Educator, Group, GroupPeriod, Shift, Week, Window,
    coverage_intervals, paid_minutes,
)
from gardeplan.optimizer import generate, _build_candidates
from gardeplan.validation import validate


def week_for_generation(people=4):
    return Week(
        "2026-10-26",
        educators=[Educator(str(i), f"Éducatrice {i}", seniority=i + 1,
                            target_minutes=630, max_minutes=720) for i in range(people)],
        groups=[Group("g", "Groupe A", periods=[GroupPeriod(0, 420, 1050, 35)])],
    )


def test_impossible_explains_insufficient_staff_without_modification():
    week = week_for_generation(1)
    original = deepcopy(week.to_dict())
    result = generate(week, 2)
    assert not result.success
    assert result.status == "infeasible"
    assert any("seulement 1" in item for item in result.diagnostics)
    assert week.to_dict() == original


def test_generation_obeys_opening_closing_ratio_and_does_not_mutate():
    week = week_for_generation()
    original = deepcopy(week.to_dict())
    result = generate(week, 10)
    assert result.success, result.message + str(result.diagnostics)
    proposal = result.proposal
    assert proposal is not None
    assert not [i for i in validate(proposal) if i.severity == "error"]
    assert sum(s.start <= 410 and s.end >= 420 for s in proposal.shifts) >= 2
    assert sum(s.start <= 1050 and s.end >= 1055 for s in proposal.shifts) >= 2
    assert week.to_dict() == original


def test_locked_shift_and_exact_minute_availability_are_preserved():
    week = week_for_generation(4)
    week.educators[2].availability = [Window(0, 733, 1055)]
    locked = Shift("locked", "0", "g", 0, 410, 733,
                   buffer_before=10, locked=True)
    week.shifts = [locked]
    result = generate(week, 10)
    assert result.success, result.message + str(result.diagnostics)
    retained = next(s for s in result.proposal.shifts if s.id == "locked")
    assert retained == locked
    for shift in result.proposal.shifts:
        if shift.educator_id == "2":
            assert shift.start >= 733
            assert shift.end <= 1055


def test_generation_with_pause_keeps_continuous_coverage():
    week = week_for_generation(4)
    week.settings.break_minutes = 30
    week.settings.break_after_minutes = 360
    result = generate(week, 10)
    assert result.success, result.message + str(result.diagnostics)
    for shift in result.proposal.shifts:
        assert all(end - start <= 360 for start, end in coverage_intervals(shift))
    assert not [i for i in validate(result.proposal) if i.severity == "error"]


def test_impossible_weekly_maximum_does_not_silently_return_invalid_schedule():
    week = week_for_generation(2)
    for educator in week.educators:
        educator.max_minutes = 300
        educator.target_minutes = 300
    result = generate(week, 5)
    assert not result.success
    assert result.proposal is None
    assert result.status in {"infeasible_candidates", "timeout"}


def test_candidate_boundaries_keep_exact_required_times_and_pause_lengths():
    week = week_for_generation(3)
    week.groups[0].periods = [GroupPeriod(0, 420, 678, 35), GroupPeriod(0, 678, 1050, 35)]
    week.settings.break_minutes = 29
    candidates, errors = _build_candidates(week)
    assert not errors
    assert any(c.shift.coverage_start == 678 for c in candidates)
    assert any(c.shift.coverage_end == 678 for c in candidates)
    assert all(type(c.paid) is int for c in candidates)
    assert all(b.end - b.start == 29 for c in candidates for b in c.shift.breaks)
