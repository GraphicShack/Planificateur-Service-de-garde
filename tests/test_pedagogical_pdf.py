"""Print-ready layout, pagination, precise geometry and empty interruptions."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from pypdf import PdfReader
from reportlab.pdfgen.canvas import Canvas

from gardeplan.daily import day_plan
from gardeplan.models import Educator, Group, Shift, Break
from gardeplan.pdf import export_general, PdfError
from gardeplan.pedagogical_pdf import minute_x, segments, GROUP_COLORS


def schedule(count):
    result = day_plan("2026-10-30")
    result.day_names[0] = "Pédagogique — Automne"
    result.groups = [Group(str(i), "Groupe " + chr(65+i)) for i in range(4)]
    for i in range(count):
        result.educators.append(Educator(str(i), f"Éducateur {i+1:02d}", seniority=min(i+1, 11)))
        result.shifts.append(Shift(str(i), str(i), str(i % 4), 0, 410, 1055))
    return result


class PedagogicalPdfTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "horaire.pdf"

    def test_eight_educators_per_landscape_letter_page(self):
        for count, expected in ((0, 1), (1, 1), (8, 1), (9, 2), (16, 2), (17, 3)):
            with self.subTest(count=count):
                export_general(schedule(count), self.path)
                reader = PdfReader(self.path)
                self.assertEqual(len(reader.pages), expected)
                for index, page in enumerate(reader.pages):
                    self.assertEqual(tuple(float(v) for v in page.mediabox), (0, 0, 792, 612))
                    text = page.extract_text()
                    self.assertIn("30 octobre 2026", text)
                    self.assertIn("Nom de l’éducateur", text)
                    self.assertIn(f"PAGE {index+1} / {expected}", text)
                    for group in ("Groupe A", "Groupe B", "Groupe C", "Groupe D"):
                        self.assertIn(group, text)
                    for hour in range(7, 18):
                        self.assertIn(f"{hour} h", text)
                    names = [e.name for e in schedule(count).educators if e.name in text]
                    self.assertLessEqual(len(names), 8)

    def test_paid_and_unpaid_breaks_are_blank_not_grey_blocks(self):
        for paid in (True, False):
            plan = schedule(1)
            plan.shifts[0].breaks = [Break(600, 630, paid=paid)]
            self.assertEqual(segments(plan, "0"), [("0", 410, 600), ("0", 630, 1055)])
            export_general(plan, self.path)
            text = PdfReader(self.path).pages[0].extract_text()
            self.assertNotIn("Pause", text)
            self.assertNotIn("Activité", text)
            self.assertNotIn("Couverture", text)
            self.assertIn("10 h 30", text)

    def test_split_shift_and_exact_102_minute_geometry(self):
        plan = schedule(1)
        plan.shifts = [Shift("a", "0", "0", 0, 433, 535), Shift("b", "0", "1", 0, 840, 1055)]
        recorded = []
        class Capture(Canvas):
            def roundRect(self, x, y, width, height, radius, **kwargs):
                if height == 28:
                    recorded.append((x, width))
                return super().roundRect(x, y, width, height, radius, **kwargs)
        before = deepcopy(plan.to_dict())
        with patch("gardeplan.pedagogical_pdf.Canvas", Capture):
            export_general(plan, self.path)
        self.assertEqual(len(recorded), 2)
        self.assertAlmostEqual(recorded[0][0], minute_x(433))
        self.assertAlmostEqual(recorded[0][1], 102 * 569 / 645)
        self.assertAlmostEqual(recorded[1][0], minute_x(840))
        self.assertEqual(plan.to_dict(), before)
        text = PdfReader(self.path).pages[0].extract_text()
        self.assertIn("07 h 13", text)
        self.assertIn("08 h 55", text)
        self.assertIn("14 h 00", text)
        self.assertEqual(text.count("Éducateur 01"), 1)

    def test_same_group_keeps_template_colour_on_second_page(self):
        plan = schedule(9)
        colours = []
        class Capture(Canvas):
            def setFillColor(self, color, *args, **kwargs):
                self.current_colour = color
                return super().setFillColor(color, *args, **kwargs)
            def roundRect(self, x, y, width, height, radius, **kwargs):
                if height == 28:
                    colours.append(self.current_colour.hexval())
                return super().roundRect(x, y, width, height, radius, **kwargs)
        with patch("gardeplan.pedagogical_pdf.Canvas", Capture):
            export_general(plan, self.path)
        self.assertEqual(colours[0], colours[8])
        self.assertEqual(colours[0].lower().replace('0x', '#'), GROUP_COLORS[0].lower())

    def test_opening_and_closing_are_exact_boundaries_without_annotation(self):
        plan = schedule(1)
        plan.shifts[0].start = 410
        export_general(plan, self.path)
        text = PdfReader(self.path).pages[0].extract_text()
        self.assertIn("06 h 50", text)
        self.assertIn("17 h 35", text)
        self.assertNotIn("Présence hors", text)

    def test_daily_export_failure_preserves_previous_pdf(self):
        export_general(schedule(1), self.path)
        previous = self.path.read_bytes()
        with patch("gardeplan.pdf.os.replace", side_effect=PermissionError("PDF ouvert")):
            with self.assertRaises(PdfError):
                export_general(schedule(2), self.path)
        self.assertEqual(self.path.read_bytes(), previous)
        self.assertFalse(list(self.path.parent.glob(".gardeplan-pdf-*")))
