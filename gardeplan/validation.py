"""Validation déterministe hors ligne des quarts, couvertures, relèves et locaux.

La vérification balaye les minutes exactes puis regroupe les erreurs identiques
adjacentes en intervalles lisibles. Aucun arrondi ni approximation par tranche.
"""
from __future__ import annotations
from .staffing import minimum_presence, pupil_requirement, daily_limit

from dataclasses import dataclass, field
from collections import defaultdict
from .models import (
    Week, Window, Shift, DAYS, coverage_intervals, working_intervals,
    paid_minutes, totals, required_educators, merge_intervals, format_time,
    format_duration, STATUSES,
)


@dataclass
class Issue:
    severity: str
    code: str
    message: str
    day: int | None = None
    start: int | None = None
    end: int | None = None
    group_id: str = ""
    shift_ids: list[str] = field(default_factory=list)
    suggestion: str = ""


def _interval_ok(start, end) -> bool:
    return type(start) is int and type(end) is int and 0 <= start < end <= 1440


def _day_ok(day) -> bool:
    return type(day) is int and 0 <= day < 5


def _contains(intervals: list[tuple[int, int]], start: int, end: int) -> bool:
    return any(a <= start and end <= b for a, b in merge_intervals(intervals))


def _available(windows: list[Window], day: int, start: int, end: int) -> bool:
    return not windows or _contains([(w.start, w.end) for w in windows if w.day == day], start, end)


def _overlap(a: int, b: int, c: int, d: int) -> bool:
    return max(a, c) < min(b, d)


def _minute_runs(values):
    """(minute, key) -> (start, end, key), ignore None values."""
    start, previous, key = None, None, None
    for minute, value in values:
        if value != key or (previous is not None and minute != previous + 1):
            if key is not None:
                yield start, previous + 1, key
            start, key = minute, value
        previous = minute
    if key is not None:
        yield start, previous + 1, key


def _prefix(day, start, end):
    return f"{DAYS[day]}, {format_time(start)} à {format_time(end)} : "


def validate(week: Week, *, _service=False) -> list[Issue]:
    if week.planning_date and not _service:
        from .planning import service_view
        from copy import deepcopy
        safe = len({g.id for g in week.groups}) == len(week.groups) and all(g.name.strip() and g.ratio > 0 and g.min_educators >= 2 and
                   all(0 <= p.start < p.end <= 1440 and p.students >= 0 for p in g.periods)
                   and all(a.day != b.day or max(a.start, b.start) >= min(a.end, b.end)
                           for i, a in enumerate(g.periods) for b in g.periods[i+1:])
                   for g in week.groups)
        schedule = service_view(week) if safe else deepcopy(week)
        schedule.activities, schedule.rooms = [], []
        return validate(schedule, _service=True)
    issues: list[Issue] = []
    def add(code, message, day=None, start=None, end=None, group_id="", shift_ids=None, suggestion="", severity="error"):
        if week.planning_date and day == 0:
            message = message.replace("Lundi,", week.day_label(0).split(" — ", 1)[0] + ",", 1)
        if week.planning_date:
            message = message.replace("du groupe Service de garde", "du service de garde").replace("au groupe Service de garde", "au service de garde").replace("le groupe Service de garde", "le service de garde").replace("groupe Service de garde", "service de garde").replace("ce groupe", "le service de garde").replace("un groupe introuvable", "une affectation introuvable")
            suggestion = suggestion.replace("rouvrir le groupe", "rouvrir le service de garde")
        issues.append(Issue(severity, code, message, day, start, end, group_id, shift_ids or [], suggestion))

    educators = {e.id: e for e in week.educators}
    groups = {g.id: g for g in week.groups}
    rooms = {r.id: r for r in week.rooms}
    settings = week.settings
    for entries, title in ((week.educators, "éducatrices"), (week.groups, "groupes"), (week.rooms, "lieux"), (week.shifts, "quarts"), (week.activities, "activités")):
        ids = [x.id for x in entries]
        if len(set(ids)) != len(ids) or any(not isinstance(x, str) or not x for x in ids):
            add("missing_data", f"Les identifiants des {title} sont manquants ou en double.")
    if week.status not in STATUSES:
        add("missing_data", "Le statut de l'horaire est invalide.")
    if not week.groups:
        add("missing_data", "Renseignez les inscriptions de la journée." if week.planning_date else "Ajoutez au moins un groupe et ses heures d'ouverture.", suggestion="Ouvrir les inscriptions.")
    if not week.educators and (not week.planning_date or any(group.periods for group in week.groups)):
        add("missing_data", "Ajoutez des éducatrices avant de préparer l'horaire.", suggestion="Cliquer sur Ajouter une éducatrice.")
    valid_settings = (
        _interval_ok(settings.open_minute, settings.close_minute)
        and all(type(x) is int and x >= 0 for x in (
            settings.opening_buffer, settings.closing_buffer, settings.handover_minutes,
            settings.break_minutes, settings.break_after_minutes, settings.max_daily_minutes,
        ))
        and settings.opening_buffer >= 10
        and settings.closing_buffer >= 5
        and settings.handover_minutes >= 15
        and settings.open_minute >= settings.opening_buffer
        and settings.close_minute + settings.closing_buffer <= 1440
        and (settings.break_minutes == 0 or settings.break_after_minutes > 0)
    )
    if not valid_settings:
        add("missing_data", "Les paramètres sont invalides. Prévoyez au minimum 10 minutes pour ouvrir les locaux, 5 minutes pour fermer l'école et 15 minutes communes à chaque relève. Vérifiez aussi les heures d'ouverture et la politique de pauses.")

    valid_periods = defaultdict(list)
    for g in week.groups:
        if not g.name.strip() or type(g.ratio) is not int or g.ratio < 1 or type(g.min_educators) is not int or g.min_educators < 2:
            add("missing_data", f"Le groupe {g.name or '(sans nom)'} doit avoir un nom, un ratio positif et un minimum d'au moins deux éducatrices.", group_id=g.id)
        for p in g.periods:
            if not _day_ok(p.day) or not _interval_ok(p.start, p.end) or type(p.students) is not int or p.students < 0:
                add("missing_data", f"Une période du groupe {g.name} contient des heures ou un effectif invalides.", group_id=g.id)
                continue
            valid_periods[(g.id, p.day)].append(p)
        for day in week.active_days:
            periods = sorted(valid_periods[(g.id, day)], key=lambda p: p.start)
            for earlier, later in zip(periods, periods[1:]):
                if earlier.end > later.start:
                    add("missing_data", _prefix(day, later.start, min(earlier.end, later.end)) + f"les périodes d'effectifs du groupe {g.name} se chevauchent.", day, later.start, min(earlier.end, later.end), g.id,
                        suggestion="Utiliser des périodes d'effectifs successives sans chevauchement.")
    for e in week.educators:
        if week.planning_date and any(other.id != e.id and other.seniority == e.seniority for other in week.educators):
            add("missing_data", f"Le rang {e.seniority} de {e.name} est déjà utilisé. Choisissez un rang libre de 1 à 11.")
        if week.planning_date and (type(e.seniority) is not int or not 1 <= e.seniority <= 11):
            add("missing_data", f"Choisissez un rang de 1 à 11 pour {e.name}. Les rangs intermédiaires peuvent rester libres.")
        if not e.name.strip() or any(type(x) is not int or x < 0 for x in (e.target_minutes, e.guaranteed_minutes, e.max_minutes)) or type(e.seniority) is not int or e.seniority < 1:
            add("missing_data", f"La fiche de {e.name or '(sans nom)'} est incomplète ou contient des heures invalides.")
        elif e.guaranteed_minutes > e.max_minutes:
            add("missing_data", f"Les heures garanties de {e.name} dépassent son maximum autorisé.")
        for w in e.availability + e.absences:
            if not _day_ok(w.day) or not _interval_ok(w.start, w.end):
                add("missing_data", f"Une disponibilité ou absence de {e.name} est invalide.")
    for r in week.rooms:
        if not r.name.strip() or type(r.capacity) is not int or r.capacity < 0:
            add("missing_data", f"Le lieu {r.name or '(sans nom)'} doit avoir un nom et une capacité entière positive (ou zéro sans limite déclarée).")
        for w in r.availability:
            if not _day_ok(w.day) or not _interval_ok(w.start, w.end):
                add("missing_data", f"Une disponibilité du lieu {r.name} est invalide.")

    shifts: list[Shift] = []
    coverage = {}
    working = {}
    by_educator = defaultdict(list)
    by_group_day = defaultdict(list)
    for s in week.shifts:
        if s.educator_id not in educators or s.group_id not in groups:
            add("missing_data", "Un quart fait référence à une éducatrice ou à un groupe introuvable.", shift_ids=[s.id])
            continue
        e = educators[s.educator_id]
        if not _day_ok(s.day) or not _interval_ok(s.start, s.end) or any(type(x) is not int or x < 0 for x in (s.buffer_before, s.buffer_after)) or s.buffer_before + s.buffer_after >= s.end - s.start:
            add("missing_data", f"Les heures ou buffers du quart de {e.name} sont invalides.", shift_ids=[s.id])
            continue
        if week.planning_date and valid_settings and (s.start < settings.open_minute-settings.opening_buffer or s.end > settings.close_minute+settings.closing_buffer):
            add("service_hours", f"Le quart de {e.name} doit rester entre {format_time(settings.open_minute-settings.opening_buffer)} et {format_time(settings.close_minute+settings.closing_buffer)}.", s.day, s.start, s.end, s.group_id, [s.id])
        breaks_ok = True
        for b in s.breaks:
            if not _interval_ok(b.start, b.end) or not (s.start <= b.start < b.end <= s.end):
                add("missing_data", f"Une pause de {e.name} doit être comprise dans son quart.", s.day, s.start, s.end, s.group_id, [s.id])
                breaks_ok = False
        if not breaks_ok:
            continue
        for a, b in zip(sorted(s.breaks, key=lambda b: b.start), sorted(s.breaks, key=lambda b: b.start)[1:]):
            if a.end > b.start:
                add("missing_data", f"Deux pauses de {e.name} se chevauchent.", s.day, b.start, min(a.end, b.end), s.group_id, [s.id])
        if not e.active:
            add("missing_data", f"{e.name} est inactive, mais un quart lui est affecté.", s.day, s.start, s.end, s.group_id, [s.id])
        if not _available(e.availability, s.day, s.start, s.end):
            add("availability", _prefix(s.day, s.start, s.end) + f"{e.name} n'est pas disponible pendant tout le quart, buffers compris.", s.day, s.start, s.end, s.group_id, [s.id], "Ajuster le quart ou choisir une éducatrice disponible.")
        for absence in e.absences:
            if absence.day == s.day and _overlap(s.start, s.end, absence.start, absence.end):
                a, b = max(s.start, absence.start), min(s.end, absence.end)
                add("absence", _prefix(s.day, a, b) + f"{e.name} est absente ou en congé.", s.day, a, b, s.group_id, [s.id], "Remplacer cette éducatrice.")
        if e.preferred_groups and s.group_id not in e.preferred_groups:
            add("preference", f"Le groupe {groups[s.group_id].name} ne fait pas partie des préférences de {e.name}.", s.day, s.start, s.end, s.group_id, [s.id], severity="warning")
        if s.buffer_before > max(30, settings.opening_buffer, settings.handover_minutes) or s.buffer_after > max(15, settings.closing_buffer):
            add("buffer", f"Le quart de {e.name} comprend un buffer inhabituellement long.", s.day, s.start, s.end, s.group_id, [s.id], severity="warning")
        if valid_settings and settings.break_minutes > 0:
            segments = coverage_intervals(s)
            if any(b - a > settings.break_after_minutes for a, b in segments):
                add("break_policy", f"{e.name} travaille plus de {format_duration(settings.break_after_minutes)} sans la pause configurée.", s.day, s.start, s.end, s.group_id, [s.id], "Ajouter une pause avec remplacement pour maintenir la couverture.")
            if s.coverage_end - s.coverage_start > settings.break_after_minutes and not any(b.end - b.start >= settings.break_minutes for b in s.breaks):
                add("break_policy", f"La pause de {format_duration(settings.break_minutes)} configurée manque au quart de {e.name}.", s.day, s.start, s.end, s.group_id, [s.id])
        # Une préparation des inscriptions peut fermer un groupe sans
        # supprimer les quarts déjà saisis. Les garder visibles et signaler
        # clairement les minutes devenues inutiles au lieu de les effacer.
        opened = merge_intervals([(p.start, p.end) for p in valid_periods[(s.group_id, s.day)]])
        outside = []
        for a, b in coverage_intervals(s):
            outside.extend((minute, True if not any(x <= minute < y for x, y in opened) else None) for minute in range(a, b))
        for a, b, _ in _minute_runs(outside):
            add("closed_group_shift", _prefix(s.day, a, b) + f"{e.name} est affectée au groupe {groups[s.group_id].name} alors que ce groupe est fermé.", s.day, a, b, s.group_id, [s.id], "Réviser ce quart ou rouvrir le groupe si des enfants sont présents.", severity="warning")
        if e.active:
            shifts.append(s)
            coverage[s.id] = coverage_intervals(s)
            working[s.id] = working_intervals(s)
            by_group_day[(s.group_id, s.day)].append(s)
        by_educator[(s.educator_id, s.day)].append(s)

    for (educator_id, day), daily in by_educator.items():
        daily.sort(key=lambda s: s.start)
        for index, s in enumerate(daily):
            for other in daily[index + 1:]:
                if other.start >= s.end:
                    break
                add("overlap", _prefix(day, other.start, min(s.end, other.end)) + f"{educators[educator_id].name} est affectée à deux quarts simultanément.", day, other.start, min(s.end, other.end), s.group_id, [s.id, other.id], "Déplacer ou raccourcir un des deux quarts.")
        minutes = sum(paid_minutes(s) for s in daily)
        if valid_settings and daily_limit(week) and minutes > daily_limit(week):
            add("max_daily", f"{DAYS[day]} : {educators[educator_id].name} dépasse la limite quotidienne de {format_duration(daily_limit(week))}.", day, shift_ids=[s.id for s in daily])

    # Les présences de chaque éducatrice sont comptées une seule fois.
    for (group_id, day), periods in valid_periods.items():
        if not periods:
            continue
        g = groups[group_id]
        if type(g.ratio) is not int or g.ratio < 1 or type(g.min_educators) is not int or g.min_educators < 2:
            continue  # The missing_data issue above must be reported before calculations.
        staff = by_group_day[(group_id, day)]
        values = []
        for minute in range(min(p.start for p in periods), max(p.end for p in periods)):
            present_periods = [p for p in periods if p.start <= minute < p.end]
            if not present_periods:
                values.append((minute, None)); continue
            students = max(p.students for p in present_periods)
            required = pupil_requirement(week,minute,students,g.ratio,g.min_educators)
            actual = len({s.educator_id for s in staff if any(a <= minute < b for a, b in coverage[s.id])})
            code = "coverage" if actual < max(minimum_presence(week,minute),g.min_educators if g.min_educators > 2 else 0) else "ratio"
            values.append((minute, (code, required, actual) if actual < required else None))
        for a, b, (code, required, actual) in _minute_runs(values):
            affected = [s.id for s in staff if _overlap(s.start, s.end, a, b)]
            add(code, _prefix(day, a, b) + f"le groupe {g.name} nécessite {required} éducatrices, mais seulement {actual} sont disponibles.", day, a, b, group_id, affected, f"Ajouter {required - actual} éducatrice(s) disponible(s) pendant cette période.")

    # École ouverte : deux personnes au travail en continu, préparation et fermeture incluses.
    if valid_settings:
        active_days = {day for (_, day), periods in valid_periods.items() if periods}
        for day in sorted(active_days):
            staff = [s for s in shifts if s.day == day]
            a, b = settings.open_minute - settings.opening_buffer, settings.close_minute + settings.closing_buffer
            values = []
            for minute in range(a, b):
                actual = len({s.educator_id for s in staff if any(x <= minute < y for x, y in working[s.id])})
                code = "opening" if minute < settings.open_minute else "closing" if minute >= settings.close_minute else "school_coverage"
                required = minimum_presence(week,minute)
                values.append((minute, (code, actual, required) if actual < required else None))
            for start, end, (code, actual, required) in _minute_runs(values):
                subject = "l'ouverture des locaux" if code == "opening" else "la fermeture de l'école" if code == "closing" else "la continuité du service de garde"
                add(code, _prefix(day, start, end) + f"{subject} exige {required} éducatrice(s) présente(s); seulement {actual} sont au travail.", day, start, end, shift_ids=[s.id for s in staff if _overlap(s.start, s.end, start, end)], suggestion=f"Ajuster les quarts pour conserver {required} éducatrice(s) présente(s) simultanément.")

        # Une arrivée en cours d'ouverture doit avoir quinze minutes communes
        # avec une personne déjà responsable du même groupe. Les buffers payés
        # peuvent servir à cette relève, mais une pause ne peut pas le faire.
        handover = settings.handover_minutes
        if handover:
            for s in shifts:
                t = s.coverage_start
                periods = valid_periods[(s.group_id, s.day)]
                if not any(p.start < t <= p.end for p in periods):
                    continue  # première ouverture du groupe ou reprise après fermeture
                # Un changement d'effectif à t n'est pas une réouverture.
                if not any(p.start <= t - 1 < p.end for p in periods):
                    continue
                predecessors = [p for p in by_group_day[(s.group_id, s.day)] if p.id != s.id and p.educator_id != s.educator_id and p.coverage_start < t and p.coverage_end >= t]
                # Prioriser la personne qui quitte le groupe : une collègue
                # restant toute la journée ne remplace pas la transmission
                # avec le quart qui se termine maintenant.
                if predecessors:
                    first_departure = min(p.coverage_end for p in predecessors)
                    predecessors = [p for p in predecessors if p.coverage_end == first_departure]
                good = False
                for previous in predecessors:
                    for a, b in working[s.id]:
                        for c, d in working[previous.id]:
                            start, end = max(a, c), min(b, d)
                            if end - start >= handover and start <= t <= end:
                                good = True
                if not good:
                    add("handover", _prefix(s.day, max(0, t - handover), t) + f"la relève de {educators[s.educator_id].name} dans {groups[s.group_id].name} ne dispose pas de {handover} minutes communes avec une éducatrice déjà présente.", s.day, max(0, t - handover), t, s.group_id, [s.id], f"Faire commencer la relève {handover} minutes plus tôt ou prolonger le quart précédent.")

    actual_totals = totals(week)
    for e in week.educators:
        if not e.active:
            continue
        minutes = actual_totals.get(e.id, 0)
        if minutes > e.max_minutes:
            add("max_hours", f"{e.name} totalise {format_duration(minutes)}, au-delà du maximum de {format_duration(e.max_minutes)}.", shift_ids=[s.id for s in week.shifts if s.educator_id == e.id], suggestion="Réaffecter des heures à une autre éducatrice.")
        if minutes < e.guaranteed_minutes:
            add("guarantee", f"Il manque {format_duration(e.guaranteed_minutes - minutes)} aux heures garanties de {e.name}.", suggestion="Attribuer des quarts supplémentaires compatibles avec ses disponibilités.")
        if minutes != e.target_minutes and (e.target_minutes or not week.planning_date):
            label = "manquent" if minutes < e.target_minutes else "dépassent la cible"
            add("target", f"{e.name} : {format_duration(abs(minutes - e.target_minutes))} {label} ({format_duration(minutes)} planifiées sur {format_duration(e.target_minutes)} visées).", severity="warning")
    # L'ancienneté conseille, elle ne peut rendre une disponibilité irréalisable obligatoire.
    active = sorted([e for e in week.educators if e.active], key=lambda e: e.seniority)
    for index, senior in enumerate(active):
        if actual_totals.get(senior.id, 0) >= senior.target_minutes:
            continue
        for junior in active[index + 1:]:
            if actual_totals.get(junior.id, 0) <= junior.target_minutes or junior.seniority == senior.seniority:
                continue
            add("seniority", f"{junior.name} dépasse sa cible alors que {senior.name}, plus ancienne, n'atteint pas la sienne.", suggestion="Vérifier si les disponibilités permettent une répartition selon l'ancienneté.", severity="warning")
            break
    ratios = [actual_totals.get(e.id, 0) * 100 // e.target_minutes for e in active if e.target_minutes > 0]
    if len(ratios) >= 2 and max(ratios) - min(ratios) > 40:
        add("balance", "Les heures sont réparties de façon déséquilibrée par rapport aux cibles configurées.", severity="warning")

    activities = []
    for activity in week.activities:
        a = activity
        if a.group_id not in groups or not a.name.strip() or not _day_ok(a.day) or not _interval_ok(a.start, a.end):
            add("missing_data", "Une activité possède un nom, un groupe ou des heures invalides.")
            continue
        if not a.room_id or a.room_id not in rooms:
            add("missing_data", f"L'activité {a.name} n'a pas de lieu valide.", a.day, a.start, a.end, a.group_id)
        else:
            room = rooms[a.room_id]
            if not _available(room.availability, a.day, a.start, a.end):
                add("room_unavailable", _prefix(a.day, a.start, a.end) + f"{room.name} n'est pas disponible pour {a.name}.", a.day, a.start, a.end, a.group_id)
        if any(eid not in educators for eid in a.responsible_ids):
            add("missing_data", f"Un responsable de l'activité {a.name} est introuvable.", a.day, a.start, a.end, a.group_id)
        staff = by_group_day[(a.group_id, a.day)]
        periods = valid_periods[(a.group_id, a.day)]
        values = []
        for minute in range(a.start, a.end):
            active_periods = [p for p in periods if p.start <= minute < p.end]
            required = required_educators(groups[a.group_id], max((p.students for p in active_periods), default=0))
            present_ids = {s.educator_id for s in staff if any(x <= minute < y for x, y in coverage[s.id])}
            actual = len(present_ids & set(a.responsible_ids)) if a.responsible_ids else len(present_ids)
            value = (required, actual, bool(active_periods)) if actual < required or not active_periods else None
            values.append((minute, value))
        for start, end, (required, actual, opened) in _minute_runs(values):
            text = f"l'activité {a.name} requiert {required} éducatrices responsables; {actual} la couvrent réellement." if opened else f"l'activité {a.name} est située pendant la fermeture du groupe {groups[a.group_id].name}."
            add("activity_coverage", _prefix(a.day, start, end) + text, a.day, start, end, a.group_id, [s.id for s in staff if _overlap(s.start, s.end, start, end)], "Ajuster les affectations ou les heures de l'activité.")
        activities.append(a)
    for index, a in enumerate(activities):
        for b in activities[index + 1:]:
            if a.day != b.day or not _overlap(a.start, a.end, b.start, b.end):
                continue
            start, end = max(a.start, b.start), min(a.end, b.end)
            if a.group_id == b.group_id and not (a.compatible and b.compatible):
                add("activity_overlap", _prefix(a.day, start, end) + f"le groupe {groups[a.group_id].name} a deux activités incompatibles : {a.name} et {b.name}.", a.day, start, end, a.group_id)
            if (a.room_id and a.room_id == b.room_id and a.room_id in rooms and not rooms[a.room_id].shared
                    and not (a.group_id == b.group_id and a.compatible and b.compatible)):
                add("room_conflict", _prefix(a.day, start, end) + f"{rooms[a.room_id].name} est réservé simultanément pour {a.name} et {b.name}.", a.day, start, end, a.group_id, suggestion="Changer le lieu ou les heures d'une activité.")
    # La capacité s'évalue sur tous les groupes simultanés, pas seulement par paire.
    for room in week.rooms:
        if room.capacity <= 0:
            continue
        for day in week.active_days:
            reservations = [a for a in activities if a.room_id == room.id and a.day == day]
            if not reservations:
                continue
            values = []
            for minute in range(min(a.start for a in reservations), max(a.end for a in reservations)):
                group_ids = {a.group_id for a in reservations if a.start <= minute < a.end}
                students = sum(max((p.students for p in valid_periods[(gid, day)] if p.start <= minute < p.end), default=0) for gid in group_ids)
                values.append((minute, students if students > room.capacity else None))
            for start, end, students in _minute_runs(values):
                add("room_capacity", _prefix(day, start, end) + f"{room.name} accueille {students} enfants pour une capacité de {room.capacity}.", day, start, end, suggestion="Choisir un lieu plus grand ou séparer les groupes.")
    return issues
