"""Transitions must never delay selection, swallow clicks or leave a snapshot."""
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QPushButton, QVBoxLayout, QWidget

from gardeplan.ui.motion import AnimatedStack, Motion


def scene(qapp):
    root = QWidget()
    motion = Motion(root)
    stack = AnimatedStack(motion)
    layout = QVBoxLayout(root)
    layout.addWidget(stack)
    pages = [QPushButton(f"Page {i}") for i in range(3)]
    for page in pages:
        stack.addWidget(page)
    root.resize(400, 250)
    root.show()
    qapp.processEvents()
    return root, motion, stack, pages


def dispose(root, qapp):
    root.close()
    root.deleteLater()
    qapp.processEvents()


def test_transition_switches_immediately_keeps_focus_and_accepts_clicks(qapp):
    root, motion, stack, pages = scene(qapp)
    clicked = []
    pages[1].clicked.connect(lambda: clicked.append(True))
    try:
        stack.setCurrentWidget(pages[1])
        pages[1].setFocus()
        assert stack.currentWidget() is pages[1]
        assert stack.animating and stack.overlay.isVisible()
        assert pages[1].hasFocus()
        assert stack.overlay.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        target = root.childAt(pages[1].mapTo(root, pages[1].rect().center()))
        QTest.mouseClick(target, Qt.MouseButton.LeftButton)
        assert clicked == [True]
        stack.animation.setCurrentTime(stack.animation.duration())
        assert not stack.animating and not stack.overlay.isVisible()
        assert stack.overlay.pixmap().isNull()
    finally:
        dispose(root, qapp)


def test_rapid_navigation_uses_the_latest_page_and_resize_finishes(qapp):
    root, motion, stack, pages = scene(qapp)
    try:
        for index in [1, 2, 0, 2, 1]:
            stack.setCurrentIndex(index)
            assert stack.currentIndex() == index and stack.animating
        stack.setCurrentIndex(-1)
        assert stack.currentWidget() is pages[1]
        root.resize(480, 300)
        qapp.processEvents()
        assert not stack.animating and not stack.overlay.isVisible()
    finally:
        dispose(root, qapp)


def test_disabling_motion_stops_all_effects_without_altering_selection(qapp):
    root, motion, stack, pages = scene(qapp)
    try:
        stack.setCurrentIndex(1)
        outline = pages[1]._motion_outline
        QTest.mouseMove(pages[1], pages[1].rect().center())
        motion.set_enabled(False)
        assert not stack.animating and not stack.overlay.isVisible()
        assert outline.animation.state() == outline.animation.State.Stopped
        assert not outline.isVisible()
        stack.setCurrentIndex(2)
        assert stack.currentIndex() == 2 and not stack.animating
        motion.set_enabled(True)
        stack.setCurrentIndex(0)
        assert stack.animating
        root.hide()
        assert not stack.animating
    finally:
        dispose(root, qapp)


def test_initial_selection_and_same_page_do_not_start_an_animation(qapp):
    root, motion, stack, pages = scene(qapp)
    try:
        assert not stack.animating
        stack.setCurrentWidget(pages[0])
        assert not stack.animating
        # Animation changes only presentation, never the contents of a page.
        assert [p.text() for p in pages] == ["Page 0", "Page 1", "Page 2"]
    finally:
        dispose(root, qapp)


def test_hidden_windows_release_event_observation_and_can_reopen(qapp):
    root, motion, stack, pages = scene(qapp)
    try:
        assert motion._watching
        root.hide()
        assert not motion._watching
        root.show()
        qapp.processEvents()
        assert motion._watching
        stack.setCurrentIndex(1)
        assert stack.animating
    finally:
        dispose(root, qapp)
