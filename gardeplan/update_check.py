"""Bounded native checks of staged and rolled-back portable executables."""
from datetime import date
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def check_update_launch(destination):
    report={'success':False,'frozen':bool(getattr(sys,'frozen',False))}
    window=None
    try:
        from PySide6.QtWidgets import QApplication
        from gardeplan import __version__
        from gardeplan.data_paths import portable_root
        from gardeplan.daily import day_plan
        from gardeplan.storage import Repository
        from gardeplan.ui.main_window import MainWindow
        from gardeplan.updater import activate_pending,atomic_json
        application=QApplication.instance() or QApplication(['verification-mise-a-jour'])
        root=portable_root()
        if root is None or not report['frozen']:raise ValueError('Ce contrôle nécessite le logiciel portable compilé.')
        activate_pending(root)
        repo=Repository(root/'donnees/gardeplan.sqlite')
        plan=repo.latest_week() or day_plan(date.today().isoformat())
        window=MainWindow(repo,plan);window.show();application.processEvents()
        if window.home_page.grab().isNull():raise ValueError('L’accueil de la version copiée ne peut pas être dessiné.')
        report.update(success=True,version=__version__,qt_platform=application.platformName(),title=plan.day_names.get(0,''))
    except Exception as error:report['error']=str(error)
    finally:
        if window is not None:
            window.autosave.stop();window.hide();window.deleteLater();application.processEvents()
    from gardeplan.updater import atomic_json
    output=Path(destination);output.parent.mkdir(parents=True,exist_ok=True);atomic_json(output,report)
    return 0 if report['success'] else 1


def verify_update_archive(archive,repository,current_root,expected_version):
    from gardeplan.portable_package import inspect_archive
    from gardeplan.updater import prepare_update,prepare_rollback
    from gardeplan.storage import Repository
    package=inspect_archive(archive,expected_version,allow_same=True)
    with tempfile.TemporaryDirectory(prefix='sdg-controle-mise-a-jour-') as temporary:
        parent=Path(temporary)
        prepared=prepare_update(package,repository,parent,current_root=current_root,current_version=expected_version)
        # A later save must be recovered at first launch, not silently lost.
        original=repository.latest_week();original.day_names[0]='Vérification après préparation';repository.save(original)
        def launch(value,name,expected_title):
            destination=parent/name
            result=subprocess.run([str(value.executable),'--check-update-launch',str(destination)],
                                  cwd=value.folder,timeout=45,check=False,
                                  env={**os.environ,'PYINSTALLER_RESET_ENVIRONMENT':'1'})
            if result.returncode!=0 or not destination.is_file():raise ValueError('La version préparée ne démarre pas correctement.')
            report=json.loads(destination.read_text(encoding='utf-8'))
            if report.get('success') is not True or report.get('frozen') is not True or report.get('version')!=value.version or report.get('title')!=expected_title:
                raise ValueError('Le démarrage préparé ne retrouve pas les données attendues : '+str(report))
        launch(prepared,'nouvelle-version.json','Vérification après préparation')
        updated=Repository(prepared.folder/'donnees/gardeplan.sqlite')
        changed=updated.latest_week();changed.day_names[0]='Travail après mise à jour';updated.save(changed)
        restored=prepare_rollback(prepared.folder,updated,parent)
        launch(restored,'retour-version.json','Vérification après préparation')
        if updated.latest_week().day_names[0]!='Travail après mise à jour':
            raise ValueError('Le retour a modifié les données de la version actuelle.')
    return True
