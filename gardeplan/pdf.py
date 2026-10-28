"""Monochrome-friendly, fully local PDF exports with exact minute totals."""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import os
import re
import tempfile
from xml.sax.saxutils import escape

import reportlab
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    KeepTogether, LongTable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, TableStyle,
)

from .branding import DISPLAY_NAME
from .models import Week, coverage_intervals, format_duration, format_time, paid_minutes, totals

DAYS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
STATUS = {"draft": "Brouillon", "validated": "Validé", "published": "Publié", "archived": "Archivé"}


class PdfError(Exception):
    pass


def _register_fonts():
    if "GardePlan" not in pdfmetrics.getRegisteredFontNames():
        root = Path(reportlab.__file__).parent / "fonts"
        pdfmetrics.registerFont(TTFont("GardePlan", str(root / "Vera.ttf")))
        pdfmetrics.registerFont(TTFont("GardePlan-Bold", str(root / "VeraBd.ttf")))
        pdfmetrics.registerFontFamily("GardePlan", normal="GardePlan", bold="GardePlan-Bold", italic="GardePlan", boldItalic="GardePlan-Bold")


def _styles():
    _register_fonts()
    base = getSampleStyleSheet()
    result = {}
    for name, size, leading, after in [("title", 21, 26, 8), ("subtitle", 12, 17, 9), ("heading", 13, 18, 8), ("body", 8, 11, 4), ("small", 7, 10, 3)]:
        result[name] = ParagraphStyle(name, parent=base["Normal"], fontName="GardePlan-Bold" if name in {"title", "heading"} else "GardePlan", fontSize=size, leading=leading, spaceAfter=after, textColor=colors.HexColor("#17212c"))
    result["cell"] = ParagraphStyle("cell", parent=result["body"], spaceAfter=0)
    result["headcell"] = ParagraphStyle("headcell", parent=result["cell"], fontName="GardePlan-Bold", textColor=colors.white)
    return result


def _p(value, style):
    return Paragraph(escape(str(value)).replace("\n", "<br/>"), style)


def _table(headers, rows, widths, styles):
    data = [[_p(h, styles["headcell"]) for h in headers]]
    data += [[_p(value, styles["cell"]) for value in row] for row in rows]
    table = LongTable(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#344353")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f3f5")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, 0), .5, colors.black),
        ("LINEBELOW", (0, 1), (-1, -1), .25, colors.HexColor("#d4dae0")),
    ]))
    return table


def _day_label(week, day):
    current = date.fromisoformat(week.planning_date or week.monday) + timedelta(days=day)
    name = week.day_names.get(day, week.day_names.get(str(day), ""))
    return f"{DAYS[current.weekday()]} {current.strftime('%d/%m/%Y')}" + (f" — {name}" if name else "")


def _range(start, end):
    return f"{format_time(start)} – {format_time(end)}"


def _week_title(week):
    if week.planning_date:
        return "Journée pédagogique — " + _day_label(week, 0)
    monday = date.fromisoformat(week.monday)
    friday = monday + timedelta(days=4)
    return f"Semaine du {monday.strftime('%d/%m/%Y')} au {friday.strftime('%d/%m/%Y')}"


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#b5bdc5"))
    canvas.line(doc.leftMargin, 15 * mm, doc.pagesize[0] - doc.rightMargin, 15 * mm)
    canvas.setFont("GardePlan", 7)
    canvas.setFillColor(colors.HexColor("#52606d"))
    canvas.drawString(doc.leftMargin, 10 * mm, f"{DISPLAY_NAME} • Document local • Horaires à la minute")
    canvas.drawRightString(doc.pagesize[0] - doc.rightMargin, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


def _write(path, story, pagesize=A4):
    path = Path(path).expanduser().resolve()
    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".gardeplan-pdf-", suffix=".pdf", dir=path.parent)
        os.close(fd)
        doc = SimpleDocTemplate(temporary, pagesize=pagesize, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=16 * mm, bottomMargin=22 * mm, title="Horaire du service de garde", author=DISPLAY_NAME, allowSplitting=True)
        doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
        os.replace(temporary, path)
        temporary = None
        return path
    except Exception as exc:
        # Preserve an existing PDF if ReportLab or the filesystem fails.
        raise PdfError(f"Le PDF n’a pas pu être créé : {exc}") from exc
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def _coverage_rows(week, day):
    rows = []
    for group in week.groups:
        shifts = [s for s in week.shifts if s.day == day and s.group_id == group.id]
        intervals = [(s.educator_id, a, b) for s in shifts for a, b in coverage_intervals(s)]
        for period in sorted((p for p in group.periods if p.day == day), key=lambda p: p.start):
            ratio = group.ratio if group.ratio > 0 else 20
            required = max(2, group.min_educators, (period.students + ratio - 1) // ratio)
            boundaries = {period.start, period.end}
            for _, a, b in intervals:
                if period.start < a < period.end:
                    boundaries.add(a)
                if period.start < b < period.end:
                    boundaries.add(b)
            points = sorted(boundaries)
            merged = []
            for a, b in zip(points, points[1:]):
                count = len({eid for eid, x, y in intervals if x <= a and y >= b})
                marker = "RATIO INVALIDE" if group.ratio <= 0 else ("OK" if count >= required else "MANQUE")
                if merged and merged[-1][1] == a and merged[-1][2:] == (count, marker):
                    merged[-1] = (merged[-1][0], b, count, marker)
                else:
                    merged.append((a, b, count, marker))
            for a, b, count, marker in merged:
                rows.append([group.name, _range(a, b), str(period.students), f"{count} / {required}", marker])
    return rows


def _general_story(week, styles):
    story = [_p("Horaire général", styles["title"]), _p(_week_title(week), styles["subtitle"]), _p(f"Statut : {STATUS.get(week.status, week.status)} · Ratio configuré par groupe (1 pour 20 par défaut).", styles["body"])]
    educators = {e.id: e for e in week.educators}
    groups = {g.id: g for g in week.groups}
    rooms = {r.id: r for r in week.rooms}
    width = landscape(A4)[0] - 32 * mm
    for day in week.active_days:
        if day != week.active_days[0]:
            story.append(PageBreak())
        story.append(_p(_day_label(week, day), styles["heading"]))
        shifts = sorted((s for s in week.shifts if s.day == day), key=lambda s: (s.start, groups.get(s.group_id).name if s.group_id in groups else "", s.educator_id))
        story.append(_p("Affectations — les buffers et pauses ne couvrent pas les élèves", styles["body"]))
        if shifts:
            rows = []
            for s in shifts:
                educator = educators.get(s.educator_id)
                group = groups.get(s.group_id)
                coverage = "\n".join(_range(a, b) for a, b in coverage_intervals(s)) or "Aucune"
                buffers = f"Avant : {s.buffer_before} min {'payées' if s.before_paid else 'non payées'}\nAprès : {s.buffer_after} min {'payées' if s.after_paid else 'non payées'}"
                pauses = "\n".join(f"{_range(b.start,b.end)} ({'payée' if b.paid else 'non payée'})" for b in s.breaks) or "—"
                rows.append([educator.name if educator else "Éducatrice manquante", group.name if group else "Groupe manquant", _range(s.start, s.end), coverage, buffers, pauses, format_duration(paid_minutes(s))])
            story.append(_table(["Éducatrice", "Groupe", "Présence", "Couverture", "Buffers", "Pauses", "Rémunéré"], rows, [width*f for f in (.16,.11,.14,.16,.14,.17,.12)], styles))
        else:
            story.append(_p("Aucune affectation.", styles["body"]))
        story.append(Spacer(1, 5 * mm))
        activities = sorted((a for a in week.activities if a.day == day), key=lambda a: (a.start, a.name))
        story.append(_p("Activités et lieux", styles["heading"]))
        if activities:
            rows = []
            for a in activities:
                room = rooms.get(a.room_id)
                location = room.name + (" (extérieur)" if room.outdoor else "") if room else "Lieu non défini"
                if a.responsible_ids:
                    responsible = ", ".join(educators[eid].name if eid in educators else "Inconnue" for eid in a.responsible_ids)
                else:
                    responsible = ", ".join(sorted({educators[s.educator_id].name for s in shifts if s.educator_id in educators and s.group_id == a.group_id and any(x < a.end and y > a.start for x, y in coverage_intervals(s))})) or "Aucune"
                rows.append([_range(a.start, a.end), groups[a.group_id].name if a.group_id in groups else "Groupe manquant", a.name, location, responsible, a.notes or "—"])
            story.append(_table(["Horaire", "Groupe", "Activité", "Lieu", "Responsables selon présence", "Notes"], rows, [width*f for f in (.15,.12,.16,.17,.23,.17)], styles))
        else:
            story.append(_p("Aucune activité.", styles["body"]))
        story.append(Spacer(1, 5 * mm))
        story.append(_p("Couverture réelle des groupes", styles["heading"]))
        rows = _coverage_rows(week, day)
        if rows:
            story.append(_table(["Groupe", "Période", "Enfants", "Présentes / requises", "Contrôle"], rows, [width*f for f in (.22,.25,.13,.25,.15)], styles))
        else:
            story.append(_p("Aucun groupe ouvert.", styles["body"]))
    return story


def _individual_story(week, educator_id, styles):
    educator = next((e for e in week.educators if e.id == educator_id), None)
    if educator is None:
        raise PdfError("Cette éducatrice n’existe pas dans la journée choisie.")
    width = A4[0] - 32 * mm
    groups = {g.id: g.name for g in week.groups}
    rooms = {r.id: r for r in week.rooms}
    story = [_p("Horaire individuel", styles["title"]), _p(educator.name, styles["heading"]), _p(_week_title(week), styles["subtitle"])]
    total = totals(week).get(educator_id, 0)
    story.append(_p(f"Statut : {STATUS.get(week.status,week.status)} · Total rémunéré : {format_duration(total)} · Cible : {format_duration(educator.target_minutes)}", styles["body"]))
    story.append(Spacer(1, 4 * mm))
    for day in week.active_days:
        story.append(_p(_day_label(week, day), styles["heading"]))
        shifts = sorted((s for s in week.shifts if s.educator_id == educator_id and s.day == day), key=lambda s: s.start)
        if not shifts:
            story.append(_p("Aucun quart prévu.", styles["body"]))
            continue
        rows = []
        for s in shifts:
            coverage = "\n".join(_range(a,b) for a,b in coverage_intervals(s)) or "Aucune"
            buffer = f"Avant : {s.buffer_before} min {'payées' if s.before_paid else 'non payées'}\nAprès : {s.buffer_after} min {'payées' if s.after_paid else 'non payées'}"
            pause = "\n".join(f"{_range(b.start,b.end)} ({'payée' if b.paid else 'non payée'})" for b in s.breaks) or "Aucune"
            rows.append([groups.get(s.group_id, "Groupe manquant"), _range(s.start,s.end), coverage, buffer + "\nPauses : " + pause, format_duration(paid_minutes(s))])
        story.append(_table(["Groupe", "Présence", "Couverture", "Buffers et pauses", "Rémunéré"], rows, [width*f for f in (.17,.2,.2,.28,.15)], styles))
        activities = []
        for a in sorted((a for a in week.activities if a.day == day), key=lambda a: a.start):
            if a.responsible_ids and educator_id not in a.responsible_ids:
                continue
            actual = []
            for s in shifts:
                if s.group_id == a.group_id:
                    for x, y in coverage_intervals(s):
                        if x < a.end and y > a.start:
                            actual.append(_range(max(x,a.start), min(y,a.end)))
            if actual:
                room = rooms.get(a.room_id)
                location = room.name + (" (extérieur)" if room.outdoor else "") if room else "Lieu non défini"
                activities.append([a.name, ", ".join(actual), location])
        if activities:
            story.append(Spacer(1, 3 * mm))
            story.append(_table(["Activité couverte", "Votre présence auprès du groupe", "Lieu"], activities, [width*.33,width*.37,width*.30], styles))
        story.append(Spacer(1, 4 * mm))
    story.append(_p(f"Total des heures rémunérées : {format_duration(total)}", styles["heading"]))
    return story


def export_general(week: Week, path: str | Path) -> Path:
    styles = _styles()
    return _write(path, _general_story(week, styles), landscape(A4))


def export_individual(week: Week, educator_id: str, path: str | Path) -> Path:
    styles = _styles()
    return _write(path, _individual_story(week, educator_id, styles))


def export_combined(week: Week, path: str | Path) -> Path:
    """One portrait PDF, one individual schedule per active/scheduled educator."""
    styles = _styles()
    story = []
    scheduled = {s.educator_id for s in week.shifts}
    for educator in sorted((e for e in week.educators if e.active or e.id in scheduled), key=lambda e: (e.seniority, e.name)):
        if story:
            story.append(PageBreak())
        story.extend(_individual_story(week, educator.id, styles))
    if not story:
        story = [_p("Aucune éducatrice à exporter.", styles["body"])]
    return _write(path, story)


def export_all_individual(week: Week, directory: str | Path) -> list[Path]:
    directory = Path(directory).expanduser().resolve()
    directory.mkdir(parents=True, exist_ok=True)
    paths = []
    scheduled = {s.educator_id for s in week.shifts}
    for educator in week.educators:
        if not educator.active and educator.id not in scheduled:
            continue
        name = re.sub(r"[^\w -]", "", educator.name, flags=re.UNICODE).strip().replace(" ", "_")[:80] or "educatrice"
        paths.append(export_individual(week, educator.id, directory / f"{name}_{educator.id[:8]}_{week.planning_date or week.monday}.pdf"))
    return paths
