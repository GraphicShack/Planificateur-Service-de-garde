"""Letter landscape calendar based on the user's pedagogical-day template.

Coordinates retain the template's 30 pt margins, 163 pt name column and eight
40 pt rows. All time positions use minute values directly; breaks are holes.
"""
from datetime import date
from pathlib import Path
import os

from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import landscape, letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.utils import simpleSplit

from .models import format_time, working_intervals

WIDTH, HEIGHT = landscape(letter)
LEFT, RIGHT, NAME_WIDTH = 30, 762, 163
GRID_LEFT, GRID_WIDTH = LEFT + NAME_WIDTH, RIGHT - LEFT - NAME_WIDTH
START, END, PER_PAGE = 410, 1055, 8
INK, MUTED, RULE = "#17364B", "#5C7180", "#CDDAE1"
GROUP_COLORS = ("#C8E6DF", "#D4E3FA", "#F8D9BA", "#E2D5F0", "#F4D4E2", "#DEE6BD", "#CBE5EC", "#F0DFAD")
MONTHS = ("janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre")


def fonts():
    if "Pedagogique" not in pdfmetrics.getRegisteredFontNames():
        bundled = Path(__file__).parent / "assets" / "fonts"
        candidates = (
            (Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "arial.ttf",
             Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "arialbd.ttf"),
            (Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
             Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf")),
            (bundled / "PlanificateurSans-Regular.ttf", bundled / "PlanificateurSans-Bold.ttf"),
        )
        for regular, bold in candidates:
            if regular.is_file() and bold.is_file():
                pdfmetrics.registerFont(TTFont("Pedagogique", str(regular)))
                pdfmetrics.registerFont(TTFont("Pedagogique-Bold", str(bold)))
                break
        else:
            raise ValueError("La police du modèle PDF est absente du logiciel.")
    return "Pedagogique", "Pedagogique-Bold"


def minute_x(minute):
    return GRID_LEFT + (minute - START) * GRID_WIDTH / (END - START)


def segments(plan, educator_id):
    return [(shift.group_id, a, b) for shift in sorted(plan.shifts, key=lambda s: (s.start, s.end))
            if shift.educator_id == educator_id and shift.day == 0
            for a, b in working_intervals(shift)]


def _text(canvas, text, x, top, font, size, color=INK, *, width=None, align="left"):
    text = str(text)
    if width:
        while size > 7 and pdfmetrics.stringWidth(text, font, size) > width:
            size -= .25
        if pdfmetrics.stringWidth(text, font, size) > width:
            while text and pdfmetrics.stringWidth(text + "…", font, size) > width:
                text = text[:-1]
            text += "…"
    canvas.setFillColor(HexColor(color))
    canvas.setFont(font, size)
    method = canvas.drawCentredString if align == "center" else canvas.drawRightString if align == "right" else canvas.drawString
    method(x, HEIGHT - top, text)


def draw_day(plan, path):
    if not plan.planning_date:
        raise ValueError("Choisissez une journée avant d’exporter son horaire.")
    regular, bold = fonts()
    current = date.fromisoformat(plan.planning_date)
    date_label = f"{current.day} {MONTHS[current.month-1]} {current.year}"
    scheduled = {s.educator_id for s in plan.shifts}
    people = sorted((e for e in plan.educators if e.active or e.id in scheduled), key=lambda e: e.seniority)
    page_count = max(1, (len(people) + PER_PAGE - 1) // PER_PAGE)
    groups = {group.id: group for group in plan.groups}
    palette = {group.id: GROUP_COLORS[index % len(GROUP_COLORS)] for index, group in enumerate(plan.groups)}
    canvas = Canvas(str(path), pagesize=(WIDTH, HEIGHT), pageCompression=1)
    canvas.setTitle("Horaire de journée pédagogique — " + date_label)
    canvas.setAuthor("Planificateur — Service de garde")
    for page in range(page_count):
        canvas.setFillColor(HexColor(INK))
        canvas.rect(0, HEIGHT-13, WIDTH, 13, fill=1, stroke=0)
        _text(canvas, "JOURNÉE PÉDAGOGIQUE", LEFT, 54, bold, 21)
        _text(canvas, "Horaire de l’équipe éducative", LEFT, 75, regular, 12, MUTED)
        _text(canvas, "DATE", 563, 46, bold, 9, MUTED)
        _text(canvas, date_label, 563, 72, bold, 18, width=199)
        _text(canvas, plan.day_names.get(0, ""), LEFT, 103, bold, 9, MUTED, width=RIGHT-LEFT)
        # Legend repeats on every page. No legend item is created for breaks.
        legend_y, legend_x = 121, LEFT
        for group in plan.groups:
            label_width = min(180, pdfmetrics.stringWidth(group.name, regular, 9))
            item_width = max(126, 27 + label_width)
            if legend_x + item_width > RIGHT and legend_x != LEFT:
                legend_y += 19
                legend_x = LEFT
            canvas.setFillColor(HexColor(palette[group.id]))
            canvas.roundRect(legend_x, HEIGHT-legend_y-13, 15, 13, 3, fill=1, stroke=0)
            _text(canvas, group.name, legend_x+21, legend_y+10, regular, 9, width=item_width-27)
            legend_x += item_width
        grid_top = max(178, legend_y + 57)
        row_height = (498-grid_top)/PER_PAGE
        if row_height < 24:
            raise ValueError("La légende contient trop de groupes pour ce modèle. Raccourcissez leurs noms ou réduisez le nombre de groupes.")
        canvas.setFillColor(HexColor(INK))
        canvas.rect(LEFT, HEIGHT-grid_top, NAME_WIDTH, 32, fill=1, stroke=0)
        _text(canvas, "Nom de l’éducateur", LEFT+10, grid_top-12, bold, 11, "#FFFFFF")
        _text(canvas, "6 h 50", GRID_LEFT, grid_top-23, bold, 9)
        _text(canvas, "17 h 35", RIGHT, grid_top-23, bold, 9, align="right")
        for minute in range(420, END, 60):
            _text(canvas, format_time(minute), minute_x(minute), grid_top-8, bold, 9, align="center")
        for row in range(PER_PAGE):
            top = grid_top + row*row_height
            canvas.setFillColor(HexColor("#F4F7F9") if row % 2 == 0 else white)
            canvas.rect(LEFT, HEIGHT-top-row_height, RIGHT-LEFT, row_height, fill=1, stroke=0)
        canvas.setStrokeColor(HexColor(RULE))
        for minute in sorted({START, END} | set(range((START+29)//30*30, END, 30))):
            canvas.setLineWidth(.55 if minute % 60 == 0 else .3)
            canvas.setDash([] if minute % 60 == 0 else [1.5, 2])
            x = minute_x(minute)
            canvas.line(x, HEIGHT-grid_top, x, HEIGHT-498)
        canvas.setDash([])
        canvas.setLineWidth(.5)
        for row in range(PER_PAGE+1):
            y = HEIGHT-grid_top-row*row_height
            canvas.line(LEFT, y, RIGHT, y)
        canvas.line(LEFT, HEIGHT-grid_top, LEFT, HEIGHT-498)
        canvas.line(RIGHT, HEIGHT-grid_top, RIGHT, HEIGHT-498)
        outside = []
        for row, person in enumerate(people[page*PER_PAGE:(page+1)*PER_PAGE]):
            top = grid_top+row*row_height
            _text(canvas, person.name, LEFT+10, top+24, bold, 10, width=NAME_WIDTH-20)
            for group_id, a, b in segments(plan, person.id):
                group = groups.get(group_id)
                if group is None:
                    raise ValueError(f"Un groupe est manquant pour {person.name}.")
                if a < START:
                    outside.append(f"{person.name} : {format_time(a)}–{format_time(min(b, START))}")
                if b > END:
                    outside.append(f"{person.name} : {format_time(max(a, END))}–{format_time(b)}")
                first, last = max(START, a), min(END, b)
                if first >= last:
                    continue
                x, end_x = minute_x(first), minute_x(last)
                # No horizontal inset: one minute must have its exact width.
                canvas.setFillColor(HexColor(palette[group_id]))
                canvas.roundRect(x, HEIGHT-top-row_height+6, end_x-x, row_height-12, min(3, (end_x-x)/2), fill=1, stroke=0)
                width = end_x-x-6
                if width >= 22:
                    _text(canvas, group.name, (x+end_x)/2, top+17, bold, 9, width=width, align="center")
                    _text(canvas, f"{format_time(a)} – {format_time(b)}", (x+end_x)/2, top+29, regular, 7, width=width, align="center")
        _text(canvas, "REPÈRES", LEFT, 521, bold, 8, MUTED)
        _text(canvas, "Une ligne = un éducateur • Traits pointillés = 30 minutes", 90, 521, regular, 9, MUTED)
        if outside:
            lines = simpleSplit("Présence hors de l’échelle 6 h 50–17 h 35 : " + " ; ".join(dict.fromkeys(outside)), regular, 7.5, RIGHT-LEFT)
            if len(lines) > 3:
                raise ValueError("Trop de plages hors de l’échelle 6 h 50–17 h 35 pour ce modèle. Vérifiez les heures de la journée.")
            for index, line in enumerate(lines):
                _text(canvas, line, LEFT, 533+index*9, regular, 7.5, MUTED)
        else:
            _text(canvas, "Les zones sans bloc correspondent aux périodes non travaillées.", LEFT, 540, regular, 9, MUTED)
        canvas.setStrokeColor(HexColor(RULE))
        canvas.line(LEFT, HEIGHT-558, RIGHT, HEIGHT-558)
        _text(canvas, "Horaire de la journée pédagogique", LEFT, 576, regular, 8, MUTED)
        _text(canvas, f"PAGE {page+1} / {page_count}", RIGHT, 576, bold, 9, align="right")
        canvas.showPage()
    canvas.save()
