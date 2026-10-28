"""Live themes remain accessible and cannot mutate schedule data or staff colours."""
import json
from copy import deepcopy
import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QWidget
from gardeplan.daily import day_plan
from gardeplan.storage import Repository
from gardeplan.ui.appearance import (
    Appearance, AppearancePanel, PRESETS, accessible_accent, set_themed_style,
)
from gardeplan.ui.forms import EducatorDialog
from gardeplan.ui.main_window import MainWindow
from gardeplan.ui.motion import Motion
from gardeplan.ui.theme import contrast


def test_all_presets_and_light_custom_accents_support_white_text():
    for value in [*PRESETS.values(), "#FFFFFF", "#FFFF00", "#00FF00", "#DD88CC", "#000000"]:
        assert contrast("#FFFFFF", accessible_accent(value)) >= 4.5
    for value in ["red", "#FFF", "#FFFFFF; color:red", None]:
        with pytest.raises(ValueError):
            accessible_accent(value)


def test_theme_and_motion_persist_and_damaged_preferences_are_nonblocking(qapp, tmp_path):
    path = tmp_path / "interface.json"
    root = QWidget()
    motion = Motion(root)
    appearance = Appearance(root, motion, path)
    appearance.choose("Personnalisé", "#FFFF00")
    motion.set_enabled(False)
    loaded = json.loads(path.read_text())
    assert loaded["preset"] == "Personnalisé" and loaded["animations"] is False
    restored = Appearance(root, Motion(root), path)
    assert restored.accent == appearance.accent
    assert not restored.motion.enabled
    path.write_text('{"preset": "inconnu", "custom": "invalid"}')
    fallback = Appearance(root, Motion(root), path)
    assert fallback.preset == "Forêt"
    assert fallback.accent == PRESETS["Forêt"]
    root.deleteLater()
    qapp.processEvents()


def test_live_theme_changes_existing_and_new_forms_without_changing_data(qapp, tmp_path, valid_week):
    repo = Repository(tmp_path / "test.sqlite")
    plan = day_plan("2026-10-28", valid_week)
    repo.save(plan)
    window = MainWindow(repo, plan)
    window.show()
    qapp.processEvents()
    before = deepcopy(window.week.to_dict())
    try:
        window.appearance.choose("Bleu")
        assert "#245C85" in window.styleSheet()
        assert "#245C85" in window.home_page.body.styleSheet()
        assert "#245C85" in window.enrolment_panel.styleSheet()
        dialog = EducatorDialog(window.week, window.week.educators[0], window)
        dialog.show()
        qapp.processEvents()
        assert "#245C85" in dialog.styleSheet()
        window.appearance.choose("Prune")
        assert "#704366" in dialog.styleSheet()
        window.appearance.choose("Forêt")
        assert "#214F40" in window.styleSheet()
        assert window.week.to_dict() == before
        assert not window.dirty
        dialog.close()
        dialog.deleteLater()
    finally:
        window.autosave.stop()
        window.dirty = False
        window.close()
        window.deleteLater()
        qapp.processEvents()


def test_keyboard_custom_colour_validation_and_preference_write_failure(qapp, tmp_path, monkeypatch):
    root = QWidget()
    appearance = Appearance(root, Motion(root), tmp_path / "interface.json")
    panel = AppearancePanel(appearance, root)
    root.show()
    try:
        panel.presets.setCurrentText("Personnalisé")
        panel.color.setText("#112255")
        QTest.keyClick(panel.color, Qt.Key.Key_Return)
        assert appearance.accent == "#112255"
        panel.color.setText("oops")
        panel.color.editingFinished.emit()
        assert "#RRGGBB" in panel.message.text()
        assert appearance.accent == "#112255"
        # A bad custom field must not prevent returning to a predefined theme.
        panel.presets.setCurrentText("Ardoise")
        assert appearance.accent == PRESETS["Ardoise"]
        def fail(*args):
            raise PermissionError("read-only")
        monkeypatch.setattr("gardeplan.ui.appearance.os.replace", fail)
        panel.presets.setCurrentText("Bleu")
        assert appearance.accent == PRESETS["Bleu"]
        assert "cette session" in panel.message.text()
        assert not list(tmp_path.glob("interface-*.tmp"))
    finally:
        root.deleteLater()
        qapp.processEvents()
