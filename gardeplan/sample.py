"""Exemple facultatif, isolé des données personnelles de la responsable."""
from .models import Week, Educator, Group, GroupPeriod, Shift, Activity, Room, Window


def example_week(monday: str) -> Week:
    week = Week(monday=monday)
    colors = ["#397F77", "#5778BB", "#AE7657", "#926DAD"]
    names = ["Marie Tremblay", "Sophie Gagnon", "Alex Roy", "Camille Bouchard"]
    week.educators = [Educator(id=f"e{i}", name=name, seniority=i + 1,
                               target_minutes=1650 if i < 2 else 1700,
                               max_minutes=2400, color=colors[i])
                      for i, name in enumerate(names)]
    week.groups = [Group(id="g1", name="Groupe A — Les Explorateurs",
                         periods=[GroupPeriod(d, 420, 1050, 32) for d in range(5)])]
    week.rooms = [Room("cour", "Cour extérieure", capacity=80, shared=True, outdoor=True),
                  Room("101", "Local 101", capacity=40)]
    for d in range(5):
        # Relève payée de12h à12h15, sans trou de couverture.
        for i in range(4):
            morning = i < 2
            week.shifts.append(Shift(id=f"s{d}-{i}", educator_id=f"e{i}",
                                     group_id="g1", day=d,
                                     start=410 if morning else 720,
                                     end=735 if morning else 1055,
                                     buffer_before=10 if morning else 15,
                                     buffer_after=0 if morning else 5))
        week.activities.append(Activity(id=f"a{d}", name="Jeux extérieurs", group_id="g1",
                                        day=d, start=840, end=960, room_id="cour"))
    week.day_names[4] = "Journée pédagogique — Halloween"
    return week
