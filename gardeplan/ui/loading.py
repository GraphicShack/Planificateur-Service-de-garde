"""Honest, non-blocking generation feedback; no simulated percentage or stages."""
from PySide6.QtCore import QElapsedTimer, QEasingCurve, QTimer, Qt, QVariantAnimation
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout, QWidget

from .appearance import accent_color, set_themed_style


class LoadingSpinner(QWidget):
    def __init__(self, motion, parent=None):
        super().__init__(parent)
        self.motion = motion
        self.angle = 0.0
        self.setFixedSize(64, 64)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAccessibleName("Calcul de l’horaire en cours")
        self.animation = QVariantAnimation(self)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(360.0)
        self.animation.setDuration(1100)
        self.animation.setLoopCount(-1)
        self.animation.setEasingCurve(QEasingCurve.Type.Linear)
        self.animation.valueChanged.connect(self._rotate)
        motion.changed.connect(self._sync)

    def _rotate(self, value):
        self.angle = float(value)
        self.update()

    def _sync(self, *_):
        self.animation.stop()
        if self.isVisible() and self.motion.enabled:
            self.animation.start()
        else:
            self._rotate(0)

    def showEvent(self, event):
        super().showEvent(event)
        self._sync()

    def hideEvent(self, event):
        self.animation.stop()
        super().hideEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(6, 6, -6, -6)
        painter.setPen(QPen(QColor("#E5EBE7"), 5))
        painter.drawEllipse(rect)
        pen = QPen(QColor(accent_color("#214F40")), 5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawArc(rect, round(-self.angle * 16), 105 * 16)


class GenerationLoading(QDialog):
    """Closing is controlled by the real worker, whose calculation continues offline."""
    def __init__(self, motion, parent=None):
        super().__init__(parent)
        self._done = False
        self.setWindowTitle("Génération de l’horaire")
        self.setObjectName("generationLoading")
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)
        self.setMinimumWidth(360)
        self.resize(460, 340)
        set_themed_style(self, """
            QDialog#generationLoading {background:#FFFFFF;}
            QDialog#generationLoading QLabel {font-size:16px;color:#203D32;background:transparent;}
            QDialog#generationLoading QLabel#loadingTitle {font-size:22px;font-weight:700;}
            QDialog#generationLoading QLabel#loadingElapsed {color:#214F40;font-weight:600;}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(16)
        self.spinner = LoadingSpinner(motion, self)
        layout.addWidget(self.spinner, 0, Qt.AlignmentFlag.AlignHCenter)
        title = QLabel("Création de votre horaire")
        title.setObjectName("loadingTitle")
        title.setWordWrap(True)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        message = QLabel("Recherche d’une proposition respectant les disponibilités, les rangs et la couverture des groupes.")
        message.setWordWrap(True)
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(message)
        self.elapsed_label = QLabel("Calcul en cours…")
        self.elapsed_label.setObjectName("loadingElapsed")
        self.elapsed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.elapsed_label)
        hint = QLabel("Cela peut prendre quelques instants. Votre horaire actuel est conservé jusqu’à votre confirmation.")
        hint.setWordWrap(True)
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)
        self.clock = QElapsedTimer()
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._elapsed)

    def _elapsed(self):
        seconds = self.clock.elapsed() // 1000
        self.elapsed_label.setText(f"Calcul en cours · {seconds} s écoulées")

    def showEvent(self, event):
        super().showEvent(event)
        if not self._done:
            if not self.clock.isValid():
                self.clock.start()
            self.timer.start()

    def hideEvent(self, event):
        self.timer.stop()
        self.spinner.animation.stop()
        super().hideEvent(event)

    def reject(self):
        # Escape must not hide the only feedback while the worker is still running.
        if self._done:
            super().reject()

    def closeEvent(self, event):
        if self._done:
            super().closeEvent(event)
        else:
            event.ignore()

    def finish(self):
        self._done = True
        self.timer.stop()
        self.spinner.animation.stop()
        super().accept()
