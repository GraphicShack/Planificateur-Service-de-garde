"""Home summaries built from existing snapshots and shared planning services."""
from dataclasses import dataclass
from copy import deepcopy
from .alerts import visible_alerts
from .coverage import coverage_timeline
from .models import totals, format_duration, format_time
from .staffing import adopt_current_draft_rules


@dataclass(frozen=True)
class DayBrief:
    date: str
    name: str
    children: int
    minimum: int
    minutes: int
    educators: int
    alerts: int
    hours: str

    @property
    def status(self):
        return f"{self.alerts} alerte{'s' if self.alerts != 1 else ''}" if self.alerts else 'Couverture complète'

    @property
    def paid(self):
        return format_duration(self.minutes)


def summarize_day(plan):
    plan = deepcopy(plan)
    adopt_current_draft_rules(plan)
    timeline = coverage_timeline(plan)
    active = {e.id for e in plan.educators if e.active}
    scheduled = {s.educator_id for s in plan.shifts if s.day == 0 and s.educator_id in active}
    return DayBrief(plan.planning_date, plan.day_names.get(0,'').strip() or 'Journée pédagogique',
                    max((p.students for p in timeline),default=0),
                    max((p.required for p in timeline),default=0),sum(totals(plan).values()),
                    len(scheduled),len(visible_alerts(plan)),
                    f'{format_time(plan.settings.open_minute-plan.settings.opening_buffer)} – {format_time(plan.settings.close_minute+plan.settings.closing_buffer)}')


def recent_days(repo):
    result=[]
    for row in repo.list_days():
        plan=repo.load_version(row['id'])
        if not plan.planning_date:
            from .daily import day_plan
            plan=day_plan(row['date'],plan,extract=True)
        result.append(summarize_day(plan))
    return sorted(result,key=lambda day:day.date,reverse=True)
