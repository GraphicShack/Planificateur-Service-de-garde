"""Shared Atelier colours; text pairs are checked against WCAG AA."""
FOREST = "#214F40"
TEXT = "#203D32"
SECONDARY = "#52655E"
BORDER = "#64786D"
SURFACE = "#FFFFFF"
SOFT = "#F0F5F2"
HOVER = "#DFEBE4"
FOCUS = "#173F32"


def light_palette():
    """Keep native editor surfaces readable even when the OS uses dark mode."""
    from PySide6.QtGui import QColor, QPalette
    palette = QPalette()
    for role, color in (
        (QPalette.ColorRole.Window, "#F7F9F8"),
        (QPalette.ColorRole.WindowText, TEXT),
        (QPalette.ColorRole.Base, SURFACE),
        (QPalette.ColorRole.AlternateBase, SOFT),
        (QPalette.ColorRole.Text, TEXT),
        (QPalette.ColorRole.Button, SURFACE),
        (QPalette.ColorRole.ButtonText, TEXT),
        (QPalette.ColorRole.Highlight, FOREST),
        (QPalette.ColorRole.HighlightedText, SURFACE),
        (QPalette.ColorRole.ToolTipBase, FOREST),
        (QPalette.ColorRole.ToolTipText, SURFACE),
        (QPalette.ColorRole.PlaceholderText, SECONDARY),
    ):
        palette.setColor(role, QColor(color))
    return palette


EDITOR_STYLE = f"""
QDialog#editorDialog {{ background:#F7F9F8; color:{TEXT}; }}
QDialog#editorDialog QWidget {{ color:{TEXT}; font-family:'Segoe UI','SF Pro Text','Noto Sans',sans-serif; font-size:16px; }}
QDialog#editorDialog QWidget#editorBody {{ background:#F7F9F8; }}
QDialog#editorDialog QScrollArea {{ background:#F7F9F8; border:0; }}
QDialog#editorDialog QFrame#formSection {{ background:{SURFACE}; border:1px solid #DCE4DF; border-radius:10px; }}
QDialog#editorDialog QLabel {{ background:transparent; }}
QDialog#editorDialog QLabel#editorHeading {{ font-size:24px; font-weight:700; }}
QDialog#editorDialog QLabel#formSectionTitle {{ font-size:17px; font-weight:700; }}
QDialog#editorDialog QLabel#formHint {{ font-size:14px; color:{SECONDARY}; }}
QDialog#editorDialog QLineEdit, QDialog#editorDialog QSpinBox,
QDialog#editorDialog QComboBox, QDialog#editorDialog QTextEdit {{
 background:{SURFACE}; color:{TEXT}; border:1px solid {BORDER};
 border-radius:6px; padding:7px; min-height:26px;
 selection-background-color:{FOREST}; selection-color:white;
}}
QDialog#editorDialog QLineEdit:focus, QDialog#editorDialog QSpinBox:focus,
QDialog#editorDialog QComboBox:focus, QDialog#editorDialog QTextEdit:focus {{ border:2px solid {FOCUS}; padding:6px; }}
QDialog#editorDialog QAbstractItemView {{ background:{SURFACE}; color:{TEXT}; font-size:16px; selection-background-color:{HOVER}; selection-color:{TEXT}; }}
QDialog#editorDialog QHeaderView::section {{ background:{SOFT}; color:{TEXT}; font-size:14px; padding:8px; border:0; }}
QDialog#editorDialog QPushButton {{ background:{SURFACE}; color:{TEXT}; font-size:16px; border:1px solid {BORDER}; border-radius:7px; padding:8px 12px; min-height:26px; }}
QDialog#editorDialog QPushButton:hover {{ background:{HOVER}; }}
QDialog#editorDialog QPushButton:focus {{ border:2px solid {FOCUS}; padding:7px 11px; }}
QDialog#editorDialog QPushButton#editorSave {{ background:{FOREST}; color:white; border-color:{FOREST}; font-weight:600; }}
QDialog#editorDialog QCheckBox {{ spacing:8px; }}
QDialog#editorDialog QTabWidget::pane {{ background:{SURFACE}; border:1px solid #DCE4DF; }}
QDialog#editorDialog QTabBar::tab {{ background:{SOFT}; color:{SECONDARY}; padding:12px; }}
QDialog#editorDialog QTabBar::tab:selected {{ background:{SURFACE}; color:{TEXT}; }}
"""


def contrast(foreground, background):
    def luminance(value):
        channels = [int(value[i:i+2], 16)/255 for i in (1, 3, 5)]
        linear = [c/12.92 if c <= .04045 else ((c+.055)/1.055)**2.4 for c in channels]
        return sum(a*b for a, b in zip(linear, (.2126, .7152, .0722)))
    a, b = sorted((luminance(foreground), luminance(background)))
    return (b+.05)/(a+.05)


DATE_STYLE = f"""
QDialog#dayPicker {{ background:{SURFACE}; }}
QDialog#dayPicker QLabel {{ color:{TEXT}; font-size:16px; }}
QDialog#dayPicker QComboBox, QDialog#dayPicker QSpinBox {{
 background:{SURFACE}; color:{TEXT}; font-size:20px; font-weight:700;
 border:1px solid {BORDER}; border-radius:8px; padding:6px; min-height:32px;
}}
QDialog#dayPicker QComboBox QAbstractItemView {{ font-size:18px; color:{TEXT}; background:{SURFACE}; selection-color:white; selection-background-color:{FOREST}; }}
QDialog#dayPicker QPushButton {{ font-size:16px; color:{TEXT}; background:{SURFACE}; border:1px solid {BORDER}; border-radius:8px; min-height:32px; padding:6px 12px; }}
QDialog#dayPicker QPushButton:hover {{ background:{HOVER}; }}
QDialog#dayPicker QPushButton:focus, QDialog#dayPicker QComboBox:focus, QDialog#dayPicker QSpinBox:focus {{ border:2px solid {FOCUS}; }}
QDialog#dayPicker QPushButton:disabled {{ color:{SECONDARY}; background:{SOFT}; }}
QPushButton#dateSelector {{ color:{TEXT}; background:{SURFACE}; font-size:16px; font-weight:600; padding:8px 12px; border:1px solid {BORDER}; border-radius:8px; }}
QPushButton#dateSelector:hover {{ background:{HOVER}; }}
QPushButton#dateSelector:focus {{ border:2px solid {FOCUS}; }}
QPushButton#dateArrow {{ color:{TEXT}; background:{SURFACE}; border:1px solid {BORDER}; border-radius:8px; padding:0; }}
QPushButton#dateArrow:hover {{ background:{HOVER}; }}
QPushButton#dateArrow:focus {{ border:2px solid {FOCUS}; }}
QPushButton#dateAction {{ color:{TEXT}; background:{SURFACE}; font-size:16px; min-height:30px; padding:8px 12px; border:1px solid {BORDER}; border-radius:8px; }}
QPushButton#dateAction:focus {{ border:2px solid {FOCUS}; }}
"""
