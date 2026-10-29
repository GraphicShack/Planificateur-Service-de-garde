"""Minute-exact coverage with merged intervals and legacy quarter-hour views."""
from dataclasses import dataclass
from .staffing import boundaries, minimum_presence, pupil_requirement, group_requirement, group_presence_requirements, shared_presence, shared_requirement
from .models import coverage_intervals, working_intervals, required_educators
from .models import totals, format_duration
from .attendance import is_absent


@dataclass(frozen=True)
class Coverage:
    start: int
    end: int
    actual: int
    required: int
    students: int
    missing: int = 0
    shared: bool = False

    @property
    def complete(self):
        return self.actual >= self.required and not self.missing


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
    all_shifts = [s for s in week.shifts if s.day==day]
    shifts = [s for s in all_shifts if not group_id or s.group_id==group_id]
    active = {e.id for e in week.educators if e.active and not is_absent(week,e.id)}
    covered = {s.id: coverage_intervals(s) for s in all_shifts}
    worked = {s.id: working_intervals(s) for s in all_shifts}
    points_set = {start, end, week.settings.open_minute, week.settings.close_minute, *boundaries(week)}
    for _, period in periods:
        points_set.update((period.start, period.end))
    for s in all_shifts:
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
                required = group_requirement(week,a,students,groups[0].ratio,groups[0].min_educators)
            intervals = covered
        missing = 0
        if week.planning_date and week.settings.staffing_policy >= 3 and not preparation and opened:
            needs = []
            for group in groups:
                present = [p for owner,p in periods if owner.id == group.id and p.start <= a < p.end]
                if not present:continue
                need = group_requirement(week,a,max(p.students for p in present),group.ratio,group.min_educators)
                actual_group = len({s.educator_id for s in shifts if s.group_id == group.id and s.educator_id in active
                                    and any(x <= a and b <= y for x,y in covered[s.id])})
                needs.append(need)
                missing += max(0,need-actual_group)
            required = sum(needs) if group_id else max(minimum_presence(week,a),sum(needs))
        if preparation and week.planning_date and week.settings.staffing_policy >= 3:
            edge_needs=[(g,n) for g in groups for x,y,n in group_presence_requirements(week,g,day) if x<=a and b<=y]
            if edge_needs:
                required=sum(n for g,n in edge_needs)
                for group,need in edge_needs:
                    actual_group=len({s.educator_id for s in shifts if s.group_id==group.id and s.educator_id in active
                                      and any(x<=a and b<=y for x,y in worked[s.id])})
                    missing+=max(0,need-actual_group)
        shared=shared_presence(week,a)
        counted=shifts
        if shared:
            required=shared_requirement(week,a,day) if periods else 0
            missing=0
            counted=all_shifts
            students=sum(max((p.students for p in g.periods if p.day==day and p.start<=a<p.end),default=0) for g in week.groups)
        actual = len({s.educator_id for s in counted if s.educator_id in active
                      and any(x <= a and b <= y for x, y in intervals[s.id])})
        item = Coverage(a, b, actual, required, students, missing,shared)
        if result and (result[-1].actual, result[-1].required, result[-1].students,result[-1].missing,result[-1].shared) == (actual, required, students,missing,shared):
            previous = result.pop()
            item = Coverage(previous.start, b, actual, required, students,missing,shared)
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
        worst = min(candidates, key=lambda p: (-max(p.required-p.actual,p.missing), -p.required))
        result.append(Coverage(start, stop, worst.actual, worst.required,
                               max(p.students for p in candidates),worst.missing,worst.shared))
        start = stop
    return result


def merged_coverage(week, day=0):
    """Merge adjacent equal actual/required values at their exact boundaries."""
    result = []
    for part in coverage_timeline(week, day):
        if result and result[-1].end == part.start and (result[-1].actual, result[-1].required,result[-1].missing,result[-1].shared) == (part.actual, part.required,part.missing,part.shared):
            previous = result.pop()
            part = Coverage(previous.start, part.end, part.actual, part.required,
                            max(previous.students, part.students), part.missing,part.shared)
        result.append(part)
    return result


def coverage_state(part):
    if part.actual < part.required or part.missing:
        return "shortage", f"Manque {max(part.required-part.actual,part.missing)}"
    if part.actual > part.required:
        return "surplus", f"+{part.actual-part.required}"
    return ("exact", "OK") if part.required else ("closed", "Fermé")


def coverage_counts(part):
    present = "présente" if part.actual == 1 else "présentes"
    required = "requise" if part.required == 1 else "requises"
    return f"{part.actual} {present} / {part.required} {required}"+(" · Tous les groupes" if part.shared else "")


def day_summary(week, day=0):
    parts = coverage_timeline(week, day)
    children = max((p.students for p in parts), default=0)
    required = max((p.required for p in parts), default=0)
    complete = all(p.complete for p in parts)
    paid = sum(totals(week).values())
    label = (f"{children} enfants · {required} éducatrices minimum · "
             f"{format_duration(paid)} planifiées · Couverture {'complète' if complete else 'incomplète'}")
    return label, complete
