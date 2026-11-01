"""Recreate bundled FAQ screenshots from real widgets and fictitious data.

Run from a development environment with the application dependencies installed:
QT_QPA_PLATFORM=offscreen QT_SCALE_FACTOR=1.5 python scripts/capture_faq.py
No personal database is opened. No network access is needed.
"""
from copy import deepcopy
from datetime import date
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from PySide6.QtCore import QPoint,QRect,QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication,QDialog
from gardeplan import __version__
from gardeplan.app import STYLE
from gardeplan.daily import day_plan
from gardeplan.models import Educator,Group,GroupPeriod,Break,paid_minutes
from gardeplan.optimizer import generate
from gardeplan.storage import Repository
from gardeplan.validation import validate
from gardeplan.ui.forms import EducatorDialog,ShiftDialog
from gardeplan.ui.main_window import MainWindow
from gardeplan.ui.proposal import ProposalDialog
from gardeplan.ui.theme import light_palette
from gardeplan.ui.update import UpdateDialog


DESTINATION=ROOT/'gardeplan/assets/faq'


def capture(widget,name,region=None):
    QApplication.processEvents();QTest.qWait(180)
    pixmap=widget.grab(region) if region is not None else widget.grab()
    if pixmap.isNull() or not pixmap.save(str(DESTINATION/(name+'.png')),'PNG'):
        raise RuntimeError('Capture impossible : '+name)
    print('Capture : '+name,flush=True)


def modal_capture(action,name,expected_title):
    errors=[]
    def take():
        dialog=QApplication.activeModalWidget()
        try:
            if not isinstance(dialog,QDialog) or dialog.windowTitle()!=expected_title:
                raise RuntimeError('Fenêtre attendue absente : '+expected_title)
            capture(dialog,name)
        except Exception as error:errors.append(error)
        finally:
            if isinstance(dialog,QDialog):dialog.reject()
    timer=QTimer();timer.setSingleShot(True);timer.timeout.connect(take);timer.start(600)
    try:action()
    finally:timer.stop()
    if errors:raise errors[0]


def main():
    DESTINATION.mkdir(parents=True,exist_ok=True)
    app=QApplication.instance() or QApplication([])
    app.setStyleSheet(STYLE);app.setPalette(light_palette())
    from gardeplan.ui.localization import install_french_translations
    install_french_translations(app)
    request=day_plan('2026-11-02');request.day_names[0]='Pédagogique — Les explorateurs'
    names=('Camille Roy','Sophie Martin','Emma Gagnon','Léa Tremblay',
           'Alice Dubois','Chloé Fortin','Juliette Bouchard','Sarah Côté')
    colors=('#3F8B83','#5E7FC2','#BD825F','#8A6AAF','#8D775A','#638D80','#9A7799','#4C8FAD')
    request.educators=[Educator('e'+str(i),name,seniority=i+1,target_minutes=0,max_minutes=480,color=colors[i]) for i,name in enumerate(names)]
    request.groups=[Group(group,'Groupe '+group,periods=[GroupPeriod(0,420,1050,20)]) for group in ('A','B')]
    generated=generate(request,time_limit=25)
    if not generated.success or any(i.severity=='error' for i in validate(generated.proposal)):
        raise RuntimeError('La journée d’exemple ne peut pas être générée : '+generated.message)
    plan=generated.proposal
    assert all(sum(paid_minutes(s) for s in plan.shifts if s.educator_id==e.id)<=480 for e in plan.educators)
    with tempfile.TemporaryDirectory(prefix='sdg-captures-faq-') as folder:
        repository=Repository(Path(folder)/'donnees/gardeplan.sqlite');repository.save(plan)
        with patch('gardeplan.session_user.session_name',return_value='Camille'):
            window=MainWindow(repository,plan);window.resize(1440,940);window.show()
        try:
            window.home_page.refresh_data(repository,plan,today=date(2026,11,2))
            capture(window,'accueil')
            window.show_planner();window.fit_day();capture(window,'grille')
            window.enrolment();app.processEvents()
            panel=window.enrolment_panel
            # Stop in the gap after the live count; do not clip a line of the
            # longer explanation that follows it.
            capture(panel,'inscriptions',QRect(0,0,panel.width(),panel.preview.geometry().bottom()+4))
            window.show_management('team')
            capture(window.educator_list.itemWidget(window.educator_list.item(0)),'equipe')
            shift=deepcopy(min(plan.shifts,key=lambda s:(s.start,s.end)))
            shift.breaks=[Break(690,720,False)]
            editor=ShiftDialog(plan,shift,parent=window);editor.resize(780,820);editor.show()
            capture(editor,'quart')
            editor.tabs.setCurrentIndex(1);capture(editor,'pauses')
            editor.reject();editor.deleteLater()
            profile=EducatorDialog(plan,plan.educators[0],window);profile.resize(1120,900);profile.show()
            capture(profile,'profil');profile.reject();profile.deleteLater()
            comparison=ProposalDialog(request,generated,window);comparison.resize(1180,900);comparison.show()
            capture(comparison,'proposition')
            comparison.tabs.setCurrentWidget(comparison.report);capture(comparison,'bilan')
            comparison.reject();comparison.deleteLater()
            broken=deepcopy(plan)
            affected=next(s for s in broken.shifts if s.start<690 and s.end>720)
            affected.breaks=[Break(690,720,False)]
            window._load(broken);window.verify()
            if window.alert_list.count():
                window.alert_list.setCurrentRow(0);window.navigate_issue(window.alert_list.item(0))
            capture(window,'alertes')
            window._load(plan);window.show_planner();window.fit_day()
            window._sync_menu_actions();window.file_menu.popup(window.folder_button.mapToGlobal(QPoint(60,0)))
            capture(window.file_menu,'dossier');window.file_menu.hide()
            modal_capture(lambda:window._preview_pdf('general',None),'pdf','Aperçu PDF')
            update=UpdateDialog(repository,window.motion,__version__,None,window);update.show()
            capture(update,'mise-a-jour');update.reject();update.deleteLater()
            modal_capture(window.show_display_options,'affichage','Affichage du calendrier')
            assert window.week.to_dict()==plan.to_dict()
        finally:
            window.autosave.stop();window.dirty=False;window.close();window.deleteLater();app.processEvents()
    print('14 captures réelles enregistrées ; données fictives uniquement.',flush=True)


if __name__=='__main__':main()
