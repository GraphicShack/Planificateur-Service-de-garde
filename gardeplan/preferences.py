"""Optional preferences, shared by validation, repair ranking and CP objectives."""
from .models import merge_intervals, format_time

LABELS={"none":"Aucune préférence", "opening":"Préfère ouvrir", "closing":"Préfère fermer"}


def preference_cost(plan, person, shifts):
    spans=merge_intervals([(s.start,s.end) for s in shifts if s.educator_id==person.id])
    if not spans:return 0
    first,last=spans[0][0],spans[-1][1]
    cost=0
    if person.shift_preference=='opening':cost+=max(0,first-(plan.settings.open_minute-plan.settings.opening_buffer))
    if person.shift_preference=='closing':cost+=max(0,plan.settings.close_minute+plan.settings.closing_buffer-last)
    if person.preferred_end is not None:cost+=max(0,last-person.preferred_end)
    if person.avoid_split and len(spans)>1:
        cost+=1441+sum(b[0]-a[1] for a,b in zip(spans,spans[1:]))
    return cost


def unmet_preferences(plan, person, shifts):
    spans=merge_intervals([(s.start,s.end) for s in shifts if s.educator_id==person.id])
    if not spans:return []
    messages=[]
    if person.shift_preference=='opening' and spans[0][0]>plan.settings.open_minute-plan.settings.opening_buffer:
        messages.append(f"préfère ouvrir, mais commence à {format_time(spans[0][0])}")
    if person.shift_preference=='closing' and spans[-1][1]<plan.settings.close_minute+plan.settings.closing_buffer:
        messages.append(f"préfère fermer, mais termine à {format_time(spans[-1][1])}")
    if person.avoid_split and len(spans)>1:messages.append("souhaite éviter les horaires coupés")
    if person.preferred_end is not None and spans[-1][1]>person.preferred_end:
        messages.append(f"souhaite partir à {format_time(person.preferred_end)}, mais termine à {format_time(spans[-1][1])}")
    return messages


def cp_preference(model, choices, used, last, plan, person):
    """Same score as preference_cost; all terms remain optional, never constraints."""
    terms=[]
    if person.shift_preference=='opening' or person.avoid_split:
        first=model.new_int_var(0,1440,'debut_'+person.id)
        model.add_min_equality(first,[c.shift.start*c.variable+1440*(1-c.variable) for c in choices] or [1440])
    def positive(expression,name):
        value=model.new_int_var(0,1440,name+'_'+person.id)
        model.add_max_equality(value,[0,expression])
        return value
    if person.shift_preference=='opening':
        terms.append(positive(first-1440*(1-used)-(plan.settings.open_minute-plan.settings.opening_buffer)*used,'ouverture'))
    if person.shift_preference=='closing':
        terms.append(positive((plan.settings.close_minute+plan.settings.closing_buffer)*used-last,'fermeture'))
    if person.preferred_end is not None:terms.append(positive(last-person.preferred_end,'depart_souhaite'))
    if person.avoid_split:
        gap=positive(last-first-sum((c.shift.end-c.shift.start)*c.variable for c in choices),'interruptions')
        cut=model.new_bool_var('horaire_coupe_'+person.id)
        model.add(gap>=1).only_enforce_if(cut)
        model.add(gap==0).only_enforce_if(cut.Not())
        terms.extend([cut*1441,gap])
    return sum(terms)
