"""Independent pedagogical days, with lossless access to historical weekly data."""
from copy import deepcopy
from datetime import date, timedelta

from .models import Week


def day_plan(selected: str, template: Week | None = None, *, extract=False) -> Week:
    current = date.fromisoformat(selected)
    monday = current - timedelta(days=current.weekday())
    result = Week(monday.isoformat(), planning_date=selected)
    if template is None:
        return result
    result.educators, result.rooms, result.settings = deepcopy((template.educators, template.rooms, template.settings))
    if not extract:
        result.settings.staffing_policy = 2
    source_day = 0 if template.planning_date else current.weekday()
    def periods(values):
        chosen = [deepcopy(p) for p in values if p.day == source_day]
        for p in chosen:
            p.day = 0
        return chosen
    for person in result.educators:
        original_availability = person.availability
        person.availability = periods(original_availability)
        # A declared restriction with no period for this date means unavailable.
        if original_availability and not person.availability:
            from .models import Window
            person.absences = [Window(0, 0, 1440)]
        else:
            person.absences = periods(person.absences) if extract else []
        if not template.planning_date:
            # A weekly goal cannot become a daily obligation implicitly.
            person.target_minutes = person.guaranteed_minutes = 0
            person.max_minutes = min(person.max_minutes, result.settings.max_daily_minutes or 1440)
    for room in result.rooms:
        original_availability = room.availability
        room.availability = periods(original_availability)
        if original_availability and not room.availability:
            from .models import Window
            room.availability = [Window(0, 0, 1)]
    if extract:
        result.groups = deepcopy(template.groups)
        for group in result.groups:
            group.periods = periods(group.periods)
        result.shifts, result.activities = periods(template.shifts), periods(template.activities)
        name = template.day_names.get(source_day, "")
        if name:
            result.day_names[0] = name
        result.status = template.status
    return result


def duplicate_day(source: Week, selected: str) -> Week:
    if not source.planning_date:
        raise ValueError("Choisissez une journée à dupliquer.")
    result = deepcopy(source)
    current = date.fromisoformat(selected)
    result.planning_date = selected
    result.monday = (current - timedelta(days=current.weekday())).isoformat()
    result.status = "draft"
    result.settings.staffing_policy = 2
    return result
