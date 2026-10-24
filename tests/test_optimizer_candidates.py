"""Contrôles sans solveur du catalogue et du regroupement des transmissions."""
from collections import defaultdict
import unittest

from gardeplan.models import Break, Educator, Group, GroupPeriod, Shift, Week, working_intervals
from gardeplan.optimizer import _Candidate, _build_candidates, _handover_profile


def common_at_point(left, right, point, length):
    return any(min(b, d) - max(a, c) >= length and max(a, c) <= point <= min(b, d)
               for a, b in left for c, d in right)


class CandidateTests(unittest.TestCase):
    def test_handover_profile_preserves_test_at_break_boundaries(self):
        # Tester notamment les pauses commençant/finissant à l'instant de
        # relève : le validateur accepte une transmission de part ou d'autre.
        for incoming_start in (570, 585, 600):
            for incoming_end in (600, 615, 630, 720):
                if incoming_end <= incoming_start:
                    continue
                for break_start, break_end in ((601, 610), (590, 600), (600, 610), (640, 650)):
                    incoming = Shift("incoming", "a", "g", 0, incoming_start, incoming_end,
                                     buffer_before=600 - incoming_start,
                                     breaks=[Break(break_start, break_end)])
                    profile = _handover_profile(_Candidate(incoming, 0), 15)
                    for old_start in (540, 575, 590, 600):
                        for old_end in (600, 605, 615, 645):
                            if old_start >= old_end:
                                continue
                            previous = Shift("previous", "b", "g", 0, old_start, old_end)
                            full = common_at_point(working_intervals(incoming), working_intervals(previous), 600, 15)
                            clipped = common_at_point(profile[2], working_intervals(previous), 600, 15)
                            self.assertEqual(full, clipped)

    def test_all_generated_variants_with_same_profile_have_same_predecessors(self):
        week = Week("2026-10-26", educators=[Educator(str(i), str(i)) for i in range(2)],
                    groups=[Group("g", "A", periods=[GroupPeriod(0, 420, 1050, 25)])])
        week.settings.break_minutes = 30
        candidates, errors = _build_candidates(week)
        self.assertFalse(errors)
        grouped = defaultdict(list)
        for candidate in candidates:
            grouped[_handover_profile(candidate, 15)].append(candidate)
        self.assertLess(len(grouped), len(candidates) // 5)
        for (educator_id, point, intervals), arrivals in grouped.items():
            for previous in candidates:
                old = previous.shift
                if old.educator_id == educator_id or not old.coverage_start < point <= old.coverage_end:
                    continue
                expected = common_at_point(intervals, working_intervals(old), point, 15)
                for incoming in arrivals:
                    actual = common_at_point(working_intervals(incoming.shift), working_intervals(old), point, 15)
                    self.assertEqual(expected, actual)


if __name__ == "__main__":
    unittest.main()
