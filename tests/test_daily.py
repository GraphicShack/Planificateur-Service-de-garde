"""Real daily persistence, compatibility, exact totals, PDFs and constraints."""
from copy import deepcopy
from contextlib import closing
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from gardeplan.daily import day_plan, duplicate_day
from gardeplan.models import Week, Educator, Group, GroupPeriod, Shift, Window, totals
from gardeplan.storage import Repository, StorageError
from gardeplan.validation import validate


def prepared_day(selected="2026-10-28"):
    plan = day_plan(selected)
    plan.educators = [Educator(str(i), name, target_minutes=645, max_minutes=720)
                      for i, name in enumerate(("Camille Roy", "Sophie Martin"))]
    plan.groups = [Group("g1", "Groupe A", periods=[GroupPeriod(0, 420, 1050, 20)])]
    plan.shifts = [Shift(str(i), person.id, "g1", 0, 410, 1055, 10, 5)
                   for i, person in enumerate(plan.educators)]
    plan.day_names = {0: "Pédagogique — Automne"}
    return plan


class DailyTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = Repository(self.root / "planning.sqlite")

    def test_two_days_same_week_have_independent_versions_status_and_hours(self):
        first = prepared_day()
        self.repo.save(first)
        second = prepared_day("2026-10-29")
        second.shifts[0].start = 433
        second.status = "archived"
        self.repo.save(second)
        first.day_names[0] = "Jour modifié"
        self.repo.save(first)
        self.assertEqual(self.repo.load_day("2026-10-29"), second)
        self.assertEqual(len(self.repo.history(first.storage_key)), 2)
        self.assertEqual(len(self.repo.history(second.storage_key)), 1)
        self.assertNotEqual(totals(first), totals(second))
        self.assertEqual(len(self.repo.list_days()), 2)

    def test_any_date_including_weekend_keeps_real_label(self):
        plan = prepared_day("2026-10-31")
        self.repo.save(plan)
        self.assertTrue(self.repo.load_day("2026-10-31").day_label(0).startswith("Samedi 31/10"))
        self.assertEqual(plan.active_days, (0,))

    def test_daily_parser_rejects_hidden_other_day_data_and_wrong_date(self):
        raw = prepared_day().to_dict()
        raw["shifts"][0]["day"] = 1
        with self.assertRaises(ValueError):
            Week.from_dict(raw)
        raw = prepared_day().to_dict()
        raw["planning_date"] = "2026-11-02"
        with self.assertRaises(ValueError):
            Week.from_dict(raw)

    def test_new_day_copies_profiles_but_not_assignments_enrolment_or_absences(self):
        first = prepared_day()
        first.educators[0].absences = [Window(0, 600, 615)]
        second = day_plan("2026-10-29", first)
        self.assertEqual(second.educators[0].name, first.educators[0].name)
        self.assertEqual(second.educators[0].target_minutes, 645)
        self.assertEqual(second.educators[0].absences, [])
        self.assertEqual((second.groups, second.shifts, second.activities, second.day_names), ([], [], [], {}))
        self.assertEqual(first.educators[0].absences, [Window(0, 600, 615)])

    def test_duplicate_copies_exact_minutes_without_overwriting_destination(self):
        plan = prepared_day()
        plan.shifts[0].start, plan.shifts[0].end = 433, 535
        self.repo.save(plan)
        copied = self.repo.duplicate_day(plan, "2026-11-03")
        self.assertEqual(copied.shifts[0].end - copied.shifts[0].start, 102)
        self.assertEqual(copied.planning_date, "2026-11-03")
        self.assertEqual(copied.monday, "2026-11-02")
        before = self.repo.load_day("2026-11-03").to_dict()
        with self.assertRaises(StorageError):
            self.repo.duplicate_day(plan, "2026-11-03")
        self.assertEqual(self.repo.load_day("2026-11-03").to_dict(), before)

    def test_restore_published_daily_version_preserves_frozen_snapshot(self):
        plan = prepared_day()
        plan.status = "published"
        original = self.repo.save(plan)
        restored = self.repo.restore(original)
        self.assertEqual(restored.status, "draft")
        self.assertEqual(self.repo.load_version(original).status, "published")
        self.assertEqual(len(self.repo.history(plan.storage_key)), 2)

    def test_legacy_schema_upgrade_preserves_payload_and_extracts_only_chosen_date(self):
        old = Week("2026-10-26", educators=[Educator("e", "Ancien profil", target_minutes=2100)])
        old.shifts = [Shift("a", "e", "g", 0, 433, 535), Shift("b", "e", "g", 2, 678, 767)]
        old.day_names = {0: "Lundi ancien", 2: "Mercredi ancien"}
        raw = old.to_dict()
        raw.pop("planning_date")
        payload = json.dumps(raw, ensure_ascii=False)
        checksum = hashlib.sha256(payload.encode()).hexdigest()
        with closing(sqlite3.connect(self.repo.path)) as conn, conn:
            conn.execute("UPDATE metadata SET value='1' WHERE key='schema_version'")
            conn.execute("INSERT INTO versions(monday,created_at,status,payload,checksum) VALUES(?,?,?,?,?)",
                         (old.monday, "2026-10-26T00:00:00Z", "draft", payload, checksum))
        reopened = Repository(self.repo.path)
        safety = list(self.root.glob("planning-avant-format2-*.sqlite3"))
        self.assertEqual(len(safety), 1)
        with closing(sqlite3.connect(safety[0])) as conn, conn:
            self.assertEqual(conn.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()[0], "1")
        extracted = reopened.load_day("2026-10-28")
        self.assertEqual([s.id for s in extracted.shifts], ["b"])
        self.assertEqual(extracted.shifts[0].day, 0)
        self.assertEqual(extracted.day_names, {0: "Mercredi ancien"})
        self.assertEqual(extracted.educators[0].target_minutes, 0)
        self.assertEqual(reopened.load_week(old.monday), old)
        with closing(sqlite3.connect(reopened.path)) as conn, conn:
            self.assertEqual(conn.execute("SELECT payload,checksum FROM versions WHERE monday=?", (old.monday,)).fetchone(), (payload, checksum))
            self.assertEqual(conn.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()[0], "2")
        self.assertIsNone(reopened.load_day("2026-10-29"))

    def test_daily_backup_import_preserves_dates_and_archives(self):
        self.repo.save(prepared_day())
        archive = prepared_day("2026-10-30")
        archive.status = "archived"
        self.repo.save(archive)
        backup = self.repo.backup(self.root / "copie.sqlite")
        other = Repository(self.root / "autre.sqlite")
        other.import_backup(backup)
        self.assertEqual(other.load_day("2026-10-30"), archive)
        self.assertEqual(len(other.list_days()), 2)

    def test_validation_uses_actual_date_and_does_not_warn_for_unset_target(self):
        plan = prepared_day()
        plan.educators[0].target_minutes = 0
        self.assertFalse(any(i.code == "target" for i in validate(plan)))
        plan.shifts.pop()
        errors = [i for i in validate(plan) if i.severity == "error"]
        self.assertTrue(any("Mercredi 28/10" in i.message for i in errors))
        self.assertFalse(any("Lundi," in i.message for i in errors))

    def test_sparse_ranks_are_valid_and_retained_exactly(self):
        plan = prepared_day()
        plan.educators[0].seniority = 1
        plan.educators[1].seniority = 9
        self.assertFalse(any(i.severity == "error" for i in validate(plan)))
        self.repo.save(plan)
        self.assertEqual([e.seniority for e in self.repo.load_day(plan.planning_date).educators], [1, 9])
        plan.educators[1].seniority = 12
        self.assertTrue(any("rang de 1 à 11" in i.message for i in validate(plan)))

    def test_daily_presence_cannot_extend_beyond_opening_and_closing_buffers(self):
        plan = prepared_day()
        self.assertFalse(any(i.code == "service_hours" for i in validate(plan)))
        plan.shifts[0].start = 409
        self.assertTrue(any(i.code == "service_hours" for i in validate(plan)))
        plan.shifts[0].start, plan.shifts[0].end = 410, 1056
        self.assertTrue(any(i.code == "service_hours" for i in validate(plan)))

    def test_colours_remain_distinct_beyond_eleven_and_survive_reopening(self):
        from gardeplan.identity import next_educator_color
        plan = day_plan("2026-10-28")
        for index in range(25):
            color = next_educator_color(plan.educators)
            plan.educators.append(Educator(str(index), f"Profil {index}", color=color, seniority=11))
        colors = [e.color for e in plan.educators]
        self.assertEqual(len(set(color.casefold() for color in colors)), 25)
        self.repo.save(plan)
        self.assertEqual([e.color for e in self.repo.load_day(plan.planning_date).educators], colors)

    @unittest.skipUnless(importlib.util.find_spec("pypdf"), "pypdf nécessaire")
    def test_daily_pdf_contains_only_selected_day(self):
        from gardeplan.pdf import export_general, export_individual
        from pypdf import PdfReader
        plan = prepared_day()
        for path in (export_general(plan, self.root / "general.pdf"),
                     export_individual(plan, "0", self.root / "individuel.pdf")):
            text = "\n".join(page.extract_text() for page in PdfReader(path).pages)
            self.assertTrue("28 octobre 2026" in text or "Mercredi 28/10/2026" in text)
            self.assertNotIn("Semaine du", text)
            self.assertNotIn("Mardi", text)
            self.assertIn("Groupe A", text)

    @unittest.skipUnless(importlib.util.find_spec("ortools"), "OR-Tools nécessaire")
    def test_daily_solver_meets_daily_target_and_preserves_other_date(self):
        from gardeplan.optimizer import generate
        plan = prepared_day()
        other = prepared_day("2026-10-29")
        self.repo.save(other)
        plan.shifts = []
        result = generate(plan, time_limit=10)
        self.assertTrue(result.success, result.message)
        self.assertEqual(result.proposal.planning_date, "2026-10-28")
        self.assertEqual(totals(result.proposal), {"0": 645, "1": 645})
        self.assertFalse(any(i.severity == "error" for i in validate(result.proposal)))
        self.assertEqual(self.repo.load_day("2026-10-29"), other)
