"""Minute-exact coverage with merged intervals and legacy quarter-hour views."""
from dataclasses import dataclass
from .staffing import boundaries, minimum_presence, pupil_requirement
from .models import coverage_intervals, working_intervals, required_educators
from .models import totals, format_duration


@dataclass(frozen=True)
class Coverage:
    start: int
    end: int
    actual: int
    required: int
    students: int

    @property
    def complete(self):
        return self.actual >= self.required


def coverage_timeline(week, day=0, group_id=""):
    """A global SDG need, or the need of one specified historical group.

    Preparation/closing follow the versioned staffing policy. Pupil coverage excludes
    buffers and every break, including a paid break. Duplicate shifts never
    count the same person twice.
    """
    groups = [g for g in week.groups if not group_id or g.id == group_id]
    periods = [(g, p) for g in groups for p in g.periods if p.day == day]
    start = max(0, week.settings.open_minute-week.settings.opening_buffer)
    end = min(1440, week.settings.close_minute+week.settings.closing_buffer)
    shifts = [s for s in week.shifts if s.day == day and (not group_id or s.group_id == group_id)]
    active = {e.id for e in week.educators if e.active}
    covered = {s.id: coverage_intervals(s) for s in shifts}
    worked = {s.id: working_intervals(s) for s in shifts}
    points_set = {start, end, week.settings.open_minute, week.settings.close_minute, *boundaries(week)}
    for _, period in periods:
        points_set.update((period.start, period.end))
    for s in shifts:
        for intervals in (covered[s.id], worked[s.id]):
            for a, b in intervals:
                points_set.update((a, b))
    points = sorted(x for x in points_set if start <= x <= end)
    result = []
    ratio = min((g.ratio for g in groups if g.ratio > 0), default=20)
    for a, b in zip(points, points[1:]):
        students = sum(max((p.students for owner, p in periods if owner.id == g.id and p.start <= a < p.end), default=0) for g in groups)
        opened = any(p.start <= a < p.end for _, p in periods)
        preparation = a < week.settings.open_minute or a >= week.settings.close_minute
        if preparation:
            required = minimum_presence(week,a) if periods else 0
            intervals = worked
        else:
            required = pupil_requirement(week,a,students,ratio) if opened else 0
            if group_id and opened:
                required = pupil_requirement(week,a,students,groups[0].ratio,groups[0].min_educators)
            intervals = covered
        actual = len({s.educator_id for s in shifts if s.educator_id in active
                      and any(x <= a and b <= y for x, y in intervals[s.id])})
        item = Coverage(a, b, actual, required, students)
        if result and (result[-1].actual, result[-1].required, result[-1].students) == (actual, required, students):
            previous = result.pop()
            item = Coverage(previous.start, b, actual, required, students)
        result.append(item)
    return result


def quarter_hour_coverage(week, day=0):
    timeline = coverage_timeline(week, day)
    if not timeline:
        return []
    result = []
    start, end = timeline[0].start, timeline[-1].end
    while start < end:
        stop = min(end, (start//15+1)*15)
        candidates = [p for p in timeline if p.start < stop and start < p.end]
        worst = min(candidates, key=lambda p: (p.actual-p.required, -p.required))
        result.append(Coverage(start, stop, worst.actual, worst.required,
                               max(p.students for p in candidates)))
        start = stop
    return result


def merged_coverage(week, day=0):
    """Merge adjacent equal actual/required values at their exact boundaries."""
    result = []
    for part in coverage_timeline(week, day):
        if result and result[-1].end == part.start and (result[-1].actual, result[-1].required) == (part.actual, part.required):
            previous = result.pop()
            part = Coverage(previous.start, part.end, part.actual, part.required,
                            max(previous.students, part.students))
        result.append(part)
    return result


def coverage_state(part):
    if part.actual < part.required:
        return "shortage", f"Manque {part.required-part.actual}"
    if part.actual > part.required:
        return "surplus", f"+{part.actual-part.required}"
    return ("exact", "OK") if part.required else ("closed", "Fermé")


def coverage_counts(part):
    present = "présente" if part.actual == 1 else "présentes"
    required = "requise" if part.required == 1 else "requises"
    return f"{part.actual} {present} / {part.required} {required}"


def day_summary(week, day=0):
    parts = coverage_timeline(week, day)
    children = max((p.students for p in parts), default=0)
    required = max((p.required for p in parts), default=0)
    complete = all(p.complete for p in parts)
    paid = sum(totals(week).values())
    label = (f"{children} enfants · {required} éducatrices minimum · "
             f"{format_duration(paid)} planifiées · Couverture {'complète' if complete else 'incomplète'}")
    return label, complete
