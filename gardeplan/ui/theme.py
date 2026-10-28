"""Shared Atelier colours; text pairs are checked against WCAG AA."""
FOREST = "#214F40"
TEXT = "#203D32"
SECONDARY = "#52655E"
BORDER = "#64786D"
SURFACE = "#FFFFFF"
SOFT = "#F0F5F2"
HOVER = "#DFEBE4"
FOCUS = "#173F32"


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
QDialog#dayPicker QPushButton#todayButton {{ color:white; background:{FOREST}; font-weight:600; }}
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
