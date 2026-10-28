import unittest
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
