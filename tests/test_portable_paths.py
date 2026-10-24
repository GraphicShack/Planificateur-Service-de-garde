"""Contrôles sans Qt du stockage portable et de sa conservation au déplacement."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import plistlib

from gardeplan.data_paths import database_path, portable_root
from gardeplan.models import Week
from gardeplan.storage import Repository


class PortablePathsTests(unittest.TestCase):
    def test_windows_marker_places_data_next_to_executable(self):
        with TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            (root / "portable.mode").touch()
            result = database_path(root / "profil", executable=root / "Planificateur-SDG.exe", frozen=True)
            self.assertEqual(result, root / "donnees" / "gardeplan.sqlite")
            self.assertFalse((root / "profil").exists())

    def test_signed_mac_bundle_keeps_data_outside_application(self):
        with TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            (root / "portable.mode").touch()
            binary = root / "Planificateur-SDG.app" / "Contents" / "MacOS" / "Planificateur-SDG"
            binary.parent.mkdir(parents=True)
            self.assertEqual(portable_root(executable=binary, frozen=True), root)
            self.assertEqual(database_path(root / "profil", executable=binary, frozen=True),
                             root / "donnees" / "gardeplan.sqlite")

    def test_missing_marker_preserves_existing_profile_location(self):
        with TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            self.assertIsNone(portable_root(executable=root / "Planificateur-SDG.exe", frozen=True))
            self.assertEqual(database_path(root / "profil", executable=root / "Planificateur-SDG.exe", frozen=True),
                             root / "profil" / "gardeplan.sqlite")

    def test_mac_portable_intent_does_not_silently_fall_back_to_profile(self):
        with TemporaryDirectory() as folder:
            root = Path(folder).resolve() / "AppTranslocation" / "hasard" / "d"
            bundle = root / "Planificateur-SDG.app"
            binary = bundle / "Contents" / "MacOS" / "Planificateur-SDG"
            binary.parent.mkdir(parents=True)
            with (bundle / "Contents" / "Info.plist").open("wb") as handle:
                plistlib.dump({"PlanificateurPortable": True}, handle)
            self.assertEqual(portable_root(executable=binary, frozen=True), root)
            self.assertEqual(database_path(Path(folder).resolve() / "profil", executable=binary, frozen=True),
                             root / "donnees" / "gardeplan.sqlite")
            self.assertFalse((Path(folder).resolve() / "profil").exists())

    def test_source_portable_flag_uses_project_not_python_installation(self):
        with TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            self.assertEqual(portable_root(force=True, frozen=False, source_root=root), root)
            self.assertEqual(database_path(root / "profil", force_portable=True,
                                           frozen=False, source_root=root, example=True),
                             root / "donnees" / "exemple.sqlite")

    def test_explicit_database_selection_remains_available(self):
        with TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            self.assertEqual(database_path(root, database=root / "personnalise.sqlite", force_portable=True),
                             root / "personnalise.sqlite")

    def test_whole_folder_can_be_moved_and_reopened_without_configuration(self):
        with TemporaryDirectory() as folder:
            root = Path(folder).resolve() / "Bureau" / "Planificateur-SDG"
            root.mkdir(parents=True)
            (root / "portable.mode").touch()
            path = database_path("unused", executable=root / "Planificateur-SDG.exe", frozen=True)
            week = Week("2026-10-26", day_names={0: "Pédagogique"})
            Repository(path).save(week)
            moved = Path(folder).resolve() / "Cle-USB"
            root.rename(moved)
            reopened = database_path("unused", executable=moved / "Planificateur-SDG.exe", frozen=True)
            self.assertEqual(Repository(reopened).load_week(week.monday).to_dict(), week.to_dict())


if __name__ == "__main__":
    unittest.main()
