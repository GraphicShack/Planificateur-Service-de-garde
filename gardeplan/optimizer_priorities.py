"""Ordered daily objectives: participation, continuity, cost, then seniority.

Each solve keeps the previous feasible proposal. A time limit never turns an
unfinished preference search into an invalid or silently empty schedule.
"""
from time import monotonic
from .staffing import daily_limit, shared_presence, shared_requirement
from .attendance import is_absent


def cohort_hint(week,candidates,ranked):
    """A verified starting schedule for two continuous teams per open group.

    This is only a warm start. CP-SAT still verifies it and optimizes the full
    model; other availability patterns and locked schedules use normal search.
    """
    from copy import deepcopy
    from .validation import validate
    s=week.settings
    groups=[g for g in week.groups if g.periods]
    if len(ranked)!=4*len(groups) or s.break_minutes or any(c.shift.locked for c in candidates):return set()
    if any(len(g.periods)!=1 or g.periods[0].start!=s.open_minute or g.periods[0].end!=s.close_minute or
           max(g.min_educators,(g.periods[0].students+g.ratio-1)//g.ratio)>2 for g in groups):return set()
    limit=min([daily_limit(week)]+[e.max_minutes for e in ranked])
    middle=s.open_minute-s.opening_buffer+limit
    if not s.open_minute<middle<s.close_minute:return set()
    index={}
    for candidate in candidates:
        shift=candidate.shift
        if not shift.breaks:
            index[(shift.educator_id,shift.group_id,shift.start,shift.end,shift.buffer_before,shift.buffer_after)]=candidate
    chosen=[];opening_count=2*len(groups)
    pooled=shared_presence(week,s.open_minute-s.opening_buffer)
    stay=shared_requirement(week,max(s.open_minute,s.close_minute-30)) if pooled else opening_count
    for i,person in enumerate(ranked):
        group=groups[(i%opening_count)//2]
        lane=i%opening_count
        # The first two open the school. Other groups join at pupil opening.
        begin=s.open_minute-s.opening_buffer if not pooled or lane<2 else s.open_minute
        lane_middle=begin+limit
        if i<opening_count:
            key=(person.id,group.id,begin,lane_middle,s.open_minute-begin,0)
        else:
            end=s.close_minute+s.closing_buffer if not pooled or lane<stay else max(s.open_minute,s.close_minute-30)
            key=(person.id,group.id,lane_middle-s.handover_minutes,end,s.handover_minutes,s.closing_buffer if end>s.close_minute else 0)
        candidate=index.get(key)
        if candidate is None:return set()
        chosen.append(candidate)
    proposal=deepcopy(week);proposal.status='draft';proposal.shifts=[c.shift for c in chosen]
    if any(i.severity=='error' for i in validate(proposal)):return set()
    return {c.shift.id for c in chosen}


def solve_daily(model,candidates,by_person,totals,week,time_limit):
    from ortools.sat.python import cp_model
    ranked=sorted((e for e in week.educators if e.active and not is_absent(week,e.id)),key=lambda e:(e.seniority,e.id))
    used={};scores={};pieces={};last={};ties={};cuts={};gaps={}
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
        scores[person.id]=used[person.id]*participation_weight-pieces[person.id]*cut_weight+totals[person.id]*1441
        from .preferences import cp_preference,cp_interruptions
        cuts[person.id],gaps[person.id]=cp_interruptions(model,choices,last[person.id],person.id)
        ties[person.id]=cp_preference(model,choices,used[person.id],last[person.id],week,person,
            interruptions=(cuts[person.id],gaps[person.id]))*1441+last[person.id]

    # Interchangeable profiles can always exchange entire schedules. Breaking
    # this symmetry makes rank order mandatory even when optimization times out.
    from .optimizer import _windows
    equivalent={}
    locked={c.shift.educator_id for c in candidates if c.shift.locked}
    for person in ranked:
        if person.id in locked:continue
        signature=(tuple(_windows(person,0,week)),min(person.max_minutes,daily_limit(week)),person.guaranteed_minutes,
                   person.target_minutes,tuple(sorted(person.preferred_groups)))
        if signature in equivalent:
            previous=equivalent[signature]
            model.add(scores[previous.id]>=scores[person.id])
            if (previous.shift_preference,previous.avoid_split,previous.preferred_end)==(person.shift_preference,person.avoid_split,person.preferred_end):
                equal=model.new_bool_var('meme_qualite_'+person.id)
                model.add(scores[previous.id]==scores[person.id]).only_enforce_if(equal)
                model.add(scores[previous.id]!=scores[person.id]).only_enforce_if(equal.Not())
                model.add(ties[previous.id]<=ties[person.id]).only_enforce_if(equal)
        equivalent[signature]=person

    seed=cohort_hint(week,candidates,ranked)
    if seed:
        for candidate in candidates:model.add_hint(candidate.variable,int(candidate.shift.id in seed))
    deadline=monotonic()+max(.1,min(float(time_limit),120))
    best=None;best_status=cp_model.UNKNOWN;optimal=True;completed=0
    def run(expression,maximize,budget):
        nonlocal best,best_status,optimal
        remaining=deadline-monotonic()
        if remaining<=.02:return None
        model.maximize(expression) if maximize else model.minimize(expression)
        if best is not None and best_status in (cp_model.OPTIMAL,cp_model.FEASIBLE):
            model.clear_hints()
            for candidate in candidates:model.add_hint(candidate.variable,int(best.boolean_value(candidate.variable)))
        solver=cp_model.CpSolver()
        solver.parameters.max_time_in_seconds=max(.02,min(remaining,budget))
        solver.parameters.num_search_workers=4;solver.parameters.random_seed=17
        if best is None and seed:
            # The verified cohort already employs every active person, so its
            # participation is globally maximal. Fix only this initial check;
            # subsequent solves optimize unrestricted candidate choices.
            solver.parameters.fix_variables_to_their_hinted_value=True
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
    if value is None and best_status==cp_model.UNKNOWN:
        # A large multi-group model may spend the first slice in presolve.
        # Use the remaining requested time before reporting a timeout.
        value=run(participation,True,max(.02,deadline-monotonic()))
    if value is None:return best,best_status,False,0
    model.add(participation>=value)
    # Saving a few paid minutes must not create an avoidable hole. First keep
    # the fewest people on split schedules, then shorten unavoidable gaps.
    # This is an objective, not a ban: availability, locks and daily limits win.
    continuity=sum(cuts.values())*(1440*len(ranked)+1)+sum(gaps.values())
    value=run(continuity,False,max(.1,time_limit*.20))
    if value is None and best_status in (cp_model.OPTIMAL,cp_model.FEASIBLE):
        value=best.value(continuity)
    if value is not None:model.add(continuity<=value)
    # Avoid creating unnecessary paid hours merely to satisfy preferences.
    cost=sum(totals.values())*(1440*len(ranked)+1)+sum(pieces.values())
    value=run(cost,False,max(.1,time_limit*.25))
    if value is None and best_status in (cp_model.OPTIMAL,cp_model.FEASIBLE):
        value=best.value(cost)
    if value is not None:model.add(cost<=value)
    for index,person in enumerate(ranked):
        remaining=deadline-monotonic()
        if remaining<=.02:optimal=False;break
        value=run(scores[person.id],True,remaining/(2*(len(ranked)-index)))
        if value is not None:
            model.add(scores[person.id]>=value)
            remaining=deadline-monotonic()
            preference=run(ties[person.id],False,remaining/max(1,2*(len(ranked)-index)-1))
            if preference is not None:
                model.add(ties[person.id]<=preference)
                completed+=1
    return best,best_status,optimal,completed
