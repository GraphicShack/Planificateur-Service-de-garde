"""Tests of the release gate, without Qt, network access or compiled binaries."""
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from prepare_release import prepare


class ReleaseGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "inputs"
        self.output = self.root / "outputs"
        for folder, platform, report_name, archive_name, executable in (
            ("windows", "windows", "portable-archive.json", "Planificateur-SDG-Portable.zip", "Planificateur-SDG.exe"),
            ("macos", "cocoa", "macos-portable-archive.json", "Planificateur-SDG-0.1.1-macOS-arm64-Portable.zip", "Planificateur-SDG.app/Contents/MacOS/Planificateur-SDG"),
        ):
            path = self.source / folder
            path.mkdir(parents=True)
            report = dict(success=True, frozen=True, portable_mode=True, version="0.1.1", qt_platform=platform,
                          checks={key: True for key in (
                              "qt_application", "home_dashboard", "coverage_and_exact_minutes", "sqlite_save_reopen_backup",
                              "dashboard_day", "pdf_export_preview_print_modules",
                              "ortools_cp_sat_generation", "offline_operations", "portable_data_write")})
            (path / report_name).write_text(json.dumps(report), encoding="utf-8-sig")
            with zipfile.ZipFile(path / archive_name, "w") as archive:
                archive.writestr("Planificateur-SDG/portable.mode", "portable")
                archive.writestr(f"Planificateur-SDG/{executable}", "synthetic test fixture")

    def change_report(self, **changes):
        path = self.source / "windows/portable-archive.json"
        report = json.loads(path.read_text(encoding="utf-8-sig"))
        report.update(changes)
        path.write_text(json.dumps(report), encoding="utf-8")

    def assert_refused(self):
        with self.assertRaises((ValueError, zipfile.BadZipFile)):
            prepare(self.source, self.output, "0.1.1")
        self.assertFalse(self.output.exists())

    def test_publishes_inner_portable_zips_and_checksums(self):
        files = prepare(self.source, self.output, "0.1.1")
        self.assertEqual(len(files), 4)
        self.assertTrue((self.output / "Planificateur-SDG-0.1.1-Windows-x64-Portable.zip").is_file())
        self.assertEqual(len((self.output / "SHA256SUMS.txt").read_text().splitlines()), 4)

    def test_rejects_failed_or_nonportable_reports(self):
        for key in ("success", "frozen", "portable_mode"):
            with self.subTest(key=key):
                self.change_report(**{key: False})
                self.assert_refused()
                self.change_report(**{key: True})

    def test_rejects_wrong_version_and_platform(self):
        self.change_report(version="0.1.0")
        self.assert_refused()
        self.change_report(version="0.1.1", qt_platform="offscreen")
        self.assert_refused()

    def test_rejects_missing_native_check(self):
        self.change_report(checks={"portable_data_write": True})
        self.assert_refused()

    def test_requires_both_platforms_before_output(self):
        (self.source / "macos/macos-portable-archive.json").unlink()
        self.assert_refused()

    def test_rejects_zip_without_marker_or_executable(self):
        with zipfile.ZipFile(self.source / "windows/Planificateur-SDG-Portable.zip", "w") as archive:
            archive.writestr("Planificateur-SDG/Planificateur-SDG.exe", "synthetic test fixture")
        self.assert_refused()

    def test_rejects_corrupt_archive(self):
        (self.source / "windows/Planificateur-SDG-Portable.zip").write_bytes(b"not a ZIP")
        self.assert_refused()


if __name__ == "__main__":
    unittest.main()
