"""Coverage gutter, sharing the calendar's time geometry and vertical scroll."""
from PySide6.QtCore import Qt, Signal, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QFont
from PySide6.QtWidgets import QWidget
from ..coverage import merged_coverage, coverage_state, coverage_counts
from ..models import format_time


class CoverageBand(QWidget):
    interval_selected = Signal(int, int)
    details_changed = Signal(str)

    def __init__(self, calendar, parent=None):
        super().__init__(parent)
        self.calendar = calendar
        self.setFixedWidth(184)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.setAccessibleName('Couverture verticale du service de garde')
        self.segments = []
        self.selected = -1
        self.label_areas = {}

    def set_week(self, week, day):
        self.segments = merged_coverage(week, day)
        self.selected = -1
        self.label_areas = {}
        self.setAccessibleDescription('Haut/bas : parcourir les plages. Entrée ou Espace : sélectionner et surligner la plage. Chaque état comporte un libellé.')
        self.update()

    def _label(self, part):
        state = coverage_state(part)[1]
        return f'{format_time(part.start)} – {format_time(part.end)}\n{coverage_counts(part)} · {state}'

    def _select(self, index, activate=False):
        if not self.segments:
            return
        self.selected = max(0, min(index, len(self.segments)-1))
        part = self.segments[self.selected]
        label = self._label(part)
        self.details_changed.emit(label)
        self.setAccessibleDescription(label+'\nHaut/bas : parcourir. Entrée : surligner.')
        self.update()
        if activate:
            self.interval_selected.emit(part.start, part.end)

    def highlight_interval(self, start, end):
        index = next((i for i,p in enumerate(self.segments) if p.start < end and start < p.end), None)
        if index is not None:
            self._select(index)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor('#F7FAF8'))
        offset = self.calendar.scroll.verticalScrollBar().value()
        font = QFont('Segoe UI')
        font.setPixelSize(13)
        painter.setFont(font)
        colors = {'shortage':('#FCEDEC','#952E28'), 'exact':('#E9F3ED','#214F40'),
                  'surplus':('#F0F2F1','#46534D'), 'closed':('#F0F2F1','#46534D')}
        visible = []
        for index, part in enumerate(self.segments):
            top = self.calendar.y(part.start)-offset
            height = (part.end-part.start)*self.calendar.scale
            if top+height < 0 or top > self.height():
                continue
            kind, state = coverage_state(part)
            background, foreground = colors[kind]
            rect = QRectF(4, top, self.width()-8, max(1, height))
            painter.fillRect(rect, QColor(background))
            painter.fillRect(QRectF(rect.left(), rect.top(), 4, rect.height()), QColor(foreground))
            painter.setPen(QPen(QColor('#173F32' if index == self.selected else '#CBD5CF'), 2 if index == self.selected else 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect)
            visible.append((index, part, rect, foreground, state))
        # The state strip keeps exact time geometry. Readable annotations may
        # extend around very short spans, with a leader to the actual interval.
        occupied = []
        self.label_areas = {}
        self._label_offset = offset
        for index, part, rect, foreground, state in sorted(visible, key=lambda row: (row[0] != self.selected, -row[2].height())):
            top, bottom = max(0,rect.top()), min(self.height(),rect.bottom())
            preferred = max(2,min(self.height()-58,(top+bottom)/2-28))
            candidates = [preferred]
            for previous in occupied:
                candidates.extend((previous.bottom()+4, previous.top()-60))
            choices = [QRectF(13,y,self.width()-22,56) for y in candidates
                       if 0 <= y <= self.height()-56]
            area = next((candidate for candidate in choices if not any(candidate.intersects(old) for old in occupied)), None)
            painter.setPen(QColor(foreground))
            if area is not None:
                occupied.append(area)
                self.label_areas[index] = area
                if rect.height() < 64:
                    painter.drawLine(QPointF(rect.left()+5,rect.center().y()),QPointF(area.left()-1,area.center().y()))
                text = f'{format_time(part.start)} – {format_time(part.end)}\n{coverage_counts(part)}\n{state}'
                painter.drawText(area, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,text)
            else:
                painter.drawText(QRectF(13,(top+bottom)/2-9,self.width()-22,18),Qt.AlignmentFlag.AlignVCenter,state)

    def _index_at(self, position):
        offset = self.calendar.scroll.verticalScrollBar().value()
        if getattr(self,'_label_offset',None) == offset:
            match = next((index for index, area in self.label_areas.items() if area.contains(position)), None)
            if match is not None:
                return match
        minute = (position.y()+offset)/self.calendar.scale+self.calendar.start_minute
        return next((i for i,p in enumerate(self.segments) if p.start <= minute < p.end), None)

    def focusInEvent(self, event):
        super().focusInEvent(event)
        if self.selected < 0 and self.segments:
            self._select(0)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            index = self._index_at(event.position())
            if index is not None:
                self.setFocus()
                self._select(index, activate=True)
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        index = self._index_at(event.position())
        self.setToolTip(self._label(self.segments[index]) if index is not None else '')
        super().mouseMoveEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Up,Qt.Key.Key_Down,Qt.Key.Key_Home,Qt.Key.Key_End):
            index = self.selected if self.selected >= 0 else 0
            index = 0 if event.key() == Qt.Key.Key_Home else len(self.segments)-1 if event.key() == Qt.Key.Key_End else index+(1 if event.key() == Qt.Key.Key_Down else -1)
            self._select(index, activate=True)
            return
        if event.key() in (Qt.Key.Key_Return,Qt.Key.Key_Enter,Qt.Key.Key_Space):
            self._select(max(0,self.selected), activate=True)
            return
        super().keyPressEvent(event)
