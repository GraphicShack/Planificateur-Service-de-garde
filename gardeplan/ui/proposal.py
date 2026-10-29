"""An explicit before/after view, reused by full generation and local repair."""
from copy import deepcopy
from PySide6.QtCore import Qt,QTimer
from PySide6.QtWidgets import (
    QAbstractItemView,QDialog,QDialogButtonBox,QHeaderView,QLabel,QTabWidget,
    QTableWidget,QTableWidgetItem,QVBoxLayout,QWidget,
)
from ..alerts import visible_alerts
from ..comparison import compare,describe_shift
from ..models import totals,format_duration
from .appearance import set_themed_style
from .calendar import CalendarWidget
from .theme import EDITOR_STYLE


def table(headers):
    widget=QTableWidget(0,len(headers))
    widget.setHorizontalHeaderLabels(headers)
    widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    widget.verticalHeader().hide()
    widget.verticalHeader().setMinimumSectionSize(44)
    widget.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    widget.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    widget.setWordWrap(True)
    return widget


class ProposalDialog(QDialog):
    def __init__(self,before,result,parent=None,focus=None):
        super().__init__(parent)
        self.before,self.after=deepcopy(before),deepcopy(result.proposal)
        self.changes=compare(self.before,self.after)
        self.setObjectName('editorDialog')
        set_themed_style(self,EDITOR_STYLE)
        self.setWindowTitle('Comparer avant d’appliquer la correction' if result.status=='repair' else 'Comparer avant d’appliquer la proposition')
        self.setMinimumSize(600,480)
        screen=self.screen().availableGeometry()
        self.resize(min(1160,screen.width()-30),min(850,screen.height()-40))
        layout=QVBoxLayout(self);layout.setContentsMargins(18,18,18,18);layout.setSpacing(10)
        heading=QLabel('Vérifiez les changements');heading.setObjectName('editorHeading');layout.addWidget(heading)
        message=QLabel(result.message);message.setWordWrap(True);layout.addWidget(message)
        prior=visible_alerts(self.before);later=visible_alerts(self.after)
        self.error_count=sum(i.severity=='error' for i in later)
        self.summary=QLabel(f"{len(self.changes)} changement(s) · {sum(i.severity=='error' for i in prior)} erreur(s) avant → {self.error_count} après · {format_duration(sum(totals(self.before).values()))} → {format_duration(sum(totals(self.after).values()))} planifiées")
        self.summary.setWordWrap(True);layout.addWidget(self.summary)
        self.tabs=QTabWidget();layout.addWidget(self.tabs,1)
        comparison=QWidget();column=QVBoxLayout(comparison);column.setContentsMargins(0,8,0,0)
        hint=QLabel('Sélectionnez un changement puis appuyez sur Entrée pour le voir dans la grille. Aucun horaire ne change avant votre confirmation.')
        hint.setWordWrap(True);column.addWidget(hint)
        self.changes_table=table(['Éducatrice','Changement','Avant','Après'])
        self.changes_table.setAccessibleName('Comparaison des quarts avant et après')
        people={e.id:e.name for e in self.before.educators+self.after.educators}
        for change in self.changes:
            row=self.changes_table.rowCount();self.changes_table.insertRow(row)
            values=[people.get(change.educator_id,'Profil inconnu'),change.label+'\n'+('+' if change.delta>0 else '')+format_duration(change.delta),
                    describe_shift(self.before,change.before),describe_shift(self.after,change.after)]
            for col,value in enumerate(values):self.changes_table.setItem(row,col,QTableWidgetItem(value))
        self.changes_table.resizeRowsToContents()
        column.addWidget(self.changes_table,1)
        if not self.changes:column.addWidget(QLabel('Aucun quart modifié.'))
        self.changes_table.cellActivated.connect(lambda row,col:self.locate_change(row))
        self.tabs.addTab(comparison,'Changements')
        self.hours_table=table(['Éducatrice','Avant','Après','Écart'])
        self.hours_table.setAccessibleName('Heures rémunérées par éducatrice avant et après')
        old,new=totals(self.before),totals(self.after)
        for person in sorted(self.after.educators,key=lambda p:(p.seniority,p.name)):
            if not person.active and not old.get(person.id,0) and not new.get(person.id,0):continue
            row=self.hours_table.rowCount();self.hours_table.insertRow(row)
            delta=new.get(person.id,0)-old.get(person.id,0)
            for col,value in enumerate([person.name,format_duration(old.get(person.id,0)),format_duration(new.get(person.id,0)),('+' if delta>0 else '')+format_duration(delta)]):
                self.hours_table.setItem(row,col,QTableWidgetItem(value))
        self.tabs.addTab(self.hours_table,'Heures')
        self.calendars=[]
        for label,plan in [('Actuel',self.before),('Proposition',self.after)]:
            calendar=CalendarWidget();calendar.single_service=bool(plan.planning_date);calendar.grouped_staff=bool(plan.planning_date)
            calendar.show_activities=False;calendar.set_week(plan,0,visible_alerts(plan));calendar.set_mode('Jour');calendar.set_read_only(True)
            if focus is not None:calendar.highlight_interval(focus.day,focus.start,focus.end)
            self.calendars.append(calendar);self.tabs.addTab(calendar,label)
        self.tabs.currentChanged.connect(lambda _:QTimer.singleShot(0,self.fit_calendar))
        details=QWidget();details_layout=QVBoxLayout(details)
        alerts=QLabel(f"{len(prior)} alerte(s) avant · {len(later)} après. Les préférences non satisfaites restent des avertissements.")
        alerts.setWordWrap(True);details_layout.addWidget(alerts)
        for text in result.diagnostics:
            label=QLabel(text);label.setWordWrap(True);details_layout.addWidget(label)
        details_layout.addStretch();self.tabs.addTab(details,'Détails')
        if self.error_count:
            warning=QLabel(f"La proposition conserve {self.error_count} erreur(s). Elle restera en brouillon et ne pourra pas être publiée avant correction.")
            warning.setWordWrap(True);warning.setStyleSheet('color:#982D24;');layout.addWidget(warning)
        buttons=QDialogButtonBox()
        buttons.addButton('Conserver l’horaire actuel',QDialogButtonBox.ButtonRole.RejectRole)
        self.apply_button=buttons.addButton('Appliquer au brouillon' if self.error_count else 'Appliquer cette proposition',QDialogButtonBox.ButtonRole.AcceptRole)
        for button in buttons.buttons():button.setMinimumHeight(44)
        buttons.accepted.connect(self.accept);buttons.rejected.connect(self.reject);layout.addWidget(buttons)

    def fit_calendar(self):
        calendar=self.tabs.currentWidget()
        if calendar not in self.calendars:return
        height=max(120,calendar.scroll.viewport().height()-14)
        factor=max(.15,min(2.,height/max(1,calendar.end_minute-calendar.start_minute)/1.65))
        calendar.set_zoom(factor);calendar.scroll_to(calendar.start_minute)

    def locate_change(self,row):
        if not 0<=row<len(self.changes):return
        change=self.changes[row];shift=change.after or change.before
        calendar=self.calendars[1 if change.after else 0]
        self.tabs.setCurrentWidget(calendar)
        QTimer.singleShot(0,lambda:calendar.highlight_interval(shift.day,shift.start,shift.end))
