"""Differentiate an optional target from a mandatory maximum in paid minutes."""
from dataclasses import dataclass
from .models import format_duration, totals
from .staffing import daily_limit


@dataclass(frozen=True)
class HourState:
    code: str
    color: str
    label: str


def hour_state(person, minutes, daily_limit=None):
    limit = min(person.max_minutes, daily_limit) if daily_limit else person.max_minutes
    if minutes > limit:
        return HourState("maximum", "#982D24", f"Maximum obligatoire dépassé de {format_duration(minutes-limit)}")
    if person.target_minutes and minutes > person.target_minutes:
        return HourState("target", "#8A4B0F", f"Objectif dépassé de {format_duration(minutes-person.target_minutes)}")
    if not person.target_minutes:
        return HourState("unset", "#52655E", "Aucun objectif défini")
    remaining = person.target_minutes-minutes
    return HourState("normal", "#52655E", f"Reste {format_duration(remaining)}" if remaining else "Objectif atteint")


def educator_hour_state(week, person):
    return hour_state(person, totals(week).get(person.id, 0),
                      daily_limit(week) if week.planning_date else None)
