"""Icônes vectorielles locales, sans police d'icônes ni accès réseau."""
from pathlib import Path

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

LOGO_PATH = Path(__file__).resolve().parent.parent / "assets" / "logo.svg"

_PATHS = {
    "calendar": '<rect x="3" y="5" width="18" height="16" rx="3"/><path d="M7 3v4m10-4v4M3 10h18m-13 4h2m4 0h2m-8 4h2"/>',
    "chevron-left": '<path d="m14 6-6 6 6 6"/>',
    "chevron-right": '<path d="m10 6 6 6-6 6"/>',
    "sparkles": '<path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5L12 3Zm7-1v4m-2-2h4"/>',
    "check": '<path d="m7 12 3 3 7-7"/><rect x="3" y="3" width="18" height="18" rx="5"/>',
    "save": '<path d="M5 3h12l4 4v12a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z"/><path d="M7 3v6h10V3M7 21v-7h10v7"/>',
    "download": '<path d="M12 3v12m-4-4 4 4 4-4M4 16v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "users": '<circle cx="9" cy="8" r="3"/><path d="M3 21v-2a6 6 0 0 1 12 0v2M16 5a3 3 0 0 1 0 6m3 10v-2a6 6 0 0 0-2-4"/>',
    "settings": '<path d="M4 6h16M4 12h16M4 18h16"/><circle cx="8" cy="6" r="2"/><circle cx="16" cy="12" r="2"/><circle cx="10" cy="18" r="2"/>',
    "undo": '<path d="M3 10h11a6 6 0 0 1 0 12M3 10l5-5m-5 5 5 5" transform="translate(0,-2)"/>',
    "redo": '<path d="M21 10H10a6 6 0 0 0 0 12m11-12-5-5m5 5-5 5" transform="translate(0,-2)"/>',
    "more": '<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>',
    "panel": '<rect x="3" y="4" width="18" height="16" rx="3"/><path d="M9 4v16"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "map-pin": '<path d="M19 10c0 5-7 11-7 11S5 15 5 10a7 7 0 0 1 14 0Z"/><circle cx="12" cy="10" r="2.5"/>',
    "search": '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
    "activity": '<path d="M3 12h4l3-8 4 16 3-8h4"/>',
    "edit": '<path d="m15 4 5 5M4 20l5-1L21 7a2 2 0 0 0-4-4L5 15l-1 5Z"/>',
    "alert": '<path d="m10 4-8 14a2 2 0 0 0 2 3h16a2 2 0 0 0 2-3L14 4a2 2 0 0 0-4 0Z"/><path d="M12 9v4m0 4h.01"/>',
    "folder": '<path d="M3 7V5a2 2 0 0 1 2-2h5l2 3h7a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7Z"/>',
}


def _render(renderer, size):
    size = max(8, int(size))
    pixmap = QPixmap(size * 2, size * 2)
    pixmap.setDevicePixelRatio(2.0)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()
    return pixmap


def icon(name, size=18, color="#60746C"):
    """Pictogramme local ; les noms inconnus restent discrets et non bloquants."""
    geometry = _PATHS.get(name, _PATHS["calendar"])
    # Colors are developer-provided Qt colors, never user text or remote SVG.
    from PySide6.QtGui import QColor
    selected = QColor(color)
    color = selected.name() if selected.isValid() else "#60746C"
    source = (f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" '
              f'viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.7" '
              f'stroke-linecap="round" stroke-linejoin="round">{geometry}</svg>')
    renderer = QSvgRenderer(QByteArray(source.encode("utf-8")))
    return QIcon(_render(renderer, size))


def logo_pixmap(size=44):
    return _render(QSvgRenderer(str(LOGO_PATH)), size)


def logo_icon():
    renderer = QSvgRenderer(str(LOGO_PATH))
    result = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        result.addPixmap(_render(renderer, size))
    return result
