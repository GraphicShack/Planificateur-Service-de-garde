"""Bundled example screenshots, responsive previews and a keyboard zoom viewer."""
from dataclasses import dataclass
from pathlib import Path
from PySide6.QtCore import Qt,QSize,QEvent,QTimer,Signal
from PySide6.QtGui import QImageReader,QPixmap,QPainter,QColor,QKeySequence,QShortcut
from PySide6.QtWidgets import (QDialog,QLabel,QPushButton,QScrollArea,QSizePolicy,
                              QVBoxLayout,QWidget,QFrame)
from .appearance import set_themed_style
from .flow_layout import FlowLayout
from .theme import EDITOR_STYLE

CAPTURE_ROOT=Path(__file__).resolve().parent.parent/'assets/faq'


@dataclass(frozen=True)
class CaptureSpec:
    filename: str
    caption: str


CAPTURES={
    'accueil':CaptureSpec('accueil.png','Depuis l’accueil, créez une journée ou ouvrez une journée récente.'),
    'inscriptions':CaptureSpec('inscriptions.png','Le panneau Inscriptions indique les effectifs et le besoin de personnel.'),
    'grille':CaptureSpec('grille.png','Les quarts sont placés à l’heure exacte, dans les colonnes des groupes.'),
    'quart':CaptureSpec('quart.png','Le formulaire du quart permet de saisir les heures et les pauses.'),
    'pauses':CaptureSpec('pauses.png','Précisez le début, la fin et le caractère payé ou non payé de chaque pause.'),
    'profil':CaptureSpec('profil.png','Le profil réunit le rang, les heures, les disponibilités et les préférences.'),
    'proposition':CaptureSpec('proposition.png','Examinez la grille proposée avant de confirmer son application.'),
    'bilan':CaptureSpec('bilan.png','Le bilan compare la couverture, les heures et les interruptions.'),
    'alertes':CaptureSpec('alertes.png','Sélectionnez une alerte pour retrouver sa plage dans la grille.'),
    'equipe':CaptureSpec('equipe.png','La carte d’équipe montre les heures et l’action Signaler une absence.'),
    'dossier':CaptureSpec('dossier.png','Le menu Dossier regroupe les journées, les versions et les sauvegardes.'),
    'pdf':CaptureSpec('pdf.png','L’aperçu PDF montre le document lettre paysage prêt à imprimer.'),
    'mise-a-jour':CaptureSpec('mise-a-jour.png','L’assistant prépare une autre version depuis un ZIP portable.'),
    'affichage':CaptureSpec('affichage.png','Les options d’affichage regroupent le zoom, les thèmes et les animations.'),
}


class ImageButton(QPushButton):
    def __init__(self,text,parent=None):
        super().__init__(text,parent);self.setMinimumHeight(44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def changeEvent(self,event):
        if event.type()==QEvent.Type.EnabledChange:
            self.setCursor(Qt.CursorShape.PointingHandCursor if self.isEnabled() else Qt.CursorShape.ArrowCursor)
        super().changeEvent(event)

    def keyPressEvent(self,event):
        if event.key() in (Qt.Key.Key_Return,Qt.Key.Key_Enter):
            self.click();event.accept();return
        super().keyPressEvent(event)


class CaptureThumbnail(QWidget):
    availability_changed=Signal(bool)

    def __init__(self,spec,parent=None):
        super().__init__(parent);self.spec=spec;self.path=CAPTURE_ROOT/spec.filename
        self.intrinsic=QImageReader(str(self.path)).size()
        self.pixmap=None
        self.setMinimumSize(0,0);self.setMaximumSize(900,360)
        policy=QSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Preferred)
        policy.setHeightForWidth(True);self.setSizePolicy(policy)
        self.setAccessibleName('Capture d’exemple : '+spec.caption)

    def heightForWidth(self,width):
        if not self.intrinsic.isValid():return 60
        return max(2,min(360,round(self.intrinsic.height()*min(max(1,width-2),self.intrinsic.width())/self.intrinsic.width())+2))

    def sizeHint(self):return QSize(760,self.heightForWidth(760))
    def minimumSizeHint(self):return QSize(0,0)

    def showEvent(self,event):
        super().showEvent(event)
        if self.pixmap is None:
            self.pixmap=QPixmap(str(self.path))
            if not self.pixmap.isNull():self.pixmap.setDevicePixelRatio(1)
            self.availability_changed.emit(not self.pixmap.isNull())
            self.updateGeometry();self.update()

    def paintEvent(self,event):
        painter=QPainter(self)
        if self.pixmap is None or self.pixmap.isNull():
            painter.setPen(QColor('#52655E'));font=painter.font();font.setPixelSize(16);painter.setFont(font)
            painter.drawText(self.rect(),Qt.AlignmentFlag.AlignCenter,'Capture indisponible')
            return
        size=self.pixmap.size();size.scale(self.size()-QSize(2,2),Qt.AspectRatioMode.KeepAspectRatio)
        scaled=self.pixmap.scaled(size,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation)
        left=0
        painter.drawPixmap(left,1,scaled)
        painter.setPen(QColor('#D9E3DD'));painter.drawRect(left,0,max(1,scaled.width()),max(1,scaled.height()+1))

    def hideEvent(self,event):
        self.pixmap=None
        super().hideEvent(event)


class CaptureDialog(QDialog):
    def __init__(self,spec,parent=None):
        super().__init__(parent);self.spec=spec;self.fit_mode=True;self.zoom=1.0
        self.setObjectName('editorDialog');set_themed_style(self,EDITOR_STYLE)
        self.setWindowTitle('Capture d’écran — exemple');self.setMinimumSize(360,320)
        available=self.screen().availableGeometry();self.resize(min(1180,available.width()-30),min(860,available.height()-30))
        layout=QVBoxLayout(self);layout.setContentsMargins(16,16,16,16);layout.setSpacing(10)
        caption=QLabel(spec.caption);caption.setTextFormat(Qt.TextFormat.PlainText);caption.setWordWrap(True);caption.setMinimumWidth(0)
        policy=caption.sizePolicy();policy.setHorizontalPolicy(QSizePolicy.Policy.Ignored);caption.setSizePolicy(policy)
        layout.addWidget(caption)
        self.scroll=QScrollArea();self.scroll.setWidgetResizable(False)
        self.scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll.setFrameShape(QFrame.Shape.StyledPanel);self.scroll.setAccessibleName('Capture agrandie, défilable')
        self.image=QLabel();self.image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image.setAccessibleName('Capture d’exemple : '+spec.caption);self.scroll.setWidget(self.image)
        self.original=QPixmap(str(CAPTURE_ROOT/spec.filename))
        if not self.original.isNull():self.original.setDevicePixelRatio(1)
        else:self.image.setText('Capture indisponible');self.image.setFixedSize(300,60)
        layout.addWidget(self.scroll,1)
        toolbar=FlowLayout(spacing=8)
        self.out_button=ImageButton('− Réduire');self.in_button=ImageButton('+ Agrandir')
        self.fit_button=ImageButton('Adapter à la fenêtre');self.actual_button=ImageButton('100 %')
        self.close_button=ImageButton('Fermer');self.zoom_label=QLabel('100 %');self.zoom_label.setMinimumWidth(65)
        for widget in (self.out_button,self.in_button,self.fit_button,self.actual_button,self.zoom_label,self.close_button):toolbar.addWidget(widget)
        layout.addLayout(toolbar)
        self.out_button.clicked.connect(lambda:self.set_zoom(self.zoom/1.25))
        self.in_button.clicked.connect(lambda:self.set_zoom(self.zoom*1.25))
        self.actual_button.clicked.connect(lambda:self.set_zoom(1.0))
        self.fit_button.clicked.connect(self.fit_to_window);self.close_button.clicked.connect(self.reject)
        self._fit_timer=QTimer(self);self._fit_timer.setSingleShot(True);self._fit_timer.timeout.connect(self.fit_to_window)
        self.scroll.viewport().installEventFilter(self)
        self.shortcuts=[]
        for key,callback in ((QKeySequence(QKeySequence.StandardKey.ZoomIn),lambda:self.set_zoom(self.zoom*1.25)),
                             (QKeySequence(QKeySequence.StandardKey.ZoomOut),lambda:self.set_zoom(self.zoom/1.25)),
                             (QKeySequence('Ctrl+0'),self.fit_to_window),(QKeySequence('Ctrl+1'),lambda:self.set_zoom(1.0))):
            shortcut=QShortcut(key,self);shortcut.activated.connect(callback);self.shortcuts.append(shortcut)
        for button in (self.out_button,self.in_button,self.fit_button,self.actual_button):button.setEnabled(not self.original.isNull())

    def eventFilter(self,watched,event):
        if event.type()==QEvent.Type.Resize and self.fit_mode:self._fit_timer.start(0)
        return super().eventFilter(watched,event)

    def showEvent(self,event):
        super().showEvent(event)
        if self.fit_mode:self._fit_timer.start(0)

    def hideEvent(self,event):
        self._fit_timer.stop();super().hideEvent(event)

    def fit_to_window(self):
        self._fit_timer.stop();self.fit_mode=True
        if self.original.isNull():return
        area=self.scroll.viewport().size()-QSize(6,6)
        self._apply_zoom(min(1.0,max(1,area.width())/self.original.width(),max(1,area.height())/self.original.height()))

    def set_zoom(self,value):
        self._fit_timer.stop();self.fit_mode=False;self._apply_zoom(value)

    def _apply_zoom(self,value):
        if self.original.isNull():return
        self.zoom=max(.05,min(3.0,float(value)))
        size=QSize(max(1,round(self.original.width()*self.zoom)),max(1,round(self.original.height()*self.zoom)))
        self.image.setFixedSize(size)
        self.image.setPixmap(self.original.scaled(size,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
        self.zoom_label.setText(str(round(self.zoom*100))+' %')


class FaqFigure(QWidget):
    def __init__(self,spec,parent=None):
        super().__init__(parent);self.spec=spec;self.setMinimumWidth(0)
        layout=QVBoxLayout(self);layout.setContentsMargins(0,6,0,0);layout.setSpacing(8)
        caption=QLabel('Capture d’exemple — '+spec.caption);caption.setWordWrap(True);caption.setMinimumWidth(0)
        caption.setTextFormat(Qt.TextFormat.PlainText);layout.addWidget(caption)
        self.thumbnail=CaptureThumbnail(spec);layout.addWidget(self.thumbnail)
        self.open_button=ImageButton('Agrandir la capture')
        self.open_button.setAccessibleName('Agrandir la capture : '+spec.caption)
        self.open_button.setEnabled(self.thumbnail.intrinsic.isValid())
        self.thumbnail.availability_changed.connect(self.open_button.setEnabled)
        self.open_button.clicked.connect(self.open_capture);layout.addWidget(self.open_button,0,Qt.AlignmentFlag.AlignLeft)

    def open_capture(self):
        dialog=CaptureDialog(self.spec,self)
        try:dialog.exec()
        finally:dialog.deleteLater()
