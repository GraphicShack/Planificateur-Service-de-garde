"""Offline portable update assistant. Only an explicit launch closes the app."""
from pathlib import Path
from PySide6.QtCore import QThread,Signal,Qt
from PySide6.QtWidgets import (QDialog,QFrame,QLabel,QPushButton,QScrollArea,QSizePolicy,
                              QFileDialog,QVBoxLayout,QWidget)
from ..portable_package import inspect_archive,machine,system
from ..updater import prepare_update,prepare_rollback,read_receipt
from .appearance import set_themed_style
from .loading import LoadingSpinner
from .theme import EDITOR_STYLE
from .flow_layout import FlowLayout


class UpdateOperation(QThread):
    completed=Signal(object)
    failed=Signal(str)

    def __init__(self,operation,parent=None):
        super().__init__(parent);self.operation=operation

    def run(self):
        try:self.completed.emit(self.operation())
        except Exception as error:self.failed.emit(str(error))


class UpdateDialog(QDialog):
    def __init__(self,repository,motion,current_version,current_root,parent=None,*,rollback=False,
                 expected_platform=None,expected_arch=None):
        super().__init__(parent)
        self.repository=repository;self.motion=motion;self.current_version=current_version
        self.current_root=current_root;self.rollback=rollback
        self.expected_platform=expected_platform;self.expected_arch=expected_arch
        self.worker=None;self.package=None;self.prepared=None;self.want_launch=False
        self._operation_result=None;self._operation_error=''
        self.setObjectName('editorDialog');set_themed_style(self,EDITOR_STYLE)
        self.setWindowTitle('Revenir à la version précédente' if rollback else 'Mettre à jour le logiciel')
        self.setMinimumSize(520,400);self.resize(650,590)
        root_layout=QVBoxLayout(self);root_layout.setContentsMargins(18,18,18,18)
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setFrameShape(QFrame.Shape.NoFrame)
        body=QWidget();outer=QVBoxLayout(body);outer.setContentsMargins(4,4,4,4);outer.setSpacing(14)
        scroll.setWidget(body);root_layout.addWidget(scroll,1)
        heading=QLabel(self.windowTitle());heading.setObjectName('editorHeading');heading.setWordWrap(True);outer.addWidget(heading)
        self.description=QLabel('Le retour prépare un autre dossier avec l’ancienne version et les données sauvegardées avant la mise à jour. Votre version actuelle et les modifications plus récentes restent conservées.' if rollback else
            'Choisissez le ZIP portable téléchargé depuis les publications GitHub du projet. Le logiciel vérifie les fichiers, copie les journées, les profils, les historiques et les préférences, puis prépare un nouveau dossier. Aucun installateur ni connexion ne sont nécessaires.')
        self.description.setWordWrap(True);self.description.setTextFormat(Qt.TextFormat.PlainText);outer.addWidget(self.description)
        self.version_label=QLabel('Version actuelle : '+current_version)
        self.version_label.setWordWrap(True);outer.addWidget(self.version_label)
        self.zip_button=QPushButton('Choisir le ZIP de mise à jour…');self.zip_button.clicked.connect(self.choose_zip)
        self.zip_button.setMinimumHeight(44);outer.addWidget(self.zip_button)
        self.archive_label=QLabel('Aucun ZIP sélectionné');self.archive_label.setWordWrap(True);self.archive_label.setTextFormat(Qt.TextFormat.PlainText);outer.addWidget(self.archive_label)
        self.destination=(Path(current_root).parent if current_root else repository.path.parent.parent).resolve()
        self.folder_button=QPushButton('Choisir le dossier de destination…');self.folder_button.setMinimumHeight(44)
        self.folder_button.clicked.connect(self.choose_destination);outer.addWidget(self.folder_button)
        self.destination_label=QLabel(str(self.destination));self.destination_label.setWordWrap(True);self.destination_label.setTextFormat(Qt.TextFormat.PlainText);outer.addWidget(self.destination_label)
        self.status=QLabel('');self.status.setWordWrap(True);self.status.setTextFormat(Qt.TextFormat.PlainText);outer.addWidget(self.status)
        self.spinner=LoadingSpinner(motion,self);self.spinner.hide();outer.addWidget(self.spinner,0,Qt.AlignmentFlag.AlignHCenter)
        outer.addStretch()
        actions=FlowLayout(spacing=8);self.prepare_button=QPushButton('Préparer le retour' if rollback else 'Préparer la mise à jour')
        self.prepare_button.setObjectName('editorSave');self.prepare_button.setMinimumHeight(44)
        self.prepare_button.setEnabled(False);self.prepare_button.clicked.connect(self.prepare)
        self.launch_button=QPushButton('Fermer et démarrer la nouvelle version');self.launch_button.setMinimumHeight(44)
        self.launch_button.setObjectName('editorSave');self.launch_button.clicked.connect(self.launch);self.launch_button.hide()
        self.close_button=QPushButton('Fermer');self.close_button.setMinimumHeight(44);self.close_button.clicked.connect(self.reject)
        for button in (self.prepare_button,self.launch_button,self.close_button):actions.addWidget(button)
        root_layout.addLayout(actions)
        for label in self.findChildren(QLabel):
            label.setTextFormat(Qt.TextFormat.PlainText);label.setMinimumWidth(0)
            policy=label.sizePolicy();policy.setHorizontalPolicy(QSizePolicy.Policy.Ignored);label.setSizePolicy(policy)
        if rollback:
            self.zip_button.hide();self.archive_label.hide()
            try:
                data=read_receipt(current_root)
                if data.get('operation')!='update' or not data.get('previous_root'):raise ValueError('Aucun retour préparé par cet assistant n’est disponible.')
                self.version_label.setText(f"Version actuelle : {current_version} → version conservée : {data['previous_version']}")
                self.status.setText('Les données restaurées seront celles d’avant cette mise à jour. Les changements plus récents seront conservés séparément.')
                self.prepare_button.setEnabled(True)
            except (OSError,ValueError,TypeError,KeyError) as error:self.status.setText(str(error))

    @property
    def busy(self):return self.worker is not None

    def choose_zip(self):
        path,_=QFileDialog.getOpenFileName(self,'Choisir le ZIP portable','','Archives ZIP (*.zip)')
        if not path:return
        self.package=None;self.archive_label.setText(path)
        self.run_operation('inspect',lambda:inspect_archive(path,self.current_version,
            self.expected_platform or system(),self.expected_arch or machine()))

    def choose_destination(self):
        value=QFileDialog.getExistingDirectory(self,'Choisir un dossier de destination',str(self.destination))
        if value:
            self.destination=Path(value).resolve();self.destination_label.setText(str(self.destination))

    def run_operation(self,name,operation):
        if self.busy:return
        self.operation_name=name;self._operation_result=None;self._operation_error=''
        self.worker=UpdateOperation(operation,self)
        owner=self.parentWidget()
        if owner is not None and hasattr(owner,'_worker'):
            if owner._worker is not None:
                self.worker.deleteLater();self.worker=None;return
            owner._worker=self.worker;owner.refresh()
        for button in (self.zip_button,self.folder_button,self.prepare_button,self.close_button):button.setEnabled(False)
        self.status.setText('Analyse du ZIP et de sa compatibilité…' if name=='inspect' else 'Préparation du dossier et vérification de la copie des données…')
        self.spinner.show()
        self.worker.completed.connect(self._completed)
        self.worker.failed.connect(self._failed)
        self.worker.finished.connect(self._finished)
        self.worker.start()

    def _completed(self,value):self._operation_result=value
    def _failed(self,message):self._operation_error=message

    def _finished(self):
        worker=self.worker;self.worker=None
        owner=self.parentWidget()
        if owner is not None and getattr(owner,'_worker',None) is worker:
            owner._worker=None;owner.refresh()
        worker.deleteLater();self.spinner.hide()
        for button in (self.zip_button,self.folder_button,self.close_button):button.setEnabled(True)
        if self._operation_error:
            self.status.setText('La préparation n’a pas abouti : '+self._operation_error+' Votre version actuelle reste conservée.')
            self.prepare_button.setEnabled(self.rollback or self.package is not None)
            return
        if self.operation_name=='inspect':
            self.package=self._operation_result
            self.version_label.setText(f"Version actuelle : {self.current_version} → version du ZIP : {self.package.manifest['version']}")
            self.status.setText('ZIP compatible. Une copie de sécurité sera conservée avant le démarrage de la nouvelle version.')
            self.prepare_button.setEnabled(True)
        else:
            self.prepared=self._operation_result
            self.version_label.setText('Version '+self.prepared.version+' prête dans :\n'+str(self.prepared.folder))
            self.status.setText('Les fichiers et la copie des données ont été vérifiés. Le dossier actuel reste conservé. Fermez cette version pour démarrer celle qui vient d’être préparée.')
            self.launch_button.setText('Fermer et démarrer la version '+self.prepared.version)
            self.prepare_button.hide();self.zip_button.hide();self.folder_button.hide();self.archive_label.hide();self.destination_label.hide()
            self.launch_button.show();self.close_button.setText('Garder la version actuelle')

    def prepare(self):
        if self.rollback:
            self.run_operation('prepare',lambda:prepare_rollback(self.current_root,self.repository,self.destination))
        elif self.package is not None:
            self.run_operation('prepare',lambda:prepare_update(self.package,self.repository,self.destination,
                current_root=self.current_root,current_version=self.current_version))

    def launch(self):
        if self.prepared is not None and not self.busy:
            self.want_launch=True;self.accept()

    def reject(self):
        if not self.busy:super().reject()

    def closeEvent(self,event):
        if self.busy:event.ignore()
        else:super().closeEvent(event)
