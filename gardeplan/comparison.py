"""Compare physical assignments, not the random IDs produced by generation."""
from dataclasses import dataclass
from .models import paid_minutes,format_time,format_duration


def fingerprint(shift):
    return (shift.educator_id,shift.day,shift.group_id,shift.start,shift.end,
            shift.buffer_before,shift.buffer_after,shift.before_paid,shift.after_paid,
            tuple((b.start,b.end,b.paid,b.kind) for b in shift.breaks),shift.locked)


@dataclass(frozen=True)
class Change:
    educator_id: str
    before: object | None
    after: object | None

    @property
    def label(self):
        return "Ajouté" if self.before is None else "Retiré" if self.after is None else "Modifié"

    @property
    def delta(self):
        return (paid_minutes(self.after) if self.after else 0)-(paid_minutes(self.before) if self.before else 0)


def compare(before,after):
    old=list(before.shifts);new=list(after.shifts)
    for shift in old[:]:
        same=next((s for s in new if fingerprint(s)==fingerprint(shift)),None)
        if same is not None:old.remove(shift);new.remove(same)
    changes=[]
    # Match each person's remaining assignments by day, group and overlap.
    pairs=sorted(((a,b) for a in old for b in new if a.educator_id==b.educator_id and a.day==b.day),
                 key=lambda pair:(pair[0].id!=pair[1].id,
                     -max(0,min(pair[0].end,pair[1].end)-max(pair[0].start,pair[1].start)),
                     pair[0].group_id!=pair[1].group_id,abs(pair[0].start-pair[1].start)))
    for a,b in pairs:
        if a in old and b in new:
            changes.append(Change(a.educator_id,a,b));old.remove(a);new.remove(b)
    changes.extend(Change(s.educator_id,s,None) for s in old)
    changes.extend(Change(s.educator_id,None,s) for s in new)
    ranks={e.id:(e.seniority,e.name) for e in after.educators+before.educators}
    return sorted(changes,key=lambda c:(ranks.get(c.educator_id,(99,'')),(c.after or c.before).day,(c.after or c.before).start))


def describe_shift(plan,shift):
    if shift is None:return "—"
    group=next((g.name for g in plan.groups if g.id==shift.group_id),"Affectation inconnue")
    text=f"{format_time(shift.start)} – {format_time(shift.end)} · {group}"
    text+=f"\n{format_duration(paid_minutes(shift))} rémunérées"
    if shift.buffer_before or shift.buffer_after:
        text+=f" · préparation {shift.buffer_before} min / fermeture {shift.buffer_after} min"
    for pause in shift.breaks:
        text+=f"\nInterruption {format_time(pause.start)} – {format_time(pause.end)} ({'payée' if pause.paid else 'non payée'})"
    if shift.locked:text+="\nVerrouillé"
    return text
