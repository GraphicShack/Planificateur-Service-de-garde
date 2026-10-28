import unittest
from importlib.util import find_spec
from gardeplan.daily import day_plan
from gardeplan.models import Educator, Group, GroupPeriod, Shift, Break, paid_minutes
from gardeplan.coverage import coverage_timeline, quarter_hour_coverage


def covered_day():
    plan = day_plan("2026-10-28")
    plan.groups = [Group("g", "Service", periods=[GroupPeriod(0, 420, 1050, 5)])]
    plan.educators = [Educator(str(i), f"Personne {i}", seniority=i+1) for i in range(2)]
    plan.shifts = [Shift(str(i), str(i), "g", 0, 410, 1055, 10, 5) for i in range(2)]
    return plan


class CoverageTests(unittest.TestCase):
    @unittest.skipUnless(find_spec("ortools"), "OR-Tools vérifié par les suites natives")
    def test_generator_refuses_invalid_ratio_instead_of_normalizing_it(self):
        from gardeplan.optimizer import generate
        plan = covered_day()
        plan.groups[0].ratio = 0
        result = generate(plan, time_limit=1)
        self.assertFalse(result.success)
        self.assertEqual(result.status, "invalid_data")

    def test_daily_registration_is_one_global_pool(self):
        from gardeplan.planning import plan_service_day
        plan = covered_day()
        result = plan_service_day(plan, 41)
        self.assertEqual(len(result.groups), 1)
        self.assertEqual(result.groups[0].periods[0].students, 41)
        self.assertEqual(next(p for p in coverage_timeline(result) if p.start == 420).required, 3)
        self.assertEqual(result.shifts, plan.shifts)
        self.assertEqual(plan.groups[0].periods[0].students, 5)

    def test_summary_counts_paid_minutes_and_reports_incomplete_coverage(self):
        from gardeplan.coverage import day_summary
        plan = covered_day()
        self.assertEqual(day_summary(plan), ("5 enfants · 2 éducatrices minimum · 21 h 30 planifiées · Couverture complète", True))
        plan.shifts[0].breaks = [Break(720, 735)]
        label, complete = day_summary(plan)
        self.assertFalse(complete)
        self.assertIn("21 h 15 planifiées", label)
        self.assertIn("Couverture incomplète", label)

    def test_historical_groups_are_analyzed_globally_without_mutating_storage_data(self):
        from copy import deepcopy
        from gardeplan.planning import service_view
        from gardeplan.validation import validate
        plan = covered_day()
        plan.groups.append(Group("old", "Ancien B", periods=[GroupPeriod(0, 420, 1050, 5)]))
        plan.shifts[1].group_id = "old"
        original = deepcopy(plan)
        view = service_view(plan)
        self.assertEqual(len(view.groups), 1)
        self.assertEqual(view.groups[0].periods[0].students, 10)
        self.assertFalse(any(p.severity == "error" for p in validate(plan)))
        self.assertEqual(plan, original)

    def test_mandatory_maximum_takes_priority_over_optional_target(self):
        from gardeplan.hours import hour_state
        person = covered_day().educators[0]
        person.target_minutes, person.max_minutes = 400, 600
        self.assertEqual(hour_state(person, 450).code, "target")
        state = hour_state(person, 601)
        self.assertEqual(state.code, "maximum")
        self.assertIn("Maximum obligatoire", state.label)
        person.target_minutes = 0
        self.assertEqual(hour_state(person, 500).label, "Aucun objectif défini")
        self.assertEqual(hour_state(person, 700).code, "maximum")

    def test_complete_day_and_partial_boundary_slices(self):
        plan = covered_day()
        pieces = quarter_hour_coverage(plan)
        self.assertEqual((pieces[0].start, pieces[0].end), (410, 420))
        self.assertEqual((pieces[-1].start, pieces[-1].end), (1050, 1055))
        self.assertTrue(all(p.complete and p.actual == p.required == 2 for p in pieces))

    def test_one_minute_break_is_not_hidden_by_quarter_average(self):
        plan = covered_day()
        plan.shifts[0].breaks = [Break(733, 734)]
        part = next(p for p in quarter_hour_coverage(plan) if p.start == 720)
        self.assertEqual((part.actual, part.required, part.complete), (1, 2, False))
        gap = next(p for p in coverage_timeline(plan) if p.start == 733)
        self.assertEqual((gap.start, gap.end), (733, 734))

    def test_paid_and_unpaid_breaks_both_remove_coverage(self):
        plan = covered_day()
        for paid in (True, False):
            plan.shifts[0].breaks = [Break(720, 750, paid)]
            gap = next(p for p in coverage_timeline(plan) if p.start == 720)
            self.assertEqual(gap.actual, 1)
            self.assertEqual(paid_minutes(plan.shifts[0]), 645 if paid else 615)

    def test_requirement_changes_do_not_create_a_false_shortage(self):
        plan = covered_day()
        plan.groups[0].periods = [GroupPeriod(0, 420, 427, 5), GroupPeriod(0, 427, 1050, 41)]
        plan.educators.append(Educator("3", "Troisième", seniority=3))
        plan.shifts.append(Shift("3", "3", "g", 0, 427, 1055))
        part = next(p for p in quarter_hour_coverage(plan) if p.start == 420)
        self.assertTrue(part.complete)

    def test_duplicate_shifts_never_double_count_one_person(self):
        plan = covered_day()
        plan.shifts[1].educator_id = "0"
        self.assertEqual(coverage_timeline(plan)[0].actual, 1)

    def test_plain_language_alert_preserves_the_exact_gap(self):
        from gardeplan.validation import Issue
        from gardeplan.alerts import alert_text
        plan = covered_day()
        plan.shifts[0].breaks = [Break(720, 795)]
        label = alert_text(plan, Issue("error", "coverage", "", 0, 720, 795, "g"))
        self.assertEqual(label, "12 h 00 – 13 h 15 : 1 éducatrice au lieu de 2")

    def test_dinner_survives_serialization_and_changes_pay_only_when_unpaid(self):
        from gardeplan.models import Week
        plan = covered_day()
        plan.shifts[0].breaks = [Break(720, 765, False, "dinner")]
        restored = Week.from_dict(plan.to_dict())
        self.assertEqual(restored.shifts[0].breaks[0].kind, "dinner")
        self.assertEqual(paid_minutes(restored.shifts[0]), 600)
        self.assertEqual(next(p for p in coverage_timeline(restored) if p.start == 720).actual, 1)


if __name__ == "__main__":
    unittest.main()
