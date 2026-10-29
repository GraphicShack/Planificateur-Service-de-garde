"""Transparent proposal figures, computed from the same rules as the planner."""
from dataclasses import dataclass
from .alerts import visible_alerts
from .attendance import is_absent
from .comparison import compare
from .coverage import coverage_timeline
from .models import totals,merge_intervals
from .preferences import unmet_preferences


@dataclass(frozen=True)
class Assessment:
    coverage: str
    errors: int
    warnings: int
    paid: int
    split_names: tuple[str,...]
    interruptions: int
    preferences_met: int
    preferences_total: int
    preference_messages: tuple[str,...]
    without_hours: tuple[str,...]


def assess(plan):
    issues=visible_alerts(plan)
    parts=[part for day in plan.active_days for part in coverage_timeline(plan,day)]
    coverage=('À renseigner' if not plan.groups else 'Journée fermée' if not any(p.required for p in parts)
              else 'Complète' if all(p.complete for p in parts) else 'Incomplète')
    paid=totals(plan);split=[];gaps=0;met=total=0;messages=[];without=[]
    for person in sorted(plan.educators,key=lambda e:(e.seniority,e.name)):
        if not person.active or is_absent(plan,person.id):continue
        own=[s for s in plan.shifts if s.educator_id==person.id]
        if not paid.get(person.id,0):without.append(person.name)
        interrupted=False
        for day in plan.active_days:
            shifts=[s for s in own if s.day==day]
            spans=merge_intervals([(s.start,s.end) for s in shifts])
            if len(spans)>1:interrupted=True;gaps+=len(spans)-1
            if not shifts:continue
            wishes=int(person.shift_preference!='none')+int(person.avoid_split)+int(person.preferred_end is not None)
            unmet=unmet_preferences(plan,person,shifts)
            total+=wishes;met+=wishes-len(unmet)
            messages.extend(person.name+' : '+text+'.' for text in unmet)
        if interrupted:split.append(person.name)
    return Assessment(coverage,sum(i.severity=='error' for i in issues),sum(i.severity!='error' for i in issues),
                      sum(paid.values()),tuple(split),gaps,met,total,tuple(messages),tuple(without))


def proposal_summary(before,after):
    changes=compare(before,after)
    locked=[s for s in before.shifts if s.locked]
    current={s.id:s for s in after.shifts}
    preserved=sum(current.get(s.id)==s for s in locked)
    return {'before':assess(before),'after':assess(after),
            'added':sum(c.before is None for c in changes),'removed':sum(c.after is None for c in changes),
            'modified':sum(c.before is not None and c.after is not None for c in changes),
            'locks_total':len(locked),'locks_preserved':preserved}
