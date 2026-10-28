"""Propositions d'horaires locales par OR-Tools CP-SAT.

Les contraintes portent sur des intervalles à bornes entières. Le solveur ne
reçoit pas une grille arrondie de l'horaire : les bornes des disponibilités,
des effectifs et des quarts verrouillés sont conservées. Pour garder un temps
raisonnable, il choisit parmi des quarts candidats (bornes métier et horaires
intermédiaires espacés d'une heure). Une recherche sans solution ne constitue
donc pas une preuve d'impossibilité de tous les horaires minute par minute.
Le résultat complet passe obligatoirement par le validateur métier.
"""
from __future__ import annotations

import copy
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from .models import (
    Break, Educator, Shift, Week, coverage_intervals, working_intervals,
    paid_minutes, required_educators, subtract_intervals, merge_intervals, new_id,
    format_time,
)


@dataclass
class GenerationResult:
    success: bool
    proposal: Week | None
    message: str
    status: str
    diagnostics: list[str] = field(default_factory=list)


@dataclass
class _Candidate:
    shift: Shift
    paid: int
    variable: Any = None


def _windows(educator: Educator, day: int) -> list[tuple[int, int]]:
    available = [(w.start, w.end) for w in educator.availability if w.day == day]
    if not educator.availability:
        available = [(0, 1440)]
    absent = [(w.start, w.end) for w in educator.absences if w.day == day]
    result: list[tuple[int, int]] = []
    for a, b in merge_intervals(available):
        result.extend(subtract_intervals(a, b, absent))
    return result


def _fits(shift: Shift, educator: Educator) -> bool:
    return any(a <= shift.start and shift.end <= b for a, b in _windows(educator, shift.day))


def _candidate_breaks(start: int, end: int, week: Week) -> list[list[Break]]:
    policy = week.settings
    length, after = policy.break_minutes, policy.break_after_minutes
    if length <= 0 or after <= 0 or end - start <= after:
        return [[]]
    # Une pause doit pouvoir couper le quart en deux séquences de la durée
    # maximale configurée. Les quarts plus longs sont composés de plusieurs
    # candidats distincts, avec leur relève, plutôt que d'omettre une pause.
    earliest = max(start + 30, end - length - after)
    latest = min(start + after, end - length - 30)
    if earliest > latest:
        return []
    points = {earliest, latest}
    points.update(range(earliest, latest + 1, 30))
    return [[Break(t, t + length, policy.break_paid)] for t in sorted(points)]


def _build_candidates(week: Week) -> tuple[list[_Candidate], list[str]]:
    settings = week.settings
    people = {e.id: e for e in week.educators}
    groups = {g.id: g for g in week.groups}
    candidates: list[_Candidate] = []
    diagnostics: list[str] = []
    signatures: set[tuple] = set()

    def add(shift: Shift):
        signature = (shift.educator_id, shift.group_id, shift.day, shift.start, shift.end,
                     shift.buffer_before, shift.buffer_after,
                     tuple((p.start, p.end, p.paid) for p in shift.breaks))
        if signature not in signatures or shift.locked:
            candidates.append(_Candidate(shift, paid_minutes(shift)))
            signatures.add(signature)

    for shift in week.shifts:
        if not shift.locked:
            continue
        educator = people.get(shift.educator_id)
        if educator is None or shift.group_id not in groups or not educator.active:
            diagnostics.append("Un quart verrouillé utilise une éducatrice inactive ou un groupe manquant.")
        elif not _fits(shift, educator):
            diagnostics.append(f"Le quart verrouillé de {educator.name} ({format_time(shift.start)} à {format_time(shift.end)}) est hors disponibilité ou pendant une absence.")
        add(copy.deepcopy(shift))
    if diagnostics:
        return candidates, diagnostics

    for group in week.groups:
        for day in week.active_days:
            periods = [p for p in group.periods if p.day == day and p.start < p.end]
            if not periods:
                continue
            # L'enveloppe permet aussi de maintenir le personnel sur place
            # entre deux périodes d'accueil du même groupe.
            opening, closing = min(p.start for p in periods), max(p.end for p in periods)
            base_points = {opening, closing}
            for period in periods:
                base_points.update((period.start, period.end))
            base_points.update(range(opening, closing + 1, 60))
            for locked in week.shifts:
                if locked.day == day and locked.locked:
                    base_points.update((locked.coverage_start, locked.coverage_end))
            for educator in week.educators:
                if not educator.active:
                    continue
                for a, b in _windows(educator, day):
                    points = set(base_points)
                    # Une arrivée peut conserver la minute exacte de sa
                    # disponibilité tout en incluant la relève rémunérée.
                    points.add(max(opening, a + settings.handover_minutes))
                    points.add(min(closing, b))
                    points.add(min(closing, b - settings.closing_buffer))
                    # Ajouter des fins liées à l'objectif quotidien évite de
                    # limiter artificiellement les cibles à des heures rondes.
                    daily_target = educator.target_minutes // len(week.active_days)
                    if daily_target > 0:
                        points.add(opening + daily_target - settings.opening_buffer)
                        points.add(closing - daily_target + settings.closing_buffer)
                    points = sorted(t for t in points if opening <= t <= closing)
                    for coverage_start in points:
                        before = settings.opening_buffer if coverage_start == settings.open_minute else settings.handover_minutes
                        start = coverage_start - before
                        if start < a:
                            continue
                        for coverage_end in points:
                            if coverage_end - coverage_start < 30:
                                continue
                            after = settings.closing_buffer if coverage_end == settings.close_minute else 0
                            end = coverage_end + after
                            if end > b:
                                continue
                            for breaks in _candidate_breaks(coverage_start, coverage_end, week):
                                shift = Shift(new_id(), educator.id, group.id, day, start, end,
                                              before, after, True, True, breaks)
                                minutes = paid_minutes(shift)
                                if minutes <= educator.max_minutes and (not settings.max_daily_minutes or minutes <= settings.max_daily_minutes):
                                    add(shift)
                    if len(candidates) > 120000:
                        diagnostics.append("La recherche dépasse 120 000 quarts candidats. Réduisez le nombre de périodes ou réduisez les groupes simultanés.")
                        return candidates, diagnostics
    return candidates, diagnostics


def _requirements(week: Week) -> list[str]:
    """Diagnostics certains, indépendants du découpage en quarts candidats."""
    result: list[str] = []
    active = [e for e in week.educators if e.active]
    if not active:
        return ["Aucune éducatrice active n'est disponible."]
    if not any(g.periods for g in week.groups):
        return ["Ajoutez au moins un groupe et ses périodes d'ouverture."]
    for day in week.active_days:
        periods = [(g, p) for g in week.groups for p in g.periods if p.day == day]
        if not periods:
            continue
        points = sorted({t for _, p in periods for t in (p.start, p.end)} |
                        {t for e in active for a, b in _windows(e, day) for t in (a, b)} |
                        {week.settings.open_minute - week.settings.opening_buffer,
                         week.settings.close_minute + week.settings.closing_buffer})
        for a, b in zip(points, points[1:]):
            needed = sum(max(required_educators(g, p.students) for p in g.periods
                             if p.day == day and p.start <= a < p.end)
                         for g in week.groups
                         if any(p.day == day and p.start <= a < p.end for p in g.periods))
            school_open = (week.settings.open_minute - week.settings.opening_buffer <= a <
                           week.settings.close_minute + week.settings.closing_buffer)
            needed = max(needed, 2 if school_open else 0)
            available = sum(any(start <= a and b <= end for start, end in _windows(e, day)) for e in active)
            if available < needed:
                result.append(f"Jour {day + 1}, {format_time(a)} à {format_time(b)} : {needed} éducatrices requises, seulement {available} disponibles.")
                if len(result) >= 12:
                    return result
    guaranteed = sum(e.guaranteed_minutes for e in active)
    maximum = sum(e.max_minutes for e in active)
    if guaranteed > maximum:
        result.append("La somme des heures garanties dépasse la somme des maximums autorisés.")
    return result


def _cover(model, candidates: list[_Candidate], day: int, required: list[tuple[int, int, int]],
           group_id: str | None = None, allowed_ids: set[str] | None = None) -> None:
    """Contraintes sur tous les segments où le besoin ou la présence change.

    Un balayage des événements évite d'arrondir une borne à un pas de temps.
    Les segments peuvent durer une seule minute.
    """
    events: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for idx, candidate in enumerate(candidates):
        shift = candidate.shift
        if shift.day != day or (group_id is not None and shift.group_id != group_id):
            continue
        if allowed_ids is not None and shift.educator_id not in allowed_ids:
            continue
        intervals = working_intervals(shift) if group_id is None else coverage_intervals(shift)
        for start, end in intervals:
            events[start].append((idx, 1))
            events[end].append((idx, -1))
    for a, b, _ in required:
        events[a]
        events[b]
    points = sorted(events)
    active: set[int] = set()
    previous_signature = None
    for point, following in zip(points, points[1:]):
        for idx, delta in events[point]:
            if delta == 1:
                active.add(idx)
            else:
                active.discard(idx)
        need = max((n for a, b, n in required if a <= point and following <= b), default=0)
        if need <= 0:
            continue
        signature = (frozenset(active), need)
        if signature == previous_signature:
            continue
        model.add(sum(candidates[idx].variable for idx in active) >= need)
        previous_signature = signature


def _handover_profile(candidate: _Candidate, length: int) -> tuple:
    """Classe d'arrivées ayant exactement les mêmes transmissions possibles.

    Seule une tranche commune contenant l'instant de relève importe. La
    restreindre à quinze minutes de part et d'autre conserve le test de durée,
    tout en regroupant les quarts dont seule la fin ou une pause ultérieure
    change. Cela évite de comparer chaque variante de quart à toutes les autres.
    """
    shift = candidate.shift
    point = shift.coverage_start
    intervals = tuple((max(a, point - length), min(b, point + length))
                      for a, b in working_intervals(shift) if a <= point <= b)
    return shift.educator_id, point, intervals


def _handovers(model, candidates: list[_Candidate], week: Week) -> None:
    """Une arrivée sélectionnée doit disposer d'une transmission réalisable.

    Les variantes ayant les mêmes possibilités de transmission partagent leurs
    contraintes. Les pauses et les fins de quarts restent représentées à leur
    minute exacte. La première personne à quitter doit pouvoir transmettre;
    un collègue qui reste toute la journée ne peut pas servir de substitution.
    """
    length = week.settings.handover_minutes
    if length <= 0:
        return
    grouped: dict[tuple[str, int], list[_Candidate]] = defaultdict(list)
    group_by_id = {g.id: g for g in week.groups}
    for candidate in candidates:
        grouped[candidate.shift.group_id, candidate.shift.day].append(candidate)
    working = {c.shift.id: working_intervals(c.shift) for c in candidates}
    profile_number = 0
    for (group_id, day), choices in grouped.items():
        periods = [p for p in group_by_id[group_id].periods if p.day == day]
        profiles: dict[tuple, list[_Candidate]] = defaultdict(list)
        for incoming in choices:
            point = incoming.shift.coverage_start
            if (any(p.start < point <= p.end for p in periods) and
                any(p.start <= point - 1 < p.end for p in periods)):
                profiles[_handover_profile(incoming, length)].append(incoming)
        for (educator_id, point, intervals), arrivals in profiles.items():
            previous_choices, bad_choices = [], []
            for previous in choices:
                older = previous.shift
                if (older.educator_id == educator_id or
                    not older.coverage_start < point <= older.coverage_end):
                    continue
                common = any(
                    min(b, d) - max(a, c) >= length and max(a, c) <= point <= min(b, d)
                    for a, b in intervals for c, d in working[older.id]
                )
                if common:
                    previous_choices.append(previous)
                else:
                    bad_choices.append(previous)
            profile_number += 1
            if len(arrivals) == 1:
                selected_arrival = arrivals[0].variable
            else:
                selected_arrival = model.new_bool_var(f"arrivee_{profile_number}")
                model.add_max_equality(selected_arrival, [c.variable for c in arrivals])
            model.add(selected_arrival <= sum(c.variable for c in previous_choices))
            # Si une personne sans transmission possible est sélectionnée,
            # une personne qui termine au plus tard au même moment doit être
            # sélectionnée avec une transmission possible. Ces implications
            # imposent exactement le minimum des fins des quarts sélectionnés,
            # et autorisent plusieurs personnes à terminer en même temps.
            earlier_good: dict[int, Any] = {}
            for bad in bad_choices:
                threshold = bad.shift.coverage_end
                if threshold not in earlier_good:
                    good_variables = [c.variable for c in previous_choices
                                      if c.shift.coverage_end <= threshold]
                    possible = model.new_bool_var(f"releve_{profile_number}_{threshold}")
                    if good_variables:
                        model.add_max_equality(possible, good_variables)
                    else:
                        model.add(possible == 0)
                    earlier_good[threshold] = possible
                model.add(selected_arrival + bad.variable <= 1 + earlier_good[threshold])


def generate(week: Week, time_limit: float = 20) -> GenerationResult:
    """Retourne une proposition indépendante; n'écrit et ne modifie jamais week.

    Un échec ``infeasible_candidates`` décrit la recherche restreinte et ne
    prétend pas que tout horaire possible serait mathématiquement impossible.
    Les garanties, maximums, disponibilités et pauses restent obligatoires.
    """
    try:
        from ortools.sat.python import cp_model
    except ImportError:
        return GenerationResult(False, None, "Le moteur OR-Tools n'est pas installé. Installez les dépendances du projet avant de générer.", "missing_dependency")
    from .validation import validate

    # Les erreurs de structure sont signalées avant tout accès au solveur.
    try:
        snapshot = Week.from_dict(week.to_dict())
        if snapshot.planning_date:
            structural = [issue.message for issue in validate(snapshot) if issue.code == "missing_data"]
            if structural:
                return GenerationResult(False, None, "Corrigez les données avant de générer l’horaire.", "invalid_data", structural)
            from .planning import service_view
            snapshot = service_view(snapshot)
    except (TypeError, ValueError) as exc:
        return GenerationResult(False, None, str(exc), "invalid_data")
    settings = snapshot.settings
    if (not 0 <= settings.open_minute < settings.close_minute <= 1440 or
        settings.opening_buffer < 0 or settings.closing_buffer < 0 or
        settings.open_minute - settings.opening_buffer < 0 or
        settings.close_minute + settings.closing_buffer > 1440 or
        settings.handover_minutes < 0 or settings.max_daily_minutes < 0):
        return GenerationResult(False, None, "Les heures d'ouverture, de fermeture ou les buffers sont invalides.", "invalid_data")
    if any(e.max_minutes < 0 or e.guaranteed_minutes < 0 or e.target_minutes < 0 or
           e.guaranteed_minutes > e.max_minutes for e in snapshot.educators):
        return GenerationResult(False, None, "Les heures garanties et cibles doivent être positives; une garantie ne peut pas dépasser le maximum.", "invalid_data")
    if any(g.ratio <= 0 or g.min_educators < 2 or
           any(p.day not in range(5) or not 0 <= p.start < p.end <= 1440 or p.students < 0
               for p in g.periods) for g in snapshot.groups):
        return GenerationResult(False, None, "Corrigez les groupes : ratio positif, minimum de deux éducatrices, périodes valides et effectifs positifs.", "invalid_data")
    retained = copy.deepcopy(snapshot)
    retained.shifts = [s for s in retained.shifts if s.locked]
    fixed_issues = [i for i in validate(retained) if i.severity == "error" and
                    i.code in {"room_conflict", "room_capacity", "room_unavailable", "activity_overlap", "missing_data"}]
    if fixed_issues:
        return GenerationResult(False, None,
            "Corrigez d'abord les données ou les activités : la génération des quarts ne peut pas résoudre ces conflits.",
            "invalid_data", [i.message for i in fixed_issues[:15]])
    impossible = _requirements(snapshot)
    if impossible:
        return GenerationResult(False, None, "La couverture est impossible avec les disponibilités actuelles.", "infeasible", impossible)
    candidates, diagnostic = _build_candidates(snapshot)
    if diagnostic:
        return GenerationResult(False, None, "La génération ne peut pas commencer.", "invalid_data", diagnostic)
    if not candidates:
        return GenerationResult(False, None, "Aucun quart compatible avec les disponibilités et les buffers n'a pu être construit.", "infeasible_candidates")
    model = cp_model.CpModel()
    educator_intervals: dict[str, list] = defaultdict(list)
    by_person: dict[str, list[_Candidate]] = defaultdict(list)
    for i, candidate in enumerate(candidates):
        shift = candidate.shift
        variable = model.new_bool_var(f"quart_{i}")
        candidate.variable = variable
        if shift.locked:
            model.add(variable == 1)
        absolute_start = shift.day * 1440 + shift.start
        interval = model.new_optional_fixed_size_interval_var(absolute_start, shift.end - shift.start, variable, f"presence_{i}")
        educator_intervals[shift.educator_id].append(interval)
        by_person[shift.educator_id].append(candidate)
    for intervals in educator_intervals.values():
        model.add_no_overlap(intervals)
    for group in snapshot.groups:
        for day in snapshot.active_days:
            requirements = [(p.start, p.end, required_educators(group, p.students))
                            for p in group.periods if p.day == day]
            if requirements:
                _cover(model, candidates, day, requirements, group.id)
    for day in snapshot.active_days:
        if any(p.day == day for group in snapshot.groups for p in group.periods):
            _cover(model, candidates, day,
                   [(settings.open_minute - settings.opening_buffer,
                     settings.close_minute + settings.closing_buffer, 2)])
    for activity in (() if snapshot.planning_date else snapshot.activities):
        if not activity.responsible_ids:
            continue
        group = next((g for g in snapshot.groups if g.id == activity.group_id), None)
        if group is None:
            continue
        needs = [(max(activity.start, p.start), min(activity.end, p.end), required_educators(group, p.students))
                 for p in group.periods if p.day == activity.day and
                 max(activity.start, p.start) < min(activity.end, p.end)]
        if needs:
            _cover(model, candidates, activity.day, needs, group.id, set(activity.responsible_ids))
    _handovers(model, candidates, snapshot)
    objective = []
    ranked = sorted((e for e in snapshot.educators if e.active), key=lambda e: (e.seniority, e.name.casefold(), e.id))
    priorities = {e.id: len(ranked) - idx for idx, e in enumerate(ranked)}
    for educator in snapshot.educators:
        choices = by_person[educator.id]
        total = model.new_int_var(0, max(0, educator.max_minutes), f"minutes_{educator.id}")
        model.add(total == sum(c.paid * c.variable for c in choices))
        model.add(total >= educator.guaranteed_minutes if educator.active else total == 0)
        bound = max(educator.max_minutes, educator.target_minutes, 1)
        under = model.new_int_var(0, bound, f"manque_{educator.id}")
        over = model.new_int_var(0, bound, f"surplus_{educator.id}")
        model.add(total + under - over == educator.target_minutes)
        priority = priorities.get(educator.id, 0)
        objective.append(under * (max(0, settings.target_weight) + max(0, settings.seniority_weight) * priority))
        objective.append(over * max(1, settings.target_weight))
        if settings.max_daily_minutes:
            for day in snapshot.active_days:
                model.add(sum(c.paid * c.variable for c in choices if c.shift.day == day) <= settings.max_daily_minutes)
        for candidate in choices:
            if educator.preferred_groups and candidate.shift.group_id not in educator.preferred_groups:
                objective.append(candidate.variable * candidate.paid * max(0, settings.preference_weight))
            # À qualité égale, préférer moins de relèves et de quarts morcelés.
            objective.append(candidate.variable * 10)
    model.minimize(sum(objective))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max(0.1, min(float(time_limit), 120.0))
    solver.parameters.num_search_workers = 4
    solver.parameters.random_seed = 17
    status = solver.solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        if status == cp_model.INFEASIBLE:
            return GenerationResult(False, None,
                "Aucune combinaison des quarts candidats ne respecte toutes les règles. Vérifiez les heures maximales et garanties, les quarts verrouillés, les pauses et les buffers. Cela ne prouve pas qu'aucun autre découpage à la minute n'existe.",
                "infeasible_candidates", [f"{len(candidates)} quarts candidats examinés; aucune modification enregistrée."])
        if status == cp_model.MODEL_INVALID:
            return GenerationResult(False, None, "Les contraintes contiennent des données incohérentes. Vérifiez les quarts verrouillés et les limites d'heures.", "invalid_data", [solver.solution_info()])
        return GenerationResult(False, None,
            "Le temps de recherche est écoulé sans proposition valide. Vous pouvez augmenter la durée de recherche ou préciser les disponibilités.", "timeout")
    proposal = copy.deepcopy(snapshot)
    proposal.status = "draft"
    proposal.shifts = [copy.deepcopy(c.shift) for c in candidates if solver.boolean_value(c.variable)]
    proposal.shifts.sort(key=lambda s: (s.day, s.start, s.group_id, s.educator_id))
    issues = validate(proposal)
    blocking = [issue for issue in issues if issue.severity == "error"]
    if blocking:
        return GenerationResult(False, None,
            "Le solveur a trouvé des quarts, mais la vérification complète détecte encore des erreurs. La proposition n'a pas été appliquée.",
            "validation_failed", [issue.message for issue in blocking[:15]])
    label = "optimale dans les quarts candidats" if status == cp_model.OPTIMAL else "valide, optimisation interrompue au délai choisi"
    return GenerationResult(True, proposal,
        f"Proposition {label}. Examinez-la avant de l'appliquer; {len(proposal.shifts)} quarts, {len(issues)} avertissements.",
        "optimal" if status == cp_model.OPTIMAL else "feasible",
        ["La recherche utilise des bornes métier exactes et des départs intermédiaires espacés d'une heure.",
         "Les quarts non verrouillés seront remplacés uniquement après votre confirmation."])
