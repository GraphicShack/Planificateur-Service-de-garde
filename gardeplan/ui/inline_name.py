"""An accessible, in-place day name: Enter/blur save, Escape cancels."""
from PySide6.QtCore import Qt, QEvent, Signal, QSize
from PySide6.QtWidgets import QWidget, QPushButton, QLineEdit, QStackedLayout
from .visuals import icon


class InlineDayName(QWidget):
    changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = ""
        self.editing = False
        self.setMinimumWidth(190)
        self.setMaximumWidth(440)
        self.stack = QStackedLayout(self)
        self.stack.setContentsMargins(0, 0, 0, 0)
        self.button = QPushButton()
        self.button.setIconSize(QSize(16, 16))
        self.button.setMinimumHeight(44)
        self.button.setStyleSheet("QPushButton{font-size:16px;font-weight:600;color:#203D32;background:transparent;border:0;text-align:left;padding:6px 26px 6px 2px;} QPushButton:hover,QPushButton:focus{background:#DFEBE4;}")
        self.editor = QLineEdit()
        self.editor.setMaxLength(160)
        self.editor.setMinimumHeight(44)
        self.editor.setAccessibleName("Nom de la journée")
        self.editor.setPlaceholderText("Nom de la journée (facultatif)")
        self.editor.setStyleSheet("font-size:16px;color:#203D32;background:white;border:2px solid #214F40;border-radius:6px;")
        self.stack.addWidget(self.button)
        self.stack.addWidget(self.editor)
        self.button.clicked.connect(self.start_editing)
        self.editor.editingFinished.connect(self.finish_editing)
        self.editor.installEventFilter(self)
        self.button.installEventFilter(self)
        self.setFocusProxy(self.button)
        self.setText("")

    def text(self):
        return self._value

    def sizeHint(self):
        width = self.button.fontMetrics().horizontalAdvance(self._value or "Journée pédagogique")+40
        return QSize(min(440, max(190, width)), 44)

    def minimumSizeHint(self):
        return QSize(190, 44)

    def setText(self, value):
        value = value.strip()
        if self.editing and value != self._value:
            self.cancel_editing()
        self._value = value
        label = value or "Journée pédagogique"
        self.button.setText(self.button.fontMetrics().elidedText(label, Qt.TextElideMode.ElideRight, max(150, self.width()-36)))
        self.button.setAccessibleName(f"Nom de la journée : {label}. Appuyer sur Entrée pour modifier.")
        self.button.setToolTip(label)
        self.updateGeometry()

    def start_editing(self):
        if not self.isEnabled():
            return
        self.editing = True
        self.editor.setText(self._value)
        self.stack.setCurrentWidget(self.editor)
        self.editor.setFocus()
        self.editor.selectAll()

    def finish_editing(self):
        if not self.editing:
            return
        value = self.editor.text().strip()
        self.editing = False
        previous = self._value
        self.setText(value)
        self.stack.setCurrentWidget(self.button)
        if value != previous:
            self.changed.emit(value)

    def cancel_editing(self):
        self.editing = False
        self.stack.setCurrentWidget(self.button)
        self.editor.setText(self._value)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.setText(self._value)

    def eventFilter(self, watched, event):
        if watched is self.editor and event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Escape:
            self.cancel_editing()
            self.button.setFocus()
            return True
        if watched is self.button:
            if event.type() in (QEvent.Type.Enter, QEvent.Type.FocusIn):
                self.button.setIcon(icon("edit"))
            elif event.type() in (QEvent.Type.Leave, QEvent.Type.FocusOut):
                from PySide6.QtGui import QIcon
                self.button.setIcon(QIcon())
            elif event.type() == QEvent.Type.KeyPress and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self.start_editing()
                return True
        return super().eventFilter(watched, event)
