import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from release_notes import version_notes, build_release_notes


class ReleaseNotesTests(unittest.TestCase):
    def test_selects_only_the_requested_version(self):
        with TemporaryDirectory() as folder:
            path=Path(folder)/'CHANGELOG.md';path.write_text('# Notes\n## [0.3.1] — date\n\n- Accueil\n\n## [0.3.0]\n\n- Ancien\n')
            self.assertEqual(version_notes(path,'0.3.1'),'- Accueil')
            notes=build_release_notes(path,'0.3.1','GraphicShack/Planificateur-Service-de-garde',12,34)
            self.assertIn('/actions/runs/12',notes);self.assertIn('donnees',notes)
            self.assertNotIn('- Ancien',notes)

    def test_missing_empty_or_invalid_notes_block_publication(self):
        with TemporaryDirectory() as folder:
            path=Path(folder)/'CHANGELOG.md';path.write_text('## [0.3.1]\n\n## [0.3.0]\nAncien\n')
            for version in ('0.3.1','0.4.0','.*'):
                with self.assertRaises(ValueError):version_notes(path,version)

    def test_current_version_has_reviewable_notes(self):
        import tomllib
        root=Path(__file__).resolve().parents[1]
        version=tomllib.loads((root/'pyproject.toml').read_text())['project']['version']
        self.assertIn('Accueil'.lower(),version_notes(root/'CHANGELOG.md',version).lower())
