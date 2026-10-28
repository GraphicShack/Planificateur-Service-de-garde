"""Préparation d'une journée pédagogique à partir des inscriptions.

La taille souhaitée des groupes est indépendante du ratio d'encadrement : une
limite de 30 enfants par groupe n'altère jamais un ratio configuré à 1 pour 20.
Ce module ne déplace aucun quart ni aucune activité.
"""
from __future__ import annotations

from copy import deepcopy
from .models import Group, GroupPeriod, Week, new_id

_COLORS = ("#8EA985", "#AB9BCB", "#D5A57D", "#87A6C9", "#BF93A7", "#9DA475")


def _letters(index: int) -> str:
    """0=A, 25=Z, 26=AA, sans limite arbitraire sur le nombre de groupes."""
    result = ""
    index += 1
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _next_name(used: set[str]) -> str:
    index = 0
    while True:
        name = f"Groupe {_letters(index)}"
        if name.casefold() not in used:
            return name
        index += 1


def plan_pedagogical_day(
    week: Week,
    day: int,
    registrations: int,
    children_per_group: int = 20,
    name: str | None = None,
) -> Week:
    """Retourne une nouvelle semaine avec les groupes de la journée préparés.

    Réutilise les groupes dans leur ordre courant puis en ajoute au besoin. Les
    premiers groupes reçoivent ``children_per_group`` enfants, le dernier reçoit
    le reste. Les groupes excédentaires sont fermés ce jour seulement. Chaque
    groupe retenu ouvre pendant toute la plage d'ouverture du service de garde.

    ``registrations=0`` ferme tous les groupes de cette journée. ``name=None``
    préserve son nom; une chaîne vide le retire. Les autres jours, les quarts et
    les activités restent intacts. Les quarts devenus inutiles doivent être
    revus manuellement : le moteur de validation les signale sans les effacer.
    Toute modification constitue un brouillon, y compris à partir d'une semaine
    publiée; les versions figées sont conservées par le stockage.
    """
    if type(day) is not int or not 0 <= day < 5:
        raise ValueError("Choisissez une journée du lundi au vendredi.")
    if type(registrations) is not int or registrations < 0:
        raise ValueError("Le nombre d'inscriptions doit être un entier positif ou nul.")
    if type(children_per_group) is not int or children_per_group < 1:
        raise ValueError("La taille souhaitée d'un groupe doit être un entier d'au moins un enfant.")
    if name is not None and (not isinstance(name, str) or len(name.strip()) > 160):
        raise ValueError("Le nom de la journée doit contenir au plus 160 caractères.")
    start, end = week.settings.open_minute, week.settings.close_minute
    if type(start) is not int or type(end) is not int or not 0 <= start < end <= 1440:
        raise ValueError("Corrigez les heures d'ouverture du service de garde avant de préparer cette journée.")

    result = deepcopy(week)
    result.status = "draft"
    count = (registrations + children_per_group - 1) // children_per_group
    used_names = {group.name.casefold() for group in result.groups}
    while len(result.groups) < count:
        group_name = _next_name(used_names)
        result.groups.append(Group(
            id=new_id(), name=group_name,
            color=_COLORS[len(result.groups) % len(_COLORS)],
            ratio=20, min_educators=2,
        ))
        used_names.add(group_name.casefold())

    remaining = registrations
    for index, group in enumerate(result.groups):
        group.periods = [period for period in group.periods if period.day != day]
        if index < count:
            students = min(children_per_group, remaining)
            group.periods.append(GroupPeriod(day=day, start=start, end=end, students=students))
            group.periods.sort(key=lambda period: (period.day, period.start))
            remaining -= students
    if name is not None:
        result.day_names.pop(day, None)
        result.day_names.pop(str(day), None)
        clean_name = name.strip()
        if clean_name:
            result.day_names[day] = clean_name
    return result
