"""Add or extend local assignments, preserving every unrelated and locked shift.

A correction may leave pre-existing alerts elsewhere, but must completely fix
the selected gap without introducing any new blocking error. No partial repair
is returned when the bounded search cannot finish the selected interval.
"""
from copy import deepcopy
from time import monotonic

from .attendance import is_absent
from .coverage import coverage_timeline
from .models import Shift,new_id,paid_minutes,subtract_intervals,format_time
from .optimizer import GenerationResult,_windows,_fits,_candidate_breaks
from .preferences import preference_cost
from .staffing import daily_limit
from .validation import validate

COVERAGE_CODES={'coverage','ratio','opening','closing','school_coverage','shared_coverage'}


def repairable(issue):
    return (issue is not None and issue.code in COVERAGE_CODES and issue.day is not None
            and issue.start is not None and issue.end is not None and issue.start<issue.end)


def _parts(plan,issue):
    group=issue.group_id if issue.code in {'coverage','ratio','opening','closing'} else ''
    return [(max(p.start,issue.start),min(p.end,issue.end),max(p.required-p.actual,p.missing))
            for p in coverage_timeline(plan,issue.day,group)
            if p.start<issue.end and issue.start<p.end and not p.complete]


def _deficit(plan,issue):
    return sum((b-a)*missing for a,b,missing in _parts(plan,issue))


def _errors(plan):
    """Minute footprints compare existing errors despite regenerated alert text."""
    result={}
    people={s.id:s.educator_id for s in plan.shifts}
    for issue in validate(plan):
        if issue.severity!='error':continue
        coverage=issue.code in COVERAGE_CODES
        owners=() if coverage else tuple(sorted({people[s] for s in issue.shift_ids if s in people}))
        key=('coverage' if coverage else issue.code,issue.group_id,issue.day,owners)
        values=set(range(issue.start,issue.end)) if issue.start is not None and issue.end is not None else {None}
        result.setdefault(key,set()).update(values)
    return result


def _safe(candidate,base_errors):
    return all(values<=base_errors.get(key,set()) for key,values in _errors(candidate).items())


def _edits(plan,issue):
    """Generate local, exact-minute edits with handover and paid-time limits."""
    settings=plan.settings
    groups=[g for g in plan.groups if not issue.group_id or g.id==issue.group_id]
    if not groups:return
    for a,b,_ in _parts(plan,issue):
        for person in sorted(plan.educators,key=lambda e:(e.seniority,e.id)):
            if not person.active or is_absent(plan,person.id):continue
            own=[s for s in plan.shifts if s.educator_id==person.id]
            total=sum(paid_minutes(s) for s in own)
            daily=sum(paid_minutes(s) for s in own if s.day==issue.day)
            cap=min(person.max_minutes-total,(daily_limit(plan) or 1440)-daily)
            for group in groups:
                if not any(p.day==issue.day and p.start<b and a<p.end for p in group.periods) and settings.open_minute<=a<settings.close_minute:
                    continue
                coverage_start=max(settings.open_minute,min(a,settings.close_minute-1))
                coverage_end=min(settings.close_minute,max(b,settings.open_minute+1))
                before=settings.opening_buffer if coverage_start==settings.open_minute else settings.handover_minutes
                after=settings.closing_buffer if b>settings.close_minute else 0
                # Extending a nearby assignment avoids a new arrival. Breaks keep
                # their absolute times; locked assignments are never edited.
                for old in own:
                    if old.locked or old.day!=issue.day or old.group_id!=group.id:continue
                    if old.end<a-settings.handover_minutes or old.start>b+settings.handover_minutes:continue
                    shift=deepcopy(old)
                    if coverage_start<old.coverage_start:
                        shift.start=coverage_start-before;shift.buffer_before=before
                    if coverage_end>old.coverage_end:
                        shift.end=coverage_end+after;shift.buffer_after=after
                    if shift==old:continue
                    extra=paid_minutes(shift)-paid_minutes(old)
                    if extra<=0 or extra>cap or not _fits(shift,person,plan):continue
                    if any(s.id!=old.id and s.day==issue.day and max(s.start,shift.start)<min(s.end,shift.end) for s in own):continue
                    yield person,old.id,shift,extra
                if cap<=before+after:continue
                for lo,hi in _windows(person,issue.day,plan):
                    for free_start,free_end in subtract_intervals(lo,hi,[(s.start,s.end) for s in own if s.day==issue.day]):
                        for buffer in ({0,before} if coverage_start==settings.open_minute and a>=settings.open_minute else {before}):
                            first=max(coverage_start,free_start+buffer)
                            start=first-buffer
                            if a<settings.open_minute and start> a:continue
                            stop=min(coverage_end,free_end-after,start+cap-after)
                            if first>=stop:continue
                            for breaks in _candidate_breaks(first,stop,plan):
                                shift=Shift(new_id(),person.id,group.id,issue.day,start,stop+after,buffer,after,breaks=breaks)
                                if (shift.start<settings.open_minute-settings.opening_buffer or
                                    shift.end>settings.close_minute+settings.closing_buffer):continue
                                yield person,None,shift,paid_minutes(shift)


def repair(plan,issue,time_limit=10):
    if not repairable(issue):
        return GenerationResult(False,None,"Cette alerte demande une modification manuelle du quart ou des paramètres.",'repair_unsupported')
    source=deepcopy(plan)
    source.status='draft'
    baseline=_errors(source)
    deficit=_deficit(source,issue)
    if not deficit:
        return GenerationResult(False,None,"Cette plage ne manque plus de personnel. Vérifiez les alertes actualisées.",'repair_stale')
    deadline=monotonic()+time_limit
    edited=set();names=[]
    for _ in range(24):
        best=None
        for person,old_id,shift,extra in _edits(source,issue):
            if monotonic()>deadline:break
            proposal=deepcopy(source)
            if old_id is None:proposal.shifts.append(shift)
            else:proposal.shifts=[shift if s.id==old_id else s for s in proposal.shifts]
            remaining=_deficit(proposal,issue)
            if remaining>=deficit or not _safe(proposal,baseline):continue
            key=(person.seniority,-(deficit-remaining),extra,preference_cost(proposal,person,[s for s in proposal.shifts if s.educator_id==person.id]),shift.start,person.id)
            if best is None or key<best[0]:best=(key,proposal,remaining,shift.id,person.name)
        if best is None:break
        _,source,deficit,identifier,name=best
        edited.add(identifier);names.append(name)
        if deficit==0:
            # Recheck all constraints after combining edits, not just each shift.
            if not _safe(source,baseline):break
            errors=sum(i.severity=='error' for i in validate(source))
            return GenerationResult(True,source,
                f"Correction ciblée de {format_time(issue.start)} à {format_time(issue.end)} : {len(edited)} quart(s) ajouté(s) ou prolongé(s). {errors} erreur(s) restante(s) à vérifier. Vérifiez avant d’appliquer.",
                'repair', ['Les quarts verrouillés et les autres affectations sont conservés.',
                           'Personnes proposées : '+', '.join(dict.fromkeys(names))+'.',
                           'Les rangs départagent les remplacements compatibles. Le brouillon reste modifiable.'])
        if monotonic()>deadline:break
    return GenerationResult(False,None,
        "Aucune correction locale complète trouvée. Aucun quart n’a été modifié. Vérifiez les disponibilités, les pauses, le maximum de huit heures et les quarts verrouillés, ou générez une proposition pour toute la journée.",
        'repair_unavailable',['La recherche conserve les autres quarts et reste limitée à la plage choisie, avec les buffers nécessaires.'])
