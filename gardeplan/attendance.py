"""One-day attendance is separate from the educator's permanent profile."""
from copy import deepcopy


def is_absent(plan, educator_id):
    return bool(plan.planning_date and educator_id in plan.absent_educator_ids)


def set_day_absence(plan, educator_id, absent):
    if not plan.planning_date:
        raise ValueError("Choisissez une journée pédagogique pour signaler une absence.")
    if not any(e.id == educator_id for e in plan.educators):
        raise ValueError("Cette éducatrice est introuvable.")
    result = deepcopy(plan)
    result.absent_educator_ids = [x for x in result.absent_educator_ids if x != educator_id]
    if absent:
        result.absent_educator_ids.append(educator_id)
        result.shifts = [s for s in result.shifts if s.educator_id != educator_id or s.locked]
    return result
