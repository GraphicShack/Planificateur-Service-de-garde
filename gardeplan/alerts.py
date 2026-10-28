"""Plain-language alert labels shared by the summary and keyboard navigation."""
from .coverage import coverage_timeline
from .models import format_time


def alert_text(week, issue, *, global_scope=False):
    if issue.code in {"coverage", "ratio", "opening", "closing", "school_coverage"} and issue.start is not None and issue.end is not None:
        parts = [p for p in coverage_timeline(week, issue.day or 0,
                 "" if global_scope else issue.group_id)
                 if p.start < issue.end and issue.start < p.end and p.required]
        if parts:
            worst = min(parts, key=lambda p: p.actual-p.required)
            noun = "éducatrice" if worst.actual == 1 else "éducatrices"
            return f"{format_time(issue.start)} – {format_time(issue.end)} : {worst.actual} {noun} au lieu de {worst.required}"
    return issue.message
