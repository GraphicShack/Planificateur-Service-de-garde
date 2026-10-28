"""A single count with a live explanation of the actual SDG staffing rule."""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDialog, QWidget, QPushButton, QVBoxLayout, QFormLayout, QLabel, QSizePolicy
from .forms import integer
from .theme import EDITOR_STYLE, light_palette
from .appearance import set_themed_style
from ..planning import service_ratio
from ..coverage import coverage_timeline


class EnrolmentPanel(QWidget):
    accepted = Signal()
    rejected = Signal()

    def __init__(self, week, parent=None):
        super().__init__(parent)
        self.setObjectName("editorDialog")
        self.setWindowTitle("Inscriptions de la journée")
        self.setPalette(light_palette())
        set_themed_style(self, EDITOR_STYLE.replace("QDialog#editorDialog", "QWidget#editorDialog"))
        self.week = week
        self.ratio = service_ratio(week)
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        title = QLabel("Inscriptions de la journée")
        title.setObjectName("editorHeading")
        title.setWordWrap(True)
        title.setStyleSheet("font-size:18px;font-weight:700;")
        root.addWidget(title)
        self.count = integer(max((p.students for p in coverage_timeline(week)), default=0), 0, 10000, " enfants")
        self.count.setMinimumHeight(44)
        self.count.setAccessibleName("Nombre d'enfants inscrits")
        root.addWidget(QLabel("Nombre d’enfants"))
        root.addWidget(self.count)
        self.preview = QLabel()
        self.preview.setWordWrap(True)
        self.preview.setAccessibleName("Besoin calculé en direct")
        root.addWidget(self.preview)
        self.explanation = QLabel()
        self.explanation.setWordWrap(True)
        root.addWidget(self.explanation)
        root.addStretch()
        self.save_button = QPushButton("Enregistrer")
        self.save_button.setObjectName("editorSave")
        self.save_button.setMinimumHeight(44)
        self.save_button.clicked.connect(lambda: self.accepted.emit())
        root.addWidget(self.save_button)
        back = QPushButton("Retour à l’équipe")
        back.setMinimumHeight(44)
        back.clicked.connect(lambda: self.rejected.emit())
        root.addWidget(back)
        # Qt6 on Windows retains large native size hints in a scroll area.
        # Let the viewport determine width; wrapped labels retain heightForWidth.
        for control in self.findChildren(QLabel) + [self.count, self.save_button, back]:
            policy = control.sizePolicy()
            policy.setHorizontalPolicy(QSizePolicy.Policy.Ignored)
            control.setSizePolicy(policy)
            control.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.count.valueChanged.connect(self.update_preview)
        self.update_preview()

    def update_preview(self):
        from ..staffing import staffing_description
        self.explanation.setText(staffing_description(self.week)+" Avec zéro inscription, la journée est fermée.")
        count = self.count.value()
        from ..planning import plan_pedagogical_day
        prepared=plan_pedagogical_day(self.week,0,count,20)
        required=max((p.required for p in coverage_timeline(prepared)),default=0) if count else 0
        self.preview.setText(f"{count} enfants → ratio 1/{self.ratio} → minimum {required} éducatrices simultanées" if count else "0 enfant → journée fermée → aucune éducatrice requise")

    def load_week(self, week):
        self.week = week
        self.ratio = service_ratio(week)
        self.count.setValue(max((p.students for p in coverage_timeline(week)), default=0))
        self.update_preview()


class EnrolmentDialog(QDialog):
    """Compatibility wrapper; the planner uses the embedded panel directly."""
    def __init__(self, week, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Inscriptions de la journée")
        self.panel = EnrolmentPanel(week, self)
        layout = QVBoxLayout(self)
        layout.addWidget(self.panel)
        self.count, self.preview = self.panel.count, self.panel.preview
        self.panel.accepted.connect(self.accept)
        self.panel.rejected.connect(self.reject)
