"""Stable group/educator columns without changing any assignment."""
from .models import Group, Educator
from .attendance import is_absent


def assignment_columns(plan, day=0):
    people = {e.id: e for e in plan.educators}
    shifts = [s for s in plan.shifts if s.day == day]
    for eid in {s.educator_id for s in shifts}-people.keys():
        people[eid] = Educator(eid,"Éducatrice manquante",seniority=12,active=False)
    groups = list(plan.groups)
    known = {g.id for g in groups}
    groups.extend(Group(gid, 'Groupe manquant') for gid in sorted({s.group_id for s in shifts}-known))
    result, assigned = [], set()
    for group in groups:
        identifiers = {s.educator_id for s in shifts if s.group_id == group.id}
        members = sorted((people[eid] for eid in identifiers if eid in people),
                         key=lambda e: (not e.active, e.seniority, e.name.casefold()))
        assigned.update(identifiers)
        result.extend((group, person) for person in members)
        if not members:
            result.append((group, None))
    unassigned = sorted((e for e in plan.educators if e.active and not is_absent(plan,e.id) and e.id not in assigned),
                        key=lambda e: (e.seniority, e.name.casefold()))
    result.extend((None, e) for e in unassigned)
    return result
