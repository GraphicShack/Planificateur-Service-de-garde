import unittest
from copy import deepcopy
from gardeplan.daily import day_plan
from gardeplan.models import Educator, Group, Shift
from gardeplan.staff_layout import assignment_columns


class StaffLayoutTests(unittest.TestCase):
    def test_groups_span_their_own_people_including_staff_working_in_two_groups(self):
        p = day_plan('2026-10-28')
        p.groups = [Group('a','Groupe A'),Group('b','Groupe B')]
        p.educators = [Educator('1','Marie',seniority=1),Educator('2','Alex',seniority=2)]
        p.shifts = [Shift('a','1','a',0,410,600),Shift('b','2','a',0,410,600),Shift('c','1','b',0,600,1055)]
        original = deepcopy(p)
        self.assertEqual([(g.id,e.id) for g,e in assignment_columns(p)], [('a','1'),('a','2'),('b','1')])
        self.assertEqual(p,original)

    def test_empty_groups_and_unassigned_active_staff_remain_accessible(self):
        p = day_plan('2026-10-28')
        p.groups = [Group('a','Groupe A')]
        p.educators = [Educator('1','Marie'),Educator('2','Inactive',active=False)]
        self.assertEqual([(g.id if g else '',e.id if e else '') for g,e in assignment_columns(p)], [('a',''),('','1')])

    def test_invalid_references_keep_repairable_columns(self):
        p = day_plan('2026-10-28')
        p.shifts = [Shift('s','missing','unknown',0,410,600)]
        g,e = assignment_columns(p)[0]
        self.assertEqual((g.id,e.id),('unknown','missing'))
