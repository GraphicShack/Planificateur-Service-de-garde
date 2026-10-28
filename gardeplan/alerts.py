"""Plain-language alert labels shared by the summary and keyboard navigation."""
from .coverage import coverage_timeline
from .models import format_time


def alert_text(week, issue, *, global_scope=False):
    if issue.code in {"coverage", "ratio", "opening", "closing", "school_coverage", "shared_coverage"} and issue.start is not None and issue.end is not None:
        specific = bool(week.planning_date and week.settings.staffing_policy >= 3 and issue.group_id and issue.code in {'coverage','ratio','opening','closing'})
        parts = [p for p in coverage_timeline(week, issue.day or 0,
                 issue.group_id if specific or not global_scope else "")
                 if p.start < issue.end and issue.start < p.end and p.required]
        if parts:
            worst = min(parts, key=lambda p: p.actual-p.required)
            noun = "éducatrice" if worst.actual == 1 else "éducatrices"
            group = next((g.name for g in week.groups if g.id == issue.group_id),'') if specific else ''
            prefix = 'Tous les groupes · ' if issue.code=='shared_coverage' else f'{group} · ' if group else ''
            return prefix+f"{format_time(issue.start)} – {format_time(issue.end)} : {worst.actual} {noun} au lieu de {worst.required}"
    return issue.message


def visible_alerts(week, issues=None):
    """The single alert count used by both the planner and the home page."""
    if issues is None:
        from .validation import validate
        issues = validate(week)
    result, seen = [], set()
    for issue in issues:
        key = (issue.severity, alert_text(week,issue,global_scope=True))
        if key not in seen:
            seen.add(key)
            result.append(issue)
    return result
