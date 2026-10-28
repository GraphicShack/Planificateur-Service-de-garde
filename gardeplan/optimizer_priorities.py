"""Ordered daily objectives: participation, staffing cost, then seniority.

Each solve keeps the previous feasible proposal. A time limit never turns an
unfinished preference search into an invalid or silently empty schedule.
"""
from time import monotonic
from .staffing import daily_limit


def solve_daily(model,candidates,by_person,totals,week,time_limit):
    from ortools.sat.python import cp_model
    ranked=sorted((e for e in week.educators if e.active),key=lambda e:(e.seniority,e.id))
    used={};scores={};pieces={};last={}
    # No educator can have more than 1,440 disjoint positive-minute shifts.
    cut_weight=(daily_limit(week)+1)*1441
    participation_weight=1441*cut_weight+(daily_limit(week)+1)*1441
    for person in ranked:
        choices=by_person[person.id]
        used[person.id]=model.new_bool_var('travaille_'+person.id)
        model.add(totals[person.id]>=1).only_enforce_if(used[person.id])
        model.add(totals[person.id]==0).only_enforce_if(used[person.id].Not())
        pieces[person.id]=sum(c.variable for c in choices)
        last[person.id]=model.new_int_var(0,1440,'fin_'+person.id)
        model.add_max_equality(last[person.id],[c.shift.end*c.variable for c in choices] or [0])
        scores[person.id]=used[person.id]*participation_weight-pieces[person.id]*cut_weight+totals[person.id]*1441-last[person.id]

    # Interchangeable profiles can always exchange entire schedules. Breaking
    # this symmetry makes rank order mandatory even when optimization times out.
    from .optimizer import _windows
    equivalent={}
    locked={c.shift.educator_id for c in candidates if c.shift.locked}
    for person in ranked:
        if person.id in locked:continue
        signature=(tuple(_windows(person,0)),min(person.max_minutes,daily_limit(week)),person.guaranteed_minutes,
                   person.target_minutes,tuple(sorted(person.preferred_groups)))
        if signature in equivalent:
            model.add(scores[equivalent[signature]]>=scores[person.id])
        equivalent[signature]=person.id

    deadline=monotonic()+max(.1,min(float(time_limit),120))
    best=None;best_status=cp_model.UNKNOWN;optimal=True;completed=0
    def run(expression,maximize,budget):
        nonlocal best,best_status,optimal
        remaining=deadline-monotonic()
        if remaining<=.02:return None
        model.maximize(expression) if maximize else model.minimize(expression)
        if best is not None:
            model.clear_hints()
            for candidate in candidates:model.add_hint(candidate.variable,int(best.boolean_value(candidate.variable)))
        solver=cp_model.CpSolver()
        solver.parameters.max_time_in_seconds=max(.02,min(remaining,budget))
        solver.parameters.num_search_workers=4;solver.parameters.random_seed=17
        status=solver.solve(model)
        if status in (cp_model.OPTIMAL,cp_model.FEASIBLE):
            best,best_status=solver,status
            optimal=optimal and status==cp_model.OPTIMAL
            return solver.value(expression)
        optimal=False
        if best is None:best,best_status=solver,status
        return None

    participation=sum(used.values())
    value=run(participation,True,max(.1,time_limit*.25))
    if value is None:return best,best_status,False,0
    model.add(participation>=value)
    # Avoid creating unnecessary paid hours merely to satisfy preferences.
    cost=sum(totals.values())*(1440*len(ranked)+1)+sum(pieces.values())
    value=run(cost,False,max(.1,time_limit*.25))
    if value is not None:model.add(cost<=value)
    for index,person in enumerate(ranked):
        remaining=deadline-monotonic()
        if remaining<=.02:optimal=False;break
        value=run(scores[person.id],True,remaining/(len(ranked)-index))
        if value is not None:
            model.add(scores[person.id]>=value)
            completed+=1
    return best,best_status,optimal,completed
