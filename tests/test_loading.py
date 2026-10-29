"""Loading follows real worker signals and never applies a proposal by itself."""
from copy import deepcopy

import pytest
from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QDialog, QMessageBox, QWidget

from gardeplan.optimizer import GenerationResult
from gardeplan.storage import Repository
from gardeplan.ui.loading import GenerationLoading
from gardeplan.ui.main_window import MainWindow
from gardeplan.ui.motion import Motion


def test_loading_animates_and_stops_when_the_calculation_finishes(qapp):
    root = QWidget()
    motion = Motion(root)
    dialog = GenerationLoading(motion, root)
    dialog.show()
    qapp.processEvents()
    try:
        animation = dialog.spinner.animation
        assert animation.state() == animation.State.Running
        assert dialog.timer.isActive()
        animation.setCurrentTime(350)
        assert dialog.spinner.angle > 0
        QTest.keyClick(dialog, Qt.Key.Key_Escape)
        dialog.close()
        assert dialog.isVisible()  # The solver has not finished or been cancelled.
        dialog._elapsed()
        assert "Calcul en cours" in dialog.elapsed_label.text()
        assert "%" not in dialog.elapsed_label.text()
        dialog.finish()
        assert not dialog.isVisible() and not dialog.timer.isActive()
        assert animation.state() == animation.State.Stopped
    finally:
        dialog.finish()
        root.deleteLater()
        qapp.processEvents()


def test_loading_respects_disabled_animations_but_keeps_text_feedback(qapp):
    root = QWidget()
    motion = Motion(root)
    motion.set_enabled(False)
    dialog = GenerationLoading(motion, root)
    dialog.show()
    qapp.processEvents()
    try:
        assert dialog.spinner.animation.state() == dialog.spinner.animation.State.Stopped
        assert dialog.elapsed_label.isVisible() and dialog.timer.isActive()
        motion.set_enabled(True)
        assert dialog.spinner.animation.state() == dialog.spinner.animation.State.Running
        motion.set_enabled(False)
        assert dialog.spinner.animation.state() == dialog.spinner.animation.State.Stopped
    finally:
        dialog.finish()
        root.deleteLater()
        qapp.processEvents()


@pytest.mark.parametrize("outcome", ["success", "infeasible", "error"])
def test_generation_signals_close_loading_before_feedback_and_restore_controls(
        outcome, tmp_path, qapp, valid_week, monkeypatch):
    class Worker(QObject):
        completed = Signal(object)
        failed = Signal(str)
        finished = Signal()

        def __init__(self, plan, parent):
            super().__init__(parent)
            self.started = False

        def start(self):
            self.started = True

    monkeypatch.setattr("gardeplan.ui.main_window.GenerationThread", Worker)
    repo = Repository(tmp_path / "loading.sqlite")
    repo.save(valid_week)
    window = MainWindow(repo, valid_week, start_home=False)
    window.show()
    qapp.processEvents()
    before = deepcopy(window.week.to_dict())
    feedback = []

    def inspect(*args):
        assert not window._progress.isVisible()
        assert not window._progress.timer.isActive()
        feedback.append(True)

    for method in ("information", "warning"):
        monkeypatch.setattr(QMessageBox, method, inspect)
    monkeypatch.setattr(QDialog, "exec", lambda self: QDialog.DialogCode.Rejected)
    try:
        window.start_generation()
        worker = window._worker
        loading = window._progress
        assert worker.started and loading.isVisible()
        assert not window.generate_button.isEnabled()
        if outcome == "error":
            worker.failed.emit("La recherche n’a pas pu se terminer.")
        else:
            worker.completed.emit(GenerationResult(
                outcome == "success", deepcopy(window.week) if outcome == "success" else None,
                "Recherche terminée", "FEASIBLE" if outcome == "success" else "INFEASIBLE"))
        assert not loading.isVisible()
        assert window.week.to_dict() == before
        worker.finished.emit()
        assert window._progress is None and window._worker is None
        assert window.generate_button.isEnabled()
        assert window.week.to_dict() == before
        assert bool(feedback) == (outcome != "success")
    finally:
        window.autosave.stop()
        window.dirty = False
        window.close()
        window.deleteLater()
        qapp.processEvents()
