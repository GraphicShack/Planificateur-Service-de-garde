"""Calendrier graphique à la minute, sans mutation directe des données métier.

Les mouvements sont des propositions émises par ``change_requested``. Le
contrôleur peut ainsi les enregistrer, les annuler et revalider l'horaire.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta, datetime
import math
from typing import Any

from PySide6.QtCore import Qt, QRectF, QSize, Signal, QPointF, QTimer, QEvent
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QWidget, QScrollArea, QGridLayout, QLabel, QMenu, QToolTip,
)

from ..models import format_time, format_duration
from .coverage_band import CoverageBand

DAYS = ("Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi")
EDUCATOR_MIME = "application/x-gardeplan-educator"


def _color(value: str, fallback: str = "#427b69") -> QColor:
    c = QColor(value)
    return c if c.isValid() else QColor(fallback)


def _light(value: QColor, opacity: float = .13) -> QColor:
    return QColor(*(round(255 * (1 - opacity) + component * opacity)
                    for component in (value.red(), value.green(), value.blue())))


def _font(size: float, weight=QFont.Weight.Normal) -> QFont:
    font = QFont("Segoe UI")
    font.setPointSizeF(size)
    font.setWeight(weight)
    return font


def _day_name(week: Any, day: int) -> str:
    names = getattr(week, "day_names", {})
    return str(names.get(str(day), names.get(day, "")))


@dataclass
class _Block:
    kind: str
    value: Any
    rect: QRectF
    column: int
    lane: int = 0
    lane_count: int = 1


class _Gutter(QWidget):
    def __init__(self, calendar: "CalendarWidget"):
        super().__init__()
        self.calendar = calendar
        self.setFixedWidth(65)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#fafbf8"))
        painter.setFont(_font(8.5))
        c = self.calendar
        offset = c.scroll.verticalScrollBar().value()
        for minute in range((c.start_minute+29)//30*30, c.end_minute+1, 30):
            y = (minute - c.start_minute) * c.scale - offset
            if -10 <= y <= self.height() + 10:
                if minute % 60 == 0:
                    if c.scale < .4 and minute % 120:
                        continue
                    painter.setPen(QColor("#69766e"))
                    painter.drawText(QRectF(0, y + 3, 58, 20), Qt.AlignmentFlag.AlignRight,
                                     f"{minute // 60:02d}:00")
                elif c.scale >= 1:
                    painter.setPen(QColor("#a6afa7"))
                    painter.drawText(QRectF(0, y + 3, 58, 18), Qt.AlignmentFlag.AlignRight, "30")
        painter.setPen(QColor("#e5eae3"))
        painter.drawLine(self.width() - 1, 0, self.width() - 1, self.height())


class _Header(QWidget):
    def __init__(self, calendar: "CalendarWidget"):
        super().__init__()
        self.calendar = calendar
        self.setFixedHeight(66)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)
        self.hover_column = -1

    def paintEvent(self, event):
        c = self.calendar
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#ffffff"))
        for i, (title, subtitle, color) in enumerate(c.columns()):
            x = i * c.column_width
            accent = _color(color)
            is_week = c.mode == "Semaine"
            active = is_week and i == c.day
            if is_week:
                p.setPen(QPen(QColor("#d5e4da") if active else QColor("#edf0e9"), 1))
                p.setBrush(QColor("#eef5ef") if active else QColor("#f7f9f5")
                           if i == self.hover_column else QColor("#ffffff"))
                p.drawRoundedRect(QRectF(x + 7, 6, c.column_width - 14, 53), 10, 10)
                text_x = x + 20
                text_width = c.column_width - 40
            else:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(_light(accent, .12))
                p.drawRoundedRect(QRectF(x + 14, 15, 32, 32), 9, 9)
                p.setPen(accent.darker(125))
                p.setFont(_font(9.5, QFont.Weight.DemiBold))
                parts = title.split()
                initial = parts[1][:2] if len(parts) > 1 and parts[0].lower() == "groupe" else title[:1]
                p.drawText(QRectF(x + 14, 15, 32, 32), Qt.AlignmentFlag.AlignCenter, initial)
                text_x = x + 56
                text_width = c.column_width - 68
            p.setPen(QColor("#234332") if active else QColor("#2f4035"))
            p.setFont(_font(10, QFont.Weight.DemiBold))
            text = p.fontMetrics().elidedText(title, Qt.TextElideMode.ElideRight, int(text_width))
            p.drawText(QRectF(text_x, 11, text_width, 23), Qt.AlignmentFlag.AlignVCenter, text)
            p.setFont(_font(8))
            p.setPen(QColor("#7a897b"))
            text = p.fontMetrics().elidedText(subtitle, Qt.TextElideMode.ElideRight, int(text_width))
            p.drawText(QRectF(text_x, 34, text_width, 19), Qt.AlignmentFlag.AlignVCenter, text)
        p.setPen(QColor("#e5eae3"))
        p.drawLine(0, self.height() - 1, self.width(), self.height() - 1)

    def mouseMoveEvent(self, event):
        column = int(event.position().x() // self.calendar.column_width)
        if column != self.hover_column:
            self.hover_column = column
            self.update()
        columns = self.calendar.columns()
        if 0 <= column < len(columns):
            title, subtitle, _ = columns[column]
            self.setToolTip(f"{title}\n{subtitle}")

    def leaveEvent(self, event):
        self.hover_column = -1
        self.update()
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.calendar.mode == "Semaine" and event.button() == Qt.MouseButton.LeftButton:
            day = int(event.position().x() // self.calendar.column_width)
            if 0 <= day < 5:
                self.calendar.day_selected.emit(day)


class _Canvas(QWidget):
    def __init__(self, calendar: "CalendarWidget"):
        super().__init__()
        self.calendar = calendar
        self.blocks: list[_Block] = []
        self.drag: dict | None = None
        self.selection: tuple[str, str] | None = None
        self.hover: tuple[str, str] | None = None
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName("Calendrier des affectations et activités")
        self.setAccessibleDescription(
            "Glissez une éducatrice dans un groupe. Déplacez un bloc ou tirez son bord. "
            "Double-cliquez pour saisir les heures exactes. Les flèches déplacent le bloc sélectionné.")

    def sizeHint(self):
        c = self.calendar
        return QSize(int(c.column_width * max(1, len(c.columns()))),
                     int((c.end_minute - c.start_minute) * c.scale))

    def rebuild(self):
        c = self.calendar
        self.blocks = []
        if not c.week:
            return
        for column in range(len(c.columns())):
            day = column if c.mode == "Semaine" else c.day
            group_id = None if c.mode == "Semaine" else c.week.groups[column].id
            shifts = [s for s in c.week.shifts if s.day == day and
                      (group_id is None or s.group_id == group_id)]
            activities = [a for a in c.week.activities if c.show_activities and a.day == day and
                          (group_id is None or a.group_id == group_id)]
            left = column * c.column_width + 8
            available = c.column_width - 16
            activity_width = max(75, available * .30) if activities else 0
            work_width = available - activity_width - (5 if activities else 0)
            lane_ends: list[int] = []
            assigned = []
            for s in sorted(shifts, key=lambda s: (s.start, s.end, s.id)):
                lane = next((i for i, end in enumerate(lane_ends) if end <= s.start), len(lane_ends))
                if lane == len(lane_ends):
                    lane_ends.append(s.end)
                else:
                    lane_ends[lane] = s.end
                assigned.append((s, lane))
            lane_count = max(1, len(lane_ends))
            for s, lane in assigned:
                width = work_width / lane_count
                rect = QRectF(left + lane * width, c.y(s.start) + 1,
                              max(8, width - 4), max(2, (s.end - s.start) * c.scale - 2))
                self.blocks.append(_Block("shift", s, rect, column, lane, lane_count))
            # Activities occupy independent lanes, distinct from educator work.
            activity_ends: list[int] = []
            assignments = []
            for activity in sorted(activities, key=lambda a: (a.start, a.end, a.id)):
                lane = next((i for i, end in enumerate(activity_ends) if end <= activity.start),
                            len(activity_ends))
                if lane == len(activity_ends):
                    activity_ends.append(activity.end)
                else:
                    activity_ends[lane] = activity.end
                assignments.append((activity, lane))
            count = max(1, len(activity_ends))
            for activity, lane in assignments:
                width = activity_width / count
                rect = QRectF(left + work_width + 5 + lane * width, c.y(activity.start) + 1,
                              max(8, width - 4), max(2, (activity.end - activity.start) * c.scale - 2))
                self.blocks.append(_Block("activity", activity, rect, column, lane, count))
        self.update()

    def _rect(self, block):
        if self.drag and self.drag["block"] is block:
            c = self.calendar
            rect = QRectF(block.rect)
            rect.translate((self.drag["column"] - block.column) * c.column_width, 0)
            rect.setTop(c.y(self.drag["start"]) + 1)
            rect.setBottom(c.y(self.drag["end"]) - 1)
            return rect
        return block.rect

    def paintEvent(self, event):
        c = self.calendar
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(event.rect(), QColor("#ffffff"))
        bounds = event.rect()
        n = len(c.columns())
        for i in range(n):
            if c.mode == "Semaine" and i == c.day:
                p.fillRect(QRectF(i * c.column_width, bounds.top(), c.column_width, bounds.height()),
                           QColor("#f8fbf7"))
            elif i % 2:
                p.fillRect(QRectF(i * c.column_width, bounds.top(), c.column_width, bounds.height()),
                           QColor("#fdfefb"))
        # Closed periods are subdued, leaving open periods clearly identifiable.
        if c.week and c.mode == "Jour":
            for index, group in enumerate(c.week.groups):
                p.fillRect(QRectF(index*c.column_width, bounds.top(), c.column_width, bounds.height()),
                           QColor("#f4f6f1"))
                for period in group.periods:
                    if period.day == c.day:
                        p.fillRect(QRectF(index*c.column_width, c.y(period.start), c.column_width,
                                        (period.end-period.start)*c.scale), QColor("#ffffff"))
        # Error bands remain visible even when there is no work block.
        if c.week:
            for issue in c.issues:
                if getattr(issue, "severity", "") != "error":
                    continue
                day = getattr(issue, "day", None)
                start, end = getattr(issue, "start", None), getattr(issue, "end", None)
                if day is None or start is None or end is None or end <= start:
                    continue
                if c.mode == "Semaine":
                    columns = [day] if 0 <= day < 5 else []
                elif day == c.day:
                    group_id = getattr(issue, "group_id", "")
                    columns = [i for i,g in enumerate(c.week.groups) if not group_id or g.id == group_id]
                else:
                    columns = []
                for i in columns:
                    rect = QRectF(i*c.column_width, c.y(start), c.column_width, (end-start)*c.scale)
                    p.fillRect(rect, QColor(191, 81, 74, 13))
                    p.fillRect(QRectF(rect.left(), rect.top(), 2, rect.height()), QColor("#c56a60"))
        first = max(c.start_minute, int(bounds.top()/c.scale+c.start_minute)//30*30)
        last = min(c.end_minute, int(bounds.bottom()/c.scale+c.start_minute)+30)
        for minute in range(first, last+1, 30):
            if c.scale < .5 and minute % 60:
                continue
            p.setPen(QPen(QColor("#e6ebe3") if minute % 60 == 0 else QColor("#f3f5ef"), 1))
            p.drawLine(QPointF(0, c.y(minute)), QPointF(self.width(), c.y(minute)))
        p.setPen(QColor("#e7ece4"))
        for i in range(n + 1):
            p.drawLine(QPointF(i*c.column_width, bounds.top()),
                       QPointF(i*c.column_width, bounds.bottom()))
        educators = {e.id:e for e in c.week.educators} if c.week else {}
        groups = {g.id:g for g in c.week.groups} if c.week else {}
        rooms = {r.id:r for r in c.week.rooms} if c.week else {}
        error_ids = {sid for issue in c.issues if getattr(issue, "severity", "") == "error"
                     for sid in getattr(issue, "shift_ids", [])}
        for block in self.blocks:
            rect = self._rect(block)
            if not rect.intersects(QRectF(bounds)):
                continue
            value = block.value
            educator = educators.get(getattr(value, "educator_id", ""))
            group = groups.get(value.group_id)
            color = _color(group.color if group else (educator.color if educator else "#667b9d"))
            is_activity = block.kind == "activity"
            border = QColor("#c56a60") if value.id in error_ids else _light(color, .28)
            selected = self.selection == (block.kind, value.id)
            hovered = self.hover == (block.kind, value.id)
            moving = bool(self.drag and self.drag["block"] is block)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(31, 54, 39, 8 if hovered or moving else 4))
            p.drawRoundedRect(rect.translated(0, 2), 8, 8)
            p.setPen(QPen(QColor("#38644a") if selected else border, 1.7 if selected else 1,
                          Qt.PenStyle.DashLine if is_activity else Qt.PenStyle.SolidLine))
            p.setBrush(_light(color, .10 if is_activity else .18 if hovered or moving else .12))
            p.drawRoundedRect(rect, 8, 8)
            p.save()
            p.setClipRect(rect.adjusted(1, 1, -1, -1))
            if not is_activity:
                p.fillRect(QRectF(rect.left()+1, rect.top()+1, rect.width()-2, 3), _light(color,.75))
                # Buffers and breaks are presence, never ordinary pupil coverage.
                start, end = (self.drag["start"], self.drag["end"]) if self.drag and self.drag["block"] is block else (value.start, value.end)
                if value.buffer_before:
                    p.fillRect(QRectF(rect.left(), c.y(start), rect.width(), value.buffer_before*c.scale),
                               _light(color,.23))
                    p.setPen(QPen(_light(color,.38), 1, Qt.PenStyle.DotLine))
                    y = c.y(start+value.buffer_before)
                    p.drawLine(QPointF(rect.left(),y),QPointF(rect.right(),y))
                if value.buffer_after:
                    p.fillRect(QRectF(rect.left(), c.y(end-value.buffer_after), rect.width(), value.buffer_after*c.scale),
                               _light(color,.23))
                    p.setPen(QPen(_light(color,.38), 1, Qt.PenStyle.DotLine))
                    y = c.y(end-value.buffer_after)
                    p.drawLine(QPointF(rect.left(),y),QPointF(rect.right(),y))
                delta = start - value.start
                for pause in value.breaks:
                    pause_rect = QRectF(rect.left(),c.y(pause.start+delta),rect.width(),
                                        (pause.end-pause.start)*c.scale)
                    p.fillRect(pause_rect, QColor("#e7ebe4"))
                    p.setPen(QPen(QColor("#cbd4c8"), 1, Qt.PenStyle.DotLine))
                    p.drawLine(pause_rect.topLeft(),pause_rect.topRight())
                    p.drawLine(pause_rect.bottomLeft(),pause_rect.bottomRight())
                    if pause_rect.height() >= 19:
                        p.setPen(QColor("#74806e"))
                        p.setFont(_font(7.5))
                        p.drawText(pause_rect.adjusted(9,0,-5,0),Qt.AlignmentFlag.AlignVCenter,"Pause")
            tall = not is_activity and rect.height() >= 128 and rect.width() >= 90
            content_offset = 43 if tall else 0
            if tall:
                avatar = QRectF(rect.left()+11, rect.top()+15, 26, 26)
                p.setPen(Qt.PenStyle.NoPen)
                identity_color = _color(educator.color) if educator else color
                p.setBrush(_light(identity_color, .16))
                p.drawEllipse(avatar)
                p.setPen(identity_color.darker(120))
                p.setFont(_font(7.5, QFont.Weight.DemiBold))
                initials = "".join(word[0].upper() for word in educator.name.split()[:2]) if educator else "?"
                p.drawText(avatar, Qt.AlignmentFlag.AlignCenter, initials)
            p.setPen(color.darker(150))
            compact = rect.width() < 70
            padding = 4 if compact else 10
            p.setFont(_font(7.5 if compact else 9 if rect.width() >= 120 else 8.5,
                            QFont.Weight.DemiBold))
            title = value.name if is_activity else (educator.name if educator else "Éducatrice manquante")
            if compact:
                title="".join(word[:1].upper() for word in title.replace("—"," ").split()[:3])
            if getattr(value, "locked", False):
                title = "· " + title
            text_width=max(0,int(rect.width()-padding-5))
            title=p.fontMetrics().elidedText(title,Qt.TextElideMode.ElideRight,text_width)
            p.drawText(QRectF(rect.left()+padding,rect.top()+9+content_offset,text_width,20),
                       Qt.AlignmentFlag.AlignVCenter,title)
            if rect.height() >= 44:
                p.setFont(_font(6.5 if compact else 8))
                p.setPen(color.darker(125))
                start = self.drag["start"] if self.drag and self.drag["block"] is block else value.start
                end = self.drag["end"] if self.drag and self.drag["block"] is block else value.end
                time_range=f"{format_time(start)} – {format_time(end)}"
                if compact:
                    subtitle=f"{start//60}:{start%60:02d}\n{end//60}:{end%60:02d}"
                    line_count=2
                    # Preserve every digit in narrow weekly lanes. The full
                    # French range and names remain available in the tooltip.
                    padding=2
                    text_width=max(0,int(rect.width()-4))
                    required=max(p.fontMetrics().horizontalAdvance(line) for line in subtitle.splitlines())
                    if required>text_width and required:
                        p.setFont(_font(max(5.5,6.5*text_width/required)))
                elif p.fontMetrics().horizontalAdvance(time_range) <= text_width:
                    subtitle=time_range
                    line_count=1
                else:
                    subtitle=f"{format_time(start)}\n{format_time(end)}"
                    line_count=2
                if c.mode == "Semaine" and group and not compact:
                    subtitle += "\n" + p.fontMetrics().elidedText(group.name,Qt.TextElideMode.ElideRight,text_width)
                    line_count+=1
                if is_activity:
                    room = rooms.get(value.room_id)
                    label=room.name if room else "Sans lieu"
                    subtitle += "\n" + p.fontMetrics().elidedText(label,Qt.TextElideMode.ElideRight,text_width)
                    line_count+=1
                p.drawText(QRectF(rect.left()+padding,rect.top()+32+content_offset,text_width,min(rect.height()-36-content_offset,line_count*18)),
                           Qt.AlignmentFlag.AlignTop,subtitle)
            p.restore()
            if (not getattr(value,"locked",False) and not c.read_only and c.mode=="Jour"
                    and rect.height()>17 and (hovered or selected or moving)):
                p.setPen(QPen(_light(color,.52),1.5))
                center = rect.center().x()
                half = min(11, rect.width()/5)
                for y in (rect.top()+4, rect.bottom()-4):
                    p.drawLine(QPointF(center-half, y), QPointF(center+half, y))
        if not n:
            p.setPen(QColor("#324a37"))
            p.setFont(_font(12,QFont.Weight.DemiBold))
            p.drawText(QRectF(30,55,self.width()-60,50),Qt.TextFlag.TextWordWrap,
                       "Votre calendrier commence ici")
            p.setFont(_font(9.5))
            p.setPen(QColor("#83907e"))
            p.drawText(QRectF(30,108,self.width()-60,90),Qt.TextFlag.TextWordWrap,
                       "Créez vos groupes avec Inscriptions, puis glissez une éducatrice dans le calendrier.")
        if c.highlighted_interval and c.highlighted_interval[0] == c.day:
            _, start, end = c.highlighted_interval
            area = QRectF(2, c.y(start), self.width()-4, max(3, (end-start)*c.scale))
            p.fillRect(area, QColor(33, 79, 64, 22))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor("#173F32"), 2, Qt.PenStyle.DashLine))
            p.drawRect(area)

    def _hit(self, pos):
        return next((b for b in reversed(self.blocks) if b.rect.contains(pos)), None)

    def _tip(self, block):
        c, value = self.calendar, block.value
        group=next((g for g in c.week.groups if g.id==value.group_id),None)
        group_name=group.name if group else "Groupe manquant"
        if block.kind == "activity":
            room = next((r for r in c.week.rooms if r.id == value.room_id), None)
            return (f"{value.name}\n{group_name}\n{format_time(value.start)} à {format_time(value.end)}"
                    f"\n{room.name if room else 'Aucun lieu'}\n{value.notes}")
        educator = next((e for e in c.week.educators if e.id == value.educator_id), None)
        return (f"{educator.name if educator else 'Éducatrice'}\n{group_name}\n"
                f"Présence : {format_time(value.start)} à {format_time(value.end)}\n"
                f"Couverture : {format_time(value.start+value.buffer_before)} à "
                f"{format_time(value.end-value.buffer_after)} (hors pauses)\n"
                f"Préparation : {value.buffer_before} min · Fermeture : {value.buffer_after} min\n"
                + ("Quart verrouillé" if value.locked else "Double-clic : modifier les heures"))

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return super().mousePressEvent(event)
        block = self._hit(event.position())
        self.selection = (block.kind, block.value.id) if block else None
        self.setFocus()
        self.update()
        if (not block or self.calendar.mode != "Jour" or self.calendar.read_only
                or getattr(block.value, "locked", False)):
            return
        rect = block.rect
        action = "move"
        if event.position().y() - rect.top() <= 7:
            action = "start"
        elif rect.bottom() - event.position().y() <= 7:
            action = "end"
        self.drag = dict(block=block, action=action, press=event.position(),
                         start=block.value.start, end=block.value.end, column=block.column)
        self.setCursor(Qt.CursorShape.SizeVerCursor if action != "move" else Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        c = self.calendar
        if self.drag:
            drag, block = self.drag, self.drag["block"]
            delta = (event.position().y() - drag["press"].y()) / c.scale
            start, end = block.value.start, block.value.end
            if drag["action"] == "move":
                proposed = c.snap(start + delta)
                proposed = max(0, min(1440-(end-start), proposed))
                drag["start"], drag["end"] = proposed, proposed+(end-start)
                drag["column"] = max(0, min(len(c.columns())-1,
                                           int(event.position().x()//c.column_width)))
            elif drag["action"] == "start":
                drag["start"] = max(0, min(end-1, c.snap(start + delta)))
            else:
                drag["end"] = min(1440, max(start+1, c.snap(end + delta)))
            QToolTip.showText(event.globalPosition().toPoint(),
                             f"{format_time(drag['start'])} à {format_time(drag['end'])}"
                             f"  ·  {format_duration(drag['end']-drag['start'])}", self)
            self.update()
            return
        block = self._hit(event.position())
        hover=(block.kind,block.value.id) if block else None
        if hover != self.hover:
            self.hover=hover
            self.update()
        if block:
            self.setToolTip(self._tip(block))
            edge = (event.position().y()-block.rect.top() <= 7 or
                    block.rect.bottom()-event.position().y() <= 7)
            self.setCursor(Qt.CursorShape.SizeVerCursor if edge and not self.calendar.read_only and not getattr(block.value,"locked",False)
                           and c.mode == "Jour" else Qt.CursorShape.OpenHandCursor
                           if c.mode == "Jour" and not self.calendar.read_only and not getattr(block.value,"locked",False)
                           else Qt.CursorShape.PointingHandCursor)
        else:
            self.setToolTip("")
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def leaveEvent(self, event):
        self.hover=None
        self.update()
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event):
        if not self.drag:
            return
        drag, self.drag = self.drag, None
        self.setCursor(Qt.CursorShape.ArrowCursor)
        QToolTip.hideText()
        block = drag["block"]
        c = self.calendar
        if (drag["start"],drag["end"],drag["column"]) != (block.value.start,block.value.end,block.column):
            group_id = c.week.groups[drag["column"]].id
            c.change_requested.emit(block.kind, block.value.id, c.day,
                                    drag["start"], drag["end"], group_id)
        self.update()

    def mouseDoubleClickEvent(self, event):
        self.drag = None
        c = self.calendar
        if c.mode == "Semaine":
            day = int(event.position().x()//c.column_width)
            if 0 <= day < 5:
                c.day_selected.emit(day)
            return
        block = self._hit(event.position())
        if block:
            c.edit_requested.emit(block.kind, block.value.id)
        elif c.week and c.week.groups and not c.read_only:
            column = min(len(c.week.groups)-1, max(0, int(event.position().x()//c.column_width)))
            c.create_requested.emit(c.day, c.minute(event.position().y()), c.week.groups[column].id)

    def contextMenuEvent(self, event):
        c = self.calendar
        if c.mode == "Semaine":
            return
        block = self._hit(QPointF(event.pos()))
        menu = QMenu(self)
        if block:
            action = menu.addAction("Modifier…")
            if menu.exec(event.globalPos()) == action:
                c.edit_requested.emit(block.kind,block.value.id)
        elif c.week and c.week.groups and not c.read_only:
            action = menu.addAction("Ajouter un bloc ici…")
            if menu.exec(event.globalPos()) == action:
                col = min(len(c.week.groups)-1,max(0,int(event.pos().x()//c.column_width)))
                c.create_requested.emit(c.day,c.minute(event.pos().y()),c.week.groups[col].id)

    def keyPressEvent(self, event):
        c = self.calendar
        block = next((b for b in self.blocks if self.selection == (b.kind,b.value.id)),None)
        if not block or c.mode != "Jour":
            return super().keyPressEvent(event)
        if event.key() in (Qt.Key.Key_Return,Qt.Key.Key_Enter):
            c.edit_requested.emit(block.kind,block.value.id)
            return
        if c.read_only or getattr(block.value,"locked",False):
            return
        step = c.snap_minutes or 1
        start,end,col = block.value.start,block.value.end,block.column
        if event.key() == Qt.Key.Key_Up:
            start,end = start-step,end-step
        elif event.key() == Qt.Key.Key_Down:
            start,end = start+step,end+step
        elif event.key() == Qt.Key.Key_Left:
            col -= 1
        elif event.key() == Qt.Key.Key_Right:
            col += 1
        else:
            return super().keyPressEvent(event)
        if 0 <= start < end <= 1440 and 0 <= col < len(c.week.groups):
            c.change_requested.emit(block.kind,block.value.id,c.day,start,end,c.week.groups[col].id)

    def dragEnterEvent(self, event):
        c = self.calendar
        if not c.read_only and c.mode == "Jour" and c.week and c.week.groups and (
                event.mimeData().hasFormat(EDUCATOR_MIME) or event.mimeData().hasText()):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        self.dragEnterEvent(event)

    def dropEvent(self, event):
        c = self.calendar
        if c.read_only or not c.week or not c.week.groups or c.mode != "Jour":
            return
        data = event.mimeData()
        educator_id = (bytes(data.data(EDUCATOR_MIME)).decode("utf-8")
                       if data.hasFormat(EDUCATOR_MIME) else data.text()).strip()
        if not any(e.id == educator_id and e.active for e in c.week.educators):
            return
        column = max(0,min(len(c.week.groups)-1,int(event.position().x()//c.column_width)))
        c.educator_dropped.emit(educator_id,c.day,c.minute(event.position().y()),c.week.groups[column].id)
        event.acceptProposedAction()


class CalendarWidget(QWidget):
    """Daily editor and weekly overview with frozen headers and time gutter."""
    edit_requested = Signal(str,str)
    change_requested = Signal(str,str,int,int,int,str)
    educator_dropped = Signal(str,int,int,str)
    day_selected = Signal(int)
    create_requested = Signal(int,int,str)

    def __init__(self,parent=None):
        super().__init__(parent)
        self.week = None
        self.show_activities = True
        self.day = 0
        self.mode = "Jour"
        self.read_only = False
        self.issues = []
        self.highlighted_interval = None
        self.snap_minutes = 1
        self.scale = 1.65
        self.start_minute,self.end_minute = 360,1140
        self.column_width = 265
        self.setMinimumSize(330,250)
        layout = QGridLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)
        corner = QLabel("HEURES")
        corner.setFixedSize(65,66)
        corner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        corner.setStyleSheet("background:#fafbf8;color:#96a18f;font-size:9px;font-weight:600;"
                             "border-bottom:1px solid #e5eae3;")
        self.header = _Header(self)
        self.header_scroll = QScrollArea()
        self.header_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.header_scroll.setWidget(self.header)
        self.header_scroll.setFixedHeight(66)
        self.header_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.header_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll = QScrollArea()
        self.scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.scroll.setWidgetResizable(False)
        self.canvas = _Canvas(self)
        self.scroll.setWidget(self.canvas)
        self.gutter = _Gutter(self)
        self.coverage_band = CoverageBand()
        self.coverage_band.interval_selected.connect(lambda a, b: self.highlight_interval(self.day, a, b))
        layout.addWidget(corner,0,0)
        layout.addWidget(self.header_scroll,0,1)
        layout.addWidget(self.coverage_band,1,0,1,2)
        layout.addWidget(self.gutter,2,0)
        layout.addWidget(self.scroll,2,1)
        layout.setRowStretch(2,1)
        layout.setColumnStretch(1,1)
        self.scroll.verticalScrollBar().valueChanged.connect(lambda _: self.gutter.update())
        self.scroll.horizontalScrollBar().valueChanged.connect(self.header_scroll.horizontalScrollBar().setValue)
        self._layout_timer=QTimer(self)
        self._layout_timer.setSingleShot(True)
        self._layout_timer.timeout.connect(self._layout_calendar)
        self.scroll.viewport().installEventFilter(self)
        self.setStyleSheet("""
            QScrollArea {background:#ffffff;border:0;}
            QScrollBar:vertical {background:#f6f8f3;width:10px;margin:2px;}
            QScrollBar:horizontal {background:#f6f8f3;height:10px;margin:2px;}
            QScrollBar::handle:vertical {background:#cbd6c8;border-radius:3px;min-height:40px;}
            QScrollBar::handle:horizontal {background:#cbd6c8;border-radius:3px;min-width:40px;}
            QScrollBar::handle:hover {background:#a7b9a2;}
            QScrollBar::add-line,QScrollBar::sub-line {width:0;height:0;}
            QScrollBar::add-page,QScrollBar::sub-page {background:transparent;}
        """)

    def columns(self):
        if not self.week:
            return []
        if self.mode == "Semaine":
            result=[]
            monday=date.fromisoformat(self.week.monday)
            for day in range(5):
                d=monday+timedelta(days=day)
                title=f"{DAYS[day]} {d.day:02d}/{d.month:02d}"
                subtitle=_day_name(self.week,day) or "Cliquer pour ouvrir la journée"
                result.append((title,subtitle,"#477d6c" if day==self.day else "#90a4b7"))
            return result
        result = []
        for group in self.week.groups:
            people = {s.educator_id for s in self.week.shifts if s.group_id == group.id and s.day == self.day}
            students = max((p.students for p in group.periods if p.day == self.day), default=0)
            result.append((group.name, f"{len(people)} éducatrices · {students} enfants", group.color))
        return result

    def y(self,minute):
        return (minute-self.start_minute)*self.scale

    def snap(self,minute):
        step=self.snap_minutes or 1
        return int(math.floor(minute/step+.5)*step)

    def minute(self,y):
        return min(1439,max(0,self.snap(y/self.scale+self.start_minute)))

    def set_week(self,week,day=0,issues=None):
        changed_day = self.week is None or self.week.storage_key != week.storage_key or self.day != day
        self.week=week
        self.day=max(0,min(4,int(day)))
        self.issues=list(issues or [])
        self.coverage_band.set_week(week, self.day)
        self.canvas.drag=None
        starts=[s.start for s in week.shifts]+([a.start for a in week.activities] if self.show_activities else [])
        ends=[s.end for s in week.shifts]+([a.end for a in week.activities] if self.show_activities else [])
        opening = week.settings.open_minute-week.settings.opening_buffer
        closing = week.settings.close_minute+week.settings.closing_buffer
        self.start_minute=max(0,min([opening]+starts)//60*60)
        self.end_minute=min(1440,(max([closing]+ends)+59)//60*60)
        self._layout_calendar()
        if changed_day:
            self.highlighted_interval = None
            self.scroll.verticalScrollBar().setValue(0)

    def set_mode(self,mode):
        self.mode="Semaine" if mode=="Semaine" and not getattr(self.week, "planning_date", "") else "Jour"
        self.canvas.drag=None
        self._layout_calendar()

    def set_read_only(self,read_only):
        """Keep navigation and inspection available while suppressing mutations."""
        self.read_only=bool(read_only)
        self.canvas.drag=None
        self.canvas.update()

    def set_snap(self,minutes):
        if minutes not in (0,1,5,15):
            raise ValueError("Le magnétisme doit être de 0, 1, 5 ou 15 minutes.")
        self.snap_minutes=minutes

    def set_zoom(self,zoom):
        old_scale=self.scale
        anchor=self.scroll.verticalScrollBar().value()/old_scale
        self.scale=max(.25,min(4.5,1.65*float(zoom)))
        self._layout_calendar()
        self.scroll.verticalScrollBar().setValue(int(anchor*self.scale))

    def scroll_to(self,minute):
        self.scroll.verticalScrollBar().setValue(int(self.y(minute)))

    def highlight_interval(self, day, start, end):
        self.highlighted_interval = (day, start, end)
        self.scroll_to(max(self.start_minute, start-20))
        self.canvas.setAccessibleDescription(f"Plage sélectionnée : {format_time(start)} à {format_time(end)}. Entrée sur un quart pour le modifier.")
        self.canvas.update()

    def _layout_calendar(self):
        n=max(1,len(self.columns()))
        minimum=220 if self.mode=="Semaine" else 225
        self.column_width=max(minimum,self.scroll.viewport().width()/n)
        self.canvas.resize(self.canvas.sizeHint())
        # The header has no vertical scrollbar. Its trailing blank area makes
        # its horizontal scroll range match the body's, even at the far right.
        trailing=max(0,self.header_scroll.viewport().width()-self.scroll.viewport().width())
        self.header.resize(int(self.column_width*n)+trailing,66)
        self.header.update()
        self.canvas.rebuild()
        self.gutter.update()

    def resizeEvent(self,event):
        super().resizeEvent(event)
        self._layout_calendar()
        # The parent resize event precedes layout and scrollbar settlement.
        # Re-evaluate once the viewport has received its final dimensions.
        self._layout_timer.start(0)

    def eventFilter(self,watched,event):
        if watched is self.scroll.viewport() and event.type()==QEvent.Type.Resize:
            self._layout_timer.start(0)
        return super().eventFilter(watched,event)
