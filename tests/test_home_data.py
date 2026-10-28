import unittest
from tempfile import TemporaryDirectory
from gardeplan.models import Educator, Group, GroupPeriod, Shift, Break
from gardeplan.daily import day_plan
from gardeplan.storage import Repository
from gardeplan.home_data import recent_days, summarize_day
from gardeplan.alerts import visible_alerts


def planned_day(selected='2026-10-28'):
    plan=day_plan(selected)
    plan.educators=[Educator(str(i),f'Éducatrice {i}',seniority=i+1,target_minutes=0,max_minutes=720) for i in range(2)]
    plan.groups=[Group('g','Groupe A',periods=[GroupPeriod(0,420,1050,5)])]
    plan.shifts=[Shift(str(i),str(i),'g',0,410,1055,10,5) for i in range(2)]
    return plan


class HomeDataTests(unittest.TestCase):
    def test_saved_days_are_sorted_by_date_without_creating_a_day(self):
        with TemporaryDirectory() as folder:
            repo=Repository(folder+'/home.sqlite')
            for selected in ('2026-02-20','2026-10-28','2026-10-23'):repo.save(planned_day(selected))
            count=len(repo.list_days())
            self.assertEqual([d.date for d in recent_days(repo)],['2026-10-28','2026-10-23','2026-02-20'])
            self.assertEqual(len(repo.list_days()),count)

    def test_status_and_figures_reuse_the_planners_calculations(self):
        plan=planned_day();plan.day_names[0]='Journée des découvertes'
        brief=summarize_day(plan)
        self.assertEqual(brief.status,'Couverture complète')
        self.assertEqual((brief.children,brief.minimum,brief.educators,brief.paid),(5,2,2,'21 h 30'))
        plan.shifts[0].breaks=[Break(720,750,False,'dinner')]
        brief=summarize_day(plan)
        self.assertEqual(brief.alerts,len(visible_alerts(plan)))
        self.assertEqual(brief.status,'1 alerte')
        self.assertEqual(brief.paid,'21 h 00')
        self.assertEqual(brief.name,'Journée des découvertes')
        self.assertEqual(brief.hours,'6 h 50 – 17 h 35')

    def test_empty_storage_stays_empty(self):
        with TemporaryDirectory() as folder:
            repo=Repository(folder+'/home.sqlite')
            self.assertEqual(recent_days(repo),[])
            self.assertIsNone(repo.latest_week())

    def test_default_name_and_nonconsecutive_staff_ranks_are_preserved(self):
        plan=planned_day();plan.educators[1].seniority=11
        self.assertEqual(summarize_day(plan).name,'Journée pédagogique')
        self.assertEqual([e.seniority for e in plan.educators],[1,11])

    def test_home_text_colours_meet_aa(self):
        from gardeplan.ui.theme import contrast
        for foreground,background in (('#203D32','#F7F9F8'),('#52655E','#FFFFFF'),('#804500','#FFF0D8'),('#214F40','#E7F2EC'),('#FFFFFF','#214F40')):
            self.assertGreaterEqual(contrast(foreground,background),4.5)
