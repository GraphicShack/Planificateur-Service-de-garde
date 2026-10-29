"""Readable, scrollable report; no opaque quality score."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView,QFrame,QHeaderView,QLabel,QScrollArea,
                              QTableWidget,QTableWidgetItem,QVBoxLayout,QWidget)
from ..models import format_duration
from ..proposal_summary import proposal_summary


class ProposalReport(QScrollArea):
    def __init__(self,before,after,parent=None):
        super().__init__(parent)
        self.report=proposal_summary(before,after)
        report=self.report;a=report['before'];b=report['after']
        self.setWidgetResizable(True);self.setFrameShape(QFrame.Shape.NoFrame)
        body=QWidget();layout=QVBoxLayout(body);layout.setContentsMargins(10,10,10,10);layout.setSpacing(12)
        self.setWidget(body)
        self.metrics=QTableWidget(0,3)
        self.metrics.setAccessibleName('Bilan de l’horaire actuel et de la proposition')
        self.metrics.setHorizontalHeaderLabels(['Indicateur','Actuel','Proposition'])
        self.metrics.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.metrics.verticalHeader().hide();self.metrics.verticalHeader().setMinimumSectionSize(44)
        self.metrics.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.metrics.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.metrics.setWordWrap(True)
        self.metrics.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        def preferences(value):
            return f'{value.preferences_met} / {value.preferences_total}' if value.preferences_total else 'Aucune définie'
        rows=[('Couverture des groupes',a.coverage,b.coverage),('Erreurs bloquantes',str(a.errors),str(b.errors)),
              ('Avertissements',str(a.warnings),str(b.warnings)),('Heures rémunérées',format_duration(a.paid),format_duration(b.paid)),
              ('Personnes avec un horaire coupé',str(len(a.split_names)),str(len(b.split_names))),
              ('Interruptions entre deux quarts',str(a.interruptions),str(b.interruptions)),
              ('Préférences respectées',preferences(a),preferences(b)),
              ('Personnes actives sans heures',str(len(a.without_hours)),str(len(b.without_hours))),
              ('Quarts verrouillés conservés',str(report['locks_total']),f"{report['locks_preserved']} / {report['locks_total']}")]
        for values in rows:
            row=self.metrics.rowCount();self.metrics.insertRow(row)
            for col,value in enumerate(values):self.metrics.setItem(row,col,QTableWidgetItem(value))
            self.metrics.setRowHeight(row,48)
        self.metrics.setFixedHeight(48*len(rows)+48)
        layout.addWidget(self.metrics)
        def text(value):
            label=QLabel(value);label.setWordWrap(True);label.setTextFormat(Qt.TextFormat.PlainText);layout.addWidget(label)
        text(f"Changements : {report['added']} ajout(s), {report['removed']} retrait(s), {report['modified']} modification(s).")
        text('Personnes sans heures dans la proposition : '+(', '.join(b.without_hours) if b.without_hours else 'aucune')+'.')
        text('Horaires coupés dans la proposition : '+(', '.join(b.split_names) if b.split_names else 'aucun')+'.')
        text('Les préférences sont comptées par souhait, pour les personnes planifiées. Les absences à la journée sont exclues des personnes sans heures. Une pause dans un quart n’est pas un horaire coupé.')
        if b.preference_messages:
            text('Préférences non satisfaites :')
            for message in b.preference_messages:text('• '+message)
        if report['locks_preserved']!=report['locks_total']:
            text('Un quart verrouillé a changé ou a été retiré. Cette proposition ne peut pas être appliquée.')
        layout.addStretch()
