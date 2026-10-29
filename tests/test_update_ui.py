"""Real assistant operations; launching a binary is covered by native checks."""
import time
from threading import Event

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget

from gardeplan.ui.motion import Motion
from gardeplan.ui.update import UpdateDialog
from gardeplan.ui.main_window import MainWindow
from gardeplan.updater import PreparedUpdate
from test_updater import update_case


def finish(dialog, qapp):
    deadline=time.monotonic()+15
    while dialog.busy and time.monotonic()<deadline:
        QTest.qWait(10);qapp.processEvents()
    assert not dialog.busy


def test_assistant_inspects_prepares_and_waits_for_explicit_launch(update_case,qapp,monkeypatch):
    old,repo,package,destination=update_case
    root=QWidget();motion=Motion(root)
    dialog=UpdateDialog(repo,motion,'0.5.0',old,root,expected_platform='windows',expected_arch='x64')
    dialog.destination=destination
    monkeypatch.setattr(QFileDialog,'getOpenFileName',lambda *args:(str(package.path),'ZIP'))
    original=repo.latest_week()
    dialog.show();dialog.choose_zip();finish(dialog,qapp)
    assert dialog.package is not None and dialog.prepare_button.isEnabled()
    dialog.prepare();finish(dialog,qapp)
    assert dialog.prepared is not None and dialog.launch_button.isVisible()
    assert not dialog.want_launch and repo.latest_week()==original
    # Keeping the current version must not launch or discard either folder.
    dialog.reject()
    assert not dialog.want_launch and dialog.prepared.folder.is_dir()
    dialog.deleteLater();root.deleteLater();qapp.processEvents()


def test_busy_assistant_refuses_escape_and_window_close(qapp,tmp_path):
    from gardeplan.storage import Repository
    root=QWidget();dialog=UpdateDialog(Repository(tmp_path/'gardeplan.sqlite'),Motion(root),'0.5.0',None,root)
    release=Event();dialog.show()
    dialog.run_operation('inspect',lambda:release.wait(10))
    try:
        QTest.keyClick(dialog,Qt.Key.Key_Escape)
        assert dialog.isVisible() and dialog.busy
        assert not dialog.close() and dialog.isVisible()
    finally:
        # Operation deliberately fails with a useful message rather than returning a package.
        dialog._operation_error='Vérification interrompue pour le test'
        release.set();finish(dialog,qapp)
        dialog.close();dialog.deleteLater();root.deleteLater();qapp.processEvents()


def test_failed_launch_keeps_current_window_and_saved_data(update_case,qapp,monkeypatch):
    from gardeplan.updater import prepare_update
    old,repo,package,destination=update_case
    window=MainWindow(repo,repo.latest_week());window.show();qapp.processEvents()
    prepared=prepare_update(package,repo,destination,current_root=old,current_version='0.5.0')
    window._pending_update=prepared
    messages=[]
    monkeypatch.setattr(QMessageBox,'warning',lambda *args:messages.append(args[2]))
    monkeypatch.setattr(window,'_launch_updated',lambda value:False)
    event=QCloseEvent();window.closeEvent(event)
    assert not event.isAccepted() and window.isVisible()
    assert messages and repo.latest_week() is not None and prepared.folder.is_dir()
    window._pending_update=None;window.close();window.deleteLater();qapp.processEvents()


def test_launcher_uses_independent_pyinstaller_environment_and_native_command(tmp_path,monkeypatch):
    from gardeplan.ui import main_window
    seen=[]
    class Process:
        def __init__(self):self.values={};seen.append(self.values)
        def setProcessEnvironment(self,value):self.values['environment']=value
        def setWorkingDirectory(self,value):self.values['cwd']=value
        def setProgram(self,value):self.values['program']=value
        def setArguments(self,value):self.values['arguments']=value
        def startDetached(self):return True,123
    monkeypatch.setattr(main_window,'QProcess',Process)
    for platform,path in [('windows','Planificateur-SDG.exe'),('macos','Planificateur-SDG.app/Contents/MacOS/Planificateur-SDG')]:
        value=PreparedUpdate(tmp_path,tmp_path/path,'0.5.1',platform)
        assert MainWindow._launch_updated(value)
        assert seen[-1]['environment'].value('PYINSTALLER_RESET_ENVIRONMENT')=='1'
        assert seen[-1]['cwd']==str(tmp_path)
    assert seen[0]['program'].endswith('.exe') and seen[0]['arguments']==[]
    assert seen[1]['program']=='/usr/bin/open'
    assert seen[1]['arguments']==['-n',str(tmp_path/'Planificateur-SDG.app')]
