"""Short, interruptible UI effects. Never animate calendar geometry or data."""
from PySide6.QtCore import (
    QAbstractAnimation, QEasingCurve, QEvent, QObject, QPropertyAnimation,
    Qt, QVariantAnimation, Signal,
)
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication, QGraphicsOpacityEffect, QLabel, QPushButton,
    QStackedWidget, QWidget,
)


class Motion(QObject):
    """Shared preference for navigation and dynamically created buttons."""
    changed = Signal(bool)

    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.enabled = True
        QApplication.instance().installEventFilter(self)

    def set_enabled(self, enabled):
        enabled = bool(enabled)
        if self.enabled != enabled:
            self.enabled = enabled
            self.changed.emit(enabled)

    def eventFilter(self, watched, event):
        if (event.type() == QEvent.Type.Show and isinstance(watched, QPushButton)
                and self.window.isAncestorOf(watched)
                and not hasattr(watched, "_motion_outline")):
            watched._motion_outline = ButtonOutline(watched, self)
        return False


class ButtonOutline(QWidget):
    """Fade a fine outline without moving buttons, changing text or eating clicks."""
    def __init__(self, button, motion):
        super().__init__(button)
        self.button, self.motion = button, motion
        self.level = 0.0
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setGeometry(button.rect())
        self.animation = QVariantAnimation(self)
        self.animation.setDuration(120)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.valueChanged.connect(self._value)
        button.installEventFilter(self)
        motion.changed.connect(self._preference)
        self.hide()

    def _value(self, value):
        self.level = float(value)
        self.setVisible(self.level > 0 and self.button.isEnabled())
        self.raise_()
        self.update()

    def _preference(self, enabled):
        if not enabled:
            self.animation.stop()
            self._value(0)

    def eventFilter(self, watched, event):
        kind = event.type()
        if kind == QEvent.Type.Resize:
            self.setGeometry(self.button.rect())
        elif kind in (QEvent.Type.Hide, QEvent.Type.EnabledChange):
            self.animation.stop()
            self._value(0)
        elif kind in (QEvent.Type.Enter, QEvent.Type.Leave,
                      QEvent.Type.FocusIn, QEvent.Type.FocusOut):
            self.animation.stop()
            if self.motion.enabled and self.button.isEnabled():
                active = self.button.underMouse() or self.button.hasFocus()
                # Enter/Leave can precede Qt's update of underMouse().
                if kind == QEvent.Type.Enter:
                    active = True
                elif kind == QEvent.Type.Leave:
                    active = self.button.hasFocus()
                self.animation.setStartValue(self.level)
                self.animation.setEndValue(1.0 if active else 0.0)
                self.animation.start()
        return False

    def paintEvent(self, event):
        from .appearance import accent_color
        color = QColor(accent_color("#D5E3DD" if self.button.objectName() == "railButton"
                                    else "#527B69"))
        color.setAlphaF(.65 * self.level)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(color, 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 8, 8)


class AnimatedStack(QStackedWidget):
    """Fade the outgoing snapshot over a live, immediately interactive new page."""
    def __init__(self, motion, parent=None):
        super().__init__(parent)
        self.motion = motion
        self.overlay = QLabel(self)
        self.overlay.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.effect = QGraphicsOpacityEffect(self.overlay)
        self.overlay.setGraphicsEffect(self.effect)
        self.animation = QPropertyAnimation(self.effect, b"opacity", self)
        self.animation.setDuration(160)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.finished.connect(self._finish)
        self.overlay.hide()
        motion.changed.connect(lambda enabled: self._finish() if not enabled else None)

    @property
    def animating(self):
        return self.animation.state() == QAbstractAnimation.State.Running

    def _finish(self):
        self.animation.stop()
        self.overlay.hide()
        self.overlay.clear()  # Release the snapshot, especially on Retina screens.

    def setCurrentWidget(self, widget):
        index = self.indexOf(widget)
        if index >= 0:
            self.setCurrentIndex(index)

    def setCurrentIndex(self, index):
        if index == self.currentIndex() or not 0 <= index < self.count():
            return
        animate = self.motion.enabled and self.isVisible() and self.currentWidget() is not None
        # A rapid second navigation completes the old transition first.
        self._finish()
        snapshot = self.grab() if animate else None
        super().setCurrentIndex(index)
        if snapshot is not None:
            self.overlay.setGeometry(self.rect())
            self.overlay.setPixmap(snapshot)
            self.effect.setOpacity(1.0)
            self.overlay.raise_()
            self.overlay.show()
            self.animation.setStartValue(1.0)
            self.animation.setEndValue(0.0)
            self.animation.start()

    def resizeEvent(self, event):
        self._finish()
        super().resizeEvent(event)

    def hideEvent(self, event):
        self._finish()
        super().hideEvent(event)
