"""Wrap controls without shrinking their fonts or hit areas."""
from PySide6.QtCore import Qt, QRect, QSize
from PySide6.QtWidgets import QLayout


class FlowLayout(QLayout):
    def __init__(self, parent=None, spacing=12, push_last=0):
        super().__init__(parent)
        self.items = []
        self.push_last = push_last
        self.setContentsMargins(0, 0, 0, 0)
        self.setSpacing(spacing)

    def addItem(self, item):
        self.items.append(item)

    def count(self):
        return len(self.items)

    def itemAt(self, index):
        return self.items[index] if 0 <= index < len(self.items) else None

    def takeAt(self, index):
        return self.items.pop(index) if 0 <= index < len(self.items) else None

    def expandingDirections(self):
        return Qt.Orientation.Horizontal

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._arrange(QRect(0, 0, width, 0), False)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._arrange(rect, True)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        result = QSize()
        for item in self.items:
            result = result.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        return result+QSize(margins.left()+margins.right(), margins.top()+margins.bottom())

    def _arrange(self, rect, apply):
        original_top = rect.y()
        margins = self.contentsMargins()
        rect = rect.adjusted(margins.left(), margins.top(), -margins.right(), -margins.bottom())
        x, y, line = rect.x(), rect.y(), 0
        gap = self.spacing()
        sizes = [item.sizeHint().expandedTo(item.minimumSize()) for item in self.items]
        spare = max(0, rect.width()-sum(s.width() for s in sizes)-max(0, len(sizes)-1)*gap)
        for index, (item, size) in enumerate(zip(self.items, sizes)):
            if x > rect.x() and x+size.width() > rect.x()+rect.width():
                x, y, line = rect.x(), y+line+gap, 0
            if self.push_last and index == len(sizes)-self.push_last:
                x += spare
            if apply:
                item.setGeometry(QRect(x, y, size.width(), size.height()))
            x += size.width()+gap
            line = max(line, size.height())
        return y+line-original_top+margins.bottom()
