"""Portable interface preferences, independent of schedules and educator colours."""
import json
import os
from pathlib import Path
import re
import tempfile

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QColorDialog, QComboBox, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QWidget,
)
from .theme import contrast

PRESETS = {"Forêt": "#214F40", "Bleu": "#245C85", "Prune": "#704366", "Ardoise": "#475569"}


def accessible_accent(value):
    """Custom accents always support white button text at WCAG AA contrast."""
    if not isinstance(value, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
        raise ValueError("Utilisez une couleur au format #RRGGBB, par exemple #245C85.")
    color = QColor(value)
    while contrast("#FFFFFF", color.name()) < 4.5:
        color = color.darker(105)
    return color.name().upper()


def _mix(value, white):
    color = QColor(value)
    return QColor(*(round(c * (1-white) + 255*white)
                    for c in (color.red(), color.green(), color.blue()))).name()


def replacements(accent):
    return {
        "#214f40": accent, "#173f32": QColor(accent).darker(125).name(),
        "#123f34": QColor(accent).darker(140).name(),
        "#2b5549": _mix(accent, .14), "#284b35": QColor(accent).darker(115).name(),
        "#dfebe4": _mix(accent, .89),
        "#eef4ec": _mix(accent, .94), "#eaf1e6": _mix(accent, .94),
        "#edf5f0": _mix(accent, .94), "#f0f7f3": _mix(accent, .96),
        "#d5e3dd": _mix(accent, .87), "#527b69": accent,
    }


def accent_color(value):
    app = QApplication.instance()
    accent = app.property("atelierAccent") if app else None
    return replacements(accent).get(value.lower(), value) if accent else value


def themed_css(source):
    return re.sub(r"#[0-9a-fA-F]{6}\b", lambda match: accent_color(match.group()), source)


def set_themed_style(widget, source):
    # Keep original tokens so repeated switching never transforms already-mapped colours.
    widget._atelier_css = source
    widget.setStyleSheet(themed_css(source))


class Appearance(QObject):
    changed = Signal()
    error = Signal(str)

    def __init__(self, window, motion, path):
        super().__init__(window)
        self.window, self.motion, self.path = window, motion, Path(path)
        self.preset, self.custom, self.problem = "Forêt", "#245C85", ""
        try:
            if self.path.stat().st_size <= 8192:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    if data.get("preset") in (*PRESETS, "Personnalisé"):
                        self.preset = data["preset"]
                    self.custom = accessible_accent(data.get("custom", self.custom))
                    if isinstance(data.get("animations"), bool):
                        motion.set_enabled(data["animations"])
        except (OSError, ValueError, TypeError):
            pass  # A damaged/missing preference file never prevents opening schedules.
        motion.changed.connect(lambda enabled: self.save())
        self.apply()

    @property
    def accent(self):
        return PRESETS.get(self.preset, self.custom)

    def choose(self, preset, custom=None):
        if preset not in (*PRESETS, "Personnalisé"):
            raise ValueError("Choisissez un thème de la liste.")
        color = accessible_accent(custom) if custom is not None else self.custom
        self.preset, self.custom = preset, color
        self.apply()
        self.save()
        self.changed.emit()

    def apply(self):
        from ..app import STYLE
        from .theme import light_palette
        QApplication.instance().setProperty("atelierAccent", self.accent)
        self.window.setStyleSheet(themed_css(STYLE))
        self.window.setPalette(light_palette())
        for widget in self.window.findChildren(QWidget):
            if hasattr(widget, "_atelier_css"):
                widget.setStyleSheet(themed_css(widget._atelier_css))
                widget.setPalette(light_palette())
            widget.update()

    def save(self):
        temporary = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.path.parent,
                                             prefix="interface-", suffix=".tmp", delete=False) as handle:
                temporary = Path(handle.name)
                json.dump({"version": 1, "preset": self.preset, "custom": self.custom,
                           "animations": self.motion.enabled}, handle)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
            self.problem = ""
        except OSError:
            self.problem = "Le choix est appliqué pour cette session, mais le dossier ne permet pas de l’enregistrer."
            self.error.emit(self.problem)
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass


class AppearancePanel(QWidget):
    """Live, keyboard accessible theme and motion controls in Display options."""
    def __init__(self, appearance, parent=None):
        super().__init__(parent)
        self.setStyleSheet("QComboBox,QLineEdit,QPushButton,QLabel,QCheckBox {font-size:16px;}")
        self.appearance = appearance
        layout = QFormLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        self.presets = QComboBox()
        self.presets.setMinimumHeight(44)
        self.presets.addItems([*PRESETS, "Personnalisé"])
        self.presets.setCurrentText(appearance.preset)
        self.presets.setAccessibleName("Thème de couleur de l’interface")
        layout.addRow("Thème de couleur", self.presets)
        self.custom_row = QWidget()
        row = QHBoxLayout(self.custom_row)
        row.setContentsMargins(0, 0, 0, 0)
        self.color = QLineEdit(appearance.custom)
        self.color.setMaxLength(7)
        self.color.setMinimumHeight(44)
        self.color.setAccessibleName("Couleur d’accent personnalisée au format hexadécimal")
        self.picker = QPushButton("Choisir une couleur…")
        self.picker.setMinimumHeight(44)
        row.addWidget(self.color, 1)
        row.addWidget(self.picker)
        layout.addRow("Accent personnalisé", self.custom_row)
        self.preview = QLabel()
        self.preview.setWordWrap(True)
        layout.addRow(self.preview)
        self.message = QLabel(appearance.problem)
        self.message.setWordWrap(True)
        self.message.setStyleSheet("color:#982D24;")
        layout.addRow(self.message)
        animations = QCheckBox("Animations discrètes")
        animations.setChecked(appearance.motion.enabled)
        animations.setMinimumHeight(44)
        animations.toggled.connect(appearance.motion.set_enabled)
        layout.addRow(animations)
        self.presets.currentTextChanged.connect(self._choose)
        self.color.editingFinished.connect(self._choose)
        self.picker.clicked.connect(self._pick)
        appearance.error.connect(self.message.setText)
        self._preview()

    def _preview(self):
        self.layout().setRowVisible(self.custom_row, self.presets.currentText() == "Personnalisé")
        accent = self.appearance.accent
        self.preview.setText(f"Accent : {accent} · Texte blanc, contraste {contrast('#FFFFFF', accent):.1f}:1. Les couleurs claires sont ajustées pour rester lisibles.")
        self.preview.setStyleSheet(f"background:{accent};color:white;padding:12px;border-radius:8px;")

    def _choose(self):
        try:
            self.appearance.choose(self.presets.currentText(),
                                   self.color.text() if self.presets.currentText() == "Personnalisé" else None)
            self.message.setText(self.appearance.problem)
            self._preview()
        except ValueError as error:
            self.message.setText(str(error))

    def _pick(self):
        selected = QColorDialog.getColor(QColor(self.color.text()), self, "Choisir la couleur d’accent")
        if selected.isValid():
            self.color.setText(selected.name().upper())
            self._choose()
