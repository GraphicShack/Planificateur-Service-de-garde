"""A single count with a live explanation of the actual SDG staffing rule."""
from PySide6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLabel, QDialogButtonBox
from .forms import integer
from .theme import EDITOR_STYLE, light_palette
from ..planning import service_ratio
from ..coverage import coverage_timeline


class EnrolmentDialog(QDialog):
    def __init__(self, week, parent=None):
        super().__init__(parent)
        self.setObjectName("editorDialog")
        self.setWindowTitle("Inscriptions de la journée")
        self.setPalette(light_palette())
        self.setStyleSheet(EDITOR_STYLE)
        self.setMinimumWidth(480)
        self.resize(580, 370)
        self.ratio = service_ratio(week)
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        title = QLabel("Inscriptions de la journée")
        title.setObjectName("editorHeading")
        root.addWidget(title)
        form = QFormLayout()
        self.count = integer(max((p.students for p in coverage_timeline(week)), default=0), 0, 10000, " enfants")
        self.count.setMinimumHeight(44)
        self.count.setAccessibleName("Nombre d'enfants inscrits")
        form.addRow("Nombre d’enfants", self.count)
        root.addLayout(form)
        self.preview = QLabel()
        self.preview.setWordWrap(True)
        self.preview.setAccessibleName("Besoin calculé en direct")
        root.addWidget(self.preview)
        explanation = QLabel("Dès que des enfants sont accueillis, au moins deux éducatrices doivent être présentes simultanément, même avec moins de vingt enfants. Le ratio peut exiger davantage de personnes. Avec zéro inscription, la journée est fermée.")
        explanation.setWordWrap(True)
        root.addWidget(explanation)
        root.addStretch()
        buttons = QDialogButtonBox()
        buttons.addButton("Annuler", QDialogButtonBox.ButtonRole.RejectRole)
        save = buttons.addButton("Appliquer les inscriptions", QDialogButtonBox.ButtonRole.AcceptRole)
        save.setObjectName("editorSave")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)
        self.count.valueChanged.connect(self.update_preview)
        self.update_preview()

    def update_preview(self):
        count = self.count.value()
        required = max(2, (count+self.ratio-1)//self.ratio) if count else 0
        self.preview.setText(f"{count} enfants → ratio 1/{self.ratio} → minimum {required} éducatrices simultanées" if count else "0 enfant → journée fermée → aucune éducatrice requise")
