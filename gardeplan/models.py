"""Modèle local du planificateur. Toutes les heures/durées sont des minutes entières.

Les intervalles sont semi-ouverts [début, fin[. Shift.start/end décrivent la
présence; les buffers et toutes les pauses sont retirés de la couverture.
Une disponibilité vide signifie aucune restriction hebdomadaire déclarée.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from typing import Any
from uuid import uuid4
import copy
import math

DAYS = ("Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi")
STATUSES = ("draft", "validated", "published", "archived")
STATUS_LABELS = {"draft": "Brouillon", "validated": "Validé", "published": "Publié", "archived": "Archivé"}


def new_id() -> str:
    return uuid4().hex


def format_time(value: int) -> str:
    return f"{value // 60:02d} h {value % 60:02d}"


def format_duration(value: int) -> str:
    sign = "−" if value < 0 else ""
    value = abs(value)
    return f"{sign}{value // 60} h {value % 60:02d}"


@dataclass
class Window:
    day: int
    start: int
    end: int


@dataclass
class Educator:
    id: str
    name: str
    seniority: int = 1
    target_minutes: int = 2100
    guaranteed_minutes: int = 0
    max_minutes: int = 2400
    availability: list[Window] = field(default_factory=list)
    absences: list[Window] = field(default_factory=list)
    preferred_groups: list[str] = field(default_factory=list)
    restrictions: str = ""
    color: str = "#476FD0"
    active: bool = True
    seniority_date: str = ""


@dataclass
class GroupPeriod:
    day: int
    start: int
    end: int
    students: int


@dataclass
class Group:
    id: str
    name: str
    color: str = "#298A80"
    ratio: int = 20
    min_educators: int = 2
    periods: list[GroupPeriod] = field(default_factory=list)


@dataclass
class Room:
    id: str
    name: str
    capacity: int = 0  # 0 : aucune limite déclarée
    shared: bool = False
    outdoor: bool = False
    availability: list[Window] = field(default_factory=list)


@dataclass
class Break:
    start: int
    end: int
    paid: bool = False
    kind: str = "pause"


@dataclass
class Shift:
    id: str
    educator_id: str
    group_id: str
    day: int
    start: int
    end: int
    buffer_before: int = 0
    buffer_after: int = 0
    before_paid: bool = True
    after_paid: bool = True
    breaks: list[Break] = field(default_factory=list)
    locked: bool = False

    @property
    def coverage_start(self) -> int:
        return self.start + self.buffer_before

    @property
    def coverage_end(self) -> int:
        return self.end - self.buffer_after


@dataclass
class Activity:
    id: str
    name: str
    group_id: str
    day: int
    start: int
    end: int
    room_id: str = ""
    notes: str = ""
    responsible_ids: list[str] = field(default_factory=list)
    compatible: bool = False


@dataclass
class Settings:
    open_minute: int = 420
    close_minute: int = 1050
    opening_buffer: int = 10
    closing_buffer: int = 5
    handover_minutes: int = 15
    snap_minutes: int = 1
    zoom: float = 1.0  # échelle graphique seulement, jamais une durée
    seniority_weight: int = 10
    preference_weight: int = 5
    target_weight: int = 2
    break_after_minutes: int = 360
    break_minutes: int = 0
    break_paid: bool = False
    max_daily_minutes: int = 720


@dataclass
class Week:
    monday: str
    educators: list[Educator] = field(default_factory=list)
    groups: list[Group] = field(default_factory=list)
    rooms: list[Room] = field(default_factory=list)
    shifts: list[Shift] = field(default_factory=list)
    activities: list[Activity] = field(default_factory=list)
    settings: Settings = field(default_factory=Settings)
    day_names: dict[int, str] = field(default_factory=dict)
    status: str = "draft"
    planning_date: str = ""  # Daily records use local day index 0; legacy weeks remain readable.

    @property
    def active_days(self):
        return (0,) if self.planning_date else tuple(range(5))

    @property
    def storage_key(self):
        return "day:" + self.planning_date if self.planning_date else self.monday

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Week:
        return from_dict(data)

    def day_label(self, day: int) -> str:
        current = date.fromisoformat(self.planning_date or self.monday) + timedelta(days=day)
        label = f"{(DAYS + ('Samedi', 'Dimanche'))[current.weekday()]} {current:%d/%m}"
        custom = self.day_names.get(day, self.day_names.get(str(day), "")).strip()
        return f"{label} — {custom}" if custom else label


def to_dict(week: Week) -> dict[str, Any]:
    return week.to_dict()


def _construct(cls, raw: Any, children: dict[str, Any] | None = None):
    """Refuse les sauvegardes mal formées avant d'entrer dans le domaine."""
    if not isinstance(raw, dict):
        raise ValueError(f"Données invalides pour {cls.__name__}.")
    unknown = set(raw) - set(cls.__dataclass_fields__)
    if unknown:
        raise ValueError(f"Champs inconnus pour {cls.__name__} : {', '.join(sorted(unknown))}.")
    values = dict(raw)
    for key, child in (children or {}).items():
        if key in values:
            if not isinstance(values[key], list):
                raise ValueError(f"La liste {key} est invalide.")
            values[key] = [_construct(child, x) for x in values[key]]
    try:
        result = cls(**values)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Données incomplètes pour {cls.__name__}.") from exc
    integer_fields = {
        "day", "start", "end", "students", "seniority", "target_minutes", "guaranteed_minutes",
        "max_minutes", "ratio", "min_educators", "capacity", "buffer_before", "buffer_after",
        "open_minute", "close_minute", "opening_buffer", "closing_buffer", "handover_minutes",
        "snap_minutes", "seniority_weight", "preference_weight", "target_weight", "break_after_minutes",
        "break_minutes", "max_daily_minutes",
    }
    bool_fields = {"active", "shared", "outdoor", "paid", "before_paid", "after_paid", "locked", "compatible", "break_paid"}
    for key in cls.__dataclass_fields__:
        val = getattr(result, key)
        if key in integer_fields and type(val) is not int:
            raise ValueError(f"{key} doit être un nombre entier de minutes ou un effectif entier.")
        if key in bool_fields and type(val) is not bool:
            raise ValueError(f"{key} doit être vrai ou faux.")
        if key in {"id", "name", "educator_id", "group_id", "room_id", "notes", "restrictions", "seniority_date", "color"} and not isinstance(val, str):
            raise ValueError(f"Texte invalide : {key}.")
        if key in {"preferred_groups", "responsible_ids"} and (not isinstance(val, list) or not all(isinstance(x, str) for x in val)):
            raise ValueError(f"Liste invalide : {key}.")
    if cls is Settings:
        if type(result.zoom) not in (int, float) or not math.isfinite(result.zoom) or not 0.25 <= result.zoom <= 4:
            raise ValueError("Le zoom du calendrier doit être un nombre compris entre 0,25 et 4.")
        if result.snap_minutes not in (0, 1, 5, 15):
            raise ValueError("Le magnétisme doit être désactivé ou réglé sur 1, 5 ou 15 minutes.")
    if cls is Break and (not isinstance(result.kind, str) or result.kind not in {"pause", "dinner"}):
        raise ValueError("Choisissez une pause ou un dîner.")
    return result


def from_dict(data: dict[str, Any]) -> Week:
    if not isinstance(data, dict):
        raise ValueError("La semaine doit être un objet.")
    raw = dict(data)
    try:
        monday = date.fromisoformat(raw["monday"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Date de semaine invalide.") from exc
    if monday.weekday() != 0:
        raise ValueError("La semaine doit commencer un lundi.")
    planning_date = raw.get("planning_date", "")
    if planning_date:
        try:
            selected = date.fromisoformat(planning_date)
        except (TypeError, ValueError) as exc:
            raise ValueError("Date de journée invalide.") from exc
        if selected - timedelta(days=selected.weekday()) != monday:
            raise ValueError("La date de la journée ne correspond pas à son calendrier.")
    elif not isinstance(planning_date, str):
        raise ValueError("Date de journée invalide.")
    converters = {
        "educators": (Educator, {"availability": Window, "absences": Window}),
        "groups": (Group, {"periods": GroupPeriod}),
        "rooms": (Room, {"availability": Window}),
        "shifts": (Shift, {"breaks": Break}),
        "activities": (Activity, {}),
    }
    for key, (cls, children) in converters.items():
        entries = raw.get(key, [])
        if not isinstance(entries, list):
            raise ValueError(f"La liste {key} est invalide.")
        raw[key] = [_construct(cls, x, children) for x in entries]
    raw["settings"] = _construct(Settings, raw.get("settings", {}))
    names = raw.get("day_names", {})
    if not isinstance(names, dict):
        raise ValueError("Les noms des journées sont invalides.")
    canonical_names = {}
    for key, value in names.items():
        if not ((type(key) is int and 0 <= key < 5) or (type(key) is str and key in {"0", "1", "2", "3", "4"})):
            raise ValueError("Journée invalide : utilisez un indice entier de 0 à 4.")
        day = int(key)
        if day in canonical_names:
            raise ValueError("Le nom d'une journée est défini deux fois.")
        canonical_names[day] = value
    raw["day_names"] = canonical_names
    if any(k not in range(5) or not isinstance(v, str) or len(v) > 160 for k, v in raw["day_names"].items()):
        raise ValueError("Le nom d'une journée doit contenir au plus 160 caractères.")
    if raw.get("status", "draft") not in STATUSES:
        raise ValueError("Statut de semaine invalide.")
    unknown = set(raw) - set(Week.__dataclass_fields__)
    if unknown:
        raise ValueError("Format de semaine inconnu.")
    if planning_date:
        periods = [p for g in raw['groups'] for p in g.periods]
        periods += [p for e in raw['educators'] for p in e.availability + e.absences]
        periods += [p for r in raw['rooms'] for p in r.availability]
        if any(p.day != 0 for p in periods + raw['shifts'] + raw['activities']) or any(k != 0 for k in raw['day_names']):
            raise ValueError("Cet horaire doit contenir uniquement la journée choisie.")
    return Week(**raw)


def merge_intervals(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for start, end in sorted(intervals):
        if start >= end:
            continue
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def subtract_intervals(start: int, end: int, removed: list[tuple[int, int]]) -> list[tuple[int, int]]:
    cursor, result = start, []
    for a, b in merge_intervals(removed):
        a, b = max(start, a), min(end, b)
        if a >= b:
            continue
        if cursor < a:
            result.append((cursor, a))
        cursor = max(cursor, b)
    if cursor < end:
        result.append((cursor, end))
    return result


def coverage_intervals(shift: Shift) -> list[tuple[int, int]]:
    return subtract_intervals(shift.coverage_start, shift.coverage_end, [(b.start, b.end) for b in shift.breaks])


def working_intervals(shift: Shift) -> list[tuple[int, int]]:
    return subtract_intervals(shift.start, shift.end, [(b.start, b.end) for b in shift.breaks])


def presence_minutes(shift: Shift) -> int:
    return max(0, shift.end - shift.start)


def paid_minutes(shift: Shift) -> int:
    unpaid = [(b.start, b.end) for b in shift.breaks if not b.paid]
    if not shift.before_paid:
        unpaid.append((shift.start, shift.start + shift.buffer_before))
    if not shift.after_paid:
        unpaid.append((shift.end - shift.buffer_after, shift.end))
    return sum(b - a for a, b in subtract_intervals(shift.start, shift.end, unpaid))


def totals(week: Week) -> dict[str, int]:
    result = {e.id: 0 for e in week.educators}
    for s in week.shifts:
        result[s.educator_id] = result.get(s.educator_id, 0) + paid_minutes(s)
    return result


def move_shift(shift: Shift, day: int, start: int, group_id: str | None = None) -> Shift:
    """Retourne un quart déplacé, en conservant ses durées et pauses relatives."""
    result = copy.deepcopy(shift)
    delta = start - shift.start
    result.day, result.start, result.end = day, start, shift.end + delta
    if group_id is not None:
        result.group_id = group_id
    for pause in result.breaks:
        pause.start += delta
        pause.end += delta
    return result


def required_educators(group: Group, students: int) -> int:
    return max(2, group.min_educators, (students + max(1, group.ratio) - 1) // max(1, group.ratio))
