"""Shared minute-exact staffing policy, versioned in historical snapshots."""

def boundaries(plan):
    s = plan.settings
    start, end = s.open_minute-s.opening_buffer, s.close_minute+s.closing_buffer
    return sorted({start, s.open_minute, max(s.open_minute,end-15), end})


def minimum_presence(plan, minute):
    s = plan.settings
    end = s.close_minute+s.closing_buffer
    if plan.planning_date and s.staffing_policy >= 2:
        if s.open_minute-s.opening_buffer <= minute < s.open_minute or max(s.open_minute,end-15) <= minute < end:
            return 1
    return 2


def pupil_requirement(plan, minute, students, ratio, minimum=2):
    base = minimum_presence(plan,minute)
    # Preserve an explicitly stricter custom minimum above the normal two.
    return max(base, minimum if minimum > 2 else 0, (students+ratio-1)//ratio)


def group_requirement(plan, minute, students, ratio, minimum=2):
    if plan.planning_date and plan.settings.staffing_policy >= 3:
        # Two is the service-wide floor; each separate group keeps its own ratio.
        return max(1, minimum if minimum > 2 else 0, (students+ratio-1)//ratio)
    return pupil_requirement(plan,minute,students,ratio,minimum)


def requirements(plan, start, end, students=None, ratio=20, minimum=2, *, per_group=False):
    points = sorted({start,end}|{p for p in boundaries(plan) if start < p < end})
    return [(a,b,minimum_presence(plan,a) if students is None else (group_requirement if per_group else pupil_requirement)(plan,a,students,ratio,minimum))
            for a,b in zip(points,points[1:])]


DAILY_MAXIMUM = 8 * 60
CURRENT_POLICY = 3


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
