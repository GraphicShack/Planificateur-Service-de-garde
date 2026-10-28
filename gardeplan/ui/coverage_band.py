"""Keyboard-accessible, horizontally scrollable quarter-hour coverage ribbon."""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QScrollArea, QFrame
from ..coverage import quarter_hour_coverage
from ..models import format_time


class CoverageBand(QWidget):
    interval_selected = Signal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAccessibleName("Couverture par tranche de quinze minutes")
        root = QHBoxLayout(self)
        root.setContentsMargins(8, 4, 8, 4)
        label = QLabel("Ratio\n15 min")
        label.setStyleSheet("font-size:12px;color:#203D32;font-weight:600;")
        root.addWidget(label)
        self.scroll = QScrollArea()
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setWidgetResizable(True)
        self.content = QWidget()
        self.row = QHBoxLayout(self.content)
        self.row.setContentsMargins(0, 0, 0, 0)
        self.row.setSpacing(4)
        self.scroll.setWidget(self.content)
        self.setFixedHeight(94)
        root.addWidget(self.scroll, 1)
        self.cells = []
        self.slices = []

    def set_week(self, week, day):
        self.slices = quarter_hour_coverage(week, day)
        while len(self.cells) > len(self.slices):
            cell = self.cells.pop()
            self.row.removeWidget(cell)
            cell.deleteLater()
        for index, part in enumerate(self.slices):
            if index == len(self.cells):
                cell = QPushButton()
                cell.setMinimumSize(96, 56)
                cell.clicked.connect(lambda checked=False, i=index: self.interval_selected.emit(self.slices[i].start, self.slices[i].end))
                self.row.addWidget(cell)
                self.cells.append(cell)
            cell = self.cells[index]
            state = "Fermé" if not part.required else "OK" if part.complete else "Manque"
            text = f"{format_time(part.start)} –\n{format_time(part.end)} · {part.actual}/{part.required}\n{state}"
            cell.setText(text)
            cell.setAccessibleName(f"{format_time(part.start)} à {format_time(part.end)} : {part.actual} éducatrices présentes pour {part.required} requises. {state}.")
            cell.setToolTip(cell.accessibleName())
            background, foreground = ("#E9F3ED", "#214F40") if part.complete else ("#FCEDEC", "#952E28")
            cell.setProperty("selected", False)
            cell.setStyleSheet(f'QPushButton{{font-size:12px;background:{background};color:{foreground};border:1px solid {foreground};border-radius:5px;padding:4px;}} QPushButton:focus,QPushButton[selected="true"]{{border:3px solid #173F32;padding:2px;}}')

    def highlight_interval(self, start, end):
        first = None
        for cell, part in zip(self.cells, self.slices):
            selected = part.start < end and start < part.end
            cell.setProperty("selected", selected)
            cell.style().unpolish(cell)
            cell.style().polish(cell)
            if selected and first is None:
                first = cell
        if first:
            self.scroll.horizontalScrollBar().setValue(max(0, first.x()-12))
