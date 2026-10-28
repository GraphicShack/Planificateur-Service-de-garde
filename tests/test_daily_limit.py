from copy import deepcopy
from gardeplan.daily import day_plan, duplicate_day
from gardeplan.models import Break, Shift
from gardeplan.staffing import adopt_current_draft_rules, daily_limit
from gardeplan.validation import validate
from gardeplan.hours import educator_hour_state
from test_coverage import covered_day


def current_day():
    plan = covered_day()
    adopt_current_draft_rules(plan)
    return plan


def test_eight_hours_exact_and_one_minute_excess_in_paid_time():
    plan = current_day()
    plan.shifts = [Shift('a','0','g',0,410,890,10), Shift('b','1','g',0,420,901)]
    errors = [i for i in validate(plan) if i.code == 'max_daily']
    assert len(errors) == 1 and errors[0].shift_ids == ['b']
    assert '8 h 00' in errors[0].message
    assert educator_hour_state(plan,plan.educators[1]).code == 'maximum'


def test_split_shifts_cumulate_and_unpaid_breaks_are_deducted():
    plan = current_day()
    plan.shifts = [Shift('a','0','g',0,410,710), Shift('b','0','g',0,800,1010)]
    assert any(i.code == 'max_daily' for i in validate(plan))
    plan.shifts[0].breaks = [Break(600,630,False)]
    assert not any(i.code == 'max_daily' for i in validate(plan))
    plan.shifts[0].breaks[0].paid = True
    assert any(i.code == 'max_daily' for i in validate(plan))


def test_no_zero_or_larger_configuration_bypasses_eight_hours():
    for configured in (0,600,720):
        plan = current_day();plan.settings.max_daily_minutes=configured
        assert daily_limit(plan) == 480
        assert len([i for i in validate(plan) if i.code == 'max_daily']) == 2
    plan.settings.max_daily_minutes=420
    assert daily_limit(plan) == 420


def test_new_days_and_copies_use_eight_hours_without_mutating_archives():
    legacy=covered_day();legacy.status='archived';before=deepcopy(legacy)
    assert not adopt_current_draft_rules(legacy)
    assert legacy == before
    assert day_plan('2026-10-29').settings.max_daily_minutes == 480
    assert duplicate_day(legacy,'2026-10-29').settings.max_daily_minutes == 480
    legacy.status='draft'
    assert adopt_current_draft_rules(legacy)
    assert legacy.settings.staffing_policy == 4 and daily_limit(legacy) == 480


def test_profile_and_settings_reject_more_than_eight_hours(qapp):
    import pytest
    from gardeplan.ui.forms import EducatorDialog,SettingsDialog
    plan=current_day()
    for dialog,field in ((EducatorDialog(plan),'maximum'),(SettingsDialog(plan),'max_daily')):
        if field == 'maximum':dialog.name.setText('Nouvelle éducatrice')
        getattr(dialog,field).setValue(481)
        with pytest.raises(ValueError,match='8 h 00'):dialog.build_item()
        dialog.deleteLater()
