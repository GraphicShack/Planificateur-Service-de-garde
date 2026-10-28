"""Shared minute-exact staffing policy, versioned in historical snapshots."""

def boundaries(plan):
    s = plan.settings
    start, end = s.open_minute-s.opening_buffer, s.close_minute+s.closing_buffer
    return sorted({start, s.open_minute, max(s.open_minute,end-15), end}|({max(s.open_minute,s.close_minute-30)} if plan.planning_date and s.staffing_policy>=4 else set()))


def minimum_presence(plan, minute):
    s = plan.settings
    end = s.close_minute+s.closing_buffer
    if plan.planning_date and s.staffing_policy == 2:
        if s.open_minute-s.opening_buffer <= minute < s.open_minute or max(s.open_minute,end-15) <= minute < end:
            return 1
    return 2


def pupil_requirement(plan, minute, students, ratio, minimum=2):
    base = minimum_presence(plan,minute)
    # Preserve an explicitly stricter custom minimum above the normal two.
    return max(base, minimum if minimum > 2 else 0, (students+ratio-1)//ratio)


def group_requirement(plan, minute, students, ratio, minimum=2):
    if shared_presence(plan,minute):return 0
    if plan.planning_date and plan.settings.staffing_policy >= 3:
        # Every open group keeps two people, including preparation and closing.
        return max(2,minimum,(students+ratio-1)//ratio)
    return pupil_requirement(plan,minute,students,ratio,minimum)


def requirements(plan, start, end, students=None, ratio=20, minimum=2, *, per_group=False):
    points = sorted({start,end}|{p for p in boundaries(plan) if start < p < end})
    return [(a,b,minimum_presence(plan,a) if students is None else (group_requirement if per_group else pupil_requirement)(plan,a,students,ratio,minimum))
            for a,b in zip(points,points[1:])]


def group_presence_requirements(plan, group, day=0):
    """Paid preparation/closing need presence rather than pupil coverage."""
    if not plan.planning_date or plan.settings.staffing_policy < 3 or plan.settings.staffing_policy>=4:return []
    s=plan.settings;parts=[]
    periods=[p for p in group.periods if p.day==day]
    minimum=max(2,group.min_educators)
    if any(p.start<=s.open_minute<p.end for p in periods) and s.opening_buffer:
        parts.append((s.open_minute-s.opening_buffer,s.open_minute,minimum))
    if any(p.start<s.close_minute<=p.end for p in periods) and s.closing_buffer:
        parts.append((s.close_minute,s.close_minute+s.closing_buffer,minimum))
    return parts


def shared_presence(plan, minute):
    if not plan.planning_date or plan.settings.staffing_policy<4:return False
    s=plan.settings
    return (s.open_minute-s.opening_buffer<=minute<s.open_minute or
            max(s.open_minute,s.close_minute-30)<=minute<s.close_minute+s.closing_buffer)


def shared_requirement(plan, minute, day=0):
    """The pool keeps its pupil ratio; preparation and closing need two."""
    s=plan.settings
    if minute<s.open_minute or minute>=s.close_minute:return 2
    present=[(g,[p for p in g.periods if p.day==day and p.start<=minute<p.end]) for g in plan.groups]
    present=[(g,ps) for g,ps in present if ps]
    students=sum(max(p.students for p in ps) for g,ps in present)
    ratio=min((g.ratio for g,ps in present if g.ratio>0),default=20)
    return max(2,(students+ratio-1)//ratio)


def shared_requirements(plan,day=0):
    if not plan.planning_date or plan.settings.staffing_policy<4:return []
    s=plan.settings
    points=sorted(set(boundaries(plan))|{s.close_minute}|{t for g in plan.groups for p in g.periods if p.day==day for t in (p.start,p.end)})
    return [(a,b,shared_requirement(plan,a,day),s.open_minute<=a<s.close_minute)
            for a,b in zip(points,points[1:]) if shared_presence(plan,a)]


def service_need(plan,minute,day=0):
    s=plan.settings
    if not s.open_minute-s.opening_buffer<=minute<s.close_minute+s.closing_buffer:return 0
    if not any(p.day==day for g in plan.groups for p in g.periods):return 0
    if shared_presence(plan,minute):return shared_requirement(plan,minute,day)
    needed=sum(group_requirement(plan,minute,max(p.students for p in g.periods if p.day==day and p.start<=minute<p.end),g.ratio,g.min_educators)
               for g in plan.groups if any(p.day==day and p.start<=minute<p.end for p in g.periods))
    needed+=sum(n for g in plan.groups for a,b,n in group_presence_requirements(plan,g,day) if a<=minute<b)
    return max(minimum_presence(plan,minute),needed)


DAILY_MAXIMUM = 8 * 60
CURRENT_POLICY = 4


def daily_limit(plan):
    configured = plan.settings.max_daily_minutes
    if plan.planning_date and plan.settings.staffing_policy >= 3:
        return min(configured or DAILY_MAXIMUM, DAILY_MAXIMUM)
    return configured


def adopt_current_draft_rules(plan):
    """Upgrade only working copies, never published or historical snapshots."""
    if plan.planning_date and plan.status in {'draft','validated'}:
        limit = min(plan.settings.max_daily_minutes or DAILY_MAXIMUM, DAILY_MAXIMUM)
        if plan.settings.staffing_policy < CURRENT_POLICY or plan.settings.max_daily_minutes != limit:
            plan.settings.staffing_policy = CURRENT_POLICY
            plan.settings.max_daily_minutes = limit
            plan.status = 'draft'
            return True
    return False


def staffing_description(plan):
    from .models import format_time
    s=plan.settings
    morning=f"{format_time(s.open_minute-s.opening_buffer)} à {format_time(s.open_minute)}"
    evening=f"{format_time(max(s.open_minute,s.close_minute-30))} à {format_time(s.close_minute+s.closing_buffer)}"
    return (f"De {morning} et de {evening} : deux personnes au total, tous groupes confondus. "
            "Entre ces plages : deux éducatrices minimum par groupe ouvert. Le ratio reste obligatoire et peut exiger davantage de personnes. "
            "Les pauses doivent être remplacées ; chaque relève conserve quinze minutes communes.")
