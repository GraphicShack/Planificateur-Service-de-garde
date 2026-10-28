import unittest
from copy import deepcopy
from importlib.util import find_spec
from gardeplan.models import Week, Window, Break, Group, GroupPeriod
from gardeplan.daily import duplicate_day
from gardeplan.coverage import coverage_timeline
from gardeplan.validation import validate
from test_coverage import covered_day


def relaxed_day():
    plan = covered_day()
    second = plan.shifts[1]
    second.start,second.end,second.buffer_before,second.buffer_after = 420,1040,0,0
    return plan


class StaffingPolicyTests(unittest.TestCase):
    def test_one_person_at_the_edges_and_two_between_are_valid(self):
        plan = relaxed_day()
        self.assertFalse([i for i in validate(plan) if i.severity == 'error'])
        self.assertEqual([(p.start,p.end,p.actual,p.required) for p in coverage_timeline(plan)],
                         [(410,420,1,1),(420,1040,2,2),(1040,1050,1,1),(1050,1055,1,1)])

    def test_exact_last_minute_before_1720_still_requires_two(self):
        plan = relaxed_day();plan.shifts[1].end=1039
        errors = [i for i in validate(plan) if i.code=='coverage']
        self.assertTrue(any((i.start,i.end)==(1039,1040) for i in errors))

    def test_ratio_still_applies_until_the_children_leave(self):
        plan = relaxed_day();plan.groups[0].periods[0].students=21
        part = next(p for p in coverage_timeline(plan) if p.start==1040)
        self.assertEqual((part.actual,part.required),(1,2))
        self.assertTrue(any(i.severity=='error' and i.start==1040 for i in validate(plan)))

    def test_paid_or_unpaid_break_never_supplies_the_single_required_person(self):
        for paid in (False,True):
            plan=relaxed_day();plan.shifts[0].breaks=[Break(1040,1055,paid)]
            self.assertTrue(any(p.actual==0 and p.required==1 for p in coverage_timeline(plan) if p.start>=1040))
            self.assertTrue(any(i.code=='closing' and i.severity=='error' for i in validate(plan)))

    def test_legacy_snapshots_keep_their_policy_and_duplication_uses_new_rules(self):
        raw=relaxed_day().to_dict();raw['status']='archived';del raw['settings']['staffing_policy']
        before=deepcopy(raw);historical=Week.from_dict(raw)
        self.assertEqual(historical.settings.staffing_policy,1)
        self.assertEqual(raw,before)
        self.assertTrue(all(p.required>=2 for p in coverage_timeline(historical)))
        self.assertEqual(duplicate_day(historical,'2026-10-29').settings.staffing_policy,4)
        self.assertEqual(Week.from_dict(historical.to_dict()).settings.staffing_policy,1)

    def test_invalid_ratio_is_reported_before_staffing_calculations(self):
        plan=relaxed_day();plan.groups[0].ratio=0
        self.assertTrue(any(i.code=='missing_data' for i in validate(plan)))

    @unittest.skipUnless(find_spec('ortools'),'OR-Tools vérifié sur Windows et Mac')
    def test_generator_can_open_with_one_and_release_the_second_at_1720(self):
        from gardeplan.optimizer import generate
        plan=relaxed_day();plan.shifts=[]
        for person in plan.educators:person.target_minutes=0
        plan.educators[0].availability=[Window(0,410,1055)]
        plan.educators[1].availability=[Window(0,420,1040)]
        before=deepcopy(plan)
        result=generate(plan,10)
        self.assertTrue(result.success,result.message+str(result.diagnostics))
        self.assertFalse([i for i in validate(result.proposal) if i.severity=='error'])
        self.assertEqual(plan,before)
        self.assertTrue(all(p.actual>=p.required for p in coverage_timeline(result.proposal)))

    @unittest.skipUnless(find_spec('ortools'),'OR-Tools vérifié sur Windows et Mac')
    def test_generator_preserves_original_groups_and_locked_assignment(self):
        from gardeplan.optimizer import generate
        plan=relaxed_day()
        plan.groups.append(Group('second','Groupe B',periods=[GroupPeriod(0,420,1050,5)]))
        plan.shifts[0].group_id='second'
        for shift in plan.shifts:shift.locked=True
        for person in plan.educators:person.target_minutes=0
        original=deepcopy(plan.shifts)
        result=generate(plan,10)
        self.assertTrue(result.success,result.message+str(result.diagnostics))
        self.assertEqual({g.id for g in result.proposal.groups},{g.id for g in plan.groups})
        self.assertEqual(sorted(result.proposal.shifts,key=lambda s:s.id),sorted(original,key=lambda s:s.id))

    @unittest.skipUnless(find_spec('ortools'),'OR-Tools vérifié sur Windows et Mac')
    def test_generator_can_cover_twenty_one_children_then_close_with_one(self):
        from gardeplan.optimizer import generate
        plan=relaxed_day();plan.shifts=[];plan.groups[0].periods[0].students=21
        for person in plan.educators:person.target_minutes=0
        plan.educators[0].availability=[Window(0,410,1055)]
        plan.educators[1].availability=[Window(0,420,1050)]
        result=generate(plan,10)
        self.assertTrue(result.success,result.message+str(result.diagnostics))
        self.assertFalse([i for i in validate(result.proposal) if i.severity=='error'])
        final=coverage_timeline(result.proposal)[-1]
        self.assertEqual((final.actual,final.required),(1,1))
