"""Accessible offline home page; all figures come from home_data."""
from datetime import date
from PySide6.QtCore import Qt, QDate, Signal, QSize
from PySide6.QtWidgets import (QWidget,QScrollArea,QFrame,QVBoxLayout,QHBoxLayout,QGridLayout,
    QLabel,QPushButton,QBoxLayout,QSizePolicy)
from ..home_data import recent_days
from .day_selector import full_date
from .flow_layout import FlowLayout
from .appearance import set_themed_style
from ..session_user import greeting

STYLE='''
QWidget#homeBody {background:#F7F9F8;color:#203D32;}
QWidget#homeBody QLabel,QWidget#homeBody QPushButton {font-size:16px;color:#203D32;}
QWidget#homeBody QFrame#homeCard {background:white;border:1px solid #D9E3DD;border-radius:16px;}
QWidget#homeBody QPushButton {background:white;border:1px solid #C7D5CC;border-radius:9px;padding:10px 14px;min-height:24px;}
QWidget#homeBody QPushButton:hover {background:#EDF5F0;}
QWidget#homeBody QPushButton:focus {border:2px solid #173F32;padding:9px 13px;}
QWidget#homeBody QPushButton#homePrimary {background:#214F40;color:white;border-color:#214F40;font-weight:700;}
QWidget#homeBody QPushButton#homeDay {text-align:left;padding:0;background:white;border:1px solid #D2DDD6;}
QWidget#homeBody QPushButton#homeDay[today='true'] {background:#F0F7F3;border:2px solid #214F40;}
QWidget#homeBody QPushButton#homeDay:focus {border:3px solid #173F32;}
QWidget#homeBody QLabel#homeTitle {font-size:32px;font-weight:700;}
QWidget#homeBody QLabel#homeSection {font-size:21px;font-weight:700;}
QWidget#homeBody QLabel#homeSecondary {color:#52655E;}
'''


def label(text, name='', parent=None):
    widget=QLabel(text,parent)
    widget.setWordWrap(True)
    widget.setObjectName(name)
    policy=widget.sizePolicy();policy.setHorizontalPolicy(QSizePolicy.Policy.Ignored)
    widget.setSizePolicy(policy)
    widget.setMinimumWidth(0)
    return widget


def button(text, callback, primary=False):
    widget=QPushButton(text)
    widget.setMinimumHeight(44)
    widget.clicked.connect(lambda _checked=False: callback())
    widget.setAccessibleName(text)
    if primary:widget.setObjectName('homePrimary')
    return widget


def card(title):
    widget=QFrame();widget.setObjectName('homeCard')
    layout=QVBoxLayout(widget);layout.setContentsMargins(20,20,20,20);layout.setSpacing(14)
    heading=label(title,'homeSection');layout.addWidget(heading)
    return widget,layout


def clear(layout):
    while layout.count():
        item=layout.takeAt(0)
        if item.widget():item.widget().deleteLater()
        elif item.layout():
            clear(item.layout())
            item.layout().deleteLater()


class Intro(QWidget):
    def sizeHint(self):return QSize(620,130)
    def minimumSizeHint(self):return QSize(0,120)


class DayButton(QPushButton):
    def __init__(self, brief, today, callback):
        super().__init__()
        self.setObjectName('homeDay');self.setProperty('today',today)
        self.setStyleSheet('QPushButton#homeDay{min-height:110px;}')
        policy=self.sizePolicy();policy.setHorizontalPolicy(QSizePolicy.Policy.Expanding);policy.setHeightForWidth(True);self.setSizePolicy(policy)
        self.setMinimumHeight(96)
        self.row=QBoxLayout(QBoxLayout.Direction.LeftToRight,self)
        self.row.setContentsMargins(16,14,16,14);self.row.setSpacing(12)
        text=QWidget();column=QVBoxLayout(text);column.setContentsMargins(0,0,0,0)
        title=label(brief.name);title.setStyleSheet('font-size:18px;font-weight:700;')
        details=f'{full_date(QDate.fromString(brief.date,"yyyy-MM-dd"))} · {brief.children} enfants · {brief.educators} éducatrices'
        if today:details+=' · '+brief.hours
        column.addWidget(title);column.addWidget(label(details,'homeSecondary'))
        self.row.addWidget(text,1)
        badge=label(brief.status)
        badge.setSizePolicy(QSizePolicy.Policy.Preferred,QSizePolicy.Policy.Preferred)
        badge.setMinimumWidth(100 if brief.alerts else 195)
        badge.setMaximumWidth(205)
        badge.setStyleSheet('background:#FFF0D8;color:#804500;padding:8px;border-radius:14px;font-weight:600;' if brief.alerts else 'background:#E7F2EC;color:#214F40;padding:8px;border-radius:14px;font-weight:600;')
        self.row.addWidget(badge)
        for child in self.findChildren(QWidget):child.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAccessibleName(f'{brief.name}. {details}. {brief.status}. Ouvrir la planification.')
        self.clicked.connect(lambda:callback(brief.date))
        self.brief=brief

    def sizeHint(self):return QSize(500,self.heightForWidth(max(300,self.width())))
    def minimumSizeHint(self):return QSize(0,110)
    def heightForWidth(self,width):return max(110,self.row.totalHeightForWidth(width)) if hasattr(self,"row") else 110

    def resizeEvent(self,event):
        super().resizeEvent(event)
        direction=QBoxLayout.Direction.TopToBottom if self.width()<520 else QBoxLayout.Direction.LeftToRight
        if self.row.direction()!=direction:
            self.row.setDirection(direction)
            self.updateGeometry()


class HomePage(QScrollArea):
    open_day=Signal(str)
    delete_day=Signal(str)
    new_day=Signal()
    create_today=Signal()
    previous_day=Signal()
    add_educator=Signal()
    edit_educator=Signal(str)

    def __init__(self,parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True);self.setFrameShape(QFrame.Shape.NoFrame)
        self.setAccessibleName('Accueil du service de garde')
        self.body=QWidget();self.body.setObjectName('homeBody');set_themed_style(self.body, STYLE)
        self.setWidget(self.body)
        root=QVBoxLayout(self.body);root.setContentsMargins(28,28,28,28);root.setSpacing(24)
        self.heading=QWidget();flow=QBoxLayout(QBoxLayout.Direction.LeftToRight,self.heading);flow.setContentsMargins(0,0,0,0);flow.setSpacing(20)
        self.heading_layout=flow
        intro=Intro();intro_box=QVBoxLayout(intro);intro_box.setContentsMargins(0,0,0,0)
        intro_box.addWidget(label('SERVICE DE GARDE','homeSecondary'))
        self.greeting=label(greeting(),'homeTitle')
        self.greeting.setTextFormat(Qt.TextFormat.PlainText)
        intro_box.addWidget(self.greeting)
        self.subtitle=label('','homeSecondary');intro_box.addWidget(self.subtitle)
        flow.addWidget(intro,1)
        self.new_button=button('Nouvelle journée pédagogique',self.new_day.emit,True);flow.addWidget(self.new_button)
        root.addWidget(self.heading)
        self.error=label('');self.error.setStyleSheet('color:#982D24;');self.error.hide();root.addWidget(self.error)
        self.cards=QWidget();self.grid=QGridLayout(self.cards);self.grid.setContentsMargins(0,0,0,0);self.grid.setSpacing(20)
        self.recent_card,self.recent_layout=card('Journées récentes')
        self.previous_button=button('Ouvrir une journée précédente',self.previous_day.emit)
        self.recent_layout.addWidget(self.previous_button)
        self.rows=QVBoxLayout();self.rows.setSpacing(12);self.recent_layout.addLayout(self.rows)
        self.recent_layout.addStretch()
        self.today_card,self.today_layout=card('Journée du jour')
        self.today_content=QVBoxLayout();self.today_layout.addLayout(self.today_content)
        self.team_card,self.team_layout=card("L’équipe")
        self.add_button=button('Ajouter',self.add_educator.emit);self.team_layout.addWidget(self.add_button)
        self.team_rows=QVBoxLayout();self.team_rows.setSpacing(8);self.team_layout.addLayout(self.team_rows)
        root.addWidget(self.cards)
        root.addStretch()
        self.days=[];self.day_buttons=[];self._narrow=None
        self._arrange()

    def _arrange(self):
        if not hasattr(self,"team_card"):return
        narrow=self.viewport().width()<1050
        if getattr(self,"_narrow",None)==narrow:return
        self._narrow=narrow
        self.heading_layout.setDirection(QBoxLayout.Direction.TopToBottom if narrow else QBoxLayout.Direction.LeftToRight)
        for widget in (self.recent_card,self.today_card,self.team_card):self.grid.removeWidget(widget)
        if narrow:
            self.grid.addWidget(self.recent_card,0,0);self.grid.addWidget(self.today_card,1,0);self.grid.addWidget(self.team_card,2,0)
        else:
            self.grid.addWidget(self.recent_card,0,0,2,1);self.grid.addWidget(self.today_card,0,1);self.grid.addWidget(self.team_card,1,1)
        self.grid.setColumnStretch(0,3 if not narrow else 1);self.grid.setColumnStretch(1,2 if not narrow else 0)

    def resizeEvent(self,event):
        super().resizeEvent(event)
        self._arrange()

    def refresh_data(self,repo,roster,today=None):
        today=today or date.today()
        self.today=today.isoformat()
        self.subtitle.setText(full_date(QDate(today.year,today.month,today.day))+' · Planifiez une journée pédagogique à la fois.')
        self.days=recent_days(repo)
        clear(self.rows);clear(self.today_content);clear(self.team_rows)
        self.day_buttons=[];self.day_delete_buttons=[]
        self.previous_button.setEnabled(bool(self.days))
        if not self.days:
            self.rows.addWidget(label("Aucune journée pour l’instant"))
            self.empty_new_button=button('Nouvelle journée pédagogique',self.new_day.emit,True)
            self.rows.addWidget(self.empty_new_button)
        for brief in self.days:
            item=DayButton(brief,brief.date==self.today,self.open_day.emit)
            row=QWidget();line=QHBoxLayout(row);line.setContentsMargins(0,0,0,0);line.setSpacing(8)
            line.addWidget(item,1)
            remove=button('Supprimer',lambda selected=brief.date:self.delete_day.emit(selected))
            remove.setAccessibleName(f'Supprimer {brief.name}, {brief.date}')
            remove.setToolTip('Retirer cette journée de l’accueil. Son historique reste conservé.')
            line.addWidget(remove)
            self.rows.addWidget(row);self.day_buttons.append(item);self.day_delete_buttons.append(remove)
        current=next((d for d in self.days if d.date==self.today),None)
        self.today_brief=current
        if current:
            metrics=QGridLayout();metrics.setSpacing(14)
            for index,(value,caption) in enumerate(((str(current.children),'enfants inscrits'),(str(current.minimum),'éducatrices minimum'),(current.paid,'heures planifiées'),(str(current.alerts),'alertes à vérifier'))):
                cell=QWidget();layout=QVBoxLayout(cell);layout.setContentsMargins(0,0,0,0)
                number=label(value);number.setStyleSheet('font-size:28px;font-weight:700;color:'+('#804500' if index==3 and current.alerts else '#203D32')+';')
                layout.addWidget(number);layout.addWidget(label(caption,'homeSecondary'));metrics.addWidget(cell,index//2,index%2)
            self.today_content.addLayout(metrics)
            self.today_button=button('Continuer la planification',lambda:self.open_day.emit(self.today),True)
        else:
            self.today_content.addWidget(label("Aucune journée planifiée aujourd’hui"))
            self.today_button=button("Créer la journée d’aujourd’hui",self.create_today.emit,True)
        self.today_content.addWidget(self.today_button)
        people=sorted((e for e in roster.educators if e.active),key=lambda e:(e.seniority,e.name.casefold()))
        if not people:self.team_rows.addWidget(label('Aucune éducatrice active'))
        for person in people:
            item=button('',lambda _checked=False,eid=person.id:self.edit_educator.emit(eid))
            item.setAccessibleName(f'{person.name}. Rang {person.seniority}. Modifier le profil.')
            line=QHBoxLayout(item);line.setContentsMargins(8,4,8,4)
            dot=QLabel('●');dot.setStyleSheet(f'color:{person.color};font-size:22px;');dot.setFixedWidth(22)
            line.addWidget(dot);line.addWidget(label(person.name),1);line.addWidget(QLabel(f'Rang {person.seniority}'))
            for child in item.findChildren(QWidget):child.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            self.team_rows.addWidget(item)
        self._arrange()
