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


def requirements(plan, start, end, students=None, ratio=20, minimum=2):
    points = sorted({start,end}|{p for p in boundaries(plan) if start < p < end})
    return [(a,b,minimum_presence(plan,a) if students is None else pupil_requirement(plan,a,students,ratio,minimum))
            for a,b in zip(points,points[1:])]


def adopt_current_draft_rules(plan):
    """Upgrade only working copies, never published or historical snapshots."""
    if plan.planning_date and plan.status in {'draft','validated'} and plan.settings.staffing_policy < 2:
        plan.settings.staffing_policy = 2
        plan.status = 'draft'
        return True
    return False
